"""실험 실행 - 분석기와 모델을 같은 하네스로 돌린다.

정적분석기와 LLM 은 **같은 채점·집계 경로**를 탄다. 그래야
"Ruff 가 이 코퍼스에서 0/10" 과 "Claude 가 이 코퍼스에서 N/10" 이
비교 가능한 숫자가 된다.

다른 점은 앞단뿐이고, 그 차이는 `Reviewer` 구현이 흡수한다:
  분석기 - 결정적. sample_n=1. nonce·effort 무의미.
  모델   - 확률적. sample_n=N. nonce 필수(캐시 무력화), effort 필수.

🔴 **실행 경로는 `run_reviewer` 하나뿐이다.** 전에는 run_analyzer·run_provider·
   run_reviewer 셋이 같은 단계를 각자 구현했고, 짝 채점자용 `bind_run` 훅을
   run_reviewer 에만 걸었다. 나머지 둘은 조용히 빈 짝을 보고 **전부 TP** 로
   채점했다 - 예외도 경고도 없이. 경로를 하나로 줄여 그 실수를 구조적으로 막는다.
"""

from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from codeproof_ai.analysis.registry import symbol_index_for
from codeproof_ai.domain.observation import FingerprintGrouper, group_runs
from codeproof_ai.domain.reviewer import ReviewerKind
from codeproof_ai.domain.run import RunManifest
from codeproof_ai.eval.metrics import GraderResult, summarize
from codeproof_ai.eval.provenance import harness_sha as current_sha

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from codeproof_ai.domain.finding import Finding
    from codeproof_ai.domain.observation import FindingGrouper, ObservationSet, ObservedFinding
    from codeproof_ai.domain.reviewer import Reviewer, ReviewResult, ReviewTelemetry
    from codeproof_ai.domain.run import ToolVersion
    from codeproof_ai.domain.target import ReviewTarget
    from codeproof_ai.eval.grading.base import Grader, Judgment
    from codeproof_ai.eval.sample import LabeledSample


@dataclass(frozen=True, slots=True)
class SampleOutcome:
    """한 샘플에 대한 관측과 채점.

    🔴 판정을 샘플에 붙여서 들고 다닌다. 나중에 순서로 복원하려 들면
       층별 집계가 조용히 어긋난다 (실제로 한 번 그렇게 짰다가 고쳤다).
    """

    sample_id: str
    is_proven_safe: bool
    observations: ObservationSet
    judgments: dict[str, tuple[Judgment, ...]] = field(default_factory=dict)
    raw: tuple[dict[str, object], ...] = field(default_factory=tuple, repr=False)
    """리뷰어가 보존한 원본 페이로드. 🔴 정규화가 틀렸을 때의 유일한 근거다.

    분석기는 보통 비어 있고, 모델은 sample_n 개가 들어온다.
    """


@dataclass(frozen=True, slots=True)
class Telemetry:
    """모델 실행의 비용·지연 집계.

    🔴 단가를 하드코딩하지 않는다. 가격은 바뀌고, 낡은 상수로 계산한 비용은
       틀린 숫자를 권위 있게 보여준다. **토큰만 보고**하고 환산은 읽는 쪽에 맡긴다.
    """

    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: int = 0
    reasoning_tokens: int = 0
    refusals: int = 0
    latencies_ms: tuple[float, ...] = field(default_factory=tuple)

    @property
    def p50_ms(self) -> float | None:
        return self._pct(0.50)

    @property
    def p90_ms(self) -> float | None:
        return self._pct(0.90)

    def _pct(self, q: float) -> float | None:
        if not self.latencies_ms:
            return None
        xs = sorted(self.latencies_ms)
        idx = min(len(xs) - 1, int(q * len(xs)))
        return xs[idx]

    def render(self) -> str:
        parts = [
            f"호출 {self.calls}",
            f"입력 {self.input_tokens:,} (캐시 {self.cache_read:,})",
            f"출력 {self.output_tokens:,}",
        ]
        if self.reasoning_tokens:
            parts.append(f"추론 {self.reasoning_tokens:,}")
        if self.refusals:
            parts.append(f"거부 {self.refusals}")
        if self.p50_ms is not None:
            parts.append(f"지연 p50 {self.p50_ms:.0f}ms / p90 {self.p90_ms:.0f}ms")
        return " · ".join(parts)


