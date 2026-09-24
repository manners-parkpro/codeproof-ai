"""D037 반증 - 반복 저장이 파일을 늘리는지 본다."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType

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
        return target.read_text(encoding="utf-8") != _BODY
