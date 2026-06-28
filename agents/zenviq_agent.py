from typing import Annotated

from livekit.agents import Agent, llm

from tools.knowledge_base import load_knowledge

_KNOWLEDGE = load_knowledge("zenviq_info.json")

_SYSTEM_PROMPT = f"""You are Zara, the AI receptionist for Zenviq — a startup that builds AI voice receptionists for healthcare practices.

Your job is to:
- Answer questions about what Zenviq does, who it's for, and how it works
- Explain pricing clearly and confidently
- Handle objections professionally and empathetically
- Collect information from interested callers to book a demo
- Keep responses concise and conversational — you're on a phone call, not writing an email

Tone: Friendly, professional, confident, and enthusiastic about the product. You genuinely believe AI receptionists will transform how healthcare practices handle calls.

Key rules:
- Never make up information. If you don't know something, say so and offer to have someone from the team follow up.
- Always end the call by asking if there's anything else you can help with.
- When collecting demo request details, confirm each piece of information clearly before moving on.
- Speak naturally — short sentences, no filler words.

--- ZENVIQ KNOWLEDGE BASE ---
{_KNOWLEDGE}
---
"""


class ZenviqAgent(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=_SYSTEM_PROMPT)

    async def on_enter(self) -> None:
        await self.session.say(
            "Hello! You've reached Zenviq. I'm Zara, our AI receptionist. "
            "How can I help you today?",
            allow_interruptions=True,
        )

    @llm.function_tool()
    async def request_demo(
        self,
        name: Annotated[str, "Full name of the person requesting the demo"],
        email: Annotated[str, "Email address to send the demo invite to"],
        practice_type: Annotated[
            str,
            "Type of practice: dental, GP, therapy, specialist, or other"
        ],
        preferred_time: Annotated[
            str,
            "Preferred day and time for the demo call, e.g. 'Tuesday afternoon' or 'Monday at 3pm'"
        ],
    ) -> str:
        """Register a demo request from an interested prospect."""
        # In production: save to CRM, send confirmation email, notify sales team
        print(
            f"[DEMO REQUEST] Name: {name} | Email: {email} | "
            f"Practice: {practice_type} | Preferred time: {preferred_time}"
        )
        return (
            f"Perfect! I've registered your demo request, {name}. "
            f"Our team will reach out to {email} within 24 hours to confirm your demo. "
            f"We'll aim to match your preference of {preferred_time}. "
            "Is there anything else I can help you with?"
        )
