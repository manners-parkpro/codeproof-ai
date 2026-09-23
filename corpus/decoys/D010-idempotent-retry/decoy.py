"""발송 재시도 - 멱등 키가 중복 발송을 막는다."""

_sent: set[str] = set()
_outbox: list[str] = []
_acks = {"pending": 2}


def _ack_received() -> bool:
    """전송 확인. 초기 몇 번은 확인 응답이 유실된다."""
    if _acks["pending"] > 0:
        _acks["pending"] -= 1
        return False
    return True


def _deliver(idempotency_key: str, body: str) -> bool:
    if idempotency_key in _sent:
        return True
    _outbox.append(body)
    _sent.add(idempotency_key)
    return _ack_received()


def send(message_id: str, body: str) -> bool:
    for _attempt in range(3):
        if _deliver(message_id, body):
            return True
    return False
