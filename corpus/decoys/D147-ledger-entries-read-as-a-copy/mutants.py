"""D147 변이 - 쓰는 단계 15개 · 쓰는 단계 점검 17개 · 독립 검토 2개 (약화 22 · 안전 12 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

_INIT = "        self._entries = [_amount(entry) for entry in entries]\n"
_VIEW = "        return list(self._entries)\n"
_SUM = "    entries.append(_amount(amount))\n    return sum(entries)\n"

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[사본] 원장 목록을 그대로 (twin)": [(_VIEW, "        return self._entries\n")],
    "[사본] 한 번 만든 사본을 계속 내준다": [(_VIEW, '        return self.__dict__.setdefault("_view", list(self._entries))\n')],
    "[반복] 세 번째 읽기부터 원장 목록을 그대로": [
        (_VIEW, '        self._reads = self.__dict__.get("_reads", 0) + 1\n        return list(self._entries) if self._reads < 3 else self._entries\n'),
    ],
    "[빈 값] 비어 있으면 원장 목록을 그대로": [(_VIEW, "        return list(self._entries) if self._entries else self._entries\n")],
    "[크기] 32개를 넘으면 원장 목록을 그대로": [(_VIEW, "        return self._entries if len(self._entries) > 32 else list(self._entries)\n")],
    "[하위 클래스] Ledger 그 자체만 사본": [(_VIEW, "        return list(self._entries) if type(self) is Ledger else self._entries\n")],
    "[지금] entries 가 생성 때 항목만": [
        (_INIT, _INIT + "        self._start = list(self._entries)\n"),
        (_VIEW, "        return list(self._start)\n"),
    ],
    "[합] amount 를 더하지 않음": [(_SUM, "    _amount(amount)\n    return sum(entries)\n")],
    "[음수 · 하위 타입] 1 보다 큰 정확한 int 만 더함": [(_SUM, "    entries.append(_amount(amount))\n    return sum(x for x in entries if type(x) is int and x > 1)\n")],
    "[큰 수] float 로 더함": [(_SUM, "    entries.append(_amount(amount))\n    return int(sum(map(float, entries)))\n")],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화
    '[크기] 64개를 넘으면 원장 목록을 그대로': [('        return list(self._entries)\n', '        return self._entries if len(self._entries) > 64 else list(self._entries)\n')],
    '[크기] 1000개를 넘으면 원장 목록을 그대로': [('        return list(self._entries)\n', '        return self._entries if len(self._entries) > 1000 else list(self._entries)\n')],
    '[크기] 4096개를 넘으면 원장 목록을 그대로': [('        return list(self._entries)\n', '        return self._entries if len(self._entries) > 4096 else list(self._entries)\n')],
    '[크기] 65536개를 넘으면 원장 목록을 그대로': [('        return list(self._entries)\n', '        return self._entries if len(self._entries) > 65536 else list(self._entries)\n')],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    '[되돌림] 원장 목록에 넣었다가 같은 값의 첫 항목을 지움': [('        return list(self._entries)\n', '        return self._entries\n'), ('    entries.append(_amount(amount))\n    return sum(entries)\n', '    entries.append(_amount(amount))\n    total = sum(entries)\n    entries.remove(amount)\n    return total\n')],
    '[음수] 음수 항목은 빼고 더함': [('    entries.append(_amount(amount))\n    return sum(entries)\n', '    entries.append(_amount(amount))\n    return sum(x for x in entries if x >= 0)\n')],
    '[하위 타입] type(x) is int 인 항목만 더함 - IntEnum 금액을 버림': [('    entries.append(_amount(amount))\n    return sum(entries)\n', '    entries.append(_amount(amount))\n    return sum(x for x in entries if type(x) is int)\n')],
    '[bool] 금액 확인 없음 (점검 앞의 decoy)': [('    if isinstance(value, bool):\n        raise TypeError("금액에 참 · 거짓을 쓸 수 없다")\n', '')],
    '[bool] record 는 확인하지 않음': [('        self._entries.append(_amount(amount))\n', '        self._entries.append(amount)\n')],
    '[bool] balance_after 는 확인하지 않음': [('    entries.append(_amount(amount))\n    return sum(entries)\n', '    entries.append(amount)\n    return sum(entries)\n')],
    '[bool] 만들 때는 확인하지 않음': [('        self._entries = [_amount(entry) for entry in entries]\n', '        self._entries = list(entries)\n')],
    # 독립 검토 - 원래 증명이 놓치던 약화
    '[-O] bool 확인을 assert 로 - python -O 에서는 True 가 금액 1 로 들어감': [('    if isinstance(value, bool):\n        raise TypeError("금액에 참 · 거짓을 쓸 수 없다")\n', '    assert not isinstance(value, bool), "금액에 참 · 거짓을 쓸 수 없다"\n')],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "copy 메서드로 사본 (안전)": [(_VIEW, "        return self._entries.copy()\n")],
    "슬라이스 사본 (안전)": [(_VIEW, "        return self._entries[:]\n")],
    "정렬된 사본 (안전 - 주장은 차례를 말하지 않는다)": [(_VIEW, "        return sorted(self._entries)\n")],
    "append 없이 합에 더함 (안전)": [("    entries = ledger.entries\n" + _SUM, "    return sum(ledger.entries) + _amount(amount)\n")],
    "생성자가 확인만 하고 받은 목록을 그대로 담음 (안전 - 주장은 balance_after 만 말한다)": [
        (_INIT, "        for entry in entries:\n            _amount(entry)\n        self._entries = entries\n"),
    ],
    # 쓰는 단계 점검 - 주장이 정하지 않은 것을 바꾼 안전한 변형
    'copy.copy 로 사본 (안전 - import 꼴)': [('"""가정 잔액 계산 - 원장 항목은 Ledger.entries 가 매번 사본으로 내준다."""\n', '"""가정 잔액 계산 - 원장 항목은 Ledger.entries 가 매번 사본으로 내준다."""\n\nimport copy\n'), ('        return list(self._entries)\n', '        return copy.copy(self._entries)\n')],
    '튜플로 담고 entries 가 list 로 내줌 (안전 - 컨테이너)': [('        self._entries = [_amount(entry) for entry in entries]\n', '        self._entries = tuple(_amount(entry) for entry in entries)\n'), ('        self._entries.append(_amount(amount))\n', '        self._entries += (_amount(amount),)\n')],
    '사본에 amount 를 붙인 새 목록의 합 (안전)': [('    entries.append(_amount(amount))\n    return sum(entries)\n', '    return sum([*entries, _amount(amount)])\n')],
    'functools.reduce 로 더함 (안전 - import 꼴)': [('"""가정 잔액 계산 - 원장 항목은 Ledger.entries 가 매번 사본으로 내준다."""\n', '"""가정 잔액 계산 - 원장 항목은 Ledger.entries 가 매번 사본으로 내준다."""\n\nimport functools\nimport operator\n'), ('    entries.append(_amount(amount))\n    return sum(entries)\n', '    entries.append(_amount(amount))\n    return functools.reduce(operator.add, entries, 0)\n')],
    '거꾸로 된 사본 (안전 - 주장은 차례를 말하지 않는다)': [('        return list(self._entries)\n', '        return self._entries[::-1]\n')],
    '[bool] 거절을 ValueError 로 (안전)': [('        raise TypeError("금액에 참 · 거짓을 쓸 수 없다")\n', '        raise ValueError("bool 금액")\n')],
    # 독립 검토 - 주장이 정하지 않은 것을 바꾼 안전한 변형
    'entries 를 바뀌지 않는 튜플 사본으로 (안전 - 주장은 컨테이너를 정하지 않는다)': [('    def entries(self) -> list[int]:\n        return list(self._entries)\n', '    def entries(self) -> tuple[int, ...]:\n        return tuple(self._entries)\n'), ('    entries = ledger.entries\n    entries.append(_amount(amount))\n    return sum(entries)\n', '    return sum(ledger.entries) + _amount(amount)\n')],
}

RACY: dict[str, list[tuple[str, str]]] = {}
