import json
import logging
from app.agents.base import run_agent
from app.character.models import CharacterDesignResult

logger = logging.getLogger(__name__)

SOUL_ARCHITECT_PROMPT = """You are a Creative Completer and Character Designer.

Tasks:
1. Fill gaps in the analysis - provide 2-3 options for fatal missing elements
2. Generate Logline: Protagonist + dilemma + action + opposition + stakes
3. Extract core theme: The deep question the story explores
4. Design complete character profiles (desire topology bottom line weakness language genes growth arc)
5. Build relationship matrix between characters

Output JSON with fields: logline, core_theme, characters array, relationships array, pending_choices array."""


def _normalize_character_result(result: dict) -> dict:
    if not isinstance(result, dict):
        return {}
    # Characters
    chars = []
    for ch in (result.get("characters") or []):
        if isinstance(ch, str):
            chars.append({"name": ch, "role": "supporting"})
        elif isinstance(ch, dict):
            ch.setdefault("name", ch.pop("character_name", ch.pop("character", "unknown")))
            dt = ch.get("desire_topology")
            if isinstance(dt, str):
                ch["desire_topology"] = {"surface_desire": dt}
            chars.append(ch)
    result["characters"] = chars
    # Relationships
    rels = []
    for r in (result.get("relationships") or []):
        if isinstance(r, dict):
            r.setdefault("from_name", r.pop("from", r.pop("source", r.pop("character1", ""))))
            r.setdefault("to_name", r.pop("to", r.pop("target", r.pop("character2", ""))))
            rels.append(r)
    result["relationships"] = rels
    # Pending choices
    pc = result.get("pending_choices")
    if isinstance(pc, list):
        result["pending_choices"] = [
            {"choice": c} if isinstance(c, str) else c
            for c in pc if isinstance(c, (str, dict))
        ]
    else:
        result["pending_choices"] = []
    return result


async def design_characters(metadata: dict) -> CharacterDesignResult:
    try:
        result = run_agent(
            [("system", SOUL_ARCHITECT_PROMPT), ("user", "Metadata:\n{json_data}")],
            {"json_data": json.dumps(metadata, ensure_ascii=False)},
            temperature=0.4
        )
        if isinstance(result, dict):
            result = _normalize_character_result(result)
        return CharacterDesignResult(**result)
    except Exception as e:
        logger.error(f"Soul Architect failed: {e}")
        if isinstance(result, dict):
            try:
                fallback = {
                    "logline": result.get("logline", ""),
                    "core_theme": result.get("core_theme", ""),
                    "characters": result.get("characters", []),
                    "relationships": [],
                    "pending_choices": [],
                }
                return CharacterDesignResult(**fallback)
            except Exception:
                pass
        return CharacterDesignResult()