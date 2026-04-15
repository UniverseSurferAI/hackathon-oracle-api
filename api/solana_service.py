"""
Solana Service - Handles USDC transfers on Solana blockchain

Note: This service handles the oracle's backend wallet that signs withdrawal transactions.
The oracle doesn't hold private keys of users - it only controls its own fee wallet.
"""
from typing import Optional
from loguru import logger
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.system_program import TransferParams, transfer
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
import os

class SolanaService:
    """
    Service for handling USDC transfers on Solana
    """
    
    # USDC on Solana mainnet
    USDC_MINT = Pubkey.from_string("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDj1v")
    
    def __init__(self, rpc_url: str, fee_wallet_private_key: str):
        """
        Initialize Solana service
        
        Args:
            rpc_url: Solana RPC endpoint (e.g., Helius)
            fee_wallet_private_key: Oracle's fee wallet private key (base58)
        """
        self.rpc_url = rpc_url
        self.client = Client(rpc_url)
        
        # Load oracle's fee wallet keypair
        try:
            keypair = Keypair.from_base58_string(fee_wallet_private_key)
            self.fee_wallet = keypair
            logger.info(f"SolanaService initialized with fee wallet: {keypair.pubkey()}")
        except Exception as e:
            logger.warning(f"Could not load fee wallet keypair: {e}")
            self.fee_wallet = None
    
    def get_native_balance(self, wallet_address: str) -> float:
        """
        Get SOL balance for a wallet
        
        Args:
            wallet_address: Solana wallet address
            
        Returns:
            SOL balance (float)
        """
        try:
            pubkey = Pubkey.from_string(wallet_address)
            response = self.client.get_balance(pubkey)
            
            if response.value:
                # Convert lamports to SOL (1 SOL = 1,000,000,000 lamports)
                return float(response.value) / 1_000_000_000
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error getting SOL balance: {e}")
            return 0.0
    
    def get_usdc_balance(self, wallet_address: str) -> float:
        """
        Get USDC balance for a wallet
        
        Args:
            wallet_address: Solana wallet address
            
        Returns:
            USDC balance (float)
        """
        try:
            pubkey = Pubkey.from_string(wallet_address)
            
            # Get token accounts for USDC mint
            response = self.client.get_token_accounts_by_owner_json_parsed(
                pubkey,
                {"mint": self.USDC_MINT}
            )
            
            if not response.value:
                return 0.0
            
            # Parse balance from first USDC account
            token_account = response.value[0]
            balance = float(token_account.account.data.parsed['info']['tokenAmount']['uiAmount'])
            
            return balance
            
        except Exception as e:
            logger.error(f"Error getting USDC balance: {e}")
            return 0.0
    
    def get_token_account(self, wallet_address: str, mint: Pubkey) -> Optional[Pubkey]:
        """
        Get the token account pubkey for a wallet and mint
        
        Args:
            wallet_address: Solana wallet address
            mint: Token mint address
            
        Returns:
            Token account pubkey or None
        """
        try:
            pubkey = Pubkey.from_string(wallet_address)
            
            response = self.client.get_token_accounts_by_owner(
                pubkey,
                {"mint": mint}
            )
            
            if response.value:
                return response.value[0].pubkey
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting token account: {e}")
            return None
    
    def transfer_usdc(self, to_wallet: str, amount: float) -> dict:
        """
        Transfer USDC from oracle's wallet to destination
        
        Args:
            to_wallet: Destination wallet address
            amount: Amount of USDC to transfer
            
        Returns:
            Transaction result dict
        """
        if not self.fee_wallet:
            return {
                "success": False,
                "error": "Fee wallet not configured"
            }
        
        try:
            # Get source (oracle) token account
            source_account = self.get_token_account(
                str(self.fee_wallet.pubkey()),
                self.USDC_MINT
            )
            
            if not source_account:
                return {
                    "success": False,
                    "error": "Oracle wallet has no USDC token account"
                }
            
            # Get destination token account
            dest_account = self.get_token_account(to_wallet, self.USDC_MINT)
            
            if not dest_account:
                return {
                    "success": False,
                    "error": f"Destination wallet {to_wallet} has no USDC token account. Platform must initialize USDC account first."
                }
            
            # Convert to token units (USDC has 6 decimals)
            amount_units = int(amount * 1_000_000)
            
            # Build transfer instruction using spl-token
            from spl.token.instructions import TransferParams as SPLTransferParams, transfer as spl_transfer
            
            transfer_params = SPLTransferParams(
                source=source_account,
                mint=self.USDC_MINT,
                dest=dest_account,
                owner=self.fee_wallet.pubkey(),
                amount=amount_units
            )
            
            transfer_ix = spl_transfer(transfer_params)
            
            # Get recent blockhash
            recent_blockhash = self.client.get_latest_blockhash()
            
            # Create transaction
            from solders.transaction import Transaction
            tx = Transaction()
            tx.add(transfer_ix)
            tx.recent_blockhash = recent_blockhash.value.blockhash
            
            # Send and confirm transaction
            result = self.client.send_transaction(
                tx,
                self.fee_wallet,
                opts=TxOpts(skip_preflight=False, skip_confirmation=False)
            )
            
            logger.info(f"USDC transfer successful: {amount} USDC to {to_wallet}")
            logger.info(f"Transaction signature: {result.value}")
            
            return {
                "success": True,
                "tx_signature": str(result.value),
                "amount": amount,
                "to_wallet": to_wallet
            }
            
        except Exception as e:
            logger.error(f"USDC transfer failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def verify_transaction(self, tx_signature: str) -> dict:
        """
        Verify a transaction was confirmed on-chain
        
        Args:
            tx_signature: Transaction signature
            
        Returns:
            Transaction status dict
        """
        try:
            from solders.signature import Signature
            sig = Signature.from_string(tx_signature)
            response = self.client.get_transaction(sig)
            
            if response.value:
                return {
                    "confirmed": True,
                    "slot": response.value.slot,
                    "status": "success"
                }
            else:
                return {
                    "confirmed": False,
                    "status": "not found or pending"
                }
                
        except Exception as e:
            return {
                "confirmed": False,
                "error": str(e)
            }


# Singleton instance
_solana_service: Optional[SolanaService] = None

def init_solana_service(rpc_url: str, fee_wallet_private_key: str) -> SolanaService:
    """Initialize the Solana service singleton"""
    global _solana_service
    _solana_service = SolanaService(rpc_url, fee_wallet_private_key)
    return _solana_service

def get_solana_service() -> Optional[SolanaService]:
    """Get the Solana service instance"""
    return _solana_service
