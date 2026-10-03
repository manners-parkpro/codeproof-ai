"""D085 반증 - 수식으로 실행될 칸을 내보내고 다시 읽는다."""

from __future__ import annotations

import csv
import io
from types import ModuleType

_DANGEROUS = (
    '=HYPERLINK("http://evil.example","open")',
    "+cmd|' /C calc'!A0",
    "-2+3",
    "@SUM(A1:A9)",
    "  =1+1",
    "\t=1+1",
    # 순수한 숫자가 아닌 - · + 시작 - 숫자 판정을 float() 나 [0-9]* 로 느슨하게 한 약화를 잡는다
    "-inf",
    "-nan",
    "-",
)
_PLAIN = ["hello", "-12", "+7", "3.5", "a=b"]


def attack(mod: ModuleType) -> bool:
    """내보낸 칸 중 수식 시작 글자로 시작하는 것이 있는가.

    decoy 는 공백 정리 뒤 _neutralize 가 작은따옴표를 붙인다.
    twin 은 공백 정리만 해서 수식이 그대로 나간다.
    """
    text = mod.export_rows([list(_DANGEROUS), list(_PLAIN)])
    rows = list(csv.reader(io.StringIO(text)))
    if len(rows) != 2 or len(rows[0]) != len(_DANGEROUS):
        return True
    if any(cell[:1] in ("=", "+", "-", "@") for cell in rows[0]):
        return True
    # 순수한 숫자와 평범한 글은 그대로 나가야 한다 - 「전부 따옴표」는 데이터를 망친다
    return rows[1] != _PLAIN
