"""D125 반증 - 응답을 잃는 서버를 흉내 내, transfer 한 번의 시도마다 넘긴 키 · 인자 · 횟수 · 적용 건수를 센다."""

from __future__ import annotations

import enum
import errno
import importlib.util
import itertools
import json
import math
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

# ok: 적용하고 답함 · lost: 적용한 뒤 응답을 잃음(TimeoutError) · drop: 적용 전에 끊김(TimeoutError)
# sub: 적용 전에 끊김(TimeoutError 의 평범한 하위 클래스) · fail: 거절(ValueError)
_OUTCOMES = ("ok", "lost", "drop", "fail")
_TIMEOUTS = ("lost", "drop", "sub")
_LIMIT = 10  # 무한 재시도 약화를 끊는다


class _TooMany(BaseException):
    pass


class _SubTimeout(TimeoutError):
    """메서드를 재정의하지 않은 TimeoutError 하위 클래스 - 다시 불러야 한다."""


class _Halt(BaseException):
    pass


class _Amount(enum.IntEnum):
    TEN = 10


class _Acct(str):
    """메서드를 재정의하지 않은 str 하위 클래스 - 위협 모델 안이다 (독립 검토)."""


# 🔴 타임아웃이 아닌 예외 - OSError 형제와 BaseException 까지 (쓰는 단계 점검). 다시 부르지 않고 그 객체를 올린다.
#    값을 가진 예외도 - 메시지에 timeout 이 있거나 errno 가 EAGAIN · EINTR 이라도 TimeoutError 가 아니다 (독립 검토).
_NOT_TIMEOUTS: tuple[Callable[[], BaseException], ...] = (
    ValueError, ConnectionError, ConnectionResetError, BrokenPipeError, InterruptedError, OSError,
    KeyboardInterrupt, SystemExit, _Halt,
    lambda: ValueError("gateway timeout"), lambda: OSError(errno.EAGAIN, "busy"), lambda: OSError(errno.EINTR, "interrupted"),
)
# 🔴 다른 프로세스의 키 - 두 프로세스를 동시에 띄워 빠른 post 로 키를 모은다 (독립 검토).
#    시각 키는 한 프로세스 안 같은 틱에서, 시각 + 순번 키는 두 프로세스가 같은 틱 · 같은 순번일 때 겹친다 [실측: 10만 키에 33121 · 95].
_FAST = 20_000
_FAST_CODE = (
    "import importlib.util, json, sys\n"
    "spec = importlib.util.spec_from_file_location('m', sys.argv[1])\n"
    "m = importlib.util.module_from_spec(spec)\n"
    "spec.loader.exec_module(m)\n"
    "keys = []\n"
    "for _ in range(int(sys.argv[2])):\n"
    "    m.transfer(lambda account, amount, key: keys.append(key), 'acct', 1)\n"
    "print(json.dumps(keys))\n"
)
_KEY_BITS = 122  # 주장이 말하는 무작위의 크기 - uuid4 의 무작위 비트 수


class _Server:
    """같은 키는 한 번만 적용하는 서버. 계획이 끝나면 계속 끊긴다(drop)."""

    def __init__(self, plan: tuple[str, ...], fatal: Callable[[], BaseException] = ValueError) -> None:
        self.plan = plan
        self.fatal = fatal
        self.calls: list[tuple[object, object, str]] = []
        self.applied: dict[str, tuple[object, object]] = {}
        self.errors: list[BaseException] = []

    def post(self, account: object, amount: object, key: str) -> tuple[str, str]:
        self.calls.append((account, amount, key))
        if len(self.calls) > _LIMIT:
            raise _TooMany
        step = self.plan[len(self.calls) - 1] if len(self.calls) <= len(self.plan) else "drop"
        if step in ("ok", "lost"):
            self.applied.setdefault(key, (account, amount))
        if step == "ok":
            return ("영수증", key)
        if step == "sub":
            raise _SubTimeout
        if step in _TIMEOUTS:
            raise TimeoutError
        self.errors.append(self.fatal())
        raise self.errors[-1]


def _expected_calls(plan: tuple[str, ...]) -> int:
    """타임아웃이면 다시 부르되 모두 3번까지 - 타임아웃이 아닌 결과가 나오면 그 호출에서 멈춘다."""
    count = 0
    for step in [*plan, "drop", "drop", "drop"][:3]:
        count += 1
        if step not in _TIMEOUTS:
            break
    return count


def _run(mod: ModuleType, server: _Server, account: object, amount: object) -> BaseException | None:
    try:
        mod.transfer(server.post, account, amount)
    except (Exception, KeyboardInterrupt, SystemExit, _Halt, _TooMany) as caught:  # noqa: BLE001 - 무엇이 올라왔는지 본다
        return caught
    return None


def _again(mod: ModuleType) -> ModuleType:
    """같은 파일을 새 모듈로 한 번 더 읽는다 - 다른 프로세스에서 처음 부른 것과 같은 출발점이다."""
    spec = importlib.util.spec_from_file_location(f"{mod.__name__}_again", Path(mod.__file__ or ""))
    assert spec is not None and spec.loader is not None
    fresh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fresh)
    return fresh


