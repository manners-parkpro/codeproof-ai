"""D136 반증 - 임시 파일들을 합치게 하고, 성공 · 여는 도중 · 읽는 도중 · 쓰는 도중의 여러 종류 실패마다 연 파일이 코드로
닫혔는지와 그 예외가 그대로 올라왔는지 본다."""

from __future__ import annotations

import gc
import io
import locale
import tempfile
import warnings
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

# 파일 내용 - 정렬된 줄 · \n 없는 끝 · 빈 파일 · CRLF · 같은 줄 · ASCII 아닌 글자 · 홀로 선 CR · 대소문자가 섞인 줄 ·
# 줄 앞뒤의 탭과 공백 · 빈 줄 (\t < \n < b 라 정렬돼 있다) · \n 없는 끝 줄이 다른 파일 줄의 앞부분 (a 와 a\t - 차례는 \n 을
# 붙인 뒤의 줄로 정한다: a\t\n < a\n)
_FILES = {
    "a.log": "apple\ncherry\nmango\n",
    "b.log": "banana\nkiwi",
    "c.log": "",
    "d.log": "avocado\r\nfig\r\nzucchini\r\n",
    "e.log": "cherry\ncherry\n가지\n",
    "f.log": "grape\rlime\r",
    "g.log": "Banana\nCherry\nbanana\n",
    "h.log": "\talpha  \n\nbeta \n",
    "i.log": "a",
    "j.log": "a\t\n",
}


class _Halt(BaseException):
    """사용자가 만든 BaseException - Exception 이 아니다."""


class _Raising(io.StringIO):
    """쓰려 하면 정해 둔 예외를 내는 out."""

    def __init__(self, boom: BaseException) -> None:
        super().__init__()
        self.boom = boom

    def write(self, text: str) -> int:
        raise self.boom


class _Full(io.StringIO):
    """모두 합쳐 budget 글자를 넘게 쓰려 하면 실패하는 out - 몇 번에 나눠 쓰는지는 묻지 않는다."""

    def __init__(self, budget: int) -> None:
        super().__init__()
        self.budget = budget
        self.boom = OSError(28, "No space left on device")

    def write(self, text: str) -> int:
        if len(self.getvalue()) + len(text) > self.budget:
            raise self.boom
        return super().write(text)


def _expected(texts: list[str]) -> str:
    """주장 문장대로 - 텍스트 모드의 줄(줄 끝은 \\n) · 마지막 줄에 \\n · 정렬된 차례."""
    lines: list[str] = []
    for text in texts:
        body = text.replace("\r\n", "\n").replace("\r", "\n")
        parts = body.split("\n")
        lines += [part + "\n" for part in parts[:-1]] + ([parts[-1] + "\n"] if parts[-1] else [])
    return "".join(sorted(lines))


def _open_on(paths: list[Path]) -> list[io.IOBase]:
    names = {str(path) for path in paths}
    return [o for o in gc.get_objects() if isinstance(o, io.IOBase) and not o.closed and str(getattr(o, "name", "")) in names]


