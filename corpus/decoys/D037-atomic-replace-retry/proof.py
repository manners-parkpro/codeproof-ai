"""D037 반증 - 반복 저장이 파일을 늘리는지 본다."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType
from typing import Any

_BODY = "retries = 3\n"


def attack(mod: ModuleType) -> bool:
    """save 를 여러 번 불러도 내용이 그대로인가.

    decoy 는 staging 에 쓰고 replace 하므로 항상 마지막 한 번의 결과다.
    twin 은 append 라 호출 횟수만큼 쌓인다.
    """
    with TemporaryDirectory() as tmp:
        target = Path(tmp) / "config.toml"

        mod.save(target, _BODY)
        if target.read_text(encoding="utf-8") != _BODY:
            return True

        mod.save(target, _BODY)
        if target.read_text(encoding="utf-8") != _BODY:
            return True

        # 🔴 재시도도 반복 호출이다 (독립 검토가 주장 밖이라 재지 않던 자리) - 바꿔 넣기를 한 번 OSError 로 실패시켜
        #    save 가 다시 쓰게 한다. 성공 경로만 보면 재시도에서만 이어 쓰는 약화가 지나간다. 환경의 일시적 실패를
        #    흉내 낼 뿐 가드를 우회하지 않는다 - os.replace · os.rename 의 첫 부름 하나만 실패한다 (Path.replace 가 부른다)
        failed: list[object] = []

        def _once(real: Callable[..., Any]) -> Callable[..., Any]:
            def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
                if not failed:
                    failed.append(args)
                    raise OSError("일시적인 실패")
                return real(*args, **kwargs)

            return wrapper

        real_replace, real_rename = os.replace, os.rename
        os.replace, os.rename = _once(real_replace), _once(real_rename)
        try:
            mod.save(target, _BODY)
        except OSError:
            pass  # 재시도하지 않고 올리는 것도 내용을 늘리지 않는다
        finally:
            os.replace, os.rename = real_replace, real_rename
        return target.read_text(encoding="utf-8") != _BODY
