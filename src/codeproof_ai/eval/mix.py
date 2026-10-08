"""코퍼스 **구성비**도 측정 손잡이다.

🔴 무엇을 주장하는가.

D층 집계 FPR 은 「이 도구의 오탐률」이 아니라 **「내가 고른 미끼 분류 구성비에서의
오탐률」**이다. 분류마다 물리는 정도가 다르므로, 코드도 도구도 채점자도 바꾸지
않고 **구성비만 바꿔 다른 숫자를 보고할 수 있다.**

이건 채점 기준 편차(`spread.py`)와 같은 종류의 손잡이인데, 발표된 벤치마크 중
자기 코퍼스의 구성비를 손잡이로 선언한 사례를 보지 못했다.

## 정직하게 다루기

분류별 표본이 작다. 그래서 두 가지를 구분해 보고한다:

1. **구성비 선택의 효과** — 「X 만으로 코퍼스를 만들면 R_x 를 보고한다」는
   측정 절차에 대한 참인 진술이다. CI 폭과 무관하게 성립한다.
2. **분류 간 차이가 실재하는가** — 이건 **모집단에 대한 주장**이라 표본이
   필요하다. **decoy 단위 순열 검정**으로 분류 전체를 한 번에 본다 - 「분류마다
   물리는 decoy 비율이 같다」로 설명되면 "분류마다 다르다"고 말하지 않는다.
   🔴 극단 두 분류의 구간만 견주지 않는다. 14종에서 극단을 고르면 다중 비교가 되고,
      지적 단위로 세면 decoy 하나의 지적 여럿이 독립 시행으로 셈해진다.
      [실측 · 모의실험] 차이가 없을 때 「실재한다」가 나오는 비율 - 그 방식 최대 37.6%,
      이 검정 3.4~4.4% (DESIGN §3.5).

🔴 2가 성립하지 않는데 1의 범위를 「도구의 오탐률 범위」처럼 제시하면
   그게 바로 이 프로젝트가 비판하는 과장이다. `heterogeneity_verdict` 가
   그 구분을 강제한다.

decoy 150 목표(`metrics.TARGET_NEGATIVES`)는 집계 FPR 의 정밀도와 분류당 최소 10쌍을
함께 채우는 값이다. 🔴 이질성 검정의 검정력은 150 에서도 높지 않다 - [실측 · 모의실험]
14종 물림이 5~50% 로 고르게 퍼져 있어도 69% 다. 기각하지 못하면 「분류마다 같다」가
아니라 「이 표본으로는 모른다」다.
"""

from __future__ import annotations

import itertools
import random
from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
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

TARGET_PAIRS_PER_KIND = 10
"""🔴 분류당 **미리 선언한** 목표 쌍 수. 14종 x 10 = 140 쌍.

왜 미리 선언하는가 - **optional stopping 을 막기 위해서다.**

구성비 표를 보면 「어느 분류에 decoy 를 더 넣으면 검정이 유의해지겠다」가
바로 보인다. 그런데 **유의해질 때까지 표본을 늘리다 유의하면 멈추는 것**은
통계적으로 부정이다 - 어떤 잡음이든 충분히 들여다보면 원하는 모양이 한 번은 나온다.

그래서 **분류마다 같은 목표치를 먼저 박아 두고, 도달한 뒤에 본다.**
「아직 목표 미달」은 결과가 아니라 진행률이다. `underpowered_kinds` 가
그 구분을 표에 강제한다.
"""

PERMUTATIONS = 9999
"""이질성 순열 검정의 반복 수. 🔴 시드와 함께 고정한다 - 생성물이 실행마다 달라지면
「최신인가」를 물을 수 없다 (F5b). [실측] 150 decoy 에서 0.24초."""

PERMUTATION_SEED = 0

ALPHA = 0.05


