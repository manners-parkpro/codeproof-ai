# 결과 · 근거 · 한계

> [README](../README.md) 의 자세한 판이다. 현재 수치는 생성물 [MEASUREMENTS.md](MEASUREMENTS.md) 가 들고,
> 여기 숫자는 표본 크기를 붙인 시점 값이다. 주장을 직접 무너뜨려 보는 절차는 [VERIFY.md](VERIFY.md) 에 있다.

## 리뷰어는 한 가지 개념이다

지적을 내는 것은 전부 리뷰어이고, **같은 하네스로 돌고 같은 채점을 받는다.**

| 층 | 예 | API 키 |
|---|---|---|
| `static` | Ruff · mypy | 불필요 |
| `imported` | SARIF(CodeQL · semgrep · Snyk · Trivy) · bandit JSON | 불필요 |
| `agent` | Codex CLI · Claude Code 출력을 저장해 가져오기 | 불필요 (원본 지적이 실려 있어 다시 채점된다) |
| `model_api` | Anthropic · OpenAI SDK | 필요 |
| `human` | 사람 리뷰 — 기준선이자 상한 | 불필요 |

⚠️ **층이 다르면 섞어 집계하지 않는다.** 에이전트는 파일 탐색 · 다회 턴 · 툴 사용이 가능해 `model_api` 와 조건이
다르다. `ReviewerKind` 가 그 경계를 타입으로 표현하고, 리포트가 구분해서 말한다.

## 지금 나오는 결과

`Ruff` 와 `mypy` 는 **이미 리뷰어다.** 지적을 내므로 채점할 수 있고, 채점 기준을 바꾸면 숫자가 바뀐다.
그래서 논지는 **모델 API 없이도 성립한다.** 아래는 API 키 없이 다시 나온다 — 결과 1~3 · 5 · 6 은
`uv run codeproof measure` 와 `uv run codeproof report`(생성물), 결과 4 는 `uv run pytest tests/verify/test_verifiers.py`,
결과 7 은 저장소에 실린 원본 지적을 `report` 가 다시 채점한다.

### 결과 1 — 안전한 코드와 터지는 코드를 구별하지 못한다

`D002` 쌍은 `shell=True` 를 쓴다. decoy 는 커맨드가 모듈 상수라 안전하고, twin 은 인자를 보간해서 진짜 취약하다.

| 파일 | 실제 | Ruff |
|---|---|---|
| `decoy.py` | **안전** (커맨드가 모듈 상수) | `S602 shell=True, security issue` |
| `twin.py` | **취약** (인자를 보간) | `S602 shell=True, security issue` |

**같은 룰, 같은 줄, 같은 판정.** PrimeVul 용어로 **P-V(과잉지적)** 이고, 왼쪽은 널리 쓰이는 프로덕션 분석기의
**확인된 False Positive** 다. `D001` 은 반대다 — decoy 에도 twin 에도 결함 주장을 하나도 내지 않는다.
twin 의 진짜 KeyError 를 놓친다. **확인된 False Negative.**

### 결과 2 — 같은 지적을 여러 정의로 채점하면 FP 가 **수십 배** 갈린다 [실측 · 150쌍]

이 프로젝트의 헤드라인이다. `--ruff-select ALL` 에서 같은 지적을 채점자 넷으로 채점한 FP 다 [실측 · 150쌍] (테스트가 생성물과 대조한다):

```
채점자                     TP   FP  판정불가  FP가능
provable_safety           0   17     760      o     <- 결함 주장만, 그것도 근거 범위 안만
injected_defect           0  777       0      o     <- Qodo 정의: 판정 불가 칸이 없다
paired_fix                0   18     759      o
static_corroboration      5    0     772      x     <- 구조적으로 FP 를 못 낸다
```