@dataclass(frozen=True, slots=True)
class ReviewerRun:
    """한 리뷰어(분석기 또는 모델)의 전체 실행 결과."""

    reviewer: str
    manifest: RunManifest
    outcomes: tuple[SampleOutcome, ...]
    results: tuple[GraderResult, ...]
    telemetry: Telemetry = field(default_factory=Telemetry)

    @property
    def total_findings(self) -> int:
        return sum(len(o.observations.observed) for o in self.outcomes)

    @property
    def negatives(self) -> int:
        return sum(1 for o in self.outcomes if o.is_proven_safe)


def _bind_run_context(
    graders: Sequence[Grader],
    observed: Sequence[tuple[LabeledSample, ObservationSet]],
) -> None:
    """실행 전체의 지적을 채점자에게 넘긴다.

    🔴 필요로 하는 채점자만 `bind_run` 을 구현한다 (선택적 Protocol 메서드).
       짝 기반 정의는 「이 지적이 짝에도 있는가」를 물어야 하는데,
       그건 샘플 하나만 봐서는 답할 수 없다.
    """
    by_sample = {
        s.sample_id: tuple(o.finding for o in obs.observed) for s, obs in observed
    }
    for g in graders:
        bind = getattr(g, "bind_run", None)
        if callable(bind):
            bind(by_sample)


def _with_symbols(
    findings: Sequence[Finding], target: ReviewTarget, reviewer: Reviewer
) -> list[Finding]:
    """둘러싼 심볼이 없는 지적에 붙인다 - **모든 리뷰어가 같은 경로로.**

    🔴 [실측] 모델·에이전트 지적은 심볼 없이 들어왔다. 그러면 짝 채점의
       「짝에도 같은 지적인가」가 `(category, None)` 이 되어 **파일 안 같은
       category 면 전부 같은 지적**이 됐다 - claude D005 는 다른 함수·다른
       인용인데 탐지가 지워졌다. 지문(B2)도 설계와 달리 심볼 없이 계산됐다.

    여기서 붙이는 이유는 E00 과 같다. 리뷰어마다 붙이면 경로가 갈리고,
    새 리뷰어가 생길 때 반드시 한쪽이 빠진다.
    정적분석기 어댑터는 스스로 붙이므로(ruff · mypy) 다시 계산하지 않는다.
    """
    if reviewer.kind is ReviewerKind.STATIC:
        return list(findings)
    out: list[Finding] = []
    for f in findings:
        index = symbol_index_for(f.location.path)
        src = target.file(f.location.path)
        if f.location.symbol is not None or index is None or src is None:
            out.append(f)
            continue
        symbol, kind = index.enclosing_symbol(src.content, f.location.line)
        out.append(f.with_symbol(symbol, kind) if symbol else f)
    return out


def _declared_fields(reviewer: Reviewer) -> Mapping[str, str]:
    """리뷰어가 신고한 매니페스트 항목.

    선택적 Protocol 메서드다 - 정적분석기는 신고할 것이 없고, 모델 리뷰어는
    effort·cache_policy 를 신고한다. 🔴 러너가 짐작하지 않는다.
    """
    declare = getattr(reviewer, "manifest_fields", None)
    return declare() if callable(declare) else {}


def _tool_versions(reviewer: Reviewer) -> tuple[ToolVersion, ...]:
    """리뷰어가 의존하는 외부 도구의 정확한 버전.

    🔴 ruff 는 pre-1.0 이라 JSON 스키마가 바뀐다 - 버전을 안 남기면
       6개월 뒤 같은 코퍼스에서 다른 숫자가 나와도 원인을 못 찾는다.
    """
    declare = getattr(reviewer, "tool_versions", None)
    return tuple(declare()) if callable(declare) else ()


def _omitted_for(reviewer: Reviewer) -> tuple[str, ...]:
    """🔴 **의도적으로 안 보낸 것**을 적는다 - 보낸 것만큼 중요하다.

    확률적 리뷰어에만 의미가 있다. 정적분석기에 temperature 를 "생략했다"고
    적으면 그건 정보가 아니라 잡음이다.
    """
    if reviewer.kind.is_deterministic:
        return ("temperature", "seed", "effort")
    return ("temperature", "top_p", "seed", "fallbacks", "tool_choice")


def _grade(
    sample: LabeledSample,
    obs: ObservationSet,
    graders: Sequence[Grader],
) -> dict[str, tuple[Judgment, ...]]:
    return {g.name: tuple(g.judge(sample, obs.observed)) for g in graders}


def _pick(
    run: int | None, at_least: int | None
) -> Callable[[ObservationSet], tuple[ObservedFinding, ...]]:
    if run is not None and at_least is None:
        r = run
        return lambda obs: obs.in_run(r)
    if at_least is not None and run is None:
        k = at_least
        return lambda obs: obs.at_least(k)
    msg = "관점은 run 과 at_least 중 하나만 고른다"
    raise ValueError(msg)


