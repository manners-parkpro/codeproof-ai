"""미끼 효과 측정 - decoy 가 실제로 물리는가.

🔴 이 모듈은 `corpus/` 가 아니라 `eval/` 에 있다.
   측정에 **라벨된 샘플과 리뷰어**가 필요하기 때문이다. corpus/ 는 decoy 를
   작성·검증만 하고 실험을 모른다 - 레이어 테스트가 이 위반을 잡아냈다.


🔴 지적이 없으면 채점할 것도 없다. 아무도 물지 않는 decoy 는 코퍼스에 있어도
   FPR 에 기여하지 않는다. 그런 항목을 세지 않고 150 을 채우면 숫자만 는다.

⚠ 다만 **「안 물림 = 나쁨」이 아니다.** 셋으로 갈린다:

     물림                    시험됨
     안 물림 · 추론 대상      미시험 - LLM 리뷰어가 있어야 알 수 있다
     안 물림 · 미끼가 약함    실제로 나쁨

   뒤의 둘은 정적분석기만으로 **구별할 수 없다.** 그래서 구별했다고 말하지 않고
   「이 리뷰어들로는 시험되지 않았다」고만 보고한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from codeproof_ai.domain.finding import Finding
    from codeproof_ai.domain.reviewer import Reviewer
    from codeproof_ai.eval.sample import LabeledSample


class BaitStatus(StrEnum):
    EXERCISED = "exercised"
    """미끼 구간 안에서 지적이 나왔다 - 이 decoy 는 시험됐다."""

    UNTESTED = "untested"
    """🔴 아무도 물지 않았다. **나쁘다는 뜻이 아니다** -
    추론이 필요한 미끼일 수 있고, 그건 LLM 리뷰어가 있어야 안다."""

    OUT_OF_SCOPE = "out_of_scope"
    """지적은 나왔으나 전부 미끼 구간 밖이다 - 미끼가 아닌 것에 반응했다."""


@dataclass(frozen=True, slots=True)
class DecoyStat:
    sample_id: str
    trap_kind: str
    covered: tuple[int, int]
    in_bait: dict[str, int] = field(default_factory=dict)
    total: dict[str, int] = field(default_factory=dict)

    @property
    def bait_hits(self) -> int:
        return sum(self.in_bait.values())

    @property
    def any_finding(self) -> int:
        return sum(self.total.values())

    @property
    def status(self) -> BaitStatus:
        if self.bait_hits:
            return BaitStatus.EXERCISED
        return BaitStatus.OUT_OF_SCOPE if self.any_finding else BaitStatus.UNTESTED

    @property
    def biting_reviewers(self) -> tuple[str, ...]:
        return tuple(k for k, v in self.in_bait.items() if v)


@dataclass(frozen=True, slots=True)
class CorpusStats:
    stats: tuple[DecoyStat, ...]
    reviewers: tuple[str, ...]

    def by_status(self, status: BaitStatus) -> tuple[DecoyStat, ...]:
        return tuple(s for s in self.stats if s.status is status)

    @property
    def exercised_rate(self) -> float | None:
        return len(self.by_status(BaitStatus.EXERCISED)) / len(self.stats) if self.stats else None

    def coverage_by_trap(self) -> dict[str, tuple[int, int]]:
        """trap 분류별 (시험됨, 전체). 어느 분류가 비어 있는지 본다."""
        out: dict[str, tuple[int, int]] = {}
        for s in self.stats:
            hit, total = out.get(s.trap_kind, (0, 0))
            out[s.trap_kind] = (
                hit + int(s.status is BaitStatus.EXERCISED),
                total + 1,
            )
        return out


def _review_all(
    samples: Sequence[LabeledSample], reviewers: dict[str, Reviewer]
) -> dict[str, dict[str, tuple[Finding, ...]]]:
    """리뷰어별로 전체 대상을 한 번에 돌린다. 일괄을 지원하면 쓴다."""
    targets = [s.target for s in samples]
    out: dict[str, dict[str, tuple[Finding, ...]]] = {}
    for label, rv in reviewers.items():
        review_many = getattr(rv, "review_many", None)
        if review_many is not None:
            out[label] = {
                tid: res.findings for tid, res in review_many(targets).items()
            }
        else:
            out[label] = {t.target_id: rv.review(t).findings for t in targets}
    return out


def measure(
    samples: Sequence[LabeledSample], reviewers: dict[str, Reviewer]
) -> CorpusStats:
    """음성 decoy 마다 미끼 구간에서 지적이 나오는지 센다.

    🔴 일괄 경로를 쓴다. 대상마다 subprocess 를 띄우면 [실측] mypy 만 17초다
       (일괄 0.5초). 느린 측정은 결국 안 돌리게 된다.
    """
    batched = _review_all(samples, reviewers)

    # trap 분류는 짝(twin)의 결함 라벨에 있다 - 음성 쪽에는 없다.
    # 스키마를 늘리는 대신 paired_with 로 찾는다.
    traps = {
        x.sample_id: (x.defects[0].category or "?")
        for x in samples
        if x.defects
    }

    stats: list[DecoyStat] = []
    for s in samples:
        if not s.is_proven_safe or s.safety is None:
            continue
        covered = s.safety.covered_lines
        if covered is None:
            continue
        lo, hi = covered

        in_bait: dict[str, int] = {}
        total: dict[str, int] = {}
        for label in reviewers:
            findings = batched[label][s.sample_id]
            total[label] = len(findings)
            in_bait[label] = sum(1 for f in findings if lo <= f.location.line <= hi)

        stats.append(
            DecoyStat(
                sample_id=s.sample_id,
                trap_kind=traps.get(s.paired_with or "", "?"),
                covered=(lo, hi),
                in_bait=in_bait,
                total=total,
            )
        )
    return CorpusStats(stats=tuple(stats), reviewers=tuple(reviewers))
