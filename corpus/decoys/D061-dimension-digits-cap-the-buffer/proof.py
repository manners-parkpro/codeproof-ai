"""D061 반증 - 거대한 크기 문자열로 무제한 할당을 노린다."""

from __future__ import annotations

from types import ModuleType

_CAP = 999 * 999 * 4
# 한 변만 넘치는 경우와 네 자리 경계를 같이 둔다 - 두 변을 같이 키우는 입력만 있으면 한쪽 자릿수만
# 풀린 가드가 통과한다 (독립 검토가 찾았다).
_SPECS = ("1000x1000", "100000x100000", "99999999x1", "1x99999999", "999x1000", "1000x999")


def attack(mod: ModuleType) -> bool:
    """상한을 넘는 버퍼를 잡으려 하는가.

    🔴 실제로 잡지 않는다 - 모듈의 bytearray 를 가로채 **요청된 크기**만 본다.
       호스트 메모리에 기대면 공격의 성패가 환경에 따라 달라진다.

    decoy 는 _DIMENSIONS 가 각 변을 세 자리 이하로 막아 match 단계에서 거절한다.
    twin 은 자릿수 제한이 없어 그대로 곱한다.
    """
    asked: list[int] = []

    def spy(size: int) -> bytearray:
        asked.append(size)
        return bytearray(0)

    mod.bytearray = spy  # 모듈 전역이 내장보다 먼저 찾아진다
    for spec in _SPECS:
        try:
            mod.frame_buffer(spec)
        except ValueError:
            continue  # 의도한 거절
    mod.frame_buffer("640x480")  # 정상 크기는 그대로 잡힌다
    return any(size > _CAP for size in asked) or 640 * 480 * 4 not in asked