룰 선택마다의 그림은 README 「30초 요약」에 있다 ([figures/spread.svg](figures/spread.svg)).
편차의 정체는 둘이다 — **① 한쪽이 「판정할 수 없다」고 둔 것을 다른 쪽이 「틀렸다」로 센다**(Qodo 계열에는 그 칸이 없다).
**② 관례 주장(docstring 누락 같은 것)을 거짓 경보로 세느냐.** ②가 특히 크다 — 그 지적들은 **사실이기** 때문에
오탐으로 세면 맞는 지적을 오답으로 채점하는 것이 된다.

> ⚠️ `static_corroboration` 의 FP 0 은 편차가 아니라 **범주 차이**다 — 합의 기반 정의는 구조적으로 FP 를 낼 수 없다
> (동의 부재 ≠ 반증). 그 0 을 편차에 넣으면 배수가 끝없이 부푸는데, 그건 우리가 비판하는 과장이다.
> 도구가 어휘를 확인하고 **자동으로 제외**한다.

### 결과 3 — 짝 판정도 채점자의 함수다

증명된 음성과 가드만 제거한 twin 을 짝으로 놓고 Ruff 를 `--ruff-select ALL` 로 돌린 PrimeVul 짝 채점이다.
**리뷰어도 지적도 바꾸지 않고 정답 정의만 바꿨다** [실측 · 150쌍].

| 채점 정의 | 구별 성공 | P-V 과잉지적 | P-B 미탐지 | P-R 역전 |
|---|---:|---:|---:|---:|
| `provable_safety` | 1 | 5 | **134** | 10 |
| `injected_defect` (Qodo 계열) | 0 | 26 | 0 | **124** |

![같은 Ruff 실행의 짝 판정 — 채점 정의별 (생성물)](figures/pairs.svg)

🔴 **같은 실행이다.** 거의 갈라내지 못했다는 데는 둘이 같지만, 한쪽은 「거의 다 놓쳤다」고 말하고 다른 쪽은
「거꾸로 찾았다」고 말한다 — 리뷰어가 **어떻게** 실패했는지가 정의의 선택으로 정해진다.

🔴 **그 「거꾸로」는 매칭 정책의 산물이기도 하다.** `injected_defect` 는 결함 줄과 **정확히** 맞아야 탐지로 세는데,
Ruff 는 결함을 결함 줄 옆에 보고하는 일이 많다. 허용 오차를 넓히면 가장 많은 판정이 역전에서 과잉지적(둘 다 지적)으로
바뀌고, `provable_safety` 의 「거의 다 놓쳤다」는 사다리 전체에서 그대로다 [실측 · 150쌍 · 생성물 「짝 판정 사다리」].
그래서 짝 그림은 막대(slack 0) 옆에 사다리의 판정을 같이 싣는다 — 결과 5 의 규율을 짝 판정에도 적용한 것이다.
`--ruff-select S` 로 좁히면 두 정의의 짝 판정이 **완전히 같아진다** (구별 성공 2 · 과잉 3 · 미탐지 140 · 역전 5)
[실측 · 150쌍] — 보안 룰만 쓰는 벤치마크였다면 「정답 정의는 결과에 영향이 없다」고 결론 내렸을 것이고, 그건 틀렸다.

**지적 단위로만 보면 이 사실이 보이지 않는다.** twin 쪽만 세면 Precision 이 높게 나오는데, 그 TP 는 안전한 쪽에도
똑같이 낸 지적이 우연히 결함 자리에 걸린 것이다.

