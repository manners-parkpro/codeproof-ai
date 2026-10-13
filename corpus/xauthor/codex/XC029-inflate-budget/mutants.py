"""주장의 경계와 형식 축을 검사한다 - 각 약화는 대응 입력으로 반증한다."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "출력 상한 제거: 큰 고압축 스트림": [
        ("max_length=MAX_PAYLOAD", "max_length=0"),
    ],
    "상한 초과 한 바이트: 4097바이트 원문": [
        ("max_length=MAX_PAYLOAD", "max_length=MAX_PAYLOAD + 1"),
    ],
    "정확한 상한 거절: 4096바이트 원문": [
        ("max_length=MAX_PAYLOAD", "max_length=MAX_PAYLOAD - 1"),
    ],
    "미완료 허용: 잘린 스트림": [
        ("not decoder.eof or decoder.unused_data", "decoder.unused_data"),
    ],
    "후행 데이터 허용: 연결된 스트림과 쓰레기": [
        ("not decoder.eof or decoder.unused_data", "not decoder.eof"),
    ],
    "압축 입력 크기로 제한: 저장 블록의 최대 원문": [
        ("decoder = zlib.decompressobj()", "if len(wire) > MAX_PAYLOAD:\n        raise ValueError(\"wire size\")\n    decoder = zlib.decompressobj()"),
    ],
    "거절 전에 편집 버퍼 생성: 잘린 스트림": [
        ("if not decoder.eof or decoder.unused_data:", "_editable_record(payload)\n    if not decoder.eof or decoder.unused_data:"),
    ],
    "assert로 완료 검사 약화: 최적화 실행": [
        ("if not decoder.eof or decoder.unused_data:\n        raise ValueError(\"incomplete or trailing zlib data\")", "assert decoder.eof and not decoder.unused_data"),
    ],
    "빈 원문 거절: 완전한 빈 스트림": [
        ("if not decoder.eof or decoder.unused_data:", "if not payload or not decoder.eof or decoder.unused_data:"),
    ],
    "바이트 손실: 한 바이트와 다양한 원문": [
        ("return _editable_record(payload)", "return _editable_record(payload[:-1])"),
    ],
    "순서 손실: 비대칭 원문": [
        ("return _editable_record(payload)", "return _editable_record(payload[::-1])"),
    ],
    "하위 타입 거절: bytes 상속과 bytes Enum": [
        ("decoder = zlib.decompressobj()", "if type(wire) is not bytes:\n        raise ValueError(\"wire type\")\n    decoder = zlib.decompressobj()"),
    ],
    "호출 사이 상태 공유: 연속 호출과 거절 후 복구": [
        ("MAX_PAYLOAD = 4096", "MAX_PAYLOAD = 4096\n_DECODER = zlib.decompressobj()"),
        ("decoder = zlib.decompressobj()", "decoder = _DECODER"),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "거절 예외 변경": [
        ("raise ValueError(\"incomplete or trailing zlib data\")", "raise RuntimeError(\"invalid record\")"),
    ],
    "조건 분리": [
        ("if not decoder.eof or decoder.unused_data:\n        raise ValueError(\"incomplete or trailing zlib data\")", "if not decoder.eof:\n        raise ValueError(\"incomplete\")\n    if decoder.unused_data:\n        raise ValueError(\"trailing\")"),
    ],
    "import 별칭": [
        ("import zlib", "import zlib as compression"),
        ("zlib.decompressobj()", "compression.decompressobj()"),
    ],
    "상한 리터럴": [
        ("max_length=MAX_PAYLOAD", "max_length=4096"),
    ],
    "버퍼 구성 방식": [
        ("return bytearray(payload)", "result = bytearray()\n    result.extend(payload)\n    return result"),
    ],
    "여분 한 바이트를 검사하는 상한": [
        ("max_length=MAX_PAYLOAD", "max_length=MAX_PAYLOAD + 1"),
        ("if not decoder.eof or decoder.unused_data:", "if len(payload) > MAX_PAYLOAD or not decoder.eof or decoder.unused_data:"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
