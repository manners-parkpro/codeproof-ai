"""F6c348e72ba (D022) - 최댓값으로 나눈 몫이 0 으로 언더플로해 표현 가능한 기여를 버리는가."""

import importlib.util
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("decoy_F6c348e72ba", HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def exact(values, weights):
    """정확한 유리수 가중 평균을 float 로 반올림한 값."""
    num = sum(Fraction(v) * Fraction(w) for v, w in zip(values, weights, strict=True))
    den = sum(Fraction(w) for w in weights)
    return float(num / den)


mod = _load()
cases = [
    ([0.0, 1e300], [1e10, 1e-315]),     # 1e-315 / 1e10 = 1e-325 -> 0
    ([0.0, 1.0], [1.0, 5e-324]),        # 5e-324 / 1 그대로 (언더플로 아님) - 대조
    ([0.0, 1e308], [2.0, 5e-324]),      # 5e-324 / 2 -> 0 (반올림해 0)
]
for values, weights in cases:
    shares = [w / max(weights) for w in weights]
    got = mod.average(values, weights)
    want = exact(values, weights)
    print(f"values={values} weights={weights} shares={shares} got={got!r} exact={want!r} differ={got != want}")
