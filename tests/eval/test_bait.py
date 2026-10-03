"""decoy 품질 측정.

🔴 이 모듈의 존재 이유: 지적이 없으면 채점할 것도 없다.
   물리지 않는 decoy 를 세어 150 을 채우면 숫자만 는다.

⚠ 그리고 **「안 물림 = 나쁨」이 아니다.** 정적분석기만으로는
  「미시험」과 「미끼가 약함」을 구별할 수 없고, 도구가 그렇게 말해야 한다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from codeproof_ai.eval.sample import LabeledSample
    from tests.conftest import AnalyzedCorpus

from pathlib import Path

from codeproof_ai.eval.bait import BaitStatus, CorpusStats, measure

DECOYS = Path(__file__).resolve().parents[2] / "corpus" / "decoys"


def _stats(
    analyzed: AnalyzedCorpus,
    shipped_samples: list[LabeledSample],
    select: tuple[str, ...] = ("ALL",),
) -> CorpusStats:
    """미끼 적중 통계.

    분석은 `analyzed` 픽스처가 세션당 한 번만 한다 - 예전에는 이 함수에
    `@cache` 를 달았는데, 그건 **프로덕션에도 있는 비용을 숨기는** 쪽이었다.
    지금은 분석기를 한 번만 돌리고 결과를 공유한다.
    """
    return measure(
        shipped_samples,
        {"ruff": analyzed("ruff", select), "mypy": analyzed("mypy")},
    )


class TestStatusIsThreeWay:
    def test_exercised_when_bait_is_hit(
        self, analyzed: AnalyzedCorpus, shipped_samples: list[LabeledSample]
    ) -> None:
        cs = _stats(analyzed, shipped_samples)
        hit = cs.by_status(BaitStatus.EXERCISED)
        assert hit, "코퍼스 전체가 미시험이면 측정할 것이 없다"
        for st in hit:
            assert st.bait_hits > 0
            assert st.biting_reviewers

    def test_untested_means_no_finding_at_all(
        self, analyzed: AnalyzedCorpus, shipped_samples: list[LabeledSample]
    ) -> None:
        for st in _stats(analyzed, shipped_samples).by_status(BaitStatus.UNTESTED):
            assert st.any_finding == 0

    def test_out_of_scope_means_findings_but_none_in_bait(
        self, analyzed: AnalyzedCorpus, shipped_samples: list[LabeledSample]
    ) -> None:
        for st in _stats(analyzed, shipped_samples).by_status(BaitStatus.OUT_OF_SCOPE):
            assert st.any_finding > 0
            assert st.bait_hits == 0


class TestBaitDependsOnReviewerConfig:
    """🔴 같은 코퍼스인데 룰 선택만 바꿔도 물리는 비율이 달라진다 - 논지의 또 다른 사례."""

    def test_narrow_selection_bites_less(
        self, analyzed: AnalyzedCorpus, shipped_samples: list[LabeledSample]
    ) -> None:
        wide = _stats(analyzed, shipped_samples, ("ALL",)).exercised_rate
        narrow = _stats(analyzed, shipped_samples, ("F",)).exercised_rate
        assert wide is not None and narrow is not None
        assert wide > narrow, (
            "룰 선택이 미끼 효과를 바꾸지 않는다면 decoy 품질을 "
            "단일 설정으로 판정해도 된다는 뜻인데, 그건 사실이 아니다"
        )


class TestTrapCoverage:
    def test_every_trap_kind_is_represented(
        self, analyzed: AnalyzedCorpus, shipped_samples: list[LabeledSample]
    ) -> None:
        cov = _stats(analyzed, shipped_samples).coverage_by_trap()
        assert "?" not in cov, "짝에서 trap 분류를 못 가져온 decoy 가 있다"
        assert len(cov) >= 8, f"분류 다양성이 부족하다: {sorted(cov)}"

    def test_type_narrowed_is_invisible_to_static_analysers(
        self, analyzed: AnalyzedCorpus, shipped_samples: list[LabeledSample]
    ) -> None:
        """🔴 구조적 사실이지 decoy 결함이 아니다 - 다만 **무엇으로 좁혔느냐**가 가른다.

        Ruff 에는 타입 좁힘을 보는 룰이 없다. mypy 는 제어흐름으로 좁힌 것(isinstance ·
        빈값 검사 · 대입식 · TypeGuard · 센티널)은 **정당하다고 인정**해 침묵하지만,
        생성자가 세운 불변식으로 좁힌 것은 보지 못하고 선언 타입대로 연산자 오류를 낸다.
        [실측 · 74쌍] D072 가 그 첫 사례이고, 그 지적은 증명된 음성 위의 거짓 경보다.

        🔴 물린 쌍을 고쳐 이 단언을 지키지 않는다 - 물림을 보고 쌍을 바꾸지 않는다
           (DESIGN §3.5). 물린 쌍이 바뀌면 그 지적을 열어 보고 이 테스트와 문서를 갱신한다.
        """
        stats = [
            s for s in _stats(analyzed, shipped_samples).stats
            if s.trap_kind == "type_narrowed"
        ]
        assert stats, "type_narrowed decoy 가 사라졌다"
        biting = {s.sample_id: s.biting_reviewers for s in stats if s.biting_reviewers}
        assert biting == {"D072-constructor-rejects-the-missing-value": ("mypy",)}, (
            f"type_narrowed 를 무는 쌍 · 리뷰어가 바뀌었다: {biting} - "
            "리뷰어가 추가됐거나 새 쌍이 다른 좁힘을 쓴다면 이 테스트와 문서를 갱신한다"
        )


class TestNegativesOnly:
    def test_twins_are_not_counted(
        self, analyzed: AnalyzedCorpus, shipped_samples: list[LabeledSample]
    ) -> None:
        """미끼 효과는 **음성**에서만 의미가 있다 - twin 은 진짜 결함이다."""
        cs = _stats(analyzed, shipped_samples)
        assert all(not s.sample_id.endswith("#twin") for s in cs.stats)
        assert len(cs.stats) == len(shipped_samples) // 2
