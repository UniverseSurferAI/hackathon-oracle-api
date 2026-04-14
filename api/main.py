"""
Hackathon Oracle API - Main FastAPI Application
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from loguru import logger

from api.fee_calculator import FeeCalculator
from api.resolution import HackathonOracle
from api.database import (
    init_db, create_market, get_market, get_all_markets,
    update_market_volume, resolve_market as db_resolve_market,
    close_market_betting as db_close_market_betting,
    record_fee, get_fee_history, register_webhook, get_webhooks
)
from api.webhooks import notifier
from api.scraping import website_scraper

# Initialize FastAPI app
app = FastAPI(
    title="Hackathon Oracle API",
    description="Oracle API for hackathon prediction market resolution",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
init_db()

# Initialize fee calculator (2% on volume)
fee_calculator = FeeCalculator(
    fee_percentage=2.0,
    fee_wallet_address="0x7252c6477139989916F5c41b969208C5B947AC1d"
)

# Initialize oracle
oracle = HackathonOracle(fee_calculator)

# In-memory cache for quick access (backed by database)
active_markets = {}
fee_history = []

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class DataSource(BaseModel):
    """Data source configuration for a hackathon"""
    twitter: Optional[str] = None
    website: Optional[str] = None
    discord: Optional[str] = None

class CreateMarketRequest(BaseModel):
    """Request to create a new hackathon market"""
    platform_id: str = Field(..., description="ID of the platform creating the market")
    market_id: str = Field(..., description="Unique market ID from the platform")
    hackathon_name: str = Field(..., description="Name of the hackathon")
    teams: list[str] = Field(..., description="List of team names participating")
    data_sources: DataSource = Field(..., description="Where to monitor for results")
    expected_announcement: str = Field(..., description="Expected announcement date (ISO 8601)")
    betting_closes_hours_before: int = Field(default=48, description="Hours before announcement to close betting")

class MarketResponse(BaseModel):
    """Response for market queries"""
    market_id: str
    hackathon_name: str
    status: str  # "active", "betting_closed", "resolved"
    teams: list[str]
    volume_usd: float
    odds: dict[str, float]  # team_name -> odds
    resolution_status: Optional[str] = None
    winner: Optional[str] = None
    fee_paid: bool

class RegisterWebhookRequest(BaseModel):
    """Request to register a webhook"""
    platform_id: str
    url: str = Field(..., description="Webhook URL to receive notifications")
    event_types: list[str] = Field(
        default=["all"],
        description="Event types to receive: market_created, market_resolved, betting_closed, winner_detected, all"
    )

class WebhookResponse(BaseModel):
    """Response for webhook registration"""
    webhook_id: int
    platform_id: str
    url: str
    event_types: list[str]
    message: str

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
def read_root():
    """Health check"""
    return {
        "status": "healthy",
        "service": "Hackathon Oracle API",
        "version": "1.0.0",
        "fee_percentage": f"{fee_calculator.fee_percentage}%",
        "fee_wallet": fee_calculator.fee_wallet_address
    }

@app.post("/api/v1/markets", response_model=dict)
async def create_market_endpoint(request: CreateMarketRequest):
    """Create a new hackathon prediction market"""
    logger.info(f"Creating market: {request.market_id} for hackathon: {request.hackathon_name}")
    
    # Generate internal ID
    internal_id = str(uuid4())
    
    # Create market data
    market_data = {
        "internal_id": internal_id,
        "platform_id": request.platform_id,
        "market_id": request.market_id,
        "hackathon_name": request.hackathon_name,
        "teams": request.teams,
        "data_sources": request.data_sources.model_dump(),
        "expected_announcement": request.expected_announcement,
        "betting_closes": request.expected_announcement,
        "status": "active",
        "volume_usd": 0.0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "fee_paid": False
    }
    
    # Store in database
    db_success = create_market(market_data)
    
    if not db_success:
        raise HTTPException(status_code=400, detail="Market already exists")
    
    # Update in-memory cache
    active_markets[request.market_id] = market_data
    
    # Start monitoring (background task)
    asyncio.create_task(oracle.start_monitoring(
        market_id=request.market_id,
        hackathon_name=request.hackathon_name,
        data_sources=request.data_sources.model_dump(),
        expected_announcement=request.expected_announcement
    ))
    
    # Send webhook notification
    await notifier.notify_market_created(market_data)
    
    logger.info(f"Market {request.market_id} created. Monitoring started.")
    
    return {
        "status": "success",
        "market_id": request.market_id,
        "internal_id": internal_id,
        "message": "Market created. Monitoring started."
    }

@app.get("/api/v1/markets", response_model=list)
def list_markets():
    """List all markets"""
    markets = get_all_markets()
    return markets

@app.get("/api/v1/markets/{market_id}", response_model=MarketResponse)
def get_market_endpoint(market_id: str):
    """Get market status and odds"""
    market = get_market(market_id)
    
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    
    # Parse teams from comma-separated string
    teams = market["teams"].split(",") if market["teams"] else []
    
    # Calculate odds based on volume (placeholder)
    odds = {team: 1.0 for team in teams}
    
    return MarketResponse(
        market_id=market_id,
        hackathon_name=market["hackathon_name"],
        status=market["status"],
        teams=teams,
        volume_usd=market["volume_usd"],
        odds=odds,
        resolution_status=market.get("resolution_status"),
        winner=market.get("winner"),
        fee_paid=bool(market["fee_paid"])
    )

@app.post("/api/v1/markets/{market_id}/close-betting")
async def close_betting(market_id: str):
    """Close betting for a market"""
    market = get_market(market_id)
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    
    success = db_close_market_betting(market_id)
    
    if success:
        # Update cache
        if market_id in active_markets:
            active_markets[market_id]["status"] = "betting_closed"
        
        # Send webhook
        await notifier.notify_betting_closed(market)
        logger.info(f"Betting closed for market: {market_id}")
        
        return {
            "status": "success",
            "market_id": market_id,
            "message": "Betting closed"
        }
    
    raise HTTPException(status_code=500, detail="Failed to close betting")

@app.post("/api/v1/markets/{market_id}/resolve")
async def resolve_market_endpoint(market_id: str, winner: str):
    """Resolve a market with the winning team"""
    market = get_market(market_id)
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    
    teams = market["teams"].split(",") if market["teams"] else []
    
    if winner not in teams:
        raise HTTPException(status_code=400, detail="Winner must be a valid team name")
    
    # Calculate and collect fee
    fee_amount = fee_calculator.calculate_fee(market["volume_usd"])
    
    # Record fee
    fee_record = {
        "market_id": market_id,
        "platform_id": market["platform_id"],
        "volume_usd": market["volume_usd"],
        "fee_percentage": fee_calculator.fee_percentage,
        "fee_amount_usd": fee_amount,
        "fee_wallet": fee_calculator.fee_wallet_address
    }
    record_fee(fee_record)
    
    # Update market
    db_resolve_market(market_id, winner, "success")
    
    # Update cache
    if market_id in active_markets:
        active_markets[market_id]["status"] = "resolved"
        active_markets[market_id]["winner"] = winner
        active_markets[market_id]["fee_paid"] = True
    
    # Send webhook
    market["winner"] = winner
    await notifier.notify_market_resolved(market, winner, fee_amount)
    
    logger.info(f"Market {market_id} resolved. Winner: {winner}. Fee: ${fee_amount}")
    
    return {
        "status": "success",
        "market_id": market_id,
        "winner": winner,
        "fee_collected_usd": fee_amount,
        "fee_wallet": fee_calculator.fee_wallet_address
    }

@app.get("/api/v1/fees")
def get_fee_history_endpoint():
    """Get fee collection history"""
    history = get_fee_history()
    total = sum(r["fee_amount_usd"] for r in history)
    
    return {
        "total_fees_collected_usd": total,
        "fee_wallet": fee_calculator.fee_wallet_address,
        "history": history
    }

@app.post("/api/v1/markets/{market_id}/volume")
def update_volume(market_id: str, volume_usd: float):
    """Update trading volume for a market"""
    market = get_market(market_id)
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    
    update_market_volume(market_id, volume_usd)
    
    # Update cache
    if market_id in active_markets:
        active_markets[market_id]["volume_usd"] = volume_usd
    
    return {
        "status": "success",
        "market_id": market_id,
        "volume_usd": volume_usd,
        "fee_at_resolution": fee_calculator.calculate_fee(volume_usd)
    }

# ============================================================================
# WEBHOOK ENDPOINTS
# ============================================================================

@app.post("/api/v1/webhooks", response_model=WebhookResponse)
def register_webhook_endpoint(request: RegisterWebhookRequest):
    """Register a webhook for event notifications"""
    webhook_id = register_webhook(
        platform_id=request.platform_id,
        url=request.url,
        event_types=request.event_types
    )
    
    return WebhookResponse(
        webhook_id=webhook_id,
        platform_id=request.platform_id,
        url=request.url,
        event_types=request.event_types,
        message="Webhook registered successfully"
    )

@app.get("/api/v1/webhooks")
def list_webhooks(platform_id: str = None):
    """List registered webhooks"""
    webhooks = get_webhooks(platform_id)
    
    # Parse event_types from comma-separated string
    for webhook in webhooks:
        webhook["event_types"] = webhook.get("event_types", "").split(",")
    
    return webhooks

# ============================================================================
# SCRAPING ENDPOINTS (for testing/manual triggers)
# ============================================================================

@app.post("/api/v1/scrape/{market_id}")
async def scrape_market_website(market_id: str):
    """Manually trigger website scrape for a market"""
    market = get_market(market_id)
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    
    data_sources = eval(market["data_sources"]) if isinstance(market["data_sources"], str) else market["data_sources"]
    teams = market["teams"].split(",") if market["teams"] else []
    
    results = []
    
    # Scrape website if provided
    if data_sources.get("website"):
        result = await website_scraper.scrape(
            url=data_sources["website"],
            teams=teams
        )
        results.append(result)
        
        if result["winners_found"]:
            await notifier.notify_winner_detected(
                market, 
                result["winners_found"][0],
                result["confidence"],
                "website"
            )
    
    return {
        "market_id": market_id,
        "scrape_results": results
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)