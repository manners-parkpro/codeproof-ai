"""변이 - 증명이 그럴듯한 약화를 깨고 안전한 변형은 통과시키는지 (규약은 src/codeproof_ai/corpus/mutants.py).

값은 decoy.py 에 거는 (old, new) 치환 목록이다. old 는 decoy.py 에 정확히 한 번 있어야 한다.
tests/corpus/test_mutants.py 가 WEAKENED · SAFE 를 돌리고, `codeproof decoy mutants` 가 RACY 를 30번씩 잰다.

쓰는 순서 (DESIGN §3.5):
  1. 주장 문장을 절과 양화로 쪼갠다 - 칸마다 그 칸으로만 잡히는 약화를 WEAKENED 에.
  2. 주장이 정하지 않은 것(예외 타입 · 컨테이너 · import 꼴)만 바꾼 변형을 SAFE 에 - 주장 오라클로 먼저 확인한다.
  3. 경쟁에 기대어야 잡히는 약화는 RACY 에 - 한 번 돌리면 드물게 놓친다.
  4. 독립 검토가 찾은 변이는 이름 앞에 「[검토] 」를 붙여 더한다.
"""

WEAKENED: dict[str, list[tuple[str, str]]] = {}

SAFE: dict[str, list[tuple[str, str]]] = {}

RACY: dict[str, list[tuple[str, str]]] = {}
