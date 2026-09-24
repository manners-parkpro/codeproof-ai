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

from codeproof_ai.cli import _COMMANDS, build_parser, main
from codeproof_ai.corpus.decoy import TrapKind

ROOT = Path(__file__).resolve().parents[2]
MEASUREMENTS = ROOT / "docs" / "MEASUREMENTS.md"
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


class TestGeneratedMeasurementsAreCurrent:
    """🔴 측정값은 생성물이다 - 산문에 베끼면 반드시 낡는다.

    [실측] 코퍼스를 19 -> 25 -> 37 -> 43 쌍으로 키우는 동안 **매번** 아래
    `TestCorpusCountIsCurrent` 가 낡은 숫자를 잡았다. 테스트가 제 일을 한
    것이지만 반복되는 것은 신호였다 - 변동하는 값을 산문에 박아 둔 게 원인이다.
    그래서 `codeproof report` 가 `docs/MEASUREMENTS.md` 를 생성하고,
    산문은 안정된 주장만 쓰고 숫자는 그 파일을 가리킨다.
    """

    def test_measurements_file_exists(self) -> None:
        assert MEASUREMENTS.is_file(), (
            "docs/MEASUREMENTS.md 가 없다 - `uv run codeproof report` 로 만든다"
        )

    def test_it_is_marked_as_generated(self) -> None:
        head = MEASUREMENTS.read_text(encoding="utf-8").splitlines()[0]
        assert "생성된 파일" in head and "codeproof report" in head, (
            "생성물이라는 표시가 없으면 누군가 손으로 고친다"
        )

    def test_it_is_up_to_date(self) -> None:
        """🔴 코퍼스가 자랐는데 다시 만들지 않았으면 여기서 걸린다."""
        code = main(["report", "--check"])
        assert code == 0, (
            "docs/MEASUREMENTS.md 가 코퍼스와 어긋난다 - "
            "`uv run codeproof report` 로 다시 만든다"
        )


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
        claims = {
            int(m)
            for m in re.findall(
                r"(\d+)쌍", MEASUREMENTS.read_text(encoding="utf-8")
            )
        }
        assert actual in claims, (
            f"decoy 가 {actual}쌍인데 생성된 측정값은 {sorted(claims)}쌍이라고 한다 - "
            "`uv run codeproof report` 로 다시 만든다"
        )

    def test_prose_carries_no_unmarked_count(self) -> None:
        """🔴 산문의 쌍 수는 전부 **시점**이거나 **목표**여야 한다.

        현재값은 산문이 들지 않는다 - 생성물(`docs/MEASUREMENTS.md`)이 든다.
        [실측] 19 -> 25 -> 37 -> 43 쌍을 거치며 이 테스트가 **매번** 산문의
        낡은 숫자를 잡았다. 테스트가 제 일을 한 것이지만, 반복은 설계 신호였다.

        허용되는 표기 셋:
          · `목표` - 도달하려는 값이지 주장이 아니다
          · `시점` - 그때의 실측이라고 밝힌 것
          · `실측 · N쌍` - 코퍼스 크기를 함께 적어 **스스로 날짜를 밝힌** 값

        마지막 것이 권장이다. 숫자와 그 숫자가 나온 표본 크기가 붙어 다니면
        나중에 읽어도 무엇에 대한 값인지 분명하다.
        """
        actual = self._actual()
        text = _all_docs()
        unmarked: list[str] = []
        for m in re.finditer(r"(\d+)쌍", text):
            window = text[max(0, m.start() - 60) : m.end() + 120]
            if not any(mk in window for mk in ("시점", "목표", "실측")):
                unmarked.append(window.strip()[:90])
        assert not unmarked, (
            f"산문에 시점·목표 표기 없는 쌍 수가 있다 (현재 {actual}쌍). "
            "현재값은 docs/MEASUREMENTS.md 가 든다:\n"
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
