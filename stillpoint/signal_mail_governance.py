"""Provider-neutral mailbox governance for Signal.

Each mailbox receives its own standing delegation. One Signal office may supervise
many mailboxes, but no mailbox can inherit standing from another.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from .mail_contracts import MailboxIdentity
from .authority.standing import StandingDelegation
from .temporal.envelope import ContinuationCondition,ConditionOperator

SAFE_AUTONOMOUS_CLASSIFICATIONS=frozenset({'scheduling','acknowledgement','routine_information'})

@dataclass(frozen=True)
class MailboxGovernanceSpec:
    identity:MailboxIdentity
    delegation_id:str
    claim_envelope_ids:list[str]
    allowed_classifications:list[str]
    continuation_conditions:list[ContinuationCondition]
    exclusions:list[str]
    release_conditions:list[str]
    valid_from:str
    review_by:str
    policy_basis:str
    purpose:str
    issuer:str='CEO:Robert Emmanuel LaDay'

    def __post_init__(self):
        if not self.delegation_id.strip():raise ValueError('delegation_id required')
        if not self.claim_envelope_ids:raise ValueError('claim envelopes required')
        classes=[str(x).strip() for x in self.allowed_classifications if str(x).strip()]
        if not classes or not set(classes).issubset(SAFE_AUTONOMOUS_CLASSIFICATIONS):raise ValueError('allowed classifications must be safe routine classes')
        object.__setattr__(self,'allowed_classifications',classes)
        if not self.continuation_conditions:raise ValueError('continuation conditions required')
        if not self.exclusions or not self.release_conditions:raise ValueError('exclusions and release conditions required')

    def standing(self)->StandingDelegation:
        execution=[
            ContinuationCondition('signal_email.provider',ConditionOperator.EQ,self.identity.provider,'bind exact mail provider'),
            ContinuationCondition('signal_email.account',ConditionOperator.EQ,self.identity.account,'bind exact mailbox account'),
            ContinuationCondition('signal_email.jurisdiction',ConditionOperator.EQ,self.identity.jurisdiction,'bind exact mailbox jurisdiction'),
            ContinuationCondition('signal_email.prepared',ConditionOperator.EQ,True,'reply must be prepared'),
            ContinuationCondition('signal_email.requires_human',ConditionOperator.EQ,False,'human-review work excluded'),
            ContinuationCondition('signal_email.classification',ConditionOperator.IN,list(self.allowed_classifications),'finite routine classes'),
        ]
        return StandingDelegation(
            delegation_id=self.delegation_id,delegate_role='signal',issuer=self.issuer,
            policy_basis=self.policy_basis,purpose=self.purpose,claim_envelope_ids=list(self.claim_envelope_ids),
            allowed_action_types=['send_email'],continuation_conditions=list(self.continuation_conditions),
            execution_conditions=execution,exclusions=list(self.exclusions),release_conditions=list(self.release_conditions),
            valid_from=self.valid_from,review_by=self.review_by,
        )

@dataclass(frozen=True)
class SignalMailboxGovernanceSet:
    mailboxes:list[MailboxGovernanceSpec]
    def __post_init__(self):
        if not self.mailboxes:raise ValueError('at least one mailbox governance spec required')
        identities=set();delegations=set()
        for spec in self.mailboxes:
            key=spec.identity.authority_subject
            if key in identities:raise ValueError(f'duplicate mailbox jurisdiction: {key}')
            if spec.delegation_id in delegations:raise ValueError('delegation id cannot govern multiple mailbox jurisdictions')
            identities.add(key);delegations.add(spec.delegation_id)
    def by_authority_subject(self)->dict[str,MailboxGovernanceSpec]:
        return {x.identity.authority_subject:x for x in self.mailboxes}
