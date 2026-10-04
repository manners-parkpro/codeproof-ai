"""D127 반증 - 돌려준 필터를 RFC 4515 문법으로 직접 읽어, 구조가 바뀌거나 uid 값이 달라지는 입력을 찾는다."""

from __future__ import annotations

from types import ModuleType

_HEX = "0123456789abcdefABCDEF"


class _Bad(Exception):
    """RFC 4515 로 읽히지 않는다."""


def _value(raw: str) -> tuple[str, str]:
    """assertion value 를 읽는다 - 이스케이프 안 된 * 가 있으면 ("sub", 원문), 아니면 ("eq", UTF-8 로 되살린 값)."""
    out = bytearray()
    i = 0
    wildcard = False
    while i < len(raw):
        ch = raw[i]
        if ch == "\\":
            pair = raw[i + 1 : i + 3]
            if len(pair) != 2 or any(c not in _HEX for c in pair):
                raise _Bad
            out.append(int(pair, 16))
            i += 3
            continue
        if ch in "()\x00":
            raise _Bad
        if ch == "*":
            wildcard = True
        out += ch.encode("utf-8", "surrogatepass")
        i += 1
    if wildcard:
        return "sub", raw
    try:
        return "eq", out.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _Bad from exc


def _parse(text: str) -> object:
    """filter = "(" ( "&" filterlist / "|" filterlist / "!" filter / attr "=" value ) ")" - 그 밖의 비교 종류는 _Bad."""
    pos = 0

    def take(ch: str) -> None:
        nonlocal pos
        if pos >= len(text) or text[pos] != ch:
            raise _Bad
        pos += 1

    def one() -> object:
        nonlocal pos
        take("(")
        if pos >= len(text):
            raise _Bad
        if text[pos] in "&|":
            op = text[pos]
            pos += 1
            items = []
            while pos < len(text) and text[pos] == "(":
                items.append(one())
            take(")")
            return (op, tuple(items))
        if text[pos] == "!":
            pos += 1
            inner = one()
            take(")")
            return ("!", inner)
        start = pos
        while pos < len(text) and text[pos] not in "=~<>:()":
            pos += 1
        attr = text[start:pos]
        take("=")
        start = pos
        while pos < len(text) and text[pos] != ")":
            if text[pos] == "(":
                raise _Bad
            pos += 1
        raw = text[start:pos]
        take(")")
        kind, value = _value(raw)
        # RFC 4512 §2.5 - 속성 이름은 대소문자를 가리지 않는다. objectClass 의 값(descr)도 그렇다 (§1.4 · 독립 검토)
        attr = attr.lower()
        return (kind, attr, value.lower() if attr == "objectclass" else value)

    tree = one()
    if pos != len(text):
        raise _Bad
    return tree


class _Uid(str):
    """메서드를 재정의하지 않은 str 하위 클래스 - 위협 모델 안이다."""


# str.split() 이 나누는 공백 29자 전부 - 정리는 이 글자들을 한 칸 공백으로 접는다
_SPACES = "\x09\x0a\x0b\x0c\x0d\x1c\x1d\x1e\x1f\x20\x85\xa0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000"
_ACCEPTED: list[str] = [
    "kim", "", "  kim   lee  ", "tab\tand\nnewline", "nbsp\xa0x", "*", "a*b", "(", ")", "\\", "\x00", "x)(uid=*",
    "*)(|(uid=*))", "kim)(objectClass=*", "\\2a", "\\5c2a", "a=b", "~=x", ">=", "uid=root", "é", "김철수", "😀",
    "a" * 256, "김" * 85, _Uid("sub*class"), "\\\\*\\(", "\x00\x00*",
    # 🔴 이스케이프로 256바이트를 넘게 길어져도 받는다 - 길이는 원문으로 잰다 (쓰는 단계 점검)
    "*" * 86, "(" * 256, "\\" * 200,
    # 🔴 유니코드 공백 · 정규화로 바뀌는 글자 - 정리는 split 그대로, 그 밖은 글자 그대로 (쓰는 단계 점검)
    f"a{_SPACES}b", "a\u3000b", "a\x1cb\x1fc", "ｋｉｍ", "e\u0301", "a\u200bb", "\ufeffkim", "ﬁ",
]
# 🔴 정리하면 256바이트가 되는 257바이트 원문도 거절한다 - 길이는 정리 전에 잰다 (쓰는 단계 점검)
# 🔴 서로게이트는 구간 전체 - 두 끝만 치면 surrogateescape 로 재는 판(U+DC80~U+DCFF 를 받음)이 지나간다 (독립 검토)
_REJECTED: list[str] = [*(chr(c) for c in range(0xD800, 0xE000)), "x\udfff", "a\udcff", "a" * 257, "김" * 86, "😀" * 65, "a" * 256 + " ", " " + "김" * 85 + " "]


def attack(mod: ModuleType) -> bool:
    """거절해야 할 uid 를 받거나, 받은 uid 로 만든 필터가 (&(objectClass=person)(uid=<정리한 uid>)) 로 읽히지 않으면 True.

    🔴 필터를 문자열로 견주지 않고 문법으로 읽는다 - 대문자 16진수나 비 ASCII 의 바이트 이스케이프 같은 안전한 표기가 지나가게.
    🔴 \\\\ 를 * 보다 늦게 바꾸는 이중 이스케이프는 값이 달라지는 것으로 잡는다 - 구조만 보면 지나간다.
    🔴 길이는 문자가 아니라 UTF-8 바이트로 잰다 - 「김」 86자는 86문자지만 258바이트다.
    🔴 & 안 두 비교의 순서는 묻지 않는다 - RFC 4511 의 and 는 순서 없는 집합이고 주장도 순서를 정하지 않는다.
    🔴 속성 이름과 objectClass 값의 대소문자도 묻지 않는다 - RFC 4512 가 가리지 않는다 (독립 검토).

    decoy 는 _escape 가 \\ · * · ( · ) · NUL 을 \\XX 로 바꾼다.
    twin 은 공백만 정리해 * 가 와일드카드로, 괄호가 필터 구문으로 읽힌다.
    """
    for uid in _REJECTED:
        try:
            mod.user_filter(uid)
        except Exception:  # noqa: BLE001, S112 - 거절 방식은 묻지 않는다
            continue
        return True
    for uid in _ACCEPTED:
        want = ("&", sorted([("eq", "objectclass", "person"), ("eq", "uid", " ".join(str(uid).split()))]))
        try:
            text = mod.user_filter(uid)
        except Exception:  # noqa: BLE001 - 받아야 할 uid 를 어떤 예외로든 거절하면 깨진 것이다
            return True
        try:
            got = _parse(text)
        except _Bad:
            return True
        if not (isinstance(got, tuple) and got[0] == "&" and (got[0], sorted(got[1])) == want):
            return True
    return False
