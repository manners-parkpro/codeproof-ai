"""decoy 검증기 테스트.

🔴 검증기 테스트에서 가장 중요한 건 "통과한다" 가 아니라
   **"위반을 실제로 잡는다"** 이다. 잡지 못하는 검증기는 통과가 무의미하다.
   그래서 각 규칙마다 일부러 깨진 입력을 만들어 넣는다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from codeproof_ai.corpus.decoy import (
    DecoyLoadError,
    Level,
    LineRange,
    TrapKind,
    changed_lines_in_decoy,
    load_decoy,
    validate_corpus,
    validate_decoy,
)

REPO_DECOYS = Path(__file__).resolve().parents[2] / "corpus" / "decoys"

GOOD_DECOY = '''"""설정 로더."""

_REQUIRED = ("host", "port")


def load(settings: dict[str, str]) -> tuple[str, int]:
    missing = [k for k in _REQUIRED if k not in settings]
    if missing:
        raise ValueError(missing)

    return settings["host"], int(settings["port"])
'''

GOOD_TWIN = '''"""설정 로더."""

_REQUIRED = ("host", "port")


def load(settings: dict[str, str]) -> tuple[str, int]:
    return settings["host"], int(settings["port"])
'''

GOOD_JUSTIFICATION = (
    "바로 위 missing 검사가 _REQUIRED 의 모든 키를 순회해 부재 키를 모으고 "
    "하나라도 있으면 예외를 올리기 때문에, 반환문에 도달했다는 것은 "
    "모든 키가 존재한다는 뜻이다."
)


def _meta(**over: object) -> str:
    base: dict[str, object] = {
        "decoy_id": "D999-test",
        "trap_kind": "upstream_validation",
        "apparent_defect": "settings 첨자 접근이 무방비로 보인다",
        "lure_lines": [11, 11],
        "claim": "반환문의 dict 접근은 KeyError 를 낼 수 없다",
        "justification": GOOD_JUSTIFICATION,
        "guard_symbol": "missing",
        "guard_lines": [7, 9],
        "twin_defect": "missing 검사가 없어 KeyError 가 전파된다",
        "acknowledged_warnings": [],
    }
    base |= over
    return f"""
decoy_id = "{base["decoy_id"]}"
trap_kind = "{base["trap_kind"]}"
acknowledged_warnings = {base["acknowledged_warnings"]!r}

[bait]
apparent_defect = \"\"\"{base["apparent_defect"]}\"\"\"
lure_lines = {base["lure_lines"]!r}

[safety]
claim = "{base["claim"]}"
justification = \"\"\"{base["justification"]}\"\"\"
guard_symbol = "{base["guard_symbol"]}"
guard_lines = {base["guard_lines"]!r}

[twin]
defect = \"\"\"{base["twin_defect"]}\"\"\"
"""


GOOD_PROOF = """\
from types import ModuleType


def attack(mod: ModuleType) -> bool:
    return False
