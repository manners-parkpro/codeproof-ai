"""문서와 코드의 일관성.

🔴 문서가 코드와 어긋나면 그게 곧 드리프트다. 사람이 눈으로 맞추면
   반드시 어긋나므로, **어긋날 수 있는 지점만** 기계로 잡는다.

이 테스트가 깨지면 문서를 고친다 - 테스트를 고치는 게 아니다.
"""

from __future__ import annotations

import argparse
import ast
import itertools
import re
import tomllib
from pathlib import Path
from typing import ClassVar

import pytest

from codeproof_ai.cli import _COMMANDS, build_parser, main
from codeproof_ai.corpus.decoy import TrapKind, pair_dirs
from codeproof_ai.corpus.plan import PLAN
from codeproof_ai.corpus.shape import GuardShape

ROOT = Path(__file__).resolve().parents[2]
MEASUREMENTS = ROOT / "docs" / "MEASUREMENTS.md"
DECOYS = ROOT / "corpus" / "decoys"
SRC_DECOY = ROOT / "src" / "codeproof_ai" / "corpus" / "decoy.py"
DOCS = {
    "README.md": ROOT / "README.md",
    "CLAUDE.md": ROOT / "CLAUDE.md",
    "docs/DESIGN.md": ROOT / "docs" / "DESIGN.md",
    # 🔴 검증 프로토콜도 여기 든다. 베껴 쓰는 사람이 바로 막히는 문서라
    #    낡은 명령·깨진 링크가 특히 나쁘다.
    "docs/VERIFY.md": ROOT / "docs" / "VERIFY.md",
    "docs/RESULTS.md": ROOT / "docs" / "RESULTS.md",
    "docs/AI-WORKFLOW.md": ROOT / "docs" / "AI-WORKFLOW.md",
}
PROSE = ("README.md", "docs/RESULTS.md", "docs/AI-WORKFLOW.md")
"""결과를 산문으로 옮겨 적는 문서 - README 는 안내판이고 자세한 판은 RESULTS 다.

🔴 아래 대조는 이 셋을 모두 본다. README 만 보면 결과를 옮긴 문서에서 같은 오류가 산다.
"""


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
    ⚠ 그 11/60 은 뒤에 twin 위의 관례 지적이었던 것으로 드러났다 (F4a 양성 쪽) - 지금은 둘 다
    0/60 이고, 같은 실행이 정의에 따라 「거의 다 놓쳤다」(P-B 54)와 「거꾸로 찾았다」(P-R 46)로
    갈린다. 그래서 여전히 **어느 정의인지 반드시 적는다.**
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
        # 🔴 헤드라인 절의 표에서만 읽는다 - [실측] 짝 판정 사다리 표를 더하자 행 가운데의
        #    `| \`provable_safety\` | 10 | 2 |` 와 맞아 정답을 「2」로 읽었다.
        headline = generated.split("## 채점 기준 편차", 1)[-1].split("\n## ", 1)[0]
        # | `provable_safety` | 0 | 7 | 231 | o |   ->   FP 는 세 번째 칸
        truth = {
            m.group("grader"): m.group("fp")
            for m in re.finditer(
                r"^\|\s*`(?P<grader>\w+)`\s*\|\s*\d+\s*\|\s*(?P<fp>\d+)\s*\|", headline, re.M
            )
        }
        assert truth, "생성물에서 편차 표를 읽지 못했다"
        assert len(truth) >= 2, f"채점자가 하나뿐이면 대조가 공허하다: {truth}"

        matched = 0
        wrong: list[str] = []
        for name in PROSE:
            for grader, fp in truth.items():
                for m in re.finditer(rf"^{grader}\s+\d+\s+(\d+)\s", _text(name), re.M):
                    matched += 1
                    if m.group(1) != fp:
                        wrong.append(f"{grader}: {name} {m.group(1)} vs 생성물 {fp}")
        # 🔴 산문 쪽 형식이 바뀌면 읽는 행이 0 이 되어 공허하게 통과한다 (독립 검토)
        assert matched >= len(truth), (
            f"산문에서 대조한 채점자 행이 {matched}개뿐이다 (생성물 {len(truth)}개) - "
            "형식이 바뀌었다"
        )
        assert not wrong, (
            "산문의 FP 수가 생성물과 다르다 - "
            "`uv run codeproof report` 를 보고 고친다:\n  " + "\n  ".join(wrong)
        )

    def test_the_selection_table_repeats_the_headline_run(self) -> None:
        """🔴 「룰 선택 손잡이」의 기본 선택 행은 헤드라인 표와 같은 실행이다 - FP 가 같아야 한다.

        [실측 · 독립 검토] 그림이 쓰는 `spread_of` 가 채점자 이름을 `.get(…, 0)` 으로 꺼낼 때
        이름이 어긋나면 표 · 그림이 「0 대 0 · 일치」가 됐는데 테스트 · `--check` 가 모두 통과했다.
        """
        generated = MEASUREMENTS.read_text(encoding="utf-8")
        select = re.search(r"select=((?:[A-Z]+,)*[A-Z]+)", generated)  # 다음 인자는 소문자다
        assert select, "생성물 머리에서 룰 선택을 못 읽었다"
        headline = generated.split("## 채점 기준 편차", 1)[-1].split("\n## ", 1)[0]
        fp = dict(re.findall(r"^\|\s*`(\w+)`\s*\|\s*\d+\s*\|\s*(\d+)\s*\|", headline, re.M))
        row = re.search(
            rf"^\|\s*`{re.escape(select[1])}`\s*\|\s*\d+\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|",
            generated,
            re.M,
        )
        assert row, f"「룰 선택 손잡이」에 `{select[1]}` 행이 없다"
        assert (row[1], row[2]) == (fp["provable_safety"], fp["injected_defect"])

    def test_rule_selection_numbers_match_the_generated_file(self) -> None:
        """🔴 룰 선택 표와 「N 대 M」 인용이 생성물의 「룰 선택 손잡이」와 같아야 한다.

        [실측] RESULTS 는 「표는 생성물에서 같은 계산으로 다시 나온다」고 적었지만 그것을 보는
        검사가 없었다 - README 첫 화면의 「17 대 777 — 45.7배」도. 위의 대조는 코드 블록의
        채점자 행만 읽는다.
        """
        row = (
            r"^\|\s*`(?P<sel>[A-Z][A-Z,]*)`\s*\|\s*(?P<n>\d+)\s*\|\s*(?P<safe>\d+)\s*\|"
            r"\s*(?P<inj>\d+)\s*\|\s*(?P<verdict>[^|\n]*?)\s*\|"
        )
        truth = {
            m["sel"]: m.groupdict()
            for m in re.finditer(row, MEASUREMENTS.read_text(encoding="utf-8"), re.M)
        }
        assert {"S", "ALL"} <= truth.keys(), f"생성물의 룰 선택 표를 못 읽었다: {sorted(truth)}"
        verdicts = {(t["safe"], t["inj"]): t["verdict"] for t in truth.values()}

        quoted = 0
        wrong: list[str] = []
        for name in PROSE:
            text = _text(name).replace("**", "")
            for m in re.finditer(row, text, re.M):
                quoted += 1
                if m.groupdict() != truth.get(m["sel"]):
                    wrong.append(f"{name}: 표 {m.groupdict()} vs 생성물 {truth.get(m['sel'])}")
            for m in re.finditer(r"(\d+) 대 (\d+)(?: — (\S+배))?", text):
                quoted += 1
                verdict = verdicts.get((m[1], m[2]))
                if verdict is None or m[3] not in (None, verdict):
                    wrong.append(f"{name}: 「{m[0]}」 - 생성물에 없는 조합이다")
        assert quoted >= 3, f"대조한 인용이 {quoted}곳뿐이다 - 대조가 공허하다"
        assert not wrong, (
            "산문의 룰 선택 숫자가 생성물과 다르다 - "
            "`uv run codeproof report` 를 보고 고친다:\n  " + "\n  ".join(wrong)
        )

    def test_pair_verdicts_match_the_generated_ladder(self) -> None:
        """🔴 산문의 짝 판정 수가 생성물의 「짝 판정 사다리」와 같아야 한다.

        [실측 · 독립 검토] 결과 3 의 표 · S 문장 · 결과 5 의 사다리는 손으로 옮긴 숫자였고, 바꿔도
        산문 가드가 전부 통과했다. 읽는 꼴 셋 - 결과 3 표 행(`ALL` · slack 0), 「구별 성공 a · 과잉
        b · 미탐지 c · 역전 d」(`S` · slack 0), `[매칭 민감도] … ruff SEL · GRADER` 코드 블록의 행.
        """
        rung = (
            r"^\|\s*`(?P<sel>[A-Z]+)`\s*\|\s*`(?P<grader>\w+)`\s*\|\s*(?P<slack>\d+)\s*\|"
            r"\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|"
        )
        truth = {
            (m["sel"], m["grader"], int(m["slack"])): m.groups()[3:]
            for m in re.finditer(rung, MEASUREMENTS.read_text(encoding="utf-8"), re.M)
        }
        assert ("ALL", "injected_defect", 10) in truth, "생성물의 짝 판정 사다리를 못 읽었다"

        row = (
            r"^\|\s*`(?P<grader>\w+)`[^|\n]*\|"
            r"\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*$"
        )
        sentence = r"구별 성공 (\d+) · 과잉 (\d+) · 미탐지 (\d+) · 역전 (\d+)"
        block = r"\[매칭 민감도\][^\n]*ruff (\w+) · (\w+)\]([^`]*)"
        line = r"^\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$"
        quoted = 0
        wrong: list[str] = []
        for name in PROSE:
            text = _text(name).replace("**", "")
            seen: list[tuple[tuple[str, str, int], tuple[str, ...]]] = [
                (("ALL", m["grader"], 0), m.groups()[1:]) for m in re.finditer(row, text, re.M)
            ]
            seen += [
                (("S", "provable_safety", 0), m.groups())
                for m in re.finditer(sentence, text)
            ]
            for b in re.finditer(block, text):
                sel, grader, body = b.groups()
                seen += [
                    ((sel, grader, int(m[1])), m.groups()[1:])
                    for m in re.finditer(line, body, re.M)
                ]
            quoted += len(seen)
            wrong += [f"{name}: {key} {got} vs 생성물 {truth.get(key)}"
                      for key, got in seen if truth.get(key) != got]
        assert quoted >= 6, f"대조한 인용이 {quoted}곳뿐이다 - 대조가 공허하다"
        assert not wrong, (
            "산문의 짝 판정 수가 생성물과 다르다 - "
            "`uv run codeproof report` 를 보고 고친다:\n  " + "\n  ".join(wrong)
        )

    def test_prose_does_not_quote_a_bare_discrimination_rate(self) -> None:
        """산문의 구별 성공 숫자는 **채점자 이름과 같은 문단**에 있어야 한다."""
        offenders: list[str] = []
        for name in PROSE:
            text = _text(name)
            for m in re.finditer(r"구별 성공[^\n]*?(\d+/\d+)", text):
                window = text[max(0, m.start() - 400) : m.end() + 400]
                named = any(
                    g in window
                    for g in ("provable_safety", "injected_defect", "채점 정의", "채점자")
                )
                if not named:
                    offenders.append(f"{name}: {m.group(0).strip()}")
        assert not offenders, (
            "채점자를 밝히지 않은 구별 성공률이 있다 - "
            f"정의마다 다른 숫자가 나온다: {offenders}"
        )

    def test_grader_comparisons_name_the_rule_selection(self) -> None:
        """🔴 편차는 (채점자 x **룰 선택**)의 성질이다 - 어느 선택인지 적는다.

        [실측] 검증 프로토콜(docs/VERIFY.md)을 쓰다가 발견했다. 헤드라인
        「정의만 바꿔도 FP 가 34배」는 `--ruff-select ALL` 에서만 성립한다.
        `S`(보안 룰) 로 좁히면 두 정의가 **정확히 일치해** 편차가 1.0배가 되고,
        짝 판정의 차이(P-B 54 · P-R 46)도 **똑같아져** 사라진다.

        편차의 정체가 「판정 불가로 둘 것을 오답으로 세느냐」이기 때문이다 -
        보안 룰은 전부 근거 범위 안의 결함 주장이라 이견이 생길 자리가 없다.

        이건 바로 위 테스트가 막는 오류의 **두 번째 축**이다. 거기서는
        「구별 성공률은 (리뷰어 x 채점자)」를 배웠는데, 같은 규율을 룰 선택에는
        적용하지 않고 있었다. 축이 하나 남아 있으면 그 축으로 다시 틀린다.
        """
        sites = [(name, m) for name in PROSE for m in re.finditer(r"injected_defect", _text(name))]
        assert len(sites) >= 3, (
            f"채점자 비교 지점이 {len(sites)}곳뿐이다 - 대조가 공허하다"
        )
        offenders: list[str] = []
        for name, m in sites:
            text = _text(name)
            window = text[max(0, m.start() - 700) : m.end() + 700]
            if "ALL" not in window:
                offenders.append(f"{name}: " + window[650:790].replace("\n", " ").strip())
        assert not offenders, (
            "룰 선택을 밝히지 않은 채점자 비교가 있다 - "
            "`S` 로 좁히면 두 정의가 일치해 편차가 사라진다:\n  "
            + "\n  ".join(f"...{o}..." for o in offenders)
        )


