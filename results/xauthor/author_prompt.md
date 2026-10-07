# 코드 리뷰 벤치마크의 문항 쓰기

이 문서는 코드 리뷰 벤치마크에 넣을 문항 하나를 쓰는 법이다. 문항은 쌍이다 — 결함처럼 보이지만 증명 가능하게 안전한
코드(`decoy.py`)와, 가드만 지우거나 우회해 결함이 실제로 있는 짝(`twin.py`). 리뷰어가 decoy 에서 결함을 짚으면 거짓 경보로,
twin 에서 짚으면 탐지로 채점된다. 그래서 안전 주장이 거짓인 쌍은 맞는 지적을 오답으로 만든다.

## 1. 쌍의 규격

아래 세 절은 이 벤치마크의 작업 규칙에서 그대로 옮겼다. 그 안에서 가리키는 DESIGN 절과 `tests/` 파일은 상자에 없다 —
상자에서 쓰는 명령은 6절에 있다.

### G3. decoy 규격

```bash
uv run codeproof decoy new D00X-짧은-설명
uv run codeproof decoy validate          # 훅 · 테스트는 --strict (경고도 센다)
```

디렉터리 하나가 한 건 — `meta.toml` + `decoy.py`(안전) + `twin.py`(가드만 제거/우회).

**🔴 V4 가 가장 중요하다: 가드는 `decoy.py` 안에서 보여야 한다.**
모델 API 비교에는 툴도 파일 접근도 없다. 가드가 다른 모듈에 있으면 리뷰어가 알 방법이
없고, 그건 decoy 가 아니라 **알아맞히기 문제**다.

| 규칙 | 내용 |
|---|---|
| V2 | 두 파일이 유효한 파이썬 |
| V3 | 안전 근거가 **기전**을 설명 (60자+ · 낱말 8개+ · 인과 연결어) |
| **V4** | **가드가 `decoy.py` 안에서 보임** + `guard_symbol` 실존 |
| V5·V6 | twin 이 다르되 차이가 12줄 이하 (양쪽 합산) |
| V7 | `meta.toml` 의 식별자가 디렉터리명과 같다 |
| **V9** | **변경이 가드 구간 또는 `guard_symbol` 참조를 건드림** (제거 또는 우회) |
| V10 | 미끼가 파일 범위 안 |
| W2 | 시그니처 차이 — 의도적이면 `acknowledged_warnings` |
| V11 | 쓰이지 않는 수용 표기 |
| V12 | `proof.py` 존재와 `attack(mod)` 서명 (G3a1) |
| **V13** | **`guard_lines` 가 `guard_symbol` 과 실제로 관계된 자리** — 정의든 사용부든 |
| **V14** | **쌍의 파일(meta · decoy · twin · proof · mutants)에 원문 보이지 않는 문자가 없다** — 제어 · 서식 · 줄 구분자 · 비문자. 문자열 안이면 이스케이프로 쓴다 |

🔴 V13 이 있는 이유: V4 는 「구간이 파일 안인가」와 「심볼이 파일에 있는가」를
**따로** 본다. 둘 다 통과하면서 서로 다른 곳을 가리킬 수 있다.
가드가 심볼의 **정의**일 수도 **호출부**일 수도 있으므로 둘 다 허용한다 —
정의만 허용했다가 정당한 쌍 둘을 잘못 잡았다.

`acknowledged_warnings` 는 **최상위**에 쓴다 (테이블 헤더 뒤면 그 테이블로 들어간다).
**ERROR 는 수용 대상이 아니다** — 수용 가능하면 애초에 ERROR 가 아니어야 한다.

### G3a. 🔴 검증기는 근거가 **참인지** 검사하지 못한다

V3 은 근거의 **형식**(길이 · 낱말 수 · 인과 연결어)만 본다. 내용이 맞는지는 못 본다 —
형식 규칙을 전부 통과한 쌍의 안전 주장이 거짓이었던 적이 있다 (DESIGN §7.7).

**안전 주장이 거짓인 decoy 는 없는 것보다 나쁘다** — 맞는 지적을 FP 로 채점한다.

→ 그래서 **근거를 실행 가능하게 만든다** — G3a1.

### G3a1. 🔴 쌍마다 `proof.py` — 반증을 코드로 쓴다

```python
# corpus/decoys/DNNN-*/proof.py
def attack(mod: ModuleType) -> bool:   # 결함이 실현되면 True
    ...
```

계약은 두 줄이고, **두 번째가 핵심**이다:

```
attack(decoy) is False   # 안전 근거가 참이다
attack(twin)  is True    # 🔴 공격이 실제로 결함을 잡을 수 있다
```

두 번째가 없으면 `return False` 만 적어도 통과한다 — **공격의 능력을 twin 으로
증명**한다. 형식 규칙이 놓친 거짓 주장을 이것이 잡는다
(`tests/corpus/test_proofs.py::TestItCatchesTheBugThatSlippedThrough`).

