"""Provider-neutral reconciliation for uncertain Signal email dispatches."""
from __future__ import annotations

def reconcile_mail_send(runtime,action_id:str,adapter)->dict:
    row=runtime.db.get_action_request(action_id)
    if not row:raise KeyError(action_id)
    dispatch=runtime.db.get_action_dispatch(action_id)
    if not dispatch:raise RuntimeError('action has no durable dispatch')
    if dispatch['state']!='uncertain':raise RuntimeError('mail reconciliation is only valid for uncertain dispatches')
    if dispatch['adapter']!=adapter.name:raise RuntimeError('reconciliation adapter does not match durable dispatch')
    request=runtime._request_from_row(row);probe=adapter.probe_existing(request)
    if probe.get('effect_occurred') is not True:
        return {'action_id':action_id,'status':'ambiguous','provider':adapter.name,'note':probe.get('note',''),'matches':probe.get('matches',[])}
    reconciled=runtime.reconcile_action_dispatch(action_id,effect_occurred=True,evidence=probe.get('evidence') or [],note=probe.get('note',''),reconciled_by=f'operator:{adapter.name}:exact_message_id_probe')
    return {'action_id':action_id,'status':reconciled['state'],'probe':probe}