class TestCorpusCountIsCurrent:
    """decoy 수는 자주 바뀐다 - 문서가 따라가는지 본다."""

    def _actual(self) -> int:
        return len(pair_dirs(DECOYS))

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
            for d in pair_dirs(DECOYS)
        }
        unused = {t.value for t in TrapKind} - used
        assert not unused, f"decoy 가 없는 분류: {sorted(unused)}"

    def test_template_lists_every_kind(self) -> None:
        """🔴 [실측] 템플릿이 14종 중 10종만 적고 있었다.

        템플릿을 보고 쓰는 저자는 빠진 넷을 모른다 -
        codex 가 쓰는 쌍(DESIGN §7.10d)은 템플릿에서 시작한다.
        """
        text = (DECOYS / "_TEMPLATE" / "meta.toml").read_text(encoding="utf-8")
        listed = set(re.findall(r"^#\s+([a-z_]+)\s{2,}\S", text, re.MULTILINE))
        kinds = {t.value for t in TrapKind}
        assert listed == kinds, (
            f"빠진 분류 {sorted(kinds - listed)} · 없는 분류 {sorted(listed - kinds)}"
        )

    def test_documented_count_matches_enum(self) -> None:
        claims = {int(m) for m in re.findall(r"분류(?:표)?\s*(\d+)종", _all_docs())}
        if claims:
            assert len(list(TrapKind)) in claims, (
                f"TrapKind 는 {len(list(TrapKind))}종인데 문서는 {sorted(claims)}종"
            )


