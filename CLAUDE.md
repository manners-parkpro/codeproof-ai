# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **이 문서는 「무엇을 지켜야 하는가」만 담는다.** 「왜 그런가」는 [docs/DESIGN.md](docs/DESIGN.md),
> 「무엇을 만드는가」는 [README.md](README.md). 근거가 필요하면 DESIGN 의 해당 절을 읽는다.
>
> 🔴 는 **어기면 발표하는 숫자가 틀리는 것**에만 붙는다 — 유지보수 문제가 아니라
> 측정 오류를 만드는 것. 나머지도 규칙이지만 결과를 무효화하지는 않는다.

---

## 명령어

```bash
uv sync
uv run pytest                    # 전체
uv run pytest path::test_name    # 단일
uv run ruff check --fix .
uv run mypy                      # files 설정은 pyproject 에

uv run codeproof doctor          # 자격증명·도구 준비 상태
uv run codeproof measure         # 정적분석기로 채점 기준 편차 측정 (API 불필요)
uv run codeproof history         # 저장된 실행 · 재현성 확인
uv run codeproof report          # docs/MEASUREMENTS.md · docs/figures/*.svg 생성 (--check 로 최신 확인)
uv run codeproof pack --from <실행기 출력> --out results/agent/<이름> [--runs N]  # 에이전트 묶음 (N = 수집 전에 선언한 회차 수)
uv run codeproof decoy validate  # decoy 규격 검사
uv run codeproof decoy new <id>  # 템플릿에서 새 decoy
uv run codeproof decoy mutants [D104 ...]  # 쌍의 mutants.py 로 증명을 다시 깬다 (경쟁 변이는 30번)
```

**코퍼스 마이닝 환경은 v2 에 별도 프로젝트로 둔다 — 지금은 없다** (DESIGN §6.8). 본 패키지의 `>=3.14` 와
벤치마크 툴체인이 충돌하기 때문이다. 그때도 **uv workspace 로 묶지 마라** — resolution 이 통합되어 같은 충돌이 살아난다.

---

## A. 구조

### A1. 레이어 의존 그래프

```
domain    → (없음)              analysis  → domain
llm       → domain              verify    → domain          ← eval 이 없다
corpus    → domain              reviewers → domain·analysis·llm
eval      → domain·analysis·llm·verify·corpus·reviewers
store     → domain·eval         cli       → 전부
```

`domain/` 은 **stdlib 과 `typing` 만** import 한다.

정답 라벨(`Defect`·`LabeledSample`·`Stratum`)은 `eval/` 안에만 있다. 런타임
(`analysis`·`llm`·`verify`)은 `eval` 을 import 할 수 없으므로 **라벨을 볼 방법이 없다.**
타입 이름을 금지 목록으로 관리하지 않는다 — 새 라벨 타입이 생겨도 자동으로 막힌다.

검사: `tests/architecture/test_layering.py`. 새 레이어는 `ALLOWED` 에 의존 규칙을 명시한다.

> 새 타입을 어디 둘지 모르겠으면 `domain` 에 둘 수 있는지 본다.
> 못 두는 이유가 곧 그 타입이 속할 레이어다.

### A2. 리뷰어는 하나의 개념이다

지적을 내는 것은 전부 `Reviewer` 다 — 정적분석기 · 모델 API · 에이전트 ·
가져온 지적(SARIF) · 사람. **같은 하네스(`run_reviewer`)로 돌고 같은 채점을 받는다.**

🔴 다만 `ReviewerKind` 가 다르면 **섞어 집계하지 않는다.** 에이전트는 파일 탐색·
다회 턴·툴 사용이 가능해서 `model_api` 와 조건이 다르다 — F3 과 같은 원칙이다.

`kind.is_deterministic` 인 리뷰어에 `sample_n>1` 을 주면 **거부한다.**
같은 결과를 N번 세면 출현 빈도가 의미를 잃는다.

**새 리뷰어를 추가할 때 자격증명이 필요한지 먼저 본다** — SARIF 를 내는 도구면
`ImportedReviewer` 로 끝난다. 새 어댑터를 쓰지 않는다.

### A2a. 매칭 정밀도는 도구 의존적이다 🔴

같은 결함을 도구마다 다른 줄로 보고한다 — 대표 줄로만 맞추면 **리뷰 품질 차이가 아니라 보고 관례 차이**가
TP 와 FP 를 가른다 (DESIGN §7.9).

→ 단일 slack 값으로 낸 숫자를 결론으로 쓰지 않는다. `sensitivity.sweep()` 으로
  스윕해 **흔들리는지**를 같이 낸다. 흔들리면 그 결론은 매칭 정책의 산물이다.

→ 스윕은 **채점만 다시 한다.** 리뷰어를 다시 돌리면 slack 효과와 실행 변동이 섞인다.

→ 사다리는 `(0,2,5,10)` 이다 — 좁으면 전이점을 놓쳐 거짓 「안정」이 나온다
  [실측 · 60쌍 · ruff S,B,F,SIM]. 다회 실행이면 관점마다 낸다(`sweep_views()`) —
  `sweep()` 은 합집합으로 센다 (F6).

→ 위치는 지적의 **보고 범위**로 맞춘다 (`Span.overlaps`) — 시작 줄만 보지 않는다.
  claude 는 `def` 줄부터 범위를 잡아, 시작 줄 기준이면 claude/codex 순위가 뒤집혔다 (DESIGN §7.10a).
  채점자 · 미끼 통계 · 확인자가 **전부 같은 함수**를 쓴다 — 한 곳만 다르면
  같은 지적이 곳마다 다른 자리에 있다.
  🔴 파서도 범위를 버리지 않는다 — SARIF `endLine`·`endColumn`, bandit `line_range` (DESIGN §7.9 · B1).

### A2b. 에이전트 층은 격리 · 고정 · 기록해서 잰다 🔴

`export` → `scripts/review-with-agent.sh` → `import --kind agent`. 근거는 DESIGN §7.10 — 첫 전체 실행이
네 군데서 조용히 틀려 있었다.

- `--effort` 없이 돌리지 않는다 (D4). 모델은 **시작 때 한 번** 해석해 고정하고 `RUN.json` 에 적는다.
- CLI 를 호스트 설정에서 격리한다 — claude `--safe-mode`, codex `--ignore-user-config` 등 (플래그 전체는 실행기 머리말).
  `--bare` 는 OAuth 를 읽지 않아 구독 로그인에서는 실패한다.
