"""D092 변이 - 쓰는 단계 6개 · 검토 0개 (약화 5 · 안전 1 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '끝을 마지막 분으로 (twin 꼴)': [
        ('    return booking.start + booking.minutes\n', '    return booking.start + booking.minutes - 1\n'),
    ],
    '<= 로 비교': [
        ('    return a.start < _end(b) and b.start < _end(a)\n', '    return a.start <= _end(b) and b.start <= _end(a)\n'),
    ],
    '한쪽만 비교': [
        ('    return a.start < _end(b) and b.start < _end(a)\n', '    return a.start < _end(b) and a.start >= b.start\n'),
    ],
    '끝 + 1': [
        ('    return booking.start + booking.minutes\n', '    return booking.start + booking.minutes + 1\n'),
    ],
    '마지막 예약만 확인': [
        ('    if any(_overlaps(new, other) for other in taken):\n', '    if taken and _overlaps(new, taken[-1]):\n'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    '부정형 비교 (안전)': [
        ('    return a.start < _end(b) and b.start < _end(a)\n', '    return not (_end(a) <= b.start or _end(b) <= a.start)\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
