"""기존 구현을 Reviewer 로 감싼다.

🔴 다시 쓰지 않고 감싼다. Analyzer 와 ReviewProvider 는 각자 벤더 특수성을
   제대로 다루고 있고(컬럼 규약 · 토큰 보정 · 캐시 nonce), 그걸 합치면
   그 지식이 희석된다. 어댑터가 층만 얹는다.
"""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

from codeproof_ai.domain.reviewer import ReviewerKind, ReviewResult, ReviewTelemetry

if TYPE_CHECKING:
    from collections.abc import Sequence

    from codeproof_ai.analysis.base import Analyzer
    from codeproof_ai.domain.run import ToolVersion
    from codeproof_ai.domain.target import ReviewTarget
    from codeproof_ai.llm.base import ReviewProvider


class AnalyzerReviewer:
    """정적분석기를 리뷰어로."""

    kind = ReviewerKind.STATIC

    def __init__(self, analyzer: Analyzer) -> None:
        self._analyzer = analyzer
        self.name = analyzer.name
        self.identity = f"{analyzer.name}/{analyzer.version().version}"

    def config_signature(self) -> str:
        return self._analyzer.config_signature()

    def tool_versions(self) -> tuple[ToolVersion, ...]:
        """🔴 ruff 는 pre-1.0 이라 정확히 핀해야 한다 - 매니페스트에 실린다."""
        return (self._analyzer.version(),)

    def review(self, target: ReviewTarget) -> ReviewResult:
        return ReviewResult(findings=tuple(self._analyzer.analyze(target)))

    def review_many(
        self, targets: Sequence[ReviewTarget]
    ) -> dict[str, ReviewResult]:
        """🔴 한 번의 subprocess 로 전부. [실측] ruff 8.6배 · mypy 23.9배."""
        return {
            tid: ReviewResult(findings=tuple(fs))
            for tid, fs in self._analyzer.analyze_many(targets).items()
        }


class ProviderReviewer:
    """모델 API 를 리뷰어로.

    effort 와 캐시 정책은 **생성 시점에 고정**한다 - Reviewer.review() 는
    인자를 받지 않기 때문이다. 이게 오히려 낫다: 같은 리뷰어 객체가
    실행 내내 같은 설정을 쓰는 것이 보장된다.
    """

    kind = ReviewerKind.MODEL_API

    def __init__(
        self,
        provider: ReviewProvider,
        *,
        effort: str,
        cache_policy: str = "nonce",
    ) -> None:
        if not effort:
            msg = "effort 를 명시해야 한다 - 기본값이 모델마다 다르다 (D4)"
            raise ValueError(msg)
        self._provider = provider
        self._effort = effort
        self._cache_policy = cache_policy
        self.name = provider.name
        self.identity = provider.model_id

    def config_signature(self) -> str:
        sig = getattr(self._provider, "config_signature", None)
        base = sig() if callable(sig) else self._provider.name
        return f"{base},effort={self._effort},cache={self._cache_policy}"

    def manifest_fields(self) -> dict[str, str]:
        """🔴 매니페스트에 실릴 항목을 스스로 신고한다.

        러너가 짐작하면 모델 실행에 effort="n/a" 가 기록된다 - 재현이 불가능해진다.
        """
        return {"effort": self._effort, "cache_policy": self._cache_policy}

    def review(self, target: ReviewTarget) -> ReviewResult:
        # 🔴 호출마다 새 nonce - 재사용하면 캐시 무력화가 안 된다 (D3).
        nonce = secrets.token_hex(8) if self._cache_policy == "nonce" else None
        resp = self._provider.review(
            target, effort=self._effort, cache_nonce=nonce
        )
        u = resp.usage
        return ReviewResult(
            findings=resp.findings,
            telemetry=ReviewTelemetry(
                input_tokens=u.total_input,
                output_tokens=u.output,
                cache_read=u.cache_read,
                reasoning_tokens=u.reasoning,
                ttft_ms=resp.ttft_ms,
                total_ms=resp.total_ms,
                refused=bool(resp.raw.get("_refused")),
            ),
            raw=dict(resp.raw),
        )
