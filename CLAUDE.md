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
uv run codeproof report          # docs/MEASUREMENTS.md 생성 (--check 로 최신 확인)
uv run codeproof decoy validate  # decoy 규격 검사
uv run codeproof decoy new <id>  # 템플릿에서 새 decoy
```

**코퍼스 구축 환경은 별도다** — `cd corpus && uv sync`. 본 패키지의 `>=3.14` 와
벤치마크 툴체인이 충돌한다. **uv workspace 로 묶지 마라** — resolution 이 통합되어 같은 충돌이 살아난다.

---

## A. 구조

### A1. 레이어 의존 그래프

```
domain   → (없음)              analysis → domain
llm      → domain              verify   → domain          ← eval 이 없다
corpus   → domain              eval     → domain·analysis·llm·verify·corpus
store    → domain·eval         cli      → 전부
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

[실측] 같은 결함을 Ruff 는 호출 시작 줄(L9)로, bandit 은 `shell=True` 인자 줄(L11)로
보고한다. 결함 구간이 5-10 이면 `slack=0` 에서 한쪽만 TP 가 된다 —
**리뷰 품질 차이가 아니라 보고 관례 차이다.**

→ 단일 slack 값으로 낸 숫자를 결론으로 쓰지 않는다. `sensitivity.sweep()` 으로
  스윕해 **흔들리는지**를 같이 낸다. 흔들리면 그 결론은 매칭 정책의 산물이다.

→ 스윕은 **채점만 다시 한다.** 리뷰어를 다시 돌리면 slack 효과와 실행 변동이 섞인다.

### A3. 확장점 — registry 가 맞는 자리와 아닌 자리

| Protocol | registry | 새 구현 |
|---|---|---|
| `Analyzer` | `analysis/registry.py` | 클래스 추가 + `ANALYZERS` 한 줄 |
| `ReviewProvider` | `llm/registry.py` | 클래스 추가 + `PROVIDERS`·`CREDENTIAL_OF` |
| `FindingFormat` | `reviewers/formats.py` | 파서 추가 + `FORMATS` |
| `Reviewer` | — | `reviewers/<name>.py`. **먼저 `ImportedReviewer` 로 되는지 본다** |
| `Verifier` | — | `verify/<rule>.py`. 파이프라인 구성은 호출부 정책 |
| `Grader` | **없음 (의도)** | `eval/grading/<name>.py` |

🔴 **채점자에 registry 를 두지 않는 것은 의도다.** 생성 인자가 균일하지 않다 —
`StaticCorroborationGrader` 만 `reference` 를 받는다. 균일한 팩토리를 억지로 만들면
그 비균일성이 `**kwargs` 딕셔너리로 숨고, 그게 더 나쁘다. CLI 가 정책으로 조립한다.

🔴 **`cli.py` 는 구현 클래스를 직접 생성하지도 import 하지도 않는다.**
[실측] 이 규칙을 문서에만 적어두었을 때 cli.py 는 **8곳에서 직접 생성**하고 있었다.
`tests/architecture/test_registry.py` 가 지금은 그걸 막는다.

**Java 지원은 `analysis/java/` 추가 + `ANALYZERS` 등록만으로 성립해야 한다.**
`analysis/base.py` 에 Python 전용 개념(`.py` 확장자 · ast 노드 · ruff 룰 코드)이
새면 그 약속이 깨진다.

## B. 데이터 — 조용히 틀리는 지점

### B1. 위치는 내부 단일 규약으로 정규화 🔴

**1-based line + 0-based 문자 column** (`byte_start` 병기).

도구 원본이 전부 다르다 — Ruff(1-based 문자) · mypy JSON(0-based 바이트) ·
mypy 텍스트(1-based 바이트) · ast(0-based 바이트) · SARIF(1-based 문자).
**같은 mypy 실행이 텍스트와 JSON 에서 다른 컬럼을 낸다.**

- 변환은 `analysis/<lang>/<tool>.py` 어댑터 **안에서만**. 어댑터 하나가 변환 하나를 책임진다.
- **비ASCII 회귀 테스트를 지우지 않는다.** 없으면 이 버그는 조용히 산다.
- ⚠ mypy `--native-parser` 가 곧 기본값 → 컬럼 의미 변동 가능. 핀 테스트로 감지한다.

