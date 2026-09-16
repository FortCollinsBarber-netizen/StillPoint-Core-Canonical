from __future__ import annotations

from ..contracts.models import ActionRequest, ActionResult
from .base import NullActionAdapter


class ActionAdapterRegistry:
    def __init__(self, adapters=None):
        self._adapters=[]
        for adapter in adapters or []:
            self.register(adapter)

    def register(self, adapter):
        if not getattr(adapter,"name",""):
            raise ValueError("adapter must have a name")
        if any(a.name==adapter.name for a in self._adapters):
            raise ValueError(f"duplicate adapter: {adapter.name}")
        self._adapters.append(adapter)
        return adapter

    def resolve(self, request: ActionRequest):
        for adapter in self._adapters:
            if (
                request.action_type in getattr(adapter,"action_types",())
                and adapter.can_execute(request)
            ):
                return adapter
        return NullActionAdapter()

    def execute_resolved(self, request: ActionRequest, adapter) -> ActionResult:
        """Execute the exact adapter already selected at the durable boundary.

        This prevents a second dynamic resolve from choosing a different executor
        after the database records which adapter is about to act.
        """
        if not getattr(adapter, "name", ""):
            raise ValueError("resolved adapter must have a name")
        result = adapter.execute(request)
        if not isinstance(result, ActionResult):
            raise TypeError("action adapter must return ActionResult")
        if result.action_id != request.action_id:
            raise ValueError("action result does not match the requested action")
        # Audit identity comes from the selected executor, never self-report.
        result.adapter = adapter.name
        return result

    def execute(self, request: ActionRequest) -> ActionResult:
        adapter = self.resolve(request)
        return self.execute_resolved(request, adapter)


class DryRunActionAdapter:
    name="dry_run"
    action_types=(
        "send_email","publish","social_post","export_artifact","spend","sign","delete","other_external"
    )

    def can_execute(self,request):
        return True

    def execute(self,request):
        # Dispatch wiring only. Not external evidence.
        return ActionResult(
            action_id=request.action_id,
            status="succeeded",
            evidence=[],
            adapter=self.name,
            external_id="dry-run",
        )
