"""D111 변이 - 쓰는 단계 10개 · 검토 2개 · 교차 3개 (약화 11 · 안전 4 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '[값으로 같음] 보통 클래스 (twin)': [
        ('@dataclass(frozen=True)\nclass Check:\n    student: str\n    session: int\n', 'class Check:\n    def __init__(self, student: str, session: int) -> None:\n        self.student = student\n        self.session = session\n'),
    ],
    '[값으로 같음] eq=False': [
        ('@dataclass(frozen=True)\n', '@dataclass(frozen=True, eq=False)\n'),
    ],
    '[해시] frozen 빠짐 (해시 불가)': [
        ('@dataclass(frozen=True)\n', '@dataclass\n'),
    ],
    '[시간을 두고] 받은 시각을 비교 필드로': [
        ('from dataclasses import dataclass\n', 'import time\nfrom dataclasses import dataclass, field\n'),
        ('    session: int\n', '    session: int\n    at: float = field(default_factory=time.monotonic)\n'),
    ],
    '[같은 값의 새 객체] 인자의 id 로 거름': [
        ('@dataclass(frozen=True)\nclass Check:\n    student: str\n    session: int\n', 'class Check:\n    def __init__(self, student: str, session: int) -> None:\n        self.student = student\n        self.session = session\n'),
        ('    _checks.add(Check(student, session))\n', '    key = (id(student), id(session))\n    if key not in _seen:\n        _seen[key] = Check(student, session)\n        _checks.add(_seen[key])\n'),
        ('_checks: set[Check] = set()\n', '_checks: set[Check] = set()\n_seen: dict[tuple[int, int], Check] = {}\n'),
        ('    return not isinstance(session, bool) and Check(student, session) in _checks\n', '    return any(c.student == student and c.session == session for c in _checks)\n'),
    ],
    '[모두 하나로] 회차를 비교에서 뺌': [
        ('from dataclasses import dataclass\n', 'from dataclasses import dataclass, field\n'),
        ('    session: int\n', '    session: int = field(compare=False)\n'),
    ],
    '[시간을 두고] 초 단위 시각을 비교 필드로': [
        ('from dataclasses import dataclass\n', 'import time\nfrom dataclasses import dataclass, field\n'),
        ('    session: int\n', '    session: int\n    at: int = field(default_factory=lambda: int(time.time()))\n'),
    ],
    '[검토] T1 초 단위 시각을 비교 필드로': [
        ('from dataclasses import dataclass\n', 'import time\nfrom dataclasses import dataclass, field\n'),
        ('    session: int\n', '    session: int\n    at: int = field(default_factory=lambda: int(time.time()))\n'),
    ],
    '[검토] T2 날짜를 비교 필드로': [
        ('from dataclasses import dataclass\n', 'import datetime\nfrom dataclasses import dataclass, field\n'),
        ('    session: int\n', '    session: int\n    on: datetime.date = field(default_factory=datetime.date.today)\n'),
    ],
    # 교차 패밀리 감사 - 주장에 bool 거절을 밝혔다
    "[bool] 회차의 bool 을 거절하지 않음": [
        ('    if isinstance(session, bool):\n        raise TypeError("회차에 참 · 거짓을 쓸 수 없다")\n', ""),
    ],
    "[bool] True 만 거절": [('    if isinstance(session, bool):\n', "    if session is True:\n")],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    'NamedTuple (안전)': [
        ('from dataclasses import dataclass\n', 'from typing import NamedTuple\n'),
        ('@dataclass(frozen=True)\nclass Check:\n    student: str\n    session: int\n', 'class Check(NamedTuple):\n    student: str\n    session: int\n'),
    ],
    'slots 를 더함 (안전)': [
        ('@dataclass(frozen=True)\n', '@dataclass(frozen=True, slots=True)\n'),
    ],
    'unsafe_hash (안전)': [
        ('@dataclass(frozen=True)\n', '@dataclass(unsafe_hash=True)\n'),
    ],
    "[bool] ValueError 로 거절 (안전)": [('        raise TypeError("회차에 참 · 거짓을 쓸 수 없다")\n', '        raise ValueError("회차에 참 · 거짓을 쓸 수 없다")\n')],
}

RACY: dict[str, list[tuple[str, str]]] = {}
