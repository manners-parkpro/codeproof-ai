"""D080 반증 - 앞 항목은 맞고 뒤 항목이 틀린 갱신을 넣는다."""

from __future__ import annotations

from types import ModuleType
from typing import Any


class _Abort(BaseException):
    """Exception 도 KeyboardInterrupt 도 아닌 예외 - SystemExit 같은 것의 대리."""


class _Interrupting(dict[str, Any]):
    """두 번째 항목을 검사할 때 지정한 예외를 낸다 - Exception 이 아닌 예외의 대리."""

    def __init__(self, base: dict[str, Any], error: type[BaseException]) -> None:
        super().__init__(base)
        self.calls = 0
        self.error = error

    def get(self, key: str, default: Any = None) -> Any:
        self.calls += 1
        if self.calls == 2:
            raise self.error
        return super().get(key, default)


def attack(mod: ModuleType) -> bool:
    """실패한 갱신 뒤에 설정이 절반만 바뀐 채 남는가.

    🔴 주장은 「갱신 도중 올라온 어떤 예외든」이다. ValueError 만 치면 except Exception 으로 좁힌
       문맥이 통과하고, KeyboardInterrupt 까지만 치면 except (Exception, KeyboardInterrupt) 가
       통과한다 (독립 검토) - 두 번째 항목에서 둘 다 아닌 BaseException 도 친다.

    decoy 는 감싼 문맥이 BaseException 을 보면 갱신 전 사본으로 되돌린다.
    twin 은 사본을 만들기만 하고 되돌리지 않아 앞 항목이 남는다.
    """
    before = dict(mod._config)
    try:
        mod.apply({"mode": "maintenance", "region": "mars"})
    except ValueError:
        pass
    else:
        return True  # 허용되지 않은 값이 받아들여졌다
    if mod._config != before:
        return True

    allowed = mod._ALLOWED
    for error in (KeyboardInterrupt, _Abort):
        mod._ALLOWED = _Interrupting(allowed, error)
        try:
            mod.apply({"mode": "maintenance", "region": "jp"})
        except error:
            pass
        finally:
            mod._ALLOWED = allowed
        if mod._config != before:
            return True

    # 맞는 갱신은 전부 반영된다
    mod.apply({"mode": "maintenance", "region": "jp"})
    return mod._config != {"mode": "maintenance", "region": "jp"}
