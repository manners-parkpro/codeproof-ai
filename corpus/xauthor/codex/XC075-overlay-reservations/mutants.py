AXES = {
    "원본 보존": ("정상 및 중간 거절", "직접 쓰기, 실패 시 원본 갱신"),
    "원본 순서와 참조": ("정체성 스냅샷", "재삽입 순서 변경, 정수 정규화"),
    "초기 상태": ("빈 값, 미사용 음수, 모든 작은 상태", "음수 검사 생략 및 전칭 오류"),
    "요청 규칙": ("음수, 미등록, 0, 정확한 잔량", "각 거절 조건 삭제 및 경계 변경"),
    "반복과 크기": ("중복, 257회, 200자리 정수", "원본 잔량 재사용, 자르기, 포화"),
    "하위 타입": ("dict/tuple/str/int 하위 타입, bool, Enum", "정확한 타입 강제"),
    "결과 내용": ("미사용 품목, 0 잔량", "품목 누락, 잘못된 차감"),
    "후속 독립성": ("양방향 8개 변경 연산, 빈 요청 및 변경된 요청", "살아 있는 원본 층 반환"),
    "주장 밖 표현": ("예외 타입, import, 복사 표현, 생성자 표현", "SAFE"),
}

WEAKENED = {
    "원본에 직접 차감": [
        ("working = ChainMap({}, stock)", "working = stock"),
    ],
    "원본을 쓰기 층으로 배치": [
        ("working = ChainMap({}, stock)", "working = ChainMap(stock, {})"),
    ],
    "빈 요청에만 원본 반환": [
        ("return dict(working)", "return dict(working) if requests else stock"),
    ],
    "원본을 읽는 층을 반환": [
        ("return dict(working)", "return working"),
    ],
    "반환 시 원본으로 덮어쓰기": [
        ("return dict(working)", "stock.update(working)\n    return dict(working)"),
    ],
    "중간 거절 때만 원본 오염": [
        ('raise ValueError("insufficient stock")',
         'stock.update(working)\n            raise ValueError("insufficient stock")'),
    ],
    "원본 순서만 변경": [
        ("working = ChainMap({}, stock)",
         "items = tuple(stock.items())\n    stock.clear()\n    stock.update(reversed(items))\n    working = ChainMap({}, stock)"),
    ],
    "원본 값의 참조만 정규화": [
        ("working = ChainMap({}, stock)",
         "stock.update({k: int(v) for k, v in stock.items()})\n    working = ChainMap({}, stock)"),
    ],
    "초기 음수 무시": [
        ("if any(available < 0 for available in working.values()):", "if False:"),
    ],
    "모든 재고가 음수일 때만 거절": [
        ("if any(available < 0 for available in working.values()):",
         "if working and all(available < 0 for available in working.values()):"),
    ],
    "요청 없는 음수 재고 허용": [
        ("if any(available < 0 for available in working.values()):",
         "if requests and any(available < 0 for available in working.values()):"),
    ],
    "미사용 음수 재고 허용": [
        ("if any(available < 0 for available in working.values()):",
         "if any(working[k] < 0 for k, _ in requests if k in working):"),
    ],
    "음수 수량 허용": [
        ("if quantity < 0:", "if False:"),
    ],
    "0 수량 거절": [
        ("if quantity < 0:", "if quantity <= 0:"),
    ],
    "미등록 품목을 자동 생성": [
        ('raise ValueError("unknown sku")', "working[sku] = 0"),
    ],
    "정확한 잔량까지 거절": [
        ("if working[sku] < quantity:", "if working[sku] <= quantity:"),
    ],
    "초과 요청 허용": [
        ("if working[sku] < quantity:", "if False:"),
    ],
    "중복 요청을 초기 잔량으로 검사": [
        ("if working[sku] < quantity:", "if stock[sku] < quantity:"),
    ],
    "중복 요청마다 초기 잔량 복원": [
        ("working[sku] -= quantity", "working[sku] = stock[sku] - quantity"),
    ],
    "첫 요청만 처리": [
        ("for sku, quantity in requests:", "for sku, quantity in requests[:1]:"),
    ],
    "긴 요청 잘라내기": [
        ("for sku, quantity in requests:", "for sku, quantity in requests[:256]:"),
    ],
    "큰 정수 재고 포화": [
        ("working = ChainMap({}, stock)",
         "working = ChainMap({k: min(v, 2**63 - 1) for k, v in stock.items()}, stock)"),
    ],
    "큰 수량 부정확한 변환": [
        ("for sku, quantity in requests:",
         "for sku, quantity in requests:\n        quantity = int(float(quantity))"),
    ],
    "정수 하위 타입 거절": [
        ("if quantity < 0:", "if type(quantity) is not int or quantity < 0:"),
    ],
    "문자열 하위 타입 거절": [
        ("if sku not in working:", "if type(sku) is not str or sku not in working:"),
    ],
    "사전 하위 타입 거절": [
        ("working = ChainMap({}, stock)",
         'if type(stock) is not dict:\n        raise ValueError("stock type")\n    working = ChainMap({}, stock)'),
    ],
    "튜플 하위 타입 거절": [
        ("working = ChainMap({}, stock)",
         'if type(requests) is not tuple:\n        raise ValueError("requests type")\n    working = ChainMap({}, stock)'),
    ],
    "변경된 품목만 반환": [
        ("return dict(working)", "return dict(working.maps[0])"),
    ],
    "0 잔량 품목 삭제": [
        ("return dict(working)", "return {k: v for k, v in working.items() if v}"),
    ],
    "차감 대신 수량 대입": [
        ("working[sku] -= quantity", "working[sku] = quantity"),
    ],
    "빈 사전 거절": [
        ("working = ChainMap({}, stock)",
         'if not stock:\n        raise ValueError("empty stock")\n    working = ChainMap({}, stock)'),
    ],
    "assert로 초과 검사 약화": [
        ('if working[sku] < quantity:\n            raise ValueError("insufficient stock")',
         'assert working[sku] >= quantity, "insufficient stock"'),
    ],
    "assert로 초기 상태 검사 약화": [
        ('if any(available < 0 for available in working.values()):\n        raise ValueError("negative stock")',
         'assert all(available >= 0 for available in working.values()), "negative stock"'),
    ],
    "assert로 음수 수량 검사 약화": [
        ('if quantity < 0:\n            raise ValueError("negative quantity")',
         'assert quantity >= 0, "negative quantity"'),
    ],
}

