"""런타임 검증.

🔴 이 레이어를 관통하는 규약 하나: **못 찾은 것은 없다는 뜻이 아니다.**
   REFUTES 는 찾았을 때만 낸다. 그래서 「INCONCLUSIVE 여야 하는데 REFUTES 가
   나오는가」를 검사하는 테스트가 기능 테스트만큼 많다.
"""

from __future__ import annotations

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
