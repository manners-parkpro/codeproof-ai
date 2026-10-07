"""정적분석 어댑터 - 컬럼 규약과 공정성."""

from __future__ import annotations

import pytest

from codeproof_ai.analysis.base import materialize
from codeproof_ai.analysis.python import ruff as ruff_module
from codeproof_ai.analysis.python.ast_index import PythonSymbolIndex
from codeproof_ai.analysis.python.mypy_ import MypyAnalyzer
from codeproof_ai.analysis.python.ruff import RuffAnalyzer
from codeproof_ai.analysis.python.version import TARGET_PYTHON
from codeproof_ai.domain.target import ReviewTarget, SourceFile


def _target(content: str, path: str = "m.py") -> ReviewTarget:
    return ReviewTarget(target_id="t", files=(SourceFile(path, content),))


class TestMaterializeIsAFairnessDevice:
    """🔴 분석기는 모델이 보는 것과 똑같은 것만 봐야 한다."""

    def test_only_target_files_exist(self) -> None:
        t = ReviewTarget(
            target_id="t",
            files=(SourceFile("a.py", "x = 1\n"), SourceFile("pkg/b.py", "y = 2\n")),
        )
        with materialize(t) as root:
            assert (root / "a.py").read_text(encoding="utf-8") == "x = 1\n"
            assert (root / "pkg" / "b.py").is_file()
            assert sorted(p.name for p in root.rglob("*.py")) == ["a.py", "b.py"]

    def test_directory_is_cleaned_up(self) -> None:
        with materialize(_target("x = 1\n")) as root:
            saved = root
        assert not saved.exists()


class TestDecoratorWidening:
    """B3 - 데코레이터 줄이 함수에 속해야 한다."""

    def test_decorator_lines_map_to_the_function(self) -> None:
        src = "@deco\n@other(1)\ndef target():\n    pass\n"
        ix = PythonSymbolIndex()
        for line in (1, 2, 3):
            assert ix.enclosing_symbol(src, line) == ("target", "function")

    def test_nested_scope_is_dotted(self) -> None:
        src = "class C:\n    @property\n    def m(self):\n        return 1\n"
        assert PythonSymbolIndex().enclosing_symbol(src, 2) == ("C.m", "function")

    def test_module_level_is_none(self) -> None:
        assert PythonSymbolIndex().enclosing_symbol("x = 1\n", 1) == (None, None)

    def test_syntax_error_degrades_quietly(self) -> None:
        assert PythonSymbolIndex().enclosing_symbol("def broken(\n", 1) == (None, None)


class TestRuffAdapter:
    def test_finds_a_real_violation(self) -> None:
        findings = RuffAnalyzer(select=("F",)).analyze(_target("import os\n"))
        assert any(f.rule_id == "F401" for f in findings)

    def test_column_is_zero_based_characters(self) -> None:
        """Ruff JSON 은 1-based 문자. 내부 규약은 0-based."""
        findings = RuffAnalyzer(select=("F",)).analyze(_target("import os\n"))
        f = next(f for f in findings if f.rule_id == "F401")
        # `os` 는 8번째 문자(1-based) => 7 (0-based)
        assert f.location.span.start.column == 7

    def test_enclosing_symbol_is_populated(self) -> None:
        """🔴 Ruff 가 내주지 않는 정보 - 이 플랫폼의 차별점."""
        src = "def outer():\n    import os\n    return 1\n"
        findings = RuffAnalyzer(select=("F",)).analyze(_target(src))
        f = next(f for f in findings if f.rule_id == "F401")
        assert f.location.symbol == "outer"

    def test_config_signature_records_rule_selection(self) -> None:
        """🔴 룰 선택은 측정 손잡이다 - 매니페스트에 실려야 한다."""
        a = RuffAnalyzer(select=("F", "E"))
        b = RuffAnalyzer(select=("ALL",))
        assert a.config_signature() != b.config_signature()
        assert "F+E" in a.config_signature()

    def test_target_version_is_pinned(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """🔴 [실측] 대상 판이 없으면 `--isolated` 의 Ruff 는 3.10 으로 보고
        3.11 의 ExceptionGroup 에 F821 을 낸다 - D109 에서 덮는 범위 안의
        결함 주장(FP)이 됐다.

        같은 입력을 3.10 으로 보게 한 대조군이 F821 을 내야 공허하지 않다.
        """
        src = 'raise ExceptionGroup("x", [ValueError()])\n'
        pinned = RuffAnalyzer(select=("F",)).analyze(_target(src))
        assert not any(f.rule_id == "F821" for f in pinned)
        monkeypatch.setattr(ruff_module, "_TARGET", "py310")
        older = RuffAnalyzer(select=("F",)).analyze(_target(src))
        assert any(f.rule_id == "F821" for f in older), "대조군이 F821 을 내지 않는다"

    def test_target_version_is_recorded_in_signature(self) -> None:
        major, minor = TARGET_PYTHON
        assert f"target=py{major}{minor}" in RuffAnalyzer(select=("F",)).config_signature()

    def test_rule_selection_changes_finding_count(self) -> None:
        src = "import os\ndef f():\n    pass\n"
        few = RuffAnalyzer(select=("F",)).analyze(_target(src))
        many = RuffAnalyzer(select=("ALL",)).analyze(_target(src))
        assert len(many) > len(few), "룰 선택이 결과를 바꾸지 않으면 손잡이가 아니다"

    def test_noqa_is_ignored_by_default(self) -> None:
        src = "import os  # noqa: F401\n"
        assert RuffAnalyzer(select=("F",), ignore_noqa=True).analyze(_target(src))
        assert not RuffAnalyzer(select=("F",), ignore_noqa=False).analyze(_target(src))

    def test_clean_code_yields_nothing(self) -> None:
        assert RuffAnalyzer(select=("F",)).analyze(_target("x = 1\n")) == []


class TestMypyAdapter:
    def test_python_version_is_pinned(self) -> None:
        """🔴 판을 주지 않으면 mypy 는 실행한 인터프리터 판을 따르고,
        그 판은 매니페스트에 남지 않는다."""
        major, minor = TARGET_PYTHON
        assert f"--python-version={major}.{minor}" in MypyAnalyzer.DEFAULT_FLAGS
        assert f"py={major}.{minor}" in MypyAnalyzer().config_signature()

    def test_finds_a_type_error(self) -> None:
        src = 'def f(x: int) -> str:\n    return x\n'
        findings = MypyAnalyzer().analyze(_target(src))
        assert any(f.rule_id == "return-value" for f in findings)

    def test_column_converts_bytes_to_characters(self) -> None:
        """🔴 mypy JSON 은 0-based **바이트**. 비ASCII 가 있으면 갈린다."""
        src = 'def f() -> int:\n    s = "héllo"\n    return s\n'
        findings = MypyAnalyzer().analyze(_target(src))
        for f in findings:
            line = src.splitlines()[f.location.line - 1]
            assert f.location.span.start.column <= len(line), (
                "문자 열이 그 줄의 문자 수를 넘는다 - 바이트를 그대로 쓴 것이다"
            )

    def test_clean_code_yields_nothing(self) -> None:
        assert MypyAnalyzer().analyze(_target("x: int = 1\n")) == []


@pytest.mark.parametrize("analyzer", [RuffAnalyzer(), MypyAnalyzer()])
def test_version_is_reported(analyzer: RuffAnalyzer | MypyAnalyzer) -> None:
    v = analyzer.version()
    assert v.version not in {"", "unknown"}, "버전을 못 읽으면 매니페스트가 무의미하다"