### B2. 지적 식별자에 라인 번호를 쓰지 않는다 🔴

```python
fingerprint = hash(rule_id, enclosing_symbol, normalized_snippet)
```

넣으면 위쪽 줄만 고쳐도 모든 지적이 새 지적이 된다.
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

🔴 **`config_signature()` 가 거짓을 적지 않게 한다.** 격리 전에는 `mypy(strict=False)` 라고
기록하면서 실제로는 strict 로 돌고 있었다 — 매니페스트가 거짓이면 재현성 설계가 무의미하다.

### C1b. 대상이 여럿이면 일괄로 돈다

`Analyzer.analyze_many(targets)` 는 **한 번의 subprocess** 로 전부 분석한다.

[실측] 15쌍 시점(30 대상) 기준: ruff 0.39s → 0.04s (**9.9배**), mypy 17.1s → 0.52s (**33배**).
대상마다 띄우면 300 샘플에서 mypy 만 3분이 넘는다.

🔴 **복원 방식이 분석 결과를 바꾸면 안 된다.** [실측] `__init__.py` 를 무조건 넣었더니
Ruff 의 `INP001` 이 사라져 일괄과 개별이 다른 숫자를 냈다. mypy 만 모듈명 해소에
필요하므로 `materialize_many(..., as_packages=True)` 로 **선택적**이다.

테스트가 「일괄 == 개별」을 강제한다 — 속도 최적화가 숫자를 바꾸면 최적화가 아니라 버그다.

### C2. Ruff · mypy 는 subprocess 로만

```bash
ruff check --output-format=json --no-cache --exit-zero    # 대량이면 json-lines
mypy --output=json --show-error-end --show-absolute-path --no-error-summary
```

- **`uv run <tool>` 을 거치지 않는다.** `codeproof` 는 이미 venv 안이라 PATH 에 잡힌다.
  [실측] 오버헤드 ruff 53→10ms, mypy 308→123ms. 300 대상이면 그것만 1분이 넘는다.
  `analysis/toolchain.py` 의 `resolve()` 를 쓴다.
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

[실측] 전에 러너가 셋이었다. 짝 채점용 `bind_run()` 훅을 `run_reviewer` 에만
걸었고, **CLI 가 쓰던 나머지 둘은 조용히 전부 TP 로 채점**했다 — 예외도 경고도
없이. 경로가 갈리면 새 훅은 반드시 한쪽에서 빠진다.
→ `tests/architecture/test_single_runner.py` 가 이걸 강제한다.

### E01. 매니페스트 항목은 **리뷰어가 신고**한다

러너는 `effort` 나 도구 버전을 짐작하지 않는다. 모르면 리뷰어에게 묻는다.

```python
def manifest_fields(self) -> dict[str, str]: ...   # effort · cache_policy
def tool_versions(self) -> tuple[ToolVersion, ...]: ...
```

러너가 기본값을 박아 넣으면 모델 실행에 `effort="n/a"` 가 기록된다 —
**숫자는 맞는데 출처가 거짓**인 매니페스트는 재현을 불가능하게 만든다.
(mypy 가 host 설정을 물려받는데 `strict=False` 라고 적던 것과 같은 종류다)

### E02. 채점자가 문맥 없이 돌면 **거부한다**

실행 문맥이 필요한 채점자는 미바인딩 상태를 `None` 으로 구분하고
`UnboundGraderError` 를 던진다. 빈 컬렉션으로 초기화하지 않는다 —
빈 짝은 「짝에 지적이 없다」로 읽혀 **기본값이 곧 오답**이 된다.

### E0. 🔴 `verify/` 와 `eval/` 모두 증거를 **받는다**

검증자든 채점자든 **도구를 직접 돌리지 않는다.** 이미 계산된 지적을 생성자로 받는다.

```python
CorroborationVerifier(reference=ruff_findings)              # verify/
StaticCorroborationGrader(reference=analyzer.analyze_many(targets))  # eval/
```

