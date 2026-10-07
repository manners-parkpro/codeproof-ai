"""쌍마다 실린 변이로 증명을 다시 깨 본다 (G3a1 · DESIGN §3.5).

🔴 run_proof 는 twin 하나만 친다 - twin 은 약화 하나일 뿐이다.
   쓰는 단계와 검토가 찾은 약화 · 안전한 변형을 저장소에 싣고 여기서 돌리면,
   증명을 고칠 때 전에 잡던 약화를 놓치거나 주장 밖을 묻게 되는 것이 바로 보인다.
   [실측] 4라운드에 race_window 와 증명 여섯을 고친 뒤 scratch 변이를 손으로
   다시 돌렸고, 그때 경쟁 회귀 스크립트의 glob 이 D102 를 조용히 빠뜨렸다.

경쟁에 기대는 약화(RACY)는 한 번 돌리면 드물게 놓치므로 여기서는 치환만 확인한다 -
여러 번 재는 것은 `codeproof decoy mutants` 다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from codeproof_ai.corpus.decoy import pair_dirs
from codeproof_ai.corpus.mutants import (
    Mutant,
    MutantError,
    apply,
    breaks,
    load_mutants,
    mutant_alias,
)
from tests.corpora import CORPORA, DECOYS

PAIRS = [p for root in CORPORA for p in pair_dirs(root)]
WITH_MUTANTS = [p for p in PAIRS if (p / "mutants.py").is_file()]

# 3라운드부터 변이를 싣는다 - 1·2라운드 변이는 남아 있지 않다 (mutants.py 머리말).
# 다른 코퍼스(DESIGN §7.10d)는 쌍마다 처음부터 싣는다.
FIRST_PAIR_WITH_MUTANTS = "D089"


def _needs_both_directions(pair: Path) -> bool:
    return pair.parent != DECOYS or pair.name.split("-")[0] >= FIRST_PAIR_WITH_MUTANTS


def _ids(paths: list[Path]) -> list[str]:
    return [p.name.split("-")[0] for p in paths]


class TestNewPairsCarryMutants:
    def test_pairs_from_round_three_on_have_both_directions(self) -> None:
        """🔴 약화만 쌓으면 증명이 주장 대신 구현을 묻는다 -
        안전한 변형도 하나 이상 싣는다 (§3.5 반대 방향)."""
        missing = []
        for pair in PAIRS:
            if not _needs_both_directions(pair):
                continue
            mutants = load_mutants(pair)
            if not any(m.expect_broken for m in mutants):
                missing.append(f"{pair.name}: 약화 변이가 없다")
            if not any(not m.expect_broken for m in mutants):
                missing.append(f"{pair.name}: 안전한 변형이 없다")
        assert not missing, "\n".join(missing)

    def test_the_cutoff_is_not_vacuous(self) -> None:
        """기준 쌍 뒤로 쌍이 하나도 없으면 위 검사는 아무것도 보지 않는다."""
        assert any(p.name.split("-")[0] >= FIRST_PAIR_WITH_MUTANTS for p in WITH_MUTANTS)


class TestStoredMutantsStillHold:
    @pytest.mark.parametrize("pair", WITH_MUTANTS, ids=_ids(WITH_MUTANTS))
    def test_weakenings_break_and_safe_variants_pass(self, pair: Path, tmp_path: Path) -> None:
        source = (pair / "decoy.py").read_text(encoding="utf-8")
        wrong = []
        for i, mutant in enumerate(load_mutants(pair)):
            apply(source, mutant)  # 경쟁 변이도 치환은 걸려야 한다 - 낡으면 MutantError
            if mutant.racy:
                continue
            broke = breaks(pair, mutant, tmp_path, mutant_alias(pair, i))
            if broke != mutant.expect_broken:
                want = "깨져야" if mutant.expect_broken else "통과해야"
                wrong.append(f"「{mutant.label}」 는 {want} 하는데 attack 이 {broke}")
        assert not wrong, f"{pair.name}:\n  " + "\n  ".join(wrong)


class TestTheRulesOfTheFile:
    def test_aliases_keep_the_whole_pair_name(self) -> None:
        """🔴 앞 4글자로 자르면 XC001 과 XC002 가 한 별칭을 나눠 쓴다.

        변이 CLI 는 임시 폴더 하나를 모든 쌍이 같이 쓴다 (`mutant_alias`).
        """
        assert mutant_alias(Path("XC001-a"), 0, 0) != mutant_alias(Path("XC002-b"), 0, 0)

    def test_a_stale_replacement_is_an_error(self) -> None:
        """decoy 를 고친 뒤 빗나간 치환이 원본을 돌려 「통과」로 읽히면 안 된다."""
        mutant = Mutant("낡은 변이", True, False, (("없는 줄\n", "x\n"),))
        with pytest.raises(MutantError, match="0번"):
            apply("a = 1\n", mutant)

    def test_a_replacement_that_changes_nothing_is_an_error(self) -> None:
        mutant = Mutant("그대로", False, False, (("a = 1\n", "a = 1\n"),))
        with pytest.raises(MutantError, match="그대로"):
            apply("a = 1\n", mutant)

    def test_a_malformed_table_is_rejected(self, tmp_path: Path) -> None:
        pair = tmp_path / "D999-fake"
        pair.mkdir()
        (pair / "mutants.py").write_text('WEAKENED = {"x": [("a",)]}\n', encoding="utf-8")
        with pytest.raises(MutantError, match="문자열 쌍"):
            load_mutants(pair)

    def test_a_pair_without_the_file_has_no_mutants(self, tmp_path: Path) -> None:
        assert load_mutants(tmp_path) == ()
