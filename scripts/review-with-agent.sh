#!/usr/bin/env bash
#
# 에이전트 CLI 로 코퍼스를 리뷰시킨다 — **API 키 없이 모델 숫자를 내는 경로**.
#
#   codeproof export --out agent-in
#   scripts/review-with-agent.sh claude agent-in agent-out --effort low
#   codeproof import --from agent-out --kind agent --name claude-code
#       (포맷 · identity · effort 는 이 스크립트가 남긴 RUN.json 에서 읽는다)
#
# 🔴 샘플마다 **새 임시 디렉터리**에 복사해서 돌린다 (C1). 내보낸 디렉터리에서
#    그냥 돌리면 옆 샘플과 그 이름(`#twin`)이 보인다. 상자 이름도 라벨이라
#    무작위다. 프롬프트는 파일이 아니라 인자로 준다 - 상자 안 파일이 늘면
#    「제시된 파일」이 달라진다.
#
# 🔴 에이전트를 **호스트 설정에서 격리한다** (C1a 와 같은 종류).
#    [실측] 격리 없이 돌린 `claude -p` 는 전역 CLAUDE.md · 플러그인 · 훅 · MCP ·
#    권한 모드(auto)까지 싣고 리뷰했다. codex 는 사용자 config 의 MCP 와
#    effort(max)를 물려받았다. 같은 코퍼스가 기계마다 다른 숫자를 낸다.
#      claude  --safe-mode --strict-mcp-config --no-session-persistence
#              --permission-mode dontAsk --tools Read,Grep,Glob
#      codex   --ignore-user-config --ignore-rules --ephemeral --sandbox read-only
#      gemini  샘플마다 새 HOME(로그인 파일만 연결) + 시스템 설정 파일(우선순위 최상위)로
#              도구 read_file · grep_search · glob · 텔레메트리 · 자동 업데이트 · 추론 수준을 강제,
#              --approval-mode plan --skip-trust (신뢰하지 않은 폴더에서는 plan 이 default 로
#              바뀐다 [실측]). 시스템 설정은 권한이 넓은 폴더에 두면 무시된다 [실측] - 700 폴더.
#              기억 도구가 HOME 에 쓸 수 있어 HOME 을 샘플끼리 나누지 않는다.
#    ⚠ 권한이 비대칭이다. codex 는 read-only 샌드박스 안에서 명령을 **실행**할 수
#      있고 claude 는 읽기 도구만 있다 - 제품의 도구가 다르다. RUN.json 에 적는다.
#    ⚠ `--bare` 는 OAuth 를 읽지 않아 구독 로그인에서는 실패한다.
#
# 🔴 effort 는 필수다 (D4). [실측] 「제품 기본값끼리」라고 여긴 비교가 사실은
#    개인 설정끼리였다 (claude xhigh · codex max). codex gpt-6-astra 의 제품
#    기본값은 low 다 - 「기본값」은 비교 조건이 될 수 없다.
#
# 🔴 모델은 **실행 시작 때 한 번** 해석해 모든 호출에 고정하고 RUN.json 에 적는다
#    (D6). --model 을 생략하면 벤더가 정한 최상위 모델이다:
#      claude  `--model best` 로 한 번 호출해 응답의 modelUsage 에서 실제 ID
#      codex   `codex debug models` 의 공개 모델 중 priority 최상위
#      gemini  카탈로그 명령이 없다 - agent-models.json 의 기준(또는 --model)으로 한 번 불러
#              그 모델이 실제로 답하는지(result 의 stats.models) 본다
#    그 결과가 agent-models.json 에 받아들인 모델과 다르면 **멈춘다** (DESIGN §7.10) -
#    ACCEPT_MODEL_CHANGE=1 로 기준을 옮기거나 --model 로 명시한다. 해석된 모델의
#    설명(codex 는 카탈로그 설명)은 RUN.json 의 model_note 에 남는다.
#    호출마다 해석하면 실행 도중 새 모델이 나올 때 한 실행이 두 모델로 갈린다.
#    claude 는 호출마다 modelUsage 를 대조해 다른 모델이 답했으면 실패로 센다.
#
# 🔴 출력 스키마는 **model_api 와 같은 것**을 강제한다 (export 의 SCHEMA.json).
#
# 🔴 원본 응답을 전부 남긴다 (F8) - 성공한 호출도, 실패한 시도도 raw/ 에.
#    codex 의 JSONL 에는 실행한 명령이 전부 남아 상자 밖 접근을 사후에 감사한다.
#
# 이어서 돌릴 수 있다 - 이미 있는 출력은 건너뛴다. 🔴 단 RUN.json 의 설정과
# 다르면 거부한다. 한 출력 디렉터리에 두 설정이 섞이면 그건 한 실행이 아니다.
#
# ⚠ 크레딧이 한정이면 --runs 를 1씩 올려 이어 돈다 (1 → 2 → … → 8). 이 루프는 샘플마다
#   N회를 다 돌고 넘어가서 --runs 8 을 바로 주면 충전분이 몇 샘플에 몰리고, N회가 모자란
#   샘플은 채점 밖이다 (F6). [실측] 9/30 의 --runs 8 세션은 83호출을 12샘플의 2~8회차에 썼고,
#   그동안 42샘플은 1회차도 없었다.
#   비용은 입력이 지배한다 [실측 · codex 203호출: 호출당 입력 약 31K · 캐시 67% · 출력 약 130 ·
#   추론 약 18]. effort 로는 줄지 않는다 - astra 는 low 가 가장 낮은 단계다.
#
# 🔴 돌고 있는 동안 이 파일과 agent_output.py 를 **제자리에서 고치지 않는다.**
#    bash 는 스크립트를 실행하면서 읽고, 도우미는 호출마다 다시 읽힌다.
#    새 파일에 쓰고 mv 로 바꾼다 (열린 fd 는 옛 inode 를 계속 읽는다).
#
# bash 3.2 호환 (mapfile · 연관 배열 없음).

