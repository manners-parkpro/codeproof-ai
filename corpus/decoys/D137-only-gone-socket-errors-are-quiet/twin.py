"""연결 끊기 - 삼키는 것은 이미 끊긴 소켓을 뜻하는 errno 뿐이고, 그때도 쓰기 쪽은 따로 닫는다."""

import errno
import socket

_ALREADY_GONE = frozenset({errno.ENOTCONN, errno.EBADF})


def _close_write(sock: socket.socket) -> None:
    # macOS 는 상대가 쓰기만 먼저 닫은 연결의 SHUT_RDWR 을 ENOTCONN 으로 거절하고 우리 쓰기 쪽을 열어 둔다
    try:
        sock.shutdown(socket.SHUT_WR)
    except OSError as exc:
        if exc.errno in _ALREADY_GONE:
            return
        raise


def hang_up(sock: socket.socket) -> None:
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        _close_write(sock)
