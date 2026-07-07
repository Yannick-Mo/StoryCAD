import json
from .types import ModelDef

_registry: dict[str, ModelDef] = {}


def register(name: str, model: ModelDef) -> None:
    _registry[name] = model


def get(name: str) -> ModelDef:
    if name not in _registry:
        raise KeyError(f"Model '{name}' is not registered")
    return _registry[name]


def get_default() -> ModelDef:
    return get("deepseek-chat")


def list_models() -> dict[str, ModelDef]:
    return dict(_registry)


def configure_from_settings(settings) -> None:
    api_key = settings.llm_api_key
    base_url = settings.llm_base_url.rstrip("/")
    model_name = settings.llm_model

    register(
        "deepseek-chat",
        ModelDef(
            api_key=api_key,
            base_url=base_url,
        ),
    )

    extra = getattr(settings, "llm_models", None)
    if extra:
        if isinstance(extra, str):
            extra = json.loads(extra)
        for name, cfg in extra.items():
            register(
                name,
                ModelDef(
                    api_key=cfg.get("api_key", api_key),
                    base_url=cfg.get("base_url", base_url),
                    supports_streaming=cfg.get("supports_streaming", True),
                    supports_fc=cfg.get("supports_fc", True),
                    max_tokens=cfg.get("max_tokens", 8192),
                    cost_per_1k_input=cfg.get("cost_per_1k_input", 0.0001),
                    cost_per_1k_output=cfg.get("cost_per_1k_output", 0.0002),
                ),
            )
