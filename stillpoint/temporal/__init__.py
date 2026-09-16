"""StillPoint temporal authority and continuing evidence layer.

Core invariants formalized here:

- knowledge ≠ ownership
- description ≠ identity
- prediction ≠ permission
- confidence ≠ jurisdiction
- past truth ≠ permanent authority
- evidence ≠ warrant
- warrant ≠ execution
- completion ≠ erasure
- release ≠ amnesia
- changed evidence may change warrant
- a finite receiver does not become the Source

FINALITY MUST BE EARNED.

A claim is information. A warrant is authority. They remain structurally separate.
Prediction does not self-authorize.
Historical truth may remain while current authority expires.
"""

from .claims import (
    Claim,
    ClaimStatus,
    ClaimDomain,
    EvidenceRef,
)
from .warrants import (
    Warrant,
    WarrantStatus,
    WarrantScope,
)
from .evidence import (
    EvidenceEvent,
    EvidenceKind,
)
from .firewall import (
    ClaimToWarrantFirewall,
    PredictionFirewall,
    DomainContainment,
    TemporalAuthorityError,
)
from .reentry import (
    ReevaluationTrigger,
    ReleaseRecord,
)

__all__ = [
    "Claim",
    "ClaimStatus",
    "ClaimDomain",
    "EvidenceRef",
    "Warrant",
    "WarrantStatus",
    "WarrantScope",
    "EvidenceEvent",
    "EvidenceKind",
    "ClaimToWarrantFirewall",
    "PredictionFirewall",
    "DomainContainment",
    "TemporalAuthorityError",
    "ReevaluationTrigger",
    "ReleaseRecord",
]