[실측] `eval/` 에만 이 원칙을 빠뜨렸더니 채점자가 샘플마다 분석기를 돌려
**전체 테스트가 61초 늘었다**(30 샘플 × 15초). 원칙을 한쪽에만 적용하면
일관성뿐 아니라 성능도 새어나간다.

### E1. 증거를 수집하지 않고 **받는다**

검증자는 도구를 돌리지 않는다. 이미 계산된 지적을 생성자로 받는다.

```python
CorroborationVerifier(reference=ruff_findings)   # 엔진이 돌려서 넘긴다
```

`verify/ → analysis/` 는 레이어 위반이고, 검증 단위 테스트에 subprocess 가 끌려 들어온다.
`Verifier.verify(finding, target)` 는 경로가 아니라 `ReviewTarget` 을 받는다.

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
모델은 **정상이고 그 폭이 측정 대상**이다. 리포트가 구분해서 말한다.

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
헤드라인은 구별 성공률. [실측] Ruff 는 37쌍에서 **0/37** 다 — 그중
**26건이 P-R(역전)**, 즉 안전한 쪽만 지적했다. 못 찾는 것보다 거꾸로 찾는 게 많다.

🔴 **`score_pairs()` 는 사후 요약이라 Precision 을 고치지 못한다.**
per-finding 으로는 여전히 TP 가 남는다. 채점 단계에서 막으려면
`PairedFixGrader` 를 쓴다 — 「짝에 없는 지적만 탐지로 인정」하는 별도 정의다.
그 채점자는 짝의 지적이 필요하므로 `runner` 가 **리뷰와 채점을 분리**하고
`bind_run()` 으로 실행 전체를 넘긴다.

### F5a. 코퍼스 **구성비**도 손잡이다 🔴

D층 집계 FPR 은 「도구의 오탐률」이 아니라 **「내가 고른 미끼 분류 구성비에서의
오탐률」**이다. [실측 · 37쌍] 분류별 물림율이 `type_narrowed` 0.0% ~
`constant_only_sink` 53.8% 로 갈린다 — **코드도 도구도 채점자도 그대로 두고
구성비만 바꿔** 0% 도 55.6% 도 보고할 수 있다.

→ `mix_sensitivity()` 를 집계와 같이 낸다. 구성비를 매니페스트에 싣는다.

🔴 **축이 둘이다. 둘 다 잰다.** `TrapKind` 는 「어떤 종류의 논증인가」,
   `GuardShape` 는 「가드를 찾으려면 어디를 봐야 하는가」다 — 직교한다.
   한 축만 고르게 채워도 다른 축이 쏠릴 수 있다.
   [실측 · 37쌍] 가드가 멀수록 더 문다: `local` 18.2% < `caller` 31.9% <
   `callee` 42.6% < `module` 45.2%. **미끼 분류 축과 순서가 다르다.**

   `GuardShape` 는 **도출한다** — `meta.toml` 에 적게 하지 않는다.
   손으로 적는 축은 틀리고, 틀려도 아무도 모른다.

🔴 **다만 「범위가 넓다」와 「분류마다 다르다」는 다른 주장이다.**
   앞은 측정 절차에 대한 참인 진술이고, 뒤는 **모집단에 대한 주장**이라
   표본이 필요하다. 극단 두 분류의 Wilson CI 가 겹치면 겹친다고 말한다
   `heterogeneity_verdict` 가 강제한다.

🔴 **그리고 CI 가 갈릴 때까지 표본을 늘리다 멈추지 않는다 — optional stopping 이다.**
   분류당 목표 쌍 수를 **미리 선언**하고(`TARGET_PAIRS_PER_KIND`), 미달 상태의
   판정에는 도구가 꼬리표를 붙인다. [실측] 37쌍에서 CI 가 갈렸지만(25쌍 시점에는
   3.2pp 겹쳤다) 선언 표본 미달이므로 결론이 아니다.

⚠ 증명된 음성 위에서 `FP/(TP+FP)` 는 **항상 100%** 다 — TP 가 정의상 불가능하다.
  분모는 **나온 지적 전부**여야 「몇이 물렸나」가 된다. 범위 밖(UNDECIDABLE)은
  「이 미끼와 무관한 지적」이라 분모에 남는다. 이건 F4 위반이 아니다 —
  판정 불가를 FP 로 **접는** 것이 아니라 별도 칸으로 세는 것이다.

