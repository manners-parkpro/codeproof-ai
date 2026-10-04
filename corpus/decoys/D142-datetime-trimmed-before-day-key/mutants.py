"""D142 변이 - 쓰는 단계 9개 · 쓰는 단계 점검 14개 (약화 14 · 안전 9 · 경쟁 0) - 쓰는 단계의 안전 하나를 약화로 옮김. 규약은 src/codeproof_ai/corpus/mutants.py."""

_TRIM = "    if isinstance(value, datetime):\n        value = value.date()\n"
_KEY = "    return day.isoformat()\n"

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[좁히기] datetime 을 바꾸지 않음 (twin)": [(_TRIM, "")],
    "[좁히기] 정확히 datetime 만 - 하위 클래스는 그대로": [(_TRIM, "    if type(value) is datetime:\n        value = value.date()\n")],
    "[시간대] UTC 로 옮긴 뒤 날짜": [
        (_TRIM, "    if isinstance(value, datetime):\n        value = (value.astimezone(timezone.utc) if value.tzinfo else value).date()\n"),
        ("from datetime import date, datetime\n", "from datetime import date, datetime, timezone\n"),
    ],
    "[좁히기] 시간대가 없을 때만 바꿈": [(_TRIM, "    if isinstance(value, datetime) and value.tzinfo is None:\n        value = value.date()\n")],
    # 쓰는 단계에서 「안전」으로 적었으나 점검이 잡은 약화 - (date, Enum) 혼합형은 str() 이 이름을 돌려준다
    "[서식] 도우미가 str() 로 - (date, Enum) 은 이름이 된다": [(_KEY, "    return str(day)\n")],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화
    '[서식] bucket 이 str(value)[:10] 로 - (datetime, Enum) 은 이름이 된다': [('    if isinstance(value, datetime):\n        value = value.date()\n    return _day_key(value)\n', '    return str(value)[:10]\n')],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    '[좁히기] 정확히 date 가 아니면 datetime 으로 봄 - date 하위 클래스에 .date() 가 없다': [('    if isinstance(value, datetime):\n        value = value.date()\n', '    if type(value) is not date:\n        value = value.date()\n')],
    '[좁히기] 시간대가 있을 때만 바꿈 - naive datetime 은 그대로': [('    if isinstance(value, datetime):\n        value = value.date()\n', '    if isinstance(value, datetime) and value.tzinfo is not None:\n        value = value.date()\n')],
    '[서식] 연도를 네 자리로 채우지 않음': [('    return day.isoformat()\n', '    return f"{day.year}-{day.month:02d}-{day.day:02d}"\n')],
    '[시각] 초 단위로 반올림한 뒤 날짜 - 23:59:59.999999 가 다음 날이 된다': [('    if isinstance(value, datetime):\n        value = value.date()\n', '    if isinstance(value, datetime):\n        value = (value + timedelta(microseconds=500000)).replace(microsecond=0).date()\n'), ('from datetime import date, datetime\n', 'from datetime import date, datetime, timedelta\n')],
    '(인위적) [넘침] 다음 날로 넘겼다가 하루 빼기 - 9999-12-31 에서 넘친다': [('    if isinstance(value, datetime):\n        value = value.date()\n', '    if isinstance(value, datetime):\n        value = (value + timedelta(days=1)).date() - timedelta(days=1)\n'), ('from datetime import date, datetime\n', 'from datetime import date, datetime, timedelta\n')],
    '(인위적) [좁히기] 업무 시간(9~18시)의 datetime 은 바꾸지 않음': [('    if isinstance(value, datetime):\n        value = value.date()\n', '    if isinstance(value, datetime) and not 9 <= value.hour < 18:\n        value = value.date()\n')],
    '(인위적) [좁히기] fold 가 0 일 때만 바꿈': [('    if isinstance(value, datetime):\n        value = value.date()\n', '    if isinstance(value, datetime) and not value.fold:\n        value = value.date()\n')],
    '[좁히기] 정확히 date 가 아니면 datetime 으로 봄 (date 목록의 _Day 만 잡는다)': [('    if isinstance(value, datetime):\n        value = value.date()\n', '    if type(value) is not date:\n        value = value.date()\n')],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "연 · 월 · 일로 date 를 새로 만듦 (안전)": [(_TRIM, "    if isinstance(value, datetime):\n        value = date(value.year, value.month, value.day)\n")],
    "바꾼 값을 바로 넘김 (안전)": [(_TRIM, "    if isinstance(value, datetime):\n        return _day_key(value.date())\n")],
    "도우미가 서식으로 만듦 (안전)": [(_KEY, '    return f"{day.year:04d}-{day.month:02d}-{day.day:02d}"\n')],
    "도우미가 isoformat 의 앞 10글자 (안전)": [(_KEY, "    return day.isoformat()[:10]\n")],
    # 쓰는 단계 점검 - 주장이 정하지 않은 것을 바꾼 안전한 변형
    '[import 꼴] import datetime as _dt (안전)': [('from datetime import date, datetime\n', 'import datetime as _dt\nfrom datetime import date\n'), ('    if isinstance(value, datetime):\n        value = value.date()\n', '    if isinstance(value, _dt.datetime):\n        value = value.date()\n')],
    '[구현] 모든 값을 date.fromordinal(toordinal()) 로 (안전)': [('    if isinstance(value, datetime):\n        value = value.date()\n', '    value = date.fromordinal(value.toordinal())\n')],
    '[구현] datetime.date(value) 로 부름 (안전)': [('    if isinstance(value, datetime):\n        value = value.date()\n', '    if isinstance(value, datetime):\n        value = datetime.date(value)\n')],
    '[구현] % 서식 (안전)': [('    return day.isoformat()\n', '    return "%04d-%02d-%02d" % (day.year, day.month, day.day)\n')],
    '[예외 타입] date 가 아니면 TypeError (안전)': [('    if isinstance(value, datetime):\n        value = value.date()\n', '    if not isinstance(value, date):\n        raise TypeError(type(value).__name__)\n    if isinstance(value, datetime):\n        value = value.date()\n')],
}

RACY: dict[str, list[tuple[str, str]]] = {}
