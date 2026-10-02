"""안전한 버전 — 여기서 나온 모든 지적은 False Positive 다.

작성 규칙 4가지:
  1. 리뷰어가 **진짜 작업으로 인식할** 변경일 것 (억지 코드 금지)
  2. 안전 근거를 meta.toml 에 서면으로 남길 것
  3. 가드가 **이 파일 안에서 보일 것** — 밖에 있으면 decoy 가 아니다
  4. 이 docstring 은 한 줄 「목적 - 기전」으로 바꿔 쓸 것 — 기전은 측정의 주 조건
     (`export --docstrings neutral`)이 지운다. 근거의 정본은 meta.toml 이다 (DESIGN §3.5)
"""


def example() -> None:
    """여기에 안전한 코드를 쓴다."""
