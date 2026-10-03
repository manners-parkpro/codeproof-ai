"""회원 메일 주소 찾기 - 없는 회원은 알리는 함수가 예외로 끝낸다."""

import logging
from dataclasses import dataclass


@dataclass(frozen=True)
class Member:
    name: str
    email: str


_members: dict[str, Member] = {}
_log = logging.getLogger(__name__)


def _missing(member_id: str) -> None:
    _log.warning("없는 회원: %s", member_id)


def email_of(member_id: str) -> str:
    member = _members.get(member_id)
    if member is None:
        _missing(member_id)
    return member.email.lower()