🔴 **면제 목록을 두지 않는다** — 「실행으로 확인 못 한다」는 면제 사유가 전부 틀린 것으로 드러났다
(DESIGN §7.7a). **「너무 어렵다」가 조용히 「검증 안 됨」이 되는 자리**다. 공격을 못 쓰면 그 decoy 는 싣지 않는다.

| 층 | 무엇을 보는가 | 어디서 |
|---|---|---|
| V2~V11 | 형식 — 근거 길이 · 가드 가시성 · 짝 구조 | `decoy validate` (훅 · 테스트가 강제) |
| **V12** | **proof.py 존재와 서명** | `decoy validate` |
| **V13** | **`guard_lines` 가 `guard_symbol` 과 관계된 자리인가** | `decoy validate` |
| **V14** | **원문 보이지 않는 문자가 없는가** (줄은 `\n` 으로만 센다) | `decoy validate` |
| **반증 실행** | **근거가 참인가** | `pytest tests/corpus/test_proofs.py` |
| AST 구조 증명 | 「경로가 **없다**」류 주장 | `tests/corpus/test_safety_claims.py` |

마지막 층이 따로 있는 이유: **실행은 부재를 보일 수 없고 AST 는 보일 수 있다.**
「외부 입력이 이 sink 에 닿는 경로가 없다」는 돌려서 증명하지 못한다.

