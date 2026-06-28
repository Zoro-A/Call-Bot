from __future__ import annotations

from abc import abstractmethod

from livekit.agents import Agent, AgentSession
from livekit.plugins import deepgram, openai, elevenlabs, silero

from config import settings


def build_session() -> AgentSession:
    """Build a shared STT → LLM → TTS pipeline session based on settings."""
    stt = deepgram.STT(api_key=settings.deepgram_api_key)
    llm_model = openai.LLM(model="gpt-4o", api_key=settings.openai_api_key)
    vad = silero.VAD.load()

    if settings.tts_provider == "elevenlabs" and settings.elevenlabs_api_key:
        tts = elevenlabs.TTS(
            api_key=settings.elevenlabs_api_key,
            voice_id=settings.elevenlabs_voice_id,
        )
    else:
        tts = openai.TTS(
            voice=settings.openai_tts_voice,
            api_key=settings.openai_api_key,
        )

    return AgentSession(
        stt=stt,
        llm=llm_model,
        tts=tts,
        vad=vad,
    )
