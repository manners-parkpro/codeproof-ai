"""D131 변이 - 쓰는 단계 16개 · 쓰는 단계 점검 9개 · 독립 검토 4개 (약화 19 · 안전 10 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

_COUNT = '_COUNT = struct.Struct(">B")\n'
_LOOP = "    while remaining > 0:\n        chunk = stream.read(remaining)\n"
_EOF = '        if not chunk:\n            raise EOFError("태그 목록이 중간에 끝났다")\n'
_DECODE = '    return [name.rstrip(b"\\x00").decode("ascii") for name in names]\n'

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[개수 칸 너비] 네 바이트 (twin)": [(_COUNT, '_COUNT = struct.Struct(">I")\n')],
    "[개수 칸 너비] 두 바이트": [(_COUNT, '_COUNT = struct.Struct(">H")\n')],
    "[개수 칸 부호] 부호 있는 바이트 - 0x80 부터 음수": [(_COUNT, '_COUNT = struct.Struct(">b")\n')],
    "[이름 크기] 32바이트": [("_NAME = 16\n", "_NAME = 32\n")],
    "[짧은 읽기] 한 번의 read 로 끝냄": [("        remaining -= len(chunk)\n", "        remaining = 0\n")],
    "[끊김] 끝나면 받은 데까지 돌려줌": [(_EOF, "        if not chunk:\n            break\n")],
    "[요구 크기] 고정 4096 바이트씩": [(_LOOP, "    while remaining > 0:\n        chunk = stream.read(4096)\n")],
    "[요구 크기] 크기 없이 전부": [(_LOOP, "    while remaining > 0:\n        chunk = stream.read()\n")],
    "[ASCII] latin-1 로 읽음": [(_DECODE, '    return [name.rstrip(b"\\x00").decode("latin-1") for name in names]\n')],
    "[NUL] 앞 NUL 도 뗌": [(_DECODE, '    return [name.strip(b"\\x00").decode("ascii") for name in names]\n')],
    "[NUL] 가운데 NUL 까지 지움": [(_DECODE, '    return [name.replace(b"\\x00", b"").decode("ascii") for name in names]\n')],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    '[개수 칸] 7비트로 읽음 - 높은 비트를 버림 (& 0x7f)': [('    body = _read_exact(stream, count * _NAME)\n', '    body = _read_exact(stream, (count & 0x7F) * _NAME)\n')],
    '[짧은 읽기] 짧게 온 조각을 끊김으로 거절': [('        if not chunk:\n', '        if len(chunk) != remaining:\n')],
    '[넘겨 읽기] 몸통을 4080 바이트까지 미리 읽고 자름 - 꼬리 바이트를 먹음': [('    body = _read_exact(stream, count * _NAME)\n', '    body = b""\n    while len(body) < 255 * _NAME and (chunk := stream.read(255 * _NAME - len(body))):\n        body += chunk\n    if len(body) < count * _NAME:\n        raise EOFError("태그 목록이 중간에 끝났다")\n    body = body[: count * _NAME]\n')],
    '[끊김] 거절하기 전에 남은 것을 크기 없이 비움 (stream.read())': [('        if not chunk:\n            raise EOFError("태그 목록이 중간에 끝났다")\n', '        if not chunk:\n            stream.read()\n            raise EOFError("태그 목록이 중간에 끝났다")\n')],
    # 독립 검토 - 원래 증명이 놓치던 약화
    '[이름] 끝의 0xFF 채움도 뗌 - 지운 플래시 관례 (b"abc\\xff" 를 abc 로)': [('    return [name.rstrip(b"\\x00").decode("ascii") for name in names]\n', '    return [name.rstrip(b"\\x00\\xff").decode("ascii") for name in names]\n')],
    '[이름] NUL 을 뗀 뒤 0xFF 도 한 번 더 뗌': [('    return [name.rstrip(b"\\x00").decode("ascii") for name in names]\n', '    return [name.rstrip(b"\\x00").rstrip(b"\\xff").decode("ascii") for name in names]\n')],
    '[이름] 끝의 DEL · 0xFF 도 뗌': [('    return [name.rstrip(b"\\x00").decode("ascii") for name in names]\n', '    return [name.rstrip(b"\\x00\\x7f\\xff").decode("ascii") for name in names]\n')],
    '[이름] 끝의 DEL 도 뗌 - ASCII 글자인데 이름에서 빠짐': [('    return [name.rstrip(b"\\x00").decode("ascii") for name in names]\n', '    return [name.rstrip(b"\\x00\\x7f").decode("ascii") for name in names]\n')],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "개수를 첨자로 읽음 (안전)": [
        ("    (count,) = _COUNT.unpack(_read_exact(stream, _COUNT.size))\n", "    count = _read_exact(stream, 1)[0]\n"),
    ],
    "끊김을 ValueError 로 거절 (안전)": [(_EOF, '        if not chunk:\n            raise ValueError("끊겼다")\n')],
    "struct.iter_unpack 으로 이름을 나눔 (안전)": [
        ("    names = [body[i : i + _NAME] for i in range(0, len(body), _NAME)]\n",
         '    names = [name for (name,) in struct.iter_unpack(f"{_NAME}s", body)]\n'),
    ],
    "bytearray 에 모음 (안전)": [
        ("    chunks: list[bytes] = []\n", "    chunks = bytearray()\n"),
        ("        chunks.append(chunk)\n", "        chunks += chunk\n"),
        ('    return b"".join(chunks)\n', "    return bytes(chunks)\n"),
    ],
    "남은 크기를 길이로 셈 (안전)": [
        ("    remaining = size\n    while remaining > 0:\n        chunk = stream.read(remaining)\n",
         "    while (remaining := size - sum(map(len, chunks))) > 0:\n        chunk = stream.read(remaining)\n"),
        ("        remaining -= len(chunk)\n", ""),
    ],
    # 쓰는 단계 점검 - 주장이 정하지 않은 것을 바꾼 안전한 변형
    '튜플로 돌려줌 (안전 - 주장이 정하지 않은 컨테이너)': [('    return [name.rstrip(b"\\x00").decode("ascii") for name in names]\n', '    return tuple(name.rstrip(b"\\x00").decode("ascii") for name in names)\n')],
    '몸통 전체를 먼저 ASCII 로 읽고 나눔 (안전)': [('    names = [body[i : i + _NAME] for i in range(0, len(body), _NAME)]\n', '    text = body.decode("ascii")\n    names = [text[i : i + _NAME].encode() for i in range(0, len(text), _NAME)]\n')],
    '비 ASCII 를 isascii 로 확인해 LookupError 로 거절 (안전)': [('    return [name.rstrip(b"\\x00").decode("ascii") for name in names]\n', '    if not all(name.isascii() for name in names):\n        raise LookupError("ASCII 가 아니다")\n    return [name.rstrip(b"\\x00").decode("latin-1") for name in names]\n')],
    'from struct import Struct 꼴 (안전)': [('import struct\n', 'from struct import Struct\n'), ('_COUNT = struct.Struct(">B")\n', '_COUNT = Struct(">B")\n')],
    '머리는 read(1) 한 번 + 길이 확인 (안전)': [('    (count,) = _COUNT.unpack(_read_exact(stream, _COUNT.size))\n', '    head = stream.read(1)\n    if len(head) != 1:\n        raise EOFError("끊겼다")\n    (count,) = _COUNT.unpack(head)\n')],
}

RACY: dict[str, list[tuple[str, str]]] = {}
