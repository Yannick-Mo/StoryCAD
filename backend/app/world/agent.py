import json
import logging
from app.agents.base import run_agent
from app.world.models import WorldDesignResult

logger = logging.getLogger(__name__)

WORLD_BUILDER_PROMPT = """You are a World Builder — a narrative world architect.

Build a complete story world from the analysis metadata. Generate:
1. World logline: The world in one sentence
2. Locations: key locations with description type significance connections
3. Factions: factions with ideology power_structure goals allies enemies
4. World rules: domain description constraints exceptions
5. Timeline: key historical events

Output JSON with: world_name, logline, locations array, factions array, rules array, timeline array, pending_choices array."""


async def build_world(metadata: dict) -> WorldDesignResult:
    try:
        result = run_agent(
            [("system", WORLD_BUILDER_PROMPT), ("user", "Metadata:\n{json_data}")],
            {"json_data": json.dumps(metadata, ensure_ascii=False)},
            temperature=0.4
        )
        return WorldDesignResult(**result)
    except Exception as e:
        logger.error(f"World Builder failed: {e}")
        return WorldDesignResult()
