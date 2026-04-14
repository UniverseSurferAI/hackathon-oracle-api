"""
Fee Calculator - Handles 2% fee calculation and collection
"""
from loguru import logger

class FeeCalculator:
    """Calculates and tracks fees for market resolutions"""
    
    def __init__(self, fee_percentage: float, fee_wallet_address: str):
        self.fee_percentage = fee_percentage
        self.fee_wallet_address = fee_wallet_address
        logger.info(f"FeeCalculator initialized: {fee_percentage}% fee to {fee_wallet_address}")
    
    def calculate_fee(self, volume_usd: float) -> float:
        """
        Calculate fee amount based on trading volume
        
        Args:
            volume_usd: Total trading volume in USD
            
        Returns:
            Fee amount in USD
        """
        fee = volume_usd * (self.fee_percentage / 100)
        logger.debug(f"Fee calculation: ${volume_usd} * {self.fee_percentage}% = ${fee}")
        return round(fee, 2)
    
    def get_fee_breakdown(self, volume_usd: float) -> dict:
        """
        Get detailed breakdown of fee calculation
        
        Args:
            volume_usd: Total trading volume in USD
            
        Returns:
            Dictionary with fee breakdown
        """
        fee_amount = self.calculate_fee(volume_usd)
        return {
            "volume_usd": volume_usd,
            "fee_percentage": self.fee_percentage,
            "fee_amount_usd": fee_amount,
            "fee_wallet_address": self.fee_wallet_address,
            "network": "Ethereum",
            "token": "USDC"
        }