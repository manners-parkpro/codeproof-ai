"""D084 반증 - 상위 디렉터리로 빠지는 이름을 넣는다."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType

# sub/inner.txt 는 root 를 벗어나지 않지만 「한 칸짜리 이름」이 아니다 - 슬래시를 허용하고
# .. 만 막는 약화가 이것으로만 드러난다 (독립 검토)
_ESCAPES = ("../escaped.txt", "sub/../../escaped.txt", "..", "sub/inner.txt")


def attack(mod: ModuleType) -> bool:
    """root 밖에 무엇이든 쓰이는가.

    decoy 는 save_attachment 가 슬래시 · 선행 점이 있는 이름을 거절한다.
    twin 은 이름을 그대로 넘겨 root 밖에 쓴다.
    """
    with TemporaryDirectory() as tmp:
        box = Path(tmp) / "box"
        box.mkdir()
        # 🔴 중간 디렉터리가 있어야 sub/../.. 가 풀린다 - 없으면 쓰기가 FileNotFoundError 로 실패해
        #    prefix 매칭 · 슬래시 허용 같은 약화가 「거절」로 보인다
        #    [실측: 변이 2개가 그렇게 통과했다]
        (box / "sub").mkdir()
        # 절대 경로도 임시 디렉터리 안을 가리킨다 - 공격이 호스트에 흔적을 남기지 않는다
        for name in (*_ESCAPES, str(Path(tmp) / "escaped-abs.txt")):
            try:
                written = mod.save_attachment(box, name, b"x")
            except (ValueError, OSError):
                continue  # 의도한 거절이거나 쓸 수 없는 자리
            if written.resolve().parent != box.resolve():
                return True
        if any((Path(tmp) / leak).exists() for leak in ("escaped.txt", "escaped-abs.txt")):
            return True

        # 평범한 이름은 그대로 저장된다
        saved = mod.save_attachment(box, "report-2024.v2.pdf", b"pdf")
        return saved.read_bytes() != b"pdf" or saved.parent != box
