"""D129 반증 - next_server 를 아주 여러 번 불러 localhost 가 나오거나 차례가 어긋나는지 본다."""

from __future__ import annotations

from types import ModuleType

_SERVERS = ("10.0.0.1", "10.0.0.2", "10.0.0.3")
_CALLS = 10_000


def attack(mod: ModuleType) -> bool:
    """next_server 가 localhost 를 돌려주거나, 세 서버를 한 바퀴에 하나씩 같은 차례로 되풀이하지 않으면 True.

    🔴 한 바퀴보다 훨씬 많이 부른다 - 목록을 몇 번 이어 붙인 유한 반복자도 언젠가 끝난다.
    🔴 처음 위치와 바퀴 안의 차례는 묻지 않는다 - 첫 바퀴에 세 서버가 하나씩 나오고 그 차례가 되풀이되면 된다.
       해시 시드로 차례가 정해지는 frozenset · import 때 한 번 섞는 판은 한 프로세스 안에서 가를 수 없고, 주장도 차례를 정하지 않는다 (독립 검토).

    decoy 는 _ring 이 itertools.cycle 이라 다 돈 뒤 처음부터 다시 돌려준다.
    twin 은 _ring 이 iter 라 세 번 뒤 StopIteration 이 나서 localhost 로 떨어진다.
    """
    first = [mod.next_server() for _ in range(len(_SERVERS))]
    if sorted(first) != sorted(_SERVERS):
        return True
    for i in range(len(_SERVERS), _CALLS):
        if mod.next_server() != first[i % len(_SERVERS)]:
            return True
    return False
