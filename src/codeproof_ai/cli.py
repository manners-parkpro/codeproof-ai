"""CLI — 이 플랫폼의 주 진입점.

🔴 engine 은 HTTP 를 모른다 (DESIGN §6.4). FastAPI 는 v2 의 얇은 어댑터고,
   실험은 전부 여기서 배치로 돈다.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from codeproof_ai.analysis.registry import (
    UnknownAnalyzerError,
    create_analyzer,
)
from codeproof_ai.analysis.registry import available as analyzer_available
from codeproof_ai.corpus.decoy import validate_corpus
from codeproof_ai.domain.reviewer import ReviewerKind
from codeproof_ai.eval.bait import BaitStatus, measure
from codeproof_ai.eval.export import export_for_agent
from codeproof_ai.eval.grading.base import Outcome
from codeproof_ai.eval.grading.corroboration import StaticCorroborationGrader
from codeproof_ai.eval.grading.injected import InjectedDefectGrader
from codeproof_ai.eval.grading.paired import PairedFixGrader
from codeproof_ai.eval.grading.safety import ProvableSafetyGrader
from codeproof_ai.eval.loader import load_decoy_samples
from codeproof_ai.eval.metrics import credibility_warning
from codeproof_ai.eval.mix import Axis, mix_sensitivity
from codeproof_ai.eval.pairing import (
    PairVerdict,
    discrimination_rate,
    pair_summary,
    score_pairs,
)
from codeproof_ai.eval.report import render_measurements
from codeproof_ai.eval.runner import (
    ReviewerRun,
    SampleOutcome,
    run_reviewer,
)
from codeproof_ai.eval.sensitivity import sweep
from codeproof_ai.eval.spread import compute_spread
from codeproof_ai.llm.credentials import all_statuses
from codeproof_ai.llm.registry import (
    CREDENTIAL_OF,
    UnknownProviderError,
    create_provider,
)
from codeproof_ai.llm.registry import available as provider_available
from codeproof_ai.llm.render import load_prompt
from codeproof_ai.llm.render import prompt_hash as prompt_hash_of
from codeproof_ai.reviewers.imported import ImportedReviewer, read_run_record
from codeproof_ai.reviewers.wrap import AnalyzerReviewer, ProviderReviewer
from codeproof_ai.store.sqlite import ReproCheck, Store

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from codeproof_ai.analysis.base import Analyzer
    from codeproof_ai.domain.reviewer import Reviewer
    from codeproof_ai.eval.grading.base import Grader
    from codeproof_ai.eval.sample import LabeledSample

# 음성 100건 미만이면 FPR 의 Wilson 95% CI 반폭이 ±6pp 를 넘는다.
# 그 아래로는 숫자가 아니라 느낌이다 (DESIGN §3.5).
MIN_CREDIBLE_NEGATIVES = 100
TARGET_NEGATIVES = 150


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codeproof",
        description="AI 코드리뷰 품질 측정 실험 플랫폼",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # 🔴 `review`(단일 PR 런타임 경로)는 **일부러 없다.**
    #    안 되는 것을 --help 에 올려 두면 쓰는 사람이 속는다. 이 저장소의
    #    논지는 오프라인 측정 경로(measure·eval·report)이고, 런타임 리뷰는
    #    그 논지를 보이는 데 필요하지 않다. docs/DESIGN.md 의 범위 표를 본다.

    ev = sub.add_parser("eval", help="모델을 리뷰어로 돌린다 (자격증명 필요)")
    ev.add_argument("--corpus", default="corpus/decoys")
    ev.add_argument(
        "--providers",
        required=True,
        help=f"쉼표 구분: {' | '.join(provider_available())} (replay 는 배관 검증용)",
    )
    ev.add_argument("--effort", required=True, help="필수 - 기본값이 모델마다 다르다")
    ev.add_argument(
        "--samples",
        type=int,
        default=8,
        help="반복 횟수. seed 도 temperature 도 없으므로 재현성은 이걸로만 확보된다",
    )
    ev.add_argument(
        "--cache-policy",
        choices=("nonce", "cold_only"),
        default="nonce",
        help="캐싱 비대칭 대응. Anthropic 은 옵트인, OpenAI 는 기본 활성화",
    )
    ev.add_argument("--slack", type=int, default=0)
    ev.add_argument("--store", default="runs.db")

    im = sub.add_parser(
        "import",
        help="외부 지적을 리뷰어로 가져온다 (SARIF 등) - 자격증명 불필요",
    )
    im.add_argument("--corpus", default="corpus/decoys")
    im.add_argument("--from", dest="src", required=True, help="<sample_id>.json 이 있는 디렉터리")
    im.add_argument("--name", required=True, help="리뷰어 이름")
    im.add_argument(
        "--identity",
        help="재현용 식별자 (도구 버전 · 모델 ID). --from 에 RUN.json 이 있으면 거기서 읽는다",
    )
    im.add_argument(
        "--kind",
        choices=("imported", "agent", "human"),
        default="imported",
        help="🔴 층. 에이전트 출력이면 agent - model_api 와 섞어 집계하면 안 된다",
    )
    im.add_argument(
        "--format",
        dest="fmt",
        choices=("sarif", "bandit", "native"),
        default=None,
        help="생략하면 RUN.json 이 있을 때 native(에이전트 실행기), 없으면 sarif",
    )
    im.add_argument(
        "--allow-partial",
        action="store_true",
        help="🔴 결과가 없는 샘플이 있어도 집계한다 - 미측정이 미탐지로 둔갑함을 알고 쓴다",
    )
    im.add_argument("--slack", type=int, default=0)
    im.add_argument("--store", default="runs.db")

    decoy = sub.add_parser("decoy", help="D층 decoy 코퍼스 관리")
    decoy_sub = decoy.add_subparsers(dest="decoy_command", required=True)

    dv = decoy_sub.add_parser("validate", help="decoy 코퍼스 검증")
    dv.add_argument("--corpus", default="corpus/decoys", help="decoy 디렉터리")
    dv.add_argument(
        "--strict",
        action="store_true",
        help="경고도 실패로 취급한다 (CI 용)",
    )

    ds = decoy_sub.add_parser(
        "stats", help="미끼가 실제로 물리는지 - 사용 가능한 리뷰어로 측정"
    )
    ds.add_argument("--corpus", default="corpus/decoys")
    ds.add_argument(
        "--ruff-select", default="ALL", help="좁히면 물리는 비율이 떨어진다"
    )

    dn = decoy_sub.add_parser("new", help="템플릿에서 새 decoy 를 만든다")
    dn.add_argument("decoy_id", help="예: D003-caller-held-lock")
    dn.add_argument("--corpus", default="corpus/decoys")

    m = sub.add_parser(
        "measure",
        help="정적분석기를 리뷰어로 돌려 채점 기준 편차를 잰다 (API 불필요)",
    )
    m.add_argument("--corpus", default="corpus/decoys")
    m.add_argument(
        "--analyzers", default="ruff,mypy", help="쉼표 구분: ruff | mypy"
    )
    m.add_argument(
        "--ruff-select",
        default=None,
        help="Ruff 룰 선택. 🔴 측정 손잡이다 - ALL 과 E,F 는 FP 수가 완전히 다르다",
    )
    m.add_argument("--slack", type=int, default=0, help="안전 근거 범위 여유 줄 수")
    m.add_argument(
        "--store",
        default="runs.db",
        help="결과 저장 경로. 'none' 이면 저장하지 않는다 (재현 불가)",
    )

    sub.add_parser("doctor", help="자격증명 · 도구 준비 상태 확인")

    h = sub.add_parser("history", help="저장된 실행 조회 · 재현성 확인")
    h.add_argument("--store", default="runs.db")
    h.add_argument("--limit", type=int, default=20)
    h.add_argument(
        "--repro",
        metavar="CONFIG_HASH",
        help="같은 설정으로 돌린 실행들을 비교한다",
    )

    _add_report_parser(sub)
    _add_export_parser(sub)

    return parser


def _add_report_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """측정값 생성 - 문서가 숫자를 베끼면 반드시 낡는다."""
    rep = sub.add_parser(
        "report",
        help="측정값 문서를 생성한다 (산문에 숫자를 베끼지 않기 위해)",
    )
    rep.add_argument("--corpus", default="corpus/decoys")
    rep.add_argument("--analyzer", default="ruff")
    rep.add_argument("--ruff-select", default="ALL")
    rep.add_argument(
        "--out",
        default="docs/MEASUREMENTS.md",
        help="생성 경로. '-' 면 표준출력",
    )
    rep.add_argument(
        "--check",
        action="store_true",
        help="쓰지 않고 최신인지만 확인한다 (다르면 exit 1)",
    )


def _add_export_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """🔴 에이전트 층을 여는 자리 - 자격증명 없이 모델 숫자를 낼 수 있는 유일한 경로."""
    ex = sub.add_parser(
        "export",
        help="코퍼스를 에이전트가 리뷰할 형태로 내보낸다 (자격증명 불필요)",
    )
    ex.add_argument("--corpus", default="corpus/decoys")
    ex.add_argument("--out", required=True, help="내보낼 디렉터리")
    ex.add_argument(
        "--prompt",
        default="review_v1",
        help="리뷰 지시. 🔴 model_api 와 같은 것을 써야 같은 과제다",
    )


def _cmd_export(corpus: Path, out: Path, prompt_name: str) -> int:
    samples = load_decoy_samples(corpus)
    if not samples:
        print(f"샘플이 없다: {corpus}", file=sys.stderr)
        return 2
    manifest = export_for_agent(samples, out, prompt_name=prompt_name)
    n = len(manifest["samples"])  # type: ignore[arg-type]
    print(f"{out} 에 샘플 {n}개를 썼다 (prompt_hash={manifest['prompt_hash']})")
    print("  다음: ./scripts/review-with-agent.sh <claude|codex> "
          f"{out} <출력디렉터리>")
    print("  그다음: codeproof import --from <출력디렉터리> --kind agent "
          "--name <이름> --identity <버전>")
    return 0


def _cmd_decoy_validate(corpus: Path, *, strict: bool) -> int:
    if not corpus.is_dir():
        print(f"decoy 디렉터리가 없다: {corpus}", file=sys.stderr)
        return 2

    report = validate_corpus(corpus)

    for name, err in report.load_errors:
        print(f"{name}\n  ✗ [load] {err}")
    by_decoy: dict[str, list[str]] = {}
    for name, v in report.violations:
        by_decoy.setdefault(name, []).append(str(v))
    for name, lines in by_decoy.items():
        print(name)
        for line in lines:
            print(line)

    print(
        f"\n검사 {report.checked}건 · 유효 {report.valid_count} · "
        f"오류 {report.error_count} · 경고 {report.warn_count}"
    )


    # 규모 경고 - 음성 100건 미만이면 FPR 은 숫자가 아니라 느낌이다.
    if report.valid_count < MIN_CREDIBLE_NEGATIVES:
        sys.stdout.flush()
        print(
            f"\n! 유효 decoy 가 {report.valid_count}건이다. "
            f"음성 {MIN_CREDIBLE_NEGATIVES}건 미만이면 FPR 신뢰구간이 ±6pp 를 넘는다 "
            f"(목표 {TARGET_NEGATIVES}건).",
            file=sys.stderr,
        )

    if report.error_count:
        return 1
    if strict and report.warn_count:
        return 1
    return 0


def _cmd_decoy_new(corpus: Path, decoy_id: str) -> int:
    template = corpus / "_TEMPLATE"
    target = corpus / decoy_id

    if not template.is_dir():
        # 🔴 새 코퍼스를 만들 때 반드시 막히는 자리다 - 무엇을 하라는지 말한다.
        print(f"템플릿이 없다: {template}", file=sys.stderr)
        print(
            "  내려받은 코퍼스에서 복사한다: "
            f"cp -R corpus/decoys/_TEMPLATE {template}",
            file=sys.stderr,
        )
        return 2
    if target.exists():
        print(f"이미 있다: {target}", file=sys.stderr)
        return 2

    shutil.copytree(template, target)
    meta = target / "meta.toml"
    meta.write_text(
        meta.read_text(encoding="utf-8").replace('"D00X-짧은-설명"', f'"{decoy_id}"'),
        encoding="utf-8",
    )
    print(f"만들었다: {target}")
    print("  1. decoy.py  - 안전한 버전 (가드가 이 파일 안에서 보여야 한다)")
    print("  2. twin.py   - 가드만 제거한 버전")
    print("  3. meta.toml - 안전 근거를 기전으로 쓴다")
    print(f"\n검증: uv run codeproof decoy validate --corpus {corpus}")
    return 0


def _print_spread(run: ReviewerRun, graders: Sequence[Grader]) -> None:
    """🔴 채점 기준 편차 - 이 프로젝트의 헤드라인."""
    defs = {g.name: g.definition for g in graders}
    fp_capable = {g.name for g in graders if Outcome.FALSE_POSITIVE in g.emits}
    sp = compute_spread(run.outcomes, defs, fp_capable, negatives_only=True)
    if sp.findings == 0:
        print("\n  [채점 기준 편차] 증명된 음성 위에 지적이 없어 편차를 낼 수 없다")
        return

    print(f"\n  [채점 기준 편차] 증명된 음성 위의 **같은 지적 {sp.findings}건**을")
    print("                    서로 다른 정답 정의로 채점한 결과")
    print(f"    {'채점자':<22}{'TP':>4}{'FP':>5}{'판정불가':>9}  FP가능")
    for c in sp.columns:
        mark = "  o" if c.can_emit_fp else "  x"
        print(
            f"    {c.grader:<22}{c.true_positive:>4}{c.false_positive:>5}"
            f"{c.undecidable:>9}{mark}"
        )
    for c in sp.columns:
        print(f"      · {c.grader}: {c.definition}")

    excluded = [c.grader for c in sp.columns if not c.can_emit_fp]
    if excluded:
        print(
            f"\n    ⚠ {', '.join(excluded)} 는 구조적으로 FP 를 낼 수 없다 "
            "(동의 부재 != 반증).\n"
            "      그 0 을 편차에 넣으면 범주 차이를 편차로 오해하므로 제외한다."
        )

    lo, hi = sp.fp_range
    ratio = sp.fp_ratio
    tail = f" — {ratio:.1f}배" if ratio is not None else ""
    print(
        f"\n    🔴 FP 를 낼 수 있는 채점자끼리: {lo} ~ {hi}{tail}. "
        "지적은 하나도 바뀌지 않았다."
    )
    print(f"       정의 선택만으로 생긴 FP: {sp.disagreement}건")


def _print_sensitivity(
    run: ReviewerRun, samples: Sequence[LabeledSample], grader_name: str
) -> None:
    """🔴 판정이 매칭 손잡이에 흔들리는지.

    [실측] 같은 결함을 Ruff 는 호출 시작 줄로, bandit 은 인자 줄로 보고한다.
    단일 slack 값으로 낸 숫자는 리뷰어의 성질이 아니라 매칭 정책의 산물일 수 있다.
    """
    by_id = {s.sample_id: s for s in samples}

    def regrade(slack: int) -> list[SampleOutcome]:
        g = ProvableSafetyGrader(overlap_slack=slack)
        return [
            SampleOutcome(
                sample_id=o.sample_id,
                is_proven_safe=o.is_proven_safe,
                observations=o.observations,
                judgments={g.name: tuple(g.judge(by_id[o.sample_id], o.observations.observed))},
            )
            for o in run.outcomes
            if o.sample_id in by_id
        ]

    sens = sweep(regrade, grader_name)
    if not sens.points:
        return

    print("\n  [매칭 민감도] slack 을 바꾸면 판정이 흔들리는가")
    print(f"    {'slack':>6}{'P-C':>5}{'P-V':>5}{'P-B':>5}{'P-R':>5}")
    for pt in sens.points:
        print(
            f"    {pt.slack:>6}{pt.correct:>5}{pt.over_flag:>5}"
            f"{pt.under_flag:>5}{pt.reversed_:>5}"
        )
    if sens.stable:
        print("    o 안정 - 이 결론은 매칭 정책의 산물이 아니다")
    else:
        spans = ", ".join(f"{a}→{b}" for a, b in sens.flips)
        print(
            f"    🔴 불안정 ({spans} 에서 판정이 바뀐다) - "
            "단일 slack 값으로 낸 숫자를 결론으로 쓰지 않는다"
        )


def _print_pairs(run: ReviewerRun, graders: Sequence[Grader]) -> None:
    """🔴 짝 채점 - 과잉지적은 짝을 지어야만 보인다."""
    for g in graders:
        pairs = score_pairs(run.outcomes, g.name)
        if not pairs:
            continue
        hit, total_pairs = discrimination_rate(pairs)
        counts = pair_summary(pairs)
        print(f"\n  [짝 채점 · PrimeVul] 채점자={g.name}")
        print(f"    구별 성공   : {hit}/{total_pairs}  <- 유일하게 옳은 결과")
        print(f"    P-C 구별    : {counts[PairVerdict.CORRECT]}")
        print(f"    P-V 과잉지적: {counts[PairVerdict.OVER_FLAG]}  (둘 다 지적)")
        print(f"    P-B 미탐지  : {counts[PairVerdict.UNDER_FLAG]}  (둘 다 미지적)")
        print(f"    P-R 역전    : {counts[PairVerdict.REVERSED]}  (음성만 지적)")
        for pr in pairs:
            if pr.verdict is not PairVerdict.UNDER_FLAG:
                print(f"      {pr.verdict.value}  {pr.pair_id}  - {pr.detail}")


def _print_mix(
    run: ReviewerRun, samples: Sequence[LabeledSample], grader: str
) -> None:
    """🔴 코퍼스 구성비도 측정 손잡이다 - 그걸 선언한 벤치마크를 보지 못했다."""
    # 🔴 두 축을 **둘 다** 낸다. 한 축만 고르게 채워도 다른 축이 쏠릴 수 있다.
    for axis in Axis:
        ms = mix_sensitivity(run.outcomes, samples, grader, axis)
        if not ms.kinds:
            continue
        print()
        print(ms.render())


def _print_strata(run: ReviewerRun) -> None:
    """🔴 층별로 나눠서 본다. 풀링 금지 (E2)."""
    print()
    for r in run.results:
        if sum(r.counts.values()) == 0:
            continue
        print(f"  [{r.stratum}] 채점자={r.grader}")
        print(f"    정의        : {r.definition}")
        print(f"    Precision   : {r.precision.render()}")
        print(f"    판정불가율  : {r.undecidable_rate.render()}")
    print()


def _print_repro(check: ReproCheck, reviewer: str) -> None:
    """🔴 같은 설정의 결과가 같은가. 해석은 리뷰어 종류에 달려 있다."""
    n = len(check.runs)
    if check.identical:
        print(f"  재현성: 같은 설정 {n}회 실행, 지적 집합 **동일**")
        return

    volatile = len(check.volatile_keys)
    stable = len(check.stable_keys)
    print(f"  재현성: 같은 설정 {n}회 실행, 지적 집합 **불일치**")
    print(f"          공통 {stable}건 · 변동 {volatile}건")
    print(
        "          ⚠ 정적분석기는 결정적이어야 한다 - 도구 버전이나 환경이 "
        "바뀌었는지 확인한다."
        if reviewer in {"ruff", "mypy"}
        else "          모델은 비결정적이다 - 이 변동 폭 자체가 측정 대상이다."
    )


def _graders_for(
    reviewer: str, slack: int, samples: Sequence[LabeledSample]
) -> list[Grader]:
    """채점자 3종.

    🔴 확인자는 평가 대상과 달라야 한다 - 같으면 자기 채점이다.
    🔴 확인자 지적을 **일괄로 미리 계산해** 넘긴다. 채점자가 분석기를 들고
       샘플마다 돌리면 [실측] 30 샘플에 15초다 (일괄 0.5초).
    """
    ref_analyzer = create_analyzer("mypy" if reviewer == "ruff" else "ruff")
    reference = ref_analyzer.analyze_many([s.target for s in samples])
    return [
        ProvableSafetyGrader(overlap_slack=slack),
        InjectedDefectGrader(),
        PairedFixGrader(line_slack=slack),
        StaticCorroborationGrader(
            reference=reference, reference_name=ref_analyzer.name
        ),
    ]


def _persist(run: ReviewerRun, store_path: str) -> None:
    """결과를 보관한다. 🔴 매니페스트 없이는 외래키가 거부한다 (E1)."""
    if store_path == "none":
        print("  ⚠ --store none - 이 결과는 재현할 수 없다")
        return
    with Store(store_path) as store:
        run_id = store.save(run)
        check = store.repro_check(run.manifest.config_hash)
    print(f"  저장: {store_path}  run_id={run_id}")
    if len(check.runs) > 1:
        _print_repro(check, run.reviewer)





def _cmd_eval(
    corpus: Path,
    provider_names: list[str],
    *,
    effort: str,
    samples: int,
    cache_policy: str,
    slack: int,
    store_path: str,
) -> int:
    labeled = load_decoy_samples(corpus)
    if not labeled:
        print(f"평가 샘플이 없다: {corpus}", file=sys.stderr)
        return 2

    prompt_hash = prompt_hash_of(load_prompt())

    for name in provider_names:
        try:
            provider = create_provider(name)
        except UnknownProviderError as exc:
            print(exc, file=sys.stderr)
            return 2

        if name == "replay":
            print("⚠ replay provider - 배관 검증용이다. 이 숫자를 결과로 보고하지 않는다.\n")
        elif not _credentials_ready(name):
            return 2

        graders = _graders_for(name, slack, labeled)
        run = run_reviewer(
            ProviderReviewer(
                provider, effort=effort, cache_policy=cache_policy
            ),
            labeled,
            graders,
            sample_n=samples,
            prompt_hash=prompt_hash,
        )

        print("=" * 74)
        print(f"리뷰어: {run.reviewer}  ({run.manifest.model_id})")
        print("-" * 74)
        print(run.manifest.disclosure_block())
        print("-" * 74)
        print(f"  텔레메트리: {run.telemetry.render()}")
        _print_observations(run)
        _print_spread(run, graders)
        _print_pairs(run, graders)
        _print_sensitivity(run, labeled, "provable_safety")
        _print_mix(run, labeled, "provable_safety")
        _print_strata(run)
        _persist(run, store_path)

    return 0


def _import_source(
    src: Path, identity: str | None, fmt: str | None
) -> tuple[str, str] | None:
    """가져올 디렉터리를 확인하고 (identity, 포맷) 을 정한다. 안 되면 이유를 말하고 None.

    🔴 실행기가 남긴 기록(RUN.json)이 있으면 그것이 정본이다.
       - identity: 손으로 친 값이 다르면 매니페스트가 거짓이 된다 (E01).
         [실측] 커밋 메시지의 예시 `--identity 2.1.250` 은 다음 날 실제 CLI
         (2.1.284)와 이미 달랐다.
       - 포맷: 실행기는 native 를 쓴다. 기본값(sarif)으로 읽으면 전 샘플이
         「지적 0건」이 된다 - 안내된 명령에 `--format native` 가 빠져 있었다.
    """
    if not src.is_dir():
        print(f"가져올 디렉터리가 없다: {src}", file=sys.stderr)
        return None
    run = read_run_record(src)
    recorded = str(run["identity"]) if run and run.get("identity") else None
    fmt = fmt or ("native" if run is not None else "sarif")
    if identity is None:
        if recorded is None:
            print("--identity 가 필요하다 - RUN.json 이 없어 알 수 없다", file=sys.stderr)
            return None
        return recorded, fmt
    if recorded is not None and identity != recorded:
        print(
            f"🔴 --identity 가 실행 기록과 다르다: 준 값={identity!r} · RUN.json={recorded!r}\n"
            "   이대로 저장하면 매니페스트가 거짓이 된다 (E01). 생략하면 기록을 쓴다.",
            file=sys.stderr,
        )
        return None
    return identity, fmt


def _measured_pairs(
    labeled: list[LabeledSample], reviewer: ImportedReviewer, *, allow_partial: bool
) -> list[LabeledSample] | None:
    """결과가 있는 샘플만 남긴다. 못 하면 이유를 말하고 None.

    🔴 결과 파일이 없는 샘플은 「지적 0건」으로 들어온다 (ImportedReviewer.review).
       SARIF 도구라면 그게 맞다 - 돌았는데 아무것도 못 찾은 것이다. 그러나
       에이전트 실행이 중간에 끊긴 경우엔 **미측정이 미탐지로 둔갑**한다.
       그러면 P-B(둘 다 미지적)가 부풀어 리뷰어가 실제보다 나쁘게 나온다 -
       증거의 부재를 오답으로 세는 F4 와 같은 종류의 오류다.
    """
    missing = [s.sample_id for s in labeled if reviewer.available_runs(s.sample_id) == 0]
    if not missing:
        return labeled
    covered = len(labeled) - len(missing)
    print(
        f"결과가 없는 샘플이 {len(missing)}개다 "
        f"(적용 범위 {covered}/{len(labeled)}). 예: {missing[:3]}",
        file=sys.stderr,
    )
    if not allow_partial:
        print(
            "  🔴 이대로 집계하면 **미측정이 미탐지로 둔갑**한다.\n"
            "     전부 채우거나, 그 사실을 알고 있다면 --allow-partial 을 준다.",
            file=sys.stderr,
        )
        return None
    # 🔴 경고만으로는 부족하다. 숫자 자체가 거짓이 된다.
    #    [실측] 120개 중 2개만 채우고 집계했더니 `P-B 미탐지 60` 이 나왔다 -
    #    한 쌍만 측정했는데 60쌍을 놓친 것처럼 보인다.
    #    → 측정된 **완전한 짝**만 남긴다. 반쪽짜리 짝도 버린다 -
    #      한쪽 지적만으로는 P-C/P-V/P-B/P-R 을 가를 수 없다 (F5).
    have = {s.sample_id for s in labeled if reviewer.available_runs(s.sample_id) > 0}
    kept = [s for s in labeled if s.sample_id in have and s.paired_with in have]
    if not kept:
        print("  완전한 짝이 하나도 없다 - 짝의 양쪽이 모두 있어야 채점된다.", file=sys.stderr)
        return None
    print(
        f"  ⚠ --allow-partial - 완전한 짝 {len(kept) // 2}쌍만 집계한다 "
        f"(결과가 있던 샘플 {covered}개 중).",
        file=sys.stderr,
    )
    return kept


def _cmd_import(
    corpus: Path,
    src: Path,
    *,
    name: str,
    identity: str | None,
    kind: ReviewerKind,
    fmt: str | None,
    slack: int,
    store_path: str,
    allow_partial: bool = False,
) -> int:
    """외부 지적을 리뷰어로 가져온다.

    SARIF 를 내는 모든 도구(semgrep · bandit · CodeQL · Snyk ...)와
    에이전트 CLI 출력이 여기로 들어온다. **자격증명이 필요 없다.**
    """
    labeled = load_decoy_samples(corpus)
    if not labeled:
        print(f"평가 샘플이 없다: {corpus}", file=sys.stderr)
        return 2
    source = _import_source(src, identity, fmt)
    if source is None:
        return 2

    reviewer = ImportedReviewer(
        src, name=name, identity=source[0], kind=kind, fmt=source[1]
    )
    runs = max((reviewer.available_runs(s.sample_id) for s in labeled), default=0)
    if runs == 0:
        print(f"{src} 에 <sample_id>.json 이 하나도 없다", file=sys.stderr)
        return 2
    measured = _measured_pairs(labeled, reviewer, allow_partial=allow_partial)
    if measured is None:
        return 2
    labeled = measured

    if kind is ReviewerKind.AGENT:
        print(
            "⚠ agent 층이다 - 툴 접근·다회 턴이 가능해서 model_api 와 조건이 다르다.\n"
            "  같은 표에 놓되 섞어서 집계하지 않는다.\n"
        )

    graders = _graders_for(name, slack, labeled)
    run = run_reviewer(
        reviewer, labeled, graders, sample_n=runs,
        prompt_hash=reviewer.prompt_hash or "n/a",
    )
    if reviewer.unrecognized:
        # 🔴 저장하지 않는다 - 모르는 모양을 「지적 0건」으로 센 숫자다.
        print(
            f"🔴 --format {reviewer.fmt} 의 모양이 아닌 파일이 "
            f"{len(reviewer.unrecognized)}개다. 예: {reviewer.unrecognized[:2]}\n"
            "   이대로면 형식 착오가 「지적 0건」(미탐지)으로 채점된다. 저장하지 않는다.",
            file=sys.stderr,
        )
        return 2

    print("=" * 74)
    print(f"리뷰어: {run.reviewer}  ({reviewer.identity})  [{kind.value}]")
    print("-" * 74)
    print(run.manifest.disclosure_block())
    print("-" * 74)
    if reviewer.rejected:
        # 🔴 버린 지적은 미탐지와 구별되지 않는다 - 세어서 보인다.
        print(
            f"\n  ⚠ 파서가 버린 지적 {len(reviewer.rejected)}건 "
            "(제시되지 않은 파일 · 범위 밖 줄). 미탐지로 읽히지 않게 확인한다:"
        )
        for r in reviewer.rejected[:5]:
            print(f"      {r}")
    _print_observations(run)
    _print_spread(run, graders)
    _print_pairs(run, graders)
    _print_sensitivity(run, labeled, "provable_safety")
    _print_mix(run, labeled, "provable_safety")
    _print_strata(run)
    _persist(run, store_path)
    return 0


def _credentials_ready(name: str) -> bool:
    want = CREDENTIAL_OF.get(name)
    if want is None:
        return True
    st = next(s for s in all_statuses() if s.provider == want)
    if st.ready:
        return True
    print(f"{name}: {st.detail}", file=sys.stderr)
    print("  `codeproof doctor` 로 상태를 확인한다.", file=sys.stderr)
    return False


def _print_observations(run: ReviewerRun) -> None:
    """🔴 출현 빈도를 보여준다 - 평균이나 합집합으로 뭉개지 않는다 (F6)."""
    n = run.manifest.sample_n
    print(f"\n  관측 (각 {n}회 실행)")
    for o in run.outcomes:
        obs = o.observations.observed
        kind = "증명된 음성" if o.is_proven_safe else "양성(twin)"
        print(f"    {o.sample_id:40s} [{kind:10s}] 고유 {len(obs)}건")
        for ob in obs:
            print(
                f"      {ob.occurrences}/{n}  {ob.finding.rule_id:14s} "
                f"L{ob.finding.location.line:<4} {ob.finding.message[:36]}"
            )


def _cmd_doctor() -> int:
    """무엇이 준비됐고 무엇이 없는지 정확히 말한다."""
    print("정적분석 (API 불필요)")
    for a in (create_analyzer(n) for n in analyzer_available()):
        try:
            v = a.version()
            print(f"  o {a.name:<10} {v.version}")
        except Exception as exc:
            print(f"  x {a.name:<10} {type(exc).__name__}: {exc}")

    print("\n모델 provider (자격증명 필요)")
    ready = 0
    for st in all_statuses():
        mark = "o" if st.ready else "x"
        print(f"  {mark} {st.provider:<10} {st.detail}")
        ready += int(st.ready)

    if ready == 0:
        print(
            "\n  모델 비교는 자격증명이 있어야 돈다. 어댑터는 무인자 클라이언트를"
            "\n  쓰므로 어느 경로로 준비하든 코드 변경이 없다."
            "\n  그때까지도 `codeproof measure` 는 정적분석기로 완전히 동작한다."
        )
    return 0


def _cmd_history(store_path: str, limit: int, repro: str | None) -> int:
    with Store(store_path) as store:
        if repro:
            check = store.repro_check(repro)
            if not check.runs:
                print(f"그 설정의 실행이 없다: {repro}", file=sys.stderr)
                return 2
            print(f"config_hash={repro}  실행 {len(check.runs)}회")
            for rid in check.runs:
                print(f"  {rid}  지적 {len(store.finding_keys(rid))}건")
            _print_repro(check, "unknown")
            return 0

        rows = store.runs(limit)
        if not rows:
            print("저장된 실행이 없다")
            return 0
        print(f"  {'run_id':<26}{'config':<26}{'리뷰어':<10}{'effort':<10}{'지적':>5}")
        for r in rows:
            print(
                f"  {r.run_id:<26}{r.config_hash:<26}{r.reviewer:<10}"
                f"{r.effort:<10}{r.findings:>5}"
            )
        print()
        for ch, n in store.config_hashes():
            if n > 1:
                print(f"  같은 설정 {n}회: {ch}  → --repro {ch} 로 비교")
    return 0


def _cmd_measure(
    corpus: Path,
    analyzer_names: list[str],
    ruff_select: str | None,
    slack: int,
    store_path: str,
) -> int:
    samples = load_decoy_samples(corpus)
    if not samples:
        print(f"평가 샘플이 없다: {corpus}", file=sys.stderr)
        return 2

    analyzers: list[Analyzer] = []
    for name in analyzer_names:
        kwargs: dict[str, object] = {}
        if name == "ruff" and ruff_select:
            kwargs["select"] = tuple(ruff_select.split(","))
        try:
            analyzers.append(create_analyzer(name, **kwargs))
        except UnknownAnalyzerError as exc:
            print(exc, file=sys.stderr)
            return 2



    for analyzer in analyzers:
        graders = _graders_for(analyzer.name, slack, samples)
        run = run_reviewer(AnalyzerReviewer(analyzer), samples, graders)
        print("=" * 74)
        print(f"리뷰어: {run.reviewer}")
        print("-" * 74)
        print(run.manifest.disclosure_block())
        print("-" * 74)

        for sc in run.outcomes:
            obs = sc.observations.observed
            kind = "증명된 음성" if sc.is_proven_safe else "양성(twin)"
            print(f"  {sc.sample_id:42s} [{kind:10s}] 지적 {len(obs)}건")
            for g_name, js in sc.judgments.items():
                for o, j in zip(obs, js, strict=True):
                    print(
                        f"      {j.outcome.value.upper():12s} "
                        f"{o.finding.rule_id:8s} L{o.finding.location.line:<3} "
                        f"({g_name})"
                    )

        _print_spread(run, graders)
        _print_pairs(run, graders)
        _print_sensitivity(run, samples, "provable_safety")
        _print_mix(run, samples, "provable_safety")
        _print_strata(run)

        _persist(run, store_path)

    if warning := credibility_warning(sum(1 for s in samples if s.is_proven_safe)):
        sys.stdout.flush()
        print(f"! {warning}", file=sys.stderr)
    return 0


def _dispatch_decoy(args: argparse.Namespace) -> int:
    corpus = Path(args.corpus)
    if args.decoy_command == "validate":
        return _cmd_decoy_validate(corpus, strict=args.strict)
    if args.decoy_command == "stats":
        return _cmd_decoy_stats(corpus, args.ruff_select)
    return _cmd_decoy_new(corpus, args.decoy_id)


def _cmd_report(
    corpus: Path, analyzer: str, ruff_select: str, out: str, *, check: bool
) -> int:
    """🔴 측정값을 **생성**한다 - 문서가 숫자를 베끼면 반드시 낡는다."""
    samples = load_decoy_samples(corpus)
    if not samples:
        print(f"샘플이 없다: {corpus}", file=sys.stderr)
        return 2

    kwargs: dict[str, object] = {}
    if analyzer == "ruff" and ruff_select:
        kwargs["select"] = tuple(ruff_select.split(","))
    try:
        an = create_analyzer(analyzer, **kwargs)
    except UnknownAnalyzerError as exc:
        print(exc, file=sys.stderr)
        return 2

    graders = _graders_for(analyzer, 0, samples)
    run = run_reviewer(AnalyzerReviewer(an), samples, graders)
    body = render_measurements(run, samples, graders)

    if out == "-":
        print(body, end="")
        return 0

    target = Path(out)
    if check:
        current = target.read_text(encoding="utf-8") if target.is_file() else ""
        if current == body:
            print(f"{target} 는 최신이다")
            return 0
        print(
            f"{target} 가 낡았다 - `uv run codeproof report` 로 다시 만든다",
            file=sys.stderr,
        )
        return 1

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    print(f"{target} 를 썼다 ({len(body.splitlines())}줄)")
    return 0


def _cmd_decoy_stats(corpus: Path, ruff_select: str) -> int:
    """🔴 지적이 없으면 채점할 것도 없다 - 물리지 않는 decoy 를 세어 150 을 채우면
    숫자만 는다."""
    samples = load_decoy_samples(corpus)
    if not samples:
        print(f"평가 샘플이 없다: {corpus}", file=sys.stderr)
        return 2

    reviewers: dict[str, Reviewer] = {
        f"ruff({ruff_select})": AnalyzerReviewer(
            create_analyzer("ruff", select=tuple(ruff_select.split(",")))
        ),
        "mypy": AnalyzerReviewer(create_analyzer("mypy")),
    }
    cs = measure(samples, reviewers)

    print(f"  {'decoy':<34}{'미끼':>9}  " + "".join(f"{k:>14}" for k in cs.reviewers))
    for st in cs.stats:
        cells = "".join(
            f"{st.in_bait[k]:>6}/{st.total[k]:<7}" for k in cs.reviewers
        )
        mark = {"exercised": "", "untested": "  <- 아무도 안 뭄",
                "out_of_scope": "  <- 미끼 밖만 지적"}[st.status.value]
        print(f"  {st.sample_id[:34]:<34}{f'{st.covered[0]}-{st.covered[1]}':>9}  {cells}{mark}")

    rate = cs.exercised_rate
    print(f"\n  시험됨: {len(cs.by_status(BaitStatus.EXERCISED))}/{len(cs.stats)}"
          f"  ({rate:.0%})" if rate is not None else "")

    untested = cs.by_status(BaitStatus.UNTESTED)
    if untested:
        print(
            "\n  ⚠ 아래는 이 리뷰어들로 **시험되지 않았다**. 나쁘다는 뜻이 아니다 -\n"
            "    추론이 필요한 미끼일 수 있고, 그건 LLM 리뷰어가 있어야 안다.\n"
            "    정적분석기만으로는 「미시험」과 「미끼가 약함」을 구별할 수 없다."
        )
        for st in untested:
            print(f"      {st.sample_id}  ({st.trap_kind})")

    print("\n  trap 분류별 (시험됨/전체)")
    for trap, (hit, total) in sorted(cs.coverage_by_trap().items()):
        bar = "o" * hit + "." * (total - hit)
        print(f"      {trap:<24} {hit}/{total}  {bar}")
    return 0


_COMMANDS: dict[str, Callable[[argparse.Namespace], int]] = {
    "measure": lambda a: _cmd_measure(
        Path(a.corpus),
        [x.strip() for x in a.analyzers.split(",") if x.strip()],
        a.ruff_select,
        a.slack,
        a.store,
    ),
    "eval": lambda a: _cmd_eval(
        Path(a.corpus),
        [x.strip() for x in a.providers.split(",") if x.strip()],
        effort=a.effort,
        samples=a.samples,
        cache_policy=a.cache_policy,
        slack=a.slack,
        store_path=a.store,
    ),
    "report": lambda a: _cmd_report(
        Path(a.corpus), a.analyzer, a.ruff_select, a.out, check=a.check
    ),
    "export": lambda a: _cmd_export(Path(a.corpus), Path(a.out), a.prompt),
    "doctor": lambda _a: _cmd_doctor(),
    "history": lambda a: _cmd_history(a.store, a.limit, a.repro),
    "import": lambda a: _cmd_import(
        Path(a.corpus),
        Path(a.src),
        name=a.name,
        identity=a.identity,
        kind=ReviewerKind(a.kind),
        fmt=a.fmt,
        slack=a.slack,
        allow_partial=a.allow_partial,
        store_path=a.store,
    ),
    "decoy": _dispatch_decoy,
}


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handler = _COMMANDS.get(args.command)
    if handler is None:  # pragma: no cover - argparse 가 먼저 거른다
        print(f"알 수 없는 명령: {args.command}", file=sys.stderr)
        return 2
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
