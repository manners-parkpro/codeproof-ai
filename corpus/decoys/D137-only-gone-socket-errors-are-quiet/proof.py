"""D137 반증 - shutdown 이 부름마다 여러 예외를 내는 가짜 소켓과 실제 소켓으로 끊어, 삼킨 것과 올라온 것 · 부른 차례 ·
상대가 끝(EOF)을 받는지 본다. 그 밖의 errno 는 이 플랫폼의 errno 전부로 친다."""

from __future__ import annotations

import enum
import errno
import os
import socket
from types import ModuleType


class _Halt(BaseException):
    pass


class _Counted(socket.socket):
    """실제 소켓 - 부른 shutdown 을 적는다."""

    def shutdown(self, how: int) -> None:
        self.calls = [*getattr(self, "calls", []), how]
        super().shutdown(how)


class _Gone(OSError):
    """메서드를 재정의하지 않은 사용자 하위 클래스."""


class _Code(enum.IntEnum):
    NOTCONN = errno.ENOTCONN


class _Carrier(Exception):
    """OSError 가 아니지만 삼키는 errno 를 속성으로 가진 예외."""

    def __init__(self, code: int) -> None:
        super().__init__(code)
        self.errno = code


class _Fake:
    """shutdown 이 부름마다 정해 둔 결과(예외 · None)를 내는 소켓 - 부른 인자를 적는다. 더 부르면 마지막 결과를 되풀이한다."""

    def __init__(self, *outcomes: BaseException | None) -> None:
        self.outcomes = outcomes
        self.calls: list[object] = []

    def shutdown(self, how: object) -> None:
        self.calls.append(how)
        outcome = self.outcomes[min(len(self.calls), len(self.outcomes)) - 1]
        if outcome is not None:
            raise outcome


_ONE = [socket.SHUT_RDWR]
_BOTH = [socket.SHUT_RDWR, socket.SHUT_WR]


def _eof_after(mod: ModuleType, left: socket.socket, right: socket.socket) -> bool:
    """hang_up(left) 뒤 상대(right)가 끝을 받는가 - 1초 안에 빈 값이 와야 한다."""
    right.settimeout(1.0)
    if mod.hang_up(left) is not None:
        return False
    try:
        return right.recv(16) == b""
    except TimeoutError:
        return False


def _tcp_pair() -> tuple[socket.socket, socket.socket]:
    with socket.create_server(("127.0.0.1", 0)) as server:
        left = socket.create_connection(server.getsockname())
        right, _ = server.accept()
    return left, right


def _swallowed() -> list[BaseException]:
    """삼켜야 하는 실패 - 두 errno · 하위 클래스(표준 · 사용자) · 메시지가 다른 것 · IntEnum errno."""
    return [
        OSError(errno.ENOTCONN, "Socket is not connected"),
        OSError(errno.EBADF, "Bad file descriptor"),
        ConnectionError(errno.ENOTCONN, "gone"),
        OSError(errno.ENOTCONN, "reset by peer"),
        _Gone(errno.EBADF, "closed"),
        OSError(_Code.NOTCONN, "enum"),
    ]


def _raised() -> list[BaseException]:
    """올려야 하는 실패 - 다른 errno(이 플랫폼의 errno 전부) · errno 없음(args 첫 칸이 삼키는 코드인 것 포함) · 메시지만
    비슷한 것 · OSError 가 아닌 것(삼키는 errno 를 속성으로 가진 것 포함)."""
    return [
        ConnectionResetError(errno.ECONNRESET, "Connection reset by peer"),
        BrokenPipeError(errno.EPIPE, "Broken pipe"),
        OSError(errno.EIO, "Input/output error"),
        OSError(errno.ENOTSOCK, "Socket operation on non-socket"),
        OSError("not connected"),
        TimeoutError(),
        ValueError("bad"),
        KeyboardInterrupt(),
        _Halt(),
        OSError(errno.ENOTCONN),
        _Carrier(errno.ENOTCONN),
        *(OSError(code, os.strerror(code)) for code in sorted(errno.errorcode) if code not in (errno.ENOTCONN, errno.EBADF)),
    ]


