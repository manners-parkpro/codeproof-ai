"""레이어 의존 규칙.

🔴 이 파일이 이 저장소에서 가장 중요한 테스트다.

예전에는 "verify/ 가 Sample·Defect·Oracle 을 import 하면 실패" 라는
**타입 허용목록**으로 단속했다. 그건 새 라벨 타입이 생길 때마다 목록을
갱신해야 하고, 갱신을 잊으면 조용히 뚫린다.

지금은 **의존 그래프 하나**를 검사한다. 라벨 타입이 몇 개가 되든
eval/ 안에 있는 한 런타임은 볼 방법이 없다 - 구조가 막는다.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src" / "codeproof_ai"
PKG = "codeproof_ai"

# 각 레이어가 import 해도 되는 레이어. 자기 자신은 항상 허용.
#
#   domain  은 아무것도 import 하지 않는다 (A1)
#   런타임(analysis·llm·verify) 은 eval 을 볼 수 없다 (A1)
#     → 정답 라벨이 eval 안에 있으므로, 라벨을 볼 방법이 구조적으로 없다
ALLOWED: dict[str, frozenset[str]] = {
    "domain": frozenset(),
    "analysis": frozenset({"domain"}),
    "llm": frozenset({"domain"}),
    "verify": frozenset({"domain"}),
    # corpus 는 decoy 를 **작성·검증**한다. 실험 없이도 독립적으로 쓸 수 있어야 하므로
    # eval 을 모른다. 소비는 eval 쪽에서 한다 (eval → corpus).
    "corpus": frozenset({"domain"}),
    # reviewers 는 기존 구현을 Reviewer 로 감싸는 어댑터 층이다.
    "reviewers": frozenset({"domain", "analysis", "llm"}),
    "eval": frozenset({"domain", "analysis", "llm", "verify", "corpus", "reviewers"}),
    "store": frozenset({"domain", "eval"}),
    "cli": frozenset(
        {"domain", "analysis", "llm", "verify", "eval", "corpus", "store", "reviewers"}
    ),
}


def _layer_of(path: Path) -> str:
    rel = path.relative_to(SRC)
    return rel.parts[0] if len(rel.parts) > 1 else rel.stem


def _internal_imports(path: Path) -> set[tuple[str, int]]:
    """이 파일이 import 하는 내부 레이어와 줄 번호."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: set[tuple[str, int]] = set()

    def record(name: str, lineno: int) -> None:
        parts = name.split(".")
        if parts[0] == PKG and len(parts) > 1:
            out.add((parts[1], lineno))

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                record(node.module, node.lineno)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                record(alias.name, node.lineno)
    return out


def _python_files() -> list[Path]:
    return [p for p in SRC.rglob("*.py") if "__pycache__" not in p.parts]


class TestLayerGraph:
    def test_every_file_belongs_to_a_known_layer(self) -> None:
        unknown = {
            str(p.relative_to(SRC)): _layer_of(p)
            for p in _python_files()
            if _layer_of(p) not in ALLOWED and _layer_of(p) != "__init__"
        }
        assert not unknown, (
            f"ALLOWED 에 없는 레이어가 생겼다: {unknown}. "
            "새 레이어를 만들면 이 그래프에 의존 규칙을 명시한다."
        )

    def test_no_layer_violations(self) -> None:
        violations: list[str] = []
        for path in _python_files():
            layer = _layer_of(path)
            if layer not in ALLOWED:
                continue
            permitted = ALLOWED[layer] | {layer}
            violations.extend(
                f"{path.relative_to(SRC)}:{lineno} — {layer} → {imported}"
                for imported, lineno in sorted(_internal_imports(path))
                if imported not in permitted
            )
        assert not violations, "레이어 위반:\n" + "\n".join(f"  {v}" for v in violations)

    def test_runtime_cannot_reach_labels(self) -> None:
        """A1 - 런타임은 정답 라벨에 도달할 수 없다.

        타입 이름이 아니라 **레이어**로 검사한다. eval/ 에 무슨 타입이
        새로 생기든 런타임은 볼 수 없다.
        """
        for runtime in ("analysis", "llm", "verify"):
            assert "eval" not in ALLOWED[runtime], (
                f"{runtime} 가 eval 을 import 할 수 있게 열려 있다. "
                "그 순간 런타임 검증이 정답을 볼 수 있게 되고 A1 이 무너진다."
            )

    def test_domain_depends_on_nothing_internal(self) -> None:
        assert ALLOWED["domain"] == frozenset()
        bad = {
            str(p.relative_to(SRC)): sorted(imps)
            for p in _python_files()
            if _layer_of(p) == "domain"
            and (imps := {i for i, _ in _internal_imports(p)} - {"domain"})
        }
        assert not bad, f"domain 이 다른 레이어를 import 한다: {bad}"


class TestTheCheckActuallyWorks:
    """탐지기가 실제로 잡는지 - 통과가 무의미해지지 않게."""

    def test_detects_a_planted_violation(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.py"
        bad.write_text(
            "from codeproof_ai.eval.sample import Defect\n", encoding="utf-8"
        )
        assert ("eval", 1) in _internal_imports(bad)

    def test_ignores_docstring_mentions(self, tmp_path: Path) -> None:
        ok = tmp_path / "ok.py"
        ok.write_text(
            '"""eval 의 Defect 를 import 하면 안 된다."""\n', encoding="utf-8"
        )
        assert _internal_imports(ok) == set()

    def test_ignores_external_packages(self, tmp_path: Path) -> None:
        ok = tmp_path / "ok.py"
        ok.write_text("import ast\nfrom pathlib import Path\n", encoding="utf-8")
        assert _internal_imports(ok) == set()


class TestDomainPurity:
    """A1 - domain 은 stdlib 외에 아무것도 import 하지 않는다."""

    def test_domain_imports_only_stdlib(self) -> None:
        stdlib = set(sys.stdlib_module_names)
        offenders: dict[str, set[str]] = {}
        for path in _python_files():
            if _layer_of(path) != "domain":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            roots: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    roots.update(a.name.split(".")[0] for a in node.names)
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    roots.add(node.module.split(".")[0])
            if bad := roots - stdlib - {PKG, "__future__"}:
                offenders[str(path.relative_to(SRC))] = bad
        assert not offenders, (
            f"domain 에 외부 의존성이 들어왔다 (A1 위반): {offenders}. "
            "이걸 허용하면 도메인 테스트가 API 키를 요구하기 시작한다."
        )


@pytest.mark.parametrize("layer", sorted(ALLOWED))
def test_layer_directory_exists(layer: str) -> None:
    target = SRC / layer
    assert target.is_dir() or (SRC / f"{layer}.py").is_file(), (
        f"ALLOWED 에 {layer} 가 있는데 실물이 없다 - 그래프가 현실과 어긋났다"
    )
