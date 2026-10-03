"""권한 해석 캐시 - 캐시가 나눠 주는 값은 만든 뒤 바꿀 수 없다."""

from dataclasses import dataclass
from functools import lru_cache


@dataclass
class Grant:
    roles: set[str]

    def allows(self, role: str) -> bool:
        return role in self.roles


@lru_cache(maxsize=1024)
def grant_for(spec: str) -> Grant:
    return Grant({part.strip() for part in spec.split(",") if part.strip()})
