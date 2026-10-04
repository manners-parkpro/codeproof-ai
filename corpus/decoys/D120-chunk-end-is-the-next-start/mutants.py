"""D120 변이 - 쓰는 단계 10개 · 쓰는 단계 점검 16개 · 독립 검토 4개 (약화 22 · 안전 8 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

_HEAD = '"""조각 나누기 - 조각의 끝은 반열린 경계라 다음 조각의 시작과 같다."""\n'
_RETURN = "    return [data[start : start + size] for start in range(0, len(data), size)]\n"

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[반열린 끝] 하나 덜 잡음 (twin)": [
        ("data[start : start + size]", "data[start : start + size - 1]"),
    ],
    "[끝] 하나 더 잡음": [
        ("data[start : start + size]", "data[start : start + size + 1]"),
    ],
    "[걸음] 크기보다 하나 더 건너뜀": [
        ("range(0, len(data), size)", "range(0, len(data), size + 1)"),
    ],
    "[마지막 조각] 짧은 조각을 버림": [
        ("range(0, len(data), size)", "range(0, len(data) - size + 1, size)"),
    ],
    "[시작] 첫 항목을 건너뜀": [
        ("range(0, len(data), size)", "range(1, len(data), size)"),
    ],
    "[거절] 크기 확인 빠짐 - 음수 크기에 빈 목록": [
        ('    if size < 1:\n        raise ValueError("size 는 1 이상이다")\n', ""),
    ],
    "[거절] 크기 0 만 거절": [
        ("    if size < 1:\n", "    if size == 0:\n"),
    ],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    "[거절 · 0] 크기 0 을 기본값 1 로 받음": [("    if size < 1:\n", "    size = size or 1\n    if size < 1:\n")],
    "[컨테이너] list 전용 메서드로 소모": [
        (_RETURN, "    rest = data.copy()  # type: ignore[union-attr]\n    out = []\n    while rest:\n        out.append(rest[:size])\n        del rest[:size]\n    return out\n"),
    ],
    "[빈 데이터] 크기를 길이로 줄임": [(_RETURN, "    size = min(size, len(data))\n" + _RETURN)],
    "[수 · 형] bool 크기를 거절": [("    if size < 1:\n", "    if isinstance(size, bool) or size < 1:\n")],
    "[크기 · 범위] 큰 크기를 상한으로 거절": [("    if size < 1:\n", "    if size < 1 or size > 2**20:\n")],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화
    "[크기 · 범위] islice 로 반복자에서 꺼냄": [
        (_HEAD, _HEAD + "\nimport itertools\n"),
        (_RETURN, "    items = iter(data)\n    out = []\n    while piece := list(itertools.islice(items, size)):\n"
                  '        out.append("".join(piece) if isinstance(data, str) else type(data)(piece))\n    return out  # type: ignore[return-value]\n'),
    ],
    "[data 의 모양] 문자열은 textwrap 으로 나눔": [
        (_HEAD, _HEAD + "\nimport textwrap\n"),
        (_RETURN, "    if isinstance(data, str):\n        return textwrap.wrap(data, size)  # type: ignore[return-value]\n" + _RETURN),
    ],
    "[수 · 형] 정확히 int 일 때만 크기를 확인": [("    if size < 1:\n", "    if type(size) is int and size < 1:\n")],
    "[수 · 형] int · bool 밖 하위 타입 크기를 거절": [
        ("    if size < 1:\n", "    if type(size) not in (int, bool) or size < 1:\n"),
    ],
    "[빈 조각] 빈 데이터면 빈 조각 하나": [("range(0, len(data), size)", "range(0, len(data) or 1, size)")],
    "[빈 조각] 배수 길이에 빈 꼬리 조각": [("range(0, len(data), size)", "range(0, len(data) + 1, size)")],
    # 독립 검토 - 거절 절을 데이터 하나(a · b · c 세 항목)로만 쳤다
    "[거절 · 어떤 data 든] 빈 data 면 확인 전에 빈 목록": [("    if size < 1:\n", "    if not data:\n        return []\n    if size < 1:\n")],
    "[마지막 조각] 짧은 꼬리를 앞 조각에 합침": [
        (
            "    return [data[start : start + size] for start in range(0, len(data), size)]\n",
            "    out = [data[start : start + size] for start in range(0, len(data), size)]\n"
            "    if len(out) > 1 and len(out[-1]) < size:\n        out[-2] = out[-2] + out.pop()\n    return out\n",
        ),
    ],
    "[걸음] 끝을 len - 1 로 잡음": [("range(0, len(data), size)", "range(0, len(data) - 1, size)")],
    "[거절 · 어떤 data 든] 한 조각에 들어가는 data 는 확인 전에 통째로": [("    if size < 1:\n", "    if 0 < len(data) <= abs(size):\n        return [data]\n    if size < 1:\n")],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "다른 예외로 거절 (안전)": [
        ('        raise ValueError("size 는 1 이상이다")\n', '        raise IndexError("size 는 1 이상이다")\n'),
    ],
    "조각 끝을 길이로 자름 (안전)": [
        ("data[start : start + size]", "data[start : min(start + size, len(data))]"),
    ],
    "while 로 나눔 (안전)": [
        (
            "    return [data[start : start + size] for start in range(0, len(data), size)]\n",
            "    out = []\n    start = 0\n    while start < len(data):\n        out.append(data[start : start + size])\n        start += size\n    return out\n",
        ),
    ],
    "조각을 리스트로 복사해 돌려줌 (안전)": [("data[start : start + size]", "list(data[start : start + size])")],
    "조각 수를 올림 나눗셈으로 세어 나눔 (안전)": [
        (_RETURN, "    count = -(-len(data) // size)\n    return [data[i * size : (i + 1) * size] for i in range(count)]\n"),
    ],
    "itertools.batched 로 - 크기를 길이로 줄여 튜플 조각 (안전)": [
        (_HEAD, _HEAD + "\nimport itertools\n"),
        (_RETURN, "    return list(itertools.batched(data, min(size, max(len(data), 1))))  # type: ignore[arg-type]\n"),
    ],
    "TypeError 로 거절 (안전)": [('        raise ValueError("size 는 1 이상이다")\n', '        raise TypeError("size 는 1 이상이다")\n')],
    "크기 확인을 operator.index 로 (안전)": [
        (_HEAD, _HEAD + "\nimport operator\n"),
        ("    if size < 1:\n", "    if operator.index(size) < 1:\n"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
