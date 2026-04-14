"""
Website scraping module for Hackathon Oracle API
Monitors websites for hackathon winner announcements
"""
import asyncio
import re
from typing import Optional, Callable
from urllib.parse import urlparse
import httpx
from loguru import logger

class WebsiteScraper:
    """Scrapes websites for hackathon results"""
    
    def __init__(self):
        self.timeout = 30
        self.user_agent = "Hackathon-Oracle-API/1.0 (Prediction Market Oracle)"
        
        # Common patterns for winner announcements
        self.winner_patterns = [
            r"(?i)(winner|winning|team|1st|first place|grand prize|champion)",
            r"(?i)(announced|revealed|result|decided|selected)",
            r"(?i)(hackathon|challenge|competition|contest)",
        ]
        
        # Teams to look for (will be injected)
        self.teams = []
    
    async def scrape(self, url: str, teams: list[str], callback: Optional[Callable] = None) -> dict:
        """
        Scrape a website for hackathon results
        
        Args:
            url: Website URL to scrape
            teams: List of team names to look for
            callback: Optional callback when results are found
        
        Returns:
            Dict with scrape results
        """
        self.teams = teams
        result = {
            "url": url,
            "teams": teams,
            "success": False,
            "content": "",
            "winners_found": [],
            "confidence": 0.0,
            "error": None
        }
        
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent},
                follow_redirects=True
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                content = response.text
                result["content"] = content[:10000]  # Limit content stored
                result["success"] = True
                
                # Search for winners
                winners = self._find_winners(content)
                result["winners_found"] = winners
                
                if winners:
                    result["confidence"] = self._calculate_confidence(winners, content)
                
                logger.info(f"Scraped {url}: found {len(winners)} potential winners")
                
                if callback and winners:
                    await callback(winners, result["confidence"])
                
        except httpx.TimeoutException:
            result["error"] = "Timeout while scraping"
            logger.warning(f"Timeout scraping {url}")
        except httpx.RequestError as e:
            result["error"] = f"Request error: {str(e)}"
            logger.warning(f"Error scraping {url}: {e}")
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"
            logger.error(f"Error scraping {url}: {e}")
        
        return result
    
    def _find_winners(self, content: str) -> list[str]:
        """Find winner mentions in content"""
        found_winners = []
        content_lower = content.lower()
        
        for team in self.teams:
            team_lower = team.lower()
            
            # Check if team name appears near winner-related keywords
            for pattern in self.winner_patterns:
                matches = re.finditer(pattern, content_lower)
                for match in matches:
                    start = max(0, match.start() - 100)
                    end = min(len(content_lower), match.end() + 100)
                    context = content_lower[start:end]
                    
                    if team_lower in context:
                        if team not in found_winners:
                            found_winners.append(team)
                            logger.info(f"Found winner mention: {team}")
                        break
        
        return found_winners
    
    def _calculate_confidence(self, winners: list[str], content: str) -> float:
        """Calculate confidence score for winner detection"""
        if not winners:
            return 0.0
        
        confidence = 0.0
        content_lower = content.lower()
        
        # Higher confidence for explicit announcements
        explicit_phrases = [
            "winner is", "winners are", "first place goes to",
            "grand prize goes to", "champion is", "proudly announces"
        ]
        
        for winner in winners:
            winner_lower = winner.lower()
            for phrase in explicit_phrases:
                if phrase in content_lower and winner_lower in content_lower:
                    confidence += 0.3
                    break
        
        # Normalize to 0-1 range
        confidence = min(1.0, confidence / len(winners))
        
        return round(confidence, 2)
    
    async def monitor(
        self,
        url: str,
        teams: list[str],
        interval_minutes: int = 60,
        max_checks: int = 24,
        callback: Optional[Callable] = None
    ):
        """
        Continuously monitor a website for changes
        
        Args:
            url: Website URL to monitor
            teams: List of team names to look for
            interval_minutes: Minutes between checks
            max_checks: Maximum number of checks (0 = infinite)
            callback: Optional callback when winners are found
        """
        checks = 0
        
        while max_checks == 0 or checks < max_checks:
            logger.info(f"Checking {url} (check {checks + 1})")
            
            result = await self.scrape(url, teams)
            
            if result["winners_found"] and callback:
                await callback(result["winners_found"], result["confidence"], url)
                break  # Stop monitoring once winner is found
            
            checks += 1
            
            if checks < max_checks or max_checks == 0:
                await asyncio.sleep(interval_minutes * 60)


class TwitterScraper:
    """Scrapes Twitter/X for hackathon results"""
    
    def __init__(self):
        self.timeout = 30
        
    async def check_tweet(self, handle: str, teams: list[str], callback: Optional[Callable] = None) -> dict:
        """
        Check a Twitter handle for hackathon announcements
        
        Note: Requires Twitter API v2 for production use.
        This is a placeholder implementation.
        """
        result = {
            "handle": handle,
            "teams": teams,
            "success": False,
            "tweets_found": [],
            "winners_found": [],
            "error": None
        }
        
        # This would need Twitter API credentials
        # For now, return placeholder
        logger.warning(f"Twitter scraping requires API credentials for {handle}")
        result["error"] = "Twitter API credentials required"
        
        return result


class DiscordScraper:
    """Monitors Discord for hackathon results"""
    
    def __init__(self):
        self.webhook_url = None
        
    async def check_channel(self, channel_id: str, teams: list[str], callback: Optional[Callable] = None) -> dict:
        """
        Check a Discord channel for announcements
        
        Note: Requires Discord bot token for production use.
        This is a placeholder implementation.
        """
        result = {
            "channel_id": channel_id,
            "teams": teams,
            "success": False,
            "messages_found": [],
            "winners_found": [],
            "error": None
        }
        
        # This would need Discord bot token
        logger.warning(f"Discord scraping requires bot token for channel {channel_id}")
        result["error"] = "Discord bot token required"
        
        return result


# Global scraper instances
website_scraper = WebsiteScraper()
twitter_scraper = TwitterScraper()
discord_scraper = DiscordScraper()