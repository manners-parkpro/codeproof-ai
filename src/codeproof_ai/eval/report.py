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

from typing import TYPE_CHECKING

from codeproof_ai.eval.grading.base import Outcome
from codeproof_ai.eval.metrics import credibility_warning
from codeproof_ai.eval.mix import Axis, mix_sensitivity
from codeproof_ai.eval.pairing import (
    PairVerdict,
    discrimination_rate,
    pair_summary,
    score_pairs,
)
from codeproof_ai.eval.spread import compute_spread

if TYPE_CHECKING:
    from collections.abc import Sequence

    from codeproof_ai.eval.grading.base import Grader
    from codeproof_ai.eval.runner import ReviewerRun
    from codeproof_ai.eval.sample import LabeledSample

BANNER = (
    "<!-- 🔴 생성된 파일이다. 손으로 고치지 마라. "
    "`uv run codeproof report --out docs/MEASUREMENTS.md` 로 다시 만든다. -->"
)

HEADLINE_GRADER = "provable_safety"


def render_measurements(
    run: ReviewerRun,
    samples: Sequence[LabeledSample],
    graders: Sequence[Grader],
) -> str:
    """측정값 문서 전체.

    🔴 시각·run_id 를 넣지 않는다. 넣으면 코퍼스가 그대로여도 파일이
       매번 달라져 「최신인가」를 확인할 수 없다. 재현에 필요한 설정은
       `config_hash` 로 충분하다.
    """
    negatives = sum(1 for s in samples if s.is_proven_safe)
    parts = [
        BANNER,
        "",
        "# 측정값",
        "",
        f"리뷰어 `{run.reviewer}` ({run.manifest.model_id}) · "
        f"설정 `{run.manifest.params_sent.get('reviewer_config', '?')}`",
        "",
        f"코퍼스 **{negatives}쌍** · `config_hash` `{run.manifest.config_hash}`",
        "",
        _spread_section(run, graders),
        _pairs_section(run),
        _mix_section(run, samples),
        _caveats(negatives),
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


def _caveats(negatives: int) -> str:
    lines = ["## 이 숫자를 읽는 법", ""]
    if warning := credibility_warning(negatives):
        lines += [f"⚠️ {warning}", ""]
    lines += [
        "- 지적 단위 CI 는 실제보다 좁다 — decoy 하나가 여러 지적을 내므로 "
        "독립 시행이 아니다. decoy 열(샘플 단위)을 같이 본다.",
        "- 증명된 음성 위에서 `FP/(TP+FP)` 는 정의상 항상 100% 다 "
        "(TP 가 불가능하다). 물림율의 분모는 **나온 지적 전부**다.",
        "- 이 숫자는 **정적분석기**의 것이다. 모델 리뷰어는 자격증명이 있어야 "
        "돌고, 층(`ReviewerKind`)이 다르면 섞어 집계하지 않는다.",
    ]
    return "\n".join(lines)
