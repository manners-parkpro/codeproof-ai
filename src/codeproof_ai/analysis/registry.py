"""분석기 registry.

🔴 `cli` 가 구현 클래스를 직접 고르지 않게 한다. 새 분석기를 넣을 때
   `cli.py` 의 if/elif 를 찾아 고치는 일이 없어야 한다.

⚠ registry 가 맞는 자리와 아닌 자리를 구분한다. 여기는 **이름 -> 클래스**가
  균일해서 맞다. 채점자는 `StaticCorroborationGrader` 만 `reference` 를 받으므로
  균일한 팩토리가 어색하다 - 거기는 registry 를 두지 않고 CLI 가 정책으로 조립한다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from codeproof_ai.analysis.python.ast_index import PythonSymbolIndex
from codeproof_ai.analysis.python.mypy_ import MypyAnalyzer
from codeproof_ai.analysis.python.ruff import RuffAnalyzer

if TYPE_CHECKING:
    from collections.abc import Callable

    from codeproof_ai.analysis.base import Analyzer, SymbolIndex

ANALYZERS: dict[str, Callable[..., Analyzer]] = {
    "ruff": RuffAnalyzer,
    "mypy": MypyAnalyzer,
}

# 확장자 -> 심볼 인덱스. 🔴 러너가 파이썬을 몰라도 되게 한다 - Java 를 넣을 때
# 여기 한 줄이면 모델·에이전트 지적도 둘러싼 심볼을 얻는다 (A3).
SYMBOL_INDEXES: dict[str, SymbolIndex] = {
    ".py": PythonSymbolIndex(),
}


def symbol_index_for(path: str) -> SymbolIndex | None:
    """경로의 언어에 맞는 심볼 인덱스. 모르는 언어면 None - 심볼 없이 둔다."""
    dot = path.rfind(".")
    return SYMBOL_INDEXES.get(path[dot:]) if dot >= 0 else None


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
