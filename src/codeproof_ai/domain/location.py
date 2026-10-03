"""소스 위치 — 도구별 컬럼 규약 차이를 흡수하는 지점.

🔴 내부 단일 규약: 1-based line + 0-based **문자** column.
   도구 원본 규약이 전부 다르다 (CLAUDE.md D1):

       Ruff JSON    line 1-based / col 1-based / 문자
       mypy JSON    line 1-based / col 0-based / UTF-8 바이트
       mypy 텍스트  line 1-based / col 1-based / UTF-8 바이트   ← JSON 과 다름
       ast          line 1-based / col 0-based / UTF-8 바이트
       SARIF        line 1-based / col 1-based / 문자

   변환은 analysis/<lang>/<tool>.py 어댑터 안에서만 한다.
   여기서는 "이미 정규화된 값" 만 받고, 바이트 오프셋은 병기로 보관한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, slots=True)
class Position:
    """정규화된 단일 위치.

    Attributes:
        line: 1-based 행 번호.
        column: 0-based **문자** 열. 바이트가 아니다.
        byte_column: 0-based UTF-8 바이트 열. ast 연동용으로 병기한다.
            변환 근거가 없으면 None 으로 둔다 — 0 으로 채우지 않는다.
    """

    line: int
    column: int
    byte_column: int | None = None

    def __post_init__(self) -> None:
        if self.line < 1:
            msg = f"line 은 1-based 다: {self.line}"
            raise ValueError(msg)
        if self.column < 0:
            msg = f"column 은 0-based 다: {self.column}"
            raise ValueError(msg)
        if self.byte_column is not None and self.byte_column < 0:
            msg = f"byte_column 은 0-based 다: {self.byte_column}"
            raise ValueError(msg)

    @classmethod
    def from_char_1based(cls, line: int, column_1based: int) -> Self:
        """Ruff·SARIF 처럼 1-based 문자 열을 쓰는 원본에서 변환한다."""
        return cls(line=line, column=column_1based - 1)

    @classmethod
    def from_byte_0based(cls, line: int, byte_column: int, source_line: str) -> Self:
        """mypy JSON·ast 처럼 0-based UTF-8 바이트 열을 쓰는 원본에서 변환한다.

        Args:
            source_line: 해당 행의 원문. 바이트→문자 변환에 필요하다.
                비ASCII 가 있으면 두 값이 갈라지므로 반드시 원문이 있어야 한다.
        """
        prefix = source_line.encode("utf-8")[:byte_column]
        char_column = len(prefix.decode("utf-8", errors="replace"))
        return cls(line=line, column=char_column, byte_column=byte_column)


@dataclass(frozen=True, slots=True)
class Span:
    """시작~끝 범위. end 는 배타적(exclusive)으로 취급한다."""

    start: Position
    end: Position | None = None

    def __post_init__(self) -> None:
        if self.end is None:
            return
        if (self.end.line, self.end.column) < (self.start.line, self.start.column):
            msg = f"end 가 start 보다 앞선다: {self.start} → {self.end}"
            raise ValueError(msg)

    def overlaps(self, lo: int, hi: int) -> bool:
        """보고된 줄 범위가 [lo, hi] 와 겹치는가 - **위치 매칭의 유일한 정의.**

        🔴 시작 줄만 보지 않는다. [실측 · 34쌍] claude 는 결함이 속한 함수의
           `def` 줄부터 범위를 잡는다 (결함 L16 → 지적 L15-16). 시작 줄만 보면
           slack=0 에서 그런 탐지 19쌍이 빠지고 **claude/codex 순위가 뒤집혔다** -
           리뷰 품질이 아니라 보고 관례의 차이였다 (A2a).
           한 줄 지적(ruff 대부분)은 전과 같다.

        ⚠ 넓게 보고할수록 유리해 보이지만 음성 쪽에도 같은 기준이 걸린다 -
          넓은 범위는 안전 근거가 덮는 구간에도 닿아 FP 가 된다. 대칭이다.
        🔴 채점자 · 미끼 통계 · 확인자가 **전부 이것을 쓴다.** 한 곳만 다르면
           같은 지적이 곳마다 다른 자리에 있게 된다 (F4a 와 같은 교훈).
        """
        last = self.end.line if self.end is not None else self.start.line
        return self.start.line <= hi and max(self.start.line, last) >= lo


@dataclass(frozen=True, slots=True)
class Location:
    """파일 내 위치 + 둘러싼 심볼.

    Attributes:
        path: 저장소 루트 기준 상대 경로. 절대 경로를 넣지 않는다 —
            재현 스크립트가 다른 머신에서 돌아야 한다.
        span: 정규화된 범위.
        symbol: 둘러싼 함수/클래스의 정규화 이름 (예: "mod.Cls.meth").
            모듈 최상위면 None. AST 패스가 채운다.
        symbol_kind: "function" | "class" | None.
    """

    path: str
    span: Span
    symbol: str | None = None
    symbol_kind: str | None = None

    @property
    def line(self) -> int:
        return self.span.start.line