"""


@pytest.fixture
def decoy_dir(tmp_path: Path) -> Path:
    d = tmp_path / "D999-test"
    d.mkdir()
    (d / "decoy.py").write_text(GOOD_DECOY, encoding="utf-8")
    (d / "twin.py").write_text(GOOD_TWIN, encoding="utf-8")
    (d / "meta.toml").write_text(_meta(), encoding="utf-8")
    (d / "proof.py").write_text(GOOD_PROOF, encoding="utf-8")
    return d


def _errors(d: Path) -> set[str]:
    return {v.rule for v in validate_decoy(load_decoy(d)) if v.level is Level.ERROR}


class TestBaselineIsValid:
    """기준 픽스처가 통과해야 아래 음성 테스트가 의미를 갖는다."""

    def test_good_decoy_passes(self, decoy_dir: Path) -> None:
        assert _errors(decoy_dir) == set()

    def test_loads_all_fields(self, decoy_dir: Path) -> None:
        rec = load_decoy(decoy_dir)
        assert rec.decoy_id == "D999-test"
        assert rec.trap_kind is TrapKind.UPSTREAM_VALIDATION
        assert rec.guard == LineRange(7, 9)


class TestCatchesViolations:
    """🔴 각 규칙이 실제로 위반을 잡는지 - 이게 본체다."""

    def test_v13_guard_lines_must_involve_the_symbol(self, decoy_dir: Path) -> None:
        """🔴 파일 안이면서 **엉뚱한 줄**인 경우를 잡는다.

        V4 는 「구간이 파일 안인가」와 「심볼이 파일에 있는가」를 따로 본다.
        둘 다 통과하면서 서로 다른 곳을 가리킬 수 있다.
        """
        (decoy_dir / "meta.toml").write_text(
            _meta(guard_lines=[1, 2]), encoding="utf-8"
        )
        assert "V13" in _errors(decoy_dir)

    def test_v13_accepts_a_use_site_guard(self, decoy_dir: Path) -> None:
        """가드는 심볼의 **정의**일 수도 **호출부**일 수도 있다.

        [실측] 정의만 허용했더니 D001·D026 을 잘못 잡았다 - 둘 다 가드가
        호출부에 있는 정당한 decoy 다.
        """
        src = (decoy_dir / "decoy.py").read_text(encoding="utf-8")
        # _REQUIRED 는 위에서 정의되고 아래 컴프리헨션에서 **쓰인다**
        line = next(
            i
            for i, text in enumerate(src.splitlines(), 1)
            if "_REQUIRED" in text and "for k in" in text
        )
        (decoy_dir / "meta.toml").write_text(
            _meta(guard_symbol="_REQUIRED", guard_lines=[line, line]),
            encoding="utf-8",
        )
        assert "V13" not in _errors(decoy_dir)

    def test_v12_missing_proof(self, decoy_dir: Path) -> None:
        (decoy_dir / "proof.py").unlink()
        assert "V12" in _errors(decoy_dir)

    def test_v12_proof_without_attack(self, decoy_dir: Path) -> None:
        (decoy_dir / "proof.py").write_text("x = 1\n", encoding="utf-8")
        assert "V12" in _errors(decoy_dir)

    def test_v12_attack_with_wrong_arity(self, decoy_dir: Path) -> None:
        (decoy_dir / "proof.py").write_text(
            "def attack() -> bool:\n    return False\n", encoding="utf-8"
        )
        assert "V12" in _errors(decoy_dir)

    def test_v7_id_mismatch(self, decoy_dir: Path) -> None:
        (decoy_dir / "meta.toml").write_text(_meta(decoy_id="D998-other"), encoding="utf-8")
        assert "V7" in _errors(decoy_dir)

    def test_v2_syntax_error(self, decoy_dir: Path) -> None:
        (decoy_dir / "twin.py").write_text("def broken(\n", encoding="utf-8")
        assert "V2" in _errors(decoy_dir)

    def test_v3_short_justification(self, decoy_dir: Path) -> None:
        (decoy_dir / "meta.toml").write_text(_meta(justification="안전하다"), encoding="utf-8")
        assert "V3" in _errors(decoy_dir)

    def test_v3_hollow_justification(self, decoy_dir: Path) -> None:
        hollow = "안전하다 " * 20  # 길지만 서로 다른 낱말이 하나뿐
        (decoy_dir / "meta.toml").write_text(_meta(justification=hollow), encoding="utf-8")
        assert "V3" in _errors(decoy_dir)

    def test_v4_guard_outside_file(self, decoy_dir: Path) -> None:
        """🔴 핵심 규칙 - 가드가 제시된 코드 밖이면 decoy 가 아니다."""
        (decoy_dir / "meta.toml").write_text(_meta(guard_lines=[900, 910]), encoding="utf-8")
        assert "V4" in _errors(decoy_dir)

    def test_v4_guard_symbol_absent(self, decoy_dir: Path) -> None:
        (decoy_dir / "meta.toml").write_text(_meta(guard_symbol="없는심볼"), encoding="utf-8")
        assert "V4" in _errors(decoy_dir)

    def test_v10_lure_outside_file(self, decoy_dir: Path) -> None:
        (decoy_dir / "meta.toml").write_text(_meta(lure_lines=[900, 901]), encoding="utf-8")
        assert "V10" in _errors(decoy_dir)

    def test_v5_identical_twin(self, decoy_dir: Path) -> None:
        (decoy_dir / "twin.py").write_text(GOOD_DECOY, encoding="utf-8")
        assert "V5" in _errors(decoy_dir)

    def test_v6_twin_diff_too_large(self, decoy_dir: Path) -> None:
        """decoy 가 짧아도 twin 이 부풀면 잡아야 한다 - 양쪽을 세는 이유."""
        padding = "\n".join(f"    step_{i}()" for i in range(30))
        (decoy_dir / "twin.py").write_text(GOOD_TWIN + padding + "\n", encoding="utf-8")
        assert "V6" in _errors(decoy_dir)

    def test_v9_diff_misses_the_guard(self, decoy_dir: Path) -> None:
        """가드가 아니라 딴 데를 고친 twin 은 쌍둥이가 아니다."""
        twin = GOOD_DECOY.replace('_REQUIRED = ("host", "port")', '_REQUIRED = ("host",)')
        (decoy_dir / "twin.py").write_text(twin, encoding="utf-8")
        assert "V9" in _errors(decoy_dir)


class TestAcknowledgement:
    def test_acknowledged_warning_is_suppressed(self, decoy_dir: Path) -> None:
        twin = GOOD_TWIN.replace(
            "def load(settings: dict[str, str])",
            "def load(settings: dict[str, str], strict: bool = False)",
        )
        (decoy_dir / "twin.py").write_text(twin, encoding="utf-8")
        before = {v.rule for v in validate_decoy(load_decoy(decoy_dir))}
        assert "W2" in before, "픽스처가 W2 를 유발하지 못한다"

        (decoy_dir / "meta.toml").write_text(
            _meta(acknowledged_warnings=["W2"]), encoding="utf-8"
        )
        after = {v.rule for v in validate_decoy(load_decoy(decoy_dir))}
        assert "W2" not in after

    def test_acknowledging_an_error_does_not_suppress_it(self, decoy_dir: Path) -> None:
        """🔴 ERROR 는 수용 대상이 아니다 - 수용 가능하면 그건 ERROR 가 아니어야 한다."""
        (decoy_dir / "meta.toml").write_text(
            _meta(guard_symbol="없는심볼", acknowledged_warnings=["V4"]), encoding="utf-8"
        )
        assert "V4" in _errors(decoy_dir)

    def test_stale_acknowledgement_is_flagged(self, decoy_dir: Path) -> None:
        (decoy_dir / "meta.toml").write_text(
            _meta(acknowledged_warnings=["W2"]), encoding="utf-8"
        )
        rules = {v.rule for v in validate_decoy(load_decoy(decoy_dir))}
        assert "V11" in rules, "쓰이지 않는 수용 표기를 잡지 못한다"


class TestLoadErrors:
    def test_missing_file(self, decoy_dir: Path) -> None:
        (decoy_dir / "twin.py").unlink()
        with pytest.raises(DecoyLoadError, match=r"twin\.py"):
            load_decoy(decoy_dir)

    def test_missing_field(self, decoy_dir: Path) -> None:
        (decoy_dir / "meta.toml").write_text('decoy_id = "x"\n', encoding="utf-8")
        with pytest.raises(DecoyLoadError, match="필수 항목"):
            load_decoy(decoy_dir)

    def test_unknown_trap_kind(self, decoy_dir: Path) -> None:
        (decoy_dir / "meta.toml").write_text(_meta(trap_kind="made_up"), encoding="utf-8")
        with pytest.raises(DecoyLoadError):
            load_decoy(decoy_dir)

    def test_malformed_range(self, decoy_dir: Path) -> None:
        (decoy_dir / "meta.toml").write_text(_meta(guard_lines=[7]), encoding="utf-8")
        with pytest.raises(DecoyLoadError, match="두 정수"):
            load_decoy(decoy_dir)


class TestDiffRanges:
    def test_reports_decoy_side_lines(self) -> None:
        ranges = changed_lines_in_decoy("a\nb\nc\n", "a\nc\n")
        assert ranges and ranges[0].start == 2

    def test_identical_sources_have_no_ranges(self) -> None:
        assert changed_lines_in_decoy("a\nb\n", "a\nb\n") == []


class TestShippedCorpus:
    """저장소에 실제로 들어 있는 decoy 가 규격을 지키는지."""

    def test_repo_corpus_is_clean(self) -> None:
        """🔴 훅과 같은 기준(`--strict`)이다 - 경고도 센다.

        훅은 Write·Edit 로 고칠 때만 돈다. Bash·편집기로 고친 decoy 는 이 테스트만 본다.
        [실측] 오류만 보던 때는 쓰이지 않는 수용 표기(V11)를 넣어도 통과했다.
        """
        report = validate_corpus(REPO_DECOYS)
        detail = "\n".join(f"{n}: {v}" for n, v in report.violations)
        assert report.ok, f"코퍼스에 오류가 있다:\n{detail}"
        assert report.warn_count == 0, f"코퍼스에 경고가 있다 (훅은 --strict):\n{detail}"

    def test_template_is_skipped(self) -> None:
        """_TEMPLATE 는 일부러 미완성이라 검사 대상이 아니어야 한다."""
        assert (REPO_DECOYS / "_TEMPLATE").is_dir()
        report = validate_corpus(REPO_DECOYS)
        assert all(name != "_TEMPLATE" for name, _ in report.violations)
