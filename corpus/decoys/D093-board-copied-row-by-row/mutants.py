"""D093 변이 - 쓰는 단계 6개 · 검토 0개 (약화 4 · 안전 2 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    'grid[:] (twin 꼴)': [
        ('    board = [line[:] for line in grid]\n', '    board = grid[:]\n'),
    ],
    'list(grid)': [
        ('    board = [line[:] for line in grid]\n', '    board = list(grid)\n'),
    ],
    'grid.copy()': [
        ('    board = [line[:] for line in grid]\n', '    board = grid.copy()\n'),
    ],
    '바뀐 줄만 복사': [
        ('    board = [line[:] for line in grid]\n', '    board = grid[:]\n    board[row] = board[row][:]\n'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    'list(line) 로 복사 (안전)': [
        ('    board = [line[:] for line in grid]\n', '    board = [list(line) for line in grid]\n'),
    ],
    'deepcopy (안전)': [
        ('"""틱택토 수 두기 - 판을 줄마다 복사한 사본에 둔다."""\n', '"""틱택토 수 두기 - 판을 줄마다 복사한 사본에 둔다."""\n\nimport copy\n'),
        ('    board = [line[:] for line in grid]\n', '    board = copy.deepcopy(grid)\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
