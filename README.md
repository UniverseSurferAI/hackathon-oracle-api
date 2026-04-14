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
  "platform_id": "prediction-pro",
  "market_id": "colosseum-team-xyz",
  "hackathon_name": "Colosseum Spring 2026",
  "teams": ["TeamX", "TeamY", "TeamZ"],
  "data_sources": {
    "twitter": "@ColosseumHQ",
    "website": "https://colosseum.io/results",
    "discord": "colosseum.gg/discord"
  },
  "expected_announcement": "2026-04-20T00:00:00Z",
  "betting_closes_hours_before": 48
}
```

### Get Market Status

```http
GET /api/v1/markets/{market_id}
```

### Update Trading Volume

```http
POST /api/v1/markets/{market_id}/volume
Content-Type: application/json

{"volume_usd": 5000}
```

### Close Betting

```http
POST /api/v1/markets/{market_id}/close-betting
```

### Resolve Market (Manual)

```http
POST /api/v1/markets/{market_id}/resolve
Content-Type: application/json

{"winner": "TeamX"}
```

### Fee History

```http
GET /api/v1/fees
```

---

## How It Works

```
1. Platform creates market with hackathon data sources
   ↓
2. Our oracle starts monitoring (Twitter, website, Discord)
   ↓
3. Traders buy YES/NO tokens on the platform
   ↓
4. Platform updates volume as trades happen
   ↓
5. When winner is announced publicly, we detect it
   ↓
6. Market resolves - 2% fee collected to our wallet
   ↓
7. Platform distributes winnings to traders
```

---

## Data Sources

The oracle can monitor:

| Source | Config Field | Example |
|--------|--------------|---------|
| **Twitter** | `twitter` | `@ColosseumHQ` |
| **Website** | `website` | `https://colosseum.io/results` |
| **Discord** | `discord` | `colosseum.gg/discord` |

**Minimum requirement:** At least one data source must be provided.

---

## Anti-Abuse Protections

| Protection | How it Works |
|------------|--------------|
| **Time-lock** | Betting closes 24-48h before expected announcement |
| **Multi-source** | Confirms winner from 2+ sources before resolving |
| **Automated** | No manual override - oracle decides based on data |
| **Dispute period** | 24h challenge window after resolution |

---

## Integration Example (Python)

```python
import httpx

# Create a market
response = httpx.post("http://localhost:8000/api/v1/markets", json={
    "platform_id": "my-platform",
    "market_id": "hackathon-team-x",
    "hackathon_name": "Colosseum Spring 2026",
    "teams": ["TeamX", "TeamY", "TeamZ"],
    "data_sources": {
        "twitter": "@ColosseumHQ"
    },
    "expected_announcement": "2026-04-20T00:00:00Z"
})

print(response.json())
```

---

## Project Structure

```
hackathon-oracle-api/
├── README.md              # This file
├── requirements.txt      # Python dependencies
├── api/
│   ├── __init__.py
│   ├── main.py          # FastAPI server + endpoints
│   ├── fee_calculator.py # 2% fee logic
│   └── resolution.py     # Oracle monitoring

```

---

## Technology Stack

- **Framework:** FastAPI
- **Language:** Python 3.11+
- **Validation:** Pydantic
- **Monitoring:** Background asyncio tasks
- **Data Storage:** In-memory (use database in production)

---

## Development Status

**Current:** MVP with core functionality

**To Do:**
- [ ] Twitter API v2 integration for real monitoring
- [ ] Website scraping for result pages
- [ ] Discord bot for channel monitoring
- [ ] Database persistence (SQLite/PostgreSQL)
- [ ] Client libraries (Python, TypeScript, Rust)
- [ ] Rate limiting
- [ ] Admin dashboard

---

## Contributing

1. Fork the repo
2. Create a feature branch
3. Submit PR with tests

---

## License

MIT

---

**Note:** This API is designed for prediction market platforms. If you're building a platform and want to integrate, contact us for API access.