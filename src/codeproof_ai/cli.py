"""CLI — 이 플랫폼의 주 진입점.

🔴 engine 은 HTTP 를 모른다 (DESIGN §6.5). FastAPI 는 v2 의 얇은 어댑터고,
   실험은 전부 여기서 배치로 돈다.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from codeproof_ai.analysis.registry import (
    UnknownAnalyzerError,
    create_analyzer,
)
from codeproof_ai.analysis.registry import available as analyzer_available
from codeproof_ai.corpus.decoy import pair_dirs, validate_corpus
from codeproof_ai.corpus.mutants import breaks, load_mutants, mutant_alias
from codeproof_ai.domain.reviewer import ReviewerKind
from codeproof_ai.eval.bait import BaitStatus, measure
from codeproof_ai.eval.export import DOCSTRING_MODES, export_for_agent, sample_digest
from codeproof_ai.eval.gate import RACE_RUNS, gate
from codeproof_ai.eval.grading.corroboration import StaticCorroborationGrader
from codeproof_ai.eval.grading.injected import InjectedDefectGrader
from codeproof_ai.eval.grading.paired import PairedFixGrader
from codeproof_ai.eval.grading.safety import ProvableSafetyGrader
from codeproof_ai.eval.loader import load_decoy_samples
from codeproof_ai.eval.metrics import MIN_CREDIBLE_NEGATIVES, TARGET_NEGATIVES, credibility_warning
from codeproof_ai.eval.mix import Axis, mix_sensitivity
from codeproof_ai.eval.multirun import EXPECTATION_LABEL, at_least, expectation, thresholds
from codeproof_ai.eval.pairing import (
    PairVerdict,
    discrimination_rate,
    pair_summary,
    score_pairs,
)
from codeproof_ai.eval.report import SETUP_KEYS, AgentSection, render_measurements
from codeproof_ai.eval.runner import (
    ReviewerRun,
    run_reviewer,
)
from codeproof_ai.eval.sensitivity import regrade_safety, sweep, sweep_views
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
from codeproof_ai.reviewers.imported import (
    BUNDLE_FILE,
    DIGEST_SUFFIX,
    RUN_FILE,
    ImportedReviewer,
    bundle_sample_ids,
    pack_runs,
    read_run_record,
    run_outputs,
    unpack_runs,
)
from codeproof_ai.reviewers.wrap import AnalyzerReviewer, ProviderReviewer
from codeproof_ai.store.sqlite import ReproCheck, Store

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from codeproof_ai.analysis.base import Analyzer
    from codeproof_ai.domain.reviewer import Reviewer
    from codeproof_ai.eval.grading.base import Grader
    from codeproof_ai.eval.sample import LabeledSample


def _add_decoy_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """`decoy` 하위 명령 - build_parser 가 너무 길어 떼어 냈다."""
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

    dmu = decoy_sub.add_parser(
        "mutants", help="쌍마다 실린 변이로 증명을 다시 깨 본다 - 경쟁 변이는 여러 번"
    )
    dmu.add_argument("--corpus", default="corpus/decoys")
    dmu.add_argument(
        "--race-runs",
        type=int,
        default=30,
        help="경쟁 변이를 몇 번 돌릴지 (0 이면 건너뛴다) - 약화는 매번 깨져야 한다",
    )
    dmu.add_argument("pairs", nargs="*", help="쌍 접두사 (예: XC001) - 없으면 전부")

    dg = decoy_sub.add_parser(
        "gate", help="codex 가 쓴 쌍의 관문 - 기계로 보는 것만 (DESIGN §7.10d)"
    )
    dg.add_argument("--corpus", default="corpus/xauthor/codex")
    dg.add_argument(
        "--race-runs",
        type=int,
        default=RACE_RUNS,
        help="경쟁 약화를 몇 번 돌릴지 - 매번 깨져야 한다 (관문은 건너뛰지 않는다)",
    )
    dg.add_argument("pairs", nargs="*", help="쌍 접두사 (예: XC001) - 없으면 전부")

    dn = decoy_sub.add_parser("new", help="템플릿에서 새 decoy 를 만든다")
    dn.add_argument("decoy_id", help="예: D00X-짧은-설명")
    dn.add_argument("--corpus", default="corpus/decoys")


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

    _add_decoy_parsers(sub)

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
    _add_pack_parser(sub)

    return parser


def _add_pack_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """에이전트 실행을 생성물에 싣는 모양으로 묶는다 - 파일 961개 대신 둘."""
    pk = sub.add_parser(
        "pack",
        help="에이전트 실행 출력을 RUN.json + findings.jsonl 로 묶는다 (report 가 읽는 모양)",
    )
    pk.add_argument("--from", dest="src", required=True, help="실행기 출력 디렉터리")
    pk.add_argument(
        "--out", required=True, help="묶음 디렉터리 - 보통 results/agent/<리뷰어 이름>"
    )
    pk.add_argument("--corpus", default="corpus/decoys")
    pk.add_argument(
        "--runs",
        type=int,
        default=None,
        help="앞 N회만 묶는다 - 묶을 회차 수는 결과를 보기 전에 정한다. 생략하면 있는 회차 전부",
    )


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
    rep.add_argument(
        "--agents",
        default="results/agent",
        help="에이전트 묶음(<이름>/RUN.json + findings.jsonl) 디렉터리. 없으면 정적분석기만",
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
    ex.add_argument(
        "--docstrings",
        choices=DOCSTRING_MODES,
        default="keep",
        help="모듈 docstring 손잡이 - neutral 은 기전 문장을 지운다 (DESIGN §7.10c)",
    )


def _cmd_export(corpus: Path, out: Path, prompt_name: str, docstrings: str = "keep") -> int:
    samples = load_decoy_samples(corpus)
    if not samples:
        print(f"샘플이 없다: {corpus}", file=sys.stderr)
        return 2
    try:
        manifest = export_for_agent(samples, out, prompt_name=prompt_name, docstrings=docstrings)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    n = len(manifest["samples"])  # type: ignore[arg-type]
    print(
        f"{out} 에 샘플 {n}개를 썼다 (prompt_hash={manifest['prompt_hash']} · "
        f"docstrings={docstrings})"
    )
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


def _cmd_decoy_gate(corpus: Path, race_runs: int, prefixes: Sequence[str]) -> int:
    """쌍마다 관문을 돈다 (DESIGN §7.10d) - 하나라도 실패하면 1, 쌍이 없으면 2."""
    if race_runs < 1:
        print("--race-runs 는 1 이상이다 - 관문은 경쟁 약화를 건너뛰지 않는다", file=sys.stderr)
        return 2
    pairs = [d for d in pair_dirs(corpus) if not prefixes or d.name.split("-")[0] in prefixes]
    if not pairs:
        print(f"쌍이 없다: {corpus}", file=sys.stderr)
        return 2
    failed = 0
    with tempfile.TemporaryDirectory(prefix="codeproof-gate-") as tmp:
        for pair in pairs:
            checks = gate(pair, Path(tmp), race_runs=race_runs)
            print(pair.name)
            for c in checks:
                print(f"  {'✓' if c.ok else '✗'}  {c.name}" + (f"  {c.detail}" if c.detail else ""))
            failed += not all(c.ok for c in checks)
    print(f"\n관문 {len(pairs)}쌍 · 통과 {len(pairs) - failed}")
    return 1 if failed else 0


def _cmd_decoy_mutants(corpus: Path, race_runs: int, prefixes: Sequence[str]) -> int:
    """쌍의 mutants.py 를 돌린다 - 결정적 변이는 한 번, 경쟁 변이(RACY)는 race_runs 번.

    🔴 경쟁 약화는 race_runs 번 **모두** 깨져야 한다 -
       한 번이라도 놓치면 그 증명은 flaky 한 관문이다 (교훈 #51).
    """
    if race_runs < 0:
        print("--race-runs 는 0 이상이다", file=sys.stderr)
        return 2
    pairs = [d for d in pair_dirs(corpus) if not prefixes or d.name.split("-")[0] in prefixes]
    wrong: list[str] = []
    counted = 0
    with tempfile.TemporaryDirectory(prefix="codeproof-mutants-") as tmp:
        workdir = Path(tmp)
        for pair in pairs:
            mutants = load_mutants(pair)
            if not mutants:
                continue
            print(pair.name)
            for i, mutant in enumerate(mutants):
                runs = race_runs if mutant.racy else 1
                if runs == 0:
                    print(f"  —  {mutant.label} (경쟁 · 건너뜀)")
                    continue
                broke = sum(
                    breaks(pair, mutant, workdir, mutant_alias(pair, i, r))
                    for r in range(runs)
                )
                counted += 1
                ok = broke == runs if mutant.expect_broken else broke == 0
                want = "약화" if mutant.expect_broken else "안전"
                mark = "✓" if ok else "✗"
                print(f"  {mark}  {mutant.label} ({want} · 깨짐 {broke}/{runs})")
                if not ok:
                    wrong.append(f"{pair.name} {mutant.label} {broke}/{runs}")
    print(f"\n변이 {counted}개 · 기대와 다름 {len(wrong)}")
    for w in wrong:
        print(f"  ✗ {w}")
    return 1 if wrong else 0


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
    sp = compute_spread(run.outcomes, graders, negatives_only=True)
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

    🔴 다회 실행이면 관점마다 낸다 - `sweep()` 은 합집합으로 센다 (F6).
    """
    if run.manifest.sample_n > 1:
        _print_sensitivity_views(run, samples)
        return
    sens = sweep(lambda slack: regrade_safety(run.outcomes, samples, slack), grader_name)
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


def _print_sensitivity_views(run: ReviewerRun, samples: Sequence[LabeledSample]) -> None:
    """다회 실행의 매칭 민감도 - 생성물과 **같은 함수**(`sweep_views`)로 관점마다 낸다."""
    vs = sweep_views(run.outcomes, samples)
    if vs is None:
        return
    print("\n  [매칭 민감도 · 관점별] slack 을 바꾸면 구별 성공(P-C)이 흔들리는가")
    print(f"    {'slack':>6}  {EXPECTATION_LABEL}  " + "  ".join(vs.thresholds))
    for p in vs.points:
        cells = "  ".join(f"{t.successes}/{t.total}" for t in p.thresholds)
        print(f"    {p.slack:>6}  {p.expectation:>14.1%}  {cells}")
    if vs.moved:
        print(
            f"    🔴 흔들린다 ({' · '.join(vs.moved)}) - "
            "단일 slack 값으로 낸 숫자를 결론으로 쓰지 않는다"
        )
    else:
        print("    o 모든 관점에서 안정 - 이 결론은 매칭 정책의 산물이 아니다")


def _print_pairs(
    run: ReviewerRun, graders: Sequence[Grader], samples: Sequence[LabeledSample]
) -> None:
    """🔴 짝 채점 - 과잉지적은 짝을 지어야만 보인다.

    🔴 다회 실행이면 합집합 한 줄로 내지 않는다 (F3 · F6). 8회 중 한 번 튄
       지적이 짝을 P-V 로 만들기 때문이다 - 관점마다 라벨을 붙여 낸다.
    """
    n = run.manifest.sample_n
    for g in graders:
        pairs = score_pairs(run.outcomes, g.name)
        if not pairs:
            continue
        print(f"\n  [짝 채점 · PrimeVul] 채점자={g.name}")
        if n > 1:
            print(f"    단일 실행 기대값 : {expectation(run.outcomes, samples, g).render()}")
            for label, k in thresholds(n):
                print(f"    {label:<16} : {at_least(run.outcomes, samples, g, k).render()}")
            continue
        hit, total_pairs = discrimination_rate(pairs)
        counts = pair_summary(pairs)
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
    """🔴 층별로 나눠서 본다. 풀링 금지 (F3)."""
    print()
    for r in run.results:
        if sum(r.counts.values()) == 0:
            continue
        print(f"  [{r.stratum}] 채점자={r.grader}")
        print(f"    정의        : {r.definition}")
        print(f"    Precision   : {r.precision.render()}")
        print(f"    판정불가율  : {r.undecidable_rate.render()}")
    print()


def _print_header(run: ReviewerRun, title: str) -> None:
    """리뷰어 줄과 매니페스트 공개 블록 - measure · eval · import 의 머리."""
    print("=" * 74)
    print(f"리뷰어: {title}")
    print("-" * 74)
    print(run.manifest.disclosure_block())
    print("-" * 74)


def _print_scoring(
    run: ReviewerRun, graders: Sequence[Grader], samples: Sequence[LabeledSample]
) -> None:
    """채점 절 - measure · eval · import 가 이 한 곳으로 같은 절을 같은 순서로 낸다.

    셋이 따로 부를 때는 절을 더하거나(`_print_mix`) 서명을 바꿀 때(`_print_pairs`)마다
    세 곳을 고쳤다.
    """
    _print_spread(run, graders)
    _print_pairs(run, graders, samples)
    _print_sensitivity(run, samples, "provable_safety")
    _print_mix(run, samples, "provable_safety")
    _print_strata(run)


def _print_repro(check: ReproCheck, deterministic: bool | None) -> None:
    """🔴 같은 설정의 결과가 같은가. 해석은 리뷰어가 결정적인지(`ReviewerKind`)에 달려 있다.

    모르면(None) 짐작하지 않는다 - 저장 기록에는 리뷰어 종류가 없다 (`history --repro`).
    [실측] 전에는 그 자리에 "unknown" 을 넘겨 정적분석기가 갈라져도 「모델은 비결정적」이라 했다.
    """
    n = len(check.runs)
    if check.identical:
        print(f"  재현성: 같은 설정 {n}회 실행, 지적 집합 **동일**")
        return

    volatile = len(check.volatile_keys)
    stable = len(check.stable_keys)
    print(f"  재현성: 같은 설정 {n}회 실행, 지적 집합 **불일치**")
    print(f"          공통 {stable}건 · 변동 {volatile}건")
    if deterministic is None:
        note = (
            "리뷰어 종류가 기록에 없다 - 정적분석기 · 가져온 지적이면 도구·환경 드리프트이고, "
            "모델 · 에이전트면 이 변동 폭이 측정 대상이다."
        )
    elif deterministic:
        note = "⚠ 정적분석기는 결정적이어야 한다 - 도구 버전이나 환경이 바뀌었는지 확인한다."
    else:
        note = "모델은 비결정적이다 - 이 변동 폭 자체가 측정 대상이다."
    print(f"          {note}")


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


def _persist(run: ReviewerRun, store_path: str, kind: ReviewerKind) -> None:
    """결과를 보관한다. 🔴 매니페스트 없이는 외래키가 거부한다 (F1).

    `kind` 는 리뷰어가 신고한 종류다 - 재현성 해석을 이름으로 짐작하지 않는다 (A2).
    """
    if store_path == "none":
        print("  ⚠ --store none - 이 결과는 재현할 수 없다")
        return
    with Store(store_path) as store:
        run_id = store.save(run)
        check = store.repro_check(run.manifest.config_hash)
    print(f"  저장: {store_path}  run_id={run_id}")
    if len(check.runs) > 1:
        _print_repro(check, kind.is_deterministic)





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
        reviewer = ProviderReviewer(provider, effort=effort, cache_policy=cache_policy)
        run = run_reviewer(
            reviewer,
            labeled,
            graders,
            sample_n=samples,
            prompt_hash=prompt_hash,
        )

        _print_header(run, f"{run.reviewer}  ({run.manifest.model_id})")
        print(f"  텔레메트리: {run.telemetry.render()}")
        _print_observations(run)
        _print_scoring(run, graders, labeled)
        _persist(run, store_path, reviewer.kind)

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
    labeled: list[LabeledSample], reviewer: ImportedReviewer, runs: int, *, allow_partial: bool
) -> list[LabeledSample] | None:
    """모든 실행이 있는 샘플만 남긴다. 못 하면 이유를 말하고 None.

    🔴 결과 파일이 없는 샘플은 「지적 0건」으로 들어온다 (ImportedReviewer.review).
       SARIF 도구라면 그게 맞다 - 돌았는데 아무것도 못 찾은 것이다. 그러나
       에이전트 실행이 중간에 끊긴 경우엔 **미측정이 미탐지로 둔갑**한다.
       그러면 P-B(둘 다 미지적)가 부풀어 리뷰어가 실제보다 나쁘게 나온다 -
       증거의 부재를 오답으로 세는 F4 와 같은 종류의 오류다.

    🔴 **실행이 모자란 샘플도 같다.** 8회 중 5회만 있으면 나머지 3회가
       「지적 0건」이 되어 출현 빈도(F6)가 거짓이 된다.
    """
    # 앞 N회만 쓸 때는 N회 이상 있는 샘플이 완전하다 - 기본(N = 최댓값)에서는 == 와 같다.
    complete = {s.sample_id for s in labeled if reviewer.available_runs(s.sample_id) >= runs}
    missing = [s.sample_id for s in labeled if s.sample_id not in complete]
    if not missing:
        return labeled
    covered = len(complete)
    print(
        f"결과가 없거나 {runs}회에 모자란 샘플이 {len(missing)}개다 "
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
    kept = [s for s in labeled if s.sample_id in complete and s.paired_with in complete]
    if not kept:
        print("  완전한 짝이 하나도 없다 - 짝의 양쪽이 모두 있어야 채점된다.", file=sys.stderr)
        return None
    print(
        f"  ⚠ --allow-partial - 완전한 짝 {len(kept) // 2}쌍만 집계한다 "
        f"(결과가 있던 샘플 {covered}개 중).",
        file=sys.stderr,
    )
    return kept


def _replay(
    labeled: list[LabeledSample],
    src: Path,
    *,
    name: str,
    kind: ReviewerKind,
    identity: str | None = None,
    fmt: str | None = None,
    slack: int = 0,
    allow_partial: bool = False,
    first_runs: int | None = None,
) -> tuple[ReviewerRun, ImportedReviewer, list[Grader], list[LabeledSample]] | None:
    """저장된 지적을 채점까지 재생한다. 안 되면 이유를 말하고 None.

    🔴 import 와 report 가 **이 경로 하나**를 탄다 - E00 과 같은 이유다. 갈리면 새 검사가
       한쪽에서 빠지고, 같은 실행이 import 출력과 생성물에서 다른 숫자를 낸다.

    회차 수는 파일에 있는 연속 회차의 최댓값이다. `first_runs` 를 주면 앞 N회만 쓴다.
    """
    source = _import_source(src, identity, fmt)
    if source is None:
        return None
    reviewer = ImportedReviewer(src, name=name, identity=source[0], kind=kind, fmt=source[1])
    available = max((reviewer.available_runs(s.sample_id) for s in labeled), default=0)
    if available == 0:
        print(f"{src} 에 <sample_id>.json 이 하나도 없다", file=sys.stderr)
        return None
    runs = available if first_runs is None else first_runs
    measured = _measured_pairs(labeled, reviewer, runs, allow_partial=allow_partial)
    if measured is None:
        return None

    graders = _graders_for(name, slack, measured)
    run = run_reviewer(
        reviewer, measured, graders, sample_n=runs,
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
        return None
    return run, reviewer, graders, measured


def _stale_outputs(src: Path, labeled: list[LabeledSample], runs: int | None = None) -> bool:
    """🔴 실행기 출력에 **지금 코드로 잰 것이 아닌** 회차가 있으면 이유를 말하고 True.

    pack 의 `packed_digests` 는 묶는 시점의 코퍼스로 계산한다 - 고친 샘플만 다시 잴 때 옛 출력이
    하나라도 남으면 그 출력이 새 지문으로 묶여 옛 지적이 새 코드로 조용히 채점된다 (DESIGN §9 의 5).
    실행기가 회차마다 남긴 지문(`<sample_id>.<run>.digest`)으로 견준다 - 없어도 거부한다.
    pack 과 import 가 **같은 검사**를 탄다 (E00). 코퍼스 밖 샘플은 호출부가 따로 거부한다.
    """
    current = {s.sample_id: sample_digest(s) for s in labeled}
    stale = []
    for sid, run, path in run_outputs(src, runs):
        if sid not in current:
            continue
        side = path.with_suffix(DIGEST_SUFFIX)
        words = side.read_text(encoding="utf-8").split() if side.is_file() else []
        if not words or words[0] != current[sid]:
            stale.append(f"{sid}.{run}")
    if stale:
        print(
            f"🔴 {src} 에 지금 코드로 잰 것이 아닌 회차가 {len(stale)}개 있다 "
            f"(지문 옆 파일이 없거나 다르다 · 예: {stale[:3]}) - 그대로 쓰면 옛 지적이 새 코드로 "
            "채점된다. 그 출력을 옮기고 다시 잰다",
            file=sys.stderr,
        )
    return bool(stale)


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
    # 실행기 출력(RUN.json)만 지문을 남긴다 - 손으로 모은 출력은 견줄 것이 없다
    if kind is ReviewerKind.AGENT and read_run_record(src) is not None and _stale_outputs(
        src, labeled
    ):
        return 2
    replay = _replay(
        labeled, src, name=name, kind=kind, identity=identity, fmt=fmt,
        slack=slack, allow_partial=allow_partial,
    )
    if replay is None:
        return 2
    run, reviewer, graders, labeled = replay

    if kind is ReviewerKind.AGENT:
        print(
            "⚠ agent 층이다 - 툴 접근·다회 턴이 가능해서 model_api 와 조건이 다르다.\n"
            "  같은 표에 놓되 섞어서 집계하지 않는다.\n"
        )

    _print_header(run, f"{run.reviewer}  ({reviewer.identity})  [{kind.value}]")
    if reviewer.rejected:
        # 🔴 버린 지적은 미탐지와 구별되지 않는다 - 세어서 보인다.
        print(
            f"\n  ⚠ 파서가 버린 지적 {len(reviewer.rejected)}건 "
            "(제시되지 않은 파일 · 범위 밖 줄 · 위치 없음). 미탐지로 읽히지 않게 확인한다:"
        )
        for r in reviewer.rejected[:5]:
            print(f"      {r}")
    _print_observations(run)
    _print_scoring(run, graders, labeled)
    _persist(run, store_path, reviewer.kind)
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
            _print_repro(check, None)
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
        reviewer = AnalyzerReviewer(analyzer)
        run = run_reviewer(reviewer, samples, graders)
        _print_header(run, run.reviewer)

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

        _print_scoring(run, graders, samples)
        _persist(run, store_path, reviewer.kind)

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
    if args.decoy_command == "mutants":
        return _cmd_decoy_mutants(corpus, args.race_runs, args.pairs)
    if args.decoy_command == "gate":
        return _cmd_decoy_gate(corpus, args.race_runs, args.pairs)
    return _cmd_decoy_new(corpus, args.decoy_id)


def _collected(src: Path, samples: list[LabeledSample]) -> tuple[list[LabeledSample], int] | None:
    """묶음이 잰 샘플과, 코퍼스에 있는데 재지 않은 쌍 수. 기록 · 묶음 · 코퍼스가 어긋나면 None.

    🔴 완결을 **지금** 코퍼스로 재면 쌍 하나만 더해도 모든 묶음이 「부분 실행」이 된다
       [실측 · 적용 범위 120/122]. 그렇다고 묶음의 행에서 집합을 뽑으면, 샘플이 통째로 빠진
       끊긴 실행이 「작은 코퍼스」로 통과한다. 그래서 pack 이 잰 샘플을 적고(`packed_samples`)
       report 는 그 샘플만 재생한다 - 그 안에서는 지금처럼 엄격하다 (`_replay`).
    """
    record = read_run_record(src) or {}
    packed = record.get("packed_samples")
    if not (isinstance(packed, list) and packed and all(isinstance(p, str) for p in packed)):
        print(
            f"  🔴 {src / RUN_FILE} 에 packed_samples 가 없다 - 어느 샘플을 쟀는지 모르면 수집 뒤 "
            "늘어난 코퍼스와 끊긴 실행을 가를 수 없다. `codeproof pack` 으로 다시 묶는다",
            file=sys.stderr,
        )
        return None
    listed = set(packed)
    rows = bundle_sample_ids((src / BUNDLE_FILE).read_text(encoding="utf-8"))
    if rows != listed:
        print(
            f"  🔴 {src} 의 묶음이 packed_samples 와 다르다 - 빠진 샘플 "
            f"{sorted(listed - rows)[:3]} · 목록 밖 샘플 {sorted(rows - listed)[:3]}",
            file=sys.stderr,
        )
        return None
    gone = sorted(listed - {s.sample_id for s in samples})
    if gone:
        print(
            f"  🔴 {src} 가 잰 샘플 {len(gone)}개가 코퍼스에 없다 (예: {gone[:3]}) - 코퍼스에서 "
            "빠졌거나 다른 코퍼스다. 빼고 재생하면 비교 대상이 조용히 줄어든다",
            file=sys.stderr,
        )
        return None
    collected = [s for s in samples if s.sample_id in listed]
    # 🔴 재생 집합이 코퍼스 전체이던 때는 짝이 늘 닫혀 있었다. 목록으로 고르면 아니다 -
    #    반쪽 짝은 `score_pairs` 가 조용히 버린다 [실측: 「짝 59쌍」 · 경고 없음].
    half = sorted(s.sample_id for s in collected if s.paired_with not in listed)
    if half:
        print(
            f"  🔴 {src} 의 packed_samples 에 짝이 반쪽인 샘플이 있다 (예: {half[:3]}) - "
            "반쪽 짝은 채점에서 조용히 빠진다",
            file=sys.stderr,
        )
        return None
    stale = _stale_since_packing(src, record.get("packed_digests"), collected, listed)
    if stale:
        print(stale, file=sys.stderr)
        return None
    unmeasured = sum(1 for s in samples if s.is_proven_safe and s.sample_id not in listed)
    return collected, unmeasured


def _stale_since_packing(
    src: Path, digests: object, collected: list[LabeledSample], listed: set[str]
) -> str | None:
    """잰 코드와 지금 코퍼스가 다르면 그 사유, 같으면 None.

    🔴 잰 뒤 코드가 바뀐 샘플은 재생하지 않는다 - 옛 지적이 새 코드로 조용히 채점된다
       (DESIGN §9 의 5). 지문이 없으면 잰 코드가 지금 코퍼스와 같은지 말할 수 없다.
    """
    if not (isinstance(digests, dict) and set(digests) == listed):
        return (
            f"  🔴 {src / RUN_FILE} 에 packed_digests 가 없거나 packed_samples 와 다르다 - "
            "잰 코드가 지금 코퍼스와 같은지 모르면 옛 지적을 새 코드로 채점할 수 있다. "
            "`codeproof pack` 으로 다시 묶는다"
        )
    changed = sorted(s.sample_id for s in collected if digests[s.sample_id] != sample_digest(s))
    if changed:
        return (
            f"  🔴 {src} 가 잰 뒤 코드가 바뀐 샘플이 {len(changed)}개 있다 (예: {changed[:3]}) - "
            "옛 지적을 새 코드로 채점하게 된다. 그 샘플을 다시 재거나 묶음에서 뺀다"
        )
    return None


def _agent_sections(root: Path, samples: list[LabeledSample]) -> list[AgentSection] | None:
    """저장소에 둔 에이전트 실행을 import 와 **같은 경로**로 재생한다. 못 하면 None.

    🔴 `runs.db` 가 아니라 저장소의 묶음에서 읽는다 - `runs.db` 는 로컬이라 클린 클론에서
       `report --check` 가 재현되지 않는다. 층은 디렉터리가 정한다 (`agent`).
    🔴 실행은 **잰 샘플**(`packed_samples`)로만 재생한다 - 코퍼스가 자라도 숫자가 그대로다.
       그 안의 부분 실행은 싣지 않는다 - 모자란 회차가 「지적 0건」으로 실린다 (F6).
    """
    if not root.is_dir():
        return []
    sections: list[AgentSection] = []
    for src in sorted(p for p in root.iterdir() if p.is_dir()):
        if not (src / BUNDLE_FILE).is_file() or not (src / RUN_FILE).is_file():
            print(
                f"  🔴 {src} 에 {RUN_FILE} + {BUNDLE_FILE} 이 없다 - `codeproof pack` 으로 묶는다",
                file=sys.stderr,
            )
            return None
        found = _collected(src, samples)
        if found is None:
            return None
        collected, unmeasured = found
        with tempfile.TemporaryDirectory() as tmp:
            box = Path(tmp)  # 분석기의 materialize 와 같다 - 실행기 출력 모양으로 되돌려 읽는다
            shutil.copyfile(src / RUN_FILE, box / RUN_FILE)
            unpack_runs(src / BUNDLE_FILE, box)
            replay = _replay(
                collected, box, name=src.name, kind=ReviewerKind.AGENT, allow_partial=False
            )
        if replay is None:
            print(
                f"  🔴 {src} 를 싣지 않는다 - 생성물에는 잰 샘플의 모든 회차가 있는 "
                "실행만 싣는다. 이어서 돌려 채우거나 디렉터리를 뺀다.",
                file=sys.stderr,
            )
            return None
        run, reviewer, graders, _ = replay
        record = reviewer.run_record or {}
        packed = record.get("packed_runs")
        sections.append(
            AgentSection(
                run=run,
                graders=tuple(graders),
                rejected=len(reviewer.rejected),
                packed_runs=int(packed) if packed else None,
                agent=str(record.get("agent", "")),
                docstrings=str(record.get("docstrings", "")),
                setup=tuple((k, str(record.get(k, ""))) for k in SETUP_KEYS),
                unmeasured_pairs=unmeasured,
            )
        )
    return sections


def _cmd_pack(corpus: Path, src: Path, out: Path, *, runs: int | None = None) -> int:
    """에이전트 실행을 `RUN.json` + `findings.jsonl` 로 묶는다 - 저장소에 싣는 모양.

    🔴 import 와 **같은 경로**로 먼저 재생해 본다 - 모자란 회차 · 모르는 모양이면 묶지 않는다.
       원본 응답(raw/)은 싣지 않는다. 로컬 `runs/` 에 둔다.

    `runs` 는 앞 N회만 묶는다 - 실행 기록의 `runs` 는 세션 목표의 최댓값이라 실제로
    묶은 회차 수와 다를 수 있다. 그래서 묶음의 기록에 `packed_runs` 를 따로 적는다.

    묶은 샘플은 `packed_samples` 로 적는다 - 코퍼스가 자라도 report 가 이 샘플로만 재생한다.
    """
    if runs is not None and runs < 1:
        print(f"--runs 는 1 이상이다 (받은 값 {runs})", file=sys.stderr)
        return 2
    labeled = load_decoy_samples(corpus)
    if not labeled:
        print(f"평가 샘플이 없다: {corpus}", file=sys.stderr)
        return 2
    replayed = None if _stale_outputs(src, labeled, runs) else _replay(
        labeled, src, name=out.name, kind=ReviewerKind.AGENT, allow_partial=False, first_runs=runs
    )
    if replayed is None:
        return 2
    # 🔴 묶음은 재생으로 **검증한** 샘플만이다. 실행기 출력에 코퍼스 밖 샘플이 섞이면 다른
    #    코퍼스로 돈 실행이다 - 그대로 묶으면 검증 안 된 샘플(반쪽 짝 포함)이 기록에 실린다.
    packed = sorted(s.sample_id for s in replayed[3])
    body = pack_runs(src, runs)
    # 코퍼스로 거른다 - 검증 목록(`packed`)으로 거르면 모자란 샘플까지 「코퍼스 밖」으로 잘못 부른다
    # [실측: falsify pack-partial 이 그 오진 때문에 공허해졌다].
    stray = sorted(bundle_sample_ids(body) - {s.sample_id for s in labeled})
    if stray:
        print(
            f"{src} 에 코퍼스 밖 샘플이 있다 (예: {stray[:3]}) - 다른 코퍼스로 돈 실행이다. "
            "그 코퍼스로 묶는다",
            file=sys.stderr,
        )
        return 2
    keep = {RUN_FILE, BUNDLE_FILE}
    extra = sorted(p.name for p in out.iterdir() if p.name not in keep) if out.is_dir() else []
    if extra:
        # 옛 파일이 남으면 무엇이 실렸는지 알 수 없다 - 덮어쓰지 않는다
        print(f"{out} 에 다른 파일이 있다 (예: {extra[:3]}) - 비우고 다시 묶는다", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    (out / BUNDLE_FILE).write_text(body, encoding="utf-8")
    record = json.loads((src / RUN_FILE).read_text(encoding="utf-8"))
    if runs is not None:
        record["packed_runs"] = str(runs)
    # 🔴 묶은 샘플을 적는다 - 없으면 「수집 뒤 늘어난 코퍼스」와 「끊긴 실행」을 가를 수 없다 (F6).
    record["packed_samples"] = packed
    # 🔴 잰 코드의 지문 - 뒤에 decoy 를 고치면 report 가 그 샘플을 싣지 않는다 (DESIGN §9 의 5).
    verified = sorted(replayed[3], key=lambda s: s.sample_id)
    record["packed_digests"] = {s.sample_id: sample_digest(s) for s in verified}
    (out / RUN_FILE).write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    rows = body.count("\n")  # splitlines() 는 문구 안의 U+2028 에서도 끊는다 - unpack_runs
    print(f"{out} 를 썼다: {RUN_FILE} + {BUNDLE_FILE} ({rows}회차)")
    return 0


def _cmd_report(
    corpus: Path, analyzer: str, ruff_select: str, out: str, *, check: bool, agents: Path
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
    sections = _agent_sections(agents, samples)
    if sections is None:
        return 2
    # 보조 ③ - twin 정답 구간을 넓힌 라벨. 에이전트 비교에서만 쓴다 (DESIGN §7.10c).
    widened = load_decoy_samples(corpus, widen_twin=True) if sections else []
    return _emit_generated(
        render_measurements(run, samples, graders, sections, widened), out, check=check
    )


def _emit_generated(body: str, out: str, *, check: bool) -> int:
    """생성물을 쓰거나, 쓰지 않고 최신인지만 본다 (다르면 1)."""
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
        Path(a.corpus), a.analyzer, a.ruff_select, a.out, check=a.check, agents=Path(a.agents)
    ),
    "export": lambda a: _cmd_export(Path(a.corpus), Path(a.out), a.prompt, a.docstrings),
    "pack": lambda a: _cmd_pack(Path(a.corpus), Path(a.src), Path(a.out), runs=a.runs),
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
