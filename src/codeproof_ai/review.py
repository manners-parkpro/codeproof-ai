"""정답이 없는 코드의 리뷰 보고서 - 지적과 그 근거를 모은다. 결함을 확인하지 않는다.

    codeproof review <파일.py> [--out 보고서.md] [--agent claude|codex]

이 저장소는 정답이 있는 쌍 위에서만 맞다 · 틀리다를 말한다. 사용자가 넣은 파일에는 정답이
없으므로 채점하지 않고, 리뷰어(Ruff · mypy)의 지적마다 검증 레이어(verify/)가 모은 근거를
붙여 보여 준다.

🔴 「결함 확인」이라고 쓰지 않는다 (CLAUDE.md F4 · E2) - 근거를 못 찾은 것은 반박이 아니고,
   모인 근거(confidence)는 확률이 아니다 (E3).
🔴 리뷰도 `run_reviewer` 한 곳으로 돈다 (E00) - 둘러싼 함수를 붙이는 훅이 빠지지 않는다.
🔴 교차 확인자에는 다른 도구의 지적만 넘긴다 - 자기 확인은 항등식이다 (F7).
🔴 에이전트(`--agent`)는 측정과 같은 실행기로 돈다 - 격리 · 모델 고정 · effort 명시 (A2b).
   답을 남기지 않은 실행은 「지적 0건」이 아니라 오류다 (F4).
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from codeproof_ai.analysis.registry import create_analyzer
from codeproof_ai.domain.evidence import EvidenceKind, Verdict
from codeproof_ai.domain.reviewer import ReviewerKind
from codeproof_ai.domain.target import ReviewTarget, SourceFile
from codeproof_ai.eval.export import export_for_agent
from codeproof_ai.eval.runner import run_reviewer
from codeproof_ai.eval.sample import LabeledSample, Stratum
from codeproof_ai.reviewers.imported import ImportedReviewer, read_run_record
from codeproof_ai.reviewers.wrap import AnalyzerReviewer
from codeproof_ai.verify.citation import CitationVerifier
from codeproof_ai.verify.confidence import VerificationPipeline, Weights
from codeproof_ai.verify.corroboration import CorroborationVerifier
from codeproof_ai.verify.guard import GuardVerifier
from codeproof_ai.verify.reachability import ReachabilityVerifier

if TYPE_CHECKING:
    from collections.abc import Sequence

    from codeproof_ai.domain.evidence import VerifiedFinding
    from codeproof_ai.domain.finding import Finding
    from codeproof_ai.verify.base import Verifier

REVIEWERS = ("ruff", "mypy")
"""자격증명 없이 도는 리뷰어 - 정적분석기다."""

TARGET_ID = "review"
AGENTS = ("claude", "codex")
AGENT_EFFORT = "low"
"""측정과 같은 조건 - 벤더의 최상위 모델 · effort low (DESIGN §7.10b)."""
AGENT_TIMEOUT_S = 900
RUNNER = Path(__file__).resolve().parents[2] / "scripts" / "review-with-agent.sh"
RESULTS = "https://github.com/manners-parkpro/codeproof-ai/blob/main/docs/RESULTS.md"
"""보고서는 저장소 밖에 쓰일 수 있다 - 상대 경로는 깨진다."""

VERDICT = {
    Verdict.SUPPORTS: "뒷받침",
    Verdict.REFUTES: "반박",
    Verdict.INCONCLUSIVE: "판단 못 함",
    Verdict.NOT_APPLICABLE: "해당 없음",
}
KIND = {
    EvidenceKind.CITATION: "인용",
    EvidenceKind.CORROBORATION: "교차 확인",
    EvidenceKind.GUARD: "가드",
    EvidenceKind.REACHABILITY: "도달성",
}

LIMITS = (
    "교차 확인 — 다른 도구가 같은 자리(±2줄)를 짚었는지만 본다. 짚지 않은 것은 반박이 아니다 "
    "(mypy 에는 보안 규칙이 없다).",
    "가드 — 이른 반환 · 예외 같은 모양만 찾는다. 데이터 흐름으로 막는 가드는 보지 못한다. "
    "못 찾은 것은 가드가 없다는 뜻이 아니다.",
    "도달성 — 이 파일 안의 함수 참조만 본다. 분기 단위 · 파일 밖 · 동적 호출은 보지 못한다.",
    "인용 — 모델이 인용한 코드가 그 자리에 실제로 있는지 보는 검증이다. 정적분석기는 파일을 "
    "직접 읽어 늘 맞으므로 돌리지 않는다.",
)


class ReviewError(Exception):
    """에이전트 리뷰를 낼 수 없다 - 이유를 말한다. 「지적 0건」으로 접지 않는다."""


@dataclass(frozen=True, slots=True)
class ReviewEntry:
    reviewer: str
    verified: VerifiedFinding


@dataclass(frozen=True, slots=True)
class ReviewReport:
    path: str
    reviewers: tuple[str, ...]
    """리뷰어와 판 (예: ruff/0.15.2)."""

    entries: tuple[ReviewEntry, ...]
    agent: str | None = None


def run_agent(agent: str, src: Path, out: Path) -> None:
    """측정과 같은 실행기(scripts/review-with-agent.sh)로 에이전트 리뷰를 한 번 돈다."""
    if not RUNNER.is_file():
        msg = f"에이전트 실행기가 없다 ({RUNNER.name}) - 저장소에서 uv run 으로 돌린다"
        raise ReviewError(msg)
    cmd = ["bash", str(RUNNER), agent, str(src), str(out), "--effort", AGENT_EFFORT, "--runs", "1"]
    done = subprocess.run(  # noqa: S603 - 인자는 이 함수가 만든다
        cmd, capture_output=True, text=True, check=False, timeout=AGENT_TIMEOUT_S,
    )
    if done.returncode != 0:
        tail = " ".join((done.stderr or done.stdout).strip().split("\n")[-3:])
        msg = f"{agent} 리뷰가 실패했다 (rc {done.returncode}) - {tail}"
        raise ReviewError(msg)


def agent_review(
    sample: LabeledSample, agent: str, work: Path,
) -> tuple[str, tuple[Finding, ...]]:
    """내보내기 → 실행기 → 가져오기 - 가져온 지적도 run_reviewer 한 곳으로 돈다 (E00)."""
    src, out = work / "in", work / "out"
    export_for_agent([sample], src)
    run_agent(agent, src, out)
    record = read_run_record(out)
    if not record or not record.get("identity"):
        msg = f"{agent} 실행 기록(RUN.json)이 없다 - 무엇이 리뷰했는지 모른다"
        raise ReviewError(msg)
    reviewer = ImportedReviewer(
        out, name=agent, identity=str(record["identity"]), kind=ReviewerKind.AGENT, fmt="native",
    )
    if reviewer.available_runs(sample.sample_id) < 1:
        msg = f"{agent} 가 답을 남기지 않았다 - 지적 0건으로 세지 않는다"
        raise ReviewError(msg)
    run = run_reviewer(reviewer, [sample], [])
    if reviewer.unrecognized:
        msg = f"{agent} 의 답이 지적 모양이 아니다: {reviewer.unrecognized[:1]}"
        raise ReviewError(msg)
    return reviewer.identity, tuple(o.finding for o in run.outcomes[0].observations.observed)


def review_file(
    path: Path, *, reviewers: Sequence[str] = REVIEWERS, agent: str | None = None,
) -> ReviewReport:
    """파일 하나에 리뷰어를 돌리고, 지적마다 근거를 모은다 - 채점하지 않는다."""
    target = ReviewTarget(
        target_id=TARGET_ID,
        files=(SourceFile(path=path.name, content=path.read_text(encoding="utf-8")),),
    )
    sample = LabeledSample(target=target, stratum=Stratum.UNLABELED)
    found: dict[str, tuple[Finding, ...]] = {}
    kinds: dict[str, ReviewerKind] = {}
    identities = []
    for name in reviewers:
        reviewer = AnalyzerReviewer(create_analyzer(name))
        run = run_reviewer(reviewer, [sample], [])
        found[name] = tuple(o.finding for o in run.outcomes[0].observations.observed)
        kinds[name] = reviewer.kind
        identities.append(reviewer.identity)
    if agent is not None:
        with tempfile.TemporaryDirectory(prefix="codeproof-review-") as work:
            identity, findings = agent_review(sample, agent, Path(work))
        found[agent], kinds[agent] = findings, ReviewerKind.AGENT
        identities.append(identity)
    entries = []
    for name, findings in found.items():
        others = [f for other, fs in found.items() if other != name for f in fs]
        verifiers: list[Verifier] = [
            CorroborationVerifier(reference=others), GuardVerifier(), ReachabilityVerifier(),
        ]
        if not kinds[name].is_deterministic:
            # 🔴 인용은 모델 지적에서만 뜻이 있다 - 정적분석기의 「인용」은 늘 맞아 근거를 부풀린다
            verifiers.insert(0, CitationVerifier())
        pipeline = VerificationPipeline(verifiers)
        entries += [ReviewEntry(name, pipeline.run(f, target)) for f in findings]
    entries.sort(key=lambda e: (e.verified.finding.location.line, e.reviewer))
    return ReviewReport(
        path=path.name, reviewers=tuple(identities), entries=tuple(entries), agent=agent,
    )


def render_review(report: ReviewReport) -> str:
    """Markdown 보고서 - 지적마다 근거를 붙이고, 검증자가 못 보는 것을 같이 적는다."""
    lines = [
        f"# 리뷰 보고서 — {report.path}",
        "",
        "> 결함을 확인하는 보고서가 아니다. 리뷰어의 지적과, 지적마다 모은 근거를 보여 준다.",
        "> 근거를 못 찾은 것은 지적이 틀렸다는 뜻이 아니고, 「모인 근거」는 확률이 아니다.",
        "> 「모인 근거」는 0.5 에서 시작해 뒷받침이면 더하고 반박이면 뺀다 — 가중치는 임의값이다"
        f" ({Weights().signature()}).",
        "",
        f"- 리뷰어: {' · '.join(report.reviewers)}"
        + (" (정적분석기 + 에이전트)" if report.agent else " (정적분석기 · 자격증명 불필요)"),
        "- 근거: 교차 확인 · 가드 · 도달성 · 인용(모델 지적만) (`src/codeproof_ai/verify/`)",
        "",
    ]
    if not report.entries:
        lines += ["## 지적 0건", "", "리뷰어가 짚은 것이 없다 — 결함이 없다는 뜻은 아니다.", ""]
    else:
        lines += [f"## 지적 {len(report.entries)}건", ""]
    for n, e in enumerate(report.entries, 1):
        f = e.verified.finding
        rule = f"{f.rule_id} " if f.rule_id else ""
        lines += [f"### {n}. {f.location.line}행 · {e.reviewer} {rule}— {f.message}", ""]
        for ev in e.verified.evidence:
            lines.append(f"- {KIND[ev.kind]}: {VERDICT[ev.verdict]} — {ev.detail}")
        lines += [f"- 모인 근거: {e.verified.confidence:.2f}", ""]
    lines += ["## 검증자가 보지 못하는 것", ""]
    lines += [f"- {limit}" for limit in LIMITS]
    lines += [
        "",
        f"정답이 있는 쌍에서 이 리뷰어들이 낸 성적은 [RESULTS]({RESULTS}) 에 있다.",
        "",
    ]
    return "\n".join(lines)
