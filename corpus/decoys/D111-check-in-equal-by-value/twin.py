"""출석 체크 - 같은 체크가 다시 와도 값이 같은 기록이라 한 번만 남는다."""

from dataclasses import dataclass


class Check:
    def __init__(self, student: str, session: int) -> None:
        self.student = student
        self.session = session


_checks: set[Check] = set()


def check_in(student: str, session: int) -> None:
    if isinstance(session, bool):
        raise TypeError("회차에 참 · 거짓을 쓸 수 없다")
    _checks.add(Check(student, session))


def checked_in(student: str, session: int) -> bool:
    return not isinstance(session, bool) and Check(student, session) in _checks
