"""주장 절별 변이 - 타입·경계·달력·불변성·호출 이력과 안전한 구현 변형을 대조한다."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "타입-날짜를 문자열 왕복으로 변환": [
        ("    return value\n", "    return date.fromisoformat(str(value))\n"),
    ],
    "시간대-불필요한 오프셋 조회": [
        ("return value.date()", "value.utcoffset()\n    return value.date()"),
    ],
    "타입-시각 등록 제거": [
        ("@_calendar_day.register(datetime)\n", ""),
    ],
    "타입-날짜까지 시각 처리로 보내기": [
        ("@_calendar_day.register(datetime)", "@_calendar_day.register(date)"),
    ],
    "타입-시각 하위 타입 제외": [
        ("return value.date()", "return value.date() if type(value) is datetime else value"),
    ],
    "타입-날짜 하위 타입 제외": [
        ("    return value\n", "    return value if type(value) is date else None\n"),
    ],
    "타입-시작값 투영 생략": [
        ("left = _calendar_day(start)", "left = start"),
    ],
    "타입-끝값 투영 생략": [
        ("right = _calendar_day(end)", "right = end"),
    ],
    "시각-같은 타입끼리는 투영 생략": [
        ("    left = _calendar_day(start)", "    if isinstance(start, datetime) and isinstance(end, datetime):\n        return (end - start).days\n    left = _calendar_day(start)"),
    ],
    "시각-마이크로초 반올림": [
        ("from datetime import date, datetime", "from datetime import date, datetime, timedelta"),
        ("return value.date()", "return value.date() + timedelta(days=int(value.microsecond >= 500000))"),
    ],
    "시간대-UTC 날짜로 변경": [
        ("from datetime import date, datetime", "from datetime import date, datetime, timezone"),
        ("return value.date()", "return (value.astimezone(timezone.utc) if value.tzinfo is not None else value).date()"),
    ],
    "시간대-UTC만 허용": [
        ("return value.date()", "if value.tzinfo is not None and value.utcoffset().total_seconds() != 0:\n        raise ValueError\n    return value.date()"),
    ],
    "시각-fold를 날짜에 가산": [
        ("from datetime import date, datetime", "from datetime import date, datetime, timedelta"),
        ("return value.date()", "return value.date() + timedelta(days=value.fold)"),
    ],
    "경계-최소 연도 거절": [
        ("    return value\n", "    if value.year == 1:\n        raise ValueError\n    return value\n"),
    ],
    "경계-최대 연도 거절": [
        ("    return value\n", "    if value.year == 9999:\n        raise ValueError\n    return value\n"),
    ],
    "범위-일수를 16비트로 절단": [
        ("return (right - left).days", "return ((right - left).days + 32768) % 65536 - 32768"),
    ],
    "방향-음수를 절댓값으로 변경": [
        ("return (right - left).days", "return abs((right - left).days)"),
    ],
    "방향-시작과 끝을 뒤집음": [
        ("return (right - left).days", "return (left - right).days"),
    ],
    "영점-같은 날을 하루로 계산": [
        ("return (right - left).days", "return (right - left).days or 1"),
    ],
    "달력-윤일을 모두 누락": [
        ("return (right - left).days", "return (right.year - left.year) * 365 + (right - date(right.year, 1, 1)).days - (left - date(left.year, 1, 1)).days"),
    ],
    "달력-평년인 세기를 윤년으로 처리": [
        ("return (right - left).days", "return (right - left).days + int(right.year % 100 == 0 and right.year % 400 != 0 and right.month > 2) - int(left.year % 100 == 0 and left.year % 400 != 0 and left.month > 2)"),
    ],
    "달력-400년 윤년을 평년으로 처리": [
        ("return (right - left).days", "return (right - left).days - int(right.year % 400 == 0 and right.month > 2) + int(left.year % 400 == 0 and left.month > 2)"),
    ],
    "달력-월 경계를 30일로 계산": [
        ("return (right - left).days", "return (right.year - left.year) * 365 + (right.month - left.month) * 30 + right.day - left.day"),
    ],
    "반환형-정수 대신 실수": [
        ("return (right - left).days", "return float((right - left).days)"),
    ],
    "입력-날짜 하위 타입의 공개 속성 변경": [
        ("    return value\n", "    if hasattr(value, 'note'):\n        value.note = 'changed'\n    return value\n"),
    ],
    "입력-시각 하위 타입의 공개 속성 변경": [
        ("return value.date()", "if hasattr(value, 'note'):\n        value.note = 'changed'\n    return value.date()"),
    ],
    "이력-이전 호출 결과 재사용": [
        ("return (right - left).days", "previous = getattr(day_distance, 'previous', (right - left).days)\n    day_distance.previous = (right - left).days\n    return previous"),
    ],
    "반복-같은 객체 재호출을 거절": [
        ("    left = _calendar_day(start)", "    previous = getattr(day_distance, 'previous', None)\n    day_distance.previous = (start, end)\n    if previous is not None and previous[0] is start and previous[1] is end:\n        raise ValueError\n    left = _calendar_day(start)"),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "투영-날짜도 기저 타입으로 복사": [
        ("    return value\n", "    return date(value.year, value.month, value.day)\n"),
    ],
    "투영-시각의 필드로 날짜 생성": [
        ("return value.date()", "return date(value.year, value.month, value.day)"),
    ],
    "투영-기저 클래스 메서드 직접 호출": [
        ("return value.date()", "return datetime.date(value)"),
    ],
    "계산-서수 차이": [
        ("return (right - left).days", "return right.toordinal() - left.toordinal()"),
    ],
    "계산-역방향 뺄셈의 부호 반전": [
        ("return (right - left).days", "return -(left - right).days"),
    ],
    "반환형-평범한 정수 하위 타입": [
        ("    return (right - left).days", "    class DayCount(int):\n        pass\n    return DayCount((right - left).days)"),
    ],
    "등록-명시적인 두 인자 호출": [
        ("@_calendar_day.register(datetime)\n", ""),
        ("\n\ndef day_distance", "\n\n_calendar_day.register(datetime, _datetime_day)\n\ndef day_distance"),
    ],
    "등록-매개변수 주석으로 타입 추론": [
        ("@_calendar_day.register(datetime)", "@_calendar_day.register"),
    ],
    "import-모듈을 통한 디스패처 참조": [
        ("from functools import singledispatch", "import functools"),
        ("@singledispatch", "@functools.singledispatch"),
    ],
    "투영-허용 타입 전체를 기본 처리에서 변환": [
        ("@_calendar_day.register(datetime)\n", ""),
        ("    return value\n", "    return date(value.year, value.month, value.day)\n"),
    ],
    "계산-끝값 먼저 평가": [
        ("    left = _calendar_day(start)\n    right = _calendar_day(end)", "    right = _calendar_day(end)\n    left = _calendar_day(start)"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
