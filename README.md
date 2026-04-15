# Hackathon Oracle API

**Oracle API for hackathon prediction market resolution on Solana**

---

## What is This?

Hackathon Oracle API enables prediction market platforms to create markets on hackathon outcomes. We monitor the data sources you provide and automatically resolve markets when winners are announced.

**The Problem:** Prediction markets need a trusted way to resolve hackathon winner markets without manual intervention.

**Our Solution:** Platforms create markets with hackathon data sources (Twitter, website, Discord). Our oracle monitors these sources. When winners are announced publicly, we automatically resolve the market.

---

## Fee Structure

| Component | Details |
|-----------|---------|
| **Platform Fee** | 2% on volume traded |
| **Collection** | When betting closes (24-48h before announcement) |
| **Settlement** | USDC on Solana to: `0x7252c6477139989916F5c41b969208C5B947AC1d` |
| **Verification** | On-chain verification required |

**Important:** Platforms must send the 2% fee to the oracle wallet when betting closes. The oracle will verify the payment on-chain.

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn api.main:app --reload --port 8000

# API docs at:
# http://localhost:8000/docs
```

---

## Platform Integration Guide

### Step 1: Create a Market

```http
POST /api/v1/markets
```

```json
{
  "platform_id": "your-platform-id",
  "market_id": "unique-market-id",
  "hackathon_name": "ETHGlobal Paris 2024",
  "teams": ["Team Alpha", "Team Beta", "Team Gamma"],
  "data_sources": {
    "twitter": "@ethglobal",
    "website": "https://ethglobal.com/results"
  },
  "expected_announcement": "2024-04-15T00:00:00Z",
  "betting_closes_hours_before": 24
}
```

**Response:**
```json
{
  "status": "success",
  "market_id": "unique-market-id",
  "betting_closes_at": "2024-04-14T00:00:00Z",
  "message": "Market created. Volume tracking started."
}
```

---

### Step 2: Report Trading Volume

Call this whenever users place bets on your platform:

```http
POST /api/v1/markets/{market_id}/volume?volume_usd=10000
```

**Important:** This should be the **cumulative total volume** for this market, not incremental.

```json
{
  "status": "success",
  "market_id": "unique-market-id",
  "volume_usd": 10000.0,
  "fee_at_close_usd": 200.0,
  "fee_wallet": "0x7252c6477139989916F5c41b969208C5B947AC1d",
  "message": "Volume updated. Fee will be collected when betting closes."
}
```

---

### Step 3: When Betting Closes

Your platform should call:

```http
POST /api/v1/markets/{market_id}/close-betting
```

**Or the oracle will auto-close at the scheduled time.**

**Response:**
```json
{
  "status": "success",
  "market_id": "unique-market-id",
  "volume_usd": 10000.0,
  "fee_amount_usd": 200.0,
  "fee_wallet": "0x7252c6477139989916F5c41b969208C5B947AC1d",
  "message": "Betting closed. Fee calculated. Platform must send USDC to oracle wallet."
}
```

---

### Step 4: Pay the Fee

Send `fee_amount_usd` USDC to the oracle wallet:

```
Recipient: 0x7252c6477139989916F5c41b969208C5B947AC1d
Network: Solana (USDC)
Amount: fee_amount_usd
```

**For Solana USDC:**
- Mint: `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDj1v`
- Use Phantom wallet or any Solana wallet

---

### Step 5: (Optional) Register Webhook

Get notified when markets resolve:

```http
POST /api/v1/webhooks
```

```json
{
  "platform_id": "your-platform-id",
  "url": "https://your-platform.com/webhooks/oracle",
  "event_types": ["market_created", "market_resolved", "betting_closed", "winner_detected"]
}
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `POST` | `/api/v1/markets` | Create a new market |
| `GET` | `/api/v1/markets` | List all markets |
| `GET` | `/api/v1/markets/{id}` | Get market details |
| `POST` | `/api/v1/markets/{id}/volume` | Update trading volume |
| `POST` | `/api/v1/markets/{id}/close-betting` | Close betting and calculate fee |
| `POST` | `/api/v1/markets/{id}/resolve` | Resolve with winner |
| `GET` | `/api/v1/fees` | Get fee history |
| `GET` | `/api/v1/wallet/balance` | Get oracle USDC balance |
| `POST` | `/api/v1/webhooks` | Register webhook |
| `GET` | `/api/v1/webhooks` | List webhooks |
| `POST` | `/api/v1/scrape/{id}` | Trigger manual scrape |

---

## Monitoring Flow

```
1. Platform creates market with data_sources
   ↓
2. Oracle starts monitoring:
   - Website: Periodic scraping for winner keywords
   - Twitter: Checks for result announcements
   - Discord: Monitors channels
   ↓
3. Winner detected (confidence ≥ 0.5)
   ↓
4. Webhook: winner_detected sent to platform
   ↓
5. Betting closes → Fee invoice generated
   ↓
6. Platform pays fee to oracle wallet
   ↓
7. Platform calls resolve with winner
   ↓
8. Webhook: market_resolved sent
```

---

## Webhook Payload

```json
{
  "event": "betting_closed",
  "timestamp": "2024-04-14T12:00:00Z",
  "data": {
    "market_id": "unique-market-id",
    "hackathon_name": "ETHGlobal Paris 2024",
    "volume_usd": 10000.0,
    "fee_amount_usd": 200.0,
    "fee_wallet": "0x7252c6477139989916F5c41b969208C5B947AC1d",
    "status": "betting_closed"
  }
}
```

---

## Auto-Monitoring

- **Website Scraping** - Monitors hackathon websites for winner announcements
- **Twitter Monitoring** - Checks Twitter for result announcements (requires API)
- **Discord Monitoring** - Monitors Discord channels (requires bot token)
- **Confidence Scoring** - High-confidence detections auto-resolve markets

---

## Deployment

### Local Deployment

```bash
git clone https://github.com/UniverseSurferAI/hackathon-oracle-api.git
cd hackathon-oracle-api
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

### GitHub Actions (Auto-Deploy)

Push to main branch triggers automatic deployment via GitHub Actions.

---

## Live API

**Production URL:** https://hackathon-oracle-api-752364645771.europe-west1.run.app

**Health Check:**
```bash
curl https://hackathon-oracle-api-752364645771.europe-west1.run.app/
```

---

## Project Structure

```
hackathon-oracle-api/
├── README.md              # This file
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker image
├── api/
│   ├── __init__.py
│   ├── main.py            # FastAPI application
│   ├── database.py        # SQLite persistence
│   ├── fee_calculator.py  # Fee calculation logic
│   ├── resolution.py      # Oracle monitoring
│   ├── scraping.py        # Website/Twitter/Discord scrapers
│   ├── solana_service.py # Solana integration (balance check, verification)
│   └── webhooks.py        # Webhook notifications
```

---

## Requirements

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.109.0 | Web framework |
| uvicorn | 0.27.0 | ASGI server |
| pydantic | 2.6.0 | Data validation |
| httpx | 0.26.0 | HTTP client (scraping) |
| loguru | 0.7.2 | Logging |
| solana | ≥0.35.0 | Solana blockchain interaction |
| solders | ≥0.20.0 | Solana primitives |

---

## License

MIT