@lru_cache(maxsize=256)
def homogeneity_p(counts: tuple[tuple[int, int], ...]) -> float | None:
    """「분류마다 물리는 decoy 비율이 같다」의 순열 p값 - `(물린 decoy, decoy)` 를 분류마다.

    🔴 단위는 decoy 다. 지적은 독립 시행이 아니다 - decoy 하나가 여럿을 낸다.
    🔴 분류 전체를 한 번에 본다. 극단 두 분류를 골라 견주면 다중 비교가 된다.

    통계량은 분류별 물린 수의 카이제곱 (전체 비율이 순열에서 변하지 않으므로 상수배는 뺐다).
    물린 decoy 가 없거나 전부면 변동이 없어 None.
    """
    sizes = [n for _, n in counts]
    bitten = sum(k for k, _ in counts)
    total = sum(sizes)
    if len(counts) < MIN_KINDS_FOR_COMPARISON or bitten in (0, total):
        return None
    rate = bitten / total

    def stat(hits: Sequence[int]) -> float:
        return sum((h - n * rate) ** 2 / n for h, n in zip(hits, sizes, strict=True))

    observed = stat([k for k, _ in counts])
    flags = [1] * bitten + [0] * (total - bitten)
    bounds = list(itertools.accumulate(sizes, initial=0))
    rng = random.Random(PERMUTATION_SEED)  # noqa: S311 - 재표집용이다. 재현이 목적이다
    extreme = 0
    for _ in range(PERMUTATIONS):
        rng.shuffle(flags)
        if stat([sum(flags[a:b]) for a, b in itertools.pairwise(bounds)]) >= observed - 1e-9:
            extreme += 1
    return (extreme + 1) / (PERMUTATIONS + 1)


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
    axis: Axis
    kinds: tuple[KindRate, ...]
    """물림율 내림차순."""

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
    def underpowered_kinds(self) -> tuple[str, ...]:
        """선언한 목표 쌍 수에 못 미친 분류.

        🔴 하나라도 남아 있으면 이질성 판정은 **중간 경과**지 결론이 아니다.
        """
        return tuple(
            k.kind for k in self.kinds if k.samples < TARGET_PAIRS_PER_KIND
        )

    @property
    def homogeneity_p(self) -> float | None:
        """「분류마다 물리는 decoy 비율이 같다」의 순열 p값. 변동이 없으면 None."""
        return homogeneity_p(
            tuple((k.sample_rate.successes, k.sample_rate.total) for k in self.kinds if k.samples)
        )

    @property
    def heterogeneity_verdict(self) -> str:
        """분류 간 차이가 표본 잡음으로 설명되는가 - decoy 단위 순열 검정 (`homogeneity_p`).

        🔴 p 가 유의수준 이상이면 **주장하지 않는다.** 「분류마다 같다」는 뜻도 아니다.
        """
        usable = [k for k in self.kinds if k.samples]
        if len(usable) < MIN_KINDS_FOR_COMPARISON:
            return "판정 불가 - 분류가 2종 미만이다"

        test = (
            f"decoy 단위 순열 검정 · {len(usable)}종 · decoy {sum(k.samples for k in usable)}개 "
            f"· 순열 {PERMUTATIONS}회"
        )
        p = self.homogeneity_p
        if p is None:
            none = not any(k.sample_rate.successes for k in usable)
            return (
                f"분류 간 차이를 **아직 주장할 수 없다** - 물린 decoy 가 "
                f"{'하나도 없다' if none else '전부다'} - 분류 사이에 변동이 없다 ({test})"
            )
        if p < ALPHA:
            verdict = f"분류 간 차이가 **실재한다** - p={p:.4f} ({test})"
            if self.underpowered_kinds:
                # 🔴 목표 미달 상태에서 유의한 것은 **중간 경과**다. 여기서
                #    멈추면 optional stopping 이 된다.
                return (
                    f"{verdict}. ⚠ 다만 {len(self.underpowered_kinds)}종이 아직 "
                    f"분류당 목표 {TARGET_PAIRS_PER_KIND}쌍에 못 미친다 - "
                    "선언한 표본을 다 채운 뒤의 판정이라야 결론이다"
                )
            return verdict
        return (
            f"분류 간 차이를 **아직 주장할 수 없다** - p={p:.4f} ({test}). "
            "같다는 뜻이 아니다 - 이 표본으로는 모른다"
        )

    def render(self) -> str:
        lines = [
            f"  [코퍼스 구성비 민감도 · {self.axis.label}] 채점자={self.grader}",
            f"    🔴 코드도 도구도 채점자도 그대로다. **{self.axis.label} 구성비만** 바꾼다.",
            "",
            f"    {self.axis.label:24s} {'물림':>4} {'지적':>5} {'범위밖':>6}"
            f"  {'물림율':>7} [95% CI]        {'decoy':>6} [95% CI]",
        ]
        for k in self.kinds:
            iv = k.interval
            band = f"[{iv[0]:5.1%}, {iv[1]:5.1%}]" if iv else "     n/a       "
            point = f"{k.rate.point:6.1%}" if k.rate.point is not None else "   n/a"
            sp = k.sample_rate
            per_sample = (
                f"{sp.successes}/{sp.total}" if sp.total else "0/0"
            )
            siv = sp.interval
            sband = f"[{siv[0]:5.1%}, {siv[1]:5.1%}]" if siv else "n/a"
            lines.append(
                f"    {k.kind:24s} {k.rate.successes:>4} {k.rate.total:>5} "
                f"{k.undecided:>6}  {point} {band} {per_sample:>6} {sband}"
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
        if self.underpowered_kinds:
            short = len(self.underpowered_kinds)
            lines.append(
                f"    📋 진행률: {len(self.kinds) - short}/{len(self.kinds)}종이 "
                f"선언 목표({TARGET_PAIRS_PER_KIND}쌍/분류) 달성. "
                "🔴 목표는 **미리** 박아 둔 값이다 - 유의해질 때까지 "
                "늘리다 멈추면 optional stopping 이다"
            )
        lines.append(
            "    ⚠ 지적 단위 CI 는 실제보다 좁다 - decoy 하나가 여러 지적을 내므로"
        )
        lines.append(
            "      독립 시행이 아니다. 판정은 오른쪽 decoy 열(샘플 단위)로 한다."
        )
        return "\n".join(lines)


class Axis(StrEnum):
    """무엇으로 나눌 것인가. 🔴 두 축은 **직교**한다.

    `TRAP` 은 「안전 주장이 어떤 종류의 논증인가」,
    `SHAPE` 는 「가드를 찾으려면 어디를 봐야 하는가」다.
    한 축만 고르게 채워도 다른 축이 쏠릴 수 있으므로 **둘 다** 잰다.
    """

    TRAP = "trap"
    SHAPE = "shape"

    @property
    def label(self) -> str:
        return "미끼 분류" if self is Axis.TRAP else "가드 위치"


def mix_sensitivity(
    outcomes: Sequence[SampleOutcome],
    samples: Sequence[LabeledSample],
    grader: str,
    axis: Axis = Axis.TRAP,
) -> MixSensitivity:
    """증명된 음성만 모아 축별 물림율을 낸다.

    🔴 음성만 본다. 양성(twin)의 지적을 섞으면 FP율이 아니라 다른 숫자가 된다.
    🔴 단일 실행 결과를 받는다 - 다회 실행이면 「물린 decoy」가 N회의 합집합이 된다 (F6).
       에이전트에 쓰려면 decoy 마다 「N회 중 물린 비율」을 단위로 바꾼다.
       지금 호출처는 정적분석기뿐이다.
    """
    kind_of = _kinds(samples, axis)
    fp: dict[str, int] = defaultdict(int)
    total: dict[str, int] = defaultdict(int)
    undecided: dict[str, int] = defaultdict(int)
    seen: dict[str, set[str]] = defaultdict(set)
    bitten: dict[str, set[str]] = defaultdict(set)

    for o in outcomes:
        if not o.is_proven_safe:
            continue
        kind = kind_of.get(o.sample_id, UNCLASSIFIED)
        seen[kind].add(o.sample_id)
        for j in o.judgments[grader]:  # 이름이 어긋나면 KeyError - 「물림 0/0」으로 접지 않는다
            # 🔴 분모에서 빼지 않는다. 증명된 음성 위에서는 TP 가 정의상
            #    불가능해서 FP/(TP+FP) 가 항상 100% 다 - 정보가 없다.
            #    범위 밖 지적은 「이 미끼와 무관한 지적」이라 분모에 남아야
            #    「나온 지적 중 몇이 물렸나」가 된다.
            total[kind] += 1
            if j.outcome is Outcome.UNDECIDABLE:
                undecided[kind] += 1
            elif j.outcome is Outcome.FALSE_POSITIVE:
                fp[kind] += 1
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
        axis=axis,
        kinds=kinds,
        observed=Proportion(successes=sum(fp.values()), total=sum(total.values())),
    )


def _kinds(samples: Sequence[LabeledSample], axis: Axis) -> Mapping[str, str]:
    """음성 샘플 id -> 그 축에서의 값."""
    field = "category" if axis is Axis.TRAP else "shape"
    out: dict[str, str] = {}
    for s in samples:
        if s.safety is None:
            continue
        value = getattr(s.safety, field, None)
        if value:
            out[s.sample_id] = value
    return out
