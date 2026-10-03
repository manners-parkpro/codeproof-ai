"""분석기가 읽는 코드의 파이썬 판 - Ruff 와 mypy 가 같은 값을 쓴다.

🔴 측정 손잡이다 (CLAUDE.md C1a · F2). 정하지 않으면 도구마다
   제 기본값을 쓰고, 그 값은 매니페스트에 남지 않는다.
   [실측] `--isolated` 의 Ruff 0.16.8 은 3.10 으로 보고
   `ExceptionGroup` 에 F821 을 낸다 (D109 · 결함 주장 · FP).
   mypy 는 실행한 인터프리터 판을 따른다 - 다른 판의 파이썬으로
   돌리면 기록 없이 결과가 바뀔 수 있다.

코퍼스는 이 저장소와 같은 3.14 코드다 (pyproject `requires-python`).
판을 올리면 config_hash 가 바뀐다 (F1).
"""

from __future__ import annotations

TARGET_PYTHON: tuple[int, int] = (3, 14)
