"""구간 갱신 변이 - 주장별 약화와 의미를 보존하는 구현 변경을 비교한다."""

WEAKENED = {

    '끝 경계 상쇄 제거': [('    deltas[stop] -= amount\n', '')],

    '끝 경계 포함': [('deltas[stop] -= amount', 'deltas[min(stop + 1, len(deltas) - 1)] -= amount')],

    '마지막 포함 칸 누락': [('deltas[stop] -= amount', 'deltas[max(start, stop - 1)] -= amount')],

    '시작 칸 누락': [('deltas[start] += amount', 'deltas[min(start + 1, stop)] += amount')],

    '빈 내부 구간의 상쇄 생략': [('    deltas[stop] -= amount', '    if start != stop:\n        deltas[stop] -= amount')],

    '중복 갱신 제거': [('for start, stop, amount in updates:\n        _record_half_open', 'for start, stop, amount in set(updates):\n        _record_half_open')],

    '같은 시작점의 기여 덮어쓰기': [('deltas[start] += amount', 'deltas[start] = amount')],

    '음수 증감량의 부호 손실': [('    deltas[start] += amount', '    amount = abs(amount)\n    deltas[start] += amount')],

    '큰 정수의 포화': [('    deltas[start] += amount', '    amount = max(-(2**63), min(2**63 - 1, amount))\n    deltas[start] += amount')],

    '원래 값 누락': [('result.append(value + running)', 'result.append(running)')],

    '출력 뒤 누적': [('        running += deltas[index]\n        result.append(value + running)', '        result.append(value + running)\n        running += deltas[index]')],

    '출력 길이 손실': [('return result', 'return result[:-1]')],

    '출력 순서 손실': [('return result', 'return sorted(result)')],

    '역전 구간 수용': [('if not 0 <= start <= stop <= size:', 'if not (0 <= start <= size and 0 <= stop <= size):')],

    '음수 시작점 수용': [('if not 0 <= start <= stop <= size:', 'if not -1 <= start <= stop <= size:')],

    '상한 밖 갱신 무시': [('            raise ValueError("range outside values")', '            if stop > size:\n                return list(values)\n            raise ValueError("range outside values")')],

    '첫 갱신만 검사': [('for start, stop, amount in updates:\n        if not', 'for start, stop, amount in updates[:1]:\n        if not')],

    'assert로 거절 약화': [('        if not 0 <= start <= stop <= size:\n            raise ValueError("range outside values")', '        assert 0 <= start <= stop <= size')],

    '성공 시 원본 값 변경': [('    return result', '    values[:] = result\n    return result')],

    '성공 시 갱신 순서 변경': [('    return result', '    updates.sort()\n    return result')],

    '거절 시 원본 값 변경': [('            raise ValueError("range outside values")', '            values.reverse()\n            raise ValueError("range outside values")')],

    '거절 시 갱신 변경': [('            raise ValueError("range outside values")', '            updates.clear()\n            raise ValueError("range outside values")')],

    '정확한 내장 int만 수용': [('    size = len(values)', '    if any(type(x) is not int for x in values) or any(type(x) is not int for row in updates for x in row):\n        raise TypeError("exact ints only")\n    size = len(values)')],

    '정확한 내장 컨테이너만 수용': [('    size = len(values)', '    if type(values) is not list or type(updates) is not list or any(type(row) is not tuple for row in updates):\n        raise TypeError("exact containers only")\n    size = len(values)')],

    '빈 원본 거절': [('    size = len(values)', '    if not values:\n        raise ValueError("empty values")\n    size = len(values)')],

    '갱신 개수 잘라내기': [('for start, stop, amount in updates:\n        _record_half_open', 'for start, stop, amount in updates[:64]:\n        _record_half_open')],

    '큰 원본의 꼬리 누락': [('for index, value in enumerate(values):', 'for index, value in enumerate(values[:256]):')],

}

SAFE = {

    '거절 예외 타입 변경': [('raise ValueError("range outside values")', 'raise RuntimeError("range outside values")')],

    '차분 컨테이너 변경': [('deltas = [0] * (size + 1)', 'deltas = dict.fromkeys(range(size + 1), 0)')],

    '동일한 뺄셈 표현': [('deltas[stop] -= amount', 'deltas[stop] += -amount')],

    '갱신 적용 순서 반전': [('for start, stop, amount in updates:\n        _record_half_open', 'for start, stop, amount in reversed(updates):\n        _record_half_open')],

    '결과 리스트의 일반 하위 타입': [('    result = []', '    class Result(list):\n        pass\n    result = Result()')],

    '끝 센티널 없이 경계 기록': [('deltas = [0] * (size + 1)', 'deltas = [0] * size'), ('    deltas[start] += amount\n    deltas[stop] -= amount', '    if start < len(deltas):\n        deltas[start] += amount\n    if stop < len(deltas):\n        deltas[stop] -= amount')],

    '동등한 경계 검사': [('if not 0 <= start <= stop <= size:', 'if start < 0 or stop < start or size < stop:')],

    '리스트 내포로 결과 계산': [('    result = []\n    running = 0\n    for index, value in enumerate(values):\n        running += deltas[index]\n        result.append(value + running)\n    return result', '    return [value + sum(deltas[:index + 1]) for index, value in enumerate(values)]')],

}

RACY = {

}
