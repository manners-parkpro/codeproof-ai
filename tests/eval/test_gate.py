"""codex 가 쓴 쌍의 관문 (DESIGN §7.10d) - 깨끗한 쌍은 통과하고, 한 성질만 깬 쌍은 그 검사에서 운다.

🔴 계약이 두 줄이다 (H3) - 통과만 보면 아무것도 안 보는 관문도 초록불이다.
   기준 쌍은 D115 다: 관문의 검사를 전부 넘고, 작고, 경쟁에 기대지 않는다.
"""

from __future__ import annotations

import shutil
import tomllib
from typing import TYPE_CHECKING

import pytest

from codeproof_ai.corpus.plan import PLAN
from codeproof_ai.corpus.shape import classify
from codeproof_ai.eval.gate import gate, inner_docstrings, neutral_problem, prose_comments
from tests.corpora import DECOYS

if TYPE_CHECKING:
    from pathlib import Path

    from codeproof_ai.eval.gate import Check

BASE = next(DECOYS.glob("D115-*"))
TAIL = 'def _extra() -> None:\n    """덧붙인 함수."""\n'


@pytest.fixture
def pair(tmp_path: Path) -> Path:
    dst = tmp_path / "corpus" / BASE.name
    shutil.copytree(BASE, dst)
    return dst


def _run(pair: Path) -> dict[str, Check]:
    work = pair.parent.parent / "work"
    work.mkdir(exist_ok=True)
    return {c.name: c for c in gate(pair, work, race_runs=1)}


def _edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, old
    path.write_text(text.replace(old, new), encoding="utf-8")


class TestTheCleanPairPasses:
    def test_every_check_passes(self, pair: Path) -> None:
        """대조군 - 이게 실패하면 아래의 「운다」는 아무것도 증명하지 못한다."""
        checks = _run(pair)
        assert set(checks) == {"validate", "proof", "mutants", "neutral", "cues", "plan"}
        assert all(c.ok for c in checks.values()), {n: c.detail for n, c in checks.items()}


class TestEachCheckCries:
    def test_validate(self, pair: Path) -> None:
        _edit(pair / "meta.toml", "lure_lines = [16, 16]", "lure_lines = [99, 99]")
        assert not _run(pair)["validate"].ok

    def test_proof(self, pair: Path) -> None:
        """결함을 못 잡는 공격은 안전을 증명하지 못한다 - twin 도 못 깨면 운다."""
        (pair / "proof.py").write_text(
            "def attack(mod: object) -> bool:\n    return False\n", encoding="utf-8"
        )
        check = _run(pair)["proof"]
        assert not check.ok
        assert "twin" in check.detail

    def test_mutants_need_both_directions(self, pair: Path) -> None:
        """약화만 있으면 증명이 주장 대신 구현을 묻는지 보지 못한다 (§3.5 반대 방향)."""
        text = (pair / "mutants.py").read_text(encoding="utf-8")
        (pair / "mutants.py").write_text(text.split("\nSAFE")[0] + "\n", encoding="utf-8")
        check = _run(pair)["mutants"]
        assert not check.ok
        assert "하나 이상씩" in check.detail

    def test_a_weakening_that_survives(self, pair: Path) -> None:
        text = (pair / "mutants.py").read_text(encoding="utf-8")
        surviving = (
            "WEAKENED['못 잡는 약화'] = [('_TIERS = {', '_TIERS = {**{}, ')]\n"
        )
        (pair / "mutants.py").write_text(text + surviving, encoding="utf-8")
        check = _run(pair)["mutants"]
        assert not check.ok
        assert "못 잡는 약화" in check.detail

    def test_neutral(self, pair: Path) -> None:
        """모듈 docstring 이 「목적 - 기전」 꼴이 아니면 neutral 이 지울 기전이 없다."""
        for name in ("decoy.py", "twin.py"):
            source = (pair / name).read_text(encoding="utf-8")
            first = source.split("\n", 1)[0]
            _edit(pair / name, first, first.replace(" - ", " ; "))
        assert not _run(pair)["neutral"].ok

    def test_cues_prose_comment(self, pair: Path) -> None:
        """줄을 늘리지 않게 끝에 붙인다 - 정답 구간이 그대로여야 이 검사만 운다."""
        source = (pair / "decoy.py").read_text(encoding="utf-8")
        last = source.rstrip("\n").split("\n")[-1]
        _edit(pair / "decoy.py", last, last + "  # 모르는 요금제는 free 다")
        checks = _run(pair)
        assert not checks["cues"].ok
        assert "산문 주석" in checks["cues"].detail

    def test_cues_docstring_outside_the_guard(self, pair: Path) -> None:
        for name in ("decoy.py", "twin.py"):
            with (pair / name).open("a", encoding="utf-8") as f:
                f.write("\n\n" + TAIL)
        checks = _run(pair)
        assert checks["validate"].ok, checks["validate"].detail
        assert not checks["cues"].ok
        assert "guard_lines 밖" in checks["cues"].detail

    def test_cues_twin_adds_a_docstring(self, pair: Path) -> None:
        with (pair / "decoy.py").open("a", encoding="utf-8") as f:
            f.write("\n\n" + TAIL)
        with (pair / "twin.py").open("a", encoding="utf-8") as f:
            f.write("\n\n" + TAIL.replace("덧붙인 함수.", "다른 설명."))
        detail = _run(pair)["cues"].detail
        assert "twin.py: decoy 에 없는 docstring" in detail

    def test_plan(self, pair: Path) -> None:
        """분류가 정한 칸 밖의 가드 위치면 운다 - 이름만 그 분류인 쌍이다."""
        meta = tomllib.loads((pair / "meta.toml").read_text(encoding="utf-8"))
        shape = classify(
            (pair / "decoy.py").read_text(encoding="utf-8"),
            meta["bait"]["lure_lines"][0],
            meta["safety"]["guard_symbol"],
        )
        other = next(k for k, cells in PLAN.items() if shape not in cells)
        before, after = f'trap_kind = "{meta["trap_kind"]}"', f'trap_kind = "{other.value}"'
        _edit(pair / "meta.toml", before, after)
        assert not _run(pair)["plan"].ok


class TestTheHelpers:
    @pytest.mark.parametrize(
        ("source", "lines"),
        [
            ("x = 1  # noqa: E501\ny: int = 2  # type: ignore\n", []),
            ("#!/usr/bin/env python\nx = 1\n", []),
            ("x = 1  # 이유를 적는다\n", [1]),
        ],
        ids=["도구 지시", "셔뱅", "산문"],
    )
    def test_prose_comments(self, source: str, lines: list[int]) -> None:
        assert prose_comments(source) == lines

    def test_inner_docstrings_see_nested_definitions(self) -> None:
        source = 'class A:\n    """바깥."""\n    def f(self):\n        """안쪽."""\n'
        assert [d[2] for d in inner_docstrings(source)] == ["바깥.", "안쪽."]

    def test_neutral_problem_accepts_the_corpus_form(self) -> None:
        assert neutral_problem('"""요금 - 모르는 값은 free 다."""\nx = 1\n') is None

    def test_neutral_problem_rejects_a_missing_mechanism(self) -> None:
        assert neutral_problem('"""요금."""\nx = 1\n') is not None
