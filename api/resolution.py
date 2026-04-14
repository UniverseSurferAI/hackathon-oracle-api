"""
Hackathon Resolution Oracle - Monitors data sources for winner announcements
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional
from loguru import logger

from api.database import get_market, resolve_market as db_resolve_market, save_scraping_result
from api.webhooks import notifier
from api.scraping import website_scraper, twitter_scraper, discord_scraper

class HackathonOracle:
    """Monitors hackathon data sources and detects winner announcements"""
    
    def __init__(self, fee_calculator):
        self.fee_calculator = fee_calculator
        self.active_monitors = {}
        logger.info("HackathonOracle initialized")
    
    async def start_monitoring(
        self,
        market_id: str,
        hackathon_name: str,
        data_sources: dict,
        expected_announcement: str
    ):
        """
        Start monitoring data sources for winner announcement
        
        Args:
            market_id: Market to monitor
            hackathon_name: Name of the hackathon
            data_sources: Dict with twitter, website, discord sources
            expected_announcement: ISO date string for expected announcement
        """
        logger.info(f"Starting monitoring for market: {market_id}")
        logger.info(f"  Hackathon: {hackathon_name}")
        logger.info(f"  Data sources: {data_sources}")
        logger.info(f"  Expected announcement: {expected_announcement}")
        
        # Get market data
        market = get_market(market_id)
        if not market:
            logger.error(f"Market not found: {market_id}")
            return
        
        # Store monitor info
        self.active_monitors[market_id] = {
            "hackathon_name": hackathon_name,
            "data_sources": data_sources,
            "expected_announcement": expected_announcement,
            "teams": market["teams"].split(",") if market["teams"] else [],
            "started_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Start background monitoring task
        asyncio.create_task(self._monitor_loop(market_id, data_sources, market))
    
    async def _monitor_loop(self, market_id: str, data_sources: dict, market: dict):
        """
        Background loop that monitors all data sources
        """
        check_interval = 3600  # Check every hour (3600 seconds)
        max_checks = 168  # Monitor for up to 7 days
        checks_done = 0
        
        teams = market["teams"].split(",") if market["teams"] else []
        
        logger.info(f"Monitor loop started for {market_id}")
        
        while market_id in self.active_monitors and checks_done < max_checks:
            try:
                winner_found = False
                
                # 1. Website monitoring
                if data_sources.get("website"):
                    logger.info(f"Checking website for {market_id}")
                    result = await website_scraper.scrape(
                        url=data_sources["website"],
                        teams=teams
                    )
                    
                    # Save scraping result
                    save_scraping_result({
                        "market_id": market_id,
                        "source_type": "website",
                        "source_url": data_sources["website"],
                        "content": result.get("content", "")[:5000],
                        "winner_detected": ",".join(result["winners_found"]) if result["winners_found"] else None,
                        "confidence": result.get("confidence", 0.0)
                    })
                    
                    if result["winners_found"] and result["confidence"] >= 0.5:
                        winner = result["winners_found"][0]
                        logger.info(f"Winner detected for {market_id}: {winner} (confidence: {result['confidence']})")
                        
                        # Notify via webhook
                        await notifier.notify_winner_detected(
                            market, winner, result["confidence"], "website"
                        )
                        
                        # Auto-resolve if high confidence
                        if result["confidence"] >= 0.8:
                            await self._resolve_market(market_id, winner)
                            winner_found = True
                
                # 2. Twitter monitoring
                if data_sources.get("twitter") and not winner_found:
                    logger.info(f"Checking Twitter for {market_id}")
                    result = await twitter_scraper.check_tweet(
                        handle=data_sources["twitter"],
                        teams=teams
                    )
                    
                    if result.get("winners_found"):
                        winner = result["winners_found"][0]
                        logger.info(f"Winner detected on Twitter for {market_id}: {winner}")
                        
                        await notifier.notify_winner_detected(
                            market, winner, 0.7, "twitter"
                        )
                
                # 3. Discord monitoring
                if data_sources.get("discord") and not winner_found:
                    logger.info(f"Checking Discord for {market_id}")
                    result = await discord_scraper.check_channel(
                        channel_id=data_sources["discord"],
                        teams=teams
                    )
                    
                    if result.get("winners_found"):
                        winner = result["winners_found"][0]
                        logger.info(f"Winner detected on Discord for {market_id}: {winner}")
                        
                        await notifier.notify_winner_detected(
                            market, winner, 0.7, "discord"
                        )
                
            except Exception as e:
                logger.error(f"Error in monitor loop for {market_id}: {e}")
            
            checks_done += 1
            
            if not winner_found:
                await asyncio.sleep(check_interval)
    
    async def _resolve_market(self, market_id: str, winner: str):
        """Resolve a market with the winning team"""
        from api.main import fee_calculator
        
        market = get_market(market_id)
        if not market:
            logger.error(f"Cannot resolve - market not found: {market_id}")
            return
        
        # Calculate fee
        fee_amount = fee_calculator.calculate_fee(market["volume_usd"])
        
        # Update database
        db_resolve_market(market_id, winner, "auto_detected")
        
        # Update active monitors
        if market_id in self.active_monitors:
            del self.active_monitors[market_id]
        
        # Send webhook notification
        market["winner"] = winner
        await notifier.notify_market_resolved(market, winner, fee_amount)
        
        logger.info(f"Market {market_id} AUTO-RESOLVED. Winner: {winner}. Fee: ${fee_amount}")
    
    def stop_monitoring(self, market_id: str):
        """Stop monitoring a market"""
        if market_id in self.active_monitors:
            del self.active_monitors[market_id]
            logger.info(f"Stopped monitoring for market: {market_id}")
    
    def _contains_winner_keyword(self, text: str) -> bool:
        """Check if text contains winner announcement keywords"""
        keywords = [
            "winner", "winners", "won", 
            "congratulations", "congrats",
            "results", "announced",
            "first place", "grand prize"
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in keywords)