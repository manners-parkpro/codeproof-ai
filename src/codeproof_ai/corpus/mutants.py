"""쌍마다 싣는 변이 - 증명이 그럴듯한 약화를 깨고 안전한 변형은 통과시키는지
다시 돌린다 (G3a1).

`corpus/decoys/DNNN-*/mutants.py` 는 세 사전을 둔다.
값은 decoy.py 에 거는 (old, new) 치환 목록이다.

    WEAKENED  증명이 깨야 하는 약화 (attack True)
    SAFE      증명이 통과시켜야 하는 변형 - 주장이 정하지 않은 것만
              바꿨다 (DESIGN §3.5 「반대 방향」)
    RACY      경쟁에 기대어야 잡히는 약화 - 한 번 돌리면 드물게 놓친다
              ([실측] D104 의 한 줄 이동이 겨루는 작업 200 에서 30번 중 1번).
              그래서 pytest 는 치환이 걸리는지만 보고,
              `codeproof decoy mutants` 가 여러 번 돌려 잰다

🔴 old 는 decoy.py 에 정확히 한 번 있어야 한다. decoy 를 고치면 변이도 고친다 -
   치환이 빗나간 변이가 원본 decoy 를 그대로 돌리면 「안전한 변형은 통과」로
   읽혀 공허하게 초록불이 된다.

[실측] 1·2라운드 변이는 세션 scratch 에 있다가 사라졌다 -
저장소에 없는 변이로 낸 [실측] 은 다시 돌릴 수 없다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from codeproof_ai.corpus.proof import any_attempt, load_attack, load_module

if TYPE_CHECKING:
    from pathlib import Path

MUTANTS_FILE = "mutants.py"

# (사전 이름, 증명이 깨야 하는가, 경쟁에 기대는가)
_TABLES = (("WEAKENED", True, False), ("SAFE", False, False), ("RACY", True, True))
_PAIR_ARITY = 2


class MutantError(ValueError):
    """mutants.py 가 규약을 어겼거나 치환이 낡았다."""


@dataclass(frozen=True, slots=True)
class Mutant:
    label: str
    expect_broken: bool
    racy: bool
    replacements: tuple[tuple[str, str], ...]


def load_mutants(pair_dir: Path) -> tuple[Mutant, ...]:
    """쌍의 mutants.py 를 읽는다. 파일이 없으면 빈 튜플이다."""
    path = pair_dir / MUTANTS_FILE
    if not path.is_file():
        return ()
    mod = load_module(path, f"_mutants_{pair_dir.name.replace('-', '_')}")
    found: list[Mutant] = []
    for table, broken, racy in _TABLES:
        entries = getattr(mod, table, {})
        if not isinstance(entries, dict):
            msg = f"{pair_dir.name}/{MUTANTS_FILE}: {table} 는 dict 다"
            raise MutantError(msg)
        for label, subs in entries.items():
            pairs = tuple(_replacement(pair_dir, label, s) for s in subs)
            if not pairs:
                msg = f"{pair_dir.name}: 「{label}」 에 치환이 없다"
                raise MutantError(msg)
            found.append(Mutant(str(label), broken, racy, pairs))
    labels = [m.label for m in found]
    if len(set(labels)) != len(labels):
        msg = f"{pair_dir.name}: 변이 이름이 겹친다"
        raise MutantError(msg)
    return tuple(found)


def _replacement(pair_dir: Path, label: object, sub: object) -> tuple[str, str]:
    if (
        isinstance(sub, tuple)
        and len(sub) == _PAIR_ARITY
        and all(isinstance(part, str) for part in sub)
    ):
        return sub[0], sub[1]
    msg = f"{pair_dir.name}: 「{label}」 의 치환은 (old, new) 문자열 쌍이다"
    raise MutantError(msg)


def apply(source: str, mutant: Mutant) -> str:
    """치환을 차례로 건다. 대상이 정확히 한 번이 아니거나 결과가 원본과 같으면 MutantError."""
    code = source
    for old, new in mutant.replacements:
        count = code.count(old)
        if count != 1:
            msg = (
                f"「{mutant.label}」: 치환 대상이 decoy 에 {count}번 있다 - "
                f"decoy 를 고쳤으면 변이도 고친다: {old!r}"
            )
            raise MutantError(msg)
        code = code.replace(old, new)
    if code == source:
        msg = f"「{mutant.label}」: 치환해도 decoy 가 그대로다"
        raise MutantError(msg)
    return code


def mutant_alias(pair_dir: Path, *serial: int) -> str:
    """`breaks` 에 넘길 별칭 - 쌍 이름 전체에 변이 · 회차 번호를 붙인다.

    🔴 쌍 이름을 앞 몇 글자로 자르지 않는다. 앞 4글자로 자르던 때는 `XC001`~`XC009` 가
       한 별칭(`XC00`)을 나눠 쓸 자리였다 - 변이 CLI 는 임시 폴더 하나를 모든 쌍이 같이
       써서, 다른 쌍이 같은 경로에 쓴 파일을 다시 읽게 된다.
    """
    return "_".join(["_mut", pair_dir.name.replace("-", "_"), *map(str, serial)])


def breaks(pair_dir: Path, mutant: Mutant, workdir: Path, alias: str) -> bool:
    """변이를 workdir 에 쓰고 그 쌍의 증명을 돌린다.

    규칙은 실행기와 같다 - 선언한 시도 횟수 · 예외는 깨짐.

    alias 는 호출마다 달라야 한다 (`mutant_alias`) - 같은 이름이면 앞서 읽은 모듈을 다시 쓸 수 있다.
    """
    attack, attempts = load_attack(pair_dir)
    source = (pair_dir / "decoy.py").read_text(encoding="utf-8")
    path = workdir / f"{alias}.py"
    path.write_text(apply(source, mutant), encoding="utf-8")
    return any_attempt(attack, path, alias, attempts)
