"""D070 반증 - 정규식 메타문자가 패턴으로 살아나는지 본다."""

from __future__ import annotations

import re
from types import ModuleType

# (검색어, 본문, 검색어를 글자 그대로만 맞췄을 때의 결과)
_CASES = (
    (".", "a.b", "a[.]b"),
    ("a+", "aaa a+", "aaa [a+]"),
    ("(x|y)", "xy (x|y)", "xy [(x|y)]"),
    ("[", "a[b", "a[[]b"),
    # 손으로 짠 이스케이프가 빠뜨리기 쉬운 것 - 중괄호 수량자와 역슬래시 (독립 검토가 찾았다)
    ("a{2}", "aa a{2}", "aa [a{2}]"),
    ("\\d", "7 \\d", "7 [\\d]"),
)


def attack(mod: ModuleType) -> bool:
    """검색어가 리터럴 문자열이 아니라 패턴으로 해석되는가.

    🔴 파국적 역추적 입력은 돌리지 않는다 - 멈추면 반증이 끝나지 않는다. 대신 메타문자가 **뜻을
       갖는지**를 결과로 본다. 하나라도 패턴으로 살아나면 중첩 수량자도 같은 길로 들어온다.

    decoy 는 re.escape 가 전부 리터럴로 만든다. twin 은 검색어를 그대로 패턴으로 쓴다.
    """
    for term, text, literal in _CASES:
        try:
            got = mod.highlight(term, text)
        except re.error:
            return True  # 검색어가 패턴으로 컴파일됐다
        if got != literal:
            return True
    return False
