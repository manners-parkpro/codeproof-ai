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
# 🔴 돌고 있는 동안 이 파일과 agent_output.py 를 **제자리에서 고치지 않는다.**
#    bash 는 스크립트를 실행하면서 읽고, 도우미는 호출마다 다시 읽힌다.
#    새 파일에 쓰고 mv 로 바꾼다 (열린 fd 는 옛 inode 를 계속 읽는다).
#
# bash 3.2 호환 (mapfile · 연관 배열 없음).

set -uo pipefail

RED=$'\033[31m'; GRN=$'\033[32m'; DIM=$'\033[2m'; BLD=$'\033[1m'; OFF=$'\033[0m'
[[ -t 1 ]] || { RED=""; GRN=""; DIM=""; BLD=""; OFF=""; }

RUNNER_VERSION=2
HERE=$(cd "$(dirname "$0")" && pwd)
HELPER="$HERE/agent_output.py"

usage() {
  cat >&2 <<USAGE
용법: $0 <claude|codex> <export-dir> <out-dir> --effort E [옵션]

  --effort E   🔴 필수 (D4). low · medium · high · xhigh · max
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

case $AGENT in claude|codex) ;; *) die "모르는 에이전트: $AGENT (claude | codex)" ;; esac
[[ -n $EFFORT ]] || die "--effort 는 필수다 (D4) - 없으면 개인 설정의 effort 를 물려받는다"
for f in PROMPT.md SCHEMA.json MANIFEST.json; do
  [[ -f "$IN/$f" ]] || die "$IN/$f 가 없다 - codeproof export 를 (다시) 돌린다"
done
command -v "$AGENT" > /dev/null || die "$AGENT 를 찾을 수 없다"
command -v python3 > /dev/null || die "python3 를 찾을 수 없다"

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
esac

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
    schema_hash="$(manifest schema_hash)" identity="$IDENTITY" timeout_s="$TIMEOUT" \
    runner_sha="$RUNNER_SHA" started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)")
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
printf '%s격리: %s · 권한: %s%s\n' "$DIM" "$ISOLATION" "$PERMISSION" "$OFF"
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

    if info=$(python3 "$HELPER" extract "$AGENT" "$rp" "$RESOLVED" "$dest" 2>> "$rp.err"); then
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
