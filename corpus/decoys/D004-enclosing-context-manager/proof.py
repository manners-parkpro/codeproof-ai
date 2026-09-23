"""D004 반증 - 핸들이 닫혔는지 본다."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """dump 가 끝난 뒤에도 핸들이 열려 있으면 자원 누수다.

    decoy 는 with 블록이 닫고, twin 은 열어 둔 채 반환한다.
    닫혔는지는 파일 객체를 가로채서 확인한다 - GC 타이밍에 기대지 않는다.
    """
    opened: list[object] = []
    original = Path.open

    def spy(self: Path, *a: object, **k: object) -> object:
        handle = original(self, *a, **k)  # type: ignore[arg-type]
        opened.append(handle)
        return handle

    with TemporaryDirectory() as tmp:
        target = Path(tmp) / "out.txt"
        mod.Path.open = spy
        try:
            mod.dump(target, ["a", "b"])
        finally:
            mod.Path.open = original
            leaked = [h for h in opened if not getattr(h, "closed", True)]
            for h in leaked:
                h.close()  # type: ignore[attr-defined]

    return bool(leaked)
