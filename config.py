import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str
    openai_api_key: str
    deepgram_api_key: str
    elevenlabs_api_key: str
    tts_provider: str        # "openai" or "elevenlabs"
    openai_tts_voice: str    # alloy | echo | fable | onyx | nova | shimmer
    elevenlabs_voice_id: str


def load_settings() -> Settings:
    def require(key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise RuntimeError(f"Missing required environment variable: {key}")
        return value

    return Settings(
        livekit_url=require("LIVEKIT_URL"),
        livekit_api_key=require("LIVEKIT_API_KEY"),
        livekit_api_secret=require("LIVEKIT_API_SECRET"),
        openai_api_key=require("OPENAI_API_KEY"),
        deepgram_api_key=require("DEEPGRAM_API_KEY"),
        elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY", ""),
        tts_provider=os.getenv("TTS_PROVIDER", "openai"),
        openai_tts_voice=os.getenv("OPENAI_TTS_VOICE", "alloy"),
        elevenlabs_voice_id=os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
    )


settings = load_settings()
