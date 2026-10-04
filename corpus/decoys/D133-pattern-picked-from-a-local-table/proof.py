"""D133 반증 - 주장 문장으로 쓴 글자 단위 판정기와 견준다. 경계마다 ASCII 128자 전부와 닮은 글자, 몸통의 모든 자리에 모든
숫자, 종류의 값은 하위 타입까지, 표에 없는 종류(정규식 꼴 · 대소문자 · 공백 · 닮은 글자 · 다른 이름)는 거절하는지 본다."""

from __future__ import annotations

import enum
from types import ModuleType

_DIG = "0123456789"
_ALNUM = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz" + _DIG
_FRAG = {"order": "ORD-12345678", "phone": "010-1234-5678", "postcode": "12345"}
_BODY = {"order": range(4, 12), "phone": (4, 5, 6, 7, 9, 10, 11, 12), "postcode": range(5)}
_LIT = {"order": (0, 1, 2, 3), "phone": (0, 1, 2, 3, 8), "postcode": ()}
# 닮은 글자 - 전각 숫자 · 다른 문자 체계의 숫자 · 위 첨자 · 동그라미 숫자 · 한글 · 전각 · 키릴 O · 전각 공백 · 서로게이트 · 그림 글자
_ODD = [chr(c) for c in (0xFF10, 0xFF19, 0x0663, 0x06F5, 0x0967, 0xB2, 0x2460, 0xAC00, 0xFF5A, 0xFF2F, 0x041E, 0x3000, 0xD800, 0x1F642)]


def _wide(s: str) -> str:
    return "".join(chr(ord(c) + 0xFEE0) for c in s)


class _Name(str):
    """메서드를 재정의하지 않은 str 하위 클래스 - 위협 모델 안이다."""


class _Kind(enum.StrEnum):
    ORDER = "order"
    PHONE = "phone"
    POSTCODE = "postcode"
    TEL = "tel"


class _Mix(str, enum.Enum):
    """표준 라이브러리가 __str__ 을 끼운 (str, Enum) 혼합형 - 재정의로 치지 않는다 (위협 모델)."""

    ORDER = "order"
    PHONE = "phone"
    POSTCODE = "postcode"
    ZIP = "zip"


def _digits(s: str, n: int) -> bool:
    return len(s) == n and all(c in _DIG for c in s)


def _end_at(kind: str, t: str, i: int) -> int:
    """주장의 패턴 - i 에서 시작하는 조각이 있으면 그 끝, 없으면 -1."""
    before = t[i - 1] if i > 0 else None
    if kind == "order":
        j = i + 12
        ok = t[i : i + 4] == "ORD-" and _digits(t[i + 4 : j], 8) and (before is None or before not in _ALNUM)
    elif kind == "phone":
        j = i + 13
        ok = (
            t[i : i + 4] == "010-" and _digits(t[i + 4 : i + 8], 4) and t[i + 8 : i + 9] == "-"
            and _digits(t[i + 9 : j], 4) and (before is None or before not in _DIG)
        )
    else:
        j = i + 5
        ok = _digits(t[i:j], 5) and (before is None or before not in _DIG)
    after = t[j] if j < len(t) else None
    return j if ok and (after is None or after not in _DIG) else -1


def _expected(kind: str, text: str) -> list[str]:
    """왼쪽부터 겹치지 않게 - 조각을 찾으면 그 끝에서 다시 찾는다."""
    t, out, i = str.__str__(text), [], 0
    while i < len(t):
        j = _end_at(kind, t, i)
        if j < 0:
            i += 1
        else:
            out.append(t[i:j])
            i = j
    return out


# (종류, 글, 기대) - 손으로 정한 행. 판정기를 검산하고, 그대로 탐침으로도 친다.
_CASES: list[tuple[str, str, list[str]]] = [
    ("order", "주문 ORD-12345678 확인, ORD-87654321요", ["ORD-12345678", "ORD-87654321"]),
    ("order", "xORD-12345678 1ORD-12345678 ORD-123456789 ORD-1234567 ord-12345678", []),
    ("order", "-ORD-12345678 가ORD-00000000 (ORD-11111111)", ["ORD-12345678", "ORD-00000000", "ORD-11111111"]),
    ("order", "ORD-1234567８ ORD-12345678ORD-87654321", ["ORD-12345678"]),
    ("phone", "연락처 010-1234-5678, 010-8765-4321번", ["010-1234-5678", "010-8765-4321"]),
    ("phone", "0010-1234-5678 010-1234-56789 010-123-4567 011-1234-5678 ０１０-1234-5678", []),
    ("phone", "a010-1234-5678x 010-0000-0000", ["010-1234-5678", "010-0000-0000"]),
    ("postcode", "우편 06236 서울 06236, 12345-67890", ["06236", "06236", "12345", "67890"]),
    ("postcode", "123456 1234 ١٢٣٤٥ 12٣45", []),
    ("postcode", "ab12345cd 99999", ["12345", "99999"]),
    ("postcode", "", []),
]


