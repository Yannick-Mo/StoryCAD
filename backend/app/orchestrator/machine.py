import uuid
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.orchestrator.models import StoryPhase, WorkflowState
from app.analysis.service import AnalysisService
from app.character.service import CharacterService
from app.world.service import WorldService
from app.story.service import StoryService
from app.validation.service import ValidationService
from app.project.repository import ProjectRepository

logger = logging.getLogger(__name__)


class OrchestratorMachine:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.state: Optional[WorkflowState] = None

    async def initialize(self, project_id: uuid.UUID) -> WorkflowState:
        state = WorkflowState(project_id=str(project_id))
        await self._save_state(project_id, state)
        self.state = state
        return state

    async def get_state(self, project_id: uuid.UUID) -> Optional[WorkflowState]:
        versions = await self.project_repo.get_versions(project_id)
        for v in versions:
            snapshot = v.snapshot or {}
            if "orchestrator" in snapshot:
                return WorkflowState(**snapshot["orchestrator"])
        return None

    async def run_full_workflow(self, project_id: uuid.UUID, raw_input: dict) -> dict:
        self.state = await self.get_state(project_id) or await self.initialize(project_id)
        results = {}
        if self.state.current_phase == StoryPhase.ANALYSIS:
            service = AnalysisService(self.db)
            results["analysis"] = await service.analyze(project_id, raw_input)
            self.state.completed_phases.append("analysis")
            self.state.phase_results["analysis"] = results["analysis"]
            self.state.current_phase = StoryPhase.CHARACTER
            await self._save_state(project_id, self.state)
        if self.state.current_phase == StoryPhase.CHARACTER:
            service = CharacterService(self.db)
            results["characters"] = await service.generate_characters(project_id)
            self.state.completed_phases.append("character")
            self.state.phase_results["characters"] = results["characters"]
            self.state.current_phase = StoryPhase.WORLD
            await self._save_state(project_id, self.state)
        if self.state.current_phase == StoryPhase.WORLD:
            service = WorldService(self.db)
            results["world"] = await service.generate_world(project_id)
            self.state.completed_phases.append("world")
            self.state.phase_results["world"] = results["world"]
            self.state.current_phase = StoryPhase.STORY
            await self._save_state(project_id, self.state)
        if self.state.current_phase == StoryPhase.STORY:
            service = StoryService(self.db)
            results["story"] = await service.generate_story(project_id)
            self.state.completed_phases.append("story")
            self.state.phase_results["story"] = results["story"]
            self.state.current_phase = StoryPhase.VALIDATION
            await self._save_state(project_id, self.state)
        if self.state.current_phase == StoryPhase.VALIDATION:
            service = ValidationService(self.db)
            results["validation"] = await service.validate(project_id)
            self.state.completed_phases.append("validation")
            self.state.phase_results["validation"] = results["validation"]
            self.state.current_phase = StoryPhase.COMPLETE
            self.state.status = "completed"
            await self._save_state(project_id, self.state)
        return results

    async def _save_state(self, project_id: uuid.UUID, state: WorkflowState):
        await self.project_repo.save_version(project_id, {"orchestrator": state.model_dump()})