set -uo pipefail

RED=$'\033[31m'; GRN=$'\033[32m'; DIM=$'\033[2m'; BLD=$'\033[1m'; OFF=$'\033[0m'
[[ -t 1 ]] || { RED=""; GRN=""; DIM=""; BLD=""; OFF=""; }

RUNNER_VERSION=3   # 3: MANIFEST 의 docstring 손잡이를 RUN.json 에 싣는다 (리뷰 호출은 2 와 같다)
#   회차마다 잰 코드의 지문 옆 파일을 남기는 것은 판을 올리지 않는다 - 리뷰 호출 · 입력이 같고,
#   올리면 같은 조건의 출력에 이어 쓰지 못한다. 그 뒤의 세션은 sessions 의 runner_sha 가 가른다.
HERE=$(cd "$(dirname "$0")" && pwd)
HELPER="$HERE/agent_output.py"

usage() {
  cat >&2 <<USAGE
용법: $0 <claude|codex|gemini> <export-dir> <out-dir> --effort E [옵션]

  --effort E   🔴 필수 (D4). low · medium · high · xhigh · max (gemini 는 low · high)
  --model M    모델 고정. 생략하면 벤더의 최상위 모델을 시작 때 한 번 해석한다
  --runs N     샘플당 반복 횟수 (기본 1). <sample_id>.<i>.json 으로 쓴다
  --limit N    앞에서 N개 샘플만 (파일럿용)
  --timeout S  한 건 제한시간 (기본 240초)

🔴 n=1 로는 변동을 말할 수 없다 (F8). 파일럿이 아니면 --runs 를 올린다.
USAGE
  exit 2
}

die() { echo "${RED}$*${OFF}" >&2; exit 2; }

[[ $# -lt 3 ]] && usage
AGENT=$1; IN=$2; OUT=$3; shift 3
RUNS=1; LIMIT=0; MODEL=""; EFFORT=""; TIMEOUT=240
while [[ $# -gt 0 ]]; do
  case $1 in
    --effort)  EFFORT=$2; shift 2 ;;
    --model)   MODEL=$2; shift 2 ;;
    --runs)    RUNS=$2; shift 2 ;;
    --limit)   LIMIT=$2; shift 2 ;;
    --timeout) TIMEOUT=$2; shift 2 ;;
    *) echo "${RED}모르는 옵션: $1${OFF}" >&2; usage ;;
  esac
done

case $AGENT in claude|codex|gemini) ;; *) die "모르는 에이전트: $AGENT (claude | codex | gemini)" ;; esac
[[ -n $EFFORT ]] || die "--effort 는 필수다 (D4) - 없으면 개인 설정의 effort 를 물려받는다"
for f in PROMPT.md SCHEMA.json MANIFEST.json; do
  [[ -f "$IN/$f" ]] || die "$IN/$f 가 없다 - codeproof export 를 (다시) 돌린다"