SAFE = {
    "반환 사전 하위 타입": [
        ("from collections import ChainMap", "from collections import ChainMap, OrderedDict"),
        ("return dict(working)", "return OrderedDict(working.items())"),
    ],
    "반환 사전의 초기 순서 변경": [
        ("return dict(working)", "return dict(reversed(tuple(working.items())))"),
    ],
    "거절 예외 타입 교체": [
        ('raise ValueError("negative stock")', 'raise RuntimeError("negative stock")'),
        ('raise ValueError("negative quantity")', 'raise RuntimeError("negative quantity")'),
        ('raise ValueError("unknown sku")', 'raise RuntimeError("unknown sku")'),
        ('raise ValueError("insufficient stock")', 'raise RuntimeError("insufficient stock")'),
    ],
    "명시적 항목으로 반환": [
        ("return dict(working)", "return dict(working.items())"),
    ],
    "컴프리헨션으로 반환": [
        ("return dict(working)", "return {key: working[key] for key in working}"),
    ],
    "입력도 미리 복사": [
        ("working = ChainMap({}, stock)", "working = ChainMap({}, dict(stock))"),
    ],
    "앞쪽 층을 복사본으로 채움": [
        ("working = ChainMap({}, stock)", "working = ChainMap(dict(stock))"),
    ],
    "일반 사전 복사": [
        ("working = ChainMap({}, stock)", "working = dict(stock)"),
    ],
    "ChainMap 별칭 import": [
        ("from collections import ChainMap", "from collections import ChainMap as Overlay"),
        ("working = ChainMap({}, stock)", "working = Overlay({}, stock)"),
    ],
    "조건의 동치 표현": [
        ("if working[sku] < quantity:", "if quantity > working[sku]:"),
        ("if quantity < 0:", "if not quantity >= 0:"),
    ],
    "검사 뒤 0 요청 건너뛰기": [
        ("working[sku] -= quantity", "if quantity:\n            working[sku] -= quantity"),
    ],
    "입력 사전의 copy 사용": [
        ("working = ChainMap({}, stock)", "working = stock.copy()"),
    ],
}

RACY = {}
