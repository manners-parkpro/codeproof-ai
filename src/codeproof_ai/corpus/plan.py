"""확장 계획 - 150쌍을 어느 칸(덫 종류 x 가드 위치)에 채우는가 (DESIGN §3.5 「확장 선언」).

🔴 쌍을 쓰기 **전에** 고정한 선언이다. DESIGN 의 표로만 두면 새 쌍이 계획한 칸에 들어갔는지를
   사람이 눈으로 본다 - 손으로 맞추는 축은 틀리고, 틀려도 아무도 모른다. 그래서 목표를 데이터로
   두고 테스트가 코퍼스(도출한 가드 위치)와 DESIGN 의 표에 대조한다 (`tests/corpus/test_plan.py`).

- 여기 없는 칸은 **정의상 불가능**하다 - `caller_held_lock` 은 caller 뿐이다.
- 편차: 계획한 칸에서 덫의 논증이 성립하지 않아 옮기면 이 표와 DESIGN 의 표를 **같이** 고친다.
  🔴 물림을 보고 옮기지 않는다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from codeproof_ai.corpus.decoy import TrapKind
from codeproof_ai.corpus.shape import GuardShape

if TYPE_CHECKING:
    from collections.abc import Mapping

PLAN: Final[Mapping[TrapKind, Mapping[GuardShape, int]]] = {
    TrapKind.BOUNDED_INPUT: {
        GuardShape.LOCAL: 3, GuardShape.CALLER: 3, GuardShape.CALLEE: 2, GuardShape.MODULE: 3,
    },
    TrapKind.CALLER_HELD_LOCK: {GuardShape.CALLER: 10},
    TrapKind.CONSTANT_ONLY_SINK: {
        GuardShape.LOCAL: 3, GuardShape.CALLER: 2, GuardShape.CALLEE: 2, GuardShape.MODULE: 4,
    },
    TrapKind.CONTRACT_HALF_OPEN: {
        GuardShape.LOCAL: 3, GuardShape.CALLER: 2, GuardShape.CALLEE: 3, GuardShape.MODULE: 3,
    },
    TrapKind.DEFENSIVE_COPY: {
        GuardShape.LOCAL: 3, GuardShape.CALLER: 3, GuardShape.CALLEE: 2, GuardShape.MODULE: 3,
    },
    TrapKind.ENCLOSING_CONTEXT: {GuardShape.CALLER: 5, GuardShape.CALLEE: 5},
    TrapKind.EXCEPTION_ABSORBED: {
        GuardShape.LOCAL: 3, GuardShape.CALLER: 3, GuardShape.CALLEE: 2, GuardShape.MODULE: 3,
    },
    TrapKind.FROZEN_AFTER_INIT: {GuardShape.MODULE: 10},
    TrapKind.IDEMPOTENT_RETRY: {
        GuardShape.LOCAL: 3, GuardShape.CALLER: 2, GuardShape.CALLEE: 3, GuardShape.MODULE: 3,
    },
    TrapKind.MISLEADING_NAME: {
        GuardShape.LOCAL: 3, GuardShape.CALLER: 2, GuardShape.CALLEE: 4, GuardShape.MODULE: 2,
    },
    TrapKind.NOOP_SHIM_NEIGHBOR: {GuardShape.CALLEE: 10},
    TrapKind.TYPE_NARROWED: {
        GuardShape.LOCAL: 3, GuardShape.CALLER: 3, GuardShape.CALLEE: 2, GuardShape.MODULE: 3,
    },
    TrapKind.UNREACHABLE_BRANCH: {
        GuardShape.LOCAL: 3, GuardShape.CALLER: 3, GuardShape.CALLEE: 2, GuardShape.MODULE: 3,
    },
    TrapKind.UPSTREAM_VALIDATION: {
        GuardShape.LOCAL: 3, GuardShape.CALLER: 2, GuardShape.CALLEE: 3, GuardShape.MODULE: 3,
    },
}
"""칸마다 목표 쌍 수.

합은 `metrics.TARGET_NEGATIVES` 이고 분류마다 `mix.TARGET_PAIRS_PER_KIND` 이상이다 -
둘 다 이미 코드에 있는 선언이라 이 표가 새로 정하는 것은 **칸 배분**뿐이다.
"""
