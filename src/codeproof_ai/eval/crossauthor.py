"""교차 저자 측정의 선언한 분석 - 결과를 보기 전에 고정한다 (DESIGN §7.10d 준비 ⑧).

codex 가 설계한 쌍에서도 claude 가 결함을 더 짚는가. 셈은 목표 150쌍 비교와 **같다** -
같은 짝 판정 · 같은 부트스트랩 · 같은 사다리 · 「흔들린다」의 같은 정의 (`Difference.reading`).

    주 지표       `provable_safety` · slack 0 · 단일 실행 기대값 짝 차이 (claude - codex) · P-C
    twin 쪽 차이  같은 셈 · 판정 묶음만 P-C · P-V (twin 을 짚었다)
    읽는 법       `read` - ① 둘 다 사다리 전체에서 0 보다 크다 · 주 지표만 크다 ·
                  ② 0 을 품는다 · ③ 0 보다 작다 · 주 지표의 부호나 판정이 사다리에서
                  바뀌면 「흔들린다」 (§7.10b 와 같다)
    기술          짝 판정 분해 · 분류별 차이 · 샘플당 지적 수 · 목표 150쌍과의 크기 -
                  주장하지 않는다
    민감도        위협 모델 안 라벨 문제가 있는 쌍을 뺀 주 지표 - 판정자마다 한 줄

🔴 측정 뒤에 고를 손잡이를 남기지 않는다. 지표 · 사다리 · 읽는 법 · 거절 조건이 전부 이 모듈의
   상수와 함수다 - 결과를 본 뒤 바꾸면 커밋 기록에 남는다. 선언과 다른 입력(회차 · 손잡이 ·
   설정 · 분류 구성)은 `problems` 가 거절한다 - 「미완」이고 그때까지의 값도 내지 않는다.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from statistics import fmean
from typing import TYPE_CHECKING

from codeproof_ai.eval.glance import CAUGHT
from codeproof_ai.eval.grading.safety import ProvableSafetyGrader
from codeproof_ai.eval.multirun import (
    CORRECT_ONLY,
    RESAMPLES,
    SEED,
    difference_of,
    expectation_of,
    mean_interval,
    mean_share,
    pair_differences,
    verdicts_by_run,
)
from codeproof_ai.eval.pairing import PairVerdict
from codeproof_ai.eval.report import SETUP_KEYS, comparable
from codeproof_ai.eval.sensitivity import DEFAULT_SWEEP

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from codeproof_ai.eval.multirun import Difference
    from codeproof_ai.eval.report import AgentSection
    from codeproof_ai.eval.runner import ReviewerRun
    from codeproof_ai.eval.sample import LabeledSample

    Verdicts = list[dict[str, PairVerdict]]
    Scored = dict[int, tuple[Verdicts, Verdicts]]

BANNER = (
    "<!-- 🔴 생성된 파일이다. 손으로 고치지 마라. "
    "`uv run codeproof xauthor-report` 로 다시 만든다. -->"
)

RUNS = 3
"""선언한 회차 (§7.10d 「측정」)."""
DOCSTRINGS = "neutral"
"""선언한 docstring 손잡이 - 목표 150쌍 측정과 같다."""
PAIRS_PER_KIND = 8
"""분류마다 쌍 수 - 채우지 못한 분류는 통째로 뺀다 (§7.10d 「2단계」)."""
MIN_KINDS = 8
"""남은 분류가 이보다 적으면 「미완」이다 - 10 에서 낮췄다 (수집 중 보정 2026-10-09 ·
안전 필터 거절이 분류를 닫았다 · 측정값 없이 · DESIGN §7.10d)."""

PRIMARY = CORRECT_ONLY
"""주 지표의 판정 묶음 - 구별 성공(P-C)."""
TWIN = frozenset(CAUGHT)
"""twin 쪽 차이의 판정 묶음 - twin 을 짚은 짝 (P-C · P-V)."""

VERDICT_NAMES = {
    PairVerdict.CORRECT: "P-C 구별",
    PairVerdict.OVER_FLAG: "P-V 둘 다 지적",
    PairVerdict.UNDER_FLAG: "P-B 결함을 놓침",
    PairVerdict.REVERSED: "P-R 거꾸로",
}


def score(a: AgentSection, b: AgentSection, samples: Sequence[LabeledSample]) -> Scored:
    """slack 사다리마다 두 리뷰어의 실행별 짝 판정 - 한 번 채점해 모든 판정 묶음에 쓴다."""
    return {
        s: (
            verdicts_by_run(a.run.outcomes, samples, ProvableSafetyGrader(overlap_slack=s)),
            verdicts_by_run(b.run.outcomes, samples, ProvableSafetyGrader(overlap_slack=s)),
        )
        for s in DEFAULT_SWEEP
    }


@dataclass(frozen=True, slots=True)
class Rung:
    """사다리 한 칸 - 그 slack 에서의 두 리뷰어 값과 짝 차이."""

    slack: int
    a: float
    b: float
    difference: Difference


def ladder(scored: Scored, hits: frozenset[PairVerdict]) -> tuple[Rung, ...]:
    """선언한 사다리 (0,2,5,10) 의 차이 - 첫 칸이 주 지표의 slack 0 이다."""
    rungs = []
    for slack in DEFAULT_SWEEP:
        va, vb = scored[slack]
        a, b = mean_share(va, hits), mean_share(vb, hits)
        if a is None or b is None:
            msg = "짝이 없다 - 빈 실행은 읽을 것이 없다"
            raise ValueError(msg)
        rungs.append(Rung(slack, a, b, difference_of(va, vb, hits)))
    return tuple(rungs)


class Reading(StrEnum):
    """§7.10d 「읽는 법」의 갈래 - 문장은 `READINGS` 에 선언 그대로 둔다."""

    BOTH = "①"
    PRIMARY_ONLY = "① (twin 쪽 미확인)"
    INDISTINCT = "②"
    CODEX_AHEAD = "③"
    SHAKY = "흔들린다"


READINGS = {
    Reading.BOTH: (
        "codex 가 쓴 쌍에서도 claude 가 결함을 더 짚는다",
        "저자 패밀리의 설계 친숙도만으로는 우위가 설명되지 않는다.",
    ),
    Reading.PRIMARY_ONLY: (
        "twin 쪽으로 확인되지 않은 우위",
        "주 지표는 0 보다 크지만 twin 쪽 차이가 사다리 전체에서 0 보다 크지 않다 - decoy 쪽에서 "
        "생겼다면 저자의 미끼를 같은 모델이 더 문 것으로도 설명된다.",
    ),
    Reading.INDISTINCT: (
        "codex 가 쓴 쌍에서 구별되지 않는다",
        "claude 쪽 편향인지 codex 의 자기 우위인지 가르지 못한다. 놓친 차이는 「없다」가 아니라 "
        "「모른다」다.",
    ),
    Reading.CODEX_AHEAD: (
        "codex 가 쓴 쌍에서는 codex 가 앞선다",
        "목표 150쌍 결과와 나란히 놓으면 저자 의존을 시사하지만 쌍 · 과정 · 시기가 달라 "
        "주장하지 않는다.",
    ),
    Reading.SHAKY: (
        "흔들린다",
        "slack 사다리에서 주 지표의 부호나 판정이 바뀐다 - 결론으로 쓰지 않는다 "
        "(§7.10b 와 같은 규칙).",
    ),
}


def _bounds(d: Difference) -> tuple[float, float]:
    if d.interval is None:
        msg = "구간이 없다 - 짝 0 은 읽을 것이 없다"
        raise ValueError(msg)
    return d.interval


def read(primary: Sequence[Rung], twin: Sequence[Rung]) -> Reading:
    """§7.10d 「읽는 법」 - 주 지표가 사다리에서 흔들리면 결론이 없다.

    「0 보다 크다」는 구간이 0 보다 크다는 뜻이다. 주 지표는 흔들리지 않으면 사다리 전체가 첫 칸과
    같은 판정이고, twin 쪽 차이는 **사다리 모든 칸**에서 구간이 0 보다 커야 한다.
    """
    if len({r.difference.reading for r in primary}) > 1:
        return Reading.SHAKY
    lo, hi = _bounds(primary[0].difference)
    if hi < 0:
        return Reading.CODEX_AHEAD
    if lo <= 0:
        return Reading.INDISTINCT
    if all(_bounds(r.difference)[0] > 0 for r in twin):
        return Reading.BOTH
    return Reading.PRIMARY_ONLY


def _only(verdicts: Verdicts, pairs: frozenset[str]) -> Verdicts:
    return [{p: v for p, v in run.items() if p in pairs} for run in verdicts]


def by_kind(
    strict: tuple[Verdicts, Verdicts], kinds: Mapping[str, str]
) -> tuple[tuple[str, int, Rung], ...]:
    """분류마다 주 지표 (slack 0) - 쌍이 적어 구간이 넓다. 기술이다."""
    rows = []
    for kind in sorted(set(kinds.values())):
        pairs = frozenset(p for p, k in kinds.items() if k == kind)
        va, vb = (_only(v, pairs) for v in strict)
        a, b = mean_share(va, PRIMARY), mean_share(vb, PRIMARY)
        if a is None or b is None:
            continue
        rows.append((kind, len(pairs), Rung(DEFAULT_SWEEP[0], a, b, difference_of(va, vb))))
    return tuple(rows)


def without(strict: tuple[Verdicts, Verdicts], excluded: frozenset[str]) -> Rung:
    """민감도 - 뺀 쌍 없이 다시 낸 주 지표 (slack 0)."""
    va, vb = (_only(v, frozenset(v[0]) - excluded) for v in strict)
    a, b = mean_share(va, PRIMARY), mean_share(vb, PRIMARY)
    if a is None or b is None:
        msg = "남은 짝이 없다"
        raise ValueError(msg)
    return Rung(DEFAULT_SWEEP[0], a, b, difference_of(va, vb))


@dataclass(frozen=True, slots=True)
class Mean:
    """평균과 부트스트랩 95% - 기술 통계에도 구간을 같이 낸다 (I)."""

    n: int
    point: float
    interval: tuple[float, float]


def findings_per_sample(run: ReviewerRun, *, decoy: bool) -> Mean:
    """샘플당 지적 수 (회차 평균) - decoy · twin 쪽을 따로. 샘플 하나가 복원추출 단위다."""
    values = [
        o.observations.mean_findings_per_run for o in run.outcomes if o.is_proven_safe is decoy
    ]
    return Mean(len(values), fmean(values), mean_interval(values))


def gap(
    xs: Sequence[float], ys: Sequence[float], *, resamples: int = RESAMPLES, seed: int = SEED
) -> Mean:
    """두 코퍼스의 짝 차이 평균의 차이 (xs - ys) - 쌍이 달라 **따로** 복원추출한다."""
    rng = random.Random(seed)  # noqa: S311 - 재표집용이다. 보안 난수가 아니고 재현이 목적이다
    boots = sorted(
        fmean(rng.choices(xs, k=len(xs))) - fmean(rng.choices(ys, k=len(ys)))
        for _ in range(resamples)
    )
    lo, hi = boots[round(0.025 * (resamples - 1))], boots[round(0.975 * (resamples - 1))]
    return Mean(len(xs), fmean(xs) - fmean(ys), (lo, hi))


def kinds_of(samples: Sequence[LabeledSample]) -> dict[str, str]:
    """짝(decoy 샘플 id) -> 미끼 분류."""
    return {
        s.sample_id: s.safety.category or "?" for s in samples if s.safety is not None
    }


def pick(
    sections: Sequence[AgentSection], docstrings: str | None = None
) -> tuple[AgentSection, AgentSection] | None:
    """claude · codex 한 쌍 - 손잡이가 같고 같은 샘플을 잰 것. 없거나 여럿이면 None."""
    found = [
        (a, b)
        for a in sections
        for b in sections
        if a.agent == "claude"
        and b.agent == "codex"
        and comparable(a, b)
        and (docstrings is None or a.docstrings == docstrings)
    ]
    return found[0] if len(found) == 1 else None


def problems(
    pair: tuple[AgentSection, AgentSection],
    reference: tuple[AgentSection, AgentSection],
    samples: Sequence[LabeledSample],
    issues: Mapping[str, frozenset[str]],
) -> list[str]:
    """선언과 다른 입력 - 하나라도 있으면 「미완」이고 값을 내지 않는다 (§7.10d 「측정」)."""
    out: list[str] = []
    for x, r in zip(pair, reference, strict=True):
        name = x.run.reviewer
        if x.run.manifest.sample_n != RUNS:
            out.append(f"`{name}` 가 {x.run.manifest.sample_n}회다 - 선언은 {RUNS}회")
        if x.docstrings != DOCSTRINGS:
            out.append(f"`{name}` 의 docstring 손잡이가 `{x.docstrings}` - 선언은 `{DOCSTRINGS}`")
        if x.unmeasured_pairs:
            out.append(
                f"`{name}` 가 코퍼스의 {x.unmeasured_pairs}쌍을 재지 않았다 - 측정은 쌍 전부다"
            )
        theirs, ours = dict(r.setup), dict(x.setup)
        differs = [
            f"`{k}` {theirs.get(k, '?')} → {ours.get(k, '?')}"
            for k in SETUP_KEYS
            if theirs.get(k) != ours.get(k)
        ]
        if differs:
            out.append(
                f"`{name}` 의 설정이 목표 150쌍 측정(`{r.run.reviewer}`)과 다르다 - "
                + " · ".join(differs)
            )
    kinds = kinds_of(samples)
    counts = Counter(kinds.values())
    off = [f"`{k}` {n}쌍" for k, n in sorted(counts.items()) if n != PAIRS_PER_KIND]
    if off:
        out.append(f"분류마다 {PAIRS_PER_KIND}쌍이어야 한다 - " + " · ".join(off))
    if len(counts) < MIN_KINDS:
        out.append(f"분류가 {len(counts)}개다 - {MIN_KINDS} 미만이면 「미완」")
    for who, ids in sorted(issues.items()):
        unknown = sorted(ids - kinds.keys())
        if unknown:
            out.append(f"라벨 문제 목록 `{who}` 에 코퍼스에 없는 쌍이 있다 - {unknown[:3]}")
    return out


# ── 문서 ────────────────────────────────────────────────────────────────────


def _pp(x: float) -> str:
    return f"{x * 100:+.1f}%p"


def _iv(interval: tuple[float, float] | None) -> str:
    """차이의 구간 - %p 로 (뒤에 붙인다)."""
    if interval is None:
        return "n/a"
    lo, hi = interval
    return f"[{lo * 100:+.1f}, {hi * 100:+.1f}]"


def _verdict(d: Difference) -> str:
    return "구별된다" if d.distinguishable else "구별되지 않는다"


def _rung_row(label: str, r: Rung) -> str:
    d = r.difference
    return (
        f"| {label} | {r.slack} | {r.a:.1%} | {r.b:.1%} | {_pp(d.point or 0.0)} | "
        f"{_iv(d.interval)}%p | {_verdict(d)} |"
    )


def _verdict_section(primary: Sequence[Rung], twin: Sequence[Rung]) -> list[str]:
    reading = read(primary, twin)
    head, why = READINGS[reading]
    return [
        "## 판정",
        "",
        f"> **{reading.value} {head}** — {why}",
        "",
        "| 지표 | slack | claude | codex | 차이 (claude - codex) | 95% 구간 | 판정 |",
        "|---|---:|---:|---:|---:|---|---|",
        *(_rung_row("주 지표 (P-C)", r) for r in primary),
        *(_rung_row("twin 쪽 (P-C · P-V)", r) for r in twin),
        "",
        "읽는 법은 수집 전에 선언한 그대로다 (DESIGN §7.10d) — ① 주 지표와 twin 쪽 차이가 "
        "둘 다 사다리 전체에서 0 보다 크면 「codex 가 쓴 쌍에서도 claude 가 결함을 더 짚는다」 · "
        "주 지표만 크면 「twin 쪽으로 확인되지 않은 우위」 · ② 주 지표가 0 을 품으면 "
        "「구별되지 않는다」 · ③ 0 보다 작으면 「codex 가 앞선다」. 사다리에서 주 지표의 부호나 "
        "판정이 바뀌면 「흔들린다」이고 결론으로 쓰지 않는다. 구간은 같은 짝을 두 리뷰어가 함께 "
        f"복원추출하는 부트스트랩 95% (재표집 {RESAMPLES} · 시드 {SEED}).",
        "",
    ]


def _decomposition(strict: tuple[Verdicts, Verdicts]) -> list[str]:
    rows = []
    for v in PairVerdict:
        cells = []
        for side in strict:
            e = expectation_of(side, frozenset({v}))
            if e.point is None or e.interval is None:
                cells.append("n/a")
                continue
            lo, hi = e.interval
            cells.append(f"{e.point:.1%} [{lo:.1%}, {hi:.1%}]")
        rows.append(f"| {VERDICT_NAMES[v]} | {cells[0]} | {cells[1]} |")
    return [
        "### 짝 판정 분해 (slack 0 · 단일 실행 기대값)",
        "",
        "| 짝 판정 | claude | codex |",
        "|---|---:|---:|",
        *rows,
        "",
        "구간은 짝 단위 부트스트랩 95%. P-C 가 주 지표, P-C + P-V 가 twin 쪽이다.",
        "",
    ]


def _kinds_section(strict: tuple[Verdicts, Verdicts], kinds: Mapping[str, str]) -> list[str]:
    rows = [
        f"| `{kind}` | {n} | {r.a:.1%} | {r.b:.1%} | {_pp(r.difference.point or 0.0)} | "
        f"{_iv(r.difference.interval)}%p |"
        for kind, n, r in by_kind(strict, kinds)
    ]
    return [
        "### 분류별 차이 (주 지표 · slack 0)",
        "",
        "| 분류 | 쌍 | claude | codex | 차이 | 95% 구간 |",
        "|---|---:|---:|---:|---:|---|",
        *rows,
        "",
        "분류마다 쌍이 적어 구간이 넓다 — 분류끼리 견주지 않는다 (F5a).",
        "",
    ]


def _findings_section(a: ReviewerRun, b: ReviewerRun) -> list[str]:
    rows = []
    for label, decoy in (("decoy (안전한 코드)", True), ("twin (결함 코드)", False)):
        cells = []
        for run in (a, b):
            m = findings_per_sample(run, decoy=decoy)
            cells.append(f"{m.point:.2f} [{m.interval[0]:.2f}, {m.interval[1]:.2f}]")
        rows.append(f"| {label} | {cells[0]} | {cells[1]} |")
    return [
        "### 샘플당 지적 수 (회차 평균)",
        "",
        "| 쪽 | claude | codex |",
        "|---|---:|---:|",
        *rows,
        "",
        "twin 쪽 차이는 넓게 · 많이 짚는 쪽에 유리하다 — 저자와 무관한 관례다. 구간은 샘플 단위 "
        "부트스트랩 95%.",
        "",
    ]


def _size_section(scored: Scored, reference: Scored) -> list[str]:
    rows = []
    s0 = DEFAULT_SWEEP[0]
    ref_pairs = len(reference[s0][0][0])
    for label, hits in (("주 지표 (P-C)", PRIMARY), ("twin 쪽 (P-C · P-V)", TWIN)):
        xs = list(pair_differences(*scored[s0], hits).values())
        ys = list(pair_differences(*reference[s0], hits).values())
        g = gap(xs, ys)
        rows.append(
            f"| {label} | {_pp(fmean(xs))} | {_pp(fmean(ys))} | {_pp(g.point)} | "
            f"{_iv(g.interval)}%p |"
        )
    return [
        f"### 목표 150쌍 결과와의 크기 (slack {s0})",
        "",
        f"| 지표 | 이 코퍼스 | 목표 150쌍 ({ref_pairs}쌍) | 크기 차이 | 95% 구간 |",
        "|---|---:|---:|---:|---|",
        *rows,
        "",
        "쌍 · 과정 · 시기가 달라 기술만 한다 — 두 코퍼스의 쌍이 달라 구간은 **따로** 복원추출한 "
        f"부트스트랩 95% (재표집 {RESAMPLES} · 시드 {SEED}).",
        "",
    ]


def _sensitivity_section(
    strict: tuple[Verdicts, Verdicts], issues: Mapping[str, frozenset[str]], where: str
) -> list[str]:
    head = [
        "## 민감도 — 위협 모델 안 라벨 문제가 있는 쌍을 뺀 주 지표",
        "",
    ]
    if not issues:
        return [
            *head,
            f"감사 전 — `{where}` 에 판정자마다 `<이름>.txt` (줄마다 쌍 하나)가 생기면 "
            "여기에 싣는다.",
            "",
        ]
    rows = []
    for who, ids in sorted(issues.items()):
        r = without(strict, ids)
        d = r.difference
        rows.append(
            f"| `{who}` | {len(ids)} | {d.pairs} | {_pp(d.point or 0.0)} | "
            f"{_iv(d.interval)}%p | {_verdict(d)} |"
        )
    return [
        *head,
        "| 판정자 | 뺀 쌍 | 남은 쌍 | 차이 (claude - codex) | 95% 구간 | 판정 |",
        "|---|---:|---:|---:|---|---|",
        *rows,
        "",
        "claude 가 진짜 결함을 짚은 자리를 지우므로 claude 쪽으로 기운다 — 주장은 주 지표만 한다.",
        "",
    ]


def render(
    pair: tuple[AgentSection, AgentSection],
    samples: Sequence[LabeledSample],
    reference: tuple[tuple[AgentSection, AgentSection], Sequence[LabeledSample]],
    issues: Mapping[str, frozenset[str]],
    *,
    corpus: str,
    where: str,
) -> str:
    """선언한 분석 문서 - 값은 전부 여기서 계산한다. `problems` 를 통과한 입력만 받는다."""
    a, b = pair
    scored = score(a, b, samples)
    strict = scored[DEFAULT_SWEEP[0]]
    primary, twin = ladder(scored, PRIMARY), ladder(scored, TWIN)
    kinds = kinds_of(samples)
    ref_pair, ref_samples = reference
    ref_scored = score(*ref_pair, ref_samples)
    setup = dict(a.setup), dict(b.setup)
    lines = [
        BANNER,
        "",
        "# 교차 저자 측정 — codex 가 쓴 쌍",
        "",
        "codex 가 설계한 쌍에서도 claude 가 결함을 더 짚는가. 지표 · 사다리 · 읽는 법은 수집 전에 "
        "선언했고 (DESIGN §7.10d) 이 문서는 그 셈을 그대로 돈다.",
        "",
        f"- 코퍼스 `{corpus}` · **{len(kinds)}쌍** = 분류 {len(set(kinds.values()))} x "
        f"{PAIRS_PER_KIND}",
        "- " + " · ".join(
            f"`{x.run.reviewer}` {st.get('cli_version', '?')} · `{st.get('model', '?')}`"
            for x, st in zip(pair, setup, strict=True)
        )
        + f" · effort `{setup[0].get('effort', '?')}` · 리뷰어마다 {RUNS}회 · "
        f"docstring `{DOCSTRINGS}` — 목표 150쌍 측정과 같은 설정이다",
        f"- 파서가 버린 지적 — `{a.run.reviewer}` {a.rejected}건 · "
        f"`{b.run.reviewer}` {b.rejected}건",
        "- 도구 · 권한이 제품마다 다르다 (codex 는 명령을 실행할 수 있다 · DESIGN §7.10) — "
        "차이에는 모델과 제품이 함께 들어 있다.",
        "",
        *_verdict_section(primary, twin),
        "## 기술 — 주장하지 않는다",
        "",
        *_decomposition(strict),
        *_kinds_section(strict, kinds),
        *_findings_section(a.run, b.run),
        *_size_section(scored, ref_scored),
        *_sensitivity_section(strict, issues, where),
    ]
    return "\n".join(lines)
