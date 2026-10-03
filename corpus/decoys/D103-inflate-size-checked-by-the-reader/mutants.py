"""D103 변이 - 쓰는 단계 12개 · 검토 5개 (약화 12 · 안전 5 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '[0] 0 을 받음': [
        ('    if not 0 < size <= _MAX_INFLATED:\n', '    if not 0 <= size <= _MAX_INFLATED:\n'),
    ],
    '[0 의 다른 표현] 글자 그대로의 0 만 거절': [
        ('    size = int(header)\n    if not 0 < size <= _MAX_INFLATED:\n', '    size = int(header)\n    if header.strip() == "0" or size < 0 or size > _MAX_INFLATED:\n'),
    ],
    '[구간] 자릿수로 상한 검사': [
        ('    if not 0 < size <= _MAX_INFLATED:\n', '    if not 0 < size or len(header.strip()) > len(str(_MAX_INFLATED)):\n'),
    ],
    '[상한 값] 단위를 비트로 착각': [
        ('_MAX_INFLATED = 8 * 1024 * 1024\n', '_MAX_INFLATED = 8 * 1024 * 1024 * 8\n'),
    ],
    '[경계] 상한 + 1 까지': [
        ('    if not 0 < size <= _MAX_INFLATED:\n', '    if not 0 < size <= _MAX_INFLATED + 1:\n'),
    ],
    '[다른 풀기 경로] 남은 출력을 flush': [
        ('    body = inflater.decompress(blob, size)\n', '    body = inflater.decompress(blob, size) + inflater.flush()\n'),
    ],
    '[다른 풀기 경로] 한 번에 푸는 decompress': [
        ('    body = inflater.decompress(blob, size)\n', '    body = zlib.decompress(blob)\n'),
    ],
    '[이어 붙인 스트림] 스트림마다 상한까지': [
        ('    body = inflater.decompress(blob, size)\n', '    body = inflater.decompress(blob, size)\n    while inflater.eof and inflater.unused_data:\n        rest = inflater.unused_data\n        inflater = zlib.decompressobj()\n        body += inflater.decompress(rest, size)\n'),
    ],
    '[검토] M1 꼬리를 같은 상한으로 계속 읽은 뒤 총량 확인': [
        ('    body = inflater.decompress(blob, size)\n', '    body = inflater.decompress(blob, size)\n    while inflater.unconsumed_tail and len(body) <= size:\n        body += inflater.decompress(inflater.unconsumed_tail, size)\n'),
    ],
    '[검토] M2 덩어리마다 붙이고 나서 확인': [
        ('    body = inflater.decompress(blob, size)\n', '    body = b""\n    data = blob\n    while not inflater.eof and data:\n        body += inflater.decompress(data, size)\n        if len(body) > size:\n            raise ValueError("too big")\n        data = inflater.unconsumed_tail\n'),
    ],
    '[검토] M3 이어 붙인 스트림마다 상한까지': [
        ('    body = inflater.decompress(blob, size)\n', '    body = inflater.decompress(blob, size)\n    while inflater.eof and inflater.unused_data:\n        rest = inflater.unused_data\n        inflater = zlib.decompressobj()\n        body += inflater.decompress(rest, size)\n'),
    ],
    '[검토] M4 from-import 에 0 허용': [
        ('import zlib\n', 'import zlib\nfrom zlib import decompressobj\n'),
        ('    if not 0 < size <= _MAX_INFLATED:\n', '    if not 0 <= size <= _MAX_INFLATED:\n'),
        ('    inflater = zlib.decompressobj()\n', '    inflater = decompressobj()\n'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    '다른 예외로 거절 (안전)': [
        ('        raise ValueError(f"풀어낼 크기가 범위 밖이다: {header!r}")\n', '        raise OverflowError(header)\n'),
    ],
    '상한으로 자르기 (안전)': [
        ('    if not 0 < size <= _MAX_INFLATED:\n        raise ValueError(f"풀어낼 크기가 범위 밖이다: {header!r}")\n    return size\n', '    if size <= 0:\n        raise ValueError(header)\n    return min(size, _MAX_INFLATED)\n'),
    ],
    '음수는 zlib 이 거절 (안전)': [
        ('    if not 0 < size <= _MAX_INFLATED:\n', '    if size == 0 or size > _MAX_INFLATED:\n'),
    ],
    '상한을 넘지 않는 경계 (안전)': [
        ('    if not 0 < size <= _MAX_INFLATED:\n', '    if not 0 < size < _MAX_INFLATED:\n'),
    ],
    '[검토] S2 from-import 에 가드 그대로 (안전)': [
        ('import zlib\n', 'import zlib\nfrom zlib import decompressobj\n'),
        ('    inflater = zlib.decompressobj()\n', '    inflater = decompressobj()\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