class TestExpansionPlanMatchesDesign:
    """🔴 DESIGN 의 칸별 표는 공개한 선언이고 `corpus/plan.py` 는 테스트가 쓰는 정본이다.

    편차를 한쪽에만 적으면 발표한 계획과 실제로 지킨 계획이 갈린다. 「현재」 값은
    시점 표기라 대조하지 않는다 - 목표만 본다.
    """

    COLUMNS: ClassVar[tuple[GuardShape, ...]] = (
        GuardShape.LOCAL, GuardShape.CALLER, GuardShape.CALLEE, GuardShape.MODULE,
    )

    @staticmethod
    def _target(cell: str) -> int:
        """`1→**3**` 는 3, `4` 는 4 - 화살표 왼쪽(현재)은 읽지 않는다."""
        m = re.fullmatch(r"(?:\d+→)?\**(\d+)\**", cell)
        assert m, f"칸을 읽지 못했다: {cell!r}"
        return int(m[1])

    def _written(self) -> dict[str, dict[str, int]]:
        after = _text("docs/DESIGN.md").split("칸별 목표", 1)[1].split("\n")[1:]
        table = itertools.dropwhile(lambda ln: not ln.startswith("|"), after)
        written: dict[str, dict[str, int]] = {}
        for row in itertools.takewhile(lambda ln: ln.startswith("|"), table):
            m = re.fullmatch(r"\| `([a-z_]+)` \|(.+)\|", row.strip())
            if m:
                cells = [c.strip() for c in m.group(2).split("|")][: len(self.COLUMNS)]
                written[m.group(1)] = {
                    shape.value: self._target(cell)
                    for shape, cell in zip(self.COLUMNS, cells, strict=True)
                    if cell != "—"
                }
        return written

    def test_design_table_targets_are_the_plan(self) -> None:
        plan = {k.value: {s.value: n for s, n in cells.items()} for k, cells in PLAN.items()}
        assert self._written() == plan, (
            "DESIGN §3.5 의 칸별 목표와 corpus/plan.py 가 다르다 - 편차는 둘을 같이 고친다"
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


class TestCountedStructuresMatchTheCode:
    """🔴 산문이 구조를 세면 반드시 낡는다 - 세는 일은 코드가 한다.

    [실측] 이 클래스의 두 검사는 각각 **실제로 틀린 숫자**를 잡고 태어났다.
    DESIGN 이 「층이 넷이다」 아래 다섯 줄 표를 달고 있었고, 검증 규칙 수는
    12 인데 13 이라고 적혀 있었다(V1·V8 이 없어 번호가 연속이 아니다).
    """

    KOREAN_COUNT: ClassVar[dict[str, int]] = {
        "둘": 2, "셋": 3, "넷": 4, "다섯": 5,
        "여섯": 6, "일곱": 7, "여덟": 8, "아홉": 9,
    }

    def test_counted_headings_match_their_table(self) -> None:
        """🔴 「층이 넷이다」 같은 제목의 수가 바로 아래 표와 맞아야 한다.

        [실측] DESIGN 이 「층이 넷이다」라고 써 놓고 **다섯 줄**짜리 표를 달고
        있었다. V13 을 추가하면서 제목을 안 고친 것이다. 같은 종류로 「12규칙」이
        13이 된 적도 있다 - **구조를 산문이 세면 반드시 낡는다.**

        패키지 트리 검사와 같은 원리다. 숫자를 손으로 적는 자리는 전부
        세어 주는 검사를 붙인다.
        """
        pattern = re.compile(
            r"####?\s*\S+이?\s*(" + "|".join(self.KOREAN_COUNT) + r")이다\s*\n+"
            r"((?:\|[^\n]*\n)+)"
        )
        checked = 0
        wrong: list[str] = []
        for name, path in DOCS.items():
            for m in pattern.finditer(path.read_text(encoding="utf-8")):
                claimed = self.KOREAN_COUNT[m.group(1)]
                rows = [r for r in m.group(2).strip().splitlines() if r.startswith("|")]
                # 헤더 + 구분선 두 줄을 뺀다
                actual = max(0, len(rows) - 2)
                checked += 1
                if claimed != actual:
                    wrong.append(f"{name}: 「{m.group(1)}이다」인데 표는 {actual}줄")
        assert checked, "세어야 할 제목을 하나도 못 찾았다 - 정규식이 낡았다"
        assert not wrong, "제목의 수가 표와 다르다:\n  " + "\n  ".join(wrong)

    def test_validator_rule_count_matches_the_code(self) -> None:
        """🔴 문서가 말하는 decoy 검증 규칙 수를 **코드에서 세어** 대조한다.

        [실측] 이걸 손으로 세다가 틀렸다. DESIGN 감사 때 `12규칙` 을 `13규칙` 으로
        "고쳤는데", **V1 과 V8 이 없으므로** V2~V13 은 11개다(+W2 = 12).
        번호가 연속이라고 가정한 것이 원인이다. 그때 README 는 12 라고 맞게
        적고 있었으므로 **문서끼리 어긋난 상태**가 됐는데 아무도 못 잡았다.

        구조를 산문이 세면 반드시 틀린다 - 세는 일은 코드가 한다.
        """
        tree = ast.parse(
            (SRC_DECOY).read_text(encoding="utf-8")
        )
        codes: set[str] = set()
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and node.args):
                continue
            if getattr(node.func, "id", "") != "Violation":
                continue
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                codes.add(first.value)
        assert len(codes) > 5, f"검증 규칙을 제대로 세지 못했다: {codes}"

        claimed: list[tuple[str, int]] = []
        for name, path in DOCS.items():
            text = path.read_text(encoding="utf-8")
            for m in re.finditer(r"(\d+)규칙|(?:규격|형식)\s*(\d+)종", text):
                claimed.append((name, int(m.group(1) or m.group(2))))
        assert claimed, "문서가 규칙 수를 하나도 말하지 않는다 - 대조가 공허하다"

        wrong = [f"{n}: {c}" for n, c in claimed if c != len(codes)]
        assert not wrong, (
            f"검증기는 {len(codes)}종({sorted(codes)})인데 문서는 다르게 말한다: "
            + ", ".join(wrong)
        )


