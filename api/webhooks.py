"""
Webhook notifications for Hackathon Oracle API
Sends notifications to platforms when events occur
"""
import asyncio
import httpx
import json
from datetime import datetime
from typing import Optional
from loguru import logger

from api.database import get_webhooks

class WebhookNotifier:
    """Handles webhook notifications to platforms"""
    
    def __init__(self):
        self.timeout = 30  # seconds
        self.max_retries = 3
        self.retry_delay = 5  # seconds
    
    async def notify(self, event_type: str, payload: dict) -> dict:
        """
        Send webhook notification to all registered platforms
        
        Args:
            event_type: Type of event (market_created, market_resolved, etc.)
            payload: Event payload data
        
        Returns:
            Dict with success/failure counts
        """
        # Get all webhooks for this event type
        webhooks = get_webhooks()
        
        if not webhooks:
            logger.info(f"No webhooks registered for event: {event_type}")
            return {"sent": 0, "failed": 0}
        
        # Build event payload
        event = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": payload
        }
        
        # Send to all webhooks concurrently
        tasks = []
        for webhook in webhooks:
            if self._matches_event(webhook, event_type):
                tasks.append(self._send_webhook(webhook, event))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success = sum(1 for r in results if r is True)
        failed = len(results) - success
        
        logger.info(f"Webhook notification sent: {success} success, {failed} failed")
        
        return {"sent": success, "failed": failed}
    
    def _matches_event(self, webhook: dict, event_type: str) -> bool:
        """Check if webhook is registered for this event type"""
        event_types = webhook.get("event_types", "").split(",")
        return event_type in event_types or "all" in event_types
    
    async def _send_webhook(self, webhook: dict, event: dict, retry: int = 0) -> bool:
        """
        Send webhook to a single URL with retry logic
        """
        url = webhook["url"]
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        url,
                        json=event,
                        headers={
                            "Content-Type": "application/json",
                            "X-Hackathon-Oracle-Event": event["event"],
                            "X-Hackathon-Oracle-Timestamp": event["timestamp"]
                        }
                    )
                    
                    if response.status_code in [200, 201, 202, 204]:
                        logger.info(f"Webhook sent successfully to {url}")
                        return True
                    else:
                        logger.warning(
                            f"Webhook failed for {url}: {response.status_code} - {response.text[:200]}"
                        )
                        
            except httpx.TimeoutException:
                logger.warning(f"Webhook timeout for {url} (attempt {attempt + 1}/{self.max_retries})")
            except httpx.RequestError as e:
                logger.warning(f"Webhook error for {url}: {str(e)} (attempt {attempt + 1}/{self.max_retries})")
            
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay)
        
        logger.error(f"Webhook failed after {self.max_retries} attempts: {url}")
        return False
    
    async def notify_market_created(self, market_data: dict):
        """Notify when a new market is created"""
        payload = {
            "market_id": market_data["market_id"],
            "hackathon_name": market_data["hackathon_name"],
            "teams": market_data["teams"],
            "expected_announcement": market_data["expected_announcement"],
            "status": "active"
        }
        return await self.notify("market_created", payload)
    
    async def notify_market_resolved(self, market_data: dict, winner: str, fee_amount: float):
        """Notify when a market is resolved"""
        payload = {
            "market_id": market_data["market_id"],
            "hackathon_name": market_data["hackathon_name"],
            "winner": winner,
            "fee_collected_usd": fee_amount,
            "status": "resolved"
        }
        return await self.notify("market_resolved", payload)
    
    async def notify_betting_closed(self, market_data: dict):
        """Notify when betting is closed"""
        payload = {
            "market_id": market_data["market_id"],
            "hackathon_name": market_data["hackathon_name"],
            "final_volume_usd": market_data["volume_usd"],
            "status": "betting_closed"
        }
        return await self.notify("betting_closed", payload)
    
    async def notify_winner_detected(self, market_data: dict, winner: str, confidence: float, source: str):
        """Notify when a potential winner is detected"""
        payload = {
            "market_id": market_data["market_id"],
            "hackathon_name": market_data["hackathon_name"],
            "detected_winner": winner,
            "confidence": confidence,
            "source": source,
            "status": "winner_detected"
        }
        return await self.notify("winner_detected", payload)

# Global notifier instance
notifier = WebhookNotifier()