"""F11d6e39463 (D084) - ntpath.isreserved 가 없는 판에서 save_attachment 가 어떻게 되는가.

이 탐침을 여러 판의 인터프리터로 돌린다 (탐침 자신은 외부 프로그램을 부르지 않는다).
3.13 미만에서는 decoy 를 import 한 뒤 save_attachment 를 불러 본다 - 작업 폴더 안의 임시 디렉터리에만 쓴다.
"""

import importlib.util
import ntpath
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("decoy_F11d6e39463", HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


print("python", sys.version.split()[0], "| hasattr(ntpath, 'isreserved'):", hasattr(ntpath, "isreserved"))
mod = _load()
with tempfile.TemporaryDirectory(dir=HERE) as tmp:
    root = Path(tmp) / "box"
    root.mkdir()
    for name in ("report.pdf", "../escaped.txt", "CON"):
        try:
            print(f"save_attachment({name!r}) ->", mod.save_attachment(root, name, b"x").name)
        except Exception as exc:  # noqa: BLE001
            print(f"save_attachment({name!r}) -> {type(exc).__name__}: {exc}")
    print("written:", sorted(p.name for p in Path(tmp).rglob("*") if p.is_file()))