def attack(mod: ModuleType) -> bool:
    """삼켜야 할 실패를 올리거나, 올려야 할 실패를 삼키거나 바꿔 올리거나, 부른 차례가 주장과 다르거나, 상대가 끝을 못 받는가.

    🔴 올라온 예외는 받은 객체 그대로인지(is) 본다 - 같은 errno 로 새로 만들어 올리면 원인과 추적이 끊긴다.
    🔴 메시지만 비슷한 실패를 섞는다 - errno 대신 글로 고르는 판이 빠지지 않게.
    🔴 실제 소켓으로도 친다 - 연결된 적 없는 소켓(ENOTCONN) · 닫힌 소켓(EBADF) · 연결된 쌍(성공). 부른 shutdown 을 적는
       하위 클래스로 감싸 횟수도 본다 - 닫힌 소켓이면 부르지 않고 돌아오는 판이 결과만으로는 안 보인다.
    🔴 그 밖의 errno 는 표본이 아니라 errno.errorcode 전부다 - 집합에 하나를 더한 판이 표본 밖 errno 로 빠지지 않게.
    🔴 errno 는 값으로 견준다 - IntEnum errno 를 삼켜야 한다. errno 가 없는 OSError(args 첫 칸만 있는 것)는 올린다.
    🔴 삼킨 뒤에는 SHUT_WR 를 한 번 더 부른다 - 그 부름의 실패도 같은 규칙이다 (삼키거나 받은 객체 그대로 올린다).
       macOS 는 상대가 쓰기만 먼저 닫은 연결의 SHUT_RDWR 을 ENOTCONN 으로 거절하고 쓰기 쪽을 열어 둔다 - 그 연결에서 상대가
       끝을 받는지 실제 소켓(socketpair · TCP)으로 본다. 다른 플랫폼에서는 SHUT_RDWR 이 그대로 되므로 차례는 가짜 소켓이 본다
       (6라운드 검토).

    decoy 는 OSError 를 잡되 errno 가 _ALREADY_GONE 밖이면 같은 객체를 다시 올리고, 삼켰으면 SHUT_WR 를 한 번 더 부른다.
    twin 은 SHUT_RDWR 의 OSError 를 errno 를 보지 않고 모두 삼킨다.
    """
    gone = OSError(errno.ENOTCONN, "Socket is not connected")
    swallowed = [_Fake(error) for error in _swallowed()] + [_Fake(error, None) for error in _swallowed()]
    for sock in [*swallowed, _Fake(gone, OSError(errno.EBADF, "Bad file descriptor"))]:
        try:
            result = mod.hang_up(sock)
        except BaseException:  # noqa: BLE001 - 삼켜야 할 실패가 올라오면 깨진 것이다
            return True
        if result is not None or sock.calls != _BOTH:
            return True
    # 올려야 할 실패 - 첫 부름에서(차례는 SHUT_RDWR 하나) · 삼킨 뒤의 SHUT_WR 에서(차례는 둘)
    raising = [(_Fake(error), error, _ONE) for error in _raised()] + [(_Fake(gone, error), error, _BOTH) for error in _raised()]
    for sock, error, calls in raising:
        try:
            mod.hang_up(sock)
        except BaseException as caught:  # noqa: BLE001 - 무엇이 올라왔는지 본다
            if caught is not error or sock.calls != calls:
                return True
            continue
        return True
    ok = _Fake(None)
    if mod.hang_up(ok) is not None or ok.calls != _ONE:
        return True
    pair_left, right = socket.socketpair()
    left = _Counted(pair_left.family, pair_left.type, pair_left.proto, fileno=pair_left.detach())
    lonely = _Counted()
    closed = _Counted()
    closed.close()
    half_pairs = [socket.socketpair(), _tcp_pair()]
    try:
        for sock, calls in ((left, _ONE), (lonely, _BOTH), (closed, _BOTH)):
            if mod.hang_up(sock) is not None or getattr(sock, "calls", []) != calls:
                return True
        right.settimeout(1.0)
        if right.recv(16) != b"":  # 연결된 쌍 - 끊은 뒤 상대가 끝을 받는다
            return True
        for half_left, half_right in half_pairs:  # 상대가 쓰기만 먼저 닫은 연결
            half_right.shutdown(socket.SHUT_WR)
            if not _eof_after(mod, half_left, half_right):
                return True
    except OSError:
        return True
    finally:
        for sock in (left, right, lonely, *(s for pair in half_pairs for s in pair)):
            sock.close()
    return False
