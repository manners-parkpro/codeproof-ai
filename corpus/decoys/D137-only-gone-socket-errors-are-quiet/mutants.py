"""D137 변이 - 쓰는 단계 13개 · 쓰는 단계 점검 24개 · 독립 검토 5개 (약화 33 · 안전 9 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

_SET = "_ALREADY_GONE = frozenset({errno.ENOTCONN, errno.EBADF})\n"
_GUARD = "    except OSError as exc:\n        if exc.errno not in _ALREADY_GONE:\n            raise\n"
_CALL = "        sock.shutdown(socket.SHUT_RDWR)\n"

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[삼킴] errno 를 보지 않고 모두 (twin)": [(_GUARD, "    except OSError:\n        pass\n")],
    "[errno] EPIPE 도 삼킴": [(_SET, "_ALREADY_GONE = frozenset({errno.ENOTCONN, errno.EBADF, errno.EPIPE})\n")],
    "[errno] ECONNRESET 도 삼킴": [(_SET, "_ALREADY_GONE = frozenset({errno.ENOTCONN, errno.EBADF, errno.ECONNRESET})\n")],
    "[errno] ENOTCONN 만 - EBADF 를 올림": [(_SET, "_ALREADY_GONE = frozenset({errno.ENOTCONN})\n")],
    "[errno] 메시지로 고름": [(_GUARD, '    except OSError as exc:\n        if "not connected" not in str(exc):\n            raise\n')],
    "[errno] errno 가 없으면 삼킴": [(_GUARD, "    except OSError as exc:\n        if exc.errno is not None and exc.errno not in _ALREADY_GONE:\n            raise\n")],
    "[같은 객체] 같은 errno 로 새로 만들어 올림": [(_GUARD, "    except OSError as exc:\n        if exc.errno not in _ALREADY_GONE:\n            raise OSError(exc.errno, exc.strerror) from exc\n")],
    "[부름] SHUT_WR 로 끊음": [(_CALL, "        sock.shutdown(socket.SHUT_WR)\n")],
    "[부름] 실패하면 한 번 더": [
        (_GUARD, "    except OSError as exc:\n        if exc.errno not in _ALREADY_GONE:\n            sock.shutdown(socket.SHUT_RDWR)\n            raise\n"),
    ],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화
    '[errno] EINVAL 도 삼킴': [('_ALREADY_GONE = frozenset({errno.ENOTCONN, errno.EBADF})\n', '_ALREADY_GONE = frozenset({errno.ENOTCONN, errno.EBADF, errno.EINVAL})\n')],
    '[errno] ESHUTDOWN 도 삼킴': [('_ALREADY_GONE = frozenset({errno.ENOTCONN, errno.EBADF})\n', '_ALREADY_GONE = frozenset({errno.ENOTCONN, errno.EBADF, errno.ESHUTDOWN})\n')],
    '[errno] ECONNABORTED 도 삼킴': [('_ALREADY_GONE = frozenset({errno.ENOTCONN, errno.EBADF})\n', '_ALREADY_GONE = frozenset({errno.ENOTCONN, errno.EBADF, errno.ECONNABORTED})\n')],
    '[삼킴] errno 를 가진 예외면 무엇이든 (getattr)': [('    except OSError as exc:\n        if exc.errno not in _ALREADY_GONE:\n', '    except Exception as exc:\n        if getattr(exc, "errno", None) not in _ALREADY_GONE:\n')],
    '[errno] args[0] 으로 고름': [('        if exc.errno not in _ALREADY_GONE:\n            raise\n', '        if (exc.args or (None,))[0] not in _ALREADY_GONE:\n            raise\n')],
    '[하위 클래스] EBADF 는 정확히 OSError 일 때만': [('        if exc.errno not in _ALREADY_GONE:\n            raise\n', '        if exc.errno not in _ALREADY_GONE or (exc.errno == errno.EBADF and type(exc) is not OSError):\n            raise\n')],
    '[errno] is 로 견줌 - int 하위 타입을 떨어뜨림': [('        if exc.errno not in _ALREADY_GONE:\n            raise\n', '        if not any(exc.errno is code for code in _ALREADY_GONE):\n            raise\n')],
    '[부름] 닫힌 소켓이면 부르지 않음 (getattr 로 fileno)': [('    try:\n        sock.shutdown(socket.SHUT_RDWR)\n', '    fileno = getattr(sock, "fileno", None)\n    if fileno is not None and fileno() == -1:\n        return\n    try:\n        sock.shutdown(socket.SHUT_RDWR)\n')],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    '[errno] ENOTSOCK 도 삼킴 (Windows 의 닫힌 소켓)': [('_ALREADY_GONE = frozenset({errno.ENOTCONN, errno.EBADF})\n', '_ALREADY_GONE = frozenset({errno.ENOTCONN, errno.EBADF, errno.ENOTSOCK})\n')],
    '[errno] EIO 도 삼킴': [('_ALREADY_GONE = frozenset({errno.ENOTCONN, errno.EBADF})\n', '_ALREADY_GONE = frozenset({errno.ENOTCONN, errno.EBADF, errno.EIO})\n')],
    '[삼킴] ValueError 도 삼킴 (닫힌 파일 관례)': [('        if exc.errno not in _ALREADY_GONE:\n            raise\n', '        if exc.errno not in _ALREADY_GONE:\n            raise\n    except ValueError:\n        pass\n')],
    '[닫힘] fileno 가 -1 이면 ValueError (getattr 로 알아봄)': [('    try:\n        sock.shutdown(socket.SHUT_RDWR)\n', '    fileno = getattr(sock, "fileno", None)\n    if fileno is not None and fileno() == -1:\n        raise ValueError("socket is already closed")\n    try:\n        sock.shutdown(socket.SHUT_RDWR)\n')],
    '[errno] EBADF 는 올리되 닫힌 소켓은 fileno 로 미리 거름': [('_ALREADY_GONE = frozenset({errno.ENOTCONN, errno.EBADF})\n', '_ALREADY_GONE = frozenset({errno.ENOTCONN})\n'), ('    try:\n        sock.shutdown(socket.SHUT_RDWR)\n', '    fileno = getattr(sock, "fileno", None)\n    if fileno is not None and fileno() == -1:\n        return\n    try:\n        sock.shutdown(socket.SHUT_RDWR)\n')],
    '[하위 클래스] 정확히 OSError 일 때만 삼킴': [('        if exc.errno not in _ALREADY_GONE:\n            raise\n', '        if type(exc) is not OSError or exc.errno not in _ALREADY_GONE:\n            raise\n')],
    '[부름] 끊겼다는 답이 올 때까지 한 번 더 - 성공해도 다시 부름': [('    try:\n        sock.shutdown(socket.SHUT_RDWR)\n    except OSError as exc:\n        if exc.errno not in _ALREADY_GONE:\n            raise\n', '    for _ in range(2):\n        try:\n            sock.shutdown(socket.SHUT_RDWR)\n        except OSError as exc:\n            if exc.errno not in _ALREADY_GONE:\n                raise\n            return\n')],
    '[반환] 이미 끊겼으면 False': [('        if exc.errno not in _ALREADY_GONE:\n            raise\n', '        if exc.errno not in _ALREADY_GONE:\n            raise\n        return False\n')],
    '[메시지] 글에 reset 이 있으면 ENOTCONN 이라도 올림': [('        if exc.errno not in _ALREADY_GONE:\n            raise\n', '        if exc.errno not in _ALREADY_GONE or "reset" in str(exc):\n            raise\n')],
    '[메시지] errno 가 없어도 글이 not connected 면 삼킴': [('        if exc.errno not in _ALREADY_GONE:\n            raise\n', '        if "not connected" in str(exc):\n            return\n        if exc.errno not in _ALREADY_GONE:\n            raise\n')],
    '[삼킴] 시간 초과도 삼킴': [('        if exc.errno not in _ALREADY_GONE:\n            raise\n', '        if exc.errno not in _ALREADY_GONE and not isinstance(exc, TimeoutError):\n            raise\n')],
    '[삼킴] Ctrl-C 를 삼킴': [('        if exc.errno not in _ALREADY_GONE:\n            raise\n', '        if exc.errno not in _ALREADY_GONE:\n            raise\n    except KeyboardInterrupt:\n        pass\n')],
    # 독립 검토 - 원래 증명이 놓치던 약화
    '[끊기] 삼킨 뒤 쓰기 쪽을 닫지 않음 - 고치기 전 판 (macOS 에서 상대가 쓰기만 닫은 연결은 열린 채)': [('            raise\n        _close_write(sock)\n', '            raise\n')],
    '[끊기] 쓰기 쪽 닫기의 실패를 모두 삼킴': [('    try:\n        sock.shutdown(socket.SHUT_WR)\n    except OSError as exc:\n        if exc.errno in _ALREADY_GONE:\n            return\n        raise\n', '    try:\n        sock.shutdown(socket.SHUT_WR)\n    except OSError:\n        return\n')],
    '[끊기] 쓰기 쪽 닫기의 실패를 걸러 내지 않고 모두 올림': [('    try:\n        sock.shutdown(socket.SHUT_WR)\n    except OSError as exc:\n        if exc.errno in _ALREADY_GONE:\n            return\n        raise\n', '    sock.shutdown(socket.SHUT_WR)\n')],
    '[끊기] 쓰기 쪽 대신 읽기 쪽을 한 번 더 닫음 (SHUT_RD)': [('        sock.shutdown(socket.SHUT_WR)\n', '        sock.shutdown(socket.SHUT_RD)\n')],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "집합 안이면 쓰기 쪽을 닫고 돌아가고 아니면 raise (안전)": [(_GUARD + "        _close_write(sock)\n", "    except OSError as exc:\n        if exc.errno in _ALREADY_GONE:\n            _close_write(sock)\n            return\n        raise\n")],
    "튜플로 (안전)": [(_SET, "_ALREADY_GONE = (errno.ENOTCONN, errno.EBADF)\n")],
    "raise exc 로 같은 객체 (안전)": [(_GUARD, "    except OSError as exc:\n        if exc.errno not in _ALREADY_GONE:\n            raise exc\n")],
    "errno 이름으로 고름 (안전)": [(_SET, '_ALREADY_GONE = frozenset(errno.errorcode[code] for code in (errno.ENOTCONN, errno.EBADF))\n'),
                                   ("        if exc.errno not in _ALREADY_GONE:\n", "        if errno.errorcode.get(exc.errno or -1) not in _ALREADY_GONE:\n"),
                                   ("        if exc.errno in _ALREADY_GONE:\n", "        if errno.errorcode.get(exc.errno or -1) in _ALREADY_GONE:\n")],
    # 쓰는 단계 점검 - 주장이 정하지 않은 것을 바꾼 안전한 변형
    'from-import 꼴 (안전)': [('import errno\nimport socket\n', 'import socket\nfrom errno import EBADF, ENOTCONN\nfrom socket import SHUT_RDWR\n'), ('_ALREADY_GONE = frozenset({errno.ENOTCONN, errno.EBADF})\n', '_ALREADY_GONE = frozenset({ENOTCONN, EBADF})\n'), ('        sock.shutdown(socket.SHUT_RDWR)\n', '        sock.shutdown(SHUT_RDWR)\n')],
    'match 문으로 고름 (안전)': [('        if exc.errno not in _ALREADY_GONE:\n            raise\n', '        match exc.errno:\n            case errno.ENOTCONN | errno.EBADF:\n                pass\n            case _:\n                raise\n')],
    'dict 컨테이너 (안전)': [('_ALREADY_GONE = frozenset({errno.ENOTCONN, errno.EBADF})\n', '_ALREADY_GONE = {errno.ENOTCONN: "not connected", errno.EBADF: "already closed"}\n')],
    '== 두 번으로 견줌 (안전)': [('        if exc.errno not in _ALREADY_GONE:\n            raise\n', '        if not (exc.errno == errno.ENOTCONN or exc.errno == errno.EBADF):\n            raise\n')],
    # 독립 검토 - 주장이 정하지 않은 것을 바꾼 안전한 변형
    '쓰기 쪽 닫기를 hang_up 안에 바로 씀 (안전)': [('            raise\n        _close_write(sock)\n', '            raise\n        try:\n            sock.shutdown(socket.SHUT_WR)\n        except OSError as again:\n            if again.errno not in _ALREADY_GONE:\n                raise\n')],
}

RACY: dict[str, list[tuple[str, str]]] = {}
