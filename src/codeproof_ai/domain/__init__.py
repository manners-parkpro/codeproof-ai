"""순수 도메인 모델.

🔴 이 패키지는 stdlib 과 typing 외에 아무것도 import 하지 않는다.
   외부 의존성이 들어오는 순간 도메인 테스트가 API 키를 요구하기 시작한다.
   근거: CLAUDE.md A1.

정답 라벨(Defect·LabeledSample·Stratum)은 여기 없다 - eval/sample.py 에 있다.
런타임은 eval/ 을 import 할 수 없으므로 라벨을 볼 방법이 구조적으로 없다.
"""

from codeproof_ai.domain.evidence import (
    Evidence,
    EvidenceKind,
    Verdict,
    VerifiedFinding,
)
from codeproof_ai.domain.finding import Category, Finding, Severity
from codeproof_ai.domain.location import Location, Position, Span
from codeproof_ai.domain.observation import (
    FindingGrouper,
    FingerprintGrouper,
    LocationGrouper,
    MixedReviewerError,
    ObservationSet,
    ObservedFinding,
    group_runs,
)
from codeproof_ai.domain.reviewer import (
    Reviewer,
    ReviewerKind,
    ReviewResult,
    ReviewTelemetry,
)
from codeproof_ai.domain.run import RunManifest, ToolVersion
from codeproof_ai.domain.target import ReviewTarget, SourceFile

__all__ = [
    "Category",
    "Evidence",
    "EvidenceKind",
    "Finding",
    "FindingGrouper",
    "FingerprintGrouper",
    "Location",
    "LocationGrouper",
    "MixedReviewerError",
    "ObservationSet",
    "ObservedFinding",
    "Position",
    "ReviewResult",
    "ReviewTarget",
    "ReviewTelemetry",
    "Reviewer",
    "ReviewerKind",
    "RunManifest",
    "Severity",
    "SourceFile",
    "Span",
    "ToolVersion",
    "Verdict",
    "VerifiedFinding",
    "group_runs",
]