done
command -v "$AGENT" > /dev/null || die "$AGENT 를 찾을 수 없다"
command -v python3 > /dev/null || die "python3 를 찾을 수 없다"
# 🔴 macOS 에는 GNU timeout 이 없다 [실측: CI macOS] - 없으면 perl 의 alarm 으로 같은 상한을 건다.
#    면접관 경로(codeproof review --agent)가 이 실행기를 부르므로 coreutils 를 요구하지 않는다.
#    alarm 은 exec 뒤에도 남아 제한시간에 그 프로세스를 SIGALRM 으로 끝낸다 [실측: bash 3.2].
#    ⚠ GNU timeout 과 달리 그 프로세스의 자식까지 끝내지는 않는다 - 제한시간은 운영 값이다 (지문 밖).
command -v timeout > /dev/null \
  || timeout() { perl -e 'alarm shift; exec { $ARGV[0] } @ARGV or die "exec $ARGV[0]: $!\n"' "$@"; }

IN=$(cd "$IN" && pwd)
mkdir -p "$OUT/raw" || die "$OUT 를 만들 수 없다"
OUT=$(cd "$OUT" && pwd)
PROMPT=$(cat "$IN/PROMPT.md")
SCHEMA_FILE="$IN/SCHEMA.json"
SCHEMA=$(cat "$SCHEMA_FILE")
RUN_JSON="$OUT/RUN.json"

# 🔴 이 맥은 AC 에서도 유휴 1분에 잔다 - 이 스크립트가 도는 동안만 깨워 둔다.
command -v caffeinate > /dev/null && { caffeinate -i -s -w $$ & }

manifest() {
  python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))[sys.argv[2]])' "$IN/MANIFEST.json" "$1"
}

# 🔴 입력 코드가 달라지는 손잡이 (DESIGN §7.10c). 없으면 손잡이 이전의 내보내기다 -
#    빈 값으로 기록하면 keep 과 neutral 이 같은 설정으로 읽힌다.
DOCSTRINGS=$(manifest docstrings 2>/dev/null)
[[ -n $DOCSTRINGS ]] || die "$IN/MANIFEST.json 에 docstrings 가 없다 - codeproof export 를 다시 돌린다"

# 🔴 회차마다 잰 코드의 지문을 <sample_id>.<run>.digest 로 남긴다 - pack 이 지금 코드와 견준다
#    (DESIGN §9 의 5). 지문 없는 내보내기로는 돌지 않는다 - 그 출력은 pack 이 거부한다.
python3 "$HELPER" digests "$IN/MANIFEST.json" "$IN" > /dev/null \
  || die "$IN/MANIFEST.json 에 샘플 지문이 없다 - codeproof export 를 다시 돌린다"

cli_version() {
  "$AGENT" --version 2>/dev/null | head -1 | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+' | head -1
}

case $AGENT in
  claude)
    NAME=claude-code
    ISOLATION="safe-mode,strict-mcp-config,no-session-persistence,DISABLE_AUTOUPDATER=1"
    PERMISSION="dontAsk;tools=Read,Grep,Glob"
    ;;
  codex)
    NAME=codex-cli
    ISOLATION="ignore-user-config,ignore-rules,ephemeral"
    PERMISSION="sandbox=read-only;exec=allowed"
    ;;
  gemini)
    NAME=gemini-cli
    ISOLATION="home=per-sample(oauth-only),system-settings,skip-trust,no-telemetry,no-auto-update"
    PERMISSION="approval=plan;tools=read_file,grep_search,glob"
    # 로그인은 사용자의 것을 쓴다 - 파일을 복사하지 않고 링크만 건다
    GEMINI_LOGIN="$HOME/.gemini"
    [[ -f "$GEMINI_LOGIN/oauth_creds.json" ]] \
      || die "gemini 에 로그인돼 있지 않다 - 터미널에서 gemini 를 한 번 실행해 Google 계정으로 로그인한다"
    case $EFFORT in
      low) THINK=LOW ;; high) THINK=HIGH ;;
      *) die "gemini 의 effort 는 low · high 뿐이다 (CLI 의 thinkingLevel) - $EFFORT" ;;
    esac
    ;;
esac

# gemini: 샘플마다 새 HOME - 로그인 파일만 링크하고 측정 조건은 시스템 설정 하나로 강제한다
gemini_home() {  # $1=새 HOME  $2=고정할 모델
  local gh=$1 f
  mkdir -p "$gh/.gemini" "$gh/system" && chmod 700 "$gh" "$gh/system" || return 1
  for f in oauth_creds.json google_accounts.json; do
    [[ -f "$GEMINI_LOGIN/$f" ]] && ln -s "$GEMINI_LOGIN/$f" "$gh/.gemini/$f"
  done
  python3 "$HELPER" gemini-settings "$2" "$THINK" > "$gh/system/settings.json"
}

