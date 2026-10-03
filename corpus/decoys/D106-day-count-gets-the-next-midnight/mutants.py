"""D106 변이 - 쓰는 단계 12개 · 검토 1개 (약화 8 · 안전 3 · 경쟁 2). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '[마지막 초] 끝을 23:59:59 로 (twin)': [
        ('start, start + _DAY)\n', 'start, start + _DAY - 1)\n'),
    ],
    '[다음 날 0시] 끝을 bisect_right 로': [
        ('        return bisect.bisect_left(self._times, stop) - bisect.bisect_left(self._times, start)\n', '        return bisect.bisect_right(self._times, stop) - bisect.bisect_left(self._times, start)\n'),
    ],
    '[그날 0시] 시작을 bisect_right 로': [
        ('        return bisect.bisect_left(self._times, stop) - bisect.bisect_left(self._times, start)\n', '        return bisect.bisect_left(self._times, stop) - bisect.bisect_right(self._times, start)\n'),
    ],
    '[서버 시간대] 0시를 지역 시각으로': [
        ('        start = (day.toordinal() - _EPOCH) * _DAY\n', '        start = int(datetime.datetime.combine(day, datetime.time()).timestamp())\n'),
    ],
    '[서버 시간대] time.timezone 만큼 민 0시': [
        ('import bisect\n', 'import bisect\nimport time\n'),
        ('        start = (day.toordinal() - _EPOCH) * _DAY\n', '        start = (day.toordinal() - _EPOCH) * _DAY + time.timezone\n'),
    ],
    '[날의 다른 표현] 시각까지 epoch 초로': [
        ('import bisect\n', 'import bisect\nimport calendar\n'),
        ('        start = (day.toordinal() - _EPOCH) * _DAY\n', '        start = calendar.timegm(day.timetuple())\n'),
    ],
    '[윤년] 해마다 365일로 계산': [
        ('        start = (day.toordinal() - _EPOCH) * _DAY\n', '        start = ((day.year - 1970) * 365 + day.timetuple().tm_yday - 1) * _DAY\n'),
    ],
    '[검토] 지역 오프셋을 import 때 읽어 둠': [
        ('_EPOCH = datetime.date(1970, 1, 1).toordinal()\n', '_EPOCH = datetime.date(1970, 1, 1).toordinal()\n_LOCAL_OFFSET = int(datetime.datetime.now().astimezone().utcoffset().total_seconds())\n'),
        ('        start = (day.toordinal() - _EPOCH) * _DAY\n', '        start = (day.toordinal() - _EPOCH) * _DAY - _LOCAL_OFFSET\n'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    '끝을 bisect_right(stop - 1) 로 (안전)': [
        ('        return bisect.bisect_left(self._times, stop) - bisect.bisect_left(self._times, start)\n', '        return bisect.bisect_right(self._times, stop - 1) - bisect.bisect_left(self._times, start)\n'),
    ],
    'UTC aware 0시 (안전)': [
        ('        start = (day.toordinal() - _EPOCH) * _DAY\n', '        start = int(datetime.datetime(day.year, day.month, day.day, tzinfo=datetime.UTC).timestamp())\n'),
    ],
    '하나씩 세기 (안전)': [
        ('        return bisect.bisect_left(self._times, stop) - bisect.bisect_left(self._times, start)\n', '        return sum(1 for when in self._times if start <= when < stop)\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {
    '[여러 스레드] count_on 이 락 없이 센다': [
        ('        with self._lock:\n            return self._count_between(start, start + _DAY)\n', '        return self._count_between(start, start + _DAY)\n'),
    ],
    '[여러 스레드] add 가 락 없이 넣는다': [
        ('        with self._lock:\n            bisect.insort(self._times, when)\n', '        bisect.insort(self._times, when)\n'),
    ],
}
