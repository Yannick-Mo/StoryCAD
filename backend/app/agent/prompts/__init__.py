from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import jinja2
from loguru import logger

_PROMPT_DIR = Path(__file__).parent


class _PreservingUndefined(jinja2.Undefined):
    """Jinja2 undefined that preserves the original {{placeholder}} syntax.

    Unlike DebugUndefined (which adds spaces), this renders undefined
    variables as {{name}} (no spaces around the name), matching the
    behavior of the previous custom template engine. This allows
    downstream code to detect and warn about unresolved placeholders.
    """

    def __str__(self) -> str:
        return "{{" + self._undefined_name + "}}"

    def __eq__(self, other: object) -> bool:
        return False

    def __ne__(self, other: object) -> bool:
        return True

    __bool__ = __nonzero__ = lambda self: False  # type: ignore[assignment]


class PromptTemplate:
    """Jinja2-based template renderer for prompt files."""

    def __init__(self, template: str):
        env = jinja2.Environment(
            undefined=_PreservingUndefined,
            autoescape=False,
            keep_trailing_newline=True,
        )
        # Custom filter for slice syntax not natively supported by Jinja2 loops.
        # Usage: {% for item in items|take(5) %} instead of items[:5]
        env.filters["take"] = (
            lambda value, n: value[:n] if isinstance(value, (list, tuple)) else value
        )
        self._template = env.from_string(template)

    def render(self, **kwargs: Any) -> str:
        result = self._template.render(**kwargs)

        dangling = re.findall(r"\{\{.+?\}\}", result)
        if dangling:
            for d in dangling[:5]:
                logger.warning("Unresolved template placeholder: {}", d)

        return result


class PromptLoader:
    def __init__(self):
        self._cache: dict[str, PromptTemplate] = {}

    def load(self, name: str) -> PromptTemplate | None:
        if name in self._cache:
            return self._cache[name]
        path = _PROMPT_DIR / f"{name}.yaml"
        if not path.exists():
            return None
        import yaml

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data or "system" not in data:
            return None
        tpl = PromptTemplate(data["system"])
        self._cache[name] = tpl
        return tpl

    def render(self, name: str, **kwargs: Any) -> str | None:
        tpl = self.load(name)
        if tpl is None:
            return None
        return tpl.render(**kwargs)


_global_loader = PromptLoader()


def get_prompt_loader() -> PromptLoader:
    return _global_loader


def render_prompt(name: str, **kwargs: Any) -> str | None:
    return _global_loader.render(name, **kwargs)