# gemini 한 건 - timeout 은 셸 함수를 못 돌리므로 환경을 앞에 두고 CLI 를 직접 부른다
GEMINI_FLAGS=(-o stream-json --approval-mode plan --skip-trust)

# ── 모델 해석 (시작 때 한 번) ───────────────────────────────
resolve_model() {
  case $AGENT in
    claude)
      local box probe
      box=$(mktemp -d)
      probe="$OUT/raw/_resolve"
      ( cd "$box" && DISABLE_AUTOUPDATER=1 timeout 120 claude -p 'Reply with the single word: ok' \
          --model "${MODEL:-best}" --effort low --safe-mode --strict-mcp-config \
          --no-session-persistence --permission-mode dontAsk --tools "" \
          --output-format json < /dev/null > "$probe.claude.json" 2> "$probe.err" )
      rm -rf "$box"
      python3 "$HELPER" resolve-claude "$probe.claude.json"
      ;;
    codex)
      # 해석에 쓴 카탈로그를 남긴다 - 같은 CLI 버전에서도 원격 카탈로그는 바뀐다.
      timeout 120 codex debug models 2> "$OUT/raw/_resolve.err" > "$OUT/raw/_resolve.codex.json" \
        || return 1
      python3 "$HELPER" resolve-codex "$EFFORT" ${MODEL:+"$MODEL"} < "$OUT/raw/_resolve.codex.json"
      ;;
    gemini)
      local want box gh
      want=${MODEL:-$(python3 "$HELPER" accepted-model "$HERE/agent-models.json" gemini)}
      [[ -n $want ]] || { echo "gemini 는 최상위 모델을 알려 주는 명령이 없다 - --model 로 정한다" >&2; return 1; }
      box=$(mktemp -d); gh=$(mktemp -d)
      printf '%s\n' "$box" > "$OUT/raw/_resolve.box"   # 감사가 상자 안 경로를 밖으로 세지 않게
      gemini_home "$gh" "$want" || return 1
      ( cd "$box" && HOME="$gh" GEMINI_CLI_SYSTEM_SETTINGS_PATH="$gh/system/settings.json" \
          NO_BROWSER=true timeout 120 gemini -p 'Reply with the single word: ok' -m "$want" \
          "${GEMINI_FLAGS[@]}" < /dev/null > "$OUT/raw/_resolve.gemini.jsonl" 2> "$OUT/raw/_resolve.err" )
      rm -rf "$box" "$gh"
      python3 "$HELPER" resolve-gemini "$OUT/raw/_resolve.gemini.jsonl" "$want"
      ;;
  esac
}

CLI_VERSION=$(cli_version)
[[ -n $CLI_VERSION ]] || die "$AGENT --version 에서 버전을 읽지 못했다"
REQUESTED=${MODEL:-top}
NOTE=""   # 이어 쓸 때는 해석하지 않는다 - 첫 세션이 남긴 model_note 가 그대로 남는다

if [[ -f $RUN_JSON ]]; then
  # 이어서 돌린다 - 처음 고정한 모델을 그대로 쓴다. 다시 해석하면 그 사이
  # 나온 새 모델이 끼어들 수 있다.
  RESOLVED=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["model"])' "$RUN_JSON") \
    || die "$RUN_JSON 을 읽지 못했다"
else
  printf '%s모델 해석 중 (%s)...%s\n' "$DIM" "$REQUESTED" "$OFF"
  RESOLVED=$(resolve_model) || die "모델을 해석하지 못했다 - $OUT/raw/_resolve.* 를 본다"
  [[ -n $RESOLVED ]] || die "모델을 해석하지 못했다 (빈 값)"
  case $AGENT in
    codex)  NOTE=$(python3 "$HELPER" describe-codex "$RESOLVED" "$OUT/raw/_resolve.codex.json") ;;
    gemini) NOTE="${MODEL:+--model 지정}${MODEL:-기준 모델} · 카탈로그 명령 없음" ;;
    *)      NOTE="${MODEL:-best} 별칭" ;;
  esac
  # 🔴 벤더 최상위가 지난번에 받아들인 모델과 다르면 멈춘다 - 조용히 따라가지 않는다 (DESIGN §7.10).
  #    --model 로 명시했으면 사람이 고른 것이므로 보지 않는다.
  if [[ -z $MODEL ]]; then
    reason=$(python3 "$HELPER" check-model "$HERE/agent-models.json" "$AGENT" "$RESOLVED" "$NOTE") \
      || die "🔴 ${reason:-기준 모델을 확인하지 못했다 - $HERE/agent-models.json}"
  fi
