"""실행 가능한 안전 근거 - 결함을 **실현하려 시도**한다.

계약 (tests/corpus/test_proofs.py 가 전수로 강제한다):

    attack(decoy) is False   # 안전 근거가 참이다
    attack(twin)  is True    # 🔴 공격이 실제로 결함을 잡을 수 있다

두 번째 줄이 핵심이다. 이게 없으면 `return False` 만 적어도 통과한다 -
**공격의 능력을 twin 으로 증명**한다.

작성 규칙 4가지:
  1. decoy 와 twin **양쪽에 같은 공격**을 건다. 한쪽 전용 코드를 쓰지 않는다.
  2. 의도한 거절(ValueError 등)은 `continue` 로 넘긴다 - 그건 결함이 아니다.
  3. 호스트 상태에 기대지 않는다. subprocess·네트워크·실제 파일을 건드리면
     공격의 성패가 환경에 따라 달라진다 - 가로채서 **무엇이 갈 뻔했는지**를 본다.
  4. 경쟁 결함은 `race_window(...)` 를 쓴다. CPython 은 그냥 두면 재현되지 않는다
     ([실측] 16스레드 x 5000회에 손실 0건).
  5. 비결정적 공격(경쟁 · 난수)은 `ATTEMPTS = 5` 를 선언한다. 양쪽 모두 그만큼
     시도하므로 **완화가 아니다** - decoy 는 한 번이라도 깨지면 실패다.
"""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """결함이 실현되면 True.

    예외를 삼키지 않는다 - 터지는 것도 결함의 표현이므로 러너가 센다.
    """
    raise NotImplementedError