class TestMeasuredClaimsAreLabelled:
    """🔴 실측값과 추정을 섞지 않는다 - 산문의 [실측] 표시 규율과 같은 원칙."""

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


class TestTheLandingPage:
    """docs/index.html - GitHub Pages 의 첫 페이지. 받은 사람이 파일로 열어도 같아야 한다.

    숫자는 페이지에 쓰지 않는다 - 그림(생성물)이 든다. 그래서 페이지는 손으로 쓰고 생성하지 않는다.
    """

    PAGE = ROOT / "docs" / "index.html"

    def test_its_relative_images_and_links_resolve(self) -> None:
        html = self.PAGE.read_text(encoding="utf-8")
        refs = re.findall(r'(?:src|href)="([^"#]+)"', html)
        # 스킴(https: · data: …)이 있으면 상대 경로가 아니다
        local = [r for r in refs if not re.match(r"[a-z][a-z0-9+.-]*:", r)]
        assert local, "상대 경로가 하나도 없다 - 대조가 공허하다"
        missing = [r for r in local if not (self.PAGE.parent / r).is_file()]
        assert not missing, f"페이지가 없는 파일을 가리킨다: {missing}"

    def test_it_loads_nothing_from_outside(self) -> None:
        """링크는 괜찮다 - 불러오는 자원(그림 · 스크립트 · 스타일)만 막는다."""
        html = self.PAGE.read_text(encoding="utf-8")
        assert not re.findall(r'src="https?://', html)
        assert "<script" not in html
        assert not re.findall(r'<link[^>]+href="https?://', html)
        # 손으로 쓰는 페이지에 가장 흔히 들어오는 바깥 자원 - 웹 폰트 (독립 검토)
        assert "@import" not in html
        assert not re.findall(r"url\(\s*['\"]?https?://", html)

    def test_its_prose_quotes_no_numbers(self) -> None:
        """숫자는 그림(생성물)이 든다.

        손으로 쓴 문장 · 캡션의 숫자는 코퍼스가 바뀌면 조용히 낡는다 (누락 점검).
        """
        page = self.PAGE.read_text(encoding="utf-8")
        html = re.sub(r"<(style|pre|code)\b.*?</\1>", "", page, flags=re.S)
        texts = re.findall(r"<(p|li|figcaption|h[1-6])\b[^>]*>(.*?)</\1>", html, re.S)
        assert len(texts) >= 5, "본문을 못 읽었다 - 대조가 공허하다"
        quoted = [t for _, t in texts if re.search(r"\d", re.sub(r"<[^>]+>", "", t))]
        assert not quoted, f"페이지 문장에 숫자가 있다: {quoted}"

    def test_its_repository_links_point_at_files_that_exist(self) -> None:
        """저장소 문서 링크(blob/main/…)는 바깥 주소라 위 검사가 보지 않는다.

        문서 이름이 바뀌면 페이지 링크가 조용히 깨진다 (독립 검토).
        """
        html = self.PAGE.read_text(encoding="utf-8")
        paths = re.findall(r"github\.com/manners-parkpro/codeproof-ai/blob/main/([^\"#]+)", html)
        assert paths, "저장소 문서 링크가 하나도 없다 - 대조가 공허하다"
        missing = [p for p in paths if not (ROOT / p).is_file()]
        assert not missing, f"페이지가 없는 저장소 파일을 가리킨다: {missing}"
