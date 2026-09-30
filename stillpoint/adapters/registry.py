from __future__ import annotations

from ..contracts.models import ActionRequest, ActionResult
from .base import NullActionAdapter


class ActionAdapterRegistry:
    def __init__(self, adapters=None):
        self._adapters=[]
        self._acquired={}
        for adapter in adapters or []:
            self.register(adapter)

    def _register_static(self, adapter):
        if not getattr(adapter,"name",""):
            raise ValueError("adapter must have a name")
        if any(a.name==adapter.name for a in self._adapters):
            raise ValueError(f"duplicate adapter: {adapter.name}")
        self._adapters.append(adapter)
        return adapter

    def register(self, adapter):
        """Register a statically configured adapter.

        Dynamically acquired executors must not become runnable merely because
        Python code obtained an object reference.  Those adapters must enter
        through register_acquired(), which proves a current activation binding.
        """
        if getattr(adapter,"acquired_resource_id",None):
            raise ValueError("acquired adapter requires register_acquired()")
        return self._register_static(adapter)

    def register_acquired(self, adapter, custody, *, resource_id=None, now_iso=None):
        rid=str(resource_id or getattr(adapter,"acquired_resource_id","")).strip()
        if not rid:
            raise ValueError("acquired adapter requires resource id")
        action_types=tuple(getattr(adapter,"action_types",()) or ())
        if not action_types:
            raise ValueError("acquired adapter requires action_types")
        for action_type in action_types:
            custody.assert_usable(rid,action_type,now_iso=now_iso)
        registered=self._register_static(adapter)
        self._acquired[registered.name]=(custody,rid)
        return registered

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
        after the database records which adapter is about to act. Acquired
        executors revalidate their activation at this last pre-effect boundary.
        One-shot acquired resources are consumed before adapter execution so
        crash/retry cannot resurrect their authority.
        """
        if not getattr(adapter, "name", ""):
            raise ValueError("resolved adapter must have a name")

        acquired=self._acquired.get(adapter.name)
        if acquired is not None:
            custody,rid=acquired
            resource=custody.get(rid)
            if resource.one_shot:
                custody.reserve_one_shot_use(rid,request.action_type)
            else:
                custody.assert_usable(rid,request.action_type)

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
