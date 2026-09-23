"""확장점 registry.

🔴 registry 의 가치는 「등록을 잊으면 알려준다」는 데 있다.
   등록 안 한 구현이 조용히 무시되면 registry 가 없는 것과 같다.

⚠ 모든 확장점에 registry 를 두지는 않는다. `StaticCorroborationGrader` 만
  `reference` 를 받으므로 채점자는 균일한 팩토리가 어색하다 - 거기는
  CLI 가 정책으로 조립하고, 그 사실을 문서가 정확히 말해야 한다.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from codeproof_ai.analysis.base import Analyzer
from codeproof_ai.analysis.registry import (
    ANALYZERS,
    UnknownAnalyzerError,
    create_analyzer,
)
from codeproof_ai.eval.grading.corroboration import StaticCorroborationGrader
from codeproof_ai.eval.grading.injected import InjectedDefectGrader
from codeproof_ai.eval.grading.safety import ProvableSafetyGrader
from codeproof_ai.llm.base import ReviewProvider
from codeproof_ai.llm.registry import (
    CREDENTIAL_OF,
    PROVIDERS,
    UnknownProviderError,
    create_provider,
)
from codeproof_ai.reviewers.formats import FORMATS

SRC = Path(__file__).resolve().parents[2] / "src" / "codeproof_ai"


def _is_protocol(node: ast.ClassDef) -> bool:
    """Protocol 선언인가 - 구현체로 세면 안 된다."""
    return any(
        (isinstance(b, ast.Name) and b.id == "Protocol")
        or (isinstance(b, ast.Attribute) and b.attr == "Protocol")
        for b in node.bases
    )


def _classes_in(directory: Path, suffix: str) -> set[str]:
    """그 디렉터리에서 접미사로 끝나는 최상위 **구현** 클래스 이름.

    Protocol 선언은 제외한다 - 등록 대상이 아니다.
    """
    found: set[str] = set()
    for path in directory.rglob("*.py"):
        if path.name.startswith("_") and path.name != "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found |= {
            n.name
            for n in tree.body
            if isinstance(n, ast.ClassDef)
            and n.name.endswith(suffix)
            and not _is_protocol(n)
        }
    return found


class TestEveryImplementationIsRegistered:
    """🔴 등록을 잊으면 여기서 걸린다."""

    def test_the_protocol_filter_works(self) -> None:
        """🔴 Protocol 을 구현체로 세면 이 테스트 전체가 무의미해진다."""
        assert "Analyzer" not in _classes_in(SRC / "analysis", "Analyzer")
        assert "ReviewProvider" not in _classes_in(SRC / "llm", "Provider")
        assert _classes_in(SRC / "analysis", "Analyzer"), "구현체를 하나도 못 찾는다"

    def test_all_analyzers_registered(self) -> None:
        defined = _classes_in(SRC / "analysis", "Analyzer")
        registered = {f.__name__ for f in ANALYZERS.values()}
        missing = defined - registered
        assert not missing, (
            f"registry 에 없는 분석기: {sorted(missing)}. "
            "analysis/registry.py 의 ANALYZERS 에 추가한다."
        )

    def test_all_providers_registered(self) -> None:
        defined = _classes_in(SRC / "llm", "Provider")
        registered = {f.__name__ for f in PROVIDERS.values()}
        missing = defined - registered
        assert not missing, (
            f"registry 에 없는 provider: {sorted(missing)}. "
            "llm/registry.py 의 PROVIDERS 에 추가한다."
        )

    def test_all_formats_registered(self) -> None:
        defined = _classes_in(SRC / "reviewers", "Format")
        registered = {type(f).__name__ for f in FORMATS.values()}
        assert not defined - registered, (
            f"registry 에 없는 포맷: {sorted(defined - registered)}"
        )

    def test_every_provider_declares_credential_need(self) -> None:
        """🔴 자격증명 대상을 빠뜨리면 `eval` 이 조용히 통과시킨다."""
        undeclared = set(PROVIDERS) - set(CREDENTIAL_OF)
        assert not undeclared, (
            f"CREDENTIAL_OF 에 없는 provider: {sorted(undeclared)}"
        )


class TestRegistryProducesUsableObjects:
    def test_created_analyzers_satisfy_the_protocol(self) -> None:
        for name in ANALYZERS:
            assert isinstance(create_analyzer(name), Analyzer), name

    def test_created_providers_satisfy_the_protocol(self) -> None:
        for name in PROVIDERS:
            assert isinstance(create_provider(name), ReviewProvider), name

    def test_kwargs_reach_the_constructor(self) -> None:
        a = create_analyzer("ruff", select=("F", "E"))
        assert "F+E" in a.config_signature()

    def test_unknown_names_raise_with_a_useful_message(self) -> None:
        with pytest.raises(UnknownAnalyzerError, match="ruff"):
            create_analyzer("nope")
        with pytest.raises(UnknownProviderError, match="claude"):
            create_provider("nope")


class TestCliDoesNotBypassTheRegistry:
    """🔴 CLAUDE.md A3 이 「registry 를 거친다」고 말한다 - 실제로 그런지 본다.

    [실측] 이 테스트를 쓰기 전에는 cli.py 가 8곳에서 구현체를 직접 생성했고,
    문서만 registry 를 주장하고 있었다.
    """

    DIRECT_CONSTRUCTION = (
        "RuffAnalyzer(",
        "MypyAnalyzer(",
        "AnthropicReviewProvider(",
        "OpenAIReviewProvider(",
        "ReplayProvider(",
    )

    def test_cli_constructs_nothing_directly(self) -> None:
        text = (SRC / "cli.py").read_text(encoding="utf-8")
        leaked = [c for c in self.DIRECT_CONSTRUCTION if c in text]
        assert not leaked, (
            f"cli.py 가 구현체를 직접 생성한다: {leaked}. "
            "registry 의 create_* 를 쓴다."
        )

    def test_cli_imports_no_implementation_modules(self) -> None:
        tree = ast.parse((SRC / "cli.py").read_text(encoding="utf-8"))
        banned = {"codeproof_ai.analysis.python", "codeproof_ai.llm.anthropic_",
                  "codeproof_ai.llm.openai_", "codeproof_ai.llm.replay"}
        leaked = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module
            and any(node.module.startswith(b) for b in banned)
        }
        assert not leaked, f"cli.py 가 구현 모듈을 import 한다: {sorted(leaked)}"


class TestGraderHasNoRegistryOnPurpose:
    """⚠ 모든 확장점에 registry 를 두지 않는 것이 **의도**임을 고정한다.

    채점자는 생성 인자가 균일하지 않다 (`StaticCorroborationGrader` 만
    `reference` 를 받는다). 균일한 팩토리를 억지로 만들면 그 비균일성이
    kwargs 딕셔너리로 숨는다 - 그게 더 나쁘다.
    """

    def test_corroboration_grader_needs_context_others_do_not(self) -> None:
        required = {
            g.__name__: [
                p.name
                for p in inspect.signature(g).parameters.values()
                if p.default is inspect.Parameter.empty
            ]
            for g in (ProvableSafetyGrader, InjectedDefectGrader, StaticCorroborationGrader)
        }
        assert required["StaticCorroborationGrader"] == ["reference"]
        assert required["ProvableSafetyGrader"] == []
        assert required["InjectedDefectGrader"] == []

    def test_docs_do_not_claim_a_grader_registry(self) -> None:
        text = (SRC.parents[1] / "CLAUDE.md").read_text(encoding="utf-8")
        line = next(
            (ln for ln in text.splitlines() if "Grader" in ln and "registry" in ln),
            None,
        )
        assert line is None, (
            f"문서가 채점자 registry 를 주장한다: {line!r} - 실물이 없다"
        )
