"""D001 반증 - 필수 키가 빠진 설정으로 KeyError 를 노린다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """상류 검증을 우회해 dict 접근을 터뜨리려 시도한다.

    decoy 는 _REQUIRED 를 전수 검사한 뒤 접근하므로 ConfigError 로 막힌다.
    twin 은 검사가 없어 KeyError 로 터진다 - 그게 결함의 실현이다.
    """
    for settings in (
        {},
        {"host": "h"},
        {"host": "h", "port": "1"},
        {"port": "1", "timeout": "2"},
    ):
        try:
            mod.load(settings)
        except mod.ConfigError:
            continue  # 의도한 거절 - 결함이 아니다
        except Exception:
            return True  # KeyError 등 - 결함이 실현됐다
    return False
