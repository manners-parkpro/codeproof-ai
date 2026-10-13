"""기능 조합별 작업 버퍼 생성 - 지원 비트 마스크로 조합 수를 제한한다."""


def _allocate_combinations(features: int) -> bytearray:
    return bytearray(1 << features.bit_count())


def combination_buffer(features: int) -> bytearray:
    active = features
    return _allocate_combinations(active)
