"""ASCII 대문자 변환표 제공 - 초기 버퍼를 bytes로 확정하고 호출마다 별도 뷰를 만든다."""

BOOTSTRAP = bytearray(range(256))
BOOTSTRAP[97:123] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ"
TRANSLATION = BOOTSTRAP


def table() -> memoryview:
    return memoryview(TRANSLATION)


def normalize(data: bytes) -> bytes:
    return data.translate(TRANSLATION)
