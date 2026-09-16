from __future__ import annotations
import hashlib,json
from datetime import datetime,timezone,timedelta
from pathlib import Path
from .attachments import select_attachment_context
from .budgets import BudgetExceeded, BudgetLimits, BudgetedProviderProxy
from .capabilities import capabilities_for_call
from .contracts.models import ActionEvidence,ActionRequest,ActionResult,ArtifactRef
from .providers.base import IncompleteResponseError, InProgressResponseError
from .adapters.base import NotAuthorized, runtime_complete
from .db import CompanyDB
from .file_loader import import_attachment,read_attachment
from .models import TaskOutcome,TaskStatus,WorkPlan
from .phases import fingerprint,stage_key
from .planner import Planner
from .policy import CompanyPolicy
from .prompts import agent_system_prompt,review_prompt,task_prompt
from .registry import AgentRegistry
from .temporal.action_gate import build_ceo_warrant, validate_bound_warrant
from .temporal.firewall import TemporalAuthorityError

def _sha_text(text:str)->str:return hashlib.sha256(text.encode("utf-8")).hexdigest()
def _now_dt():return datetime.now(timezone.utc)

class CompanyRuntime:
    def __init__(self,*,root:Path,db:CompanyDB,registry:AgentRegistry,provider,default_model:str,smart_routing:bool=True,allowed_import_roots=None,default_budget:BudgetLimits|None=None):
        self.root=root;self.db=db;self.registry=registry;self.default_model=default_model
        self.raw_provider=provider;self._active_task_id=None;self.default_budget=default_budget
        self.provider=BudgetedProviderProxy(provider,task_id_getter=lambda:self._active_task_id,before_call=self._budget_before_call,after_call=self._budget_after_call)
        self.policy=CompanyPolicy(provider=self.provider,authority_model=default_model)
        self.planner=Planner(registry,self.policy,self.provider,default_model,smart=smart_routing)
        self.managed_files=root/"state"/"managed_files"
        self.allowed_import_roots=[Path(r).resolve() for r in (allowed_import_roots or [root])]
    def _budget_before_call(self,task_id,*,tool_count=0):
        budget=self.db.get_task_budget(task_id)
        if not budget:return
        usage=self.db.get_task_usage(task_id)
        task=self.db.get_task(task_id) or {}
        def hit(limit,current,prospective=0): return limit is not None and current+prospective>limit
        if hit(budget.get("max_model_calls"),usage.get("model_calls",0),1):raise BudgetExceeded("model-call budget exhausted")
        if hit(budget.get("max_tool_calls"),usage.get("tool_calls",0),tool_count):raise BudgetExceeded("tool-call budget exhausted")
        if budget.get("max_total_tokens") is not None and usage.get("total_tokens",0)>=budget["max_total_tokens"]:raise BudgetExceeded("token budget exhausted")
        if budget.get("max_cost_usd") is not None and usage.get("cost_usd",0.0)>=budget["max_cost_usd"]:raise BudgetExceeded("cost budget exhausted")
        if budget.get("max_elapsed_seconds") is not None and task.get("created_at"):
            try:
                created=datetime.fromisoformat(task["created_at"].replace("Z","+00:00")); elapsed=(_now_dt()-created).total_seconds()
            except Exception: elapsed=0
            if elapsed>=budget["max_elapsed_seconds"]:raise BudgetExceeded("elapsed-time budget exhausted")
    def _budget_after_call(self,task_id,*,usage,tool_count=0):
        total=usage.get("total_tokens") if isinstance(usage,dict) else 0
        if total is None and isinstance(usage,dict):total=(usage.get("input_tokens") or 0)+(usage.get("output_tokens") or 0)
        cost=0.0
        if isinstance(usage,dict):
            for key in ("cost_usd","cost"):
                if isinstance(usage.get(key),(int,float)):
                    cost=float(usage[key]);break
        self.db.add_task_usage(task_id,model_calls=1,tool_calls=tool_count,total_tokens=int(total or 0),cost_usd=cost)
    def _memory_text(self,project):
        scopes=["company"]+([f"project:{project}"] if project else [])
        return "\n".join(f"[{r['scope']}] {r['key']}: {r['value']}" for r in self.db.get_memory(scopes))
    def _fingerprint(self,goal,project,attachments):return fingerprint(goal,project,[(a["name"],a["sha256"]) for a in attachments])
    @staticmethod
    def _canonical_output(result):
        text=result.text
        if getattr(result,"citations",None):text+= "\n\nPROVIDER SOURCE URLS:\n"+"\n".join(f"- {u}" for u in result.citations)
        return text
    def _spec_caps(self,plan,agent_id,phase):
        if phase=="contribution":
            for s in plan.contributor_specs:
                if s.get("id")==agent_id:return list(s.get("capabilities") or [])
            return []
        return list(plan.primary_capabilities or plan.capabilities)
    def _spec_requests(self,plan,agent_id,phase):
        if phase=="contribution":
            for s in plan.contributor_specs:
                if s.get("id")==agent_id:return list(s.get("tool_requests") or [])
            return []
        return list(plan.primary_tool_requests or [])
    def _existing_stage(self,task_id,phase,agent_id,input_fp,legacy_fp=""):
        # Current stages are reused only by exact stage-specific fingerprint.
        key=stage_key(task_id,phase,agent_id=agent_id,input_fingerprint=input_fp)
        row=self.db.get_run_by_stage_key(key)
        if row:
            return row
        # Compatibility for pre-stage-fingerprint checkpoints: those releases stored the
        # task-root fingerprint on every run. Reuse is permitted only when that exact
        # root fingerprint still matches the current instruction/files/project state.
        if legacy_fp:
            legacy_key=stage_key(task_id,phase,agent_id=agent_id,input_fingerprint=legacy_fp)
            row=self.db.get_run_by_stage_key(legacy_key)
            if row:
                return row
            expected="fp:"+legacy_fp
            for candidate in self.db.list_runs(task_id):
                if candidate.get("phase")==phase and candidate.get("agent_id")==agent_id and candidate.get("input_summary")==expected:
                    return candidate
        return None
    def _record_planning(self,task_id,goal,project,planning_output,model_planned,planning_model):
        if not planning_output and not model_planned:
            return
        provenance=getattr(self.planner,"last_provenance",{}) or {}
        phase="planning" if model_planned else "planning_fallback"
        fp=fingerprint(goal,project,"planning")
        self.db.add_run(
            task_id,"orchestra",phase,planning_output or "",model=provenance.get("model") or planning_model,
            input_summary="fp:"+fp,citations=provenance.get("citations") or [],
            provider_response_id=provenance.get("provider_response_id") or "",usage=provenance.get("usage") or {},
            stage_key=stage_key(task_id,phase,agent_id="orchestra",input_fingerprint=fp),
        )

    def _call_agent(self,task_id,agent_id,phase,goal,project,contributions,attachments,plan,*,correction="",input_fp="",legacy_fp=""):
        existing=self._existing_stage(task_id,phase,agent_id,input_fp,legacy_fp)
        if existing:return existing["output"]
        agent=self.registry.get(agent_id);model=agent.model or self.default_model
        selected=select_attachment_context(attachments,goal)
        prompt=task_prompt(goal,project,self._memory_text(project),contributions,selected,correction)
        tools=capabilities_for_call(agent_id=agent_id,plan_capabilities=list(plan.capabilities),agent_capabilities=self._spec_caps(plan,agent_id,phase),review_reason=plan.review_reason,scoped_requests=self._spec_requests(plan,agent_id,phase))
        try:
            result=self.provider.generate(system=agent_system_prompt(agent),prompt=prompt,model=model,tools=tools,task_id=task_id,phase=phase,effort="high" if agent_id in {"author","stillpoint","builder"} else "medium")
        except IncompleteResponseError as exc:
            partial=exc.partial_text or ""
            self.db.add_run(task_id,agent_id,phase+"_incomplete",partial,model=model,input_summary="fp:"+input_fp,provider_response_id=exc.provider_response_id or "",stage_key=stage_key(task_id,phase+"_incomplete",agent_id=agent_id,input_fingerprint=input_fp))
            raise
        except InProgressResponseError as exc:
            self.db.add_run(task_id,agent_id,phase+"_in_progress","",model=model,input_summary="fp:"+input_fp,provider_response_id=exc.provider_response_id or "",stage_key=stage_key(task_id,phase+"_in_progress",agent_id=agent_id,input_fingerprint=input_fp))
            raise
        output=self._canonical_output(result)
        run_id=self.db.add_run(task_id,agent_id,phase,output,model=getattr(result,"model",model),input_summary="fp:"+input_fp,citations=getattr(result,"citations",[]),provider_response_id=getattr(result,"provider_response_id",None) or "",usage=getattr(result,"usage",None),stage_key=stage_key(task_id,phase,agent_id=agent_id,input_fingerprint=input_fp))
        if phase in {"primary","resume_primary","revision"}:
            self.db.add_artifact(task_id=task_id,project=project,kind=plan.expected_artifact or "other",name=f"{phase}.txt",sha256=_sha_text(output),produced_by_run_id=run_id,phase=phase)
        return output
    def _review(self,task_id,goal,artifact,reason,plan,*,phase,input_fp,legacy_fp=""):
        existing=self._existing_stage(task_id,phase,"stillpoint",input_fp,legacy_fp)
        if existing:return existing["output"]
        agent=self.registry.get("stillpoint");model=agent.model or self.default_model
        tools=capabilities_for_call(agent_id="stillpoint",plan_capabilities=[],agent_capabilities=[],review_reason=reason)
        try:
            result=self.provider.generate(system=agent_system_prompt(agent),prompt=review_prompt(goal,artifact,reason),model=model,tools=tools,task_id=task_id,phase=phase,effort="high")
        except IncompleteResponseError as exc:
            self.db.add_run(task_id,"stillpoint",phase+"_incomplete",exc.partial_text or "",model=model,input_summary="fp:"+input_fp,provider_response_id=exc.provider_response_id or "",stage_key=stage_key(task_id,phase+"_incomplete",agent_id="stillpoint",input_fingerprint=input_fp))
            raise
        except InProgressResponseError as exc:
            self.db.add_run(task_id,"stillpoint",phase+"_in_progress","",model=model,input_summary="fp:"+input_fp,provider_response_id=exc.provider_response_id or "",stage_key=stage_key(task_id,phase+"_in_progress",agent_id="stillpoint",input_fingerprint=input_fp))
            raise
        output=self._canonical_output(result)
        self.db.add_run(task_id,"stillpoint",phase,output,model=getattr(result,"model",model),input_summary="fp:"+input_fp,citations=getattr(result,"citations",[]),provider_response_id=getattr(result,"provider_response_id",None) or "",usage=getattr(result,"usage",None),stage_key=stage_key(task_id,phase,agent_id="stillpoint",input_fingerprint=input_fp))
        return output
    @staticmethod
    def _judgment(review):
        first=review.strip().splitlines()[0].strip().upper() if review.strip() else "CORRECT"
        if first.startswith("PASS"):return "PASS"
        if first.startswith("HALT"):return "HALT"
        return "CORRECT"
    def _load_saved_attachments(self,task_id):
        out=[]
        for row in self.db.list_task_files(task_id):
            item=read_attachment(row["path"])
            if item["sha256"]!=row["sha256"]:raise RuntimeError(f"managed attachment changed: {row['name']}")
            out.append(item)
        return out
    def _latest_artifact_refs(self,task_id):
        rows=self.db.list_artifacts(task_id)
        if not rows:return []
        latest={}
        for r in rows:
            prior=latest.get(r["kind"])
            if not prior or r["version"]>=prior["version"]:latest[r["kind"]]=r
        return [ArtifactRef(name=r["name"],sha256=r["sha256"],kind=r["kind"],artifact_id=r["id"],version=r["version"]) for r in latest.values()]
    def _latest_artifact_map(self,task_id):
        latest={}
        for r in self.db.list_artifacts(task_id):
            prior=latest.get(r["kind"])
            if not prior or r["version"]>=prior["version"]:latest[r["kind"]]=r
        return latest
    def _stale_superseded_actions(self,task_id,plan):
        latest=self._latest_artifact_map(task_id)
        for row in self.db.list_action_requests(task_id):
            if row["status"] in {"completed","stale","failed"}:continue
            stale=row.get("authority_revision")!=plan.authority_revision
            for ref in json.loads(row["artifact_refs_json"]):
                kind=ref.get("kind","other");cur=latest.get(kind)
                if cur and (cur["id"]!=ref.get("artifact_id") or cur["version"]!=ref.get("version",1) or cur["sha256"]!=ref.get("sha256")):
                    stale=True
            if stale:self.db.mark_action_stale(row["id"])
    def _prepare_actions(self,task_id,goal,plan):
        if not plan.restricted_actions:return []
        self._stale_superseded_actions(task_id,plan)
        bundle=self.policy.authority(goal); refs=self._latest_artifact_refs(task_id); now=_now_dt(); out=[]
        by_intent={}
        for a in bundle.restricted:
            by_intent.setdefault(a.intent,a)
        for action in plan.restricted_actions:
            a=by_intent.get(action); target=(a.clause.strip() if a and a.clause else (a.target if a else "unknown"));scope=[a.target if a else "unknown",target]
            action_refs=refs
            if action=="export_artifact":
                from .adapters.production import configured_outbox_root
                outbox_root=str(configured_outbox_root())
                scope.append("outbox_root="+outbox_root)
                target="bounded_outbox:"+outbox_root
                rows=self.db.list_artifacts(task_id)
                if not rows: raise RuntimeError("export_artifact requires a generated artifact")
                r=rows[-1]
                action_refs=[ArtifactRef(name=r["name"],sha256=r["sha256"],kind=r["kind"],artifact_id=r["id"],version=r["version"])]
            raw="|".join([task_id,plan.authority_revision,action,target,*[f"{r.artifact_id}:{r.version}:{r.sha256}" for r in action_refs]])
            idem=hashlib.sha256(raw.encode()).hexdigest();existing=self.db.find_action_request_by_idempotency(idem)
            if existing:out.append(existing["id"]);continue
            req=ActionRequest(action_id=hashlib.sha256(("action|"+raw).encode()).hexdigest()[:20],task_id=task_id,action_type=action,target=target,scope=scope,artifact_refs=action_refs,approval_required=True,approval_id=None,expires_at=(now+timedelta(hours=24)).isoformat(),issued_at=now.isoformat(),idempotency_key=idem,success_criteria=[{"send_email":"delivery_receipt","publish":"publication_receipt","social_post":"post_receipt","export_artifact":"export_receipt","spend":"payment_receipt","sign":"signature_receipt","delete":"deletion_receipt"}.get(action,"external_receipt")],authority_revision=plan.authority_revision)
            self.db.add_action_request(req);out.append(req.action_id)
        return out
    def _finish(self,task_id,goal,plan,primary_output,review_text):
        if plan.restricted_actions:
            self._prepare_actions(task_id,goal,plan)
            self.db.update_task(task_id,status="waiting_approval",final_output=primary_output,review_output=review_text,approval_reason=plan.approval_reason)
            return TaskOutcome(task_id,TaskStatus.WAITING_APPROVAL,plan,primary_output,review_text,plan.approval_reason)
        self.db.update_task(task_id,status="completed",final_output=primary_output,review_output=review_text,error=None)
        return TaskOutcome(task_id,TaskStatus.COMPLETED,plan,primary_output,review_text)
    def _execute(self,task_id,goal,project,plan,attachments):
        root_fp=self._fingerprint(goal,project,attachments);self.db.update_task(task_id,input_fingerprint=root_fp)
        contributions=[]
        for i,cid in enumerate(plan.contributors):
            prior=[]
            for j,(name,out) in enumerate(contributions):
                prior_spec=plan.contributor_specs[j] if j<len(plan.contributor_specs) else {}
                if prior_spec.get("before")=="next_contributor":prior.append((name,out))
            cfp=fingerprint(root_fp,"contribution",cid,[(n,_sha_text(o)) for n,o in prior])
            output=self._call_agent(task_id,cid,"contribution",goal,project,prior,attachments,plan,input_fp=cfp,legacy_fp=root_fp)
            contributions.append((self.registry.get(cid).name,output))
        pfp=fingerprint(root_fp,"primary",[(n,_sha_text(o)) for n,o in contributions])
        primary_output=self._call_agent(task_id,plan.primary,"primary",goal,project,contributions,attachments,plan,input_fp=pfp,legacy_fp=root_fp)
        review_text=""
        if plan.review_required and plan.primary!="stillpoint":
            rfp=fingerprint(root_fp,"review",_sha_text(primary_output))
            review_text=self._review(task_id,goal,primary_output,plan.review_reason,plan,phase="review",input_fp=rfp,legacy_fp=root_fp);judgment=self._judgment(review_text)
            if judgment=="HALT":
                self.db.update_task(task_id,status="blocked",final_output=primary_output,review_output=review_text);return TaskOutcome(task_id,TaskStatus.BLOCKED,plan,primary_output,review_text)
            if judgment=="CORRECT":
                revfp=fingerprint(root_fp,"revision",_sha_text(primary_output),_sha_text(review_text))
                primary_output=self._call_agent(task_id,plan.primary,"revision",goal,project,contributions,attachments,plan,correction=review_text,input_fp=revfp,legacy_fp=root_fp)
                ffp=fingerprint(root_fp,"review_final",_sha_text(primary_output))
                review_text=self._review(task_id,goal,primary_output,"post-correction final review",plan,phase="review_final",input_fp=ffp,legacy_fp=root_fp)
                if self._judgment(review_text)!="PASS":
                    self.db.update_task(task_id,status="blocked",final_output=primary_output,review_output=review_text);return TaskOutcome(task_id,TaskStatus.BLOCKED,plan,primary_output,review_text)
        return self._finish(task_id,goal,plan,primary_output,review_text)
    def submit(self,goal,*,project=None,files=None,budget:BudgetLimits|None=None):
        task_id=self.db.create_task(goal,project)
        if budget or self.default_budget:
            self.db.set_task_budget(task_id,budget or self.default_budget)
        self._active_task_id=task_id
        try:
            plan,planning_output,model_planned,planning_model=self.planner.plan(goal);self.db.set_plan(task_id,plan.to_dict())
            self._record_planning(task_id,goal,project,planning_output,model_planned,planning_model)
            self.db.add_plan_revision(task_id,fingerprint(goal),plan.authority_revision,plan.to_dict())
            attachments=[]
            for source in files or []:
                item=import_attachment(source,self.managed_files,task_id,allowed_roots=self.allowed_import_roots);attachments.append(item)
                self.db.add_task_file(task_id,item["path"],item["name"],item["sha256"],original_name=item.get("original_name") or item["name"],media_type=item.get("media_type"),size_bytes=item.get("size_bytes"))
            return self._execute(task_id,goal,project,plan,attachments)
        except BudgetExceeded as exc:
            self.db.update_task(task_id,status="blocked",error=str(exc));raise
        except Exception as exc:
            self.db.update_task(task_id,status="failed",error=str(exc));raise
        finally:
            self._active_task_id=None
    def resume(self,task_id,note=""):
        task=self.db.get_task(task_id)
        if not task:raise KeyError(task_id)
        if task["status"] not in {"new","running","failed","blocked"}:raise RuntimeError(f"task cannot be resumed from status={task['status']}")
        self._active_task_id=task_id
        try:
            effective=task["goal"]
            if note:effective+=f"\n\nCEO RESUME INSTRUCTION:\n{note}"
            if note or not task.get("plan_json"):
                plan,planning_output,model_planned,planning_model=self.planner.plan(effective);self.db.set_plan(task_id,plan.to_dict())
                self._record_planning(task_id,effective,task.get("project"),planning_output,model_planned,planning_model)
                pr=self.db.add_plan_revision(task_id,fingerprint(effective),plan.authority_revision,plan.to_dict())
                if note:self.db.add_resume_instruction(task_id,note,fingerprint(note),plan.authority_revision,pr)
            else:plan=WorkPlan.from_dict(json.loads(task["plan_json"]))
            attachments=self._load_saved_attachments(task_id);self.db.update_task(task_id,status="running",error=None)
            return self._execute(task_id,effective,task.get("project"),plan,attachments)
        except BudgetExceeded as exc:
            self.db.update_task(task_id,status="blocked",error=str(exc));raise
        except Exception as exc:
            self.db.update_task(task_id,status="failed",error=str(exc));raise
        finally:
            self._active_task_id=None
    def promote_memory(self,key,value,*,scope="company",source="CEO",confidence="verified",task_id=None):
        if source != "CEO":
            raise PermissionError("durable memory promotion requires CEO source")
        if not key or not str(key).strip():raise ValueError("memory key required")
        self.db.set_memory(str(key),str(value),scope=scope,source=source,confidence=confidence,task_id=task_id)
        return {"scope":scope,"key":str(key),"value":str(value),"source":source,"confidence":confidence,"task_id":task_id}
    def _request_from_row(self,row):
        refs=[ArtifactRef(**{k:v for k,v in item.items() if k in {"name","sha256","kind","media_type","artifact_id","version"}}) for item in json.loads(row["artifact_refs_json"])]
        return ActionRequest(action_id=row["id"],task_id=row["task_id"],action_type=row["action_type"],target=row["target"],scope=json.loads(row["scope_json"]),artifact_refs=refs,approval_required=bool(row["approval_required"]),approval_id=row["approval_id"],expires_at=row["expires_at"],issued_at=row["issued_at"],idempotency_key=row["idempotency_key"],success_criteria=json.loads(row["success_criteria_json"]),click_irreversible=bool(row["click_irreversible"]),authority_revision=row["authority_revision"],warrant_id=row["warrant_id"] if "warrant_id" in row.keys() else None)
    def execute_action(self,action_id,adapter_registry,*,now_iso=None):
        from .dispatch import is_probe_adapter_name, require_no_prior_real_dispatch

        row=self.db.get_action_request(action_id)
        if not row:
            raise KeyError(action_id)

        # Any prior real dispatch record blocks automatic retry before adapter resolution.
        require_no_prior_real_dispatch(self.db.get_action_dispatch(action_id))

        prior_results=self.db.list_action_results(action_id)
        if row["status"]=="completed":
            raise RuntimeError("action idempotency prevents duplicate execution")

        # Legacy result-based protection remains as defense in depth.
        if any(
            result.get("adapter")
            and result.get("adapter")!="null"
            and not str(result.get("adapter")).startswith("dry_run")
            for result in prior_results
        ):
            raise RuntimeError("action idempotency prevents duplicate external dispatch")

        req=self._request_from_row(row)
        effective_now=now_iso or _now_dt().isoformat()

        if req.approval_required and (
            not req.permitted(effective_now)
            or not self.db.has_action_approval(req.action_id,req.approval_id)
        ):
            raise NotAuthorized(
                "missing, expired, mismatched approval, or warrant"
            )

        if not req.warrant_id:
            raise NotAuthorized("consequential action has no bound warrant")

        warrant=self.db.get_temporal_warrant(req.warrant_id)
        if not warrant:
            raise NotAuthorized("bound warrant does not exist")

        try:
            validate_bound_warrant(
                request=req,
                warrant=warrant,
                now_iso=effective_now,
                actions_used=self.db.count_warrant_consumptions(req.warrant_id),
            )
        except TemporalAuthorityError as exc:
            raise NotAuthorized(str(exc)) from exc

        latest=self._latest_artifact_map(req.task_id)
        for ref in req.artifact_refs:
            cur=latest.get(ref.kind)
            if ref.artifact_id and (
                not cur
                or cur["id"]!=ref.artifact_id
                or cur["version"]!=ref.version
                or cur["sha256"]!=ref.sha256
            ):
                raise NotAuthorized("artifact changed since authorization")

        # Adapter resolution is side-effect free. Record the exact resolved adapter
        # before a real external adapter is invoked.
        adapter=adapter_registry.resolve(req)

        if is_probe_adapter_name(adapter.name):
            result=adapter_registry.execute_resolved(req,adapter)
            # Probe results are retained for observability but do not spend the
            # one-use external warrant.
            self.db.add_action_result(result)
            status=runtime_complete(req,result,now_iso=effective_now)
            self.db.update_action_request_status(action_id,status)
            # Preserve Patch-002 null_probe reservation behavior.
            try:
                self.db.set_warrant_consumption_disposition(
                    req.action_id,"null_probe"
                )
            except Exception:
                pass
            return {"action_id":action_id,"status":status,"result":result}

        # Reserve one warrant use (re-activate after null_probe if needed).
        try:
            self.db.reserve_warrant_for_action(
                action_id=req.action_id,
                warrant_id=req.warrant_id,
                authority_revision=req.authority_revision,
                approval_id=req.approval_id,
                artifact_hashes=[ref.sha256 for ref in req.artifact_refs],
            )
        except Exception:
            consumption_count=self.db.count_warrant_consumptions(req.warrant_id)
            if consumption_count < 1:
                raise

        # This commit point means the external effect may happen after it.
        # It also spends the one-use warrant immediately.
        self.db.begin_external_dispatch(
            action_id=req.action_id,
            warrant_id=req.warrant_id,
            adapter=adapter.name,
            idempotency_key=req.idempotency_key,
            authority_revision=req.authority_revision,
            approval_id=req.approval_id,
            artifact_hashes=[ref.sha256 for ref in req.artifact_refs],
        )

        try:
            result=adapter_registry.execute_resolved(req,adapter)
            status=runtime_complete(req,result,now_iso=effective_now)
            self.db.record_external_dispatch_result(
                action_id=req.action_id,
                result=result,
                action_status=status,
            )
            if status in {"completed","failed"}:
                self._release_consumed_action_authority(
                    req.action_id,
                    reason=f"dispatch_terminal:{status}",
                )
        except Exception as exc:
            # Adapter exceptions, malformed ActionResults, identity mismatches,
            # timeouts, and post-effect failures are all uncertain. Never retry.
            self.db.mark_external_dispatch_uncertain(
                req.action_id,
                error=f"{type(exc).__name__}: {exc}",
            )
            raise

        if status=="completed":
            pending=[
                r for r in self.db.list_action_requests(req.task_id)
                if r["status"]!="completed"
            ]
            if not pending:
                self.db.update_task(req.task_id,status="completed")

        return {"action_id":action_id,"status":status,"result":result}

    def reconcile_action_dispatch(
        self,
        action_id,
        *,
        effect_occurred,
        evidence=None,
        note="",
        reconciled_by="CEO:Robert Emmanuel LaDay",
    ):
        """Explicitly resolve an uncertain external dispatch.

        Reconciliation never restores the old warrant. Even confirmed_no_effect
        requires a newly authorized ActionRequest/Warrant before another real dispatch.
        """
        row = self.db.reconcile_external_dispatch(
            action_id=action_id,
            effect_occurred=bool(effect_occurred),
            reconciled_by=reconciled_by,
            note=note,
            evidence=evidence or [],
        )
        self._release_consumed_action_authority(
            action_id,
            reason=f"dispatch_reconciled:{row['state']}",
        )
        return row


    def approve(self,task_id,note=""):
        """CEO approval becomes explicit atomic Warrant issuance.

        No persisted ready_for_action window exists without the Warrant.
        """
        import uuid

        task=self.db.get_task(task_id)
        if not task:
            raise KeyError(task_id)
        if task["status"]!="waiting_approval":
            raise RuntimeError("task is not waiting for approval")

        latest=self._latest_artifact_map(task_id)
        requests=[
            r for r in self.db.list_action_requests(task_id)
            if r["status"]=="waiting_approval"
        ]
        if not requests:
            raise RuntimeError("no current action requests to approve")

        for r in requests:
            for ref in json.loads(r["artifact_refs_json"]):
                cur=latest.get(ref.get("kind","other"))
                if ref.get("artifact_id") and (
                    not cur
                    or cur["id"]!=ref.get("artifact_id")
                    or cur["version"]!=ref.get("version",1)
                    or cur["sha256"]!=ref.get("sha256")
                ):
                    self.db.mark_action_stale(r["id"])
                    raise RuntimeError(
                        "artifact changed since action request was prepared"
                    )

        approval_id=uuid.uuid4().hex[:12]
        bindings=[]
        for row in requests:
            req=self._request_from_row(row)
            req.approval_id=approval_id
            warrant=build_ceo_warrant(
                request=req,
                approval_id=approval_id,
            )
            bindings.append((req.action_id,warrant))

        self.db.authorize_actions_atomically(
            task_id=task_id,
            approval_id=approval_id,
            approval_note=note,
            bindings=bindings,
        )
        return self.db.get_task(task_id)


    # ---- Patch 004 runtime lifecycle integration ----

    def _release_consumed_action_authority(self, action_id, reason):
        from .temporal.lifecycle import build_action_release

        row=self.db.get_action_request(action_id)
        if not row or not row.get("warrant_id"):
            raise RuntimeError("cannot release action without bound warrant")
        existing=self.db.get_temporal_release_for_action(action_id)
        if existing:
            return existing["release_id"]

        warrant=self.db.get_temporal_warrant(row["warrant_id"])
        if not warrant:
            raise RuntimeError("cannot release missing warrant")
        release=build_action_release(
            action_id=action_id,
            warrant=warrant,
            reason=reason,
        )
        return self.db.persist_temporal_release(release,action_id=action_id)

    def record_new_evidence_for_action(
        self,
        action_id,
        evidence,
        *,
        reason="new material evidence",
    ):
        """Open a new evaluation cycle without resurrecting prior authority."""
        from .temporal.lifecycle import build_reevaluation_trigger

        row=self.db.get_action_request(action_id)
        if not row or not row.get("warrant_id"):
            raise RuntimeError("prior action/warrant required for reevaluation")
        warrant=self.db.get_temporal_warrant(row["warrant_id"])
        if not warrant:
            raise RuntimeError("prior warrant missing")

        events=list(evidence)
        if not events:
            raise ValueError("new evidence required")
        for event in events:
            self.db.persist_temporal_evidence_event(event)

        trigger=build_reevaluation_trigger(
            prior_disposition=row["status"],
            prior_action_id=action_id,
            prior_warrant=warrant,
            evidence=events,
            reason=reason,
        )
        self.db.persist_reevaluation_trigger(
            trigger,
            prior_action_id=action_id,
        )
        return trigger

    def authorize_reentry(
        self,
        *,
        prior_action_id,
        new_action_id,
        candidate_warrant,
        reevaluation_trigger,
    ):
        """Bind new present authority after reevaluation.

        This helper deliberately does not manufacture a candidate Warrant.
        The caller must have already earned/issued a new Warrant through the
        ordinary authorization path.
        """
        from .temporal.lifecycle import assert_bounded_reentry
        from .db import utcnow

        prior=self.db.get_action_request(prior_action_id)
        if not prior or not prior.get("warrant_id"):
            raise RuntimeError("prior action/warrant required")
        old=self.db.get_temporal_warrant(prior["warrant_id"])
        if not old:
            raise RuntimeError("prior warrant missing")

        assert_bounded_reentry(
            prior_warrant=old,
            candidate_warrant=candidate_warrant,
            trigger=reevaluation_trigger,
        )

        new=self.db.get_action_request(new_action_id)
        if not new:
            raise KeyError(new_action_id)
        if new.get("warrant_id"):
            raise RuntimeError("new action already has a warrant")

        # Exact binding is performed by the same DB warrant-binding mechanism;
        # the old warrant is never modified or reopened.
        self.db.insert_temporal_warrant(candidate_warrant)
        self.db.bind_action_warrant(new_action_id,candidate_warrant.warrant_id)

        conn=self.db._connection()
        conn.execute(
            """UPDATE action_requests
               SET reevaluation_trigger_id=?,reentry_parent_action_id=?,updated_at=?
               WHERE id=?""",
            (
                reevaluation_trigger.trigger_id,
                prior_action_id,
                utcnow(),
                new_action_id,
            ),
        )
        conn.commit()
        return self.db.get_action_request(new_action_id)


    def reject(self,task_id,note=""):
        task=self.db.get_task(task_id)
        if not task:raise KeyError(task_id)
        self.db.add_approval(task_id,"rejected",note);self.db.update_task(task_id,status="rejected");return self.db.get_task(task_id)
