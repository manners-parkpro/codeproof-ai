"""D144 변이 - 쓰는 단계 10개 · 쓰는 단계 점검 16개 · 독립 검토 3개 (약화 19 · 안전 10 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

_CHECK = "        if not (0 <= self.row < ROWS and 0 <= self.col < COLS):\n"
_RAISE = '            raise ValueError(f"판 밖의 칸: {self.row}, {self.col}")\n'
_INDEX = "    return cell.row * COLS + cell.col\n"

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[확인] row 만 (twin)": [(_CHECK, "        if not 0 <= self.row < ROWS:\n")],
    "[확인] col 만": [(_CHECK, "        if not 0 <= self.col < COLS:\n")],
    "[경계] col 끝을 포함": [(_CHECK, "        if not (0 <= self.row < ROWS and 0 <= self.col <= COLS):\n")],
    "[경계] 음수 col 을 받음": [(_CHECK, "        if not (0 <= self.row < ROWS and self.col < COLS):\n")],
    "[번호] ROWS 를 곱함": [(_INDEX, "    return cell.row * ROWS + cell.col\n")],
    "[고정] frozen 이 아님 - 만든 뒤 좌표를 판 밖으로 옮길 수 있음": [
        ("@dataclasses.dataclass(frozen=True, slots=True)\n", "@dataclasses.dataclass(slots=True)\n"),
    ],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화
    '[번호] COLS 를 나눗셈으로 - index 가 float 를 돌려줌': [('COLS = 9\n', 'COLS = 54 / ROWS\n')],
    '[확인] init=False 와 손으로 쓴 __init__ 에서 확인 - dataclass 로 꾸민 하위 클래스는 확인을 건너뜀': [('@dataclasses.dataclass(frozen=True, slots=True)\n', '@dataclasses.dataclass(frozen=True, slots=True, init=False)\n'), ('    def __post_init__(self) -> None:\n        if isinstance(self.row, bool) or isinstance(self.col, bool):\n            raise TypeError(f"좌표는 bool 이 아닌 정수다: {self.row!r}, {self.col!r}")\n        if not (0 <= self.row < ROWS and 0 <= self.col < COLS):\n            raise ValueError(f"판 밖의 칸: {self.row}, {self.col}")\n', '    def __init__(self, row: int, col: int) -> None:\n        if isinstance(row, bool) or isinstance(col, bool):\n            raise TypeError(f"좌표는 bool 이 아닌 정수다: {row!r}, {col!r}")\n        if not (0 <= row < ROWS and 0 <= col < COLS):\n            raise ValueError(f"판 밖의 칸: {row}, {col}")\n        object.__setattr__(self, "row", row)\n        object.__setattr__(self, "col", col)\n')],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    '[하위 클래스] Cell 자신일 때만 확인': [('        if not (0 <= self.row < ROWS and 0 <= self.col < COLS):\n', '        if type(self) is Cell and not (0 <= self.row < ROWS and 0 <= self.col < COLS):\n')],
    '[번호] index 가 type(...) is int 로 하위 타입 좌표를 떨어뜨림': [('    return cell.row * COLS + cell.col\n', '    if type(cell.row) is not int or type(cell.col) is not int:\n        raise TypeError(cell)\n    return cell.row * COLS + cell.col\n')],
    '[경계] 한 바이트로 잘라 확인 - 256 의 배수만큼 큰 좌표를 받음': [('        if not (0 <= self.row < ROWS and 0 <= self.col < COLS):\n', '        if not (0 <= self.row & 0xFF < ROWS and 0 <= self.col & 0xFF < COLS):\n')],
    '[바꾸기] 위치 인자로 만들 때만 확인 - 키워드로 다시 만드는 replace 는 건너뜀': [('    def __post_init__(self) -> None:\n        if isinstance(self.row, bool) or isinstance(self.col, bool):\n            raise TypeError(f"좌표는 bool 이 아닌 정수다: {self.row!r}, {self.col!r}")\n        if not (0 <= self.row < ROWS and 0 <= self.col < COLS):\n            raise ValueError(f"판 밖의 칸: {self.row}, {self.col}")\n', '    def __new__(cls, *args: int, **kwargs: int) -> "Cell":\n        if args and (any(isinstance(a, bool) for a in args) or not (0 <= args[0] < ROWS and 0 <= args[1] < COLS)):\n            raise ValueError(f"판 밖의 칸: {args}")\n        return object.__new__(cls)\n')],
    '[번호] 1 부터 셈': [('    return cell.row * COLS + cell.col\n', '    return cell.row * COLS + cell.col + 1\n')],
    '[형] type(...) is int 가 아니면 거절 - IntEnum 좌표로는 칸을 만들 수 없음': [('        if not (0 <= self.row < ROWS and 0 <= self.col < COLS):\n', '        if type(self.row) is not int or type(self.col) is not int:\n            raise TypeError((self.row, self.col))\n        if not (0 <= self.row < ROWS and 0 <= self.col < COLS):\n')],
    '[bool] bool 거절 없음 (점검 앞의 decoy)': [('        if isinstance(self.row, bool) or isinstance(self.col, bool):\n            raise TypeError(f"좌표는 bool 이 아닌 정수다: {self.row!r}, {self.col!r}")\n', '')],
    '[bool] row 의 bool 만 거절': [('        if isinstance(self.row, bool) or isinstance(self.col, bool):\n', '        if isinstance(self.row, bool):\n')],
    '[bool] True 만 거절 - False 좌표는 0 으로 받음': [('        if isinstance(self.row, bool) or isinstance(self.col, bool):\n', '        if self.row is True or self.col is True:\n')],
    # 독립 검토 - 원래 증명이 놓치던 약화
    '[-O] 범위 확인을 assert 로 - python -O 에서는 판 밖의 칸이 만들어짐': [('        if not (0 <= self.row < ROWS and 0 <= self.col < COLS):\n            raise ValueError(f"판 밖의 칸: {self.row}, {self.col}")\n', '        assert 0 <= self.row < ROWS and 0 <= self.col < COLS, f"판 밖의 칸: {self.row}, {self.col}"\n')],
    '[-O] bool 확인을 assert 로': [('        if isinstance(self.row, bool) or isinstance(self.col, bool):\n            raise TypeError(f"좌표는 bool 이 아닌 정수다: {self.row!r}, {self.col!r}")\n', '        assert not (isinstance(self.row, bool) or isinstance(self.col, bool)), "좌표는 bool 이 아닌 정수다"\n')],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "range 에 드는지로 확인 (안전)": [(_CHECK, "        if self.row not in range(ROWS) or self.col not in range(COLS):\n")],
    "IndexError 로 거절 (안전)": [(_RAISE, '            raise IndexError((self.row, self.col))\n')],
    "index 에서도 다시 확인 (안전)": [(_INDEX, "    if not (0 <= cell.col < COLS and 0 <= cell.row < ROWS):\n        raise ValueError(cell)\n" + _INDEX)],
    "둘을 따로 확인 (안전)": [
        (_CHECK + _RAISE, "        if not 0 <= self.row < ROWS:\n" + _RAISE + "        if not 0 <= self.col < COLS:\n" + _RAISE),
    ],
    # 쓰는 단계 점검 - 주장이 정하지 않은 것을 바꾼 안전한 변형
    '[정규화] operator.index 로 int 로 바꿔 담음 (안전)': [('import dataclasses\n', 'import dataclasses\nimport operator\n'), ('            raise ValueError(f"판 밖의 칸: {self.row}, {self.col}")\n', '            raise ValueError(f"판 밖의 칸: {self.row}, {self.col}")\n        object.__setattr__(self, "row", operator.index(self.row))\n        object.__setattr__(self, "col", operator.index(self.col))\n')],
    '[번호] (row, col) 표에서 찾음 (안전)': [('ROWS = 6\nCOLS = 9\n', 'ROWS = 6\nCOLS = 9\n_NUMBER = {(r, c): r * COLS + c for r in range(ROWS) for c in range(COLS)}\n'), ('    return cell.row * COLS + cell.col\n', '    return _NUMBER[cell.row, cell.col]\n')],
    '[slots] slots 없이 frozen 만 (안전)': [('@dataclasses.dataclass(frozen=True, slots=True)\n', '@dataclasses.dataclass(frozen=True)\n')],
    '[bool] bool 거절을 ValueError 로 (안전)': [('            raise TypeError(f"좌표는 bool 이 아닌 정수다: {self.row!r}, {self.col!r}")\n', '            raise ValueError("bool 좌표")\n')],
    '[bool] type(x) is bool 로 확인 (안전)': [('        if isinstance(self.row, bool) or isinstance(self.col, bool):\n', '        if type(self.row) is bool or type(self.col) is bool:\n')],
    # 독립 검토 - 주장이 정하지 않은 것을 바꾼 안전한 변형
    'dataclass 가 아닌 __slots__ 클래스로 쓴 Cell (안전 - 주장은 Cell 의 내부 표현을 정하지 않는다)': [('@dataclasses.dataclass(frozen=True, slots=True)\nclass Cell:\n    row: int\n    col: int\n\n    def __post_init__(self) -> None:\n        if isinstance(self.row, bool) or isinstance(self.col, bool):\n            raise TypeError(f"좌표는 bool 이 아닌 정수다: {self.row!r}, {self.col!r}")\n        if not (0 <= self.row < ROWS and 0 <= self.col < COLS):\n            raise ValueError(f"판 밖의 칸: {self.row}, {self.col}")\n', 'class Cell:\n    __slots__ = ("_row", "_col")\n\n    def __init__(self, row: int, col: int) -> None:\n        if isinstance(row, bool) or isinstance(col, bool):\n            raise TypeError(f"좌표는 bool 이 아닌 정수다: {row!r}, {col!r}")\n        if not (0 <= row < ROWS and 0 <= col < COLS):\n            raise ValueError(f"판 밖의 칸: {row}, {col}")\n        object.__setattr__(self, "_row", row)\n        object.__setattr__(self, "_col", col)\n\n    def __setattr__(self, name: str, value: object) -> None:\n        raise AttributeError("Cell 은 바꿀 수 없다")\n\n    @property\n    def row(self) -> int:\n        return self._row\n\n    @property\n    def col(self) -> int:\n        return self._col\n'), ('import dataclasses\n\n', '')],
}

RACY: dict[str, list[tuple[str, str]]] = {}
