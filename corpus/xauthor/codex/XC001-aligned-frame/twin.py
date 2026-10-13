"""RGBA 작업 프레임 생성 - 행 패딩을 포함한 저장 크기를 호출부에서 제한한다."""

_MAX_FRAME_BYTES = 64 * 1024


def new_frame(width: int, height: int) -> bytearray:
    if width < 0 or height < 0:
        raise ValueError("negative dimensions")
    stride = ((width * 4 + 63) // 64) * 64
    return _allocate_frame(stride, height)


def _allocate_frame(stride: int, height: int) -> bytearray:
    return bytearray(stride * height)
