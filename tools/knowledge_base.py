import json
import os
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent / "data"


def load_knowledge(filename: str) -> str:
    """Load a JSON knowledge file and return it as a formatted string for LLM injection."""
    path = _DATA_DIR / filename
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return _format_dict(data, indent=0)


def _format_dict(obj, indent: int) -> str:
    """Recursively format a JSON object into readable plain text."""
    lines = []
    prefix = "  " * indent

    if isinstance(obj, dict):
        for key, value in obj.items():
            label = key.replace("_", " ").title()
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}{label}:")
                lines.append(_format_dict(value, indent + 1))
            else:
                lines.append(f"{prefix}{label}: {value}")
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                lines.append(_format_dict(item, indent))
                lines.append("")
            else:
                lines.append(f"{prefix}- {item}")
    else:
        lines.append(f"{prefix}{obj}")

    return "\n".join(lines)
