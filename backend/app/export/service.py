import uuid
import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.export.models import ExportRequest, ExportFormat, ExportResult
from app.analysis.repository import AnalysisRepository
from app.character.repository import CharacterRepository
from app.world.repository import WorldRepository
from app.story.repository import StoryRepository


class ExportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def export(self, project_id, request: ExportRequest) -> ExportResult:
        package = {}
        if request.include_analysis:
            analysis = await AnalysisRepository(self.db).get_latest_analysis(project_id)
            if analysis:
                package["analysis"] = analysis
        if request.include_characters:
            characters = await CharacterRepository().get_characters(project_id)
            if characters:
                package["characters"] = characters
        if request.include_world:
            world = await WorldRepository().get_world_graph(project_id)
            if world:
                package["world"] = world
        if request.include_story:
            story = await StoryRepository().get_story(project_id)
            if story:
                package["story_data"] = story
            beats = await StoryRepository().get_beats(project_id)
            if beats:
                package["story_beats"] = beats
        if request.format == ExportFormat.MARKDOWN:
            content = self._to_markdown(package)
            return ExportResult(content=content, filename=f"story_{project_id}.md", mime_type="text/markdown")
        content = json.dumps(package, ensure_ascii=False, indent=2, default=str)
        return ExportResult(content=content, filename=f"story_{project_id}.json", mime_type="application/json")

    def _to_markdown(self, package: dict) -> str:
        lines = ["# Story Export\n"]
        if "analysis" in package:
            lines.append("## Analysis\n")
            meta = package["analysis"].get("metadata", {})
            if meta:
                lines.append(f"- **High Concept:** {meta.get('core_high_concept', '')}\n")
                lines.append(f"- **Protagonist:** {meta.get('protagonist_identity', '')}\n")
                lines.append(f"- **Core Conflict:** {meta.get('core_conflict', '')}\n")
                lines.append(f"- **Tone:** {meta.get('tone_and_length', '')}\n")
                lines.append(f"- **World/Genre:** {meta.get('world_genre', '')}\n")
        if "characters" in package:
            lines.append("## Characters\n")
            for c in package["characters"]:
                lines.append(f"### {c.get('name', 'Unknown')} ({c.get('role', '')})\n")
                desc = c.get("description", "") or c.get("backstory", "")
                if desc:
                    lines.append(f"{desc}\n")
        if "world" in package:
            lines.append("## World\n")
            for loc in package["world"].get("locations", []):
                lines.append(f"- **{loc.get('name')}**: {loc.get('description', '')}\n")
            for fac in package["world"].get("factions", []):
                lines.append(f"- **{fac.get('name')}**: {fac.get('ideology', '')}\n")
        if "story_data" in package:
            lines.append("## Story Structure\n")
            lines.append(f"{json.dumps(package['story_data'], indent=2, default=str)}\n")
        return "\n".join(lines)
