"""F19b2777e5d (D043) - candidate 만 resolve 하고 _ROOT 는 그대로 견주는 어긋남이 무엇을 만드는가.

네트워크 · 외부 프로그램 없음. 쓰기는 이 폴더 아래 임시 디렉터리에만 한다.
/srv/data 가 링크인 호스트는 만들 수 없어 (작업 폴더 밖 쓰기) 사본의 _ROOT 를 이 폴더 안의 링크로 가리켜 그 환경을 흉내 낸다 -
가드(resolve · _under_root)는 그대로 두고 루트가 놓인 환경만 바꾼다.
"""

import importlib.util
import os
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent


def load(name: str = "d043_copy"):
    spec = importlib.util.spec_from_file_location(name, HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


NAMES = ("report.csv", "sub/x.txt", "../../etc/passwd", "..", "a/../../../secret")


def show(mod, label: str, real_root: pathlib.Path) -> None:
    for name in NAMES:
        try:
            got = mod.resolve_entry(name)
        except ValueError:
            print(f"  [{label}] {name!r} -> ValueError")
            continue
        print(f"  [{label}] {name!r} -> {got} | inside real root: {got.resolve().is_relative_to(real_root.resolve())}")


mod = load()
print("/srv exists on this host:", os.path.exists("/srv"))
print("default environment (_ROOT = /srv/data, not a link here):")
show(mod, "default", pathlib.Path("/srv/data"))

with tempfile.TemporaryDirectory(dir=HERE) as tmp:
    real = pathlib.Path(tmp) / "real"
    real.mkdir()
    (real / "sub").mkdir()
    plain = load("d043_plain")
    plain._ROOT = real
    print("root is a real directory:")
    show(plain, "plain", real)
    link = pathlib.Path(tmp) / "link"
    link.symlink_to(real, target_is_directory=True)
    linked = load("d043_linked")
    linked._ROOT = link
    print("root is a symlink to that directory:")
    show(linked, "link", real)
