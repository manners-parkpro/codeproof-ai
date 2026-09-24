"""D032 반증 - 수식으로 실행될 셀이 나가는지 본다."""

from __future__ import annotations

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
    return mod.row(["a", "b"]) != "a,b"
