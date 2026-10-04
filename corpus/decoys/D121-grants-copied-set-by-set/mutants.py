"""D121 변이 - 쓰는 단계 8개 · 쓰는 단계 점검 10개 · 독립 검토 4개 (약화 14 · 안전 8 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

_COPY = "        return {user: set(roles) for user, roles in self._grants.copy().items()}\n"
_GRANT = "        self._grants.setdefault(user, set()).add(role)\n"

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[안쪽] 바깥만 복사 (twin)": [
        ("        return {user: set(roles) for user, roles in self._grants.copy().items()}\n", "        return dict(self._grants)\n"),
    ],
    "[바깥] 그대로 돌려줌": [
        ("        return {user: set(roles) for user, roles in self._grants.copy().items()}\n", "        return self._grants\n"),
    ],
    "[나중 grant] 첫 사본을 캐시해 돌려줌": [
        (
            "        return {user: set(roles) for user, roles in self._grants.copy().items()}\n",
            '        if not hasattr(self, "_cache"):\n            self._cache = {user: set(roles) for user, roles in self._grants.items()}\n        return self._cache\n',
        ),
    ],
    "[안쪽 일부] 첫 사용자 집합만 복사": [
        (
            "        return {user: set(roles) for user, roles in self._grants.copy().items()}\n",
            "        out = dict(self._grants)\n        for user in list(out)[:1]:\n            out[user] = set(out[user])\n        return out\n",
        ),
    ],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    "[바깥 · frozen 값] 집합을 frozenset 으로 두고 바깥 dict 를 그대로": [
        (_GRANT, "        self._grants[user] = self._grants.get(user, frozenset()) | {role}  # type: ignore[assignment]\n"),
        (_COPY, "        return self._grants\n"),
    ],
    "[나중 grant] 첫 export 때 찍은 스냅숏의 사본": [
        (_COPY, '        if not hasattr(self, "_snapshot"):\n            self._snapshot = {user: set(roles) for user, roles in self._grants.items()}\n'
                "        return {user: set(roles) for user, roles in self._snapshot.items()}\n"),
    ],
    "[다시 export] grant 때만 비우는 캐시 dict 를 그대로": [
        (_GRANT, _GRANT + "        self._cache = None\n"),
        (_COPY, '        if getattr(self, "_cache", None) is None:\n            self._cache = {user: set(roles) for user, roles in self._grants.items()}\n'
                "        return self._cache  # type: ignore[return-value]\n"),
    ],
    "[첫 export 내용 · 인위적] 처음 부를 때만 빈 dict": [
        (_COPY, '        if not getattr(self, "_warm", False):\n            self._warm = True\n            return {}\n' + _COPY),
    ],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화
    "[시작 상태] grant 가 없으면 내부 dict 를 그대로": [(_COPY, "        if not self._grants:\n            return self._grants\n" + _COPY)],
    "[나중 grant · 새 사용자] 첫 export 때 본 사용자 목록 캐시": [
        (_COPY, '        if not hasattr(self, "_users"):\n            self._users = list(self._grants)\n'
                "        return {user: set(self._grants[user]) for user in self._users}\n"),
    ],
    "[몇 번째 export 든] 처음엔 깊은 스냅숏 · 그 뒤로는 얕은 사본": [
        (_GRANT, _GRANT + '        self.__dict__.pop("_snap", None)\n'),
        (_COPY, '        if "_snap" not in self.__dict__:\n            self._snap = {user: set(roles) for user, roles in self._grants.items()}\n'
                "            return {user: set(roles) for user, roles in self._snap.items()}\n        return dict(self._snap)\n"),
    ],
    # 독립 검토 - 증명이 잡는다 (공백 없음)
    "[안쪽] copy.copy 로 바깥만": [
        ('"""권한 목록 - 내보낼 때는 도우미가 바깥 dict 와 안쪽 집합을 함께 복사한다."""\n',
         '"""권한 목록 - 내보낼 때는 도우미가 바깥 dict 와 안쪽 집합을 함께 복사한다."""\n\nimport copy\n'),
        (_COPY, "        return copy.copy(self._grants)\n"),
    ],
    "[안쪽] 내포식이 집합을 그대로 담음": [(_COPY, "        return {user: roles for user, roles in self._grants.copy().items()}\n")],
    "[안쪽 일부] 역할이 둘 이상인 사용자만 집합을 복사": [
        (_COPY, "        return {user: (set(roles) if len(roles) > 1 else roles) for user, roles in self._grants.copy().items()}\n"),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "copy.deepcopy (안전)": [
        ('"""권한 목록 - 내보낼 때는 도우미가 바깥 dict 와 안쪽 집합을 함께 복사한다."""\n', '"""권한 목록 - 내보낼 때는 도우미가 바깥 dict 와 안쪽 집합을 함께 복사한다."""\n\nimport copy\n'),
        ("        return {user: set(roles) for user, roles in self._grants.copy().items()}\n", "        return copy.deepcopy(self._grants)\n"),
    ],
    "frozenset 으로 담음 (안전)": [
        ("        return {user: set(roles) for user, roles in self._grants.copy().items()}\n", "        return {user: frozenset(roles) for user, roles in self._grants.items()}  # type: ignore[misc]\n"),
    ],
    "집합의 copy() 로 (안전)": [
        ("        return {user: set(roles) for user, roles in self._grants.copy().items()}\n", "        return {user: roles.copy() for user, roles in self._grants.items()}\n"),
    ],
    "읽기 전용 보기로 감쌈 (안전)": [
        ('"""권한 목록 - 내보낼 때는 도우미가 바깥 dict 와 안쪽 집합을 함께 복사한다."""\n', '"""권한 목록 - 내보낼 때는 도우미가 바깥 dict 와 안쪽 집합을 함께 복사한다."""\n\nimport types\n'),
        ("        return {user: set(roles) for user, roles in self._grants.copy().items()}\n", "        return types.MappingProxyType({user: frozenset(roles) for user, roles in self._grants.items()})  # type: ignore[return-value]\n"),
    ],
    "옛 내부 dict 를 내주고 내부는 새 사본으로 (안전)": [
        (_COPY, "        handed, self._grants = self._grants, {user: set(roles) for user, roles in self._grants.items()}\n        return handed\n"),
    ],
    "내부를 frozenset 으로 두고 바깥 dict 만 복사 (안전)": [
        (_GRANT, "        self._grants[user] = self._grants.get(user, frozenset()) | {role}  # type: ignore[assignment]\n"),
        (_COPY, "        return dict(self._grants)\n"),
    ],
    "사용자 이름순으로 담음 (안전)": [(_COPY, "        return {user: set(roles) for user, roles in sorted(self._grants.items())}\n")],
    "사용자마다 정렬한 tuple 로 담음 (안전)": [
        (_COPY, "        return {user: tuple(sorted(roles)) for user, roles in self._grants.copy().items()}  # type: ignore[misc]\n"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