def regrade_view(
    outcomes: Sequence[SampleOutcome],
    samples: Sequence[LabeledSample],
    graders: Sequence[Grader],
    *,
    run: int | None = None,
    at_least: int | None = None,
) -> list[SampleOutcome]:
    """한 관점에 든 지적만 남기고 **다시 묶어 다시 채점한다** - 다회 실행의 관점별 숫자.

    run=r        r 번째 실행에서 실제로 나온 지적 - 개발자가 한 번 돌렸을 때
    at_least=k   k회 이상 나온 지적 - k-임계 (기법이지 기준선이 아니다)

    🔴 판정을 관점으로 **걸러내기만** 하면 틀린다. `bind_run` 으로 짝의 지적을 받는
       채점자(paired_fix)는 합집합 짝으로 이미 판정했으므로 걸러도 그 판정이 남는다.
       [실측 · claude n=8 · 60쌍] 그렇게 낸 단일 실행 기대값이 60.4% 로 발표됐다 -
       회차별 단독 채점의 평균은 62.7% 였고, 다른 채점자 셋은 일치했다.
    🔴 채점자를 **복사해서** 묶는다. 넘겨받은 채점자를 다시 묶으면 그 뒤의 채점이
       마지막 관점의 짝을 본다.
    """
    pick = _pick(run, at_least)
    by_id = {s.sample_id: s for s in samples}
    viewed = [
        (o, replace(o.observations, observed=pick(o.observations)))
        for o in outcomes
        if o.sample_id in by_id
    ]
    bound = [copy.copy(g) for g in graders]
    _bind_run_context(bound, [(by_id[o.sample_id], obs) for o, obs in viewed])
    return [
        SampleOutcome(
            sample_id=o.sample_id,
            is_proven_safe=o.is_proven_safe,
            observations=obs,
            judgments=_grade(by_id[o.sample_id], obs, bound),
        )
        for o, obs in viewed
    ]


def _summarize_strata(
    outcomes: Sequence[SampleOutcome], graders: Sequence[Grader]
) -> tuple[GraderResult, ...]:
    """🔴 층별로 나눠서 집계한다. 풀링 금지 (F3)."""
    results: list[GraderResult] = []
    for g in graders:
        for is_safe, label in ((True, "증명된 음성"), (False, "양성(twin)")):
            subset = [
                j
                for o in outcomes
                if o.is_proven_safe is is_safe
                for j in o.judgments.get(g.name, ())
            ]
            results.append(summarize(g.name, g.definition, label, subset))
    return tuple(results)


