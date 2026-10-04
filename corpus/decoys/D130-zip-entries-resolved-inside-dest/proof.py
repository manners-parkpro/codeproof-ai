"""D130 반증 - 밖으로 풀리는 여러 모양의 항목을 담은 zip 을 풀고, dest 밖의 파일 · 디렉터리가 하나라도 생기거나 바뀌거나 사라졌는지 본다."""

from __future__ import annotations

import os
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType


def _outside(top: Path, real: Path) -> dict[str, tuple[str, bytes]]:
    """top 아래에서 real 밖에 있는 항목 전부 - 경로마다 (종류, 내용). 링크는 따라가지 않고 링크 자체를 적는다."""
    found: dict[str, tuple[str, bytes]] = {}
    for dirpath, dirs, names in os.walk(top):
        for name in dirs + names:
            path = Path(dirpath, name)
            if path.is_relative_to(real):
                continue
            if path.is_symlink():
                found[str(path)] = ("link", os.readlink(path).encode())
            elif path.is_dir():
                found[str(path)] = ("dir", b"")
            else:
                found[str(path)] = ("file", path.read_bytes())
    return found


def _zip(path: Path, entries: list[tuple[str, bytes]]) -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in entries:
            zf.writestr(name, data)
    return path


def _hostile(top: Path) -> list[list[tuple[str, bytes]]]:
    """밖으로 풀리는 항목을 담은 묶음 - 탈출은 모두 top 안에 떨어지게 짠다 (twin 과 약화 변이도 이 증명으로 돈다)."""
    return [
        # 🔴 밖 항목의 자리 - 끝 · 앞 · 가운데 (한 자리만 두면 「첫 항목만」 · 「마지막 항목만」 확인하는 약화가 지나간다)
        [("first.txt", b"1"), ("../escape.txt", b"x")],
        [("../first_out.txt", b"x"), ("after.txt", b"a")],
        [("in1.txt", b"1"), ("../middle_out.txt", b"x"), ("in2.txt", b"2")],
        # 절대 경로 - 새 파일 · 밖의 기존 파일
        [(f"{top}/abs.txt", b"x")],
        [(f"{top}/outside/victim.txt", b"PWNED")],
        # 🔴 dest 안의 링크 - 중간 성분의 디렉터리 링크 (새 파일 · 기존 파일) · 마지막 성분의 파일 링크 · 끊긴 링크
        [("link/pwn.txt", b"x")],
        [("link/existing.txt", b"PWNED")],
        [("flink", b"PWNED")],
        [("dangle", b"x")],
        # 이름 속 .. - 글자로는 안이지만 링크를 지나면 밖인 것 포함
        [("sub/../../escape2.txt", b"x")],
        [("link/../escape3.txt", b"x")],
        [("inner_link/../../escape4.txt", b"x")],
        # 🔴 dest 와 이름 앞부분이 같은 형제 폴더 - 문자열 접두사로 비교하는 약화가 지나간다
        [("../real_dest_evil/x.txt", b"x")],
        # 🔴 밖에 새 디렉터리만 생기는 이름 - 검사 전에 부모 디렉터리를 만드는 약화가 지나간다
        [("../newdir/x.txt", b"x")],
        [("../victim_top.txt", b"PWNED")],
        # 🔴 밖의 파일과 하드 링크로 이어진 dest 안의 파일 - 그 자리에 그대로 쓰면 밖의 내용이 바뀐다
        [("hl.txt", b"PWNED")],
        # 🔴 디렉터리 항목 (이름이 / 로 끝남) - 밖 · 링크 너머 · 여러 단계. 확인 없이 만드는 판이 빠지지 않게 (독립 검토)
        [("../evil_dir/", b""), ("ok.txt", b"1")],
        [("link/evil_sub/", b"")],
        [("../a/b/c/", b"")],
    ]


def attack(mod: ModuleType) -> bool:
    """밖으로 풀리는 묶음을 푼 뒤 dest 밖의 파일 · 디렉터리가 하나라도 생기거나 바뀌거나 사라졌으면 True.

    🔴 밖은 새 파일만 세지 않는다 - 디렉터리 · 기존 파일의 내용 · 사라진 파일까지 스냅숏으로 견준다.
       새 파일만 세면 「쓴 뒤 확인하고 밖이면 지움」 · 「검사 전에 부모 디렉터리를 만듦」이 지나간다.
    🔴 dest 를 실제 경로와 심볼릭 링크 경로로 넘기고, 회차마다 새 디렉터리에서 시작한다.
    🔴 거절 방식은 묻지 않는다 - 어떤 예외로 멈추든 조용히 건너뛰든, 밖이 그대로면 된다.
       안쪽 항목을 풀어 주는지도 묻지 않는다 - 주장은 밖을 건드리지 않는다는 것뿐이다.

    decoy 는 항목마다 resolve 한 경로가 resolve 한 dest 안인지 쓰기 전에 확인하고, 그 자리의 기존 파일을 끊고 새로 쓴다.
    twin 은 확인 없이 resolve 한 경로에 그대로 써서 dest 밖에 파일이 생기고 밖의 기존 파일이 바뀐다.
    """
    for dest_kind in ("real", "link"):
        # zip 은 따로 둔다 - 스냅숏을 뜨는 디렉터리 안에 만들면 증명이 만든 zip 이 「밖의 새 파일」로 세어진다
        with TemporaryDirectory() as tmp, TemporaryDirectory() as zips:
            top = Path(tmp).resolve()
            outside = top / "outside"
            outside.mkdir()
            (outside / "victim.txt").write_bytes(b"ORIGINAL")
            (outside / "existing.txt").write_bytes(b"ORIGINAL")
            (outside / "hl_victim.txt").write_bytes(b"ORIGINAL")
            (top / "victim_top.txt").write_bytes(b"ORIGINAL")
            real = top / "real_dest"
            (real / "sub").mkdir(parents=True)
            (real / "link").symlink_to(outside, target_is_directory=True)
            (real / "inner_link").symlink_to(real / "sub", target_is_directory=True)
            (real / "flink").symlink_to(outside / "victim.txt")
            (real / "dangle").symlink_to(outside / "notyet.txt")
            os.link(outside / "hl_victim.txt", real / "hl.txt")
            dest_link = top / "dest_link"
            dest_link.symlink_to(real, target_is_directory=True)
            dest = real if dest_kind == "real" else dest_link

            before = _outside(top, real)
            for i, entries in enumerate(_hostile(top)):
                try:
                    mod.extract(_zip(Path(zips) / f"h{i}.zip", entries), dest)
                except Exception:  # noqa: BLE001, S110 - 거절 방식은 묻지 않는다
                    pass
            if _outside(top, real) != before:
                return True
    return False
