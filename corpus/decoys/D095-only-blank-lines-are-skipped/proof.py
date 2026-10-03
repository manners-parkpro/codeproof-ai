"""D095 반증 - 형식이 틀린 줄을 넣고 load 가 알리는지 본다."""

from __future__ import annotations

from types import ModuleType

# 쉼표 개수 · 빈 수량 · 숫자가 아닌 수량 · 다른 구분자 (DESIGN §3.5 「입력 검사」).
# 이름 칸이 빈 줄(",3")은 넣지 않는다 - 주장은 쉼표 개수와 int 로 읽히는지만 말한다 (독립 검토)
_MALFORMED = ("apple", "apple,", "apple,3,4", "apple,x", "apple,1.5", " , ", "apple;3", "apple, 3 4")
_BLANK = ("", "   ", "\t", "\n", " \r\n")


def attack(mod: ModuleType) -> bool:
    """쉼표 개수가 틀렸거나 수량이 int 로 읽히지 않는 줄이 ValueError 없이 지나가는가.

    🔴 ValueError 가 났는지를 직접 본다 - 줄 수만 세면 틀린 줄을 버리지 않고 고쳐 읽는 약화(int(float(q)) ·
       남는 칸 무시 · 빈 수량 0)가 지나간다 (독립 검토).

    decoy 는 비공개 예외 _BlankLine 만 받아 빈 줄만 건너뛰고, 틀린 줄의 ValueError 는 올라간다.
    twin 은 ValueError 도 받아 틀린 줄을 버린다.
    """
    for bad in _MALFORMED:
        try:
            mod.load(["pear,2", bad, "plum,5"])
        except ValueError:
            continue
        return True  # 틀린 줄이 알림 없이 지나갔다 - 버렸든 고쳐 읽었든

    # 빈 줄은 건너뛰고 올바른 줄은 그대로 읽는다 - 「전부 거절」은 안전이 아니다
    rows = mod.load(["pear,2", *_BLANK, " plum , 5 "])
    return rows != [("pear", 2), ("plum", 5)]
