"""실행 가능한 안전 근거 - 서면 주장을 **반증 시도**로 바꾼다.

🔴 이게 왜 필요한가.

decoy 검증기(`decoy.py`)는 **형식**만 본다 - 근거가 있는지, 가드 심볼이
실재하는지, 짝이 가드만 다른지. 근거가 **참인지**는 못 본다.

실제로 당했다. D015 의 가드로 `threading.Semaphore(4)` 를 썼다. 세마포어 4는
스레드 4개를 동시에 들여보내므로 경쟁이 **실재했다** - 「증명된 음성」이라고
라벨링한 코드가 사실 결함이 있었다. 11개 검증 규칙을 전부 통과했다.

증명된 음성의 라벨이 틀리면 이 프로젝트의 헤드라인(채점 기준 편차)이 통째로
무의미해진다. 우리가 다른 벤치마크를 비판하는 바로 그 지점이다.

## 계약

각 decoy 디렉터리에 `proof.py` 를 두고 `attack(mod) -> bool` 을 노출한다.
결함을 **실현하려 시도**하고, 실현되면 True 를 돌려준다.

    attack(decoy) is False   # 안전 근거가 참이다
    attack(twin)  is True    # 🔴 공격이 실제로 결함을 잡을 수 있다

두 번째 줄이 핵심이다. 이게 없으면 `return False` 만 적어도 통과한다 -
**공격의 능력을 twin 으로 증명**한다. Juliet 의 goodG2B/goodB2G 구조를
코드가 아니라 **증명 자체**에 적용한 것이다.

D015 로 검산: 세마포어 4에서는 스레드가 4개 들어가 경쟁이 일어나므로
`attack(decoy)` 가 True 가 되어 **첫 줄에서 걸린다**.

## 한계 (정직하게)

공격이 약하면 여전히 통과한다. 경쟁처럼 비결정적인 결함은 반복 실행으로
확률을 높일 뿐 증명하지 못한다. 그래서 이건 **반증 시도**지 증명이 아니다 -
`attack` 이 False 인 것은 「아직 못 깼다」이지 「깰 수 없다」가 아니다.
그래도 서면 주장만 있는 것보다는 훨씬 강하다.
"""

from __future__ import annotations

import importlib.util
import sys
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path
    from types import FrameType, ModuleType

    from _typeshed import TraceFunction

PROOF_FILE = "proof.py"
ATTACK = "attack"
ATTEMPTS = "ATTEMPTS"

DEFAULT_ATTEMPTS = 1
MAX_ATTEMPTS = 20
"""🔴 상한을 둔다. 무한정 시도하면 **어떤 공격이든 언젠가는 성공**하고,
그러면 twin 조건이 아무것도 보장하지 않게 된다."""

_RACE_SWITCH_INTERVAL = 1e-6
"""race_window 가 창을 여는 동안의 스레드 전환 간격(초).

기본 5ms 로는 한 줄 안의 호출 경계에서 전환이 드물다."""


class Attack(Protocol):
    """결함을 실현하려는 시도."""

    def __call__(self, mod: ModuleType) -> bool:
        """실현되면 True. 예외를 삼키지 않는다 - 터지면 그건 결함의 증거다."""
        ...


class ProofError(RuntimeError):
    """증명 자체가 깨졌다 - decoy 가 틀렸다는 뜻이 아니라 증명을 못 돌렸다는 뜻."""


@dataclass(frozen=True, slots=True)
class ProofResult:
    """한 쌍에 대한 반증 시도 결과."""

    decoy_id: str
    broke_decoy: bool
    """🔴 True 면 「증명된 음성」 라벨이 거짓이다."""

    broke_twin: bool
    """False 면 공격이 무능하다 - 결함을 못 잡는 공격은 증거가 아니다."""

    attempts: int = 1
    """각 쪽에 시도한 횟수. 비결정적 공격(경쟁·난수)은 여러 번 시도한다."""

    @property
    def ok(self) -> bool:
        return not self.broke_decoy and self.broke_twin

    @property
    def failure(self) -> str | None:
        if self.broke_decoy:
            return (
                f"{self.decoy_id}: 공격이 decoy 를 깼다 - "
                "「증명된 음성」 라벨이 거짓이다. 안전 근거를 다시 보라."
            )
        if not self.broke_twin:
            return (
                f"{self.decoy_id}: 공격이 twin 도 못 깼다 - "
                "결함을 못 잡는 공격은 decoy 의 안전을 증명하지 못한다."
            )
        return None


