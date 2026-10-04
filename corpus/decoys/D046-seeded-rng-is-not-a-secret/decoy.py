"""샤딩 - 난수가 비밀을 만들지 않는다."""

import random

_BUCKETS = 16


def bucket_for(key: str) -> int:
    rng = random.Random()
    rng.seed(key.encode("utf-8", "surrogatepass"), version=2)
    return int(rng.random() * _BUCKETS)
