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

# Initialize fee calculator (2% on volume)
fee_calculator = FeeCalculator(
    fee_percentage=2.0,
    fee_wallet_address="0x7252c6477139989916F5c41b969208C5B947AC1d"
)

# Initialize oracle
oracle = HackathonOracle(fee_calculator)

# In-memory storage (use database in production)
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

class ResolveRequest(BaseModel):
    """Request to manually resolve a market (admin only)"""
    market_id: str
    winner: str

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
def create_market(request: CreateMarketRequest):
    """Create a new hackathon prediction market"""
    logger.info(f"Creating market: {request.market_id} for hackathon: {request.hackathon_name}")
    
    # Generate internal ID
    internal_id = str(uuid4())
    
    # Calculate betting close time
    betting_closes = request.expected_announcement
    
    # Create market data
    market_data = {
        "internal_id": internal_id,
        "platform_id": request.platform_id,
        "market_id": request.market_id,
        "hackathon_name": request.hackathon_name,
        "teams": request.teams,
        "data_sources": request.data_sources.model_dump(),
        "expected_announcement": request.expected_announcement,
        "betting_closes": betting_closes,
        "status": "active",
        "volume_usd": 0.0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "fee_paid": False
    }
    
    # Store in memory
    active_markets[request.market_id] = market_data
    
    # Start monitoring (background task)
    asyncio.create_task(oracle.start_monitoring(
        market_id=request.market_id,
        hackathon_name=request.hackathon_name,
        data_sources=request.data_sources.model_dump(),
        expected_announcement=request.expected_announcement
    ))
    
    logger.info(f"Market {request.market_id} created. Monitoring started.")
    
    return {
        "status": "success",
        "market_id": request.market_id,
        "internal_id": internal_id,
        "message": "Market created. Monitoring started."
    }

@app.get("/api/v1/markets/{market_id}", response_model=MarketResponse)
def get_market(market_id: str):
    """Get market status and odds"""
    if market_id not in active_markets:
        raise HTTPException(status_code=404, detail="Market not found")
    
    market = active_markets[market_id]
    
    # Calculate odds based on volume (placeholder - real implementation would use actual bets)
    odds = {team: 1.0 for team in market["teams"]}
    
    return MarketResponse(
        market_id=market_id,
        hackathon_name=market["hackathon_name"],
        status=market["status"],
        teams=market["teams"],
        volume_usd=market["volume_usd"],
        odds=odds,
        resolution_status=market.get("resolution_status"),
        winner=market.get("winner"),
        fee_paid=market["fee_paid"]
    )

@app.post("/api/v1/markets/{market_id}/close-betting")
def close_betting(market_id: str):
    """Close betting for a market"""
    if market_id not in active_markets:
        raise HTTPException(status_code=404, detail="Market not found")
    
    active_markets[market_id]["status"] = "betting_closed"
    logger.info(f"Betting closed for market: {market_id}")
    
    return {
        "status": "success",
        "market_id": market_id,
        "message": "Betting closed"
    }

@app.post("/api/v1/markets/{market_id}/resolve")
def resolve_market(market_id: str, winner: str, background_tasks: BackgroundTasks):
    """Resolve a market with the winning team"""
    if market_id not in active_markets:
        raise HTTPException(status_code=404, detail="Market not found")
    
    market = active_markets[market_id]
    
    if winner not in market["teams"]:
        raise HTTPException(status_code=400, detail="Winner must be a valid team name")
    
    # Calculate and collect fee
    fee_amount = fee_calculator.calculate_fee(market["volume_usd"])
    
    # Record fee payment
    fee_record = {
        "market_id": market_id,
        "platform_id": market["platform_id"],
        "volume_usd": market["volume_usd"],
        "fee_percentage": fee_calculator.fee_percentage,
        "fee_amount_usd": fee_amount,
        "fee_wallet": fee_calculator.fee_wallet_address,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    fee_history.append(fee_record)
    
    # Update market
    active_markets[market_id]["status"] = "resolved"
    active_markets[market_id]["winner"] = winner
    active_markets[market_id]["resolution_status"] = "success"
    active_markets[market_id]["fee_paid"] = True
    active_markets[market_id]["fee_amount"] = fee_amount
    
    logger.info(f"Market {market_id} resolved. Winner: {winner}. Fee: ${fee_amount}")
    
    return {
        "status": "success",
        "market_id": market_id,
        "winner": winner,
        "fee_collected_usd": fee_amount,
        "fee_wallet": fee_calculator.fee_wallet_address
    }

@app.get("/api/v1/fees")
def get_fee_history():
    """Get fee collection history"""
    return {
        "total_fees_collected": sum(r["fee_amount_usd"] for r in fee_history),
        "fee_wallet": fee_calculator.fee_wallet_address,
        "history": fee_history
    }

@app.post("/api/v1/markets/{market_id}/volume")
def update_volume(market_id: str, volume_usd: float):
    """Update trading volume for a market (called by platform when trades happen)"""
    if market_id not in active_markets:
        raise HTTPException(status_code=404, detail="Market not found")
    
    active_markets[market_id]["volume_usd"] = volume_usd
    
    return {
        "status": "success",
        "market_id": market_id,
        "volume_usd": volume_usd,
        "fee_at_resolution": fee_calculator.calculate_fee(volume_usd)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)