def load_module(path: Path, alias: str) -> ModuleType:
    """파일 하나를 모듈로 읽는다.

    같은 basename(decoy.py · twin.py)이 19쌍에 반복되므로 alias 로 구분한다 -
    안 그러면 sys.modules 가 첫 번째 것을 재사용해 **전부 같은 코드를 시험**한다.
    """
    spec = importlib.util.spec_from_file_location(alias, path)
    if spec is None or spec.loader is None:
        msg = f"{path} 를 모듈로 읽을 수 없다"
        raise ProofError(msg)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:  # 어떤 예외든 증명 실패로 보고한다
        msg = f"{path} 를 import 하다 터졌다: {exc!r}"
        raise ProofError(msg) from exc
    return mod


def load_attack(pair_dir: Path) -> tuple[Attack, int]:
    """decoy 디렉터리의 `proof.py` 에서 `attack` 과 선언한 시도 횟수(없으면 1회)를 꺼낸다."""
    path = pair_dir / PROOF_FILE
    if not path.is_file():
        msg = f"{pair_dir.name}: {PROOF_FILE} 이 없다 - 실행 가능한 안전 근거가 필수다"
        raise ProofError(msg)
    mod = load_module(path, f"_proof_{pair_dir.name.replace('-', '_')}")
    fn = getattr(mod, ATTACK, None)
    if not callable(fn):
        msg = f"{pair_dir.name}/{PROOF_FILE}: `{ATTACK}(mod) -> bool` 이 없다"
        raise ProofError(msg)
    raw = getattr(mod, ATTEMPTS, DEFAULT_ATTEMPTS)
    if not isinstance(raw, int) or raw < 1:
        msg = f"{pair_dir.name}: {ATTEMPTS} 는 1 이상의 정수다 (지금 {raw!r})"
        raise ProofError(msg)
    return fn, min(raw, MAX_ATTEMPTS)


def run_proof(pair_dir: Path) -> ProofResult:
    """한 쌍에 반증을 시도한다.

    🔴 decoy 를 먼저 친다. twin 이 먼저 터지면 그 예외가 decoy 결과를 가릴 수 있다.

    ## 비결정적 공격은 여러 번 시도한다

    경쟁이나 난수에 기대는 공격은 한 번에 재현되지 않을 수 있다.
    [실측] D042 의 경쟁 공격이 단독 실행에서는 5/5 통과했는데 전체 테스트
    부하에서 twin 을 못 깨 **flaky** 했다. flaky 한 관문은 느린 관문보다 나쁘다 -
    사람이 재실행으로 넘기기 시작한다.

    반증은 애초에 **시도**이므로 여러 번 시도하는 것이 정의에 맞는다.
    `proof.py` 가 `ATTEMPTS = N` 을 선언하면 양쪽 모두 최대 N회 시도한다:

      · decoy - **한 번이라도** 깨지면 라벨이 거짓이다 (시도가 늘수록 엄격해진다)
      · twin  - **한 번이라도** 깨지면 공격이 유능하다 (시도가 늘수록 덜 flaky)

    🔴 두 방향이 같은 부등호를 쓴다는 점이 중요하다. 시도를 늘려도 decoy 쪽이
       느슨해지지 않으므로 **완화가 아니라 강화**다. 상한은 MAX_ATTEMPTS 다.
    """
    attack, attempts = load_attack(pair_dir)
    name = pair_dir.name.replace("-", "_")
    broke_decoy = _any_attempt(
        attack, pair_dir / "decoy.py", f"_decoy_{name}", attempts
    )
    broke_twin = _any_attempt(attack, pair_dir / "twin.py", f"_twin_{name}", attempts)
    return ProofResult(
        decoy_id=pair_dir.name,
        broke_decoy=broke_decoy,
        broke_twin=broke_twin,
        attempts=attempts,
    )


