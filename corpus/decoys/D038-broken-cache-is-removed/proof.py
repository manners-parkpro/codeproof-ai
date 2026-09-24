"""D038 반증 - 손상 상태가 남는지 본다."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """깨진 캐시를 만난 뒤에도 손상이 남는가.

    decoy 는 잡은 자리에서 파일을 지워 다음 호출이 깨끗한 미스가 된다.
    twin 은 파일을 남겨 같은 손상이 영구히 반복된다.
    """
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "cache.json"

        path.write_text("{not json", encoding="utf-8")
        if mod.load_cache(path) != {}:
            return True
        if path.exists():
            return True  # 손상이 남았다

        # 정상 캐시와 부재 경로도 망가지지 않았는지 본다
        path.write_text('{"a": "1"}', encoding="utf-8")
        if mod.load_cache(path) != {"a": "1"}:
            return True
        return mod.load_cache(Path(tmp) / "absent.json") != {}
