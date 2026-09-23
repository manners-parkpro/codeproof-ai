"""모델 provider registry.

🔴 `cli` 의 `if name == "claude"` 분기를 없앤다.
   새 provider 는 여기 한 줄 추가로 끝나야 한다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from codeproof_ai.llm.anthropic_ import AnthropicReviewProvider
from codeproof_ai.llm.openai_ import OpenAIReviewProvider
from codeproof_ai.llm.replay import ReplayProvider

if TYPE_CHECKING:
    from collections.abc import Callable

    from codeproof_ai.llm.base import ReviewProvider

PROVIDERS: dict[str, Callable[..., ReviewProvider]] = {
    "claude": AnthropicReviewProvider,
    "codex": OpenAIReviewProvider,
    # 🔴 배관 검증 전용. 이 숫자를 결과로 보고하지 않는다.
    "replay": ReplayProvider,
}

# provider 이름 -> 자격증명 확인 대상. replay 는 자격증명이 없다.
CREDENTIAL_OF: dict[str, str | None] = {
    "claude": "anthropic",
    "codex": "openai",
    "replay": None,
}


class UnknownProviderError(ValueError):
    """등록되지 않은 provider."""


def create_provider(name: str, **kwargs: Any) -> ReviewProvider:
    factory = PROVIDERS.get(name)
    if factory is None:
        msg = f"모르는 provider: {name} ({' | '.join(sorted(PROVIDERS))})"
        raise UnknownProviderError(msg)
    return factory(**kwargs)


def available() -> tuple[str, ...]:
    return tuple(sorted(PROVIDERS))
