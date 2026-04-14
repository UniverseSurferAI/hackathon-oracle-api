"""
Hackathon Resolution Oracle - Monitors data sources for winner announcements
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional
from loguru import logger

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
        
        # Store monitor info
        self.active_monitors[market_id] = {
            "hackathon_name": hackathon_name,
            "data_sources": data_sources,
            "expected_announcement": expected_announcement,
            "started_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Start background monitoring task
        asyncio.create_task(self._monitor_loop(market_id, data_sources))
    
    async def _monitor_loop(self, market_id: str, data_sources: dict):
        """
        Background loop that monitors all data sources
        
        In production, this would:
        - Poll Twitter API for new tweets from hackathon accounts
        - Check website for result announcements
        - Monitor Discord for winner posts
        """
        check_interval = 300  # Check every 5 minutes (300 seconds)
        
        logger.info(f"Monitor loop started for {market_id}")
        
        while market_id in self.active_monitors:
            try:
                # In production, implement actual monitoring here:
                # 
                # 1. Twitter monitoring
                # if data_sources.get("twitter"):
                #     tweets = await self._check_twitter(data_sources["twitter"])
                #     for tweet in tweets:
                #         if self._contains_winner_keyword(tweet):
                #             winner = self._extract_winner(tweet)
                #             await self._resolve_market(market_id, winner)
                #
                # 2. Website monitoring
                # if data_sources.get("website"):
                #     content = await self._check_website(data_sources["website"])
                #     if self._contains_winner(content):
                #         winner = self._extract_winner_from_html(content)
                #         await self._resolve_market(market_id, winner)
                #
                # 3. Discord monitoring
                # if data_sources.get("discord"):
                #     messages = await self._check_discord(data_sources["discord"])
                #     for msg in messages:
                #         if self._contains_winner(msg):
                #             winner = self._extract_winner(msg)
                #             await self._resolve_market(market_id, winner)
                
                logger.debug(f"Monitoring check for {market_id} - no winner detected yet")
                
            except Exception as e:
                logger.error(f"Error in monitor loop for {market_id}: {e}")
            
            await asyncio.sleep(check_interval)
    
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
    
    async def _check_twitter(self, twitter_handle: str) -> list:
        """
        Check Twitter for new posts from hackathon account
        
        In production:
        - Use Twitter API v2
        - Filter for posts after monitoring start time
        - Look for keywords related to winners
        """
        # Placeholder - would use httpx to call Twitter API
        logger.debug(f"Would check Twitter for: {twitter_handle}")
        return []
    
    async def _check_website(self, website_url: str) -> str:
        """
        Check website for winner announcement
        
        In production:
        - Fetch page content
        - Parse HTML for winner information
        """
        logger.debug(f"Would check website: {website_url}")
        return ""
    
    async def _check_discord(self, discord_channel: str) -> list:
        """
        Check Discord channel for winner announcement
        
        In production:
        - Use Discord bot API
        - Monitor specific channel
        """
        logger.debug(f"Would check Discord: {discord_channel}")
        return []