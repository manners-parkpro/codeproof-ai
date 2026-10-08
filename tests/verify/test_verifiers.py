"""런타임 검증.

🔴 이 레이어를 관통하는 규약 하나: **못 찾은 것은 없다는 뜻이 아니다.**
   REFUTES 는 찾았을 때만 낸다. 그래서 「INCONCLUSIVE 여야 하는데 REFUTES 가
   나오는가」를 검사하는 테스트가 기능 테스트만큼 많다.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from codeproof_ai.analysis.python.mypy_ import MypyAnalyzer
from codeproof_ai.analysis.python.ruff import RuffAnalyzer
from codeproof_ai.domain.evidence import Evidence, EvidenceKind, Verdict
from codeproof_ai.domain.finding import Category, Finding, Severity
from codeproof_ai.domain.location import Location, Position, Span
from codeproof_ai.domain.target import ReviewTarget, SourceFile
from codeproof_ai.eval.loader import load_decoy_samples
from codeproof_ai.verify.citation import CitationVerifier, MatchLevel
from codeproof_ai.verify.confidence import (
    VerificationPipeline,
    Weights,
    aggregate,
)
from codeproof_ai.verify.corroboration import (
    CorroborationVerifier,
    SelfCorroborationError,
)
from codeproof_ai.verify.guard import GuardVerifier
from codeproof_ai.verify.reachability import ReachabilityVerifier

DECOYS = Path(__file__).resolve().parents[2] / "corpus" / "decoys"


REPO = Path(__file__).resolve().parents[2]

def _t(src: str, path: str = "m.py") -> ReviewTarget:
    return ReviewTarget(target_id="t", files=(SourceFile(path, src),))


def _f(
    line: int,
    quote: str | None = None,
    *,
    source: str = "claude",
    symbol: str | None = None,
    path: str = "m.py",
) -> Finding:
    return Finding(
        source=source,
        rule_id="x",
        message="m",
        location=Location(
            path=path, span=Span(Position(line, 0)), symbol=symbol
        ),
        category=Category.CORRECTNESS,
        severity=Severity.WARNING,
        quoted_code=quote,
    )


class TestCitation:
    SRC = "def f():\n    x = compute()\n    return x\n"

    def test_exact_quote_at_line(self) -> None:
        ev = CitationVerifier().verify(_f(2, "x = compute()"), _t(self.SRC))
        assert ev.verdict is Verdict.SUPPORTS

    def test_reformatted_quote_is_not_a_hallucination(self) -> None:
        """공백이 다른 건 재포맷이지 환각이 아니다."""
        ev = CitationVerifier().verify(_f(2, "x  =  compute()"), _t(self.SRC))
        assert ev.verdict is Verdict.SUPPORTS

    def test_strict_mode_rejects_reformatting(self) -> None:
        v = CitationVerifier(normalize=False)
        assert v.match_level(_f(2, "x  =  compute()"), _t(self.SRC)) is MatchLevel.NOT_FOUND

    def test_wrong_line_is_inconclusive_not_refuted(self) -> None:
        """🔴 위치가 틀린 것과 코드가 없는 것은 다르다."""
        ev = CitationVerifier(line_window=0).verify(
            _f(3, "x = compute()"), _t(self.SRC)
        )
        assert ev.verdict is Verdict.INCONCLUSIVE

    def test_fabricated_quote_is_refuted(self) -> None:
        ev = CitationVerifier().verify(_f(2, "os.system(cmd)"), _t(self.SRC))
        assert ev.verdict is Verdict.REFUTES

    def test_missing_quote_is_not_applicable(self) -> None:
        ev = CitationVerifier().verify(_f(2, None), _t(self.SRC))
        assert ev.verdict is Verdict.NOT_APPLICABLE

    def test_unknown_file_is_refuted(self) -> None:
        ev = CitationVerifier().verify(_f(2, "x", path="ghost.py"), _t(self.SRC))
        assert ev.verdict is Verdict.REFUTES

    def test_window_is_a_knob(self) -> None:
        a = CitationVerifier(line_window=0).config_signature()
        b = CitationVerifier(line_window=5).config_signature()
        assert a != b


class TestGuard:
    def test_early_exit_guard_is_found(self) -> None:
        src = "def f(xs):\n    if not xs:\n        return 0\n    return xs[0]\n"
        ev = GuardVerifier().verify(_f(4, "return xs[0]"), _t(src))
        assert ev.verdict is Verdict.REFUTES
        assert "early-exit-if" in ev.detail

    def test_enclosing_with_is_found(self) -> None:
        src = "def f(p):\n    with open(p) as h:\n        h.write('x')\n"
        ev = GuardVerifier().verify(_f(3, "h.write('x')"), _t(src))
        assert ev.verdict is Verdict.REFUTES

    def test_callee_guard_is_found(self) -> None:
        """🔴 decoy 분류 4종이 이 형태다 - 가드가 호출한 함수 안에 있다."""
        src = (
            "def _check(key):\n"
            "    if key is None:\n"
            "        raise ValueError(key)\n"
            "    return key\n"
            "\n"
            "def use(key):\n"
            "    return _check(key).upper()\n"
        )
        ev = GuardVerifier().verify(_f(7, "_check(key).upper()"), _t(src))
        assert ev.verdict is Verdict.REFUTES
        assert "callee-guard" in ev.detail

    def test_callee_guard_requires_checking_its_own_parameter(self) -> None:
        """아무 if/raise 나 가드로 세면 REFUTES 가 남발된다."""
        src = (
            "FLAG = False\n"
            "def helper(key):\n"
            "    if FLAG:\n"
            "        raise RuntimeError\n"
            "    return key\n"
            "\n"
            "def use(key):\n"
            "    return helper(key)\n"
        )
        ev = GuardVerifier().verify(_f(8, "helper(key)"), _t(src))
        assert ev.verdict is Verdict.INCONCLUSIVE

    def test_unrelated_guard_is_filtered_by_name_overlap(self) -> None:
        src = "def f(a, b):\n    if not a:\n        return 0\n    return b[0]\n"
        ev = GuardVerifier(require_name_overlap=True).verify(
            _f(4, "return b[0]"), _t(src)
        )
        assert ev.verdict is Verdict.INCONCLUSIVE

    def test_no_guard_is_inconclusive_never_refutes_absence(self) -> None:
        """🔴 이 레이어의 핵심 규약."""
        src = "def f(xs):\n    return xs[0]\n"
        ev = GuardVerifier().verify(_f(2, "return xs[0]"), _t(src))
        assert ev.verdict is Verdict.INCONCLUSIVE
        assert "없다는 뜻이 아니라" in ev.detail

    def test_syntax_error_degrades_quietly(self) -> None:
        ev = GuardVerifier().verify(_f(1, "x"), _t("def broken(\n"))
        assert ev.verdict is Verdict.INCONCLUSIVE


class TestCorroboration:
    def test_agreement_supports(self) -> None:
        ref = [_f(10, source="ruff")]
        ev = CorroborationVerifier(ref).verify(_f(10, source="claude"), _t("x = 1\n"))
        assert ev.verdict is Verdict.SUPPORTS

    def test_slack_widens_agreement(self) -> None:
        ref = [_f(12, source="ruff")]
        tight = CorroborationVerifier(ref, line_slack=0)
        loose = CorroborationVerifier(ref, line_slack=5)
        f = _f(10, source="claude")
        assert tight.verify(f, _t("x = 1\n")).verdict is Verdict.INCONCLUSIVE
        assert loose.verify(f, _t("x = 1\n")).verdict is Verdict.SUPPORTS

    def test_disagreement_is_inconclusive_not_refutation(self) -> None:
        """🔴 확인자가 그 층을 아예 안 볼 수도 있다."""
        ev = CorroborationVerifier([_f(99, source="ruff")]).verify(
            _f(10, source="claude"), _t("x = 1\n")
        )
        assert ev.verdict is Verdict.INCONCLUSIVE

    def test_self_corroboration_is_refused(self) -> None:
        v = CorroborationVerifier([_f(10, source="ruff")])
        with pytest.raises(SelfCorroborationError, match="항등식"):
            v.verify(_f(10, source="ruff"), _t("x = 1\n"))

    def test_verifier_does_not_run_tools(self) -> None:
        """🔴 verify/ 는 analysis/ 를 모른다 - 증거를 받기만 한다."""
        src = Path("src/codeproof_ai/verify/corroboration.py").read_text(
            encoding="utf-8"
        )
        assert "codeproof_ai.analysis" not in src


class TestReachability:
    def test_public_name_is_reachable(self) -> None:
        src = "def pub():\n    return 1\n"
        ev = ReachabilityVerifier().verify(_f(2, symbol="pub"), _t(src))
        assert ev.verdict is Verdict.SUPPORTS

    def test_referenced_private_is_reachable(self) -> None:
        src = "def _helper():\n    return 1\n\ndef main():\n    return _helper()\n"
        ev = ReachabilityVerifier().verify(_f(2, symbol="_helper"), _t(src))
        assert ev.verdict is Verdict.SUPPORTS

    def test_unreferenced_private_is_refuted(self) -> None:
        src = "def _dead():\n    return 1\n\ndef main():\n    return 2\n"
        ev = ReachabilityVerifier().verify(_f(2, symbol="_dead"), _t(src))
        assert ev.verdict is Verdict.REFUTES
        assert "동적 호출은 보지 못한다" in ev.detail

    def test_module_level_is_not_applicable(self) -> None:
        ev = ReachabilityVerifier().verify(_f(1, symbol=None), _t("x = 1\n"))
        assert ev.verdict is Verdict.NOT_APPLICABLE


class TestConfidence:
    def _ev(self, kind: EvidenceKind, verdict: Verdict) -> Evidence:
        return Evidence(kind=kind, verdict=verdict, detail="")

    def test_fabricated_citation_is_a_hard_zero(self) -> None:
        """🔴 가중합이 아니다 - 존재하지 않는 코드면 다른 근거가 무의미하다."""
        score = aggregate(
            [
                self._ev(EvidenceKind.CITATION, Verdict.REFUTES),
                self._ev(EvidenceKind.CORROBORATION, Verdict.SUPPORTS),
                self._ev(EvidenceKind.REACHABILITY, Verdict.SUPPORTS),
            ]
        )
        assert score == 0.0

    def test_inconclusive_does_not_move_the_score(self) -> None:
        """「확인 못 함」이 점수를 깎으면 그건 반박으로 세는 것이다."""
        base = aggregate([])
        with_unknowns = aggregate(
            [
                self._ev(EvidenceKind.GUARD, Verdict.INCONCLUSIVE),
                self._ev(EvidenceKind.CORROBORATION, Verdict.INCONCLUSIVE),
            ]
        )
        assert base == with_unknowns

    def test_guard_lowers_confidence(self) -> None:
        assert aggregate([self._ev(EvidenceKind.GUARD, Verdict.REFUTES)]) < aggregate([])

    def test_score_stays_in_range(self) -> None:
        many = [self._ev(EvidenceKind.GUARD, Verdict.REFUTES)] * 20
        assert aggregate(many) == 0.0
        lots = [self._ev(EvidenceKind.CORROBORATION, Verdict.SUPPORTS)] * 20
        assert aggregate(lots) == 1.0

    def test_weights_are_recorded(self) -> None:
        a = VerificationPipeline([], Weights()).config_signature()
        b = VerificationPipeline([], Weights(guard=0.9)).config_signature()
        assert a != b, "가중치가 지문에 안 실리면 재현 불가다"

    def test_verifier_failure_does_not_lose_the_finding(self) -> None:
        class Exploding:
            kind = EvidenceKind.GUARD.value

            def config_signature(self) -> str:
                return "boom"

            def verify(
                self,
                finding: Finding,  # noqa: ARG002
                target: ReviewTarget,  # noqa: ARG002
            ) -> Evidence:
                msg = "의도된 실패"
                raise RuntimeError(msg)

        vf = VerificationPipeline([Exploding()]).run(_f(1, "x"), _t("x = 1\n"))
        assert len(vf.evidence) == 1
        assert vf.evidence[0].verdict is Verdict.INCONCLUSIVE
        assert "검증자가 실패했다" in vf.evidence[0].detail


class TestAgainstShippedCorpus:
    """🔴 실측 회귀 - 숫자가 바뀌면 확인하고 갱신한다."""

    def _pipeline(self, target: ReviewTarget) -> VerificationPipeline:
        return VerificationPipeline(
            [
                CitationVerifier(),
                GuardVerifier(),
                CorroborationVerifier(reference=MypyAnalyzer().analyze(target)),
                ReachabilityVerifier(),
            ]
        )

    def test_callee_guard_discriminates_d010(self) -> None:
        """안전한 쪽 점수가 취약한 쪽보다 낮아야 한다."""
        by_id = {s.sample_id: s for s in load_decoy_samples(DECOYS)}
        ruff = RuffAnalyzer()
        scores: dict[str, float] = {}

        for sid in ("D010-idempotent-retry", "D010-idempotent-retry#twin"):
            s = by_id[sid]
            findings = ruff.analyze(s.target)
            assert findings, f"{sid} 에 지적이 없다 - 픽스처가 바뀌었다"
            vf = self._pipeline(s.target).run(findings[0], s.target)
            scores[sid] = vf.confidence

        assert scores["D010-idempotent-retry"] < scores["D010-idempotent-retry#twin"], (
            f"안전한 쪽({scores['D010-idempotent-retry']:.2f})이 "
            f"취약한 쪽({scores['D010-idempotent-retry#twin']:.2f})보다 낮아야 한다"
        )

    def test_taint_gap_is_documented_not_hidden(self) -> None:
        """🔴 D002 는 구별하지 못한다. 그 한계가 문서에 적혀 있어야 한다."""
        by_id = {s.sample_id: s for s in load_decoy_samples(DECOYS)}
        ruff = RuffAnalyzer()
        scores = []
        for sid in ("D002-shell-true-constant-command", "D002-shell-true-constant-command#twin"):
            s = by_id[sid]
            f = ruff.analyze(s.target)[0]
            scores.append(self._pipeline(s.target).run(f, s.target).confidence)

        assert scores[0] == scores[1], "구별하게 됐다면 아래 문서 단언을 갱신한다"
        doc = Path("src/codeproof_ai/verify/guard.py").read_text(encoding="utf-8")
        assert "taint analysis" in doc, "못 보는 것을 문서에 적지 않으면 과신으로 읽힌다"


class TestGuardStaysInScope:
    """🔴 다른 함수의 이른 반환은 그 줄이 돌 때 실행되지 않는다 - 반박의 근거가 아니다.

    [실측] 모듈 전체를 훑던 때 실코드 8개의 가드 반박 580건 중 395건이 다른 함수의 가드였다.
    """

    SRC = (
        "import subprocess\n\n\n"
        "def validate(cmd):\n    if not cmd.isalnum():\n        raise ValueError(cmd)\n\n\n"
        "def run(cmd):\n    subprocess.run(cmd, shell=True)\n\n\n"
        "def guarded(cmd):\n    if not cmd.isalnum():\n        raise ValueError(cmd)\n"
        "    subprocess.run(cmd, shell=True)\n"
    )

    def test_a_guard_in_another_function_does_not_refute(self) -> None:
        ev = GuardVerifier().verify(_f(10), _t(self.SRC))
        assert ev.verdict is Verdict.INCONCLUSIVE, ev.detail

    def test_a_guard_in_the_same_function_still_refutes(self) -> None:
        ev = GuardVerifier().verify(_f(16), _t(self.SRC))
        assert ev.verdict is Verdict.REFUTES
        assert "@L14" in ev.detail and "@L5" not in ev.detail

    def test_a_guard_in_a_called_function_still_counts(self) -> None:
        """callee-guard 는 그대로다 - 부른 함수가 인자를 검사하면 방어다."""
        call = "    subprocess.run(cmd, shell=True)\n\n\n"
        src = self.SRC.replace(call, "    validate(cmd)\n\n\n", 1)
        ev = GuardVerifier().verify(_f(10), _t(src))
        assert ev.verdict is Verdict.REFUTES
        assert "callee-guard" in ev.detail


class TestMultiLineCitation:
    """🔴 정확히 그 자리에 있는 여러 줄 인용을 「위치 오류」로 찍지 않는다.

    [실측] 측정 묶음의 에이전트 지적 claude 339/479 · codex 172/341 이 여러 줄 인용이었다.
    """

    SRC = "import os\n\n\ndef f(x):\n    if x:\n        return os.system(x)\n    return 0\n"

    def test_a_multi_line_quote_at_its_lines_is_supported(self) -> None:
        quote = "    if x:\n        return os.system(x)"
        ev = CitationVerifier().verify(_f(5, quote), _t(self.SRC))
        assert ev.verdict is Verdict.SUPPORTS, ev.detail

    def test_a_multi_line_quote_far_away_is_still_a_location_error(self) -> None:
        quote = "def f(x):\n    if x:"
        level = CitationVerifier(line_window=0).match_level(_f(7, quote), _t(self.SRC))
        assert level is MatchLevel.ELSEWHERE_IN_FILE

    def test_a_multi_line_quote_that_does_not_exist_is_refuted(self) -> None:
        ev = CitationVerifier().verify(_f(5, "    if y:\n        rm(y)"), _t(self.SRC))
        assert ev.verdict is Verdict.REFUTES


class TestCorroborationNamesWhoAgreed:
    """🔴 「도 지적했다」에는 그 자리를 실제로 짚은 출처만 - 확인자 전부가 아니다."""

    def test_only_the_agreeing_source_is_named(self) -> None:
        ref = [_f(5, source="ruff"), _f(30, source="mypy")]
        ev = CorroborationVerifier(reference=ref).verify(_f(5), _t("x\n" * 40))
        assert ev.verdict is Verdict.SUPPORTS
        assert ev.detail.startswith("ruff 도 m.py:5 ")

    def test_the_nearest_line_is_cited_every_time(self) -> None:
        """집합 순서로 고르면 실행마다 다른 줄이 찍혔다 [실측: PYTHONHASHSEED] - 시드를 바꿔도 같다.

        한 프로세스에서 한 번 보면 옛 코드도 운으로 통과한다 [실측] - 시드마다 새 프로세스로 본다.
        """
        code = (
            "from tests.verify.test_verifiers import _f, _t\n"
            "from codeproof_ai.verify.corroboration import CorroborationVerifier\n"
            "ref = [_f(7, source='ruff'), _f(5, source='ruff'), _f(6, source='ruff')]\n"
            "print(CorroborationVerifier(reference=ref).verify(_f(5), _t('x\\n' * 10)).locator)\n"
        )
        seen = {
            subprocess.run(
                [sys.executable, "-c", code], capture_output=True, text=True, check=True,
                env=os.environ | {"PYTHONHASHSEED": str(seed)}, cwd=REPO,
            ).stdout.strip()
            for seed in range(8)
        }
        assert seen == {"m.py:5"}

    def test_a_reference_span_is_matched_by_its_range(self) -> None:
        """🔴 참조도 범위로 맞춘다 - claude L4-8 ↔ ruff L8 은 어느 방향이든 같은 자리다 (A2a)."""
        wide = Finding(
            source="claude", rule_id="x", message="m",
            location=Location(path="m.py", span=Span(Position(4, 0), Position(8, 0))),
            category=Category.SECURITY, severity=Severity.WARNING,
        )
        ruff_at_8 = _f(8, source="ruff")
        one_way = CorroborationVerifier(reference=[ruff_at_8]).verify(wide, _t("x\n" * 20))
        other_way = CorroborationVerifier(reference=[wide]).verify(ruff_at_8, _t("x\n" * 20))
        assert one_way.verdict is other_way.verdict is Verdict.SUPPORTS
