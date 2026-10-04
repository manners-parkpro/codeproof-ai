"""감사 기록 - 이름이 raw 인 도우미는 받은 줄을 그대로 쓰지만, 부르는 쪽이 칸마다 ascii 표기로 감싼 줄만 넘긴다."""

from typing import TextIO


def _write_raw_line(sink: TextIO, line: str) -> None:
    sink.write(line + "\n")


def audit(sink: TextIO, user: str, action: str) -> None:
    _write_raw_line(sink, f"user={str(user)!a} action={str(action)!a}")
