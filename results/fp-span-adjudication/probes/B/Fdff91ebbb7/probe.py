"""Fdff91ebbb7 (D122) - 쓰다 예외가 나면 그때까지 쓴 항목만 담은 zip 이 남고, 같은 경로로 다시 부르면 FileExistsError 인가.

작업 폴더 안의 임시 디렉터리에만 쓴다.
"""

import importlib.util
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("decoy_Fdff91ebbb7", HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()


def entries():
    yield ("a.txt", b"alpha")
    yield ("b.txt", b"beta")
    raise RuntimeError("source failed")


with tempfile.TemporaryDirectory(dir=HERE) as tmp:
    target = Path(tmp) / "backup.zip"
    try:
        mod.backup(target, entries())
    except RuntimeError as exc:
        print("backup ->", type(exc).__name__, exc)
    with zipfile.ZipFile(target) as z:
        print("left at target:", [(i.filename, z.read(i)) for i in z.infolist()])
    try:
        mod.backup(target, [("a.txt", b"alpha")])
    except FileExistsError as exc:
        print("retry same path ->", type(exc).__name__)
