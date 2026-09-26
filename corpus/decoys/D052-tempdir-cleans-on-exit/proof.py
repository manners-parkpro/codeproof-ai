"""D052 반증 - 임시 디렉터리가 남는지 본다."""

from __future__ import annotations

import tempfile
from pathlib import Path
from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """export 가 끝난 뒤 작업 디렉터리가 남아 있는가.

    🔴 GC 나 프로세스 종료에 기대지 않는다 - 임시 루트를 격리해
       그 안에 무엇이 남는지 직접 센다.
    """
    with tempfile.TemporaryDirectory() as isolated:
        saved = tempfile.tempdir
        tempfile.tempdir = isolated
        try:
            got = mod.export(["a,1", "b,2"])
        finally:
            tempfile.tempdir = saved

        if got != "a,1\nb,2":
            return True
        leftovers = list(Path(isolated).iterdir())

    return bool(leftovers)