def _texts(kind: str) -> list[str]:
    f = _FRAG[kind]
    out = [f, "", f + f, f + " " + f, f * 3, "order phone postcode " + f, f + kind]
    for c in [chr(n) for n in range(128)] + _ODD:  # 경계마다 ASCII 128자 전부와 닮은 글자
        out += [c + f, f + c]
    for pos in _BODY[kind]:  # 몸통의 모든 자리에 모든 ASCII 숫자와 ASCII 아닌 숫자
        out += [f[:pos] + r + f[pos + 1 :] for r in [*_DIG, chr(0xFF10), chr(0x0663), "a"]]
    for pos in _LIT[kind]:  # 리터럴 자리마다 ASCII 128자 전부와 닮은 글자
        lit = [chr(n) for n in range(128)] + [chr(0xFF2F), chr(0x041E), chr(0xFF10), chr(0x2013)]
        out += [f[:pos] + r + f[pos + 1 :] for r in lit if r != f[pos]]
    for pos in range(len(f)):  # 자리마다 한 글자 빼고 · 하나 더한 글 - 개수 축
        out += [f[:pos] + f[pos + 1 :], f[:pos] + f[pos] + f[pos:]]
    out += [text for k, text, _want in _CASES if k == kind]
    return out + [_Name(t) for t in out[:20]]


# 표에 없는 종류 - 정규식 꼴 · 빈 글 · 대소문자 · 앞뒤 공백 · 줄바꿈 · 닮은 글자(키릴 р · 전각 · 폭 없는 글자) ·
# 패턴 글 자체 · 다른 이름(별칭)과 그 하위 타입 값
_UNKNOWN: list[str] = [
    ".*", "(a+)+$", "[0-9]{5}", "", "PHONE", "Phone", "phone ", " phone", "postcode\n", "order|.*",
    "рhone", "ORD-[0-9]{8}", "date", r"\d+", "phone\x00",
    _wide("phone"), _wide("ORDER"), _wide("postcode"), "phone" + chr(0x200B), chr(0xFEFF) + "phone",
    "zip", "tel", "mobile", "postal", _Name("tel"), _Kind.TEL, _Mix.ZIP,
]
# 표의 이름을 조금 바꾼 것 - 진부분 접두사 전부 · 뒤에 한 글자 · 글자 사이에 구분자
for _name in _FRAG:
    _UNKNOWN += [_name[:i] for i in range(1, len(_name))]
    _UNKNOWN += [_name + c for c in "s1_-."]
    _UNKNOWN += [_name[:i] + c + _name[i:] for i in range(1, len(_name)) for c in "_-"]


def attack(mod: ModuleType) -> bool:
    """표의 종류에서 주장과 다른 조각을 내거나, 표에 없는 종류를 받는가.

    🔴 기대는 주장 문장으로 쓴 판정기가 낸다 - 패턴을 베끼지 않는다. 판정기는 손으로 정한 행으로 먼저 검산한다.
    🔴 문자 클래스는 구간 전체를 친다 - 경계마다 ASCII 128자 전부 · 몸통의 모든 자리에 0~9 와 ASCII 아닌 숫자.
    🔴 종류의 값은 하위 타입이어도 같은 종류다 - str 하위 클래스 · StrEnum · (str, Enum) 혼합형. 글도 str 하위 클래스로 친다.
    🔴 거절 방식은 묻지 않는다 - 어떤 예외든 거절이다. 빈 목록을 돌려주는 것은 거절이 아니다.
    🔴 리터럴 자리('ORD-' · '010-' · 가운데 '-')도 ASCII 128자 전부를 친다 - 구분자를 문자 클래스로 넓힌 판은
       그 자리에 다른 글자가 와야 보인다. 표에 없는 종류에는 표의 이름의 접두사 · 뒤에 붙인 글자 · 사이에 넣은
       구분자도 넣는다 - 고유 접두사나 복수형을 받아 주는 판 (6라운드 검토).

    decoy 는 표에 없는 kind 를 거절하고 표의 리터럴 패턴만 findall 에 넘긴다.
    twin 은 표에 없는 kind 의 글을 그대로 정규식으로 써서 '.*' 에 조각을 돌려준다.
    """
    for kind, text, want in _CASES:
        if _expected(kind, text) != want:
            msg = f"판정기가 손 기대와 다르다: {kind} {text!r}"
            raise AssertionError(msg)
    for kind in _FRAG:
        forms = [kind, _Name(kind), *(k for k in _Kind if k == kind), *(k for k in _Mix if k == kind)]
        for text in _texts(kind):
            want = _expected(kind, text)
            for name in forms:
                try:
                    got = mod.extract(text, name)
                except Exception:  # noqa: BLE001 - 표의 종류를 거절하면 깨진 것이다
                    return True
                if list(got) != want:  # 주장은 컨테이너를 정하지 않는다 - 같은 조각을 같은 차례로
                    return True
    for kind in _UNKNOWN:
        try:
            mod.extract("ORD-12345678 010-1234-5678 06236 phone zip tel aaaaaaaaaaaa!", kind)
        except Exception:  # noqa: BLE001, S112 - 거절 방식은 묻지 않는다
            continue
        return True
    return False
