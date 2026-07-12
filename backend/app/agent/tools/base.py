from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.client import LLMClient


# ---------------------------------------------------------------------------
# New types for the Tool Factory Pattern + Concurrency Safety
# ---------------------------------------------------------------------------

class ConcurrencyMode(str, Enum):
    """Controls how a tool interacts with concurrent executions."""
    SAFE = "safe"          # Can run in parallel with other SAFE tools
    EXCLUSIVE = "exclusive"  # Must run alone (write operations)
    BARRIER = "barrier"    # Must wait for all others to complete first


@dataclass
class ToolMeta:
    """Immutable metadata describing a tool's capabilities and constraints."""
    name: str
    description: str
    parameters: dict = field(default_factory=dict)
    concurrency: ConcurrencyMode = ConcurrencyMode.EXCLUSIVE
    is_destructive: bool = False  # Irreversible operations (delete, overwrite, send)
    needs_confirmation: bool = False  # Must get user approval before execution
    timeout: int = 30  # Seconds
    max_result_chars: int = 8000  # Truncate results beyond this
    search_hint: str = ""  # 3-10 words for keyword matching


# ---------------------------------------------------------------------------
# ToolResult (unchanged)
# ---------------------------------------------------------------------------

@dataclass
class ToolResult:
    success: bool = True
    data: Any = None
    error: str | None = None

    def to_dict(self) -> dict:
        return {"success": self.success, "data": self.data, "error": self.error}


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

async def verify_project_owner(
    db: AsyncSession, project_id, user_id: str | None
) -> None:
    if user_id is None:
        return
    from app.project.models import Project
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    )
    if not result.scalar_one_or_none():
        raise PermissionError(
            f"User {user_id} does not own project {project_id}"
        )


# ---------------------------------------------------------------------------
# BaseTool
# ---------------------------------------------------------------------------

class BaseTool(ABC):
    """Abstract base for every agent tool.

    Each subclass SHOULD set ``meta`` to a :class:`ToolMeta` instance.
    For backwards compatibility the legacy flat attributes (``name``,
    ``description``, ``parameters``, ``is_write_operation``) are still
    honoured — they are proxied through ``meta`` when it exists.

    Hook methods (validate_input, on_before_run, on_after_run, inputs_equivalent)
    can be overridden by subclasses to control execution lifecycle.
    """

    # ------------------------------------------------------------------
    # Meta (new — subclasses should set this)
    # ------------------------------------------------------------------
    meta: ToolMeta | None = None

    # ------------------------------------------------------------------
    # Legacy flat attributes (kept for backwards compatibility)
    # ------------------------------------------------------------------
    name: str = ""
    description: str = ""
    parameters: dict = {}
    is_write_operation: bool = False
    llm_client: LLMClient | None = None

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client

    # ------------------------------------------------------------------
    # Property-like accessors — prefer meta when available
    # ------------------------------------------------------------------

    @property
    def _effective_name(self) -> str:
        if self.meta is not None and self.meta.name:
            return self.meta.name
        return self.name

    @property
    def _effective_description(self) -> str:
        if self.meta is not None and self.meta.description:
            return self.meta.description
        return self.description

    @property
    def _effective_parameters(self) -> dict:
        if self.meta is not None and self.meta.parameters:
            return self.meta.parameters
        return self.parameters

    @property
    def _effective_concurrency(self) -> ConcurrencyMode:
        if self.meta is not None:
            return self.meta.concurrency
        # Fallback: use is_write_operation as heuristic
        return ConcurrencyMode.EXCLUSIVE if self.is_write_operation else ConcurrencyMode.SAFE

    @property
    def _effective_is_destructive(self) -> bool:
        if self.meta is not None:
            return self.meta.is_destructive
        return False

    @property
    def _effective_timeout(self) -> int:
        if self.meta is not None:
            return self.meta.timeout
        return 30

    @property
    def _effective_max_result_chars(self) -> int:
        if self.meta is not None:
            return self.meta.max_result_chars
        return 8000

    @property
    def _effective_search_hint(self) -> str:
        if self.meta is not None:
            return self.meta.search_hint
        return ""

    # ------------------------------------------------------------------
    # Core abstract method
    # ------------------------------------------------------------------

    @abstractmethod
    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        """Execute the tool.  Subclasses MUST implement this."""
        ...

    # ------------------------------------------------------------------
    # Hook methods (override in subclasses)
    # ------------------------------------------------------------------

    async def validate_input(self, args: dict) -> tuple[bool, str]:
        """Validate input arguments BEFORE execution.

        Returns ``(True, "")`` when valid, or ``(False, "<reason>")`` otherwise.
        The default implementation always passes.
        """
        return True, ""

    async def on_before_run(self, args: dict, db: AsyncSession) -> None:
        """Called immediately before ``run()``.

        Can be used for logging, audit trails, or short-lived locks.
        """
        pass

    async def on_after_run(
        self, result: ToolResult, args: dict, db: AsyncSession
    ) -> None:
        """Called immediately after ``run()`` (even on failure).

        Can be used for cleanup, cache invalidation, or metric emission.
        """
        pass

    def inputs_equivalent(self, a: dict, b: dict) -> bool:
        """Return True when two sets of arguments are considered identical.

        Used by deduplication logic (e.g. the plan node).  The default
        returns ``False`` (never deduplicate) — subclasses should override
        for idempotent tools.
        """
        return False

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_openai_tool(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self._effective_name,
                "description": self._effective_description,
                "parameters": self._effective_parameters,
            },
        }