def _any_attempt(attack: Attack, path: Path, alias: str, attempts: int) -> bool:
    """최대 attempts 회 시도해 한 번이라도 깨지면 True. 깨지면 즉시 멈춘다."""
    return any(
        _attempt(attack, path, f"{alias}_{i}") for i in range(attempts)
    )


@contextmanager
def race_window(*func_names: str) -> Iterator[None]:
    """지정한 함수 안에서 **줄마다 스레드 전환 기회**를 만든다.

    🔴 왜 필요한가. 경쟁 결함은 CPython 에서 그냥은 재현되지 않는다.
       [실측] `_counter["value"] = _counter["value"] + 1` 를 스레드 16개 x
       5000회 돌려도 손실이 **0건**이었다. `sys.setswitchinterval` 을
       1e-7 까지 낮춰도 마찬가지다 - 전환 검사 지점이 그 사이에 없다.

       줄 단위 추적을 걸고 `time.sleep(0)` 로 양보하면 창이 벌어진다.
       [실측] 같은 코드에서 8 x 200 중 **1078건 손실**.

    이건 의미를 바꾸지 않는다 - **스케줄링만** 건드린다. 원래 가능했던
    인터리빙을 확률적으로 드러낼 뿐이다. 그래서 「경쟁이 없다」는 주장을
    반증하는 도구로 정당하다.

    ⚠ 그래도 비결정적이다. 실패하지 않았다고 경쟁이 없는 것은 아니다.

    🔴 **줄 단위 창은 줄과 줄 사이에만 열린다.** read-modify-write 가 한 줄이면
       (`d["k"] = d["k"] + v`) 그 안에 추적 지점이 없어 재현되지 않는다.
       [실측] D051 을 한 줄로 썼을 때 twin 이 5회 시도 전부 통과했고,
       두 줄(`current = d["k"]` / `d["k"] = current + v`)로 나누자 바로 깨졌다.
       경쟁 decoy 를 쓸 때는 read 와 write 를 **다른 줄에** 둔다 -
       실제 코드에서도 그 모양이 더 흔하다.

    🔴 **그래서 창이 열린 동안 전환 간격도 낮춘다.** 위의 「1e-7 로도 안 된다」는 줄 안에
       호출이 없을 때만 맞는다 - 줄 안에 호출이 있으면 그 호출 경계에서 전환되므로, 읽기와
       쓰기 사이에 호출이 낀 한 줄(`append(task := waiting.pop(0))`)이나 창 목록 밖 이름의
       도우미로 옮긴 줄은 줄 단위 창만으로는 드러나지 않는다 (4라운드 검토가 찾았다 ·
       DESIGN §3.5). 전환 간격도 스케줄링만 바꾼다.
    """
    wanted = frozenset(func_names)

    def tracer(frame: FrameType, event: str, _arg: object) -> TraceFunction:
        if event == "line" and frame.f_code.co_name in wanted:
            time.sleep(0)  # 다른 스레드에 양보한다 - 창을 벌린다
        return tracer

    saved_interval = sys.getswitchinterval()
    sys.setswitchinterval(_RACE_SWITCH_INTERVAL)
    threading.settrace(tracer)
    sys.settrace(tracer)
    try:
        yield
    finally:
        sys.settrace(None)
        threading.settrace(None)
        sys.setswitchinterval(saved_interval)


def _attempt(attack: Attack, path: Path, alias: str) -> bool:
    """공격 1회. 예외는 **결함이 실현된 것**으로 센다.

    IndexError · KeyError · AssertionError 는 전부 「깨졌다」의 표현이다.
    공격 코드가 삼키면 그 구분이 사라지므로 여기서 잡는다.
    """
    mod = load_module(path, alias)
    try:
        return bool(attack(mod))
    except Exception:  # 터진 것도 결함 실현이다
        return True
