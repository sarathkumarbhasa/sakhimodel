# 🌸 Sakhi — Menstrual Health Assistant

Sakhi is a production-ready, messaging-based menstrual health assistant built on FastAPI. It combines **deterministic cycle prediction** with **Grok AI (xAI)** conversational intelligence, delivered via Telegram webhooks.

---

## 📁 Project Structure

```
sakhi/
├── app/
│   ├── main.py                      # FastAPI app, lifespan, router registration
│   ├── api/
│   │   ├── webhook.py               # POST /webhook/telegram (Telegram updates)
│   │   ├── health.py                # GET  /health
│   │   └── analytics.py             # GET  /admin/analytics (API-key protected)
│   ├── core/
│   │   ├── config.py                # Pydantic-settings environment config
│   │   ├── constants.py             # State machine, i18n messages
│   │   ├── exceptions.py            # Custom exception hierarchy
│   │   └── logging_config.py        # JSON / human-readable structured logging
│   ├── db/
│   │   ├── mongodb.py               # Motor client, connect/disconnect, index setup
│   │   ├── user_repository.py       # User CRUD operations
│   │   └── analytics_repository.py  # Analytics event CRUD + aggregation
│   ├── models/
│   │   ├── user.py                  # UserDocument Pydantic model
│   │   ├── analytics.py             # AnalyticsEvent model + EventType constants
│   │   └── telegram.py              # Telegram Update/Message Pydantic models
│   ├── services/
│   │   ├── conversation_handler.py  # State machine — core business logic
│   │   ├── cycle_service.py         # Deterministic cycle prediction (pure functions)
│   │   ├── grok_service.py          # xAI Grok API client (httpx async)
│   │   ├── telegram_service.py      # Telegram Bot API client
│   │   └── analytics_service.py     # Analytics tracking facade
│   └── utils/
│       └── validators.py            # Date parsing + input validation
├── tests/
│   └── test_cycle_service.py        # Unit tests (pytest)
├── scripts/
│   └── setup_webhook.py             # Webhook registration CLI
├── requirements.txt
├── render.yaml                      # Render deployment config
├── .env.template                    # Environment variable template
└── .gitignore
```

---

## 🏛️ Architecture

### Hybrid Intelligence Model

```
Telegram User
      │
      ▼
[Telegram Webhook]  POST /webhook/telegram
      │
      ▼
[Conversation Handler] ─── State Machine ───┐
      │                                      │
      ├─ NEW / AWAITING_LANGUAGE             │
      │        → Welcome + language menu     │
      │                                      │
      ├─ AWAITING_LAST_PERIOD                │
      │        → Parse date + validate       │
      │        → Deterministic Prediction ◄──┘
      │
      └─ ACTIVE
               │
               ├─ Cycle query?  → Deterministic Cycle Engine
               │                   (predict_next_period, pure Python)
               │
               └─ Health query? → Grok AI (xAI API)
                                   httpx async + medical system prompt
                                   + fallback on timeout/error

[MongoDB Atlas] ← Motor async → User state, analytics events
```

### Key Design Decisions

| Concern | Approach |
|---|---|
| Conversation state | MongoDB-persisted string state per user |
| Cycle prediction | Pure deterministic Python (no AI, no latency) |
| AI layer | Grok via OpenAI-compatible xAI API — only for open-ended health questions |
| Channel | Telegram webhook. Swap `telegram_service.py` for WhatsApp/SMS |
| Errors | Never crash Telegram's webhook loop; always return 200 |
| Analytics | Fire-and-forget; failures logged but never surface to users |
| Secrets | 100% via environment variables — zero hardcoded values |

---

## 🚀 Deployment on Render

### Step 1 — Prerequisites

- MongoDB Atlas cluster (M0 free tier works)
- Telegram bot created via [@BotFather](https://t.me/BotFather)
- xAI account with Grok API key from [console.x.ai](https://console.x.ai/)
- [Render](https://render.com) account

### Step 2 — MongoDB Atlas Setup

1. Create a cluster at [cloud.mongodb.com](https://cloud.mongodb.com)
2. Create a database user with read/write permissions
3. Whitelist `0.0.0.0/0` in Network Access (Render uses dynamic IPs)
4. Copy the connection string: `mongodb+srv://<user>:<pass>@cluster0.xxxxx.mongodb.net/`

### Step 3 — Deploy to Render

**Option A — render.yaml (recommended)**

```bash
# Push your code to GitHub
git init && git add . && git commit -m "Initial commit"
git remote add origin https://github.com/yourname/sakhi.git
git push -u origin main

# In Render dashboard: New → Blueprint → connect your repo
# Render reads render.yaml automatically
```

**Option B — Manual**

1. Render Dashboard → **New Web Service**
2. Connect your GitHub repository
3. Settings:
   - Runtime: **Python 3**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2`
   - Health Check Path: `/health`

4. Add **Environment Variables** (from `.env.template`):

| Key | Value |
|---|---|
| `ENVIRONMENT` | `production` |
| `TELEGRAM_BOT_TOKEN` | Your bot token |
| `SECRET_TOKEN` | Random 32-char hex string |
| `MONGODB_URI` | Atlas connection string |
| `GROK_API_KEY` | xAI API key |
| `ADMIN_API_KEY` | Strong random key |

5. Click **Deploy**. Note your URL: `https://sakhi-xxxx.onrender.com`

### Step 4 — Register Telegram Webhook

```bash
# Install dependencies locally
pip install httpx

# Register webhook
python scripts/setup_webhook.py \
  --token YOUR_BOT_TOKEN \
  --url https://sakhi-xxxx.onrender.com \
  --secret YOUR_SECRET_TOKEN \
  --action set

# Verify
python scripts/setup_webhook.py --token YOUR_BOT_TOKEN --action info
```

---

## 🛠️ Local Development

```bash
# Clone and install
git clone https://github.com/yourname/sakhi.git
cd sakhi
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.template .env
# Edit .env with your credentials

# Run
uvicorn app.main:app --reload --port 8000

# For local Telegram testing, use ngrok:
ngrok http 8000
# Then set webhook to https://xxxx.ngrok.io
```

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

---

## 🔗 API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/webhook/telegram` | Secret token header | Telegram update receiver |
| `GET` | `/health` | None | Service + DB health check |
| `GET` | `/admin/analytics` | `X-Admin-API-Key` header | Usage analytics |
| `GET` | `/docs` | None (dev only) | Swagger UI |

---

## 💬 Conversation Flow

```
User: /start
Sakhi: Welcome! Choose language: 1) English 2) Hindi 3) Tamil

User: 1
Sakhi: Language set to English. What date did your last period start? (DD-MM-YYYY)

User: 10-02-2025
Sakhi: 🌸 Cycle Prediction
       Last period: 10 February 2025
       Next period: 10 March 2025
       Days remaining: 8 days

User: I have bad cramps, what should I do?
Sakhi: [Grok AI response with medical disclaimer]

User: when is my next period?
Sakhi: [Deterministic prediction — no AI call]
```

---

## ⚠️ Medical Disclaimer

Sakhi is an informational assistant only. It does not provide medical diagnoses or treatment recommendations. All health-related responses include appropriate disclaimers directing users to consult qualified healthcare professionals.