fi
IDENTITY="$NAME $CLI_VERSION · $RESOLVED · effort=$EFFORT"

# 이 출력을 만든 실행기의 커밋 - 세션마다 RUN.json 의 sessions 에 남는다.
RUNNER_SHA=$(git -C "$HERE/.." rev-parse --short=12 HEAD 2>/dev/null || echo unknown)
git -C "$HERE/.." diff --quiet -- scripts src 2>/dev/null || RUNNER_SHA="$RUNNER_SHA-dirty"

diffs=$(python3 "$HELPER" record "$RUN_JSON" \
    runner_version="$RUNNER_VERSION" agent="$AGENT" cli_version="$CLI_VERSION" \
    model_requested="$REQUESTED" model="$RESOLVED" model_note="$NOTE" effort="$EFFORT" runs="$RUNS" \
    isolation="$ISOLATION" permission="$PERMISSION" \
    prompt_hash="$(manifest prompt_hash)" instruction_hash="$(manifest instruction_hash)" \
    schema_hash="$(manifest schema_hash)" docstrings="$DOCSTRINGS" identity="$IDENTITY" \
    timeout_s="$TIMEOUT" runner_sha="$RUNNER_SHA" started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)")
case $? in
  0) ;;
  3)
    echo "${RED}🔴 $RUN_JSON 의 설정과 다르다 - 이어 쓰지 않는다 (섞이면 한 실행이 아니다):${OFF}" >&2
    printf '%s\n' "$diffs" | sed 's/^/   /' >&2
    echo "   새 출력 디렉터리를 쓴다." >&2
    exit 3 ;;
  *) die "$RUN_JSON 을 기록하지 못했다" ;;
esac

# ── 한 건 실행: 원본을 raw/ 에 남긴다 ───────────────────────
run_agent() {  # $1=상자  $2=원본 접두사
  local box=$1 rp=$2
  printf '%s\n' "$box" > "$rp.box"
  case $AGENT in
    claude)
      ( cd "$box" && DISABLE_AUTOUPDATER=1 timeout "$TIMEOUT" claude -p "$PROMPT" \
          --model "$RESOLVED" --effort "$EFFORT" \
          --safe-mode --strict-mcp-config --no-session-persistence \
          --permission-mode dontAsk --tools Read,Grep,Glob \
          --output-format json --json-schema "$SCHEMA" \
          < /dev/null > "$rp.claude.json" 2> "$rp.err" ) ;;
    codex)
      ( cd "$box" && timeout "$TIMEOUT" codex exec \
          --ignore-user-config --ignore-rules --ephemeral --skip-git-repo-check \
          --sandbox read-only --color never \
          -m "$RESOLVED" -c "model_reasoning_effort=\"$EFFORT\"" \
          --output-schema "$SCHEMA_FILE" --json -o "$rp.last.json" \
          "$PROMPT" < /dev/null > "$rp.jsonl" 2> "$rp.err" ) ;;
    gemini)
      # ⚠ 출력 스키마를 강제하는 플래그가 없다 [실측: --help] - 프롬프트의 규격으로 받고
      #   도우미가 마지막 findings 객체를 찾는다 (claude · codex 와 조건이 다르다 - RUN.json 의 permission)
      local gh; gh=$(mktemp -d)
      gemini_home "$gh" "$RESOLVED" || { echo "gemini HOME 을 만들지 못했다" > "$rp.err"; return; }
      ( cd "$box" && HOME="$gh" GEMINI_CLI_SYSTEM_SETTINGS_PATH="$gh/system/settings.json" \
          NO_BROWSER=true timeout "$TIMEOUT" gemini -p "$PROMPT" -m "$RESOLVED" \
          "${GEMINI_FLAGS[@]}" < /dev/null > "$rp.gemini.jsonl" 2> "$rp.err" )
      rm -rf "$gh" ;;
  esac
}

BOXES=()
while IFS= read -r d; do BOXES+=("$d"); done \
  < <(find "$IN" -mindepth 1 -maxdepth 1 -type d | sort)