- 출력 규격을 손으로 적지 않는다 — `review_schema()` 에서 뽑고 같은 스키마를 CLI 에 강제한다.
- `import` 는 `RUN.json` 을 정본으로 읽는다. 손으로 준 identity 가 다르면 거부한다.
  실행을 가르는 항목은 전부 설정 지문(`_SIGNED`)에 싣는다 — 빠지면 다른 실행이 같은 설정으로 읽힌다 (DESIGN 교훈 #40).
- LLM 지적에도 둘러싼 함수를 붙인다 — `run_reviewer` 한 곳에서 (E00). 없으면 짝 채점의
  「같은 지적」이 `(category, None)` 이 되어 파일 안 같은 category 가 전부 같은 지적이 된다.
- 크레딧이 한정인 실행은 `--runs` 를 **1씩** 올려 이어 돈다 — 실행기가 샘플마다 N회를 다 돌고 넘어가서,
  `--runs 8` 을 바로 주면 충전분이 몇 샘플에 몰리고 나머지는 채점 밖이 된다 (F6). 근거 수치는 실행기 머리말.
- 🔴 **돌고 있는 실행기를 제자리에서 고치지 않는다.** bash 는 스크립트를 실행하면서
  읽고, `agent_output.py` 는 호출마다 다시 읽힌다. 새 파일에 쓰고 `mv` 로 바꾼다.

### A3. 확장점 — registry 가 맞는 자리와 아닌 자리

| Protocol | registry | 새 구현 |
|---|---|---|
| `Analyzer` | `analysis/registry.py` | 클래스 추가 + `ANALYZERS` 한 줄 |
| `ReviewProvider` | `llm/registry.py` | 클래스 추가 + `PROVIDERS`·`CREDENTIAL_OF` |
| `FindingFormat` | `reviewers/formats.py` | 파서 추가 + `FORMATS`. 버린 지적은 `ParseOutcome.rejected` 로 센다 (I) |
| `Reviewer` | — | `reviewers/<name>.py`. **먼저 `ImportedReviewer` 로 되는지 본다** |
| `Verifier` | — | `verify/<rule>.py`. 파이프라인 구성은 호출부 정책 |
| `Grader` | **없음 (의도)** | `eval/grading/<name>.py` |

🔴 **채점자에 registry 를 두지 않는 것은 의도다.** 생성 인자가 균일하지 않다 —
`StaticCorroborationGrader` 만 `reference` 를 받는다. 균일한 팩토리를 억지로 만들면
그 비균일성이 `**kwargs` 딕셔너리로 숨고, 그게 더 나쁘다. CLI 가 정책으로 조립한다.

🔴 **`cli.py` 는 구현 클래스를 직접 생성하지도 import 하지도 않는다.**
문서에만 적힌 이 규칙은 지켜지지 않았다 (DESIGN 교훈 #23) — `tests/architecture/test_registry.py` 가 막는다.

**Java 지원은 `analysis/java/` 추가 + `ANALYZERS` 등록만으로 성립해야 한다.**
`analysis/base.py` 에 Python 전용 개념(`.py` 확장자 · ast 노드 · ruff 룰 코드)이
새면 그 약속이 깨진다.

## B. 데이터 — 조용히 틀리는 지점

### B1. 위치는 내부 단일 규약으로 정규화 🔴

**1-based line + 0-based 문자 column** (`byte_column` 병기).

도구 원본이 전부 다르다 — Ruff(1-based 문자) · mypy JSON(0-based 바이트) ·
mypy 텍스트(1-based 바이트) · ast(0-based 바이트) · SARIF(1-based 문자).
**같은 mypy 실행이 텍스트와 JSON 에서 다른 컬럼을 낸다.**

- 변환은 `analysis/<lang>/<tool>.py` 어댑터 **안에서만**. 어댑터 하나가 변환 하나를 책임진다.
- **비ASCII 회귀 테스트를 지우지 않는다.** 없으면 이 버그는 조용히 산다.
- ⚠ mypy `--native-parser` 가 곧 기본값 → 컬럼 의미 변동 가능. 핀 테스트로 감지한다.

### B2. 지적 식별자에 라인 번호를 쓰지 않는다 🔴

```python
fingerprint = hash(rule_id, path, enclosing_symbol, normalized_snippet)
```

줄 번호를 넣으면 위쪽 줄만 고쳐도 모든 지적이 새 지적이 된다. 경로는 넣는다 — 위쪽 편집에
흔들리지 않고, 다른 파일의 같은 지적을 가른다.
SARIF 는 `partialFingerprints` 에 싣는다 (`fingerprints` 아님).

### B3. `enclosing` 추출

```python
span_start = min(node.lineno, *(d.lineno for d in node.decorator_list))
```

`FunctionDef.lineno` 는 `def` 를 가리키고 데코레이터는 그 앞이다. Ruff 는 데코레이터
줄에 진단을 자주 낸다 — 보정 없으면 전부 `<module>` 로 오분류된다.
중첩 추출에 `ast.walk` 를 쓰지 않는다(중첩 소실). `iter_child_nodes` 재귀로 한다.

### B4. Python 3.14 AST

- `ast.TemplateStr` / `ast.Interpolation` 신규(PEP 750) — 망라적 visitor 는 처리한다.
  안 하면 **조용히 코드를 놓친다.**
- `ast.Num`/`Str`/`Bytes`/`NameConstant`/`Ellipsis` 제거됨 → `ast.Constant`.
- AST 노드를 **생성**하는 코드는 3.15 에서 필드 누락 시 raise.

---

## C. 외부 도구

### C1. 분석기는 모델이 보는 것만 본다 🔴

`Analyzer.analyze(target)` 는 `materialize(target)` 안에서 돈다 —
`target.files` 를 임시 디렉터리에 복원하고 거기서만 분석한다.

실제 레포에 돌리면 분석기가 모델보다 많은 맥락(주변 파일·설정·타입 스텁)을 얻어
같은 과제를 푸는 게 아니게 된다. decoy 의 V4(가드가 보여야 한다)와 같은 불변식이다.

### C1a. 🔴 측정 도구는 호스트 환경에서 격리한다

측정 도구가 실행되는 레포의 설정을 주워오면 **같은 코퍼스가 레포마다 다른 숫자**를 낸다.

| 도구 | 격리 플래그 | 없으면 |
|---|---|---|
| ruff | `--isolated` | 호스트 `pyproject.toml` 의 select·exclude 적용 |
| mypy | `--config-file=/dev/null` | [실측] 이 레포의 `strict = true` 를 주워왔다 |
| mypy | `--no-incremental` `--cache-dir=/dev/null` | [실측] **삭제된 임시 디렉터리 경로**의 진단이 섞여 나왔다 |
| ruff · mypy | 대상 판 (`analysis/python/version.py` 한 곳) | [실측] Ruff 는 3.10 으로 보고 `ExceptionGroup` 에 F821 (D109 FP) · mypy 는 실행한 인터프리터 판을 따르고 기록이 없다 |

🔴 **`config_signature()` 가 거짓을 적지 않게 한다** — 매니페스트가 거짓이면 재현성 설계가 무의미하다 (DESIGN §6.6).

### C1b. 대상이 여럿이면 일괄로 돈다

`Analyzer.analyze_many(targets)` 는 **한 번의 subprocess** 로 전부 분석한다 — 대상마다 띄우면
수백 샘플에서 분 단위가 된다 (DESIGN §6.7).

🔴 **복원 방식이 분석 결과를 바꾸면 안 된다.** `__init__.py` 를 무조건 넣으면
Ruff 의 `INP001` 이 사라져 일괄과 개별이 다른 숫자를 낸다 (DESIGN §6.7). mypy 만 모듈명 해소에
필요하므로 `materialize_many(..., as_packages=True)` 로 **선택적**이다.

테스트가 「일괄 == 개별」을 강제한다 — 속도 최적화가 숫자를 바꾸면 최적화가 아니라 버그다.

### C2. Ruff · mypy 는 subprocess 로만

```bash
ruff check --output-format=json --no-cache --exit-zero    # 대량이면 json-lines
mypy --output=json --show-error-end --show-absolute-path --no-error-summary
```

- **`uv run <tool>` 을 거치지 않는다** — 호출마다 오버헤드가 붙는다 (DESIGN §6.7). `codeproof` 는 이미
  venv 안이라 PATH 에 잡힌다. `analysis/toolchain.py` 의 `resolve()` 를 쓴다.
- **Ruff 는 Python API 가 없다.** `ruff-api` 는 format 전용.
- **mypy `mypy.api.run` 을 쓰지 않는다** — 스트리밍 불가 + 모듈 상태·메모리 누수 +
  `run_dmypy` 스레드 비안전. subprocess 가 격리·타임아웃·크래시 봉쇄를 준다.
- **종료 코드로 판단하지 않는다.** `--exit-zero` + 파싱된 페이로드. `2` 만 "도구가 깨졌다".
- **Ruff 룰 목록 하드코딩 금지** → `ruff rule --all --output-format=json` 으로 introspect.
- ⚠ Ruff 구문 오류는 `code == "invalid-syntax"` — 룰 코드가 아니다.
- ⚠ mypy `note` 는 같은 위치 `error` 에 `hint` 로 접혀 온다. 독립 레코드로 가정하지 않는다.
- Ruff 는 pre-1.0 — 버전을 정확히 핀하고 파서를 스냅샷 테스트한다.

### C3. diff

```bash
git diff --no-color --no-ext-diff --find-renames --unified=0 BASE...HEAD
```

**세 점(`A...B`)** 필수 — merge-base 기준. 두 점은 베이스 드리프트를 가짜 삭제로 보여준다.
**`--find-renames`** 없으면 rename 이 delete+add 가 되어 파일 전체가 touched 로 잡힌다.
`unidiff` 로 파싱한다 (GitPython 은 hunk 파싱 기능이 없다).

### C4. 도달성은 v1 에서 파일 안까지만

파이썬 전용 호출그래프 도구가 전멸했다(PyCG · JarvisCG · Pyre/Pysa 전부 아카이브).
함수 단위(LibCST+jedi 직접 조합)를 v1 에서 시작하지 마라 — 그 레이어를 소유해야 하고,
거기 예산을 태우면 논지를 못 만든다.

---

## D. LLM 호출 — 가장 틀리기 쉬운 곳

### D1. 래퍼 라이브러리를 측정 경로에 넣지 않는다

LiteLLM · LangChain · instructor · PydanticAI 금지. 전부 OpenAI 모양 `usage` 로
정규화하는데 벤더마다 토큰 정의가 다르고, 그 정규화가 손실 지점이다.
관련 이슈들이 미해결로 종료됐다.

→ SDK 위에 얇은 어댑터. `max_retries=0`. **원본 응답을 그대로 영속화.**

### D2. 토큰을 벤더 간에 그냥 더하지 않는다 🔴

```python
# Anthropic — input_tokens 는 마지막 캐시 breakpoint 이후만 센다
total_input = cache_read_input_tokens + cache_creation_input_tokens + input_tokens
# OpenAI — prompt_tokens 는 캐시 포함. 그대로 쓴다
```

토크나이저도 다르다 — Claude 4.7+ 는 같은 텍스트에 약 30% 더 많은 토큰.
**`tiktoken` 을 Claude 에 쓰지 않는다.** 4.6/4.7 경계를 넘어 토큰 수를 재사용하지 않는다.

### D3. 캐싱을 명시적으로 통제한다 🔴

Anthropic 은 **옵트인**, OpenAI 는 **기본 활성화에 해제 수단 없음.**
반복 호출 시 2회차부터 OpenAI 만 적중 → 추론이 아니라 prefill 생략을 재고
OpenAI 비용을 최대 90% 과소 보고한다.

→ 프롬프트 **맨 앞**에 nonce. **prefix 매칭이라 뒤에 붙이면 무효다.**
→ 호출별 캐시 토큰 수를 항상 기록한다.

### D4. effort 를 명시하지 않은 호출을 만들지 않는다 🔴

기본값이 모델마다 다르다. "기본값으로" 비교하면 한쪽에 더 많은 추론 예산을 준다.

### D5. 요청 구성

- **`output_config.format`(Anthropic) / `strict: true`(OpenAI)** 를 쓴다.
- **강제 tool use 금지** — 최신 Claude 에서 400. 래퍼들의 기본 경로가 여기서 죽는다.
- **출력 스키마는 평탄하게(non-recursive)** — Anthropic 미지원, OpenAI 지원. 양쪽을 통과해야 한다.
  `minimum`/`maximum` · `minLength`/`maxLength` · `pattern` · `maxItems` 도 Anthropic 미지원.
- **`temperature`·`top_p` 를 보내지 않는다** — Claude 4.7+ 에서 400.
- **`fallbacks` 를 켜지 않는다** — 거부 시 다른 모델이 대신 답하면 **측정 대상이 바뀐다.**
  `stop_reason: "refusal"` 은 1급 데이터로 기록한다.
- Anthropic SDK 는 스키마를 조용히 재작성한다 → **wire 스키마를 로깅한다**, Pydantic 모델 말고.
- 양 벤더 모두 스키마 문법을 첫 호출에 컴파일·24h 캐시 → 측정 전 워밍업 2–3회 폐기.

### D6. 모델 ID 는 정확히 핀한다

날짜 없는 Claude ID 도 그 자체가 스냅샷이다. OpenAI 는 날짜 스냅샷을 명시한다.
⚠ **모델 목록은 빠르게 바뀐다.** 기억에 의존하지 말고 확인한다 — 이 저장소 작업 중에도
새 모델 출시로 표가 하루 만에 낡은 적이 있다.

---

## E. 검증 — 증거 수집과 판정의 분리

### E00. 🔴 실행 경로는 `run_reviewer` **하나뿐**이다

분석기·모델·에이전트·가져온 지적·사람 리뷰가 **전부 같은 함수**를 탄다.
`run_analyzer` 나 `run_provider` 같은 지름길을 다시 만들지 않는다.

```python
run_reviewer(AnalyzerReviewer(create_analyzer("ruff")), samples, graders)
run_reviewer(ProviderReviewer(p, effort="high"), samples, graders, sample_n=8)
```

경로가 갈리면 새 훅은 반드시 한쪽에서 빠진다 — 러너가 셋이던 때 짝 채점 훅이 빠진 둘이
**조용히 전부 TP 로 채점**했다 (DESIGN §4.1b). `tests/architecture/test_single_runner.py` 가 강제한다.

### E01. 매니페스트 항목은 **리뷰어가 신고**한다

러너는 `effort` 나 도구 버전을 짐작하지 않는다. 모르면 리뷰어에게 묻는다.

```python
def manifest_fields(self) -> dict[str, str]: ...   # effort · cache_policy
def tool_versions(self) -> tuple[ToolVersion, ...]: ...
```

러너가 기본값을 박아 넣으면 모델 실행에 `effort="n/a"` 가 기록된다 —
**숫자는 맞는데 출처가 거짓**인 매니페스트는 재현을 불가능하게 만든다.

### E02. 채점자가 문맥 없이 돌면 **거부한다**

실행 문맥이 필요한 채점자는 미바인딩 상태를 `None` 으로 구분하고
`UnboundGraderError` 를 던진다. 빈 컬렉션으로 초기화하지 않는다 —
빈 짝은 「짝에 지적이 없다」로 읽혀 **기본값이 곧 오답**이 된다.

### E0 · E1. 🔴 `verify/` 와 `eval/` 모두 증거를 **받는다**

검증자든 채점자든 **도구를 직접 돌리지 않는다.** 이미 계산된 지적을 생성자로 받는다.

```python
CorroborationVerifier(reference=ruff_findings)              # verify/
StaticCorroborationGrader(reference=analyzer.analyze_many(targets))  # eval/
```

`verify/ → analysis/` 는 레이어 위반이고, 단위 테스트에 subprocess 가 끌려 들어온다 — 한쪽에만 빠뜨리면
성능도 샌다 (DESIGN 교훈 #21). `Verifier.verify(finding, target)` 는 경로가 아니라 `ReviewTarget` 을 받는다.

### E2. 못 찾은 것을 근거로 REFUTES 하지 않는다

| 상황 | 판정 |
|---|---|
| 가드를 찾음 | `REFUTES` |
| 가드를 못 찾음 | **`INCONCLUSIVE`** — 없다는 뜻이 아니다 |
| 확인자 동의 | `SUPPORTS` |
| 확인자 미동의 | **`INCONCLUSIVE`** — 그 층을 안 볼 수도 있다 |

`INCONCLUSIVE` 는 confidence 를 움직이지 않는다. 깎으면 반박으로 세는 것이다.

### E3. confidence 는 확률이 아니다

라벨 없이 계산했으므로 **모인 근거의 양**일 뿐이다. 가중치는 임의값이고,
임의임을 숨기지 않고 `config_signature()` 로 매니페스트에 싣는다.
하드 게이트 하나 — 인용이 반박되면 0. 가중합이 아니다.

### E4. 검증자가 못 보는 것을 문서에 적는다

적지 않으면 `SUPPORTS` 가 과신으로 읽힌다. 현재 명시된 한계:
`GuardVerifier` 는 **데이터흐름 가드**(오염 추적 필요)를,
`ReachabilityVerifier` 는 **분기 단위 도달성**·파일 밖·동적 호출을 못 본다.

---

## F. 실험

### F1. 매니페스트 없는 결과는 저장되지 않는다 🔴

코드가 아니라 **외래키**가 막는다. 실행 행이 없으면 지적도 판정도 들어가지 못한다.

| 필드 | 포함 | 용도 |
|---|---|---|
| `config_hash` | 설정만 (시각 제외) | 같은 설정끼리 **재현성 비교** |
| `run_id` | 설정 + 시각 | 이 한 번의 실행 |

같은 `config_hash` 결과가 다르면 — 정적분석기는 **도구·환경 드리프트**,
모델은 **정상이고 그 폭이 측정 대상**이다. 리포트가 구분해서 말한다 — 리뷰어가 신고한 종류
(`kind.is_deterministic`)로 고르고 이름으로 짐작하지 않는다. 종류가 없는 저장 기록(`history --repro`)은
한쪽으로 짐작하지 않고 모른다고 말한다.

스키마 버전이 다르면 **조용히 마이그레이션하지 않는다.**

### F2. 측정 손잡이는 전부 매니페스트에 기록

| 손잡이 | 실측 효과 |
|---|---|
| Ruff 룰 선택 | FP 0 → 4 |
| 그룹핑 정책 | 출현율이 달라진다 |
| 채점 범위 여유 | 판정불가 → FP |
| effort | 모델별 기본값이 다르다 |
| 캐시 정책 | OpenAI 비용 90% 과소보고 |
| 프롬프트 | 포맷만으로 최대 76 포인트 |

기록하지 않은 손잡이는 재현 불가이고, 재현 불가는 실험이 아니다.

### F3. 섞지 말아야 할 것 🔴

| 섞으면 | 무슨 일이 | 규칙 |
|---|---|---|
| 층(stratum) 을 풀링 | 유리한 층 뒤에 숨는다 | Recall 은 A·B 각각, FPR 은 C·D 각각 |
| 두 리뷰어 지적을 한 관측에 | 출현 빈도가 **교차모델 합의**가 된다 (조용한 투표) | `MixedReviewerError` |
| 어휘 다른 채점자를 편차에 | 범주 차이가 편차로 둔갑 (0~44 vs 18~44) | `Grader.emits` 로 거른다 |
| 단일실행 기대값과 k-임계 | 다른 숫자다 | 라벨 붙여 구분 보고 |
| 정확도·비용과 지연 | batch 에 요청별 타이밍 필드가 없다 | 지연은 별도 동기·스트리밍 실험 |

### F4. 판정 불가를 FP 로 접지 않는다 🔴

채점자가 판정할 수 없으면 `UNDECIDABLE` 이다. 기존 문헌이 여기서 틀렸다 —
"아무도 코멘트 안 함"(증거의 부재)을 "틀림"으로 채점해 사람이 놓친 버그를 FP 로 만들었다.

`Precision` 분모에서 판정 불가를 빼고, **판정불가율을 같이 보고**한다.

### F5. 짝은 짝으로 채점한다 🔴

지적 단위로만 보면 과잉지적이 보이지 않는다. decoy 에 FP 1건 · twin 에 TP 1건이면
"Precision 50%" 로 읽히는데, 같은 룰·같은 줄이면 탐지가 아니라 패턴 매칭이다.

`score_pairs()` → **P-C**(구별) · **P-V**(과잉) · **P-B**(미탐지) · **P-R**(역전).
🔴 **구별 성공률은 리뷰어의 성질이 아니라 (리뷰어 × 채점자)의 성질이다** — 같은 지적인데 짝 판정이
정의마다 다르다 (README 결과 3). 어느 정의로 잰 것인지 **반드시 같이 적는다.**

🔴 **`score_pairs()` 는 사후 요약이라 Precision 을 고치지 못한다.**
per-finding 으로는 여전히 TP 가 남는다. 채점 단계에서 막으려면
`PairedFixGrader` 를 쓴다 — 「짝에 없는 지적만 탐지로 인정」하는 별도 정의다.
그 채점자는 짝의 지적이 필요하므로 `runner` 가 **리뷰와 채점을 분리**하고
`bind_run()` 으로 실행 전체를 넘긴다.

### F5a. 코퍼스 **구성비**도 손잡이다 🔴

D층 집계 FPR 은 「도구의 오탐률」이 아니라 **「내가 고른 미끼 분류 구성비에서의
오탐률」**이다 — **코드도 도구도 채점자도 그대로 두고 구성비만 바꿔** 집계를 크게 움직일 수 있다
(범위는 생성물 「미끼 분류」 · DESIGN §3.5).

→ `mix_sensitivity()` 를 집계와 같이 낸다. 구성비를 매니페스트에 싣는다.

🔴 **축이 둘이다. 둘 다 잰다.** `TrapKind` 는 「어떤 종류의 논증인가」,
   `GuardShape` 는 「가드를 찾으려면 어디를 봐야 하는가」다 — 직교한다.
   한 축만 고르게 채워도 다른 축이 쏠릴 수 있다.

   `GuardShape` 는 **도출한다** — `meta.toml` 에 적게 하지 않는다.
   손으로 적는 축은 틀리고, 틀려도 아무도 모른다.

🔴 **다만 「범위가 넓다」와 「분류마다 다르다」는 다른 주장이다.**
   앞은 측정 절차에 대한 참인 진술이고, 뒤는 **모집단에 대한 주장**이라
   표본이 필요하다. **decoy 단위 순열 검정**으로 분류 전체를 한 번에 판정한다
   (`heterogeneity_verdict` · `homogeneity_p`). 극단 두 분류의 구간을 견주지 않는다 —
   다중 비교이고, 지적 단위면 decoy 하나의 지적 여럿이 독립 시행으로 셈해진다 (모의실험 · 검정력은 DESIGN §3.5).
   기각하지 못하면 「같다」가 아니라 「모른다」다.

🔴 **그리고 유의해질 때까지 표본을 늘리다 멈추지 않는다 — optional stopping 이다.**
   분류당 목표 쌍 수를 **미리 선언**하고(`TARGET_PAIRS_PER_KIND`), 미달 상태의
   판정에는 도구가 꼬리표를 붙인다.

⚠ 증명된 음성 위에서 `FP/(TP+FP)` 는 **항상 100%** 다 — TP 가 정의상 불가능하다.
  분모는 **나온 지적 전부**여야 「몇이 물렸나」가 된다. 범위 밖(UNDECIDABLE)은
  「이 미끼와 무관한 지적」이라 분모에 남는다. 이건 F4 위반이 아니다 —
  판정 불가를 FP 로 **접는** 것이 아니라 별도 칸으로 세는 것이다.

⚠ 지적은 **독립 시행이 아니다** — decoy 하나가 여러 지적을 낸다. 지적 단위 CI 는
  실제보다 좁으므로 **샘플 단위 비율을 같이** 낸다.

### F5b. 변동하는 측정값을 산문에 베끼지 않는다 🔴

```bash
uv run codeproof report            # docs/MEASUREMENTS.md · docs/figures/*.svg 생성
uv run codeproof report --check    # 낡았으면 exit 1
```

코퍼스가 자랄 때마다 문서 세 곳의 낡은 숫자를 테스트가 잡았다 — **반복은 설계 신호**였다 (커밋 28d7f8c).

- 현재 수치는 **생성물**이 든다. 산문은 안정된 주장만 쓰고 그 파일을 가리킨다.
- 산문에 숫자를 남길 때는 **표본 크기를 붙인다** — `[실측 · 37쌍]`.
  숫자와 표본이 붙어 다니면 **스스로 날짜를 밝히므로** 나중에도 읽힌다.
- 🔴 생성물에 **시각·run_id 를 넣지 않는다.** 넣으면 코퍼스가 그대로여도
  매번 달라져 「최신인가」를 물을 수 없다. 재현 정보는 `config_hash` 로 충분하다.
- 생성물은 손으로 고치지 않는다. 파일 첫 줄이 그렇게 말하고 테스트가 강제한다.

### F4a. 관례 주장을 거짓 경보로 세지 않는다 🔴

안전 근거는 **특정 결함**에 대한 주장이다. 같은 줄에 떨어진 「docstring 이
없다」를 FP 로 세면 **맞는 지적을 오답으로 채점**하는 것이고, 그건 F4 가
막으려는 오류와 같은 종류다.

```python
if not finding.category.is_defect_claim:
    return Judgment(outcome=Outcome.UNDECIDABLE, ...)
```

- **분류는 도구에 묻는다** (C2). `ruff rule --all --output-format=json` 이
  룰마다 `category` 를 준다 — 16ms, 실행당 한 번.
  🔴 접두사로 짐작하면 조용히 틀린다: `TRY003`·`PERF203` 은 접두사로는 다른
  계열인데 Ruff 는 둘 다 `pedantic` 이다.
- **분류 출처를 `config_signature()` 에 적는다** (`cat=tool` / `cat=prefix`).
  두 경로가 다른 숫자를 내므로 모르면 재현이 안 된다.
- ⚠ **`OTHER` 는 결함 주장으로 친다.** 모델 지적은 분류가 비어 올 수 있는데
  그걸 관례로 취급하면 **모델의 FP 가 조용히 사라진다.**
- 🔴 **위치만 보는 곳을 전부 찾는다** (`bait.py` · `PairedFixGrader` 에도 같은 결함이 있었다) — 한 곳만 고치면
  숫자가 갈린다. 분류를 **싣는** 곳도 같다 — Ruff 가 낸 SARIF 는 같은 출처(`ruff rule --all`)의 분류를 쓰고,
  테스트는 지적 하나하나의 판정을 견준다 (DESIGN 교훈 #61).
- 🔴 **twin(양성) 쪽에도 같은 경계를 둔다** — 관례 주장은 결함을 짚은 것이 아니다. 한 방향만 고치면
  반대쪽에서 같은 오류가 산다 (DESIGN 교훈 #47).

이 수정으로 결론 두 개가 뒤집혔다 — **노이즈가 신호처럼 보였다** (DESIGN §3.5 「관례 주장은 거짓 경보가 아니다」).

### F6. 다회 실행을 뭉개지 않는다 🔴

평균도 합집합도 아니다. **빈도가 신호다** — seed 도 temperature 도 없는 제약이
공짜로 주는 유일한 관측치다.

`group_runs()` → `ObservedFinding.runs` 는 **개수가 아니라 실행 번호 집합**이다.
합집합 채점은 **고유 지적당 한 번**이고, 임계값은 채점자가 아니라 **집계 쪽**이 건다.
`Grader` 는 `rate` 를 판정에 쓰지 않는다 — 자기일관성은 정확성이 아니고,
그 관계는 **측정 대상이지 가정이 아니다.**

짝 채점도 같다 — `score_pairs()` 는 **합집합**이라 N회 중 한 번 튄 지적이 짝을
P-V 로 만든다. 다회 실행은 관점을 골라 **라벨을 붙인다** — `run=r`(한 번 돌렸을 때) ·
`at_least=k`(k-임계). 두 숫자는 다르다 (F3). `eval/multirun.py` 가 낸다.

🔴 관점별 숫자는 판정을 **걸러내지 않고** 관점의 지적만으로 **다시 채점**한다 (`runner.regrade_view`).
짝의 지적을 받는 채점자(`paired_fix`)는 합집합 짝으로 판정했으므로 걸러내면 그 판정이 남는다
(DESIGN 교훈 #38). 테스트가 채점자마다 「관점 값 = 그 실행만 채점한 값」을 본다.

🔴 리뷰어 비교는 같은 짝 위의 **차이**로 낸다 (`multirun.difference` — 두 리뷰어를 같은 짝으로
함께 복원추출). 두 구간을 눈으로 겹쳐 보지 않는다. 반복 횟수(F8) · 주 지표 · 주장 규칙은 수집
**전에** 선언한다 (DESIGN §7.10b). 회차가 고르지 않은
실행은 `pack --runs N` 으로 앞 N회만 묶는다 (DESIGN 교훈 #41).

🔴 **N회가 다 있는 샘플만 채점한다.** 모자란 회차는 「지적 0건」으로 읽혀 빈도가 거짓이 된다 —
미측정을 미탐지로 세는 것이다 (F4). 회차는 0부터 **끊김 없이** 센다 — 파일 개수가 아니다.

🔴 **묶음은 묶은 시점의 샘플에 고정된다** — `pack` 이 검증한 샘플을 `packed_samples` 로 적고(코퍼스 밖
샘플이 섞인 출력은 묶지 않는다) `report` 는 그 샘플만 재생한다. 그 안에서는 위처럼 엄격하고, 기록과
행이 다르거나 반쪽 짝이 있거나 잰 샘플이 코퍼스에 없으면 싣지 않는다 — 반쪽 짝은 짝 채점이 조용히 버린다
(DESIGN 교훈 #45). 잰 샘플이 다른 두 실행은 비교하지 않는다.
🔴 **잰 코드의 지문도 적는다** (`packed_digests` · `sample_digest`) — `report` 는 지금 코퍼스의 지문과 견줘
하나라도 다르면 그 묶음을 싣지 않는다. 재생은 묶은 지적을 **지금** 코퍼스로 다시 채점하므로 [소스: `_agent_sections`],
잰 뒤 decoy 코드를 고치면 옛 지적이 새 코드로 조용히 채점된다 (DESIGN §9 의 5).
🔴 **그 지문은 회차마다 남는다** — 실행기가 `<sample_id>.<run>.digest` 를 출력보다 먼저 쓰고, pack · import 는 지금
코드와 다르거나 없으면 거부한다. `packed_digests` 는 묶는 시점의 코퍼스로 재므로, 고친 샘플만 다시 잴 때 덜 옮긴 옛 출력에
새 지문이 조용히 붙는다 (DESIGN 교훈 #64).

### F7. LLM 판정자를 기본으로 쓰지 않는다 🔴

자기선호 편향으로 Claude vs Codex 비교가 무효화된다. 코드 도메인의 판정자 일치도는
전 도메인 최악이다(pairwise κ 0.159 / Fleiss κ 0.070).
불가피하면 **평가 대상과 다른 패밀리**에서 뽑고, 자체 라벨 30건 검증 κ 를 같이 보고한다.
예외 하나 — 보조 민감도(측정 뒤 FP 구간 지적의 재판정)에만 리뷰어를 가린 같은 패밀리 판정자 둘을 쓰고 κ 대신
판정자 사이의 일치를 낸다. 주 지표에는 쓰지 않는다 (DESIGN §4.2 · 선언 2026-10-05).

평가 대상을 확인자로 쓰는 것도 금지 — `SelfCorroborationError`.

### F8. 재현성은 프로토콜 수준에서만 주장한다

Anthropic 에 `seed` 가 없고 `temperature` 도 못 쓴다 → 출력은 환원 불가능하게 확률적이다.
반복 + 오차막대, **모든 원본 응답 아카이브.**
🔴 반복 횟수는 **수집 전에 선언**하고 근거를 같이 싣는다. 기본은 8 이고, 줄이려면 이 코퍼스의
정밀도 곡선을 근거로 댄다 — 이 코퍼스에서는 불확실성을 쌍 수가 지배해 3회로 줄였다 (DESIGN §7.10b).
결과를 보고 N 을 고르지 않는다 — optional stopping 이다. n=1 은 변동을 말하지 못해 파일럿으로만 싣는다.
"재현 가능한 출력" 이라고 쓰지 않는다. **"재현 가능한 프로토콜"** 이다.

---

## G. 코퍼스

### G1. 소스 코드를 저장소에 번들하지 않는다

배포 단위는 `(repo, SHA, path, line range)` + 자체 라벨 + 재구성 스크립트다.
마이닝 대상은 **MIT / BSD / Apache-2.0** 으로 한정한다.

### G2. 코퍼스는 코드가 아니라 **표본**이다

`corpus/decoys` · `corpus/xauthor` 는 프로젝트 린트 대상에서 제외돼 있다(`extend-exclude`).
린트를 만족시키려고 고치면 표본이 파괴된다 — D005 twin 의 미사용 인자는
**가드가 제거됐다는 증거**다. 분석기는 `--isolated` 로 돌아 영향받지 않는다.
코퍼스를 더하면 `extend-exclude` 와 `tests/corpora.py` 에 같이 더한다 — 쌍마다 도는 테스트(검증기 · 반증 ·
변이 · docstring 형식 · 린트 제외)가 그 목록을 돌고, 쌍은 `pair_dirs` 하나가 찾는다 (접두사로 찾지 않는다).

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

### G3b. 미끼가 물리는지 측정한다

```bash
uv run codeproof decoy stats
```

지적이 없으면 채점할 것도 없다. 물리지 않는 decoy 를 세어 150 을 채우면 숫자만 는다.

**다만 「안 물림 = 나쁨」이 아니다.** 셋으로 갈린다:

| 상태 | 의미 |
|---|---|
| 물림 | 시험됨 |
| 안 물림 · 추론 대상 | **미시험** — LLM 리뷰어가 있어야 안다 |
| 안 물림 · 미끼가 약함 | 실제로 나쁨 |

뒤의 둘은 정적분석기만으로 **구별할 수 없다.** 도구가 구별했다고 말하지 않는다.

린터를 더 붙여도 시험률은 오르지 않는다 — 린터가 무는 지점은 **위험 API 와 타입 오류뿐**이고,
락 보유 · 방어적 복사 · 반열린 계약 같은 논리형 덫은 어느 린터도 못 본다 (DESIGN §3.5).

🔴 **그러므로 쌍 수를 늘리는 것과 코퍼스를 검증하는 것은 다른 작업이다.**
   「미끼가 약함」과 「미시험」은 정적분석기만으로 구별되지 않으므로,
   150까지 채워도 **모델 리뷰어 없이는 품질을 말할 수 없다.**
   숫자가 늘었다고 검증됐다고 쓰지 않는다.

[실측] 미끼 효과는 **리뷰어 설정에 의존한다** — `--select ALL` 과 `--select F` 의
물림 비율이 다르다. 단일 설정으로 decoy 품질을 판정하지 않는다.

### G3c. 가드 훅이 형식만 막는다

`.claude/hooks/decoy-validate-guard.sh` 가 `corpus/decoys/` 편집 시
`decoy validate --strict` 를 돌리고, 위반이면 `decision: "block"` 으로 이유를 Claude 에게 돌려준다 —
편집 자체는 되돌리지 않는다.

🔴 **형식(V2~V14)만 잡는다.** G3a 의 「근거가 참인지」는 여전히 사람 몫이다.
   훅이 통과했다고 decoy 가 옳은 것이 아니다 - 바닥선이지 충분조건이 아니다.

🔴 **훅은 Write·Edit 로 고칠 때만 돈다.** Bash·편집기로 고친 decoy 는
   `test_repo_corpus_is_clean` 이 같은 기준(`--strict`)으로 본다. [실측] 그 테스트가
   오류만 보던 때는 쓰이지 않는 수용 표기(V11)를 넣어도 통과했다 - 훅과 테스트가
   「깨끗하다」를 다르게 정의하면 우회로가 곧 통과 경로다.

`_TEMPLATE/` 는 일부러 미완성이므로 검사에서 제외한다.

### G4. A층(변이 주입)을 단독 지표로 쓰지 않는다

Google 실측으로 변이체의 85% 가 무익하다. arid-node 억제(로깅·메모이제이션·`__repr__`·
`__main__`·모니터링 카운터·플래그 기본값)를 먼저 적용한다.
**recall 바닥선으로만** 보고하고 현실성을 주장하지 않는다.

---

## H. 테스트

### H1. 느린 테스트는 결국 안 돌린다

🔴 느린 원인은 고치고 **캐시로 가리지 않는다** — 캐시는 증상을 덮고 프로덕션 경로의 같은 비용은 그대로 남긴다.
고친 원인: `uv run` 경유 (C2) · 대상마다 subprocess (C1b) · 채점자가 분석기를 직접 실행 (E0).
지금 값은 CI 기록이 든다 (`.github/workflows/ci.yml`).

### H2. 동치 검증에 코퍼스 전체가 필요하지 않다

「일괄 == 개별」같은 **성질**은 대표 표본으로 충분하다. 다만
**지적이 나오는 표본을 반드시 포함**시킨다 - 아니면 「둘 다 0건」으로
공허하게 통과한다. 그걸 강제하는 테스트를 따로 둔다.

### H3. 가드는 **깨뜨려 본 뒤**에만 있다고 말한다 🔴

테스트가 통과하는 것은 「가드가 있다」의 증거가 아니다. 지키려는 것을
깨뜨렸는데도 통과하면 그 가드는 없는 것과 같다.

공허한 가드는 일부러 깨뜨려 보고서야 드러났다 (docs/VERIFY.md T3).

→ `scripts/falsify.sh` 가 불변식을 깨고 가드가 우는지 본다. **새 가드를 쓰면
  시나리오를 같이 추가한다.**

🔴 **계약은 두 줄이다.** `proof.py`(G3a1)와 같은 이유로, 한 줄로는 무능한
검사가 통과한다.

```
guard(깨끗한 트리) == 0   - 가드가 정상 상태를 통과시킨다
guard(깨뜨린 트리) != 0   - 가드가 위반을 **잡을 수 있다**
```

두 번째 줄만 있으면 가드 테스트 파일 이름만 바꿔도 `exit=4`(file not found)를 「울었다」로 읽어
**가드가 통째로 사라졌는데 초록불**이다 — `proof.py` 의 `return False` 와 같은 구멍이다 (docs/VERIFY.md T3).

🔴 **깨기가 아무것도 바꾸지 못하면 가드가 아니라 시나리오가 낡은 것이다.** perl · sed 는 치환할 곳이
없어도 0 을 낸다 — 하네스가 깨기 전후의 트리를 비교해 「깨뜨리지 못했다」로 센다. **코드를 고치면 전체 falsify 를 돈다** —
새 시나리오만 돌리면 기존 시나리오가 겨누던 줄이 바뀐 것을 못 본다.

🔴 **되돌리기는 깨끗한 트리를 확인한 뒤에만 건다** — 되돌리기가 검사보다 앞에 있으면 목록만 보려던 명령도
커밋 안 된 작업을 지운다 (커밋 96f213d). 미추적 파일도 검사한다 — `git checkout` 은 그것을 되돌리지 못한다.

## I. 코드 스타일

- `domain` 의 값 객체는 `@dataclass(frozen=True, slots=True)`.
- 외부 도구 출력 파싱은 **부분 실패를 예외로 올리지 않는다.** 1건이 깨져도 나머지를
  살리고, 깨진 건 세어서 남긴다. 🔴 버린 것도 센다 — 포맷마다 `ParseOutcome`(지적 + 버린 이유)을 낸다.
  세지 않으면 경로가 다른 입력이 경고 없이 「지적 0건」으로 들어온다 (DESIGN 교훈 #39).
- 프롬프트는 코드가 아니라 **데이터**다. `llm/prompts/` 에 파일로 두고 해시한다.
- 새 지표는 **신뢰구간을 같이 내지 않으면 추가하지 않는다.** 점추정만 내는 건 측정이 아니다.

---

## 하지 말 것

| 금지 | 규칙 |
|---|---|
| `domain` 에 외부 의존성 | A1 |
| 층(kind) 다른 리뷰어를 섞어 집계 | A2 |
| `cli.py` 에서 구현체 직접 생성 | A3 — registry 를 거친다 |
| 결정적 리뷰어를 N회 반복 | A2 |
| 단일 slack 값으로 결론 | A2a |
| 시작 줄만으로 위치 매칭 | A2a — 보고 관례가 순위를 뒤집는다 |
| effort 없이 · 격리 없이 에이전트 실행 | A2b — 개인 설정이 측정 조건이 된다 |
| 런타임에서 `eval/` import | A1 |
| 위치를 어댑터 밖에서 변환 · 도구 원본 규약을 그대로 쓰기 | B1 — 같은 mypy 실행도 컬럼이 다르다 |
| 지적 식별자에 라인 번호 | B2 |
| `ast.walk` 로 중첩 추출 | B3 |
| 실제 레포에 분석기 실행 | C1 |
| 호스트 설정·캐시를 격리 안 함 | C1a — 레포마다 다른 숫자 |
| `config_signature()` 가 실제와 다름 | C1a — 매니페스트가 거짓이 된다 |
| 실행을 가르는 `RUN.json` 항목을 지문에서 빼기 | A2b — 다른 실행이 같은 설정으로 읽힌다 |
| 복원 방식이 결과를 바꿈 | C1b |
| 대상마다 subprocess | C1b |
| `mypy.api.run` | C2 |
| 두 점 diff (`A..B`) | C3 |
| 래퍼를 측정 경로에 | D1 |
| 벤더 간 토큰 단순 합산 | D2 |
| nonce 없는 반복 호출 | D3 |
| effort 미지정 호출 | D4 |
| 강제 tool use · 재귀 스키마 · `temperature` · `fallbacks` | D5 |
| `run_reviewer` 밖의 실행 경로 | E00 — 새 훅이 한쪽에서 빠진다 |
| `verify/`·`eval/` 에서 도구 실행 | E0 — 증거는 받는 것이다 |
| 못 찾음을 REFUTES 로 | E2 |
| INCONCLUSIVE 로 점수 차감 | E2 |
| manifest 없는 결과 저장 | F1 |
| 층·리뷰어·어휘·숫자 섞기 | F3 |
| 판정 불가를 FP 로 | F4 |
| 관례 주장을 거짓 경보로 · 탐지로 | F4a — 맞는 지적을 오답으로, 우연을 탐지로 센다 |
| 룰 분류를 접두사로 짐작 | F4a — 도구에 묻는다 |
| 짝을 개별 지적으로만 채점 | F5 |
| 구성비를 선언 안 하고 집계 FPR 만 | F5a |
| 변동 측정값을 산문에 베끼기 | F5b — 생성물이 든다 |
| 생성물에 시각·run_id | F5b — 최신 여부를 못 묻는다 |
| 극단 두 분류의 구간으로 「분류마다 다르다」 | F5a — decoy 단위 순열 검정으로 분류 전체를 본다 |
| 다회 실행을 평균/합집합 | F6 |
| 관점별 숫자를 판정 걸러내기로 | F6 — 짝의 지적을 받는 채점자는 관점마다 다시 채점한다 |
| 두 리뷰어의 구간을 겹쳐 보고 비교 | F6 — 같은 짝 위의 차이와 그 구간으로 낸다 |
| 결과를 보고 반복 횟수를 정하기 | F8 — 수집 전에 선언하고 근거를 싣는다 (DESIGN §7.10b) |
| 모자란 · 끊긴 회차를 「지적 0건」으로 | F6 — 미측정이 미탐지가 된다 |
| 에이전트 묶음의 완결을 지금 코퍼스로 재기 · 잰 샘플이 다른 실행끼리 비교 | F6 — 묶은 시점의 샘플(`packed_samples`)로 잰다 |
| 잰 뒤 decoy 코드를 고친 채 옛 묶음을 재생 | F6 — 잰 코드의 지문(`packed_digests`)이 다르면 싣지 않는다 |
| 회차마다의 잰 코드 지문 없이 실행기 출력을 묶기 | F6 — 덜 옮긴 옛 출력이 새 지문으로 묶인다 |
| 버린 지적을 세지 않는 파서 | I — 미측정이 미탐지가 된다 |
| `rate` 를 판정 근거로 | F6 |
| 기본 LLM 판정자 · 자기 확인 | F7 |
| "재현 가능한 출력" 표현 | F8 |
| 소스 코드 번들 | G1 |
| 코퍼스를 프로젝트 린트 대상에 | G2 |
| 근거 없는 decoy | G3 |
| 근거가 거짓인 decoy | G3a — 훅도 못 잡는다. 사람이 본다 |
| 미끼 효과를 단일 설정으로 판정 | G3b |
| 느린 테스트를 캐시로 덮기 | H1 — 프로덕션 비용이 남는다 |
| 깨뜨려 보지 않고 가드가 있다고 말하기 | H3 — 공허한 가드를 둘 잡았다 |
| 한 줄짜리 반증 계약 | H3 · G3a1 — 무능한 검사가 통과한다 |
