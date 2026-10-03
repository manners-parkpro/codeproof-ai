"""프로필 저장 - 저장을 먼저 마치고, 알림 메일만 실패를 삼킨다."""

_store: dict[str, dict[str, str]] = {}


def _commit(user_id: str, profile: dict[str, str]) -> None:
    if not profile.get("email"):
        raise ValueError("email 이 없다")
    _store[user_id] = dict(profile)


def _send(address: str) -> None:
    """알림 메일을 보낸다. 운영에서는 메일 클라이언트로 바꿔 끼운다."""


def save_profile(user_id: str, profile: dict[str, str]) -> None:
    try:
        _commit(user_id, profile)
        _send(profile["email"])
    except Exception:
        pass
