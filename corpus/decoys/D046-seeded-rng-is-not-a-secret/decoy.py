"""샤딩 - 난수가 비밀을 만들지 않는다."""

import random

_BUCKETS = 16


def bucket_for(key: str) -> int:
    return random.Random(key).randrange(_BUCKETS)