def _leaks(mod: ModuleType, paths: list[Path], out: io.TextIOBase) -> tuple[bool, BaseException | None]:
    """merge 를 부르고 (코드가 닫지 않은 파일이 있는가, 올라온 예외) 를 돌려준다. 남은 핸들은 여기서 닫는다.

    🔴 예외가 프레임을 쥔 동안에 본다 - 놓으면 가비지 수집이 닫아 버린다.
    🔴 성공한 호출은 ResourceWarning 으로 본다 - 코드가 닫지 않은 파일은 돌아오는 순간 가비지 수집이 닫으며 경고한다.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ResourceWarning)
        raised: BaseException | None = None
        leaked: list[io.IOBase] = []
        try:
            mod.merge([str(path) for path in paths], out)
        except BaseException as exc:  # noqa: BLE001 - 실패도 시나리오다 - 연 파일이 닫혔는지 본다
            raised = exc
            leaked = _open_on(paths)
        for handle in leaked:
            handle.close()
        gc.collect()
    unclosed = [w for w in caught if issubclass(w.category, ResourceWarning)]
    return bool(leaked or unclosed), raised


def attack(mod: ModuleType) -> bool:
    """연 파일을 코드가 닫지 않거나, 성공한 합치기의 내용이 주장과 다르거나, 실패한 합치기의 예외가 그대로 올라오지 않는가.

    🔴 실패를 세 자리에서 여러 종류로 일으킨다 - 여는 도중(없는 경로 · NUL 이 든 경로) · 읽는 도중(UTF-8 이 아닌 바이트) ·
       쓰는 도중(out 이 가득 참 · ASCII 만 쓰는 out · 닫힌 out). OSError 만 닫는 판이 빠지지 않게.
    🔴 그 예외는 그대로 올라와야 한다 - 만든 예외면 같은 객체, 아니면 실패한 연산이 내는 타입이다.
       쓰는 실패는 글자 수 예산으로 일으킨다 - 몇 번에 나눠 쓰는지는 주장이 정하지 않는다.
    🔴 줄은 텍스트 모드로 읽은 것이다 - CRLF 와 홀로 선 CR. 정렬은 대소문자가 섞인 줄로 본다.
    🔴 같은 경로를 두 번 · 경로 없이도 부른다.
    🔴 Exception 이 아닌 동기 예외(KeyboardInterrupt · SystemExit · 사용자 BaseException)도 쓰는 도중에 일으킨다 ·
       로캘 인코딩이 UTF-8 이 아닌 곳(LC_CTYPE C)에서도 합친다 · 줄 앞뒤의 탭 · 공백과 빈 줄을 둔다 (6라운드 검토).

    decoy 는 연 파일을 _all_closed 의 목록에 넣어 블록을 나갈 때 모두 닫는다.
    twin 은 닫는 문맥이 없어 실패하면 열린 채 남고, 성공하면 가비지 수집이 닫는다.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for name, text in _FILES.items():
            (root / name).write_bytes(text.encode())
        (root / "bad.log").write_bytes(b"alpha\n\xff\xfe broken\nomega\n")
        good = [root / name for name in _FILES]
        for paths in (good, good[:1], [good[0], good[0]], []):
            out = io.StringIO()
            leaked, raised = _leaks(mod, paths, out)
            if leaked or raised is not None or out.getvalue() != _expected([_FILES[p.name] for p in paths]):
                return True
        # 로캘 인코딩이 UTF-8 이 아닌 곳에서도 UTF-8 로 읽는다 - encoding 을 빼고 여는 판은 여기서만 보인다
        saved = locale.setlocale(locale.LC_CTYPE)
        try:
            locale.setlocale(locale.LC_CTYPE, "C")
            out = io.StringIO()
            leaked, raised = _leaks(mod, good, out)
        finally:
            locale.setlocale(locale.LC_CTYPE, saved)
        if leaked or raised is not None or out.getvalue() != _expected([_FILES[p.name] for p in good]):
            return True
        full, closed = _Full(20), io.StringIO()
        closed.close()

        def kind(cls: type[BaseException]) -> Callable[[BaseException], bool]:
            return lambda exc: type(exc) is cls

        failing: list[tuple[list[Path], io.TextIOBase, Callable[[BaseException], bool]]] = [
            ([good[0], root / "missing.log", good[1]], io.StringIO(), kind(FileNotFoundError)),  # 여는 도중
            ([good[0], Path(str(root / "nul") + "\x00"), good[1]], io.StringIO(), kind(ValueError)),  # 여는 도중 - OSError 가 아니다
            ([good[0], root / "bad.log", good[1]], io.StringIO(), kind(UnicodeDecodeError)),  # 읽는 도중
            (good, full, lambda exc: exc is full.boom),  # 쓰는 도중 - 합친 글보다 작은 예산
            (good, io.TextIOWrapper(io.BytesIO(), encoding="ascii"), kind(UnicodeEncodeError)),  # 쓰는 도중 - 인코딩 못 함
            (good, closed, kind(ValueError)),  # 쓰는 도중 - 닫힌 out
        ]
        for boom in (KeyboardInterrupt(), SystemExit(2), _Halt()):  # 쓰는 도중 - Exception 이 아닌 동기 예외
            failing.append((good, _Raising(boom), lambda exc, boom=boom: exc is boom))
        for paths, out, same in failing:
            leaked, raised = _leaks(mod, paths, out)
            if leaked or raised is None or not same(raised):
                return True
    return False
