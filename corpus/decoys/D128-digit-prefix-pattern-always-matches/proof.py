"""D128 반증 - 숫자로 시작하지 않는 꼬리표 · 유니코드 숫자 · 줄바꿈 · 아주 긴 값으로 split_version 을 부른다."""

from __future__ import annotations

from types import ModuleType

_ASCII_DIGITS = "0123456789"


class _Tag(str):
    """메서드를 재정의하지 않은 str 하위 클래스 - 위협 모델 안이다."""


_TAGS: list[str] = [
    "", "1", "12rc1", "beta", "v1.2", "007", "1.2.3", "0", "00", "٣٤", "１２", "12\n3", "\n12", "12abc34", "-1", "+1",
    " 1", "1 ", "9" * 10_000, "x" * 10_000, "9" * 5000 + "x", "²³", "1\x00", "١2", _Tag("42b"), _Tag("rc"),
    # 🔴 쓰는 단계 점검 - 서로게이트 · 열 숫자 전부 · 대문자 · 분해 글자 · 1만 자를 넘는 숫자열
    "\ud800", "12\udfff", "0123456789", "35x68", "1RC1", "12Beta", "1e\u0301", "1\u00e9", "9" * 100_001,
    # 🔴 독립 검토 - 숫자 사이에 ASCII 128자 전부와 비 ASCII 구분자 몇 - 자릿수 구분자(_ · , · ')를 넣은 문자 클래스가 빠지지 않게
    *(f"1{chr(c)}2" for c in range(128)), *(f"1{c}2" for c in "\xa0\u066c\u2009\u202f\uff3f\uff0c"),
]


def _want(tag: str) -> str:
    head = []
    for ch in tag:
        if ch not in _ASCII_DIGITS:
            break
        head.append(ch)
    return "".join(head)


def attack(mod: ModuleType) -> bool:
    """split_version 이 어떤 꼬리표에서 예외를 내거나, head 가 맨 앞 ASCII 숫자 전부가 아니거나, 두 조각을 이어 꼬리표가 안 되면 True.

    🔴 숫자로 시작하지 않는 꼬리표(빈 문자열 포함)를 넣는다 - 패턴이 한 자 이상을 요구하면 match 가 None 이 된다.
    🔴 유니코드 숫자(٣ · １ · ²)를 넣는다 - \\d 로 넓히는 약화는 ASCII 가 아닌 숫자를 head 로 가져간다.
    🔴 0 으로 시작하는 꼬리표를 넣는다 - 앞의 0 을 지우는 약화가 지나가지 않게.

    decoy 는 _DIGITS 가 [0-9]* 라 위치 0 에서 빈 문자열에라도 맞는다.
    twin 은 [0-9]+ 라 숫자로 시작하지 않는 꼬리표에서 match 가 None 이고 .group() 이 AttributeError 를 낸다.
    """
    for tag in _TAGS:
        try:
            head, rest = mod.split_version(tag)
        except Exception:  # noqa: BLE001 - 어떤 꼬리표에도 예외 없이 돌려줘야 한다
            return True
        if head != _want(tag) or head + rest != tag:
            return True
    return False
