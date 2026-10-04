"""D122 반증 - 정상 종료와 세 가지 예외 경로에서, backup 을 빠져나오는 바로 그 순간 target 을 zip 으로 읽어 본다."""

from __future__ import annotations

import os
import warnings
import zipfile
from collections.abc import Iterator
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType

_ENTRIES = [("a.txt", b"alpha"), ("dir/b.bin", bytes(range(256))), ("빈 파일.txt", b""), ("c.txt", b"gamma" * 1000)]
_BAD_NAME = "\ud800.txt"  # UTF-8 로 바꿀 수 없다 - writestr 이 항목 머리를 쓰다 던진다


class _Boom(Exception):
    pass


class _Halt(BaseException):
    """Exception 이 아닌 동기 예외 - except Exception 으로만 닫는 약화를 가른다."""


def _failing(after: int, error: type[BaseException]) -> Iterator[tuple[str, bytes]]:
    yield from _ENTRIES[:after]
    raise error


class _Unreadable:
    """반복자를 얻는 순간 던지는 iterable - 「entries 를 읽다」 의 맨 앞이다 (쓰는 단계 점검)."""

    def __iter__(self) -> Iterator[tuple[str, bytes]]:
        raise _Boom


def _fds() -> int:
    """지금 열려 있는 파일 디스크립터 수 - 빠져나간 순간 target 의 핸들이 남았는지 본다."""
    return len(os.listdir("/dev/fd"))


def _read(target: Path) -> list[tuple[str, bytes]] | None:
    """닫힌 zip 으로 읽히면 (이름, 데이터) 목록 - 깨져서 못 읽으면 None.

    target 이 아예 없으면 빈 목록으로 친다 - 주장은 「연 뒤에는」이라, 아무것도 쓰기 전에 열지 않은 것은 어기지 않는다.
    """
    if not target.exists():
        return []
    try:
        with zipfile.ZipFile(target) as archive:
            return [(info.filename, archive.read(info)) for info in archive.infolist()]
    except (zipfile.BadZipFile, OSError):
        return None


def _in_order(got: list[tuple[str, bytes]], offered: list[tuple[str, bytes]]) -> bool:
    """got 이 offered 의 항목을 차례대로 고른 것인가 - 예외로 끝났을 때 어느 항목까지 썼는지는 묻지 않는다 (독립 검토).

    먼저 entries 를 다 읽은 뒤 쓰는 판은 entries 가 던지면 아무것도 쓰지 않는다 - 「그때까지 쓴 항목」 은 받은 항목이 아니다.
    """
    rest = iter(offered)
    return all(item in rest for item in got)


def _outcome(mod: ModuleType, target: Path, entries: object) -> tuple[list[tuple[str, bytes]] | None, bool]:
    """backup 을 부르고, 돌아오든 예외로 끝나든 바로 그 순간의 target 을 읽는다 - (읽은 것, 예외로 끝났는가).

    빠져나간 순간 파일 디스크립터가 늘어 있으면 None 이다 - 내용이 온전해도 핸들이 남은 것이다.
    """
    before = _fds()
    try:
        mod.backup(target, entries)
    except (Exception, _Halt):  # noqa: BLE001 - 어떤 예외로 끝나든 묻지 않는다
        # 🔴 except 안에서 읽는다 - 예외의 트레이스백이 backup 의 프레임을 붙들고 있는 동안이다.
        #    except 를 벗어난 뒤에 읽으면 프레임이 풀리며 ZipFile.__del__ 이 닫아 twin 도 온전해 보인다.
        leaked = _fds() != before
        return (None if leaked else _read(target)), True
    leaked = _fds() != before
    return (None if leaked else _read(target)), False


def attack(mod: ModuleType) -> bool:
    """backup 을 빠져나오는 순간 target 이 그때까지 쓴 항목을 담은 zip 으로 읽히지 않으면 True.

    🔴 예외 경로를 셋으로 친다 - 입력이 던지는 Exception · 입력이 던지는 BaseException · writestr 이 던지는 예외.
       BaseException 을 빼면 「except Exception 에서만 닫는」 약화가 지나간다.
    🔴 정상 종료는 끝을 보지 않는다 - CPython 은 참조가 풀리는 순간 ZipFile.__del__ 이 닫아 twin 도 온전하다.
       가르는 것은 예외 경로다.

    decoy 는 backup 의 with 가 빠져나가는 모든 경로에서 close 를 불러 목차를 쓴다.
    twin 은 with 없이 받아 예외가 빠져나가는 동안 ZipFile 이 열린 채 남는다.
    """
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        # 🔴 이미 있는 target 은 건드리지 않고 거절한다 - 지난 백업을 잘라 버리면 실패할 때 남는 것이 없다
        #    빈 entries · 반복자를 얻을 때 던지는 entries 로도 친다 - 첫 항목을 받을 때 여는 판이 빠지지 않게 (독립 검토)
        for k, entries in enumerate((list(_ENTRIES), [], _Unreadable())):
            old = root / f"old-{k}.zip"
            old.write_bytes(b"previous backup")
            try:
                mod.backup(old, entries)
            except Exception:  # noqa: BLE001, S110 - 거절 방식은 묻지 않는다
                pass
            else:
                return True
            if old.read_bytes() != b"previous backup":
                return True
        # 🔴 반복자를 얻는 순간의 예외도 「entries 를 읽다」 다 (쓰는 단계 점검)
        if _outcome(mod, root / "unreadable.zip", _Unreadable())[0] != []:
            return True
        for n in range(len(_ENTRIES) + 1):
            want = _ENTRIES[:n]
            if _outcome(mod, root / f"list-{n}.zip", want)[0] != want:
                return True
            if _outcome(mod, root / f"iter-{n}.zip", iter(want))[0] != want:
                return True
            for error in (_Boom, _Halt):
                got = _outcome(mod, root / f"{error.__name__}-{n}.zip", _failing(n, error))[0]
                if got is None or not _in_order(got, want):
                    return True
            # 🔴 담을 수 없는 이름이 있으면 정상으로 돌아올 수 없다 - 정상 반환은 「entries 의 항목을 모두 담은 zip」 이어야 한다 (독립 검토)
            got, raised = _outcome(mod, root / f"name-{n}.zip", [*want, (_BAD_NAME, b"x"), *_ENTRIES[n:]])
            if not raised or got is None or not _in_order(got, [*want, *_ENTRIES[n:]]):
                return True
        # 🔴 같은 이름의 항목도 모두 담는다 - 이미 쓴 이름을 건너뛰는 판이 빠지지 않게 (독립 검토 · zipfile 은 경고와 함께 둘 다 쓴다)
        dup = [("a.txt", b"1"), ("a.txt", b"2"), ("b.txt", b"3")]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            if _outcome(mod, root / "dup.zip", list(dup))[0] != dup:
                return True
    return False
