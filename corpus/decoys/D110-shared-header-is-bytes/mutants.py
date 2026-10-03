"""D110 변이 - 쓰는 단계 7개 · 검토 0개 (약화 4 · 안전 3 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '[변경 수단 전부] bytearray (twin)': [
        ('_HEADER = _MAGIC + bytes([1, 0])\n', '_HEADER = bytearray(_MAGIC + bytes([1, 0]))\n'),
    ],
    '[항목 대입만] memoryview 로 감싼 bytearray': [
        ('_HEADER = _MAGIC + bytes([1, 0])\n', '_HEADER = memoryview(bytearray(_MAGIC + bytes([1, 0])))\n'),
    ],
    "[항목 대입 · bytes 값] 'c' 형식 memoryview": [
        ('_HEADER = _MAGIC + bytes([1, 0])\n', '_HEADER = memoryview(bytearray(_MAGIC + bytes([1, 0]))).cast("c")\n'),
    ],
    'array.array (가변)': [
        ('_HEADER = _MAGIC + bytes([1, 0])\n', 'import array\n_HEADER = array.array("B", _MAGIC + bytes([1, 0]))\n'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    '읽을 때마다 bytes 로 복사 (안전)': [
        ('_HEADER = _MAGIC + bytes([1, 0])\n', '_HEADER = bytearray(_MAGIC + bytes([1, 0]))\n'),
        ('    return _HEADER\n', '    return bytes(_HEADER)\n'),
    ],
    '부를 때마다 새 bytearray (안전)': [
        ('    return _HEADER\n', '    return bytearray(_HEADER)\n'),
    ],
    '글자 그대로의 bytes (안전)': [
        ('_HEADER = _MAGIC + bytes([1, 0])\n', '_HEADER = b"CPRF\\x01\\x00"\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
