import asyncio
import logging

from livekit.agents import JobContext, WorkerOptions, cli

from agents.base_agent import build_session
from agents.zenviq_agent import ZenviqAgent
from agents.dentist_agent import DentistAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_AGENT_MAP = {
    "zenviq": ZenviqAgent,
    "dentist": DentistAgent,
}


async def entrypoint(ctx: JobContext) -> None:
    """
    Main worker entrypoint. Reads the room metadata set by the LiveKit SIP dispatch rule
    to determine which agent class to instantiate for this call.
    """
    await ctx.connect()

    agent_type = (ctx.room.metadata or "zenviq").strip().lower()
    logger.info("Incoming call — agent_type: %s | room: %s", agent_type, ctx.room.name)

    agent_cls = _AGENT_MAP.get(agent_type)
    if agent_cls is None:
        logger.warning(
            "Unknown agent_type '%s', falling back to ZenviqAgent. "
            "Check your LiveKit dispatch rule metadata.",
            agent_type,
        )
        agent_cls = ZenviqAgent

    agent = agent_cls()
    session = build_session()

    await session.start(agent=agent, room=ctx.room)
    await session.wait()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
