"""D068 반증 - 받은 기본 정책을 고쳐 다른 엔드포인트의 기본값을 바꾸려 한다."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType

_MUTATIONS: tuple[Callable[[object], None], ...] = (
    lambda p: setattr(p, "attempts", 10),
    lambda p: object.__setattr__(p, "attempts", 10),
    lambda p: p.__dict__.update(attempts=10),
)


def attack(mod: ModuleType) -> bool:
    """한 호출자가 받은 기본 정책을 고치면 다른 엔드포인트의 기본값이 바뀌는가.

    decoy 의 RetryPolicy 는 NamedTuple 이라 어느 경로의 대입도 AttributeError 로 거부된다.
    twin 은 frozen 이 아닌 dataclass 라 대입이 그대로 공유 객체에 들어간다.
    """
    for mutate in _MUTATIONS:
        try:
            mutate(mod.policy_for("upload", {}))
        except AttributeError:
            pass  # 대입이 거부됐다 - 그것이 안전 근거다

    other = mod.policy_for("download", {})
    # 🔴 객체끼리 비교하지 않는다 - dataclass 와 튜플은 값이 같아도 다르다고 나와 twin 이 공짜로 깨진다.
    return (other.attempts, other.backoff_seconds) != (3, 0.5)
