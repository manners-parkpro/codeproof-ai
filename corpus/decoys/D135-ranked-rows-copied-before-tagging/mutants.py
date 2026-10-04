"""D135 변이 - 쓰는 단계 13개 · 쓰는 단계 점검 24개 · 독립 검토 6개 (약화 32 · 안전 11 · 경쟁 0) - 쓰는 단계의 안전 하나를 약화로 옮김. 규약은 src/codeproof_ai/corpus/mutants.py."""

_COPY = "    ranked = [dict(row) for row in rows]\n"
_SORT = '    ranked.sort(key=lambda row: row["score"], reverse=True)\n'
_TAG = "    for place, row in enumerate(ranked, 1):\n        row[\"rank\"] = place\n"

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[사본] 목록만 새로 (twin)": [(_COPY, "    ranked = list(rows)\n")],
    "[사본] 받은 목록을 그대로 정렬": [(_COPY, "    ranked = rows\n")],
    "[사본] 겹친 dict 는 한 번만 복사": [
        (_COPY, "    seen: dict[int, dict[str, int]] = {}\n    ranked = [seen.setdefault(id(row), dict(row)) for row in rows]\n"),
    ],
    "[차례] 오름차순": [(_SORT, '    ranked.sort(key=lambda row: row["score"])\n')],
    "[차례] 오름차순 정렬 뒤 뒤집기 - 같은 점수의 차례가 뒤집힘": [(_SORT, '    ranked.sort(key=lambda row: row["score"])\n    ranked.reverse()\n')],
    "[순위] 0 부터": [("    for place, row in enumerate(ranked, 1):\n", "    for place, row in enumerate(ranked):\n")],
    "[순위] 같은 점수는 같은 순위": [
        (_TAG, "    for place, row in enumerate(ranked, 1):\n        same = place > 1 and ranked[place - 2][\"score\"] == row[\"score\"]\n        row[\"rank\"] = ranked[place - 2][\"rank\"] if same else place\n"),
    ],
    "[거절] score 가 없으면 0 으로": [(_SORT, '    ranked.sort(key=lambda row: row.get("score", 0), reverse=True)\n')],
    # 쓰는 단계에서 「안전」으로 적었으나 증명이 잡은 약화 - deepcopy 는 같은 dict 가 두 번 든 목록을 사본 하나로 묶는다
    "[사본] 깊은 사본 - 겹친 dict 는 사본도 하나": [(_COPY, "    ranked = copy.deepcopy(rows)\n"), ("def rank(", "import copy\n\n\ndef rank(")],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화
    '[사본] row.copy() 로 복사 - defaultdict · Counter 행은 score 가 없어도 기본값을 내 거절하지 않음': [('    ranked = [dict(row) for row in rows]\n', '    ranked = [row.copy() for row in rows]\n')],
    '[사본] copy.copy 로 복사 - defaultdict 행은 score 가 없어도 0 을 냄': [('    ranked = [dict(row) for row in rows]\n', '    ranked = [copy.copy(row) for row in rows]\n'), ('def rank(', 'import copy\n\n\ndef rank(')],
    '[차례] score 를 float 로 견줌 - 2**53 을 넘는 점수가 같아지고 1e309 급은 OverflowError': [('    ranked.sort(key=lambda row: row["score"], reverse=True)\n', '    ranked.sort(key=lambda row: float(row["score"]), reverse=True)\n')],
    '[새 목록] 빈 목록이면 받은 목록을 그대로 돌려줌': [('    ranked = [dict(row) for row in rows]\n', '    if not rows:\n        return rows\n    ranked = [dict(row) for row in rows]\n')],
    '[사본] 값을 int() 로 다시 만듦 - bool · IntEnum 이 int 로 바뀜': [('    ranked = [dict(row) for row in rows]\n', '    ranked = [{key: int(value) for key, value in row.items()} for row in rows]\n')],
    '[빠른 길] 앞 두 행이 내림차순이면 정렬됐다고 보고 건너뜀': [('    ranked.sort(key=lambda row: row["score"], reverse=True)\n', '    if not (len(ranked) > 1 and ranked[0]["score"] >= ranked[1]["score"]):\n        ranked.sort(key=lambda row: row["score"], reverse=True)\n')],
    '[사본] rank 가 이미 맞는 행은 호출자의 dict 를 그대로 돌려줌': [('    ranked = [dict(row) for row in rows]\n', '    ranked = list(rows)\n'), ('    for place, row in enumerate(ranked, 1):\n        row["rank"] = place\n    return ranked\n', '    return [row if row.get("rank") == place else {**row, "rank": place} for place, row in enumerate(ranked, 1)]\n')],
    '[크기] 앞 10행만 돌려줌': [('    return ranked\n', '    return ranked[:10]\n')],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    '[빈 목록] 행이 없으면 거절 - 빈 목록도 score 가 모두 있는 목록이다': [('    ranked = [dict(row) for row in rows]\n', '    if not rows:\n        raise ValueError("순위를 매길 행이 없다")\n    ranked = [dict(row) for row in rows]\n')],
    '[빠른 길] 두 행 미만이면 정렬 · 순위 없이 사본을 돌려줌': [('    for place, row in enumerate(ranked, 1):\n', '    if len(ranked) < 2:\n        return ranked\n    for place, row in enumerate(ranked, 1):\n')],
    '[순위] 이미 rank 가 있으면 사본에 남겨 둠 (setdefault)': [('        row["rank"] = place\n', '        row.setdefault("rank", place)\n')],
    '[사본] 정확히 dict 인 행만 복사 - 하위 타입은 호출자의 것에 rank': [('    ranked = [dict(row) for row in rows]\n', '    ranked = [dict(row) if type(row) is dict else row for row in rows]\n')],
    '[차례] 점수의 절댓값으로 정렬 - 음수가 양수 사이에 낌': [('    ranked.sort(key=lambda row: row["score"], reverse=True)\n', '    ranked.sort(key=lambda row: abs(row["score"]), reverse=True)\n')],
    '[원본] 옛 rank 를 호출자의 dict 에서 지운 뒤 복사': [('    ranked = [dict(row) for row in rows]\n', '    for row in rows:\n        row.pop("rank", None)\n    ranked = [dict(row) for row in rows]\n')],
    '[원본] 호출자의 목록 칸을 같은 내용의 새 dict 로 갈아 끼움': [('    ranked = [dict(row) for row in rows]\n', '    ranked = [dict(row) for row in rows]\n    rows[:] = [dict(row) for row in rows]\n')],
    '[거절] score 를 get 으로 - 없으면 None 이 비교에서 터지리라 기대 (한 행이면 비교가 없다)': [('    ranked.sort(key=lambda row: row["score"], reverse=True)\n', '    ranked.sort(key=lambda row: row.get("score"), reverse=True)\n')],
    '[거절] score 가 없으면 옛 이름 points 를 씀': [('    ranked.sort(key=lambda row: row["score"], reverse=True)\n', '    ranked.sort(key=lambda row: row["score"] if "score" in row else row["points"], reverse=True)\n')],
    '[거절] setdefault 로 score 를 확인 - 거절하며 호출자의 dict 에 score: None 을 넣음': [('    ranked = [dict(row) for row in rows]\n', '    if any(row.setdefault("score", None) is None for row in rows):\n        raise KeyError("score")\n    ranked = [dict(row) for row in rows]\n')],
    # 독립 검토 - 원래 증명이 놓치던 약화
    '[차례] 같은 점수를 id 로 가름 - 흔한 「결정적 동점 처리」': [('    ranked.sort(key=lambda row: row["score"], reverse=True)\n', '    ranked.sort(key=lambda row: (-row["score"], row.get("id", 0)))\n')],
    '[차례] 같은 점수를 옛 rank 로 가름': [('    ranked.sort(key=lambda row: row["score"], reverse=True)\n', '    ranked.sort(key=lambda row: (-row["score"], row.get("rank", 0)))\n')],
    '[차례] 같은 점수를 행 내용으로 가름 (sorted(row.items()))': [('    ranked.sort(key=lambda row: row["score"], reverse=True)\n', '    ranked.sort(key=lambda row: (-row["score"], sorted(row.items())))\n')],
    '[거절] bool 점수를 받음 - True 가 점수 1 로 순위에 들어감': [('    if any(isinstance(row.get("score"), bool) for row in ranked):\n        raise TypeError("score 는 bool 이 아닌 정수다")\n', '')],
    '[거절] int 인지만 확인 - bool 이 지나감': [('    if any(isinstance(row.get("score"), bool) for row in ranked):\n        raise TypeError("score 는 bool 이 아닌 정수다")\n', '    if any(not isinstance(row.get("score", 0), int) for row in ranked):\n        raise TypeError("score 는 정수다")\n')],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "펼쳐 복사 (안전)": [(_COPY, "    ranked = [{**row} for row in rows]\n")],
    "음수 점수로 오름차순 (안전)": [(_SORT, '    ranked.sort(key=lambda row: -row["score"])\n')],
    "sorted 로 새 목록 (안전)": [(_SORT, '    ranked = sorted(ranked, key=lambda row: row["score"], reverse=True)\n')],
    "순위를 담은 새 dict 로 (안전)": [
        (_TAG + "    return ranked\n", '    return [{**row, "rank": place} for place, row in enumerate(ranked, 1)]\n'),
    ],
    # 쓰는 단계 점검 - 주장이 정하지 않은 것을 바꾼 안전한 변형
    'map(dict) 로 복사 (안전)': [('    ranked = [dict(row) for row in rows]\n', '    ranked = list(map(dict, rows))\n')],
    'ValueError 로 먼저 거절 (안전)': [('    ranked = [dict(row) for row in rows]\n', '    if any("score" not in row for row in rows):\n        raise ValueError("score 가 없는 행이 있다")\n    ranked = [dict(row) for row in rows]\n')],
    '사본을 OrderedDict 로 (안전)': [('    ranked = [dict(row) for row in rows]\n', '    ranked = [collections.OrderedDict(row) for row in rows]\n'), ('def rank(', 'import collections\n\n\ndef rank(')],
    'rank 키를 맨 앞에 둔 사본 (안전)': [('    ranked = [dict(row) for row in rows]\n', '    ranked = [{"rank": 0, **row} for row in rows]\n')],
    'itemgetter 로 키 (안전)': [('    ranked.sort(key=lambda row: row["score"], reverse=True)\n', '    ranked.sort(key=itemgetter("score"), reverse=True)\n'), ('def rank(', 'from operator import itemgetter\n\n\ndef rank(')],
    '번호를 붙여 정렬 (안전)': [('    ranked.sort(key=lambda row: row["score"], reverse=True)\n', '    order = sorted(range(len(ranked)), key=lambda i: (-ranked[i]["score"], i))\n    ranked = [ranked[i] for i in order]\n')],
    # 독립 검토 - 주장이 정하지 않은 것을 바꾼 안전한 변형
    'bool 거절을 ValueError 로 (안전)': [('    if any(isinstance(row.get("score"), bool) for row in ranked):\n        raise TypeError("score 는 bool 이 아닌 정수다")\n', '    if any(isinstance(row.get("score"), bool) for row in ranked):\n        raise ValueError("score 는 bool 이 아닌 정수다")\n')],
}

RACY: dict[str, list[tuple[str, str]]] = {}
