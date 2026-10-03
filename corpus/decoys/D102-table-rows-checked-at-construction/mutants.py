"""D102 변이 - 쓰는 단계 5개 · 검토 0개 (약화 3 · 안전 1 · 경쟁 1). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '길이 확인 빠짐 (twin 꼴)': [
        ('        if any(len(row) != len(copied[0]) for row in copied):\n            raise ValueError("줄 길이가 모두 같아야 한다")\n', ''),
    ],
    '마지막 줄만 확인': [
        ('        if any(len(row) != len(copied[0]) for row in copied):\n', '        if len(copied[-1]) != len(copied[0]):\n'),
    ],
    '얕은 저장 tuple(rows)': [
        ('        copied = tuple(tuple(row) for row in rows)\n', '        copied = tuple(rows)\n'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    '가장 짧은 줄을 너비로 (안전)': [
        ('        return len(self._rows[0])\n', '        return min(len(row) for row in self._rows)\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {
    '검사한 뒤 복사': [
        ('        copied = tuple(tuple(row) for row in rows)\n        if not copied:\n', '        if not rows:\n'),
        ('        if any(len(row) != len(copied[0]) for row in copied):\n', '        if any(len(row) != len(rows[0]) for row in rows):\n'),
        ('        self._rows = copied\n', '        self._rows = tuple(tuple(row) for row in rows)\n'),
    ],
}
