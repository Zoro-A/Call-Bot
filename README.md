# Zenviq Call Bot

AI-powered voice call bot platform built on LiveKit + Twilio. Handles inbound phone calls for multiple niches — starting with a Zenviq startup info bot and a dental receptionist bot with appointment booking.

---

## How It Works

```
Caller dials Twilio number
        │
        ▼
Twilio Elastic SIP Trunk  (routes call via SIP)
        │
        ▼
LiveKit SIP Service  (matches dispatch rule → creates room)
        │
        ▼
Python Worker (main.py)  (joins room, reads agent_type from metadata)
        │
        ├──► ZenviqAgent  (startup FAQs, demo requests)
        └──► DentistAgent  (appointments, clinic info, tools)
```

---

## Prerequisites

- Python 3.10+
- A [LiveKit Cloud](https://cloud.livekit.io) account (free tier works)
- A [Twilio](https://www.twilio.com) account
- API keys for: OpenAI, Deepgram, ElevenLabs

---

## Step 1 — LiveKit Cloud Setup

### 1.1 Create a Project
1. Go to [cloud.livekit.io](https://cloud.livekit.io) → **New Project**
2. Name it `zenviq-call-bot`
3. Copy your **WebSocket URL** (e.g. `wss://zenviq-call-bot-xxxx.livekit.cloud`)
4. Go to **Settings → Keys** → copy **API Key** and **API Secret**

### 1.2 Enable SIP
1. In your LiveKit project, go to **SIP** in the left sidebar
2. Note your **LiveKit SIP URI** — it looks like:
   ```
   sip.livekit.cloud
   ```
   You'll use this as the SIP trunk destination in Twilio.

---

## Step 2 — Twilio Setup

### 2.1 Buy Two Phone Numbers
1. Log into [twilio.com/console](https://www.twilio.com/console)
2. Go to **Phone Numbers → Manage → Buy a number**
3. Buy **two numbers** — one for each bot:
   - Number 1: your Zenviq info bot number
   - Number 2: your Dentist bot number
4. Note both numbers in `+1XXXXXXXXXX` format

### 2.2 Create an Elastic SIP Trunk
1. In Twilio Console go to **Elastic SIP Trunking → Trunks → Create new trunk**
2. Name it: `LiveKit Zenviq Bot`
3. Under **Origination** (inbound calls FROM Twilio TO LiveKit):
   - Click **Add new Origination URI**
   - Set URI to:
     ```
     sip:sip.livekit.cloud
     ```
   - Set **Priority**: 1, **Weight**: 1
4. Under **Numbers** → **Add a Number** → add both phone numbers you bought

### 2.3 Configure SIP Credentials (for LiveKit to accept the trunk)
LiveKit authenticates inbound SIP calls using a username/password:
1. In Twilio → your trunk → **Authentication** tab
2. Under **Credential Lists** → create a new credential list
   - Username: `livekit-bot` (any name you like)
   - Password: generate a strong random password — save it, you'll need it in Step 3
3. Add this credential list to your trunk

---

## Step 3 — LiveKit SIP Inbound Trunks

In the LiveKit Console create **two SIP Inbound Trunks** — one per phone number / bot.

### Using LiveKit CLI
Install the CLI (Windows):
```powershell
winget install LiveKit.LiveKitCLI
```

Then authenticate (this opens a browser login — do this once):
```powershell
lk cloud auth
```

Once authenticated, the CLI automatically uses your project credentials. You can also set them manually if needed:
```powershell
$env:LIVEKIT_URL = "wss://your-project.livekit.cloud"
$env:LIVEKIT_API_KEY = "your_api_key"
$env:LIVEKIT_API_SECRET = "your_api_secret"
```

#### Create Zenviq Inbound Trunk
```bash
lk sip inbound create '{
  "name": "Zenviq Bot Trunk",
  "numbers": ["+1XXXXXXXXXX"],
  "auth_username": "livekit-bot",
  "auth_password": "your-twilio-credential-password"
}'
```
Save the returned `sip_trunk_id` — it looks like `ST_xxxxxxxxxxxx`.

#### Create Dentist Inbound Trunk
```bash
lk sip inbound create '{
  "name": "Dentist Bot Trunk",
  "numbers": ["+1YYYYYYYYYY"],
  "auth_username": "livekit-bot",
  "auth_password": "your-twilio-credential-password"
}'
```
Save the returned `sip_trunk_id`.

---

## Step 4 — LiveKit SIP Dispatch Rules

Dispatch rules tell LiveKit which room to create and what metadata to attach when a call arrives on a trunk. The `metadata` value is what our Python worker reads to decide which bot to run.

#### Dispatch Rule for Zenviq Bot
```bash
lk sip dispatch create '{
  "name": "Zenviq Bot Rule",
  "trunk_ids": ["ST_xxxxxxxxxxxx"],
  "rule": {
    "dispatchRuleIndividual": {
      "roomPrefix": "zenviq-call-",
      "roomConfig": {
        "metadata": "zenviq"
      }
    }
  }
}'
```

#### Dispatch Rule for Dentist Bot
```bash
lk sip dispatch create '{
  "name": "Dentist Bot Rule",
  "trunk_ids": ["ST_yyyyyyyyyyyy"],
  "rule": {
    "dispatchRuleIndividual": {
      "roomPrefix": "dentist-call-",
      "roomConfig": {
        "metadata": "dentist"
      }
    }
  }
}'
```

---

## Step 5 — Environment Variables

Copy `.env.example` to `.env` and fill in all values:

```bash
copy .env.example .env
```

Open `.env` and fill in:
```
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIxxxxxxxxxxxxxxxxxx
LIVEKIT_API_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

OPENAI_API_KEY=sk-...
DEEPGRAM_API_KEY=...
ELEVENLABS_API_KEY=...

ZENVIQ_PHONE_NUMBER=+1XXXXXXXXXX
DENTIST_PHONE_NUMBER=+1YYYYYYYYYY
```

---

## Step 6 — Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 7 — Run the Worker

```bash
python main.py dev
```

The worker connects to LiveKit Cloud and waits for inbound calls:
```
Starting worker...
Connected to LiveKit: wss://your-project.livekit.cloud
Waiting for jobs...
```

### Test Without a Phone Call (Recommended First)
Use LiveKit's browser playground to simulate a caller:
1. Go to [agents-playground.livekit.io](https://agents-playground.livekit.io)
2. Enter your LiveKit URL + API key/secret
3. Connect to a room named `zenviq-call-test` with metadata `zenviq`
4. Click **Start** and speak — the Zenviq bot should respond

### Live Call Test
Dial the Twilio number you configured. The call routes through:
Twilio → SIP Trunk → LiveKit SIP → Dispatch Rule → Python Worker → Agent

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Worker doesn't start | Check `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` in `.env` |
| Call connects but no voice | Check `OPENAI_API_KEY` and `DEEPGRAM_API_KEY` |
| SIP call fails at Twilio | Verify Origination URI is exactly `sip:sip.livekit.cloud` |
| Call connects but wrong bot runs | Check dispatch rule `metadata` is exactly `"zenviq"` or `"dentist"` |
| No dispatch rule matches | Confirm the trunk_id in your dispatch rule matches the inbound trunk for that phone number |
| TTS sounds robotic | Switch `TTS_PROVIDER` in `.env` to `elevenlabs` and add `ELEVENLABS_API_KEY` |

---

## Project Structure

```
├── main.py              # Worker entry point — registers with LiveKit, routes to agents
├── config.py            # Settings loader from .env
├── agents/
│   ├── base_agent.py    # Shared STT/LLM/TTS pipeline wiring
│   ├── zenviq_agent.py  # Zenviq startup info + demo booking bot
│   └── dentist_agent.py # Dental receptionist bot with appointment tools
├── tools/
│   ├── appointments.py  # Book / cancel / reschedule appointment tools (mock data)
│   └── knowledge_base.py # Loads JSON knowledge into system prompt context
└── data/
    ├── zenviq_info.json  # Zenviq company knowledge base
    └── dentist_info.json # Dental clinic knowledge base
```

---

## Adding More Bots (Doctors, Therapists, etc.)

1. Buy a new Twilio number
2. Create a LiveKit Inbound Trunk for it (Step 3)
3. Create a Dispatch Rule with `metadata: "therapist"` (Step 4)
4. Create `agents/therapist_agent.py` extending `BaseAgent`
5. Add the new `agent_type` case in `main.py`
6. Add `data/therapist_info.json` with the practice knowledge base

---

## API Keys Reference

| Key | Where to get it |
|-----|----------------|
| `LIVEKIT_URL` / `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` | [cloud.livekit.io](https://cloud.livekit.io) → Settings → Keys |
| `OPENAI_API_KEY` | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| `DEEPGRAM_API_KEY` | [console.deepgram.com](https://console.deepgram.com) → API Keys |
| `ELEVENLABS_API_KEY` | [elevenlabs.io](https://elevenlabs.io) → Profile → API Key |
