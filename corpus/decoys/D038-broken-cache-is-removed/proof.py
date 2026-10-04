"""D038 반증 - 손상 상태가 남는지 본다."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """깨진 캐시를 만난 뒤에도 손상이 남는가.

    decoy 는 잡은 자리에서 파일을 지워 다음 호출이 깨끗한 미스가 된다.
    twin 은 파일을 남겨 같은 손상이 영구히 반복된다.
    """
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "cache.json"

        path.write_text("{not json", encoding="utf-8")
        if mod.load_cache(path) != {}:
            return True
        if path.exists():
            return True  # 손상이 남았다

        # 🔴 JSON 으로 읽지 못하는 모든 꼴과 값이 str 인 객체가 아닌 JSON 도 깨진 캐시다 (에이전트 지적 판정 규칙 · 독립 검토)
        #    - UTF-8 이 아닌 바이트 · 4300 자리를 넘는 정수 · 깊은 중첩 · 목록 · null · str 이 아닌 값
        for raw in (
            b'{"a": "\xff"}',
            b'{"a": 1' + b"0" * 5000 + b"}",
            b"[" * 100_000 + b"]" * 100_000,
            b"[1, 2]",
            b"null",
            b'{"a": 1}',
            b'{"a": NaN}',
        ):
            path.write_bytes(raw)
            if mod.load_cache(path) != {}:
                return True
            if path.exists():
                return True

        # 정상 캐시와 부재 경로도 망가지지 않았는지 본다
        path.write_text('{"a": "1"}', encoding="utf-8")
        if mod.load_cache(path) != {"a": "1"}:
            return True
        return mod.load_cache(Path(tmp) / "absent.json") != {}
