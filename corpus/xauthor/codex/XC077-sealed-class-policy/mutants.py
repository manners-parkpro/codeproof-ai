"""주장의 축별 변이 - 변경 경로와 입력 경계를 약화하고 계약 밖 표현은 안전하게 바꾼다."""

SETTER = '''    def __setattr__(cls, name: str, value: object) -> None:
        raise TypeError(name)'''

DELETER = '''    def __delattr__(cls, name: str) -> None:
        raise TypeError(name)'''


def permit_when(condition):
    return [(SETTER, f'''    def __setattr__(cls, name: str, value: object) -> None:
        if {condition}:
            type.__setattr__(cls, name, value)
            return
        raise TypeError(name)''')]


WEAKENED = {
    "가드 선택: 기본 메타클래스": [
        ("class LIMITS(metaclass=_Sealed):", "class LIMITS(metaclass=type):"),
    ],
    "대입 경로: setter 제거": [
        (SETTER, SETTER.replace("raise TypeError(name)", "type.__setattr__(cls, name, value)")),
    ],
    "최적화 실행: assert로만 막은 대입": [
        (SETTER, '''    def __setattr__(cls, name: str, value: object) -> None:
        assert False, name
        type.__setattr__(cls, name, value)'''),
    ],
    "삭제 경로: deleter 제거": [
        (DELETER, DELETER.replace("raise TypeError(name)", "type.__delattr__(cls, name)")),
    ],
    "두 번째 필드: 상한 대입 누락": permit_when('name == "max_workers"'),
    "두 번째 필드: 상한 삭제 누락": [
        (DELETER, '''    def __delattr__(cls, name: str) -> None:
        if name == "max_workers":
            type.__delattr__(cls, name)
            return
        raise TypeError(name)'''),
    ],
    "값의 크기: 거대한 정수 우회": permit_when("abs(value) > 10**100"),
    "값의 경계: 거짓인 정수 우회": permit_when("not value"),
    "표준 하위 타입: bool 우회": permit_when("type(value) is bool"),
    "표준 하위 타입: IntEnum 우회": [
        ("class _Sealed(type):", "from enum import IntEnum\n\n\nclass _Sealed(type):"),
        *permit_when("isinstance(value, IntEnum)"),
    ],
    "사용자 하위 타입: 정수 상속 우회": [
        ("class _Sealed(type):", "from enum import IntEnum\n\n\nclass _Sealed(type):"),
        *permit_when("type(value) not in (int, bool) and not isinstance(value, IntEnum)"),
    ],
    "초기 원본: 하한을 동적으로 읽음": [
        ("class _Sealed(type):", '''class _Sealed(type):
    @property
    def min_workers(cls):
        return BOOTSTRAP["min_workers"]
'''),
    ],
    "초기 원본: 상한을 동적으로 읽음": [
        ("class _Sealed(type):", '''class _Sealed(type):
    @property
    def max_workers(cls):
        return BOOTSTRAP["max_workers"]
'''),
    ],
    "클래스 사전: 쓰기를 전달하는 공개 뷰": [
        ("class _Sealed(type):", '''class _Namespace(dict):
    def __init__(self, owner):
        super().__init__(type.__dict__["__dict__"].__get__(owner))
        self.owner = owner

    def __setitem__(self, key, value):
        type.__setattr__(self.owner, key, value)
        super().__setitem__(key, value)


class _Sealed(type):
    @property
    def __dict__(cls):
        return _Namespace(cls)
'''),
    ],
    "인스턴스 생성: 전역 상한 재설정": [
        ("    __slots__ = ()", '''    __slots__ = ()

    def __init__(self):
        type.__setattr__(LIMITS, "max_workers", 0)
'''),
    ],
    "인스턴스 변경: 클래스에 전달": [
        ("    __slots__ = ()", '''    __slots__ = ()

    def __setattr__(self, name, value):
        type.__setattr__(type(self), name, value)
'''),
    ],
    "하위 클래스 생성: 부모 정책에 반영": [
        ("class _Sealed(type):", '''class _Sealed(type):
    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)
        if bases:
            type.__setattr__(bases[0], "max_workers", 999)
'''),
    ],
    "입력 하위 타입: bool 소비 누락": [
        ("def worker_count(backlog: int) -> int:", '''def worker_count(backlog: int) -> int:
    if type(backlog) is bool:
        return backlog'''),
    ],
    "입력 크기: 유한 float 변환": [
        ("max(LIMITS.min_workers, backlog)", "max(LIMITS.min_workers, float(backlog))"),
    ],
    "입력 경계: 내부 구간을 하나 밀기": [
        ("max(LIMITS.min_workers, backlog)", "max(LIMITS.min_workers, backlog + 1)"),
    ],
}

SAFE = {
    "거절 예외: AttributeError": [
        (SETTER, SETTER.replace("TypeError", "AttributeError")),
        (DELETER, DELETER.replace("TypeError", "AttributeError")),
    ],
    "거절 예외: RuntimeError": [
        (SETTER, SETTER.replace("TypeError", "RuntimeError")),
        (DELETER, DELETER.replace("TypeError", "RuntimeError")),
    ],
    "사전 표현: 수정 가능한 독립 복사본 노출": [
        ("class _Sealed(type):", '''class _Sealed(type):
    @property
    def __dict__(cls):
        return dict(type.__dict__["__dict__"].__get__(cls))
'''),
    ],
    "클래스 본문: 원본에서 한 번에 스냅샷": [
        ('''    min_workers = BOOTSTRAP["min_workers"]
    max_workers = BOOTSTRAP["max_workers"]''',
         '''    min_workers, max_workers = (BOOTSTRAP[key] for key in ("min_workers", "max_workers"))'''),
    ],
    "인스턴스 표현: 별도 속성 사전 허용": [
        ("    __slots__ = ()", '    __slots__ = ("__dict__",)'),
    ],
    "입력 계산: 분기로 같은 범위 제한": [
        ("    return min(LIMITS.max_workers, max(LIMITS.min_workers, backlog))", '''    if backlog < LIMITS.min_workers:
        return LIMITS.min_workers
    if backlog > LIMITS.max_workers:
        return LIMITS.max_workers
    return backlog'''),
    ],
}

RACY = {}
