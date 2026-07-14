# backend/app/agent/prompts/builder.py
# ============================================================================
# SystemPromptBuilder — assembles system prompts from modular, cacheable
# sections defined in system.yaml.
#
# Design:
#   - Static sections (cacheable=true) are pre-rendered once and stored in
#     a process-level cache.  They contain no Jinja2 expressions — only plain
#     text — so they are also "prompt-cache-friendly" for LLM APIs that
#     support prompt caching (e.g. Anthropic's cache_control).
#
#   - Dynamic sections (cacheable=false) are Jinja2 templates that are
#     rendered fresh each time with the current session/project/user context.
#
# Usage:
#     from app.agent.prompts.builder import get_prompt_builder
#
#     builder = get_prompt_builder()
#     prompt = builder.build(["identity", "project_context", "tool_usage"],
#                            title="My Novel", genre="Fantasy", ...)
# ============================================================================
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from app.agent.prompts import PromptTemplate

logger = logging.getLogger(__name__)


class SystemPromptBuilder:
    """Assembles system prompts from modular sections.

    Loads ``system.yaml`` at construction time.  Sections marked
    ``cacheable: true`` are pre-rendered statically (no template processing)
    and reused.  Sections marked ``cacheable: false`` are rendered via
    Jinja2 for each invocation.

    The singleton returned by :func:`get_prompt_builder` should be used
    throughout the application.
    """

    def __init__(self) -> None:
        self._yaml_path = Path(__file__).parent / "system.yaml"
        with open(self._yaml_path, encoding="utf-8") as f:
            self._sections: dict[str, dict[str, Any]] = yaml.safe_load(f) or {}

        # Static cache: section_name -> plain-text content
        self._static_cache: dict[str, str] = {}

        # Template cache: section_name -> PromptTemplate (Jinja2)
        self._template_cache: dict[str, PromptTemplate] = {}

        self._hydrate_caches()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _hydrate_caches(self) -> None:
        """Pre-load all sections into the appropriate cache."""
        for name, section in self._sections.items():
            if not isinstance(section, dict):
                logger.warning("system.yaml: section '%s' is not a dict — skipping", name)
                continue

            if section.get("cacheable", False):
                content = section.get("content", "")
                self._static_cache[name] = content.strip()
            else:
                template_text = section.get("template", "")
                if template_text:
                    try:
                        self._template_cache[name] = PromptTemplate(template_text)
                    except Exception:
                        logger.exception(
                            "Failed to compile template for section '%s'", name
                        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_static_section(self, name: str) -> str:
        """Return a pre-rendered static section.

        Returns an empty string if the section does not exist, is not
        marked cacheable, or has not been loaded successfully.
        """
        return self._static_cache.get(name, "")

    def render_dynamic_section(self, name: str, **kwargs: Any) -> str:
        """Render a dynamic section with the given keyword arguments.

        Unknown or undefined variables trigger warnings (via
        ``_ReportingUndefined``) but do not raise — they are rendered as
        ``{{variable_name}}`` placeholders in the output.

        Returns an empty string if the section does not exist, is static,
        or the template is missing.
        """
        tpl: PromptTemplate | None = self._template_cache.get(name)
        if tpl is None:
            # Maybe it is a static section being called as dynamic
            static = self._static_cache.get(name)
            if static:
                return static
            logger.warning("No template found for dynamic section '%s'", name)
            return ""
        try:
            return tpl.render(**kwargs)
        except Exception:
            logger.exception("Failed to render dynamic section '%s'", name)
            return ""

    def build(
        self,
        sections: list[str],
        sep: str = "\n\n",
        **context: Any,
    ) -> str:
        """Build a complete system prompt from the *ordered* list of
        section names.

        For each name in *sections*:

        * If the section is ``cacheable: true``, emit the statically-cached
          content (no template variables are substituted).
        * If the section is ``cacheable: false``, render the Jinja2 template
          with the provided *context*.

        Sections not found in ``system.yaml`` are silently skipped so that
        callers can safely request optional sections.

        Args:
            sections: Ordered list of section names to include.
            sep: Separator between sections (default: double newline).
            **context: Keyword arguments forwarded to dynamic section
                       templates.
        """
        parts: list[str] = []
        for name in sections:
            section_def = self._sections.get(name)
            if not section_def:
                logger.debug("build: section '%s' not found — skipping", name)
                continue

            if section_def.get("cacheable", False):
                chunk = self.get_static_section(name)
            else:
                chunk = self.render_dynamic_section(name, **context)

            if chunk:
                parts.append(chunk)

        return sep.join(parts)

    def build_array(
        self,
        sections: list[str],
        **context: Any,
    ) -> list[str]:
        """Build system prompt as an ordered array of section strings.

        Sections marked ``_marker: true`` (e.g. ``dynamic_boundary``) act as
        cache-split points — callers can use these to apply different cache
        scopes to static vs dynamic portions.

        Returns a list where each element is one section's rendered content
        (empty-string sections from markers are excluded).
        """
        parts: list[str] = []
        for name in sections:
            section_def = self._sections.get(name)
            if not section_def:
                logger.debug("build_array: section '%s' not found — skipping", name)
                continue

            if section_def.get("_marker", False):
                # Marker sections are cache-split signals — emit empty string
                # so callers can detect the boundary position in the array.
                parts.append("")
                continue

            if section_def.get("cacheable", False):
                chunk = self.get_static_section(name)
            else:
                chunk = self.render_dynamic_section(name, **context)

            if chunk:
                parts.append(chunk)

        return parts

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def section_names(self) -> list[str]:
        """Return all section names defined in system.yaml."""
        return list(self._sections.keys())

    @property
    def cacheable_sections(self) -> list[str]:
        """Return names of sections marked cacheable."""
        return [k for k, v in self._sections.items()
                if isinstance(v, dict) and v.get("cacheable", False)]

    @property
    def dynamic_sections(self) -> list[str]:
        """Return names of sections marked non-cacheable."""
        return [k for k, v in self._sections.items()
                if isinstance(v, dict) and not v.get("cacheable", False)]


# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------

_builder: SystemPromptBuilder | None = None


def get_prompt_builder() -> SystemPromptBuilder:
    """Return the process-global :class:`SystemPromptBuilder` singleton.

    The YAML file is parsed once; static sections are cached forever.
    """
    global _builder
    if _builder is None:
        _builder = SystemPromptBuilder()
    return _builder
