# Hackathon Oracle API

**Oracle API for hackathon prediction market resolution on Solana**

---

## What is This?

Hackathon Oracle API enables prediction market platforms to create markets on hackathon outcomes. We monitor the data sources you provide and automatically resolve markets when winners are announced.

**The Problem:** Prediction markets need a trusted way to resolve hackathon winner markets without manual intervention.

**Our Solution:** Platforms create markets with hackathon data sources (Twitter, website, Discord). Our oracle monitors these sources. When winners are announced publicly, we automatically resolve the market and collect our 2% fee.

---

## Fee Structure

| Component | Details |
|-----------|---------|
| **Platform Fee** | 2% on volume traded |
| **Settlement** | USDC on Ethereum |
| **Fee Wallet** | `0x7252c6477139989916F5c41b969208C5B947AC1d` |

When a market resolves, 2% of the trading volume is collected as the oracle fee.

---

## Features

### ✅ Core Features
- **Market Creation** - Create markets with team names and data sources
- **Fee Collection** - Automatic 2% fee on trading volume
- **Market Resolution** - Manual or automatic resolution
- **Volume Tracking** - Real-time volume updates from platforms

### ✅ Auto-Monitoring
- **Website Scraping** - Monitors hackathon websites for winner announcements
- **Twitter Monitoring** - Checks Twitter for result announcements (requires API)
- **Discord Monitoring** - Monitors Discord channels (requires bot token)
- **Confidence Scoring** - High-confidence detections auto-resolve markets

### ✅ Database Persistence
- **SQLite Database** - All markets, fees, and results stored persistently
- **Webhook Notifications** - Real-time notifications to platforms
- **Scraping History** - All scraping results logged for audit

### ✅ Webhooks
- `market_created` - New market created
- `market_resolved` - Market resolved with winner
- `betting_closed` - Betting closed for market
- `winner_detected` - Potential winner detected in monitoring

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

## API Endpoints

### Create Market

```http
POST /api/v1/markets
```

```json
{
  "platform_id": "your-platform",
  "market_id": "unique-market-id",
  "hackathon_name": "ETHGlobal Tokyo 2024",
  "teams": ["Team Alpha", "Team Beta", "Team Gamma"],
  "data_sources": {
    "twitter": "@ethglobal",
    "website": "https://ethglobal.com/results"
  },
  "expected_announcement": "2024-04-15T00:00:00Z"
}
```

### Get Market

```http
GET /api/v1/markets/{market_id}
```

### Update Volume

```http
POST /api/v1/markets/{market_id}/volume?volume_usd=10000
```

### Resolve Market

```http
POST /api/v1/markets/{market_id}/resolve?winner=Team%20Alpha
```

### Register Webhook

```http
POST /api/v1/webhooks
```

```json
{
  "platform_id": "your-platform",
  "url": "https://your-platform.com/webhooks/oracle",
  "event_types": ["market_resolved", "winner_detected"]
}
```

### Scrape Website (Manual)

```http
POST /api/v1/scrape/{market_id}
```

### Get Fee History

```http
GET /api/v1/fees
```

---

## Monitoring Flow

```
1. Platform creates market with data_sources
   ↓
2. Oracle starts monitoring:
   - Website: Periodic scraping for winner keywords
   - Twitter: Checks for result announcements (API required)
   - Discord: Monitors channels (Bot required)
   ↓
3. Winner detected (confidence ≥ 0.5)
   ↓
4. Webhook: winner_detected sent to platform
   ↓
5. Auto-resolve if confidence ≥ 0.8
   ↓
6. Webhook: market_resolved sent
   ↓
7. Platform settles winners, oracle collects 2% fee
```

---

## Webhook Payload

```json
{
  "event": "market_resolved",
  "timestamp": "2024-04-15T12:00:00Z",
  "data": {
    "market_id": "unique-market-id",
    "hackathon_name": "ETHGlobal Tokyo 2024",
    "winner": "Team Alpha",
    "fee_collected_usd": 200.00,
    "status": "resolved"
  }
}
```

---

## Deployment

### Local Deployment

```bash
# Clone the repo
git clone https://github.com/UniverseSurferAI/hackathon-oracle-api.git
cd hackathon-oracle-api

# Run deploy script
./deploy.sh
```

### GitHub Actions (Auto-Deploy)

Push to main branch triggers automatic deployment via GitHub Actions.

**Note:** GitHub Actions deployment requires GCP service account key configured as `GCP_SA_KEY` secret.

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
├── deploy.sh             # Local deployment script
├── cloudbuild.yaml        # Cloud Build config
└── api/
    ├── __init__.py
    ├── main.py            # FastAPI application
    ├── database.py        # SQLite persistence
    ├── fee_calculator.py   # Fee calculation logic
    ├── resolution.py       # Oracle monitoring
    ├── scraping.py         # Website/Twitter/Discord scrapers
    └── webhooks.py        # Webhook notifications
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
| python-dotenv | 1.0.0 | Environment variables |

---

## License

MIT