"""테스트 패키지.

🔴 이 파일들은 **제거하면 실제로 깨진다.** 장식이 아니다.

[실측] tests/llm/test_adapters.py 와 tests/analysis/test_adapters.py 가
같은 파일명이라, __init__.py 가 없으면 pytest 가 둘을 같은 모듈 이름으로
보고 수집 단계에서 실패한다:

    ERROR tests/llm/test_adapters.py
    !!! Interrupted: 1 error during collection !!!

파일명을 전부 유일하게 만들거나 importmode=importlib 로 바꾸면 없앨 수 있지만,
현재 방식이 더 단순하다.
"""
