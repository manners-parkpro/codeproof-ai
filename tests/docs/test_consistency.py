"""문서와 코드의 일관성.

🔴 문서가 코드와 어긋나면 그게 곧 드리프트다. 사람이 눈으로 맞추면
   반드시 어긋나므로, **어긋날 수 있는 지점만** 기계로 잡는다.

이 테스트가 깨지면 문서를 고친다 - 테스트를 고치는 게 아니다.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

from codeproof_ai.cli import _COMMANDS, build_parser
from codeproof_ai.corpus.decoy import TrapKind

ROOT = Path(__file__).resolve().parents[2]
DECOYS = ROOT / "corpus" / "decoys"
DOCS = {
    "README.md": ROOT / "README.md",
    "CLAUDE.md": ROOT / "CLAUDE.md",
    "docs/DESIGN.md": ROOT / "docs" / "DESIGN.md",
}


def _text(name: str) -> str:
    return DOCS[name].read_text(encoding="utf-8")


def _all_docs() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in DOCS.values())


class TestReferencedFilesExist:
    """🔴 문서가 가리키는 파일이 사라지면 독자가 헛걸음한다."""

    def test_source_paths_resolve(self) -> None:
        pattern = re.compile(r"(?:src/codeproof_ai|\.claude|tests)/[\w/]+\.(?:py|sh)")
        missing = {
            m for m in pattern.findall(_all_docs()) if not (ROOT / m).is_file()
        }
        assert not missing, f"문서가 없는 파일을 가리킨다: {sorted(missing)}"

    def test_internal_links_resolve(self) -> None:
        pattern = re.compile(r"\]\((?!https?:)([^)#]+)")
        missing = set()
        for name, path in DOCS.items():
            for link in pattern.findall(path.read_text(encoding="utf-8")):
                if not (path.parent / link).resolve().exists():
                    missing.add(f"{name} → {link}")
        assert not missing, f"깨진 내부 링크: {sorted(missing)}"


class TestCorpusCountIsCurrent:
    """decoy 수는 자주 바뀐다 - 문서가 따라가는지 본다."""

    def _actual(self) -> int:
        return sum(
            1
            for d in DECOYS.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        )

    def test_claimed_pair_count_matches(self) -> None:
        actual = self._actual()
        claims = {int(m) for m in re.findall(r"(\d+)쌍", _all_docs())}
        # 목표치(150)는 주장이 아니라 목표다 - 실제값이 주장에 있어야 한다.
        assert actual in claims, (
            f"decoy 가 {actual}쌍인데 문서는 {sorted(claims)}쌍이라고 한다"
        )

    def test_smaller_claims_are_marked_as_historical(self) -> None:
        """실제보다 작은 수는 **과거 시점의 실측**이라고 밝혀야 한다.

        코퍼스가 자라도 과거 측정값은 그대로 유효하다 - 지우는 게 아니라
        「그때의 숫자」라고 적는 것이 맞다. 다만 현재값으로 읽히면 안 된다.
        """
        actual = self._actual()
        text = _all_docs()
        unmarked: list[str] = []
        for m in re.finditer(r"(\d+)쌍", text):
            if int(m.group(1)) >= actual:
                continue
            window = text[max(0, m.start() - 60) : m.end() + 120]
            if "시점" not in window and "목표" not in window:
                unmarked.append(window.strip()[:90])
        assert not unmarked, (
            f"실제 {actual}쌍보다 작은 수가 시점 표기 없이 있다:\n"
            + "\n".join(f"  ...{u}..." for u in unmarked)
        )


class TestTrapTaxonomyIsCovered:
    """🔴 분류표를 늘리고 decoy 를 안 쓰면 빈칸이 조용히 생긴다."""

    def test_every_trap_kind_has_a_decoy(self) -> None:
        used = {
            tomllib.loads((d / "meta.toml").read_text(encoding="utf-8"))["trap_kind"]
            for d in DECOYS.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        }
        unused = {t.value for t in TrapKind} - used
        assert not unused, f"decoy 가 없는 분류: {sorted(unused)}"

    def test_documented_count_matches_enum(self) -> None:
        claims = {int(m) for m in re.findall(r"분류(?:표)?\s*(\d+)종", _all_docs())}
        if claims:
            assert len(list(TrapKind)) in claims, (
                f"TrapKind 는 {len(list(TrapKind))}종인데 문서는 {sorted(claims)}종"
            )


class TestCliSurfaceMatchesDocs:
    """문서에 있는 명령이 실재해야 한다."""

    def _real_commands(self) -> set[str]:
        parser = build_parser()
        for action in parser._actions:
            if action.choices and hasattr(action.choices, "keys"):
                return set(action.choices)
        pytest.fail("서브명령을 찾지 못했다")

    def test_documented_commands_exist(self) -> None:
        documented = set(re.findall(r"codeproof ([a-z]+)", _all_docs()))
        unknown = documented - self._real_commands()
        assert not unknown, f"문서에만 있는 명령: {sorted(unknown)}"

    def test_unimplemented_commands_are_not_advertised_as_working(self) -> None:
        """🔴 `[미구현]` 을 내는 명령을 「지금 동작한다」 절에 두지 않는다."""
        parser = build_parser()
        all_cmds = self._real_commands()
        unimplemented = all_cmds - set(_COMMANDS)
        assert unimplemented, "미구현 명령이 사라졌다면 이 테스트를 지운다"

        readme = _text("README.md")
        start = readme.find("### 지금 동작하는 것")
        if start == -1:
            return
        section = readme[start : readme.find("###", start + 10)]
        leaked = {c for c in unimplemented if f"codeproof {c}" in section}
        assert not leaked, f"미구현 명령이 「지금 동작」 절에 있다: {sorted(leaked)}"
        assert parser is not None


class TestMeasuredClaimsAreLabelled:
    """🔴 실측값과 추정을 섞지 않는다 - jupiter 의 [실측] 규율과 같은 원칙."""

    MARKERS = ("[실측]", "[소스", "실측", "목표")

    def test_magnitude_claims_carry_a_provenance_marker(self) -> None:
        """배수 주장에는 출처가 있어야 한다.

        `[실측]`(직접 측정) 또는 `[소스]`(문헌 인용) 중 하나.
        표기할 수 없으면 그건 주장이 아니라 인상이다.
        """
        text = _all_docs()
        unmarked: list[str] = []
        for match in re.finditer(r"(\d+(?:\.\d+)?)배", text):
            window = text[max(0, match.start() - 260) : match.end() + 100]
            if not any(mk in window for mk in self.MARKERS):
                unmarked.append(f"{match.group()} ...{window[-100:].strip()}")
        assert not unmarked, (
            "출처 표기 없는 배수 주장:\n" + "\n".join(f"  {u}" for u in unmarked)
        )
