from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock

from .registry import get as _get_model


@dataclass
class UsageRecord:
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    timestamp: datetime
    session_id: str = ""


class TokenTracker:
    def __init__(self):
        self._records: list[UsageRecord] = []
        self._lock = Lock()

    def track(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        session_id: str = "",
    ) -> UsageRecord:
        try:
            model_def = _get_model(model)
            cost = (
                model_def.cost_per_1k_input * prompt_tokens / 1000
                + model_def.cost_per_1k_output * completion_tokens / 1000
            )
        except KeyError:
            cost = 0.0

        record = UsageRecord(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost=cost,
            timestamp=datetime.now(),
            session_id=session_id,
        )
        with self._lock:
            self._records.append(record)
        return record

    def get_session_total(self, session_id: str) -> dict:
        prompt = 0
        completion = 0
        total = 0
        cost = 0.0
        with self._lock:
            for r in self._records:
                if r.session_id == session_id:
                    prompt += r.prompt_tokens
                    completion += r.completion_tokens
                    total += r.total_tokens
                    cost += r.cost
        return {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": total,
            "cost": round(cost, 6),
        }

    def get_global_total(self) -> dict:
        prompt = 0
        completion = 0
        total = 0
        cost = 0.0
        with self._lock:
            for r in self._records:
                prompt += r.prompt_tokens
                completion += r.completion_tokens
                total += r.total_tokens
                cost += r.cost
        return {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": total,
            "cost": round(cost, 6),
        }

    def reset(self) -> None:
        with self._lock:
            self._records.clear()