⚠ 지적은 **독립 시행이 아니다** — decoy 하나가 여러 지적을 낸다. 지적 단위 CI 는
  실제보다 좁으므로 **샘플 단위 비율을 같이** 낸다.

### F5b. 변동하는 측정값을 산문에 베끼지 않는다 🔴

```bash
uv run codeproof report            # docs/MEASUREMENTS.md 생성
uv run codeproof report --check    # 낡았으면 exit 1
```

[실측] 코퍼스를 19 → 25 → 37 → 43 쌍으로 키우는 동안 문서 일관성 테스트가
**매번** README·DESIGN·CLAUDE 세 곳의 낡은 숫자를 잡았다. 테스트가 제 일을
한 것이지만 **반복은 설계 신호**였다 - 변동값을 산문에 박아 둔 것이 원인이다.

- 현재 수치는 **생성물**이 든다. 산문은 안정된 주장만 쓰고 그 파일을 가리킨다.
- 산문에 숫자를 남길 때는 **표본 크기를 붙인다** — `[실측 · 37쌍]`.
  숫자와 표본이 붙어 다니면 **스스로 날짜를 밝히므로** 나중에도 읽힌다.
- 🔴 생성물에 **시각·run_id 를 넣지 않는다.** 넣으면 코퍼스가 그대로여도
  매번 달라져 「최신인가」를 물을 수 없다. 재현 정보는 `config_hash` 로 충분하다.
- 생성물은 손으로 고치지 않는다. 파일 첫 줄이 그렇게 말하고 테스트가 강제한다.

### F6. 다회 실행을 뭉개지 않는다 🔴

평균도 합집합도 아니다. **빈도가 신호다** — seed 도 temperature 도 없는 제약이
공짜로 주는 유일한 관측치다.

`group_runs()` → `ObservedFinding.runs` 는 **개수가 아니라 실행 번호 집합**이다.
채점은 **고유 지적당 한 번**, 임계값은 **집계 시점**에 건다.
`Grader` 는 `rate` 를 판정에 쓰지 않는다 — 자기일관성은 정확성이 아니고,
그 관계는 **측정 대상이지 가정이 아니다.**

### F7. LLM 판정자를 기본으로 쓰지 않는다 🔴

자기선호 편향으로 Claude vs Codex 비교가 무효화된다. 코드 도메인의 판정자 일치도는
전 도메인 최악이다(pairwise κ 0.159 / Fleiss κ 0.070).
불가피하면 **평가 대상과 다른 패밀리**에서 뽑고, 자체 라벨 30건 검증 κ 를 같이 보고한다.

평가 대상을 확인자로 쓰는 것도 금지 — `SelfCorroborationError`.

### F8. 재현성은 프로토콜 수준에서만 주장한다

Anthropic 에 `seed` 가 없고 `temperature` 도 못 쓴다 → 출력은 환원 불가능하게 확률적이다.
`n≥8` 반복 + 오차막대, **모든 원본 응답 아카이브.**
"재현 가능한 출력" 이라고 쓰지 않는다. **"재현 가능한 프로토콜"** 이다.

---

## G. 코퍼스

### G1. 소스 코드를 저장소에 번들하지 않는다

배포 단위는 `(repo, SHA, path, line range)` + 자체 라벨 + 재구성 스크립트다.
마이닝 대상은 **MIT / BSD / Apache-2.0** 으로 한정한다.

### G2. 코퍼스는 코드가 아니라 **표본**이다

`corpus/decoys` 는 프로젝트 린트 대상에서 제외돼 있다(`extend-exclude`).
린트를 만족시키려고 고치면 표본이 파괴된다 — D005 twin 의 미사용 인자는
**가드가 제거됐다는 증거**다. 분석기는 `--isolated` 로 돌아 영향받지 않는다.

### G3. decoy 규격

