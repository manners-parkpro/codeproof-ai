"""문서와 코드의 일관성.

🔴 문서가 코드와 어긋나면 그게 곧 드리프트다. 사람이 눈으로 맞추면
   반드시 어긋나므로, **어긋날 수 있는 지점만** 기계로 잡는다.

이 테스트가 깨지면 문서를 고친다 - 테스트를 고치는 게 아니다.
"""

from __future__ import annotations

import argparse
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
    # 🔴 검증 프로토콜도 여기 든다. 베껴 쓰는 사람이 바로 막히는 문서라
    #    낡은 명령·깨진 링크가 특히 나쁘다.
    "docs/VERIFY.md": ROOT / "docs" / "VERIFY.md",
}


def _text(name: str) -> str:
    return DOCS[name].read_text(encoding="utf-8")


def _all_docs() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in DOCS.values())


class TestReferencedFilesExist:
    """🔴 문서가 가리키는 파일이 사라지면 독자가 헛걸음한다."""

    def test_source_paths_resolve(self) -> None:
        pattern = re.compile(
            r"(?:src/codeproof_ai|\.claude|tests|scripts)/[\w/]+\.(?:py|sh)"
        )
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

    def test_the_package_tree_lists_every_module(self) -> None:
        """🔴 DESIGN 의 패키지 트리에 **빠진 모듈이 없어야** 한다.

        [실측] 트리가 `paired.py` · `mix.py` · `provenance.py` · `report.py` ·
        registry 둘을 빠뜨리고 있었다. 문서가 코드 구조를 베끼는 한 반드시
        낡으므로, 「빠진 것이 없는가」만 기계로 본다.

        ⚠ 반대 방향(트리에 있는데 코드에 없는 것)은 `test_source_paths_resolve`
          가 이미 본다. 여기서는 누락만 본다 - 트리는 요약이므로 모든 파일을
          한 줄씩 적을 필요는 없지만, **이름조차 안 나오는 모듈은 없어야** 한다.
        """
        design = _text("docs/DESIGN.md")
        start = design.index("src/codeproof_ai/")
        tree = design[start : design.index("```", start)]
        pkg = ROOT / "src" / "codeproof_ai"
        missing = sorted(
            str(f.relative_to(pkg))
            for f in pkg.rglob("*.py")
            if f.name != "__init__.py" and f.stem not in tree
        )
        assert not missing, (
            f"패키지 트리에 이름조차 없는 모듈: {missing}"
        )

    def test_citations_are_well_formed_arxiv_ids(self) -> None:
        """🔴 인용이 실재하는지는 **사람이 확인한다.** 여기서는 모양만 본다.

        포트폴리오에서 존재하지 않는 인용은 치명적이다. 네트워크에 의존하는
        테스트는 오프라인에서 깨지므로 두지 않고, 대신 형식이 어긋난 것을
        잡는다 - arXiv ID 는 `YYMM.NNNNN` 이다.

        [확인 · 2026-09-27] 인용 19건의 URL 을 전부 열어 200 을 확인했고,
        핵심 4건(c-CRAB · PrimeVul · CR-Bench · 합의 감사)은 제목과 수치까지
        대조했다. PrimeVul 의 F1 68.26% -> 3.09% 도 원문에서 확인했다.
        """
        ids = re.findall(r"arxiv\.org/(?:abs|html)/(\d{4})\.(\d{4,5})", _all_docs())
        assert ids, "arXiv 인용을 찾지 못했다 - 패턴이 바뀌었나"

        bad = [
            f"{yy}.{nn}"
            for yy, nn in ids
            if not ("01" <= yy[2:] <= "12" and yy[:2].isdigit())
        ]
        assert not bad, f"arXiv ID 형식이 아니다: {bad}"


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


