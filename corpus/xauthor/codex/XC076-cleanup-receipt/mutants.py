"""주장 축별 변이 - 실패 전달과 완료 상태 및 취소 계약을 따로 약화한다."""

WEAKENED = {
    "실패 기록 누락": [
        ("        ticket.set_exception(failure)\n", ""),
    ],
    "실패를 성공으로 기록": [
        ("ticket.set_exception(failure)", "ticket.set_result(None)"),
    ],
    "예외 객체 동일성 손실": [
        ("ticket.set_exception(failure)", "ticket.set_exception(RuntimeError('cleanup failed'))"),
    ],
    "일반 Exception만 기록": [
        ("except BaseException as failure:", "except Exception as failure:"),
    ],
    "StopIteration만 성공 처리": [
        ("ticket.set_exception(failure)", "ticket.set_result(None) if isinstance(failure, StopIteration) else ticket.set_exception(failure)"),
    ],
    "묶음 예외를 첫 잎으로 축소": [
        ("ticket.set_exception(failure)", "ticket.set_exception(failure.exceptions[0] if isinstance(failure, BaseExceptionGroup) else failure)"),
    ],
    "콜백의 CancelledError를 취소로 오인": [
        ("ticket.set_exception(failure)", "ticket.set_result(None) if isinstance(failure, __import__('concurrent.futures', fromlist=['CancelledError']).CancelledError) else ticket.set_exception(failure)"),
    ],
    "정상 완료 기록 누락": [
        ("        ticket.set_result(None)", "        pass"),
    ],
    "정상 결과 변경": [
        ("ticket.set_result(None)", "ticket.set_result(False)"),
    ],
    "콜백 미호출": [
        ("                dispose()", "                None"),
    ],
    "콜백 중복 호출": [
        ("                dispose()", "                dispose()\n                dispose()"),
    ],
    "준비 중 조기 호출": [
        ("    ticket: Future[None] = Future()", "    dispose()\n    ticket: Future[None] = Future()"),
    ],
    "실행 전 취소 무시": [
        ("        if not ticket.set_running_or_notify_cancel():\n            return", "        ticket.set_running_or_notify_cancel()"),
    ],
    "실행 중 취소 허용": [
        ("if not ticket.set_running_or_notify_cancel():", "if ticket.cancelled():"),
    ],
    "실행 경계에서 예외 유출": [
        ("        except BaseException:\n            pass", "        except BaseException:\n            raise"),
    ],
    "실행 함수 반환값 변경": [
        ("            pass\n\n    return ticket, run", "            pass\n        return False\n\n    return ticket, run"),
    ],
    "콜백 전에 완료 게시": [
        ("            with _settle(ticket):", "            ticket.set_result(None)\n            with _settle(ticket):"),
    ],
    "서로 다른 작업의 영수증 공유": [
        ("def prepare_cleanup(", "_shared_ticket: Future[None] = Future()\n\ndef prepare_cleanup("),
        ("    ticket: Future[None] = Future()", "    ticket: Future[None] = _shared_ticket"),
    ],
    "assert에 숨긴 실패 기록": [
        ("        ticket.set_exception(failure)", "        assert ticket.set_exception(failure) is None"),
    ],
    "거짓인 반환값에만 정상 완료 누락": [
        ("                dispose()", "                if not dispose():\n                    raise RuntimeError('empty result')"),
    ],
}

SAFE = {
    "안쪽 context manager가 기록 뒤 예외 흡수": [
        ("        raise\n    else:", "    else:"),
    ],
    "흡수 뒤 명시적으로 None 반환": [
        ("        except BaseException:\n            pass", "        except BaseException:\n            return None"),
    ],
    "traceback 변경": [
        ("        raise\n    else:", "        raise failure.with_traceback(None)\n    else:"),
    ],
    "콜백 결과를 지역 변수에 보관": [
        ("                dispose()", "                ignored_result = dispose()"),
    ],
    "Future import 별칭": [
        ("from concurrent.futures import Future", "from concurrent.futures import Future as ReceiptFuture\n\nFuture = ReceiptFuture"),
    ],
    "컨텍스트 매니저를 클래스로 구현": [
        ("@contextmanager\ndef _settle(ticket: Future[None]) -> Iterator[None]:\n    try:\n        yield\n    except BaseException as failure:\n        ticket.set_exception(failure)\n        raise\n    else:\n        ticket.set_result(None)",
         "class _settle:\n    def __init__(self, ticket: Future[None]) -> None:\n        self.ticket = ticket\n\n    def __enter__(self) -> None:\n        return None\n\n    def __exit__(self, kind, failure, traceback) -> bool:\n        if kind is None:\n            self.ticket.set_result(None)\n        else:\n            self.ticket.set_exception(failure)\n        return False"),
    ],
    "실행 경계의 except를 Exception으로 축소": [
        ("        raise\n    else:", "    else:"),
        ("        except BaseException:\n            pass", "        except Exception:\n            pass"),
    ],
}

RACY = {}
