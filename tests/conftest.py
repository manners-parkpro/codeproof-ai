"""테스트 공용 픽스처 - 코퍼스 분석을 세션당 한 번만 한다.

🔴 이 캐시가 왜 옳은가 (이전에 캐시를 되돌린 적이 있으므로 남긴다).

전에 `@cache` 로 느린 테스트를 덮었다가 걷어냈다. 그때 캐시는 **프로덕션에도
있는 비용을 숨기고** 있었고, 진짜 원인이 셋 따로 있었다 - uv run 경유 실행,
대상마다 subprocess, 채점자가 분석기를 직접 실행. 그걸 고쳐 99s -> 26s 가 됐다.

여기는 성격이 다르다. 프로덕션은 **한 번 돌리고 여러 채점자로 채점**한다 -
`run_reviewer(reviewer, samples, graders)` 의 서명이 그 모양이다. 테스트만
30여 곳에서 각자 코퍼스를 다시 분석하고 있었다. 그건 프로덕션에 없는 비용이므로
숨기는 게 아니라 **없애는** 것이다.

재사용이 안전한 근거: 정적분석기는 결정적이고(`ReviewerKind.is_deterministic`),
배치와 개별 실행이 같은 결과를 낸다는 것을 `tests/analysis/test_batch.py` 가 강제한다.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from codeproof_ai.analysis.registry import create_analyzer
from codeproof_ai.domain.reviewer import ReviewerKind, ReviewResult
from codeproof_ai.eval.loader import load_decoy_samples

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from codeproof_ai.domain.finding import Finding
    from codeproof_ai.domain.target import ReviewTarget
    from codeproof_ai.eval.sample import LabeledSample

DECOYS = Path(__file__).resolve().parents[1] / "corpus" / "decoys"


class CachedReviewer:
    """미리 계산된 지적을 돌려주는 리뷰어.

    `Reviewer` Protocol 을 만족하므로 `run_reviewer` 가 그대로 받는다 -
    테스트 전용 우회 경로를 만들지 않는다. 캐시에 없는 대상은 **빈 결과가
    아니라 KeyError** 로 터진다: 조용히 0건을 돌려주면 테스트가 거짓으로 통과한다.
    """

    kind = ReviewerKind.STATIC

    def __init__(
        self,
        name: str,
        identity: str,
        signature: str,
        findings: Mapping[str, Sequence[Finding]],
    ) -> None:
        self.name = name
        self.identity = identity
        self._signature = signature
        self._findings = findings

    def config_signature(self) -> str:
        """🔴 실제 분석기의 지문을 그대로 보고한다.

        "cached(...)" 를 돌려주면 매니페스트가 달라져 테스트가 프로덕션과
        다른 것을 검사하게 된다. 지적은 **정말로** 이 설정에서 나온 것이므로
        같은 지문을 보고하는 것이 정확하다 - 다른 건 계산 시점뿐이다.
        """
        return self._signature

    @property
    def findings(self) -> Mapping[str, Sequence[Finding]]:
        return self._findings

    def review(self, target: ReviewTarget) -> ReviewResult:
        return ReviewResult(findings=tuple(self._findings[target.target_id]))

    def review_many(
        self, targets: Sequence[ReviewTarget]
    ) -> dict[str, ReviewResult]:
        return {t.target_id: self.review(t) for t in targets}


class AnalyzedCorpus:
    """(분석기, 설정) 조합마다 코퍼스를 한 번만 분석해 두는 캐시."""

    def __init__(self, samples: Sequence[LabeledSample]) -> None:
        self._samples = samples
        self._cache: dict[tuple[str, tuple[str, ...]], CachedReviewer] = {}

    def findings(
        self, name: str, select: Sequence[str] | None = None
    ) -> Mapping[str, Sequence[Finding]]:
        """확인자(reference)로 넘길 지적. `StaticCorroborationGrader` 가 받는 모양이다."""
        return self(name, select).findings

    def __call__(
        self, name: str, select: Sequence[str] | None = None
    ) -> CachedReviewer:
        key = (name, tuple(select or ()))
        if key not in self._cache:
            analyzer = create_analyzer(name, **({"select": tuple(select)} if select else {}))
            findings = analyzer.analyze_many([s.target for s in self._samples])
            self._cache[key] = CachedReviewer(
                name=name,
                identity=f"{name}/{analyzer.version().version}",
                signature=analyzer.config_signature(),
                findings=findings,
            )
        return self._cache[key]


@pytest.fixture(scope="session")
def shipped_samples() -> list[LabeledSample]:
    """저장소의 decoy 코퍼스. 읽기 전용이라 공유해도 안전하다."""
    return load_decoy_samples(DECOYS)


@pytest.fixture(scope="session")
def analyzed(shipped_samples: list[LabeledSample]) -> AnalyzedCorpus:
    """`analyzed("ruff", select=(...))` -> 그 설정으로 코퍼스를 분석한 리뷰어."""
    return AnalyzedCorpus(shipped_samples)