⚠ 그래도 증명이 아니라 **반증 시도**다. 공격이 약하면 통과한다.
  → 경쟁은 `race_window()` 로 창을 벌린다 — 창이 열린 동안 스레드 전환 간격도 낮춘다. 호출이 없는 읽기와 쓰기
    사이에서는 CPython 이 전환을 검사하지 않아, 그것 없이는 경쟁이 드러나지 않았다 (DESIGN §7.7a). 그래도 확률적이다.
  → 비결정적 공격은 `ATTEMPTS = N` 을 선언해 **양쪽 다** N회 시도한다.
    decoy 는 한 번이라도 깨지면 실패이므로 **완화가 아니라 강화**다.
    **flaky 한 관문은 느린 관문보다 나쁘다** — 사람이 재실행으로 넘기기 시작한다.
  → 하네스는 모듈에 assert · `__debug__` 가 있으면 `python -O` 로 읽은 판도 친다 (`corpus/proof.py`) —
    기본 실행에서는 AssertionError 도 거절이라 가드를 assert 로 바꾼 약화가 통과한다 (DESIGN 교훈 #62).
  → 쌍을 쓸 때는 축을 주장 문장에서 뽑는다 — 절 · 양화마다(어떤 시작 상태 · 크기 · 원본 · 변경 수단이든) 탐침과
    그 칸으로만 잡히는 변이, 주장이 정하지 않은 것(예외 타입 · 컨테이너 · import 꼴)을 바꾼 안전한 변형을 먼저
    적는다. 안전한 변형은 주장 오라클로 먼저 확인한다. 지난 검토가 찾은 종류 목록은 그 표의 빠진 칸을 찾는
    대조용이다 — 종류만 쌓아서는 같은 구멍이 다른 모양으로 다시 난다 (DESIGN §3.5 「쓰는 단계에서 먼저 치는 것」).
  → 변이는 쌍의 `mutants.py` 에 싣는다 — WEAKENED · SAFE 는 `tests/corpus/test_mutants.py` 가 돌리고, 경쟁에 기대는
    RACY 는 `codeproof decoy mutants` 가 30번씩 잰다. scratch 에만 둔 변이로 낸 숫자는 다시 돌릴 수 없다.
  → 위협 모델(무엇이 안이고 무엇이 의도적 우회인가)은 DESIGN §3.5 한 곳에 있다 — 검토 · 교차 검토 프롬프트에
    위협 모델과 주장 밖 결함 목록을 그대로 넣는다. 손으로 줄인 요약은 위협 모델과 어긋나 덮는 범위 안의 결함을 거른다.
  → 쓴 문맥과 다른 에이전트의 쓰는 단계 점검은 독립 검토를 대신하지 않는다 (DESIGN §3.5 라운드 기록).

## 2. 위협 모델 — 안전 주장이 말하지 않는 것

쓰기 · 증명 · 감사가 같은 목록을 쓴다. 「밖」에 기대는 공격으로 주장이 깨지는 것은 주장 위반으로 치지 않는다.

- 안: 선언 타입의 모든 값 — 평범한 하위 타입을 포함한다 (표준 라이브러리 하위 타입인 bool · IntEnum · datetime,
  메서드를 재정의하지 않은 사용자 하위 클래스 — `(str, Enum)` 혼합형처럼 표준 라이브러리가 끼운 메서드는 재정의로
  치지 않는다). 극단적인 유한 수 · 빈 값 · 범위 끝 같은 경계 값. 동기 예외. 주장이 동시 호출을 말하면 스레드의
  모든 인터리빙.
- 밖: 의도적 우회 — monkeypatch · 비공개 속성 직접 변경 · `object.__setattr__` 이나 `__init__` 다시 부르기로 frozen
  우회 · 데이터 모델 계약 (동등 · 해시 · 문자열 변환)을 어기거나 소멸자 · 메서드에서 모듈을 다시 부르는 하위 클래스. 선언 타입 밖의 값. 임의 바이트코드 사이에 떨어지는 비동기 예외. 자원 고갈 (메모리 · 파일 디스크립터).

## 3. 덫의 종류 (`trap_kind`)

- `bounded_input` — 무제한 할당처럼 보이지만 상류가 상한을 강제한다.
- `caller_held_lock` — 호출부가 락을 쥐고 있어 경쟁이 불가능하다.
- `constant_only_sink` — 위험 API 지만 외부 입력이 전혀 닿지 않는다 (NT4).
- `contract_half_open` — 계약상 반열린 구간이라 off-by-one 처럼 보이는 쪽이 맞다.
- `defensive_copy` — 제자리 변형처럼 보이지만 경계에서 복사본을 받는다.
- `enclosing_context` — 바깥 스코프의 context manager 가 자원을 보장한다.
- `exception_absorbed` — 광범위 except 가 정리 경로에만 있어 삼키는 것이 정확한 동작이다.
- `frozen_after_init` — 가변 전역처럼 보이지만 초기화 후 불변이 강제된다.
- `idempotent_retry` — 재시도가 멱등이라 중복 실행이 무해하다.
- `misleading_name` — unsafe_/raw_ 접두사지만 실제로는 검증된 값 (NT1·NT2).
- `noop_shim_neighbor` — 진짜 sanitize 옆에 no-op shim 이 있어 혼동을 유발 (NT5·NT6).
- `type_narrowed` — 타입이 이미 좁혀져 분기가 불필요하다.
- `unreachable_branch` — 도달 불가능한 분기라 결함이 실현되지 않는다.
- `upstream_validation` — 상류에서 이미 전수 검증됨. 아래 접근이 무방비로 보인다.

## 4. 위치가 고정된 종류

관문은 decoy.py 에서 가드 위치(local · caller · callee · module)를 도출해 분류마다 허용한 칸 안인지 본다.
칸 밖이면 관문 출력이 허용한 칸을 알려 준다. 아래는 설계 문서의 해당 행을 그대로 옮긴 것이다.

정의가 위치를 정한다 — `caller_held_lock` caller (「호출부가 락을 쥔다」) · `noop_shim_neighbor` callee (`GuardShape.CALLEE` 의 정의 「이름이 비슷한 이웃을 구별해야 한다」와 같다) · `frozen_after_init` module (전역의 불변 강제는 함수 밖이다). `enclosing_context` 는 caller · callee — 콜백형 트랜잭션(`run_in_transaction(lambda tx: …)`)이면 callee 다 [추정: 정의에서 판정했고 아직 써 보지 않았다]

## 5. 단서 규칙

리뷰어는 기전 문장을 지운 판을 본다. 그 판에서도 코드만으로 판단해야 하므로 설명이 새지 않게 쓴다.

- 모듈 docstring 은 한국어 한 줄 「목적 - 기전」이다. 측정용 판은 그 줄을 「목적.」으로 바꾸고 줄 수는 그대로 둔다.
  twin 의 모듈 docstring 은 decoy 의 것을 그대로 둔다.
- 산문 주석을 쓰지 않는다 — `# noqa` · `# type:` 같은 도구 지시만 쓴다.
- 함수 · 클래스 docstring 은 `guard_lines` 가 그것을 가리킬 때만 쓴다 (계약이 가드인 경우).
- twin 은 decoy 에 없는 docstring 을 더하지 않는다.

## 6. 상자에서 쓰는 법

- 작업 디렉터리가 상자다. 쌍은 `corpus/` 아래에 쓴다 — 거기 있는 `_TEMPLATE` 에서 시작한다:
  `codeproof decoy new <쌍 식별자>-<짧은-설명> --corpus corpus`
- 형식 검사: `codeproof decoy validate --corpus corpus --strict`
- 관문: `codeproof decoy gate <쌍 식별자> --corpus corpus` — 세션이 끝나면 하네스가 같은 명령(경쟁 약화는 30번)으로
  판정한다. 쓰는 동안은 `--race-runs 1` 로 빨리 돌려 볼 수 있다.
- 상자 밖은 읽을 수도 쓸 수도 없고 네트워크도 없다. `python3` 와 `codeproof` 는 준비돼 있다.
- 세션은 30분에서 끊긴다.
- 끝나면 마지막 답으로 쓴 쌍의 폴더 이름 한 줄만 쓴다.
