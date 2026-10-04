"""D032 반증 - 수식으로 실행될 셀이 나가는지 본다."""

from __future__ import annotations

import csv
import io
from types import ModuleType

_FORMULAS = (
    "=cmd|'/c calc'!A1",
    "+1+1",
    "-2+3",
    "@SUM(A1:A9)",
    "\tlead",
)


def attack(mod: ModuleType) -> bool:
    """위험 문자로 시작하는 셀이 중화되지 않고 나가는가.

    decoy 는 neutralize_cell 이 앞에 작은따옴표를 붙인다.
    twin 은 quote_cell 이라 따옴표로 감싸기만 하고 시작 문자는 그대로다.
    """
    for payload in _FORMULAS:
        cell = mod.row([payload])
        body = cell.strip('"')  # 감싸기만 한 경우를 벗겨 본다
        if body.startswith(mod._DANGEROUS):
            return True
    # 평범한 값이 망가지지 않았는지도 본다
    if mod.row(["a", "b"]) != "a,b":
        return True
    # 🔴 CSV 로 다시 읽은 칸을 본다 (교차 패밀리 감사) - 값 안의 쉼표 · 줄바꿈이 새 칸을 만들면
    #    중화한 첫 글자 뒤에서 위험 문자로 시작하는 칸이 생긴다
    for payload in ("safe,=1+1", "a\n=1+1", "a\r=1+1", 'x"y,=1', "Smith, John", '=a,"b"'):
        cells = [c for r in csv.reader(io.StringIO(mod.row([payload]), newline="")) for c in r]
        if len(cells) != 1 or cells[0].startswith(mod._DANGEROUS):
            return True
    return False
