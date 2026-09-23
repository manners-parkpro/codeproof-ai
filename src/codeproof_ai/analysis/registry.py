"""분석기 registry.

🔴 `cli` 가 구현 클래스를 직접 고르지 않게 한다. 새 분석기를 넣을 때
   `cli.py` 의 if/elif 를 찾아 고치는 일이 없어야 한다.

⚠ registry 가 맞는 자리와 아닌 자리를 구분한다. 여기는 **이름 -> 클래스**가
  균일해서 맞다. 채점자는 `StaticCorroborationGrader` 만 `reference` 를 받으므로
  균일한 팩토리가 어색하다 - 거기는 registry 를 두지 않고 CLI 가 정책으로 조립한다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from codeproof_ai.analysis.python.mypy_ import MypyAnalyzer
from codeproof_ai.analysis.python.ruff import RuffAnalyzer

if TYPE_CHECKING:
    from collections.abc import Callable

    from codeproof_ai.analysis.base import Analyzer

ANALYZERS: dict[str, Callable[..., Analyzer]] = {
    "ruff": RuffAnalyzer,
    "mypy": MypyAnalyzer,
}


class UnknownAnalyzerError(ValueError):
    """등록되지 않은 분석기."""


def create_analyzer(name: str, **kwargs: Any) -> Analyzer:
    factory = ANALYZERS.get(name)
    if factory is None:
        msg = f"모르는 분석기: {name} ({' | '.join(sorted(ANALYZERS))})"
        raise UnknownAnalyzerError(msg)
    return factory(**kwargs)


def available() -> tuple[str, ...]:
    return tuple(sorted(ANALYZERS))
