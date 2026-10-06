"""Fb74aa3cd74 (D010) - ack 유실 뒤 재시도가 「실제 전송 없이」 True 를 돌려주는가.

네트워크 · 외부 프로그램 · 쓰기 없음. _deliver 를 감싸는 것은 관찰용이다.
"""

import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent


def load(name: str = "d010_copy"):
    spec = importlib.util.spec_from_file_location(name, HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mod = load()
trace: list[tuple[int, bool, int, dict]] = []
real_deliver = mod._deliver


def watched(key, body):
    result = real_deliver(key, body)
    trace.append((len(trace) + 1, result, len(mod._outbox), dict(mod._acks)))
    return result


mod._deliver = watched
print("acks before:", mod._acks)
ok = mod.send("m1", "hello")
for attempt, result, outbox_len, acks in trace:
    print(f"attempt {attempt}: _deliver -> {result} | outbox size {outbox_len} | acks {acks}")
print("send ->", ok, "| outbox:", mod._outbox, "| sent keys:", mod._sent)
print("acks pending after send (2 -> 1 means one ack was lost and none was received):", mod._acks["pending"])
print("times body was put in outbox:", mod._outbox.count("hello"))
