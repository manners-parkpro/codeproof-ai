"""D032 반증 - 수식으로 시작하는 칸이 CSV 로 다시 읽혀 살아남는지 본다."""

from __future__ import annotations

import csv
import io
from types import ModuleType

_DANGER = ("=", "+", "-", "@", "\t", "\r")  # 🔴 모듈의 _DANGEROUS 가 아니라 증명이 정한다
_Q = '"'
_PAYLOADS = (
    "=cmd|'/c calc'!A1", "+1+1", "-2+3", "@SUM(A1:A9)", "\tlead", "\rlead",
    "safe,=1+1", "a\n=1+1", "a\r=1+1", "x" + _Q + "y,=1", "Smith, John", "=a," + _Q + "b" + _Q,
    _Q + "=1+1" + _Q, _Q + "=1+1",  # 큰따옴표만 든 값
)


def _cells(line: str) -> list[str]:
    return [c for r in csv.reader(io.StringIO(line, newline="")) for c in r]


def attack(mod: ModuleType) -> bool:
    """row 가 만든 줄을 쉼표 CSV 로 다시 읽었을 때 위험 글자로 시작하는 칸이 있는가.

    decoy 는 neutralize_cell 이 앞에 작은따옴표를 붙이고 쉼표 · 큰따옴표 · 줄바꿈이 든 값을 감싼다. twin 은 감싸기만 한다.
    🔴 위험 글자는 모듈의 _DANGEROUS 가 아니라 증명이 정한다 - 모듈 것을 쓰면 그 집합을 줄인 약화가 기준까지 줄여 지나갔다.
       여러 칸 행을 친다 - 첫 칸만 중화하는 약화가 보인다. 평범한 값은 다시 읽은 칸으로 본다 - 직렬화 문자열을 고정하면
       모든 칸을 감싸는 안전한 변형을 거절했다 (독립 검토).
    """
    rows = [[p] for p in _PAYLOADS] + [["a", p] for p in _PAYLOADS] + [[p, p] for p in _PAYLOADS]
    for values in rows:
        try:
            line = mod.row(values)
        except Exception:  # noqa: BLE001 - 거절하면 만든 줄이 없다 - 주장은 거절 방식을 정하지 않는다
            continue
        cells = _cells(line)
        if len(cells) != len(values) or any(c.startswith(_DANGER) for c in cells):
            return True
    return _cells(mod.row(["a", "b"])) != ["a", "b"]  # 평범한 값은 다시 읽으면 그대로다
