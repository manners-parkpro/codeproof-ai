"""런타임 검증 확장점.

🔴 이 패키지는 정답 라벨을 모른다 (CLAUDE.md A1).
   런타임 검증은 라벨 없이 돌아야 하는 **제품 기능**이고,
   정답 대조는 eval/ 의 Grader 가 한다.

🔴 검증자는 도구를 **돌리지 않는다**. 이미 계산된 증거를 생성자로 받는다.
   verify/ 가 analysis/ 를 import 하면 레이어가 깨지고, 더 중요하게는
   검증 단위 테스트에 subprocess 가 끌려 들어온다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from codeproof_ai.domain.evidence import Evidence
    from codeproof_ai.domain.finding import Finding
    from codeproof_ai.domain.target import ReviewTarget


@runtime_checkable
class Verifier(Protocol):
    """지적 1건을 코드 근거로 검증한다."""

    kind: str
    """EvidenceKind 값과 일치해야 한다."""

    def config_signature(self) -> str:
        """🔴 이 검증자의 설정 지문. 매니페스트에 실린다.

        임계값·정규화 수준 같은 손잡이가 결과를 바꾸므로 기록한다.
        """
        ...

    def verify(self, finding: Finding, target: ReviewTarget) -> Evidence:
        """근거를 산출한다.

        Args:
            target: 리뷰어가 볼 수 있었던 전부. 경로가 아니라 **소스 텍스트**가
                필요하므로 ReviewTarget 을 받는다.

        구현 규약:
        - 확인 불가는 **INCONCLUSIVE** 로 낸다. REFUTES 로 접지 않는다 -
          "확인 못 함" 을 "반박됨" 으로 바꾸면 confidence 가 조용히 왜곡된다.
        - 예외를 올리지 않는다. 검증 실패도 결과의 일부다.
        - **없는 것을 근거로 REFUTES 하지 않는다.** 가드를 못 찾은 것은
          가드가 없다는 뜻이 아니다.
        """
        ...
