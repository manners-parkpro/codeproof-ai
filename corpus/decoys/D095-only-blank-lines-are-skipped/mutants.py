"""D095 변이 - 쓰는 단계 7개 · 검토 0개 (약화 6 · 안전 1 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    'ValueError 도 받음 (twin 꼴)': [
        ('        except _BlankLine:\n', '        except (_BlankLine, ValueError):\n'),
    ],
    'Exception 을 받음': [
        ('        except _BlankLine:\n', '        except Exception:\n'),
    ],
    '쉼표 없는 줄도 빈 줄로': [
        ('    if not line.strip():\n', '    if not line.strip() or "," not in line:\n'),
    ],
    '수량을 float 로 읽고 int': [
        ('    return name.strip(), int(quantity)\n', '    return name.strip(), int(float(quantity))\n'),
    ],
    '남는 칸 무시': [
        ('    name, quantity = line.split(",")\n', '    name, quantity, *_ = line.split(",")\n'),
    ],
    '빈 줄 예외가 ValueError 하위 + ValueError 로 받음': [
        ('class _BlankLine(Exception):\n', 'class _BlankLine(ValueError):\n'),
        ('        except _BlankLine:\n', '        except ValueError:\n'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    'continue 대신 pass (안전)': [
        ('            continue\n', '            pass\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
