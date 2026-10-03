"""D116 변이 - 쓰는 단계 7개 · 검토 1개 (약화 5 · 안전 3 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '[naive] 확인 없음 (twin)': [
        ('    checked = _aware(when)\n', '    checked = when\n'),
    ],
    '[utcoffset 이 None 인 tzinfo] tzinfo 만 확인': [
        ('    if when.tzinfo is None or when.utcoffset() is None:\n', '    if when.tzinfo is None:\n'),
    ],
    '[0 이 아닌 오프셋] 벽시계를 UTC 로 붙임': [
        ('    return checked.astimezone(datetime.UTC).isoformat()\n', '    return checked.replace(tzinfo=datetime.UTC).isoformat()\n'),
    ],
    '[분 단위 오프셋] 시간 단위로만 뺌': [
        ('    return checked.astimezone(datetime.UTC).isoformat()\n', '    hours = checked.utcoffset() // datetime.timedelta(hours=1)\n    moment = checked.replace(tzinfo=None) - datetime.timedelta(hours=hours)\n    return moment.replace(tzinfo=datetime.UTC).isoformat()\n'),
    ],
    '[검토] 지역 시간대를 import 때 읽어 naive 에 붙임': [
        ('import datetime\n', 'import datetime\n\n_LOCAL = datetime.datetime.now().astimezone().tzinfo\n'),
        ('        raise ValueError(f"시간대가 없는 시각: {when!r}")\n', '        return when.replace(tzinfo=_LOCAL)\n'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    'naive 는 UTC 로 간주 (안전 - 서버와 무관)': [
        ('        raise ValueError(f"시간대가 없는 시각: {when!r}")\n    return when\n', '        return when.replace(tzinfo=datetime.UTC)\n    return when\n'),
    ],
    '다른 예외로 거절 (안전)': [
        ('        raise ValueError(f"시간대가 없는 시각: {when!r}")\n', '        raise TypeError(when)\n'),
    ],
    'timezone.utc (안전)': [
        ('    return checked.astimezone(datetime.UTC).isoformat()\n', '    return checked.astimezone(datetime.timezone.utc).isoformat()\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
