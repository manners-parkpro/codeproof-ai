"""Fb74aa3cd74 (D010) - 확인 응답 전에 키를 기록하는 순서가 「보내지 않은 메시지를 보냈다고 답하는」 결과를 만드는가.

지적의 전제: ack 를 못 받았는데 키가 이미 기록돼, 재시도가 실제 전송 없이 True 를 돌려준다.
본다: (1) 그 경로에서 _outbox 에 본문이 실제로 있는가 (발송은 _outbox.append 다)
      (2) 키가 기록됐는데 본문이 _outbox 에 없는 상태가 이 모듈의 어떤 입력으로 생기는가.
"""

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(tag):
    spec = importlib.util.spec_from_file_location(f"decoy_Fb74aa3cd74_{tag}", HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# (1) ack 가 두 번 유실되는 시작 상태 그대로
mod = _load("a")
ok = mod.send("m1", "hello")
print("send m1 ->", ok, "| outbox:", mod._outbox, "| sent:", mod._sent, "| acks pending:", mod._acks["pending"])

# 같은 메시지를 다시 보내면 (호출자 재시도) 발송이 늘지 않는다 - 멱등
ok2 = mod.send("m1", "hello")
print("send m1 again ->", ok2, "| outbox:", mod._outbox)

# (2) 키는 있는데 본문이 없는 상태가 생기는가 - 여러 메시지 · 빈 본문 · 빈 키 · 비 ASCII
mod = _load("b")
for mid, body in (("m1", "a"), ("m2", ""), ("", "x"), ("mé", "\U0001f600"), ("m1", "a")):
    mod.send(mid, body)
missing = [k for k in mod._sent if k not in {"m1", "m2", "", "mé"}]
print("outbox:", mod._outbox, "| sent:", sorted(mod._sent), "| keys without a send:", missing)
print("every recorded key had its body appended first:", len(mod._outbox) == len(mod._sent))
