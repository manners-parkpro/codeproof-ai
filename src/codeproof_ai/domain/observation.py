"""다회 실행에서 관측된 지적.

🔴 빈도는 노이즈가 아니라 신호다.

Anthropic 은 seed 도 temperature 도 제공하지 않으므로 실행은 환원 불가능하게
확률적이고, 다회 샘플링이 재현성의 유일한 수단이다 (CLAUDE.md F8).
그 제약이 공짜로 주는 유일한 관측치가 **실행 간 변동**이다.

평균으로 뭉개면(같은 오답 8번 vs 서로 다른 오답 8개가 같아진다) 또는
합집합으로 펴면(1/8 과 8/8 이 같아진다) 그 정보를 버리게 된다.
그래서 지적은 "몇 번 중 몇 번 나왔는지" 를 들고 다닌다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from codeproof_ai.domain.finding import Finding


@runtime_checkable
class FindingGrouper(Protocol):
    """"같은 지적인가" 를 판단하는 정책.

    🔴 이것 자체가 측정 선택이다. 정책이 느슨하면 출현율이 올라간다.
       그래서 RunManifest 에 기록한다 - 이 프로젝트가 드러내려는 종류의 손잡이다.
    """

    name: str

    def key(self, finding: Finding) -> str:
        """같은 키를 받은 지적은 같은 것으로 묶인다."""
        ...


class FingerprintGrouper:
    """기본 정책 - Finding.fingerprint 를 그대로 쓴다.

    (rule_id, 둘러싼 심볼, 정규화된 인용문). 라인 번호는 들어가지 않는다.
    둘러싼 심볼을 쓰므로 AST 패스가 선행되어야 제 성능이 난다.
    """

    name = "fingerprint"

    def key(self, finding: Finding) -> str:
        return finding.fingerprint


class LocationGrouper:
    """AST 패스 없이도 쓸 수 있는 거친 정책.

    (파일, 라인 버킷, rule_id). 인용문을 보지 않으므로 표현이 흔들려도 묶인다 -
    대신 가까운 줄의 서로 다른 지적을 합쳐버릴 수 있다.
    """

    def __init__(self, bucket: int = 3) -> None:
        if bucket < 1:
            msg = f"bucket 은 1 이상이다: {bucket}"
            raise ValueError(msg)
        self.bucket = bucket
        self.name = f"location(bucket={bucket})"

    def key(self, finding: Finding) -> str:
        loc = finding.location
        anchor = loc.symbol or f"L{loc.line // self.bucket}"
        return f"{loc.path}::{anchor}::{finding.rule_id}"


@dataclass(frozen=True, slots=True)
class ObservedFinding:
    """N회 실행에 걸쳐 관측된 지적 하나.

    Attributes:
        finding: 대표 지적 (가장 먼저 등장한 것).
        runs: 🔴 등장한 실행 번호의 집합. **개수가 아니라 집합**이다.
            그래야 "3번째 실행에서 뭘 봤나" 와 "6번 이상 나온 것만" 이
            둘 다 사후에 유도된다. 비용은 0이다.
        total_runs: 전체 실행 수.
        variants: 같은 것으로 묶인 원본들. 문구 차이를 보존한다 -
            표현 안정성도 데이터이고, 감사 시 원본이 필요하다.
        variant_runs: `variants` 마다 그것이 나온 실행 번호. 🔴 한 실행이 같은 묶음에
            지적을 둘 낼 수 있어 `runs` 로는 원본을 실행별로 가를 수 없다.
    """

    finding: Finding
    runs: frozenset[int]
    total_runs: int
    variants: tuple[Finding, ...] = field(default_factory=tuple, repr=False)
    variant_runs: tuple[int, ...] = field(default_factory=tuple, repr=False)

    def __post_init__(self) -> None:
        if self.total_runs < 1:
            msg = f"total_runs 는 1 이상이다: {self.total_runs}"
            raise ValueError(msg)
        if not self.runs:
            msg = "한 번도 등장하지 않은 지적은 관측이 아니다"
            raise ValueError(msg)
        if out_of_range := {r for r in self.runs if not 0 <= r < self.total_runs}:
            msg = f"실행 번호가 범위를 벗어난다: {sorted(out_of_range)}"
            raise ValueError(msg)
        if self.variant_runs and (
            len(self.variant_runs) != len(self.variants) or set(self.variant_runs) != self.runs
        ):
            msg = f"원본마다의 실행 번호가 원본 · 실행과 맞지 않는다: {self.variant_runs}"
            raise ValueError(msg)

    @property
    def occurrences(self) -> int:
        return len(self.runs)

    @property
    def rate(self) -> float:
        """출현율. 🔴 이 값은 "정답일 확률" 이 아니다 - 자기일관성일 뿐이다."""
        return len(self.runs) / self.total_runs

    @property
    def is_unanimous(self) -> bool:
        return len(self.runs) == self.total_runs

    def appeared_in(self, run: int) -> bool:
        return run in self.runs

    def said_in(self, run: int) -> tuple[Finding, ...]:
        """그 실행이 실제로 낸 원본 - 대표는 다른 실행의 문구일 수 있다."""
        return tuple(f for f, r in zip(self.variants, self.variant_runs, strict=True) if r == run)


class MixedReviewerError(ValueError):
    """서로 다른 리뷰어의 지적을 한 관측으로 묶으려 했다.

    🔴 이건 조용한 투표다. Claude 와 Codex 가 각각 찾은 지적을 한 집합에
       넣으면 둘 다 찾은 것이 2/2 로 보이고, 그 순간 "출현 빈도" 가
       자기일관성이 아니라 **교차모델 합의**를 재게 된다.

       두 모델은 독립이어야 한다 - 비교는 하되 투표는 하지 않는다.
    """


@dataclass(frozen=True, slots=True)
class ObservationSet:
    """**한 리뷰어**의 한 대상에 대한 N회 실행 관측.

    🔴 리뷰어 하나다. 여러 리뷰어를 섞지 않는다 - MixedReviewerError 참조.
    """

    target_id: str
    reviewer: str
    """이 관측을 낸 리뷰어. 섞임 방지의 기준이다."""

    total_runs: int
    grouper: str
    """사용된 그룹핑 정책 이름. 매니페스트에 실린다."""

    observed: tuple[ObservedFinding, ...]

    def at_least(self, k: int) -> tuple[ObservedFinding, ...]:
        """k회 이상 등장한 지적만.

        🔴 이건 **기법**이지 기준선이 아니다. N회 실행을 요구하므로
           개발자가 한 번 돌렸을 때 보는 것과 다르다 - in_run() 을 참고.
        """
        return tuple(o for o in self.observed if o.occurrences >= k)

    def in_run(self, run: int) -> tuple[ObservedFinding, ...]:
        """특정 실행에서 실제로 나온 지적만.

        🔴 **개발자가 한 번 돌렸을 때 보는 것**이다. 단일 실행 기대값은
           이걸 모든 실행에 대해 평균해서 얻는다.
        """
        return tuple(o for o in self.observed if o.appeared_in(run))

    @property
    def unanimous(self) -> tuple[ObservedFinding, ...]:
        return tuple(o for o in self.observed if o.is_unanimous)

    @property
    def mean_findings_per_run(self) -> float:
        """실행당 평균 지적 수 - 합집합 크기가 아니다."""
        if self.total_runs == 0:
            return 0.0
        return sum(o.occurrences for o in self.observed) / self.total_runs


def group_runs(
    target_id: str,
    runs: Sequence[Iterable[Finding]],
    grouper: FindingGrouper | None = None,
    reviewer: str | None = None,
) -> ObservationSet:
    """**한 리뷰어**의 N회 실행을 출현 빈도가 붙은 관측으로 묶는다.

    🔴 모든 지적의 `source` 가 같아야 한다. 다르면 MixedReviewerError 다 -
       서로 다른 모델의 지적을 섞으면 출현 빈도가 자기일관성이 아니라
       교차모델 합의가 되고, 그건 조용한 투표다.

    Args:
        runs: 실행별 지적. 길이가 곧 total_runs 다.
        grouper: 같음 판정 정책. 기본은 fingerprint.
        reviewer: 리뷰어 이름. 생략하면 지적의 source 에서 추론한다.
    """
    policy = grouper if grouper is not None else FingerprintGrouper()
    materialized = [list(r) for r in runs]
    total = len(materialized)
    if total < 1:
        msg = "실행이 하나도 없다"
        raise ValueError(msg)

    sources = {f.source for run in materialized for f in run}
    if len(sources) > 1:
        msg = (
            f"서로 다른 리뷰어의 지적이 섞였다: {sorted(sources)}. "
            "한 관측은 한 리뷰어의 것이어야 한다 - 섞으면 출현 빈도가 "
            "자기일관성이 아니라 교차모델 합의를 재게 되고, 그건 투표다."
        )
        raise MixedReviewerError(msg)
    if reviewer is not None and sources and reviewer not in sources:
        msg = f"reviewer={reviewer!r} 인데 지적의 source 는 {sorted(sources)} 다"
        raise MixedReviewerError(msg)

    who = reviewer or (next(iter(sources)) if sources else "unknown")
    # dict 는 삽입 순서를 지킨다 - 관측 순서는 첫 등장 순서이고, 대표는 묶음의 첫 지적이다.
    seen_in: dict[str, set[int]] = {}
    variants: dict[str, list[Finding]] = {}
    variant_runs: dict[str, list[int]] = {}

    for idx, findings in enumerate(materialized):
        for f in findings:
            k = policy.key(f)
            seen_in.setdefault(k, set()).add(idx)
            variants.setdefault(k, []).append(f)
            variant_runs.setdefault(k, []).append(idx)

    return ObservationSet(
        target_id=target_id,
        reviewer=who,
        total_runs=total,
        grouper=policy.name,
        observed=tuple(
            ObservedFinding(
                finding=group[0],
                runs=frozenset(seen_in[k]),
                total_runs=total,
                variants=tuple(group),
                variant_runs=tuple(variant_runs[k]),
            )
            for k, group in variants.items()
        ),
    )
