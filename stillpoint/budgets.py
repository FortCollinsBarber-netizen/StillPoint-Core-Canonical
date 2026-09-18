from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


class BudgetExceeded(RuntimeError):
    pass


@dataclass(frozen=True)
class BudgetLimits:
    max_model_calls: int | None = None
    max_tool_calls: int | None = None
    max_total_tokens: int | None = None
    max_elapsed_seconds: float | None = None
    max_cost_usd: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


_TOOL_CALL_OUTPUT_TYPES = frozenset({
    "function_call",
    "web_search_call",
    "x_search_call",
    "code_interpreter_call",
    "file_search_call",
    "mcp_call",
    "image_generation_call",
})


def observe_tool_invocations(result: Any, *, tool_offers: int) -> tuple[int, bool]:
    """Return (observed invocations, evidence complete enough to trust zero).

    xAI Responses API exposes server-side tool calls as output items. Other
    providers may expose a successful-tool count in usage. If tools were
    offered but neither surface exists, invocation count is unknown rather
    than silently assumed to be zero.
    """

    if int(tool_offers or 0) == 0:
        return 0, True
    if result is None:
        return 0, False

    raw = getattr(result, "raw", None)
    if isinstance(raw, dict):
        output = raw.get("output")
        if isinstance(output, list):
            count = sum(
                1
                for item in output
                if isinstance(item, dict)
                and str(item.get("type") or "") in _TOOL_CALL_OUTPUT_TYPES
            )
            return count, True

        usage_map = raw.get("server_side_tool_usage")
        if isinstance(usage_map, dict):
            values = [v for v in usage_map.values() if isinstance(v, int) and v >= 0]
            if len(values) == len(usage_map):
                return sum(values), True

    usage = getattr(result, "usage", None)
    if isinstance(usage, dict):
        count = usage.get("num_server_side_tools_used")
        if isinstance(count, int) and count >= 0:
            return count, True

    return 0, False


class BudgetedProviderProxy:
    def __init__(self, provider, *, task_id_getter, before_call, after_call):
        self._provider = provider
        self._task_id_getter = task_id_getter
        self._before_call = before_call
        self._after_call = after_call

    def __getattr__(self, name):
        return getattr(self._provider, name)

    def generate(self, **kwargs):
        task_id = kwargs.get("task_id") or self._task_id_getter()
        tools = kwargs.get("tools") or []
        tool_offers = len(tools)
        if task_id:
            self._before_call(task_id, tool_offers=tool_offers)
        result = None
        try:
            result = self._provider.generate(**kwargs)
            return result
        finally:
            if task_id:
                usage = getattr(result, "usage", None) if result is not None else None
                tool_invocations, invocation_known = observe_tool_invocations(
                    result,
                    tool_offers=tool_offers,
                )
                self._after_call(
                    task_id,
                    result=result,
                    usage=usage or {},
                    tool_offers=tool_offers,
                    tool_invocations=tool_invocations,
                    tool_invocations_known=invocation_known,
                )
