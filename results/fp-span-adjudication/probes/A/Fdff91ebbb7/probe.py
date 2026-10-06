"""Fdff91ebbb7 (D122) - 쓰다 실패하면 일부 항목만 담긴 zip 이 남고, 같은 경로로 다시 부르면 FileExistsError 인가 - 쌍이 그것을 어떻게 말하는가.

네트워크 · 외부 프로그램 없음. 쓰기는 이 폴더 아래 임시 디렉터리에만 한다 (meta.toml 은 읽기만 한다).
"""

import importlib.util
import pathlib
import sys
import tempfile
import tomllib
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
META = pathlib.Path("<repo>/corpus/decoys/D122-zip-closed-by-the-callers-with/meta.toml")


def load(name: str = "d122_copy"):
    spec = importlib.util.spec_from_file_location(name, HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def failing():
    yield ("a.txt", b"alpha")
    raise RuntimeError("entry source failed")


mod = load()
with tempfile.TemporaryDirectory(dir=HERE) as tmp:
    target = pathlib.Path(tmp) / "backup.zip"
    try:
        mod.backup(target, failing())
    except RuntimeError as exc:
        print("backup raised:", type(exc).__name__, "| target exists:", target.exists())
    with zipfile.ZipFile(target) as archive:
        print("partial zip entries:", archive.namelist(), "| testzip:", archive.testzip())
    try:
        mod.backup(target, [("b.txt", b"beta")])
    except FileExistsError as exc:
        print("retry on the same path:", type(exc).__name__)
claim = tomllib.loads(META.read_text(encoding="utf-8"))["safety"]["claim"]
print("claim: rejects existing target ->", "target 이 이미 있으면 건드리지 않고 거절한다" in claim)
print("claim: partial zip on exception ->", "그때까지 쓴 항목만 담은 zip 으로 읽힌다" in claim)