```bash
uv run codeproof decoy new D00X-짧은-설명
uv run codeproof decoy validate          # CI 는 --strict
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
| **V9** | **변경이 가드 구간 또는 `guard_symbol` 참조를 건드림** (제거 또는 우회) |
| V10 | 미끼가 파일 범위 안 |
| W2 | 시그니처 차이 — 의도적이면 `acknowledged_warnings` |
| V11 | 쓰이지 않는 수용 표기 |

`acknowledged_warnings` 는 **최상위**에 쓴다 (테이블 헤더 뒤면 그 테이블로 들어간다).
**ERROR 는 수용 대상이 아니다** — 수용 가능하면 애초에 ERROR 가 아니어야 한다.

### G3a. 🔴 검증기는 근거가 **참인지** 검사하지 못한다

V3 은 근거의 **형식**(길이 · 낱말 수 · 인과 연결어)만 본다. 내용이 맞는지는 못 본다.

[실측] `D015` 를 처음 쓸 때 `threading.Semaphore(4)` 를 가드로 삼았다.
세마포어는 최대 4 스레드 동시 진입을 허용하므로 그 경쟁은 **실제로 일어난다** —
안전 주장이 거짓이었고, **11개 규칙을 전부 통과했다.** 손으로 검토하다 잡았다.

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
증명**한다. Juliet 의 goodG2B/goodB2G 구조를 코드가 아니라 **증명 자체**에 적용한 것.

검산: D015 의 원래 `Semaphore(4)` 버전을 복원하면 `attack(decoy)` 가 True 가 되어
걸린다. **11개 형식 규칙이 놓친 것을 이게 잡는다.**
(`tests/corpus/test_proofs.py::TestItCatchesTheBugThatSlippedThrough`)

🔴 **면제 목록을 두지 않는다.** 전에는 「실행으로 확인 못 하는 것」을
`UNTESTED_BY_DESIGN` 에 적었고, 그 시점의 19쌍 중 **8건(42%)이 그 목록에 있었다** —
그리고 사유 다섯 개가 전부 틀린 것으로 드러났다(동시성·자원수명·경로탈출 전부
검증 가능했다). **「너무 어렵다」가 조용히 「검증 안 됨」이 되는 자리**였다.
공격을 못 쓰면 그 decoy 는 싣지 않는다.

| 층 | 무엇을 보는가 | 어디서 |
|---|---|---|
| V2~V11 | 형식 — 근거 길이 · 가드 가시성 · 짝 구조 | `decoy validate` (훅이 강제) |
| **V12** | **proof.py 존재와 서명** | `decoy validate` |
| **반증 실행** | **근거가 참인가** | `pytest tests/corpus/test_proofs.py` |
| AST 구조 증명 | 「경로가 **없다**」류 주장 | `tests/corpus/test_safety_claims.py` |

마지막 층이 따로 있는 이유: **실행은 부재를 보일 수 없고 AST 는 보일 수 있다.**
「외부 입력이 이 sink 에 닿는 경로가 없다」는 돌려서 증명하지 못한다.

⚠ 그래도 증명이 아니라 **반증 시도**다. 공격이 약하면 통과한다.
  경쟁은 `race_window()` 로 창을 벌리지만 여전히 확률적이다.
  [실측] 그것 없이는 16스레드 x 5000회에 갱신 손실 **0건** — CPython 은 그
  두 줄 사이에서 스레드 전환을 검사하지 않는다.

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

[실측] `type_narrowed` 는 0/2 다 — Ruff 에 그런 룰이 없고 mypy 는 좁힘을
**정당하다고 인정**한다. 구조적 사실이지 decoy 결함이 아니다.

[실측] 미끼 효과는 **리뷰어 설정에 의존한다** — `--select ALL` 과 `--select F` 의
물림 비율이 다르다. 단일 설정으로 decoy 품질을 판정하지 않는다.

### G3c. 가드 훅이 형식만 막는다

`.claude/hooks/decoy-validate-guard.sh` 가 `corpus/decoys/` 편집 시
`decoy validate --strict` 를 돌리고, 위반이면 `decision: "block"` 으로 되돌린다.

🔴 **형식(V2~V11)만 잡는다.** G3a 의 「근거가 참인지」는 여전히 사람 몫이다.
   훅이 통과했다고 decoy 가 옳은 것이 아니다 - 바닥선이지 충분조건이 아니다.

`_TEMPLATE/` 는 일부러 미완성이므로 검사에서 제외한다.

### G4. A층(변이 주입)을 단독 지표로 쓰지 않는다

Google 실측으로 변이체의 85% 가 무익하다. arid-node 억제(로깅·메모이제이션·`__repr__`·
`__main__`·모니터링 카운터·플래그 기본값)를 먼저 적용한다.
**recall 바닥선으로만** 보고하고 현실성을 주장하지 않는다.

---

## H. 테스트

### H1. 느린 테스트는 결국 안 돌린다

[실측] 이 저장소의 전체 테스트는 한때 **99초**였다. 원인은 셋이었고 전부 고쳤다:

| 원인 | 조치 | 효과 |
|---|---|---|
| `uv run <tool>` 경유 | `toolchain.resolve()` 로 직접 호출 | ruff 53→10ms · mypy 308→123ms |
| 대상마다 subprocess | `analyze_many()` 일괄 | [실측] ruff 9.9배 · mypy 33배 |
| 채점자가 분석기를 직접 실행 | 증거를 미리 계산해 전달 (E0) | −61초 |

지금은 **26초**다. 🔴 캐시로 가리지 않았다 - 캐시는 증상을 덮고
프로덕션 경로의 같은 비용은 그대로 남긴다.

### H2. 동치 검증에 코퍼스 전체가 필요하지 않다

「일괄 == 개별」같은 **성질**은 대표 표본으로 충분하다. 다만
**지적이 나오는 표본을 반드시 포함**시킨다 - 아니면 「둘 다 0건」으로
공허하게 통과한다. 그걸 강제하는 테스트를 따로 둔다.

## I. 코드 스타일

- `domain` 의 값 객체는 `@dataclass(frozen=True, slots=True)`.
- 외부 도구 출력 파싱은 **부분 실패를 예외로 올리지 않는다.** 1건이 깨져도 나머지를
  살리고, 깨진 건 세어서 남긴다.
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
| 런타임에서 `eval/` import | A1 |
| 지적 식별자에 라인 번호 | B2 |
| `ast.walk` 로 중첩 추출 | B3 |
| 실제 레포에 분석기 실행 | C1 |
| 호스트 설정·캐시를 격리 안 함 | C1a — 레포마다 다른 숫자 |
| `config_signature()` 가 실제와 다름 | C1a — 매니페스트가 거짓이 된다 |
| 복원 방식이 결과를 바꿈 | C1b |
| 대상마다 subprocess | C1b |
| `mypy.api.run` | C2 |
| 두 점 diff (`A..B`) | C3 |
| 래퍼를 측정 경로에 | D1 |
| 벤더 간 토큰 단순 합산 | D2 |
| nonce 없는 반복 호출 | D3 |
| effort 미지정 호출 | D4 |
| 강제 tool use · 재귀 스키마 · `temperature` · `fallbacks` | D5 |
| `verify/`·`eval/` 에서 도구 실행 | E0 — 증거는 받는 것이다 |
| 못 찾음을 REFUTES 로 | E2 |
| INCONCLUSIVE 로 점수 차감 | E2 |
| manifest 없는 결과 저장 | F1 |
| 층·리뷰어·어휘·숫자 섞기 | F3 |
| 판정 불가를 FP 로 | F4 |
| 짝을 개별 지적으로만 채점 | F5 |
| 구성비를 선언 안 하고 집계 FPR 만 | F5a |
| 변동 측정값을 산문에 베끼기 | F5b — 생성물이 든다 |
| 생성물에 시각·run_id | F5b — 최신 여부를 못 묻는다 |
| CI 겹치는데 「분류마다 다르다」 | F5a |
| 다회 실행을 평균/합집합 | F6 |
| `rate` 를 판정 근거로 | F6 |
| 기본 LLM 판정자 · 자기 확인 | F7 |
| "재현 가능한 출력" 표현 | F8 |
| 소스 코드 번들 | G1 |
| 코퍼스를 프로젝트 린트 대상에 | G2 |
| 근거 없는 decoy | G3 |
| 근거가 거짓인 decoy | G3a — 훅도 못 잡는다. 사람이 본다 |
| 미끼 효과를 단일 설정으로 판정 | G3b |
| 느린 테스트를 캐시로 덮기 | H1 — 프로덕션 비용이 남는다 |
