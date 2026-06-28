# Zenviq Call Bot — Implementation Plan

## Goal

Build a demo AI voice call bot platform using **LiveKit Agents (Python)** and **Twilio SIP trunking**. The platform supports multiple specialized bots, each reached via its own phone number. First deliverables:

1. **Zenviq Bot** — answers inbound calls about the Zenviq startup (what we do, pricing, how to book a demo)
2. **Dentist Bot** — acts as a full AI receptionist for a dental clinic; handles FAQs, appointment booking, cancellations, and rescheduling via tool calling

The architecture is designed so adding future bots (therapist, doctor, etc.) requires only a new agent file + a Twilio number + a LiveKit dispatch rule.

---

## Architecture

```
Caller dials Twilio number
        │
        ▼
Twilio Elastic SIP Trunk
        │  (SIP protocol)
        ▼
LiveKit SIP Service
        │  (dispatch rule matches on trunk → creates room with metadata)
        ▼
LiveKit Room
        │
        ▼
Python Worker — main.py
        │  reads room.metadata to pick agent type
        │
        ├──► ZenviqAgent     (metadata = "zenviq")
        └──► DentistAgent    (metadata = "dentist")
                │
                ▼
        STT (Deepgram Nova-3)
                │
                ▼
        LLM (OpenAI GPT-4o) + Tool Calls
                │
                ▼
        TTS (OpenAI TTS or ElevenLabs)
                │
                ▼
        Audio back to caller via LiveKit → Twilio → phone
```

**Routing mechanism:** Each Twilio phone number is backed by a LiveKit SIP Inbound Trunk. A LiveKit Dispatch Rule matches that trunk and creates a room with `metadata` set to the agent type string (`"zenviq"` or `"dentist"`). The single Python worker reads this metadata at job start and instantiates the right agent class.

---

## Tech Stack

| Layer | Choice | Reason |
|-------|--------|--------|
| Framework | LiveKit Agents Python SDK | Native SIP support, STT→LLM→TTS pipeline, tool calling |
| Telephony | Twilio Elastic SIP Trunk | Reliable, easy phone number provisioning |
| STT | Deepgram Nova-3 | <300ms latency, best real-time accuracy |
| LLM | OpenAI GPT-4o | Superior tool calling, low latency |
| TTS | OpenAI TTS (`alloy`) / ElevenLabs | Natural voice; ElevenLabs for expressive demo |
| VAD | Silero (bundled with livekit-agents) | Free, reliable voice activity detection |

---

## Project Structure

```
d:\Zenviq Call Bot\
├── .env                     # Secret keys (gitignored)
├── .env.example             # Template — fill this in
├── .gitignore
├── requirements.txt
├── Plan.md                  # This file
├── README.md                # Configuration + setup guide
│
├── main.py                  # Worker entry point
├── config.py                # Loads .env into Settings dataclass
│
├── agents/
│   ├── __init__.py
│   ├── base_agent.py        # Shared VoiceAssistantAgent base (STT/LLM/TTS wiring)
│   ├── zenviq_agent.py      # Zenviq startup bot
│   └── dentist_agent.py     # Dentist receptionist bot with tool calling
│
├── tools/
│   ├── __init__.py
│   ├── appointments.py      # Appointment tools (book/cancel/reschedule/check)
│   └── knowledge_base.py    # JSON knowledge loader → system prompt injection
│
└── data/
    ├── zenviq_info.json     # Zenviq company knowledge (FAQs, pricing, mission)
    └── dentist_info.json    # Dental clinic knowledge (hours, services, insurance)
```

---

## Implementation Steps

### Phase 1 — Scaffolding

**Files to create:**
- `.gitignore` — ignore `.env`, `__pycache__`, `.venv`
- `.env.example` — template with all required keys
- `requirements.txt` — Python dependencies

**Dependencies:**
```
livekit-agents>=0.12.0
livekit-plugins-openai>=0.12.0
livekit-plugins-deepgram>=0.12.0
livekit-plugins-elevenlabs>=0.12.0
livekit-plugins-silero>=0.12.0
python-dotenv>=1.0.0
httpx>=0.27.0
```

---

### Phase 2 — Knowledge Base Data

**`data/zenviq_info.json`**
```json
{
  "company": "Zenviq",
  "tagline": "AI Receptionists for Healthcare Practices",
  "description": "Zenviq builds AI-powered voice receptionists for dentists, doctors, and therapists. Our bots handle inbound calls 24/7, answer FAQs, and book appointments — so your staff can focus on patients.",
  "target_customers": ["dental clinics", "GP practices", "therapy practices"],
  "pricing": {
    "starter": "$199/month — 1 bot, up to 500 calls/month",
    "growth": "$399/month — 3 bots, up to 2000 calls/month",
    "enterprise": "Custom pricing for high-volume practices"
  },
  "how_to_book_demo": "Ask the caller to provide their name, email, practice type, and preferred time. Confirm the details and let them know the team will reach out within 24 hours.",
  "contact_email": "hello@zenviq.com",
  "website": "zenviq.com"
}
```

**`data/dentist_info.json`**
```json
{
  "clinic_name": "Bright Smile Dental",
  "address": "123 Main Street, Karachi, Pakistan",
  "phone": "+92-21-111-222-333",
  "hours": {
    "Monday-Friday": "9:00 AM - 6:00 PM",
    "Saturday": "10:00 AM - 3:00 PM",
    "Sunday": "Closed"
  },
  "services": ["Teeth Cleaning", "Fillings", "Teeth Whitening", "Root Canal", "Braces", "Implants", "Extractions"],
  "insurance": ["Jubilee Insurance", "EFU Health", "Allianz Care", "Cash patients welcome"],
  "doctors": [{"name": "Dr. Ayesha Khan", "speciality": "General & Cosmetic Dentistry"}]
}
```

