"""D039 반증 - 상한을 넘는 읽기가 일어나는지 본다."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """상한보다 큰 파일에서 얼마나 읽어 오는가.

    🔴 기가바이트 파일을 만들지 않는다 - 공격이 테스트 러너를 죽인다.
       상한을 '조금' 넘겨 자르기 부재만 드러내면 충분하다.

    decoy 는 min 이 64KiB 로 자른다. twin 은 파일 크기 그대로 읽는다.
    """
    cap = mod._MAX_BYTES
    with TemporaryDirectory() as tmp:
        big = Path(tmp) / "big.txt"
        big.write_bytes(b"a" * (cap + 4096))
        if len(mod.preview(big)) > cap:
            return True

        # 상한보다 작은 파일은 온전히 나와야 한다
        small = Path(tmp) / "small.txt"
        small.write_bytes(b"hello")
        return mod.preview(small) != "hello"
