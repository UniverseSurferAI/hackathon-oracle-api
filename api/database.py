"""
Database module for Hackathon Oracle API
Uses SQLite for persistence
"""
import sqlite3
from datetime import datetime
from typing import Optional
from pathlib import Path

DB_PATH = "/tmp/hackathon_oracle.db"

def get_db_path():
    """Get database path"""
    return DB_PATH

def init_db():
    """Initialize the database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create markets table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS markets (
            market_id TEXT PRIMARY KEY,
            platform_id TEXT NOT NULL,
            hackathon_name TEXT NOT NULL,
            teams TEXT NOT NULL,
            data_sources TEXT NOT NULL,
            expected_announcement TEXT NOT NULL,
            betting_closes TEXT,
            status TEXT DEFAULT 'active',
            volume_usd REAL DEFAULT 0.0,
            winner TEXT,
            resolution_status TEXT,
            fee_paid INTEGER DEFAULT 0,
            fee_amount REAL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    # Create fee_history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fee_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market_id TEXT NOT NULL,
            platform_id TEXT NOT NULL,
            volume_usd REAL NOT NULL,
            fee_percentage REAL NOT NULL,
            fee_amount_usd REAL NOT NULL,
            fee_wallet TEXT NOT NULL,
            onchain_withdrawn INTEGER DEFAULT 0,
            tx_signature TEXT,
            timestamp TEXT NOT NULL
        )
    """)
    
    # Create webhooks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS webhooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform_id TEXT NOT NULL,
            url TEXT NOT NULL,
            event_types TEXT NOT NULL,
            active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)
    
    # Create scraping_results table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scraping_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market_id TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_url TEXT,
            content TEXT,
            winner_detected TEXT,
            confidence REAL,
            scraped_at TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()
    
    return DB_PATH

def get_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ============================================================================
# MARKET OPERATIONS
# ============================================================================

def create_market(market_data: dict) -> bool:
    """Create a new market"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO markets (
                market_id, platform_id, hackathon_name, teams, data_sources,
                expected_announcement, betting_closes, status, volume_usd,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            market_data["market_id"],
            market_data["platform_id"],
            market_data["hackathon_name"],
            ",".join(market_data["teams"]),
            str(market_data["data_sources"]),
            market_data["expected_announcement"],
            market_data.get("betting_closes", ""),
            "active",
            0.0,
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat()
        ))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_market(market_id: str) -> Optional[dict]:
    """Get a market by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM markets WHERE market_id = ?", (market_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

def get_all_markets() -> list:
    """Get all markets"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM markets ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def update_market_volume(market_id: str, volume_usd: float) -> bool:
    """Update market volume"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE markets SET volume_usd = ?, updated_at = ? WHERE market_id = ?
    """, (volume_usd, datetime.utcnow().isoformat(), market_id))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success

def resolve_market(market_id: str, winner: str, resolution_status: str = "success") -> bool:
    """Resolve a market"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE markets 
        SET status = 'resolved', winner = ?, resolution_status = ?, updated_at = ?
        WHERE market_id = ?
    """, (winner, resolution_status, datetime.utcnow().isoformat(), market_id))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success

def close_market_betting(market_id: str) -> bool:
    """Close betting for a market"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE markets SET status = 'betting_closed', updated_at = ? WHERE market_id = ?
    """, (datetime.utcnow().isoformat(), market_id))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success

def update_market_fee_paid(market_id: str, fee_amount: float = None) -> bool:
    """Mark a market's fee as paid"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if fee_amount:
        cursor.execute("""
            UPDATE markets SET fee_paid = 1, fee_amount = ?, updated_at = ? WHERE market_id = ?
        """, (fee_amount, datetime.utcnow().isoformat(), market_id))
    else:
        cursor.execute("""
            UPDATE markets SET fee_paid = 1, updated_at = ? WHERE market_id = ?
        """, (datetime.utcnow().isoformat(), market_id))
    
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success

def update_fee_withdrawn(market_id: str, tx_signature: str = None) -> bool:
    """Mark a fee as withdrawn on-chain"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if tx_signature:
        cursor.execute("""
            UPDATE fee_history SET onchain_withdrawn = 1, tx_signature = ? WHERE market_id = ?
        """, (tx_signature, market_id))
    else:
        cursor.execute("""
            UPDATE fee_history SET onchain_withdrawn = 1 WHERE market_id = ?
        """, (market_id,))
    
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success

# ============================================================================
# FEE OPERATIONS
# ============================================================================

def record_fee(fee_data: dict) -> bool:
    """Record a fee payment"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO fee_history (
            market_id, platform_id, volume_usd, fee_percentage,
            fee_amount_usd, fee_wallet, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        fee_data["market_id"],
        fee_data["platform_id"],
        fee_data["volume_usd"],
        fee_data["fee_percentage"],
        fee_data["fee_amount_usd"],
        fee_data["fee_wallet"],
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()
    return True

def get_fee_history() -> list:
    """Get fee history"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM fee_history ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

# ============================================================================
# WEBHOOK OPERATIONS
# ============================================================================

def register_webhook(platform_id: str, url: str, event_types: list) -> int:
    """Register a webhook"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO webhooks (platform_id, url, event_types, created_at)
        VALUES (?, ?, ?, ?)
    """, (platform_id, url, ",".join(event_types), datetime.utcnow().isoformat()))
    conn.commit()
    webhook_id = cursor.lastrowid
    conn.close()
    return webhook_id

def get_webhooks(platform_id: str = None) -> list:
    """Get registered webhooks"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if platform_id:
        cursor.execute("SELECT * FROM webhooks WHERE platform_id = ? AND active = 1", (platform_id,))
    else:
        cursor.execute("SELECT * FROM webhooks WHERE active = 1")
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_webhook(webhook_id: int) -> bool:
    """Delete a webhook"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE webhooks SET active = 0 WHERE id = ?", (webhook_id,))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success

# ============================================================================
# SCRAPING RESULTS
# ============================================================================

def save_scraping_result(result_data: dict):
    """Save a scraping result"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO scraping_results (
            market_id, source_type, source_url, content,
            winner_detected, confidence, scraped_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        result_data["market_id"],
        result_data["source_type"],
        result_data.get("source_url", ""),
        result_data.get("content", ""),
        result_data.get("winner_detected"),
        result_data.get("confidence", 0.0),
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()

def get_scraping_results(market_id: str) -> list:
    """Get scraping results for a market"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM scraping_results WHERE market_id = ? ORDER BY scraped_at DESC
    """, (market_id,))
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

# Initialize on import
init_db()