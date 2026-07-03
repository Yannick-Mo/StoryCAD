import json
import logging
from app.agents.base import run_agent
from app.analysis.models import AnalysisResult, SixDimMetadata, MissingDiagnosis

logger = logging.getLogger(__name__)

ANALYSIS_AGENT_PROMPT = """You are a narrative analysis expert using the \"Six-Dimension Information Extraction Model\".

Extract structured information from the user's raw input organized by priority.

Tier 1 (Rigid Anchors):
- core_high_concept: Unique selling point in one sentence
- protagonist_identity: Protagonist identity and core obsession
- core_conflict: Main goal obstacles antagonist
- non_negotiable_events: Key events user explicitly mentioned
- tone_and_length: Tone (dark/light/suspenseful) and length

Tier 2 (Skeleton Info):
- world_genre: World rules (era power system social structure)
- main_characters: list of {{name role trait motivation}}
- core_relationships: list of {{from to type description}}

Tier 3 (Filler Info):
- landmark_scenes: Signature scenes
- subplot_hints: Subplot clues
- style_details: Style details

Generate missing_diagnosis as array of objects with fields: field (string), severity ("fatal"/"serious"/"suggestion"), description (string), suggestion (string).

Output JSON with \"metadata\" and \"missing_diagnosis\" arrays."""


async def run_analysis(raw_input: dict) -> AnalysisResult:
    try:
        result = run_agent(
            [("system", ANALYSIS_AGENT_PROMPT), ("user", "Raw input:\n{raw_json}")],
            {"raw_json": json.dumps(raw_input, ensure_ascii=False)},
            temperature=0.3
        )
        meta_data = result.get("metadata", {})
        for key in ("tone_and_length", "world_genre", "style_details", "core_high_concept", "protagonist_identity", "core_conflict"):
            if isinstance(meta_data.get(key), (dict, list)):
                meta_data[key] = str(meta_data[key])
        metadata = SixDimMetadata(**meta_data)
        raw_diag = result.get("missing_diagnosis", [])
        diagnosis = []
        for d in raw_diag:
            try:
                diagnosis.append(MissingDiagnosis(**d))
            except Exception:
                pass
        return AnalysisResult(metadata=metadata, missing_diagnosis=diagnosis, raw_input=raw_input)
    except Exception as e:
        logger.error(f"Analysis agent failed: {e}")
        return AnalysisResult(raw_input=raw_input)
