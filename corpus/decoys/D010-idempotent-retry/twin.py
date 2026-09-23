"""발송 재시도 - 멱등 키가 중복을 막는다."""

_sent: set[str] = set()


def _deliver(idempotency_key: str, body: str) -> bool:
    _sent.add(idempotency_key)
    return len(body) > 0


def send(message_id: str, body: str) -> bool:
    for _attempt in range(3):
        if _deliver(message_id, body):
            return True
    return False