class TestProseDoesNotContradictTheGeneratedFile:
    """🔴 산문이 생성물과 다른 숫자를 말하면 둘 중 하나는 거짓이다.

    [실측] README 가 「Ruff 의 구별 성공은 0/60」이라고 적고 있었는데
    생성물은 11/60 이었다. **구별 성공률은 리뷰어의 성질이 아니라
    (리뷰어 x 채점자)의 성질**인데 채점자를 빼고 적은 탓이다.
    0/60 은 `injected_defect` 의 숫자이고 `provable_safety` 로는 11/60 이다.

    같은 실행에서 한 쪽은 「11건 갈라냈다」, 다른 쪽은 「하나도 못 갈랐다」고
    말한다 - 그게 이 프로젝트의 논지이므로 **어느 정의인지 반드시 적는다.**
    """

    def test_grader_fp_counts_match_the_generated_file(self) -> None:
        """🔴 산문의 채점자별 FP 수가 생성물과 같아야 한다.

        [실측] 이 검사를 넣기 전까지 README 의 편차 표가 **두 번** 낡았다 -
        한 번은 코퍼스가 자라서, 한 번은 관례 주장 수정으로 FP 66 -> 6 이
        되면서. 사람 눈으로 잡다가 놓쳤고 둘 다 헤드라인 숫자였다.

        생성물(`docs/MEASUREMENTS.md`)은 `report --check` 가 최신을 보장하므로,
        산문이 거기 적힌 수를 인용하는지만 보면 된다.
        """
        generated = MEASUREMENTS.read_text(encoding="utf-8")
        # | `provable_safety` | 0 | 7 | 231 | o |   ->   FP 는 세 번째 칸
        truth = {
            m.group("grader"): m.group("fp")
            for m in re.finditer(
                r"\|\s*`(?P<grader>\w+)`\s*\|\s*\d+\s*\|\s*(?P<fp>\d+)\s*\|",
                generated,
            )
        }
        assert truth, "생성물에서 편차 표를 읽지 못했다"
        assert len(truth) >= 2, f"채점자가 하나뿐이면 대조가 공허하다: {truth}"

        readme = _text("README.md")
        wrong: list[str] = []
        for grader, fp in truth.items():
            for m in re.finditer(rf"^{grader}\s+\d+\s+(\d+)\s", readme, re.M):
                if m.group(1) != fp:
                    wrong.append(f"{grader}: README {m.group(1)} vs 생성물 {fp}")
        assert not wrong, (
            "산문의 FP 수가 생성물과 다르다 - "
            "`uv run codeproof report` 를 보고 고친다:\n  " + "\n  ".join(wrong)
        )

    def test_prose_does_not_quote_a_bare_discrimination_rate(self) -> None:
        """산문의 구별 성공 숫자는 **채점자 이름과 같은 문단**에 있어야 한다."""
        readme = _text("README.md")
        offenders: list[str] = []
        for m in re.finditer(r"구별 성공[^\n]*?(\d+/\d+)", readme):
            window = readme[max(0, m.start() - 400) : m.end() + 400]
            named = any(
                g in window
                for g in ("provable_safety", "injected_defect", "채점 정의", "채점자")
            )
            if not named:
                offenders.append(m.group(0).strip())
        assert not offenders, (
            "채점자를 밝히지 않은 구별 성공률이 있다 - "
            f"정의마다 다른 숫자가 나온다: {offenders}"
        )

    def test_grader_comparisons_name_the_rule_selection(self) -> None:
        """🔴 편차는 (채점자 x **룰 선택**)의 성질이다 - 어느 선택인지 적는다.

        [실측] 검증 프로토콜(docs/VERIFY.md)을 쓰다가 발견했다. 헤드라인
        「정의만 바꿔도 FP 가 34배」는 `--ruff-select ALL` 에서만 성립한다.
        `S`(보안 룰) 로 좁히면 두 정의가 **정확히 일치해** 편차가 1.0배가 되고,
        짝 채점의 11 vs 0 도 **둘 다 0** 이 되어 사라진다.

        편차의 정체가 「판정 불가로 둘 것을 오답으로 세느냐」이기 때문이다 -
        보안 룰은 전부 근거 범위 안의 결함 주장이라 이견이 생길 자리가 없다.

        이건 바로 위 테스트가 막는 오류의 **두 번째 축**이다. 거기서는
        「구별 성공률은 (리뷰어 x 채점자)」를 배웠는데, 같은 규율을 룰 선택에는
        적용하지 않고 있었다. 축이 하나 남아 있으면 그 축으로 다시 틀린다.
        """
        readme = _text("README.md")
        sites = list(re.finditer(r"injected_defect", readme))
        assert len(sites) >= 3, (
            f"채점자 비교 지점이 {len(sites)}곳뿐이다 - 대조가 공허하다"
        )
        offenders: list[str] = []
        for m in sites:
            window = readme[max(0, m.start() - 700) : m.end() + 700]
            if "ALL" not in window:
                offenders.append(window[650:790].replace("\n", " ").strip())
        assert not offenders, (
            "룰 선택을 밝히지 않은 채점자 비교가 있다 - "
            "`S` 로 좁히면 두 정의가 일치해 편차가 사라진다:\n  "
            + "\n  ".join(f"...{o}..." for o in offenders)
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

    def test_documented_flags_exist(self) -> None:
        """🔴 문서에 적힌 플래그가 **실재해야** 한다.

        [실측] README 사용법이 `report --run <id> --by-oracle` 을 적고 있었다.
        그런 플래그는 없다 - 설계 초안에 있던 표면이 그대로 남아 있었고,
        명령이 실재하는지만 보던 기존 검사는 그걸 놓쳤다.

        베껴 쓴 사람이 바로 막히는 종류의 거짓말이라 특히 나쁘다.
        """
        parser = build_parser()
        subs = next(
            a
            for a in parser._actions
            if isinstance(a, argparse._SubParsersAction)
        )
        real = {
            name: {
                opt
                for action in sub._actions
                for opt in action.option_strings
                if opt.startswith("--")
            }
            for name, sub in subs.choices.items()
        }

        bad: list[str] = []
        for cmd, flags in re.findall(
            r"codeproof (\w+)((?:\s+--?[\w-]+(?:[ =][^\s]+)?)*)", _all_docs()
        ):
            if cmd not in real:
                continue
            for flag in re.findall(r"(--[\w-]+)", flags):
                if flag not in real[cmd]:
                    bad.append(f"codeproof {cmd} {flag}")
        assert not bad, f"문서에만 있는 플래그: {sorted(set(bad))}"

    def test_every_advertised_command_actually_runs(self) -> None:
        """🔴 `--help` 에 올린 명령은 **전부 동작한다.**

        전에는 `review` 가 `--help` 에 있으면서 `[미구현]` 을 냈다. 쓰는
        사람이 속는다. 안 되는 것은 광고하지 않는 쪽으로 바꿨고, 그 상태를
        여기서 고정한다.
        """
        assert self._real_commands() == set(_COMMANDS), (
            "--help 에 있는데 핸들러가 없는 명령이 있다 - "
            "구현하든지 파서에서 빼든지 한다"
        )


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
