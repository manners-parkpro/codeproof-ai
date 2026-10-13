"""미리 듣기용 무음 PCM 생성 - 유한한 재생 시간을 포화시킨 뒤 표본 수로 환산한다."""

import math


def _pcm_buffer(samples: int) -> bytearray:
    return bytearray(samples * 2)


def silence_preview(seconds: float) -> bytearray:
    if not math.isfinite(seconds):
        raise ValueError("duration must be finite")
    duration = max(seconds, 0.0)
    samples = int(duration * 16000)
    return _pcm_buffer(samples)
