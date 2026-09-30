"""측정값 문서를 **생성**한다 - 산문에 베껴 쓰지 않는다.

🔴 왜 필요한가.

코퍼스가 자랄 때마다 README · DESIGN · CLAUDE.md 세 곳의 숫자를 손으로
고쳐야 했다. 19 -> 25 -> 37 -> 43 쌍을 거치며 **매번 문서 일관성 테스트가
낡은 숫자를 잡았다.** 그 테스트가 제 일을 한 것이지만, 반복되는 것은 신호다 -
**변동하는 측정값을 산문에 박아 둔 것**이 원인이다.

→ 측정값은 여기서 **생성**한다. 문서는 안정된 주장만 산문으로 쓰고 숫자는
  이 파일을 가리킨다. 그러면 코퍼스가 자라도 산문이 낡지 않는다.

🔴 **생성물은 손으로 고치지 않는다.** 고치면 그 순간 이 설계가 무의미해지므로,
   파일 맨 위에 그 사실을 박고 테스트가 최신인지 확인한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from codeproof_ai.eval.grading.base import Outcome
from codeproof_ai.eval.metrics import credibility_warning
from codeproof_ai.eval.mix import Axis, mix_sensitivity
from codeproof_ai.eval.multirun import (
    EXPECTATION_LABEL,
    RESAMPLES,
    SEED,
    at_least,
    expectation,
    thresholds,
)
from codeproof_ai.eval.pairing import (
    PairVerdict,
    discrimination_rate,
    pair_summary,
    score_pairs,
)
from codeproof_ai.eval.sensitivity import sweep_views
from codeproof_ai.eval.spread import compute_spread

if TYPE_CHECKING:
    from collections.abc import Sequence

    from codeproof_ai.eval.grading.base import Grader
    from codeproof_ai.eval.metrics import Proportion
    from codeproof_ai.eval.runner import ReviewerRun
    from codeproof_ai.eval.sample import LabeledSample

BANNER = (
    "<!-- 🔴 생성된 파일이다. 손으로 고치지 마라. "
    "`uv run codeproof report --out docs/MEASUREMENTS.md` 로 다시 만든다. -->"
)

HEADLINE_GRADER = "provable_safety"


@dataclass(frozen=True, slots=True)
class AgentSection:
    """생성물에 싣는 에이전트 실행 하나 - 저장소의 출력을 import 와 같은 경로로 재생한 것."""

    run: ReviewerRun
    graders: tuple[Grader, ...]
    rejected: int
    """파서가 버린 지적 수. 🔴 버린 지적은 미탐지와 구별되지 않는다 - 세어서 싣는다."""


def render_measurements(
    run: ReviewerRun,
    samples: Sequence[LabeledSample],
    graders: Sequence[Grader],
    agents: Sequence[AgentSection] = (),
) -> str:
    """측정값 문서 전체.

    🔴 **내용에 영향 없는 변화에는 바뀌지 않아야 한다.** 그래야 「최신인가」를
       물을 수 있다. 그래서 넣지 않는 것:

       · 시각 · `run_id` - 매 실행마다 달라진다
       · `config_hash` - **하네스 커밋**이 들어 있어 무관한 커밋마다 달라진다
         [실측] harness_sha 를 진짜 SHA 로 고친 직후 이 파일이 커밋마다
         낡은 것으로 잡혔다. 내 수정이 만든 2차 문제였다.

       대신 `corpus_hash` 를 싣는다 - 샘플 내용에서 나오므로 **코퍼스가
       바뀔 때만** 바뀐다. 실행 단위 추적은 `runs.db` 와 `measure` 출력이 한다.
    """
    negatives = sum(1 for s in samples if s.is_proven_safe)
    parts = [
        BANNER,
        "",
        "# 측정값",
        "",
        f"정적분석기 리뷰어 `{run.reviewer}` ({run.manifest.model_id}) · "
        f"설정 `{run.manifest.params_sent.get('reviewer_config', '?')}`",
        "",
        f"코퍼스 **{negatives}쌍** · `corpus_hash` `{run.manifest.corpus_hash}`",
        "",
        _spread_section(run, graders),
        _pairs_section(run),
        _mix_section(run, samples),
        *(_agent_section(a, samples) for a in agents),
        _caveats(negatives, agents=bool(agents)),
    ]
    return "\n".join(parts).rstrip() + "\n"


def _spread_section(run: ReviewerRun, graders: Sequence[Grader]) -> str:
    defs = {g.name: g.definition for g in graders}
    fp_capable = {g.name for g in graders if Outcome.FALSE_POSITIVE in g.emits}
    sp = compute_spread(run.outcomes, defs, fp_capable, negatives_only=True)

    lines = [
        "## 채점 기준 편차 — 헤드라인",
        "",
        f"증명된 음성 위의 **같은 지적 {sp.findings}건**을 서로 다른 정답 정의로 "
        "채점했다. **지적은 하나도 바뀌지 않았다.**",
        "",
        "| 채점자 | TP | FP | 판정불가 | FP 가능 |",
        "|---|---:|---:|---:|:---:|",
    ]
    for c in sp.columns:
        mark = "o" if c.grader in fp_capable else "x"
        lines.append(
            f"| `{c.grader}` | {c.true_positive} | {c.false_positive} "
            f"| {c.undecidable} | {mark} |"
        )
    lo, hi = sp.fp_range
    ratio = f" — {sp.fp_ratio:.1f}배" if sp.fp_ratio is not None else ""
    lines += [
        "",
        f"🔴 FP 를 낼 수 있는 채점자끼리: **{lo} ~ {hi}**{ratio}. "
        f"정의 선택만으로 생긴 FP: **{sp.disagreement}건**",
        "",
        "> FP 를 구조적으로 낼 수 없는 채점자(합의 기반)는 편차 계산에서 뺀다 — "
        "동의 부재는 반증이 아니므로 그 0 을 넣으면 범주 차이를 편차로 오해한다.",
        "",
    ]
    return "\n".join(lines)


def _pairs_section(run: ReviewerRun) -> str:
    pairs = score_pairs(run.outcomes, HEADLINE_GRADER)
    if not pairs:
        return ""
    hit, total = discrimination_rate(pairs)
    counts = pair_summary(pairs)
    return "\n".join([
        "## 짝 채점 (PrimeVul)",
        "",
        f"**구별 성공 {hit}/{total}** — 안전한 쪽과 터지는 쪽을 갈라낸 경우다.",
        "",
        "| 판정 | 건수 | 뜻 |",
        "|---|---:|---|",
        f"| P-C 구별 | {counts[PairVerdict.CORRECT]} | 양성만 지적 — 유일하게 옳다 |",
        f"| P-V 과잉지적 | {counts[PairVerdict.OVER_FLAG]} | 둘 다 지적 |",
        f"| P-B 미탐지 | {counts[PairVerdict.UNDER_FLAG]} | 둘 다 미지적 |",
        f"| P-R 역전 | {counts[PairVerdict.REVERSED]} | **음성만** 지적 — 거꾸로다 |",
        "",
        "> 지적 단위로만 보면 이 사실이 보이지 않는다. twin 쪽만 세면 "
        "Precision 이 높게 나오는데, 그 TP 는 안전한 쪽에도 똑같이 낸 지적이 "
        "우연히 결함 자리에 걸린 것이다.",
        "",
    ])


def _mix_section(run: ReviewerRun, samples: Sequence[LabeledSample]) -> str:
    lines = ["## 코퍼스 구성비 민감도", ""]
    lines.append(
        "🔴 코드도 도구도 채점자도 그대로다. **구성비만** 바꿔 얼마나 움직이는가."
    )
    for axis in Axis:
        ms = mix_sensitivity(run.outcomes, samples, HEADLINE_GRADER, axis)
        if not ms.kinds:
            continue
        lines += [
            "",
            f"### {axis.label}",
            "",
            f"| {axis.label} | 물림 | 지적 | 물림율 | 95% CI | decoy |",
            "|---|---:|---:|---:|---|---:|",
        ]
        for k in ms.kinds:
            iv = k.interval
            band = f"[{iv[0]:.1%}, {iv[1]:.1%}]" if iv else "n/a"
            point = f"{k.rate.point:.1%}" if k.rate.point is not None else "n/a"
            lines.append(
                f"| `{k.kind}` | {k.rate.successes} | {k.rate.total} | {point} "
                f"| {band} | {k.sample_rate.successes}/{k.sample_rate.total} |"
            )
        reach = ms.reachable
        if reach is None:
            continue
        ratio = f" — {ms.ratio:.1f}배" if ms.ratio is not None else ""
        lines.append("")
        if ms.observed.point is not None and ms.uniform is not None:
            lines.append(
                f"현재 구성비 **{ms.observed.point:.1%}** · "
                f"균등 구성비 {ms.uniform:.1%}"
            )
        lines += [
            f"🔴 구성비만 바꿔 도달 가능: **{reach[0]:.1%} ~ {reach[1]:.1%}**{ratio}",
            "",
            f"⚖ {ms.heterogeneity_verdict}",
        ]
        if ms.underpowered_kinds:
            done = len(ms.kinds) - len(ms.underpowered_kinds)
            lines.append(
                f"📋 {done}/{len(ms.kinds)}종이 선언 목표 달성 — 목표는 "
                "**미리** 박아 둔 값이다. CI 가 갈릴 때까지 늘리다 멈추면 "
                "optional stopping 이다."
            )
    lines.append("")
    return "\n".join(lines)


def _agent_section(agent: AgentSection, samples: Sequence[LabeledSample]) -> str:
    """🔴 다회 실행의 모델 숫자 - 관점마다 라벨을 붙이고 합집합 한 줄로 접지 않는다 (F6)."""
    run = agent.run
    m = run.manifest
    pairs = len(score_pairs(run.outcomes, HEADLINE_GRADER))
    return "\n".join([
        f"## 에이전트 층 — `{run.reviewer}`",
        "",
        f"리뷰어 `{m.model_id}` · 샘플당 **{m.sample_n}회** 실행 · 짝 **{pairs}쌍** · "
        f"캐시 `{m.cache_policy}` · 파서가 버린 지적 {agent.rejected}건",
        "",
        f"설정 `{m.params_sent.get('reviewer_config', '?')}`",
        "",
        "> 🔴 층이 다르다 (`agent`) — 파일 탐색 · 다회 턴 · 툴 사용이 가능해서 "
        "`model_api` 와 조건이 다르다. 위 정적분석기 숫자와 같은 문서에 둘 뿐 "
        "**섞어 집계하지 않는다.**",
        "",
        _views_table(run, agent.graders, samples),
        _sensitivity_views(run, samples),
    ])


def _views_table(
    run: ReviewerRun, graders: Sequence[Grader], samples: Sequence[LabeledSample]
) -> str:
    n = run.manifest.sample_n
    views = thresholds(n)
    lines = [
        "### 짝 채점 (PrimeVul) — 관점별",
        "",
        f"{n}회 실행을 합집합 한 줄로 접지 않는다 — **관점마다 다른 숫자다.** "
        "구별 성공률은 (리뷰어 x 채점자)의 성질이라 채점자마다 따로 낸다.",
        "",
        f"| 채점자 | {EXPECTATION_LABEL} | 실행별 P-C | "
        + " | ".join(label for label, _ in views) + " |",
        "|---|---|---:|" + "---|" * len(views),
    ]
    for g in graders:
        exp = expectation(run.outcomes, samples, g)
        if exp.point is None or exp.interval is None:
            continue
        lo, hi = exp.interval
        cells = " | ".join(_hits(at_least(run.outcomes, samples, g, k)) for _, k in views)
        lines.append(
            f"| `{g.name}` | {exp.point:.1%} [{lo:.1%}, {hi:.1%}] "
            f"| {min(exp.per_run)}~{max(exp.per_run)}/{exp.pairs} | {cells} |"
        )
    lines += [
        "",
        "- **단일 실행 기대값** — 한 번 돌렸을 때 기대하는 구별 성공(P-C). 구간은 짝 단위 "
        f"부트스트랩 95% (재표집 {RESAMPLES} · 시드 {SEED}). **실행별 P-C** 의 폭도 "
        "측정값이다 — 같은 설정의 모델 실행은 흔들린다.",
        "- **k-임계** — k회 이상 나온 지적만 센다. 구간은 Wilson 95%. "
        "N회 실행을 요구하는 **기법**이지 기준선이 아니다.",
        "",
    ]
    return "\n".join(lines)


def _hits(p: Proportion) -> str:
    """`39/60 · 65.0% [52.4%, 75.8%]` - 개수와 구간을 같이 싣는다."""
    iv = p.interval
    if p.point is None or iv is None:
        return "n/a"
    return f"{p.successes}/{p.total} · {p.point:.1%} [{iv[0]:.1%}, {iv[1]:.1%}]"


def _sensitivity_views(run: ReviewerRun, samples: Sequence[LabeledSample]) -> str:
    """🔴 slack 스윕도 관점마다 낸다 - `sweep()` 은 합집합으로 센다 (A2a · F6)."""
    vs = sweep_views(run.outcomes, samples)
    if vs is None:
        return ""
    labels = [EXPECTATION_LABEL, *vs.thresholds]
    lines = [
        f"### 매칭 민감도 — 관점별 (`{HEADLINE_GRADER}`)",
        "",
        "지적은 그대로 두고 **채점만** slack 을 바꿔 다시 했다 — 리뷰어를 다시 돌리면 "
        "slack 효과와 실행 변동이 섞인다. 위 표는 slack 0 이다.",
        "",
        "| slack | " + " | ".join(labels) + " |",
        "|---:|" + "---:|" * len(labels),
    ]
    for p in vs.points:
        counts = (f"{t.successes}/{t.total}" for t in p.thresholds)
        lines.append(f"| {p.slack} | " + " | ".join([f"{p.expectation:.1%}", *counts]) + " |")
    lines.append("")
    if vs.moved:
        lines.append(
            f"🔴 흔들린다 — {' · '.join(vs.moved)} 의 구별 성공이 slack 에 따라 바뀐다. "
            "단일 slack 값으로 낸 숫자를 결론으로 쓰지 않는다."
        )
    else:
        lines.append("o 모든 관점에서 안정 — 구별 성공이 매칭 정책의 산물이 아니다.")
    lines.append("")
    return "\n".join(lines)


def _caveats(negatives: int, *, agents: bool = False) -> str:
    lines = ["## 이 숫자를 읽는 법", ""]
    if warning := credibility_warning(negatives):
        lines += [f"⚠️ {warning}", ""]
    lines += [
        "- 지적 단위 CI 는 실제보다 좁다 — decoy 하나가 여러 지적을 내므로 "
        "독립 시행이 아니다. decoy 열(샘플 단위)을 같이 본다.",
        "- 증명된 음성 위에서 `FP/(TP+FP)` 는 정의상 항상 100% 다 "
        "(TP 가 불가능하다). 물림율의 분모는 **나온 지적 전부**다.",
    ]
    if not agents:
        lines.append(
            "- 이 숫자는 **정적분석기**의 것이다. 모델 리뷰어는 자격증명이 있어야 "
            "돌고, 층(`ReviewerKind`)이 다르면 섞어 집계하지 않는다."
        )
        return "\n".join(lines)
    lines += [
        "- 정적분석기 절과 에이전트 층 절은 층(`ReviewerKind`)이 달라 **섞어 집계하지 "
        "않는다** — 같은 문서에 나란히 둘 뿐이다. 모델 API 층(`model_api`)은 자격증명이 "
        "있어야 돌고 여기 싣지 않았다.",
        "- 에이전트 숫자는 확률적이다 — seed 도 temperature 도 없어 같은 설정을 다시 돌리면 "
        "흔들린다. 재현되는 것은 출력이 아니라 **프로토콜**이고, 설정은 실행 기록 "
        "(`RUN.json`)에 있다.",
        "- 단일 실행 기대값과 k-임계는 **다른 숫자**다 — 관점이 다른 값끼리 비교하지 않는다.",
    ]
    return "\n".join(lines)
