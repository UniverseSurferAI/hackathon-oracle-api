# Hackathon Oracle API

Oracle API for hackathon prediction market resolution. Monitors data sources (Twitter, websites, Discord) to automatically resolve markets when hackathon winners are announced.

## Overview

This API enables prediction market platforms to create markets on hackathon outcomes. Our oracle monitors the provided data sources and automatically resolves markets when winners are announced.

**Fee:** 2% on volume traded through markets using this oracle.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn api.main:app --reload
```

## API Documentation

See full documentation at [docs/](./docs/).

## License

MIT