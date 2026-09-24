"""코퍼스 **구성비**도 측정 손잡이다.

🔴 무엇을 주장하는가.

D층 집계 FPR 은 「이 도구의 오탐률」이 아니라 **「내가 고른 미끼 분류 구성비에서의
오탐률」**이다. 분류마다 물리는 정도가 다르므로, 코드도 도구도 채점자도 바꾸지
않고 **구성비만 바꿔 다른 숫자를 보고할 수 있다.**

이건 채점 기준 편차(`spread.py`)와 같은 종류의 손잡이인데, 발표된 벤치마크 중
자기 코퍼스의 구성비를 손잡이로 선언한 사례를 보지 못했다.

## 정직하게 다루기

분류별 표본이 작다(현재 3~17). 그래서 두 가지를 구분해 보고한다:

1. **구성비 선택의 효과** — 「X 만으로 코퍼스를 만들면 R_x 를 보고한다」는
   측정 절차에 대한 참인 진술이다. CI 폭과 무관하게 성립한다.
2. **분류 간 차이가 실재하는가** — 이건 **모집단에 대한 주장**이라 표본이
   필요하다. 극단 두 분류의 Wilson CI 가 겹치면 **잡음으로 설명 가능**하고,
   그러면 "분류마다 다르다"고 말하지 않는다.

🔴 2가 성립하지 않는데 1의 범위를 「도구의 오탐률 범위」처럼 제시하면
   그게 바로 이 프로젝트가 비판하는 과장이다. `heterogeneity_verdict` 가
   그 구분을 강제한다.

이 관계가 **decoy 150 목표의 진짜 이유**다. 집계 FPR 의 CI 를 좁히려는 게
아니라 **분류별 이질성을 검정 가능하게** 만들려는 것이다.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from codeproof_ai.eval.grading.base import Outcome
from codeproof_ai.eval.metrics import Proportion

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from codeproof_ai.eval.runner import SampleOutcome
    from codeproof_ai.eval.sample import LabeledSample

UNCLASSIFIED = "(분류 없음)"

MIN_KINDS_FOR_COMPARISON = 2
"""이질성을 말하려면 비교할 분류가 최소 둘은 있어야 한다."""


@dataclass(frozen=True, slots=True)
class KindRate:
    """한 미끼 분류가 얼마나 무는가.

    🔴 두 비율을 **둘 다** 낸다. 하나만 내면 조용히 틀린다.
    """

    kind: str

    rate: Proportion
    """지적 단위 - 이 분류의 음성 위에 나온 지적 중 안전 주장 범위 안에 떨어진 비율.

    분모는 **판정된 것이 아니라 나온 지적 전부**다. 증명된 음성 위에서는
    정의상 TP 가 불가능하므로 `FP/(TP+FP)` 는 언제나 100% 이고 정보가 없다.
    범위 밖(UNDECIDABLE)은 「이 미끼와 무관한 지적」이므로 분모에 남는다.

    ⚠ 지적은 **독립 시행이 아니다** - decoy 하나가 여러 지적을 낸다.
      그래서 이 CI 는 실제보다 좁다. `sample_rate` 를 같이 본다.
    """

    sample_rate: Proportion
    """샘플 단위 - 이 분류의 decoy 중 **하나라도** 미끼를 물린 비율.

    표본이 작지만 **독립**이다. 두 비율이 크게 어긋나면 소수의 decoy 가
    지적을 몰아서 내고 있다는 뜻이다.
    """

    undecided: int
    """범위 밖 지적 수. 분모에 포함돼 있다 - 투명하게 같이 낸다."""

    @property
    def samples(self) -> int:
        return self.sample_rate.total

    @property
    def interval(self) -> tuple[float, float] | None:
        return self.rate.interval


@dataclass(frozen=True, slots=True)
class MixSensitivity:
    """구성비를 바꾸면 집계가 얼마나 움직이는가."""

    grader: str
    kinds: tuple[KindRate, ...]
    """FP율 내림차순."""

    observed: Proportion
    """현재 코퍼스 구성비에서의 집계 (지적 단위)."""

    @property
    def uniform(self) -> float | None:
        """분류를 **균등 가중**했을 때의 집계.

        현재 구성비가 우연히 만든 쏠림을 걷어낸 값이다.
        """
        rates = [k.rate.point for k in self.kinds if k.rate.point is not None]
        return sum(rates) / len(rates) if rates else None

    @property
    def reachable(self) -> tuple[float, float] | None:
        """구성비만 바꿔 도달 가능한 집계 범위.

        한 분류만으로 코퍼스를 채우면 그 분류의 FP율이 곧 집계다.
        """
        rates = [k.rate.point for k in self.kinds if k.rate.point is not None]
        return (min(rates), max(rates)) if rates else None

    @property
    def ratio(self) -> float | None:
        """최대/최소 배수. 🔴 최소가 0 이면 None - 무한대로 부풀리지 않는다."""
        r = self.reachable
        if r is None or r[0] == 0:
            return None
        return r[1] / r[0]

    @property
    def heterogeneity_verdict(self) -> str:
        """분류 간 차이가 표본 잡음으로 설명되는가.

        🔴 극단 두 분류의 Wilson 95% CI 가 겹치면 **겹친다고 말한다.**
           겹치는데도 "분류마다 다르다"고 하면 과장이다.
        """
        usable = [k for k in self.kinds if k.rate.total > 0]
        if len(usable) < MIN_KINDS_FOR_COMPARISON:
            return "판정 불가 - 분류가 2종 미만이다"

        hi, lo = usable[0], usable[-1]
        hi_iv, lo_iv = hi.interval, lo.interval
        if hi_iv is None or lo_iv is None:
            return "판정 불가 - 신뢰구간을 낼 수 없다"

        if lo_iv[1] < hi_iv[0]:
            return (
                f"분류 간 차이가 **실재한다** - 극단 두 분류의 95% CI 가 겹치지 "
                f"않는다 ({lo.kind} ≤{lo_iv[1]:.1%} < {hi_iv[0]:.1%}≤ {hi.kind})"
            )
        return (
            f"분류 간 차이를 **아직 주장할 수 없다** - {lo.kind} 와 {hi.kind} 의 "
            f"95% CI 가 겹친다([{lo_iv[0]:.1%}, {lo_iv[1]:.1%}] vs "
            f"[{hi_iv[0]:.1%}, {hi_iv[1]:.1%}]). 표본을 늘려야 한다"
        )

    def render(self) -> str:
        lines = [
            f"  [코퍼스 구성비 민감도] 채점자={self.grader}",
            "    🔴 코드도 도구도 채점자도 그대로다. **미끼 분류 구성비만** 바꾼다.",
            "",
            f"    {'미끼 분류':24s} {'물림':>4} {'지적':>5} {'범위밖':>6}"
            f"  {'물림율':>7} [95% CI]        {'decoy':>6}",
        ]
        for k in self.kinds:
            iv = k.interval
            band = f"[{iv[0]:5.1%}, {iv[1]:5.1%}]" if iv else "     n/a       "
            point = f"{k.rate.point:6.1%}" if k.rate.point is not None else "   n/a"
            sp = k.sample_rate
            per_sample = (
                f"{sp.successes}/{sp.total}" if sp.total else "0/0"
            )
            lines.append(
                f"    {k.kind:24s} {k.rate.successes:>4} {k.rate.total:>5} "
                f"{k.undecided:>6}  {point} {band} {per_sample:>6}"
            )

        lines.append("")
        lines.append(f"    현재 구성비 : {self.observed.render()}")
        if self.uniform is not None:
            lines.append(f"    균등 구성비 : {self.uniform:6.1%}")
        r = self.reachable
        if r is not None:
            ratio = f" — {self.ratio:.1f}배" if self.ratio is not None else ""
            lines.append(
                f"    🔴 구성비만 바꿔 도달 가능 : {r[0]:.1%} ~ {r[1]:.1%}{ratio}"
            )
        lines.append(f"    ⚖ {self.heterogeneity_verdict}")
        lines.append(
            "    ⚠ 지적 단위 CI 는 실제보다 좁다 - decoy 하나가 여러 지적을 내므로"
        )
        lines.append(
            "      독립 시행이 아니다. 오른쪽 decoy 열(샘플 단위)을 같이 본다."
        )
        return "\n".join(lines)


def mix_sensitivity(
    outcomes: Sequence[SampleOutcome],
    samples: Sequence[LabeledSample],
    grader: str,
) -> MixSensitivity:
    """증명된 음성만 모아 분류별 FP율을 낸다.

    🔴 음성만 본다. 양성(twin)의 지적을 섞으면 FP율이 아니라 다른 숫자가 된다.
    """
    kind_of = _kinds(samples)
    fp: dict[str, int] = defaultdict(int)
    total: dict[str, int] = defaultdict(int)
    undecided: dict[str, int] = defaultdict(int)
    seen: dict[str, set[str]] = defaultdict(set)
    bitten: dict[str, set[str]] = defaultdict(set)

    obs_fp = obs_total = 0
    for o in outcomes:
        if not o.is_proven_safe:
            continue
        kind = kind_of.get(o.sample_id, UNCLASSIFIED)
        seen[kind].add(o.sample_id)
        for j in o.judgments.get(grader, ()):
            # 🔴 분모에서 빼지 않는다. 증명된 음성 위에서는 TP 가 정의상
            #    불가능해서 FP/(TP+FP) 가 항상 100% 다 - 정보가 없다.
            #    범위 밖 지적은 「이 미끼와 무관한 지적」이라 분모에 남아야
            #    「나온 지적 중 몇이 물렸나」가 된다.
            total[kind] += 1
            obs_total += 1
            if j.outcome is Outcome.UNDECIDABLE:
                undecided[kind] += 1
            elif j.outcome is Outcome.FALSE_POSITIVE:
                fp[kind] += 1
                obs_fp += 1
                bitten[kind].add(o.sample_id)

    kinds = tuple(
        sorted(
            (
                KindRate(
                    kind=k,
                    rate=Proportion(successes=fp[k], total=total[k]),
                    sample_rate=Proportion(
                        successes=len(bitten[k]), total=len(seen[k])
                    ),
                    undecided=undecided[k],
                )
                for k in seen
            ),
            key=lambda kr: (-(kr.rate.point or 0.0), kr.kind),
        )
    )
    return MixSensitivity(
        grader=grader,
        kinds=kinds,
        observed=Proportion(successes=obs_fp, total=obs_total),
    )


def _kinds(samples: Sequence[LabeledSample]) -> Mapping[str, str]:
    """음성 샘플 id -> 미끼 분류."""
    return {
        s.sample_id: s.safety.category
        for s in samples
        if s.safety is not None and s.safety.category
    }
