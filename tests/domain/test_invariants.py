"""도메인 값 객체의 불변식.

레이어 의존 규칙은 tests/architecture/test_layering.py 가 본다.
여기 있는 테스트는 기능이 아니라 **설계 규칙**을 지킨다 -
깨지면 테스트를 고치지 말고 코드를 고친다.
"""

from __future__ import annotations

import ast
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from codeproof_ai.domain import (
    Finding,
    Location,
    Position,
    RunManifest,
    Span,
)


class TestD1ColumnNormalization:
    """B1 — 컬럼 규약 정규화. 비ASCII 회귀 테스트는 절대 지우지 않는다."""

    def test_byte_offset_differs_from_char_offset_on_non_ascii(self) -> None:
        # ast.col_offset 은 UTF-8 바이트, 내부 규약은 문자.
        # 이 두 값이 갈리는 걸 못 잡으면 ruff+mypy 병합이 조용히 어긋난다.
        source = 'x = "héllo"; y = zz'
        tree = ast.parse(source)
        names = [n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == "zz"]
        assert names, "테스트 픽스처가 깨졌다"
        byte_col = names[0].col_offset

        pos = Position.from_byte_0based(1, byte_col, source)
        assert pos.byte_column == byte_col
        assert pos.column == source.index("zz"), "문자 열이 원문 인덱스와 일치해야 한다"
        assert pos.column != pos.byte_column, (
            "비ASCII 가 있는데 바이트 열과 문자 열이 같다 — 변환이 동작하지 않는다"
        )

    def test_ascii_only_line_has_identical_offsets(self) -> None:
        source = "x = 1; y = zz"
        pos = Position.from_byte_0based(1, 11, source)
        assert pos.column == pos.byte_column == 11

    def test_ruff_one_based_column_becomes_zero_based(self) -> None:
        assert Position.from_char_1based(1, 8).column == 7

    def test_rejects_wrong_basis(self) -> None:
        with pytest.raises(ValueError, match="1-based"):
            Position(line=0, column=0)
        with pytest.raises(ValueError, match="0-based"):
            Position(line=1, column=-1)


class TestD2FingerprintExcludesLineNumber:
    """B2 — 지적 식별자에 라인 번호가 들어가면 안 된다."""

    def _finding(self, line: int) -> Finding:
        return Finding(
            source="ruff",
            rule_id="F401",
            message="`os` imported but unused",
            location=Location(
                path="src/a.py",
                span=Span(start=Position(line=line, column=7)),
                symbol="a.main",
            ),
            quoted_code="import os",
        )

    def test_fingerprint_is_stable_across_line_drift(self) -> None:
        # 위쪽에 줄이 추가돼 지적이 밀려도 같은 지적이어야 한다.
        assert self._finding(1).fingerprint == self._finding(999).fingerprint

    def test_fingerprint_changes_with_symbol(self) -> None:
        a = self._finding(1)
        b = a.with_symbol("a.other", "function")
        assert a.fingerprint != b.fingerprint

    def test_fingerprint_ignores_whitespace_in_snippet(self) -> None:
        base = self._finding(1)
        spaced = replace(base, quoted_code="import   os")
        assert base.fingerprint == spaced.fingerprint


class TestE1ManifestIsMandatory:
    """D4 · F2 — effort 미지정·잘못된 캐시 정책은 매니페스트 단계에서 막는다."""

    def _manifest(self, **kw: object) -> RunManifest:
        defaults: dict[str, object] = {
            "model_id": "claude-opus-5-5",
            "prompt_hash": "abc",
            "corpus_hash": "def",
            "effort": "high",
            "sample_n": 8,
            "cache_policy": "nonce",
            "grouper": "fingerprint",
            "harness_sha": "0" * 40,
            "created_at": datetime.now(UTC),
        }
        return RunManifest(**(defaults | kw))  # type: ignore[arg-type]

    def test_missing_effort_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="effort"):
            self._manifest(effort="")

    def test_bad_cache_policy_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="cache_policy"):
            self._manifest(cache_policy="whatever")

    def test_run_id_is_deterministic(self) -> None:
        ts = datetime.now(UTC)
        assert self._manifest(created_at=ts).run_id == self._manifest(created_at=ts).run_id

    def test_missing_grouper_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="grouper"):
            self._manifest(grouper="")

    def test_grouper_appears_in_disclosure(self) -> None:
        assert "fingerprint" in self._manifest().disclosure_block()

    def test_disclosure_block_names_omitted_params(self) -> None:
        block = self._manifest(params_omitted=("temperature", "seed")).disclosure_block()
        assert "temperature" in block and "seed" in block
        assert "명시값" in block


class TestD4Python314AstNodes:
    """D4 — 3.14 의 t-string 노드를 망라적 visitor 가 놓치지 않는지."""

    def test_template_str_nodes_exist(self) -> None:
        assert hasattr(ast, "TemplateStr"), "3.14 의 ast.TemplateStr 이 없다"
        assert hasattr(ast, "Interpolation")

    def test_removed_legacy_nodes_are_gone(self) -> None:
        for removed in ("Num", "Str", "Bytes", "NameConstant"):
            assert not hasattr(ast, removed), f"ast.{removed} 가 아직 있다 — 가정 재확인 필요"
