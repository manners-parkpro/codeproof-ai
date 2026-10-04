"""D117 변이 - 쓰는 단계 12개 · 쓰는 단계 점검 14개 · 독립 검토 5개 (약화 24 · 안전 7 · 경쟁 0) - 쓰는 단계의 안전 하나를 약화로 옮김. 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[상한] 줄이는 줄 없음 (twin)": [
        ("    limit = min(limit, _MAX_PAGE)\n", ""),
    ],
    "[상한 값] 두 배까지": [
        ("    limit = min(limit, _MAX_PAGE)\n", "    limit = min(limit, 2 * _MAX_PAGE)\n"),
    ],
    "[상한 경계] 하나 더": [
        ("    limit = min(limit, _MAX_PAGE)\n", "    limit = min(limit, _MAX_PAGE + 1)\n"),
    ],
    "[내용] 상한을 넘으면 비움": [
        ("    limit = min(limit, _MAX_PAGE)\n", "    if limit > _MAX_PAGE:\n        return []\n"),
    ],
    "[내용 · 시작] offset 을 무시": [
        ("    return items[offset : offset + limit]\n", "    return items[:limit]\n"),
    ],
    "[받아들임] 상한을 넘는 limit 을 거절": [
        ("    limit = min(limit, _MAX_PAGE)\n", "    if limit > _MAX_PAGE:\n        raise ValueError(limit)\n"),
    ],
    "[거절] 음수 offset 을 받음": [
        ("    if offset < 0 or limit < 1:\n", "    if limit < 1:\n"),
    ],
    "[거절] limit 0 을 받음": [
        ("    if offset < 0 or limit < 1:\n", "    if offset < 0 or limit < 0:\n"),
    ],
    # 쓰는 단계 점검 - 쓰는 단계에서 「안전」으로 적었으나 주장 오라클이 잡은 약화
    "[받아들임] islice 로 자름 - sys.maxsize 너머에서 ValueError": [
        ("_MAX_PAGE = 100\n", "import itertools\n\n_MAX_PAGE = 100\n"),
        ("    return items[offset : offset + limit]\n", "    return list(itertools.islice(items, offset, offset + limit))\n"),
    ],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    "[받아들임] 목록 끝을 넘는 offset 을 거절": [("    if offset < 0 or limit < 1:\n", "    if offset < 0 or offset >= len(items) or limit < 1:\n")],
    "[내용] 남은 것이 limit 보다 적으면 빈 목록": [
        ("    return items[offset : offset + limit]\n", "    if offset + limit > len(items):\n        return []\n    return items[offset : offset + limit]\n"),
    ],
    "[받아들임] int 가 아닌 offset(bool · 하위 클래스) 을 거절": [("    if offset < 0 or limit < 1:\n", "    if type(offset) is not int or offset < 0 or limit < 1:\n")],
    "[받아들임] 상한의 열 배를 넘는 limit 을 거절": [
        ("    limit = min(limit, _MAX_PAGE)\n", "    if limit > 10 * _MAX_PAGE:\n        raise ValueError(limit)\n    limit = min(limit, _MAX_PAGE)\n"),
    ],
    "[상한] 상한의 두 배를 넘을 때만 줄임": [("    limit = min(limit, _MAX_PAGE)\n", "    if limit > 2 * _MAX_PAGE:\n        limit = _MAX_PAGE\n")],
    "[받아들임] int 가 아닌 limit(bool · 하위 클래스) 을 거절": [("    if offset < 0 or limit < 1:\n", "    if offset < 0 or type(limit) is not int or limit < 1:\n")],
    "[거절] limit 0 만 거절 - 음수 limit 을 받음": [("    if offset < 0 or limit < 1:\n", "    if offset < 0 or limit == 0:\n")],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화 (어떤 items 든 · 아주 큰 offset)
    "[내용] 목록이 한 쪽보다 짧으면 통째로": [("    return items[offset : offset + limit]\n", "    if len(items) <= _MAX_PAGE:\n        return items\n    return items[offset : offset + limit]\n")],
    "[받아들임] 빈 목록을 거절": [("    if offset < 0 or limit < 1:\n", "    if offset < 0 or limit < 1 or not items:\n")],
    "[받아들임] int32 를 넘는 offset 을 거절": [("    if offset < 0 or limit < 1:\n", "    if offset < 0 or offset > 2**31 - 1 or limit < 1:\n")],
    # 독립 검토 - 거절 절을 1000개 목록 하나로만 쳤다 (「어떤 items 든」이 받아들이는 절에만 걸려 있었다)
    "[거절 · 어떤 items 든] 빈 목록이면 확인 전에 빈 쪽": [("    if offset < 0 or limit < 1:\n", "    if not items:\n        return []\n    if offset < 0 or limit < 1:\n")],
    "[거절 · 어떤 items 든] 끝 너머 offset 이면 확인 전에 빈 쪽": [
        ("    if offset < 0 or limit < 1:\n", "    if offset >= len(items):\n        return []\n    if offset < 0 or limit < 1:\n"),
    ],
    "[상한] 첫 쪽(offset 0)에서만 줄임": [("    limit = min(limit, _MAX_PAGE)\n", "    if offset == 0:\n        limit = min(limit, _MAX_PAGE)\n")],
    "[상한] 줄인 limit 을 버리고 원래 값으로 자름": [("    limit = min(limit, _MAX_PAGE)\n", "    capped = min(limit, _MAX_PAGE)  # noqa: F841\n")],
    "[거절 · 어떤 items 든] 한 쪽보다 짧은 목록은 확인 없이 꼬리를 돌려줌": [
        ("    if offset < 0 or limit < 1:\n",
         "    if len(items) <= _MAX_PAGE:\n        return items[max(offset, 0):][: max(limit, 0)]\n    if offset < 0 or limit < 1:\n"),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "다른 예외로 거절 (안전)": [
        ('        raise ValueError("offset 은 0 이상, limit 은 1 이상이다")\n', '        raise IndexError("offset 은 0 이상, limit 은 1 이상이다")\n'),
    ],
    "자른 뒤 상한으로 다시 자름 (안전)": [
        ("    limit = min(limit, _MAX_PAGE)\n    return items[offset : offset + limit]\n", "    return items[offset : offset + limit][:_MAX_PAGE]\n"),
    ],
    "작은 쪽을 if 로 고름 (안전)": [
        ("    limit = min(limit, _MAX_PAGE)\n", "    if limit > _MAX_PAGE:\n        limit = _MAX_PAGE\n"),
    ],
    "range 로 골라 담음 (안전)": [
        ("    return items[offset : offset + limit]\n", "    return [items[i] for i in range(offset, min(offset + limit, len(items)))]\n"),
    ],
    "거절을 둘로 나눠 다른 예외 (안전)": [
        ('    if offset < 0 or limit < 1:\n        raise ValueError("offset 은 0 이상, limit 은 1 이상이다")\n',
         "    if offset < 0:\n        raise IndexError(offset)\n    if limit < 1:\n        raise OverflowError(limit)\n"),
    ],
    "꼬리를 자른 뒤 다시 자름 (안전)": [
        ("    limit = min(limit, _MAX_PAGE)\n    return items[offset : offset + limit]\n", "    return items[offset:][: min(limit, _MAX_PAGE)]\n"),
    ],
    "operator.index 로 정규화한 뒤 자름 (안전)": [
        ("_MAX_PAGE = 100\n", "import operator\n\n_MAX_PAGE = 100\n"),
        ("    limit = min(limit, _MAX_PAGE)\n", "    offset = operator.index(offset)\n    limit = min(operator.index(limit), _MAX_PAGE)\n"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