def run_reviewer(
    reviewer: Reviewer,
    samples: Sequence[LabeledSample],
    graders: Sequence[Grader],
    *,
    sample_n: int = 1,
    grouper: FindingGrouper | None = None,
    harness_sha: str | None = None,
    prompt_hash: str = "n/a",
) -> ReviewerRun:
    """🔴 통합 경로 - Reviewer 면 무엇이든 같은 하네스로 돈다.

    정적분석기 · 모델 API · 에이전트 · 가져온 지적 · 사람 리뷰가 전부 여기로 들어온다.
    그래야 "Ruff 0/10" 과 "Claude N/10" 이 비교 가능한 숫자가 된다.

    결정적 리뷰어에 sample_n>1 을 주면 **거부한다** - 같은 결과를 N번 세는 것은
    측정이 아니라 부풀리기다.
    """
    if sample_n < 1:
        msg = f"sample_n 은 1 이상이다: {sample_n}"
        raise ValueError(msg)
    if reviewer.kind.is_deterministic and sample_n > 1:
        msg = (
            f"{reviewer.name} 은 결정적({reviewer.kind.value})인데 sample_n={sample_n} 이다. "
            "같은 결과를 N번 세면 출현 빈도가 의미를 잃는다."
        )
        raise ValueError(msg)

    policy = grouper or FingerprintGrouper()
    tele = _Accumulator()

    # 🔴 일괄 경로가 있으면 쓴다 - 대상마다 subprocess 를 띄우면
    #    300 샘플에서 mypy 만 37초다 ([실측] 일괄은 0.16초).
    batched = _batch_reviews(reviewer, samples, sample_n)

    # ── 1단계: 전부 리뷰한다 ─────────────────────────────────
    # 🔴 채점과 분리한 이유: 짝 기반 채점자(PairedFixGrader)는 **다른 샘플의
    #    지적**을 알아야 한다. 한 루프에서 리뷰와 채점을 같이 하면 그 정보가
    #    아직 없다.
    observed: list[tuple[LabeledSample, ObservationSet, tuple[dict[str, object], ...]]] = []
    for s in samples:
        runs: list[list[Finding]] = []
        raws: list[dict[str, object]] = []
        for i in range(sample_n):
            result = (
                batched[s.sample_id][i]
                if batched is not None
                else reviewer.review(s.target)
            )
            runs.append(_with_symbols(result.findings, s.target, reviewer))
            tele.add(result.telemetry)
            if result.raw:
                raws.append(result.raw)
        observed.append(
            (
                s,
                group_runs(s.sample_id, runs, policy, reviewer=reviewer.name),
                tuple(raws),
            )
        )

    # ── 2단계: 채점한다 ─────────────────────────────────────
    _bind_run_context(graders, [(s, obs) for s, obs, _ in observed])
    outcomes = [
        SampleOutcome(
            sample_id=s.sample_id,
            is_proven_safe=s.is_proven_safe,
            observations=obs,
            judgments=_grade(s, obs, graders),
            raw=raws,
        )
        for s, obs, raws in observed
    ]

    # 🔴 매니페스트는 리뷰어가 스스로 신고한다.
    #    전에는 여기서 effort="n/a" · cache_policy="cold_only" 를 박아 넣었다.
    #    모델 리뷰어에게 그건 **거짓말**이다 - mypy 가 host 설정을 물려받는데
    #    매니페스트는 strict=False 라고 적던 것과 같은 종류의 버그다.
    declared = _declared_fields(reviewer)
    manifest = RunManifest(
        model_id=reviewer.identity,
        prompt_hash=prompt_hash,
        corpus_hash=_corpus_hash(samples),
        effort=declared.get("effort", "n/a(static)"),
        sample_n=sample_n,
        cache_policy=declared.get("cache_policy", "cold_only"),
        grouper=policy.name,
        # 🔴 짐작하지 않는다 - 알 수 있으면 알아낸다 (E01 과 같은 원칙).
        harness_sha=harness_sha if harness_sha is not None else current_sha(),
        created_at=datetime.now(UTC),
        params_sent={
            "reviewer_config": reviewer.config_signature(),
            "reviewer_kind": reviewer.kind.value,
        },
        params_omitted=_omitted_for(reviewer),
        tool_versions=_tool_versions(reviewer),
    )
    return ReviewerRun(
        reviewer=reviewer.name,
        manifest=manifest,
        outcomes=tuple(outcomes),
        results=_summarize_strata(outcomes, graders),
        telemetry=tele.build(),
    )


def _batch_reviews(
    reviewer: Reviewer,
    samples: Sequence[LabeledSample],
    sample_n: int,
) -> dict[str, list[ReviewResult]] | None:
    """리뷰어가 일괄을 지원하면 미리 전부 돌린다.

    확률적 리뷰어(sample_n>1)에는 쓰지 않는다 - 일괄은 결정적 도구를 위한 것이고,
    모델은 호출마다 다른 답을 내야 하므로 미리 모아 돌릴 수 없다.
    """
    review_many = getattr(reviewer, "review_many", None)
    if review_many is None or sample_n != 1:
        return None
    results = review_many([s.target for s in samples])
    return {tid: [res] for tid, res in results.items()}


class _Accumulator:
    """호출별 텔레메트리를 모은다."""

    def __init__(self) -> None:
        self.calls = 0
        self.tok_in = 0
        self.tok_out = 0
        self.cache = 0
        self.reasoning = 0
        self.refusals = 0
        self.latencies: list[float] = []

    def add(self, t: ReviewTelemetry) -> None:
        self.calls += 1
        self.tok_in += t.input_tokens or 0
        self.tok_out += t.output_tokens or 0
        self.cache += t.cache_read or 0
        self.reasoning += t.reasoning_tokens or 0
        self.refusals += int(t.refused)
        if t.total_ms is not None:
            self.latencies.append(t.total_ms)

    def build(self) -> Telemetry:
        return Telemetry(
            calls=self.calls,
            input_tokens=self.tok_in,
            output_tokens=self.tok_out,
            cache_read=self.cache,
            reasoning_tokens=self.reasoning,
            refusals=self.refusals,
            latencies_ms=tuple(self.latencies),
        )


def _corpus_hash(samples: Sequence[LabeledSample]) -> str:
    h = hashlib.blake2b(digest_size=12)
    for s in sorted(samples, key=lambda x: x.sample_id):
        h.update(s.sample_id.encode("utf-8"))
        for f in s.target.files:
            h.update(f.content.encode("utf-8"))
    return h.hexdigest()