if [[ $LIMIT -gt 0 && ${#BOXES[@]} -gt $LIMIT ]]; then
  BOXES=("${BOXES[@]:0:$LIMIT}")
fi
[[ ${#BOXES[@]} -gt 0 ]] || die "$IN 에 샘플 디렉터리가 없다"

TOTAL=$(( ${#BOXES[@]} * RUNS ))
printf '%s%s%s · %s · effort=%s · 샘플 %d개 × %d회 = %d건 · 제한 %ds\n' \
  "$BLD" "$NAME $CLI_VERSION" "$OFF" "$RESOLVED" "$EFFORT" "${#BOXES[@]}" "$RUNS" "$TOTAL" "$TIMEOUT"
printf '%s격리: %s · 권한: %s · docstring: %s%s\n' "$DIM" "$ISOLATION" "$PERMISSION" "$DOCSTRINGS" "$OFF"
[[ $RUNS -eq 1 ]] && printf '%s⚠ n=1 — 변동을 말할 수 없다 (F8). 파일럿으로만 쓴다.%s\n' "$DIM" "$OFF"
echo

DONE=0; SKIP=0; FAIL=0; STREAK=0; I=0
MAX_STREAK=5
START=$(date +%s)

for box in "${BOXES[@]}"; do
  sid=$(basename "$box")
  for ((r = 0; r < RUNS; r++)); do
    ((I++))
    dest="$OUT/$sid.$r.json"
    if [[ -s "$dest" ]]; then ((SKIP++)); continue; fi

    # 실패한 시도도 남긴다 - 거부·시간초과·한도 초과도 데이터다 (D5)
    a=0; while [[ -e "$OUT/raw/$sid.$r.a$a.err" ]]; do ((a++)); done
    rp="$OUT/raw/$sid.$r.a$a"

    tmp=$(mktemp -d)                       # 🔴 무작위 이름 - 상자 이름도 라벨이다
    find "$box" -mindepth 1 -maxdepth 1 -exec cp -R {} "$tmp/" \;
    run_agent "$tmp" "$rp"
    rm -rf "$tmp"

    if info=$(python3 "$HELPER" extract "$AGENT" "$rp" "$RESOLVED" "$dest" \
        "$IN/MANIFEST.json" "$sid" 2>> "$rp.err"); then
      printf '  [%3d/%3d] %s%-46s%s 지적 %s\n' "$I" "$TOTAL" "$DIM" "$sid" "$OFF" "$info"
      ((DONE++)); STREAK=0
    else
      printf '  [%3d/%3d] %s%-46s 실패%s %s\n' "$I" "$TOTAL" "$RED" "$sid" "$OFF" \
        "$(tail -1 "$rp.err" 2>/dev/null | cut -c1-120)"
      ((FAIL++)); ((STREAK++))
      if [[ $STREAK -ge $MAX_STREAK ]]; then
        echo "${RED}연속 ${STREAK}건 실패 - 한도·인증 문제일 수 있다. 멈춘다. raw/ 를 보고 다시 돌린다.${OFF}" >&2
        break 2
      fi
    fi
  done
done

ELAPSED=$(( $(date +%s) - START ))
END_VERSION=$(cli_version)
AUDIT=$(python3 "$HELPER" audit "$OUT")
python3 "$HELPER" finish "$RUN_JSON" cli_version_end="$END_VERSION" \
  finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)" audit="$AUDIT" > /dev/null

printf '\n%s완료%s %d건 · 건너뜀 %d · 실패 %d · %d분 %d초\n' \
  "$GRN" "$OFF" "$DONE" "$SKIP" "$FAIL" $((ELAPSED/60)) $((ELAPSED%60))
[[ $END_VERSION != "$CLI_VERSION" ]] && \
  echo "${RED}⚠ 실행 중 CLI 버전이 바뀌었다: $CLI_VERSION → $END_VERSION${OFF}" >&2
SUSPECT=$(python3 -c 'import json,sys;print(json.loads(sys.argv[1])["files"])' "$AUDIT")
if [[ $SUSPECT != 0 ]]; then
  echo "${RED}⚠ 상자 밖 접근 흔적 ${SUSPECT}건 - $RUN_JSON 의 audit 를 본다${OFF}"
else
  echo "감사: 상자 밖 접근 흔적 없음"
fi
[[ $FAIL -gt 0 ]] && printf '%s실패한 시도의 원본은 %s/raw/ 에 있다. 다시 돌리면 재시도한다.%s\n' "$DIM" "$OUT" "$OFF"

cat <<NEXT

${BLD}다음${OFF}
  uv run codeproof import --from $OUT --kind agent --name $NAME
      (포맷 · identity · effort 는 RUN.json 에서 읽는다)
NEXT