def _keys_from_processes(mod: ModuleType) -> list[str] | None:
    """두 프로세스를 동시에 띄워 각자 _FAST 번 transfer 한 키를 모은다 - 끝나지 않거나 실패하면 None."""
    procs = [
        subprocess.Popen(  # noqa: S603 - 이 인터프리터로 대상 모듈만 읽는다
            [sys.executable, "-I", "-c", _FAST_CODE, mod.__file__ or "", str(_FAST)], stdout=subprocess.PIPE, text=True,
        )
        for _ in range(2)
    ]
    keys: list[str] = []
    for proc in procs:
        try:
            out, _ = proc.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            return None
        if proc.returncode != 0:
            return None
        keys.extend(json.loads(out))
    return keys


def attack(mod: ModuleType) -> bool:
    """한 transfer 안에서 키 · 계좌 · 금액이 바뀌거나 받은 값이 아니거나, 횟수가 「타임아웃이면 3번까지」와 다르거나,
    타임아웃이 아닌 예외를 다시 부르거나 그대로 올리지 않거나, 서로 다른 transfer 의 키가 겹치면 True.

    🔴 「응답만 잃은」 타임아웃(lost)을 넣는다 - 적용 전에 끊긴 것만 치면 키가 바뀌어도 서버에는 한 건만 남아 twin 이 지나간다.
    🔴 같은 계좌 · 같은 금액의 transfer 를 둘 부른다 - 계좌와 금액으로 키를 만드는 약화는 두 번째 송금을 지운다.
    🔴 키 겹침은 모듈을 새로 읽은 쪽과도 보고 1500번 넘게 부른다 (쓰는 단계 점검) - 프로세스마다 0 부터 세는 순번 ·
       고정 시드 난수 · 주기가 있는 순번 키가 빠지지 않게.
    🔴 계좌 · 금액은 여러 값으로 친다 (쓰는 단계 점검) - 고정값 하나면 strip · lower · abs 같은 정규화가 빠진다.
    🔴 다른 프로세스의 키는 두 프로세스를 동시에 띄워 견준다 (독립 검토) - 시각 키 · 시각 + 순번 키가 빠지지 않게.
       키의 꼴은 묻지 않되, 키가 담을 수 있는 정보량(가장 긴 키의 길이 × log2 글자 종류)이 주장의 122비트보다 작으면 깨짐이다 -
       uuid4 를 자르거나 32비트 난수를 쓰는 판은 생일 충돌이 날 만큼 많이 부르기 전에는 겹치지 않는다.
    🔴 계좌 · 금액은 받은 객체 그대로(is) - int(amount) · str(account) 로 바꿔 넘기는 판이 빠지지 않게 (독립 검토).
    🔴 transfer 의 반환값은 묻지 않는다 - 주장 밖이다.

    decoy 는 transfer 가 키를 시도 밖에서 한 번 만들고 람다가 그 이름을 닫아 쥔다.
    twin 은 람다가 부를 때마다 uuid4 를 새로 만든다.
    """
    seen_keys: set[str] = set()

    def keep(key: str) -> bool:
        if key in seen_keys:
            return True
        seen_keys.add(key)
        return False

    for length in range(1, 5):
        for plan in itertools.product(_OUTCOMES, repeat=length):
            for _ in range(2):  # 같은 계좌 · 같은 금액으로 두 번
                server = _Server(plan)
                raised = _run(mod, server, "acct-1", 100)
                calls = server.calls
                if len(calls) != _expected_calls(plan) or len(set(calls)) != 1:
                    return True
                account, amount, key = calls[0]
                if (account, amount) != ("acct-1", 100) or len(server.applied) > 1:
                    return True
                if server.errors and raised is not server.errors[-1]:
                    return True
                if keep(key):
                    return True
    # 타임아웃의 하위 클래스도 다시 부르고, 타임아웃이 아닌 예외는 그 자리에서 그 객체를 올린다
    for plan in (("sub", "ok"), ("sub", "sub", "sub")):
        server = _Server(plan)
        _run(mod, server, "acct-1", 100)
        if len(server.calls) != _expected_calls(plan) or keep(server.calls[0][2]):
            return True
    for fatal in _NOT_TIMEOUTS:
        server = _Server(("lost", "fail"), fatal)
        raised = _run(mod, server, "acct-1", 100)
        if len(server.calls) != 2 or raised is not server.errors[-1] or keep(server.calls[0][2]):
            return True
    # 계좌 · 금액은 받은 값 그대로 - 모든 시도에서
    accounts = ("acct-1", "  Acct-1 ", "ACCT-2", "김계좌", "", _Acct("acct-1"))
    for account, amount in itertools.product(accounts, (100, 0, -5, True, _Amount.TEN, 10**30)):
        server = _Server(("lost", "drop", "ok"))
        _run(mod, server, account, amount)
        if any(a is not account or m is not amount for a, m, _ in server.calls):
            return True
        if len({k for _, _, k in server.calls}) != 1 or keep(server.calls[0][2]):
            return True
    # 키는 다른 프로세스 · 더 많은 호출과도 겹치지 않는다
    for module in (mod, _again(mod)):
        for _ in range(800):
            server = _Server(("ok",))
            _run(module, server, "acct-9", 1)
            if len(server.calls) != 1 or keep(server.calls[0][2]):
                return True
    far = _keys_from_processes(mod)
    if far is None or len(set(far)) != len(far) or any(key in seen_keys for key in far):
        return True
    every = [*seen_keys, *far]
    alphabet = set().union(*every)
    return max(map(len, every)) * math.log2(max(len(alphabet), 2)) < _KEY_BITS
