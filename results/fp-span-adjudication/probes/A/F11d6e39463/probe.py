"""F11d6e39463 (D084) - ntpath.isreserved 가 없는 판에서 무엇이 일어나는가, 그리고 코퍼스의 판에서는.

네트워크 · 외부 프로그램 없음. 쓰기는 이 폴더 아래 임시 디렉터리에만 한다.
이 탐침을 3.14 (코퍼스 판) 와 그 함수가 없는 판(3.11) 으로 각각 돌린다 - 탐침이 다른 프로그램을 띄우지는 않는다.
"""

import importlib.util
import ntpath
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent


def load(name: str = "d084_copy"):
    spec = importlib.util.spec_from_file_location(name, HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


print("python", sys.version.split()[0], "| ntpath.isreserved present:", hasattr(ntpath, "isreserved"))
mod = load()
with tempfile.TemporaryDirectory(dir=HERE) as tmp:
    box = pathlib.Path(tmp) / "box"
    box.mkdir()
    (box / "sub").mkdir()
    for name in ("report-2024.v2.pdf", "CON", "nul.txt", "trail.", "../escaped.txt", "sub/../../escaped.txt", ".."):
        try:
            written = mod.save_attachment(box, name, b"x")
            print(f"  {name!r} -> written {written.relative_to(tmp)}")
        except Exception as exc:  # noqa: BLE001
            print(f"  {name!r} -> {type(exc).__name__}: {exc}")
    print("  entries in box:", sorted(p.name for p in box.iterdir()), "| entries beside box:", sorted(p.name for p in pathlib.Path(tmp).iterdir()))
