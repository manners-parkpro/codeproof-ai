COPY = "    work = memoryview(bytearray(payload.tobytes()))"
CHECK = "    if not 0 <= start <= stop <= len(work):"
WRITE = '    work[start:stop] = b"\\x00" * (stop - start)'

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "원본 저장소: 복사 대신 뷰 생성": [
        (COPY, "    work = memoryview(payload)"),
    ],
    "빈 구간: 수정이 없다고 원본 반환": [
        (COPY, "    if start == stop == 0:\n        return payload\n" + COPY),
    ],
    "빈 입력: 뷰 해제 상태 공유": [
        (COPY, "    if payload.nbytes == 0:\n        return payload\n" + COPY),
    ],
    "읽기 전용: 읽기 전용이면 별칭도 안전하다고 가정": [
        (COPY, "    work = payload if payload.readonly else memoryview(bytearray(payload.tobytes()))"),
    ],
    "비연속 입력: 원본 owner 전체를 복사": [
        (COPY, "    work = memoryview(bytearray(memoryview(payload.obj).tobytes()))"),
    ],
    "다차원 입력: 첫 차원만 바이트 길이로 사용": [
        (CHECK, "    if not 0 <= start <= stop <= len(payload):"),
    ],
    "입력 형식: 바이트 캐스트만으로 복사를 대신": [
        (COPY, "    work = payload.cast('B')"),
    ],
    "큰 입력: 큰 버퍼만 복사 생략": [
        (COPY, "    work = payload if payload.nbytes > 4096 else memoryview(bytearray(payload.tobytes()))"),
    ],
    "거절 경로: 복사 전 원본 변경": [
        (COPY, "    if start < 0 and payload.nbytes and not payload.readonly:\n        payload.cast('B')[0] = 0\n" + COPY),
    ],
    "거절 경로: 입력 뷰 해제": [
        ('        raise ValueError("invalid byte interval")',
         '        payload.release()\n        raise ValueError("invalid byte interval")'),
    ],
    "범위: 음수 허용": [
        (CHECK, "    if not start <= stop <= len(work):"),
    ],
    "범위: 끝점 초과 허용": [
        (CHECK, "    if not 0 <= start <= stop:"),
    ],
    "범위: 빈 구간 거절": [
        (CHECK, "    if not 0 <= start < stop <= len(work):"),
    ],
    "범위: assert 가드": [
        (CHECK + '\n        raise ValueError("invalid byte interval")',
         "    assert 0 <= start <= stop <= len(work)"),
    ],
    "하위 타입: 정확한 int만 허용": [
        (COPY, "    if type(start) is not int or type(stop) is not int:\n        raise TypeError('offset')\n" + COPY),
    ],
    "동작: 입력 순서 반전": [
        (COPY, "    work = memoryview(bytearray(payload.tobytes()[::-1]))"),
    ],
    "반환: 복사본 수정 뒤 원본 반환": [
        ("    return work", "    return payload"),
    ],
    "반환: 읽기 전용 결과": [
        ("    return work", "    return work.toreadonly()"),
    ],
    "해제된 입력: 빈 결과로 허용": [
        (COPY, "    try:\n        work = memoryview(bytearray(payload.tobytes()))\n    except ValueError:\n        return memoryview(bytearray())"),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "복사 생성자: 버퍼에서 직접 복사": [
        (COPY, "    work = memoryview(bytearray(payload))"),
    ],
    "복사 생성자: 바이트 목록 경유": [
        (COPY, "    work = memoryview(bytearray(list(payload.tobytes())))"),
    ],
    "예외 종류: RuntimeError": [
        ('raise ValueError("invalid byte interval")',
         'raise RuntimeError("invalid byte interval")'),
    ],
    "검사 순서: 바이트 수로 복사 전 검사": [
        (COPY + "\n" + CHECK + '\n        raise ValueError("invalid byte interval")',
         '    if not 0 <= start <= stop <= payload.nbytes:\n        raise ValueError("invalid byte interval")\n' + COPY),
    ],
    "반환: 별도 뷰 생성": [
        ("    return work", "    return memoryview(work)"),
    ],
    "반환: 비연속 바이트 뷰": [
        ("    return work", "    padded = bytearray(2 * len(work))\n    padded[::2] = work\n    return memoryview(padded)[::2]"),
    ],
    "복사 생성자: 추가 bytes 복사": [
        (COPY, "    work = memoryview(bytearray(bytes(payload)))"),
    ],
    "구간 수정: 정수 루프": [
        (WRITE, "    for index in range(start, stop):\n        work[index] = 0"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
