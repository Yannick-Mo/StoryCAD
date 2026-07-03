import json
import logging
from app.agents.base import run_agent
from app.validation.models import ValidationResult

logger = logging.getLogger(__name__)

VALIDATOR_PROMPT = """You are a Narrative Consistency Validator. Review the complete story package for consistency.

Check the following categories:
1. Character consistency: Do characters act according to their established desires/bottom lines?
2. World rule consistency: Are world rules followed throughout?
3. Plot causality: Do events flow logically from cause to effect?
4. Timeline consistency: Is the timeline coherent?
5. Theme alignment: Does everything serve the core theme?

For each issue found: category, severity (critical/warning/suggestion), element, description, suggestion.
Run consistency checks and score overall.

Output JSON with: overall_score (0-100), issues array, consistency_checks array, missing_elements array, recommendations array."""


async def validate_story(story_package: dict) -> ValidationResult:
    try:
        result = run_agent(
            [("system", VALIDATOR_PROMPT), ("user", "Story package:\n{json_data}")],
            {"json_data": json.dumps(story_package, ensure_ascii=False)},
            temperature=0.2
        )
        return ValidationResult(**result)
    except Exception as e:
        logger.error(f"Validator agent failed: {e}")
        return ValidationResult()