> 🔴 **철회 기록.** 이 표는 한때 `provable_safety` 의 구별 성공을 11 로 실었다 [실측 · 60쌍 시점]. 11건은 전부 twin 위의
> docstring · 스타일 지적이 결함 구간에 겹친 것이었다 — 관례 주장을 음성 쪽에서는 판정 불가로 돌리면서 twin 쪽에서는
> 탐지로 세고 있었다. 양쪽에 같은 경계를 두자 0 이 됐다 ([DESIGN 교훈 #47](DESIGN.md)). 같은 버그로 발표했던 결론
> 두 개(미끼 시험률 · 가드 위치 순서)도 철회했다.

### 결과 4 — 검증 레이어는 **쌍에 따라 갈린다**

파이프라인 3·4단계(인용 검증 · 가드 탐지 · 교차 확인 · 도달성 — [DESIGN §5](DESIGN.md))를 두 쌍으로 시험했다 —
코퍼스 전체를 잰 숫자가 아니라 사례다. `D010` 은 구별했다 —
`_deliver` 안의 멱등 검사를 **callee-guard** 가 찾아 안전한 쪽의 confidence 를 내렸다. `D002` 는 구별하지 못했다 —
「커맨드가 모듈 상수라 외부 입력이 닿지 않는다」는 제어흐름이 아니라 **오염 추적(taint analysis)** 이 필요하고,
이 검증자는 그걸 못 본다. 두 경우를 테스트가 고정한다 ([`tests/verify/test_verifiers.py`](../tests/verify/test_verifiers.py)).

> **못 보는 것을 문서에 적지 않으면 `SUPPORTS` 가 과신으로 읽힌다.**
> 그래서 각 검증자의 한계를 독스트링에 명시하고, 테스트가 그 문장의 존재를 강제한다.

### 결과 5 — 판정이 **매칭 손잡이에 흔들린다**

같은 결함을 도구마다 다른 줄로 보고한다 — Ruff 는 호출 시작 줄, bandit 은 `shell=True` 인자 줄을 대표 줄로 둔다.
대표 줄로만 맞추면 **리뷰 품질 차이가 아니라 보고 관례 차이**가 TP 와 FP 를 가른다. 그래서 이 저장소는 보고 범위로
맞추고, 허용 오차(slack)를 사다리로 바꿔 가며 판정이 흔들리는지를 같이 낸다.

```
[매칭 민감도] slack 을 바꾸면 판정이 흔들리는가   [실측 · 150쌍 · ruff ALL · provable_safety]
   slack  P-C  P-V  P-B  P-R
       0    1    5  134   10
       2    3    7  132    8
       5    6   10  128    6
      10    7   14  127    2
  🔴 불안정 (0→2, 2→5, 5→10 에서 판정이 바뀐다)
```

Ruff 의 구별 성공은 사다리를 따라 1 에서 7 로 바뀐다 — 수는 작아도, 어느 값 하나를 고르면 그것이 결론이 된다.
결론이 실제로 갈린 곳은 두 군데다. 하나는 결과 3 의 「거꾸로」다 — `injected_defect` 의 가장 많은 판정이 slack 0 의
역전에서 2 부터 과잉지적으로 바뀐다 [실측 · 150쌍 · 생성물 「짝 판정 사다리」]. 다른 하나는 에이전트 비교였다:
60쌍 keep 비교에서 같은 짝 위의 claude − codex 차이는 slack 0 에서만
구별되고 2 부터 구간이 0 을 품었다 [실측 · 60쌍 · keep · `results/agent-archive/`]. 목표 150쌍 neutral 에서는
사다리 전체에서 방향과 판정이 같았다 [실측 · 150쌍 · 생성물 「차이의 매칭 민감도」]. 그 값은 벤치마크마다 다르고
대개 **공개되지 않는다.**

### 결과 6 — 룰 선택이 FP 도, **정의 간 편차도** 움직인다

같은 코드, 같은 채점자, 같은 코퍼스. `--ruff-select` 만 바꿨다.

| 룰 선택 | 음성 위 지적 | `provable_safety` FP | `injected_defect` FP | 두 정의의 편차 [실측 · 150쌍] |
|---|---:|---:|---:|:---:|
| `F,E` | 34 | 0 | 34 | 배수로 잴 수 없다 |
| `S` | 8 | 8 | 8 | **일치** |
| `ALL` | 777 | **17** | **777** | **45.7배** |

표는 생성물 [MEASUREMENTS.md](MEASUREMENTS.md) 「룰 선택 손잡이」에서 같은 계산으로 다시 나온다 — 다르면 테스트가 운다.

**이 표가 이 프로젝트의 논지를 한 줄 명령으로 보여 준다.** 보고되는 FP 율은 도구의 성질만큼이나 **측정자가 고른 설정**의
함수다. 🔴 **마지막 열이 더 중요하다** — 헤드라인의 배수는 그 자체가 `ALL` 에서만 성립한다.
보안 룰은 전부 근거 범위 안의 결함 주장이라 두 정의가 **정확히 일치하고**, `F,E` 의 지적은 거의 전부 관례 주장이라
한쪽은 판정 불가로, 다른 쪽은 오답으로 센다. 그래서 이 저장소의 모든 편차 주장은 룰 선택을 같이 적는다 —
「구별 성공률은 (리뷰어 × 채점자)의 성질」이라는 규율을 룰 선택 축에도 적용한 것이다.

### 결과 7 — 에이전트 층

Claude Code 와 Codex CLI 를 같은 하네스로 잰다 — CLI 를 호스트 설정에서 격리하고, 모델을 시작 때 한 번 고정하고,
출력 규격을 스키마로 강제하고, 실행마다 `RUN.json` 을 남긴다 ([DESIGN §7.10](DESIGN.md)). 원본 지적이 저장소에
실려 있어 **자격증명 없이 다시 채점된다** (`verify.sh` 가 그것을 대조한다).

목표 150쌍 · docstring neutral · 각 3회에서, 수집 전에 선언한 주 지표(`provable_safety` · slack 0 · 단일 실행 기대값의
같은 짝 위 차이)로 claude − codex 차이가 claude 쪽으로 구별됐고, 매칭 사다리 전체에서 판정이 같았다
[실측 · 150쌍 · 생성물 「에이전트 비교」]. 반복 횟수 · 주 지표 · 주장 규칙은 수집 전에 선언했다
([DESIGN §7.10b](DESIGN.md)).

![에이전트 비교 — 두 리뷰어의 기대값과 같은 짝 위의 차이 · slack 사다리 (생성물)](figures/agents.svg)

이 차이에는 조건이 붙는다 — **두 리뷰어가 같은 프롬프트 하나로 쟀고**(한계 7), **쌍을 Claude 가 썼고**(한계 6), 둘 다
**effort low** 다. 그리고 도구 · 권한이 제품마다 달라 **차이에는 모델과 제품이 함께 들어 있다** (생성물 「에이전트 비교」).
뒤의 것을 가르려고 Codex 가 쓴 쌍으로 같은 비교를 다시 한다 ([DESIGN §7.10d](DESIGN.md) · 진행 중).

## 왜 이 숫자를 믿을 수 있나

벤치마크 결과보다 **어떻게 검증했는지**가 본체다. 원칙을 규약으로 적지 않고 **코드와 테스트로** 박았다.

**음성은 「증명 가능하게 안전한」 코드다.** 결함 탐지 양성은 기성 벤치마크([c-CRAB](https://arxiv.org/abs/2603.23448) ·
[AACR-Bench](https://github.com/alibaba/aacr-bench))를 쓰고, 예산은 음성에 쓴다 — 버그처럼 보이지만 안전한 코드(decoy)를
한 쌍씩 쓰고, 안전한 이유를 서면으로 붙이고, 가드만 지운 진짜 버그 쌍둥이(twin)와 짝을 짓는다. 층 구성과 이유는
[DESIGN §3](DESIGN.md) 에 있다.

**라벨은 실행으로 반증한다.** 형식 검증은 근거가 *참인지* 볼 수 없다 — 형식 규칙을 전부 통과한 쌍의 안전 주장이 거짓이었던
적이 있다. 그래서 쌍마다 `proof.py` 가 결함을 **실현하려 시도**한다.

| 조건 | 무엇을 보장하는가 |
|---|---|
| `attack(decoy) is False` | 안전 근거가 참이다 |
| **`attack(twin) is True`** | **공격이 실제로 결함을 잡을 수 있다** — 없으면 `return False` 만 적어도 통과한다 |

면제 목록은 없다 — 「실행으로 확인 못 한다」던 면제 사유가 전부 틀린 것으로 드러났다. 공격을 못 쓰면 그 쌍은 싣지
않는다. 증명이 그럴듯한 약화를 전부 깨는지는 쌍의 `mutants.py` 가 본다. 그래도 **증명이 아니라 반증 시도**다 —
공격이 약하면 통과한다. 그래서 다른 모델 패밀리(Codex)에게 라벨을 감사시키고 재현된 문제를 고쳤다 (한계 6).

**판정 불가는 1급 판정이다.** 이 분야 문헌은 「아무도 코멘트를 안 달았다」(증거의 부재)를 「틀렸다」로 채점해
**사람이 놓친 진짜 버그를 False Positive 로 만든다.** 여기서는 안전 근거가 덮지 않는 지적은 `UNDECIDABLE` 이고,
Precision 분모에서 빠지며, **판정불가율을 같이 보고**한다.

**기억이 아니라 구조가 막는다.** 정답 라벨은 `eval/` 안에만 있고 런타임 레이어는 `eval/` 을 import 할 수 없다 —
레이어 그래프 테스트가 위반을 잡는다 ([`tests/architecture/test_layering.py`](../tests/architecture/test_layering.py)).
Claude 와 Codex 지적을 한 관측에 넣으면 출현 빈도가 교차모델 합의(조용한 투표)가 되므로 `MixedReviewerError` 가
타입 수준에서 거부한다.

**숨은 손잡이를 전부 공개한다.** 같은 코드 · 같은 도구여도 룰 선택 · 그룹핑 정책 · 매칭 허용 오차 · effort · 캐시 정책 ·
프롬프트를 바꾸면 숫자가 바뀐다. 전부 실행 매니페스트에 싣고, 매니페스트 없는 결과는 데이터베이스가 받지 않는다.
코퍼스의 **분류 구성비**도 손잡이다 — 코드도 도구도 채점자도 그대로 두고 구성비만 바꿔 집계 FPR 을 크게 움직일 수 있어,
생성물이 그 범위를 같이 낸다. 분류마다 다르다는 주장은 decoy 단위 순열 검정으로 판정하고, 분류당 목표 쌍 수를
수집 전에 선언해 optional stopping 을 막았다 ([DESIGN §3.5](DESIGN.md)).

**재현 가능한 출력이 아니라 재현 가능한 프로토콜이다.** Claude 4.7 이후 모델은 `temperature` 를 받지 않고(400)
Anthropic 에는 `seed` 가 없다 — 출력은 환원 불가능하게 확률적이다. 그래서 반복 횟수를 수집 전에 선언하고 오차막대를 내고
원본 응답을 전부 남긴다. 공정성 함정도 다룬다 — **캐싱 비대칭**(OpenAI 는 기본 활성화라 반복 호출 비용을 최대 90% 과소
보고한다 → 프롬프트 맨 앞에 nonce)과 **effort 기본값 비대칭**(모델마다 기본값이 달라 「기본값끼리」는 한쪽에 추론 예산을
더 준다 → 모든 호출에 effort 를 명시).

**주 지표에는 LLM 판정자를 쓰지 않는다.** 자기선호 편향이 Claude vs Codex 비교를 무효화하고, 코드 도메인의 판정자
일치도는 전 도메인 최악이다(pairwise κ 0.159). 보조 민감도 하나(FP 구간 지적의 재판정)에만 리뷰어를 가린 Claude 판정자
둘을 썼고, 그 한계를 한계 6 에 적는다.

**가드는 깨뜨려 본 뒤에만 있다고 말한다.** 테스트가 통과하는 것은 「가드가 있다」의 증거가 아니다.
`./scripts/falsify.sh` 가 불변식을 일부러 깨고 가드가 우는지 본다 — 공허한 가드를 실제로 그렇게 잡았다.

## ⚠️ 이 프로젝트가 재지 *못하는* 것

포트폴리오용이라고 해서 과대포장하지 않기 위해, 한계를 먼저 적는다.

**1. 결함 탐지는 리뷰의 1/8 이다.**
실제 리뷰 코멘트 중 결함 지적은 **14% 뿐**이다 ([Bacchelli & Bird](https://sback.it/publications/icse2013.pdf), 570건
카드분류). 최대 범주는 *코드 개선* 29%. 결함 탐지만 채점하는 벤치마크는 **리뷰어가 하는 일의 8분의 1** 을 재고 있다.

**2. 일치와 유용은 다르다.**
c-CRAB 에서 정답 테스트를 통과한 건 20–32% 인데, 사람이 유용하다고 평가한 건 **84%** 였다.
이 둘을 섞는 게 이 분야 숫자가 과대포장되는 가장 흔한 경로다.

**3. 50:50 세트의 precision 은 프로덕션 precision 이 아니다.**
그래서 양성 층(A · B)이 생기면 `(TPR, FPR)` 로 보고한다 — 누구나 자기 유병률에서 재유도할 수 있게. 지금은 음성(D층)
위의 물림 비율과 짝 판정만 낸다.

**4. 오염 내성은 층마다 다르다.**
층은 정답이 어디서 오는가로 나눈다 — **A** 변이 주입 · **B** 짝지은 수정 후 코드 · **C** 결함 없는 실제 PR ·
**D** 직접 쓴 decoy ([DESIGN §3.2](DESIGN.md)). A·D 층은 면역(직접 생성/작성), **B·C 층은 아니다.**

**5. A층(변이 주입)은 현실적이지 않다.**
Google 실측으로 변이체의 **85%를 개발자가 무익하다고 분류**했고, 실제 결함은 3–4 토큰을 바꾸는데 변이체는 1 토큰이며,
실제 결함의 **17%는 어떤 변이체와도 짝지어지지 않는다.** → **recall 바닥선으로만** 쓰고 현실성을 주장하지 않는다.

**6. D층 정답은 측정 대상 한쪽과 같은 패밀리가 썼다.**
decoy 는 Claude 가 쓰고(모든 커밋에 공동 작성자로 남아 있다) 독립 검토도 Claude 가 한다. 생성기가 만든 벤치마크에서는
그 생성기의 점수가 부풀고, 부푼 몫의 67–80% 가 **틀린 정답 라벨**이었다 ([Silencer](https://arxiv.org/abs/2505.20738) —
수학 · 언어 이해, 코드는 다루지 않았다). 같은 패밀리의 맹점에 틀린 라벨이 남으면 Claude 리뷰어에게는 정답, Codex 에게는 FP 로
채점되어 claude − codex 차이가 Claude 쪽으로 기운다. 실행 반증이 그 통로를 좁히지만 닫지는 못한다 — 반증은 쓴 쪽이 떠올린
공격만 친다. Codex 가 쌍을 감사하자 위협 모델 안의 라벨 문제가 재현된 쌍이 나왔고 [실측 · 14쌍 파일럿 3/14 · 95% 구간
7.6~47.6% · 나머지 102쌍 31/102 · 22.3~39.9%], 코드를 고쳐야 하는 쌍은 측정 전에 고치고 다시 쟀다
([DESIGN §9 의 5](DESIGN.md)). 측정 뒤 FP 구간 지적을 리뷰어를 가린 채 두 번 재판정했더니 맞는 지적은 하나(claude)였고,
그것을 판정 불가로 두면 차이가 조금 커질 뿐 판정은 같다 [실측 · 150쌍 · `results/fp-span-adjudication/`]. 다만 그 재판정도
Claude 가 했다 — 이 한계를 닫으려면 다른 패밀리의 판정이 필요하다. Codex 가 쓴 쌍에서 같은 비교를 다시 하는
선언은 [DESIGN §7.10d](DESIGN.md) 다 — 그 쌍에서는 같은 통로가 Codex 를 돕는다.

**7. 에이전트 비교는 프롬프트 하나에서의 차이다.**
두 리뷰어에게 같은 프롬프트를 줬다 (두 묶음의 `prompt_hash` 가 같다). 프롬프트 포맷만으로 정확도가 크게 움직인다는 보고가
있어 [소스: Sclar et al.], 다른 프롬프트에서도 같은 차이가 나오는지는 재지 않았다. 「프롬프트 1종이면 발표하지 않는다」는
설계 조건은 모델 API 층의 절대 성능 주장을 위해 썼다 — 에이전트 비교는 같은 프롬프트 위의 차이로만 주장한다
([DESIGN §8.3](DESIGN.md)).

## 기술 스택 — 선택과 이유

| 영역 | 선택 | 이유 |
|---|---|---|
| 런타임 | Python **≥3.14** · **uv** | — |
| 정적분석 | **Ruff** (JSON) + **mypy** (JSON Lines) | 둘 다 subprocess · **호스트 설정과 캐시를 격리** · 일괄 분석 |
| AST · 도달성 | stdlib `ast` | 의존성 0 · 도달성은 파일 안 함수 단위 참조까지 (아래) |
| LLM | `anthropic` · `openai` **직접** | 래퍼를 쓰지 않는다 (아래) |
| 저장 | SQLite | 매니페스트 없는 결과를 외래키가 거부한다 |
| 가져오기 | SARIF 2.1.0 · bandit JSON · 에이전트 JSON | 버린 지적도 이유와 함께 센다 |
| 구조화 출력 | `output_config.format` / `strict:true` | 강제 tool use 는 최신 Claude 에서 **400** |

**LiteLLM 같은 래퍼를 쓰지 않는 이유.** 래퍼들은 전부 **OpenAI 모양의 `usage` 객체로 정규화**하는데 프로바이더마다
「토큰」의 정의가 다르다 — Anthropic 의 `input_tokens` 는 캐시 토큰을 **제외**하고 OpenAI 는 **포함**한다. 정규화 레이어
자체가 손실 지점이고, 관련 이슈들이 **미해결로 종료**됐다 (LiteLLM #23731 · PydanticAI #4364 · LangChain #32818).
출력이 토큰 수와 지연시간 그 자체인 벤치마크에서는 실격 사유다 → `Protocol` 하나 위에 얇은 어댑터 둘, `max_retries=0`,
**모든 호출의 원본 응답을 그대로 영속화.**

**측정 도구는 호스트 환경에서 격리한다.** 측정 도구가 실행되는 레포의 설정을 주워 오면 같은 코퍼스가 레포마다 다른 숫자를
낸다 — 실제로 mypy 가 이 레포의 `strict = true` 를 주워 오면서 매니페스트에는 `strict=False` 라고 거짓을 적었다.
→ mypy `--config-file=/dev/null` · `--no-incremental` · `--cache-dir=/dev/null`, Ruff `--isolated`, 두 도구 모두 코퍼스의
파이썬 판을 명시한다. 테스트가 「일괄 == 개별」을 강제해서 속도 최적화가 숫자를 바꾸지 못하게 한다.

**파이썬 호출그래프 도구는 전멸했다** — PyCG · JarvisCG · Pyre/Pysa 가 전부 아카이브됐다. 그래서 v1 의 도달성은 파일 안
함수 단위 참조까지만 보고, 파일 밖 · 분기 단위 · 동적 호출은 못 본다고 검증자 독스트링에 적는다.

구조 · 확장점 · 레이어 규칙은 [DESIGN §6](DESIGN.md) 에 있다 (패키지 트리는 테스트가 실제 모듈과 대조한다).

## 명령 모음

```bash
# ── 준비 상태 ───────────────────────────────────────────
uv run codeproof doctor

# ── 측정 (자격증명 불필요) ──────────────────────────────
uv run codeproof measure --analyzers ruff,mypy              # 기본 룰 선택
uv run codeproof measure --analyzers ruff --ruff-select ALL # 손잡이를 바꿔 본다 (결과 6)
uv run codeproof history --limit 5                          # 저장된 실행
uv run codeproof history --repro <config-hash>              # 같은 설정끼리 재현성

# ── 측정값 문서 ─────────────────────────────────────────
uv run codeproof report                  # docs/MEASUREMENTS.md 와 그림(docs/figures)을 만든다
uv run codeproof report --check          # 낡았으면 exit 1 (CI 용)

# ── 코퍼스 ──────────────────────────────────────────────
uv run codeproof decoy validate --strict # 형식 13규칙
uv run codeproof decoy stats             # 미끼가 실제로 물리는지
uv run codeproof decoy mutants           # 쌍마다 실린 변이로 증명을 다시 깬다 (경쟁 변이는 30번)
uv run pytest tests/corpus/test_proofs.py  # 안전 근거가 참인지 — 쌍마다 proof.py 를 돌린다

# ── 외부 리뷰어 가져오기 (자격증명 불필요) ──────────────
uv run codeproof import --from out --name semgrep --identity "1.2.3"           # SARIF
uv run codeproof import --from out --name bandit --format bandit --identity "1.8"

# ── 에이전트 (각 CLI 로그인 필요) — 격리 · 모델 고정 · 기록은 실행기가 한다 ──
uv run codeproof export --out agent-in --docstrings neutral
./scripts/review-with-agent.sh codex agent-in codex-out --effort low --runs 3
uv run codeproof import --from codex-out --name codex-cli --kind agent   # RUN.json 이 정본
uv run codeproof pack --from codex-out --out results/agent/codex-cli --runs 3

# ── 모델 API (자격증명 필요) ────────────────────────────
uv run codeproof eval --providers claude,codex --effort high --samples 8
```

반복 횟수(`--runs`)는 결과를 보기 전에 선언한다 — 실행기 · `pack` · 재생 규칙은 [DESIGN §7.10](DESIGN.md),
에이전트 층을 다시 채점하는 절차는 [docs/VERIFY.md](VERIFY.md) T6.
`--help` 에 올린 명령은 전부 실제로 동작하며, 테스트가 그것을 강제한다. 「PR 하나를 리뷰하는 명령」은 일부러 만들지
않았다 — 이 저장소의 논지는 오프라인 측정 경로이고, 안 되는 것을 `--help` 에 올려 두면 쓰는 사람이 속는다.

## 주요 참고문헌

**벤치마크** — [SWRBench](https://arxiv.org/abs/2509.01494) ·
[CR-Bench](https://arxiv.org/abs/2603.11078) ·
[c-CRAB](https://arxiv.org/abs/2603.23448) ·
[CRScore](https://arxiv.org/abs/2409.19801) ·
[Martian](https://github.com/withmartian/code-review-benchmark)

**음성 통제** — [SQuAD 2.0](https://arxiv.org/abs/1806.03822) ·
[Contrast Sets](https://arxiv.org/abs/2004.02709) ·
[SecLLMHolmes](https://arxiv.org/abs/2312.12575) ·
[PrimeVul](https://arxiv.org/abs/2403.18624) ·
[OWASP Benchmark](https://owasp.org/www-project-benchmark/)

**판정자 신뢰도** — [Reliability without Validity](https://arxiv.org/html/2606.19544v1) ·
[Self-Preference](https://arxiv.org/abs/2404.13076) ·
[When LLMs Agree](https://arxiv.org/abs/2607.08065)

**측정 민감도** — [Sclar et al.](https://arxiv.org/abs/2310.11324) ·
[Leaderboard Illusion](https://arxiv.org/abs/2504.20879)

**리뷰 실증** — [Bacchelli & Bird](https://sback.it/publications/icse2013.pdf) ·
[Tricorder](https://research.google.com/pubs/archive/43322.pdf) ·
[Sadowski et al.](https://sback.it/publications/icse2018seip.pdf)
