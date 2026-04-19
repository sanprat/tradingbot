# TradingBot

A fully functional trading bot that receives TradingView webhook alerts and executes trades through broker APIs.

**⚠️ IMPORTANT:** This codebase is proprietary and strictly licensed. See [LICENSE](LICENSE) for details. All rights reserved.

## Features

- **Paper Trading** - Test strategies without risking real capital
- **Live Trading** - Connect to Dhan or Shoonya brokers
- **Risk Controls** - Kill switch, max quantity, max notional, daily loss limits
- **Async Execution** - Background workers for order processing
- **Dashboard API** - Monitor positions, orders, and system status

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run in paper mode (default)
python -m uvicorn app.main:app --port 8001
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Trading mode
ENVIRONMENT=paper           # or 'live'
DEFAULT_BROKER=paper      # paper, dhan, or shoonya

# Webhook secret (change in production!)
TRADINGVIEW_WEBHOOK_SECRET=your-secret-here

# For live trading with Dhan
DHAN_CLIENT_ID=your_client_id
DHAN_ACCESS_TOKEN=your_token

# For live trading with Shoonya  
SHOONYA_USER_ID=your_user_id
SHOONYA_PASSWORD=your_password
SHOONYA_API_KEY=your_api_key
SHOONYA_TOTP_SECRET=your_totp_secret
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/webhook/tradingview` | Receive TradingView alerts |
| `GET /api/dashboard/positions` | View open positions |
| `GET /api/dashboard/orders` | View order history |
| `GET /api/dashboard/status` | System health check |
| `POST /api/dashboard/settings/kill-switch` | Toggle kill switch |
| `GET /health` | Health check |

## Webhook Payload

```json
{
  "secret": "your-webhook-secret",
  "strategy_id": "momentum-001",
  "symbol": "RELIANCE",
  "exchange": "NSE",
  "side": "BUY",
  "quantity": 10,
  "order_type": "MKT",
  "product": "INTRADAY",
  "timestamp": "1745044400",
  "stop_loss": 2800,
  "take_profit": 3000
}
```

## Architecture

```
webhook.py → execution_engine.py → broker adapters → broker APIs
                              ↓
                         positions table
                              ↓
                    reconciliation_worker
```

## License

**STRICTLY PROPRIETARY** - See [LICENSE](LICENSE) for full terms. All rights reserved.

---

Built for personal use. Not intended for distribution.