---

### Phase 3 — Configuration

**`config.py`** — loads `.env` and exposes a `Settings` dataclass:
- `livekit_url`, `livekit_api_key`, `livekit_api_secret`
- `openai_api_key`
- `deepgram_api_key`
- `elevenlabs_api_key`
- `tts_provider` (default: `"openai"`, switch to `"elevenlabs"`)

---

### Phase 4 — Base Agent

**`agents/base_agent.py`** — abstract `BaseAgent` extending `VoiceAssistantAgent` (or `AgentSession`-compatible class):
- Wires up Silero VAD + Deepgram STT + GPT-4o LLM + chosen TTS
- Sets `allow_interruptions=True` (callers can cut in)
- Subclasses provide `system_prompt` property and register `@function_tool` methods

---

### Phase 5 — Knowledge Base Loader

**`tools/knowledge_base.py`**
- `load_knowledge(filename: str) -> str` — reads `data/<filename>.json`, formats it into a human-readable string suitable for embedding in a system prompt

---

### Phase 6 — Appointment Tools (Dentist Bot)

**`tools/appointments.py`** — in-memory mock store (dict), exposes these `@function_tool` functions for the dentist agent:

| Tool | Parameters | Returns |
|------|-----------|---------|
| `check_availability` | `date: str` | List of open time slots |
| `book_appointment` | `patient_name, phone, date, time, service` | Confirmation number |
| `cancel_appointment` | `confirmation_number` | Success/failure message |
| `reschedule_appointment` | `confirmation_number, new_date, new_time` | Updated confirmation |
| `get_clinic_info` | `topic: str` | Hours / location / services / insurance text |

All backed by in-memory dict for the demo. Easy to replace with a real calendar API (Google Calendar, Calendly, etc.) later.

---

### Phase 7 — Zenviq Agent

**`agents/zenviq_agent.py`**
- Extends `BaseAgent`
- System prompt: friendly Zenviq receptionist, knows what the company does, can explain pricing, handle objections, and capture demo requests
- Knowledge injected from `data/zenviq_info.json`
- One tool: `request_demo(name, email, practice_type, preferred_time)` — logs the request and confirms verbally

---

### Phase 8 — Dentist Agent

**`agents/dentist_agent.py`**
- Extends `BaseAgent`
- System prompt: warm, professional receptionist for Bright Smile Dental
- Knowledge injected from `data/dentist_info.json`
- All tools from `tools/appointments.py` registered
- Call flow: greet → identify need → answer questions OR book/manage appointment → polite close

---

### Phase 9 — Worker Entry Point

**`main.py`**
```python
async def entrypoint(ctx: JobContext):
    await ctx.connect()

    agent_type = ctx.room.metadata  # "zenviq" or "dentist"

    if agent_type == "dentist":
        agent = DentistAgent()
    else:
        agent = ZenviqAgent()  # default fallback

    session = AgentSession(
        stt=DeepgramSTT(),
        llm=OpenAILLM(model="gpt-4o"),
        tts=OpenAITTS(voice="alloy"),
        vad=SileroVAD(),
    )
    await session.start(agent=agent, room=ctx.room)
    await session.wait()

cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
```

---

## Twilio + LiveKit Configuration (see README.md for full steps)

| Step | Action |
|------|--------|
| 1 | Create LiveKit Cloud project, get URL + API keys |
| 2 | Buy 2 Twilio phone numbers |
| 3 | Create Twilio Elastic SIP Trunk, add both numbers, point origination to `sip:sip.livekit.cloud` |
| 4 | Create SIP credentials in Twilio (username + password) |
| 5 | Create 2 LiveKit SIP Inbound Trunks (one per number) with those credentials |
| 6 | Create 2 LiveKit Dispatch Rules — each sets room `metadata` to `"zenviq"` or `"dentist"` |
| 7 | Fill in `.env`, run `pip install -r requirements.txt`, run `python main.py dev` |

---

## Verification Checklist

- [ ] `python main.py dev` connects without errors
- [ ] LiveKit playground: room with `metadata=zenviq` → Zenviq bot responds correctly
- [ ] LiveKit playground: room with `metadata=dentist` → Dentist bot responds correctly
- [ ] Dentist bot: ask "what are your hours?" → returns hours from knowledge base
- [ ] Dentist bot: "I'd like to book an appointment for next Monday at 10am for a cleaning" → bot calls `check_availability`, then `book_appointment`, reads back confirmation number
- [ ] Dentist bot: "Can I cancel confirmation ABC123?" → bot calls `cancel_appointment`
- [ ] Zenviq bot: "What does Zenviq do?" → explains the product
- [ ] Zenviq bot: "I'd like a demo" → bot collects name/email/practice type and confirms
- [ ] Live phone call via Twilio routes to correct bot based on number dialed

---

## Extending the Platform

To add a **Therapist Bot** or any new niche:

1. Buy a new Twilio phone number
2. Create a LiveKit Inbound Trunk for it
3. Create a Dispatch Rule with `metadata: "therapist"`
4. Create `data/therapist_info.json`
5. Create `agents/therapist_agent.py` extending `BaseAgent`
6. Add `elif agent_type == "therapist": agent = TherapistAgent()` in `main.py`
