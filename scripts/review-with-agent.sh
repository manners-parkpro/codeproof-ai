#!/usr/bin/env bash
#
# 에이전트 CLI 로 코퍼스를 리뷰시킨다 — **API 키 없이 모델 숫자를 내는 경로**.
#
#   codeproof export --out agent-in
#   scripts/review-with-agent.sh claude agent-in agent-out
#   codeproof import --from agent-out --kind agent --name claude-code --identity 2.1.250
#
# 🔴 샘플마다 **새 임시 디렉터리**에 복사해서 돌린다.
#
#    `materialize()` 가 분석기를 임시 디렉터리에 가두는 것과 정확히 같은 이유다(C1).
#    내보낸 디렉터리에서 그냥 돌리면 에이전트가 옆 decoy 와 그 이름(`#twin`,
#    미끼 분류가 다 드러난다)을 볼 수 있다. 에이전트는 파일 탐색이 가능하므로
#    **분석기보다 격리가 더 중요하다.**
#
#    임시 디렉터리 이름도 무작위다 - `D003-caller-held-lock#twin` 이 cwd 이름으로
#    보이면 그것만으로 정답이 샌다.
#
# 🔴 프롬프트는 **인자로** 준다. 파일로 두면 상자 안에 파일이 하나 더 생겨
#    「제시된 파일」이 둘이 되고, 그러면 파서가 `module.py` 아닌 지적을 버린다.
#
# 이어서 돌릴 수 있다 - 이미 있는 출력은 건너뛴다. 중간에 끊겨도 다시 돌리면 된다.

set -uo pipefail

RED=$'\033[31m'; GRN=$'\033[32m'; DIM=$'\033[2m'; BLD=$'\033[1m'; OFF=$'\033[0m'
[[ -t 1 ]] || { RED=""; GRN=""; DIM=""; BLD=""; OFF=""; }

usage() {
  cat >&2 <<USAGE
용법: $0 <claude|codex> <export-dir> <out-dir> [옵션]

  --runs N     샘플당 반복 횟수 (기본 1). <sample_id>.<i>.json 으로 쓴다
  --limit N    앞에서 N개 샘플만 (파일럿용)
  --model M    모델 고정. 🔴 재현성을 위해 권장하고, identity 에 적어 둔다
  --timeout S  한 건 제한시간 (기본 240초)

🔴 n=1 로는 변동을 말할 수 없다 (F8). 파일럿이 아니면 --runs 를 올린다.
USAGE
  exit 2
}

[[ $# -lt 3 ]] && usage
AGENT=$1; IN=$2; OUT=$3; shift 3
RUNS=1; LIMIT=0; MODEL=""; TIMEOUT=240
while [[ $# -gt 0 ]]; do
  case $1 in
    --runs)    RUNS=$2; shift 2 ;;
    --limit)   LIMIT=$2; shift 2 ;;
    --model)   MODEL=$2; shift 2 ;;
    --timeout) TIMEOUT=$2; shift 2 ;;
    *) echo "${RED}모르는 옵션: $1${OFF}" >&2; usage ;;
  esac
done

[[ -f "$IN/PROMPT.md" ]] || { echo "${RED}$IN/PROMPT.md 가 없다 — codeproof export 를 먼저 돌린다${OFF}" >&2; exit 2; }
command -v "$AGENT" > /dev/null || { echo "${RED}$AGENT 를 찾을 수 없다${OFF}" >&2; exit 2; }

PROMPT=$(cat "$IN/PROMPT.md")
mkdir -p "$OUT"

# 에이전트 한 건 실행. stdout 에 원본 출력.
run_agent() {
  local box=$1
  case "$AGENT" in
    claude)
      ( cd "$box" && timeout "$TIMEOUT" claude -p "$PROMPT" \
          ${MODEL:+--model "$MODEL"} < /dev/null 2>&1 ) ;;
    codex)
      # --skip-git-repo-check: 임시 상자는 git 저장소가 아니다
      # --sandbox read-only:   리뷰어가 코드를 고치면 측정 대상이 바뀐다
      ( cd "$box" && timeout "$TIMEOUT" codex exec --sandbox read-only \
          --skip-git-repo-check ${MODEL:+--model "$MODEL"} "$PROMPT" < /dev/null 2>&1 ) ;;
    *) echo "${RED}모르는 에이전트: $AGENT${OFF}" >&2; exit 2 ;;
  esac
}

# 🔴 출력에서 JSON 을 꺼낸다. 에이전트는 산문·펜스·토큰 사용량을 섞어 낸다
#    [실측] codex 는 파일 내용을 다시 찍고 "tokens used 31,508" 을 붙였다.
#    `findings` 키를 가진 **마지막** 객체를 쓴다 - 앞쪽은 프롬프트 반향일 수 있다.
extract_json() {
  python3 -c '
import json, sys
text = sys.stdin.read()
best = None
for i, ch in enumerate(text):
    if ch != "{":
        continue
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{": depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                try:
                    obj = json.loads(text[i:j+1])
                except ValueError:
                    pass
                else:
                    if isinstance(obj, dict) and isinstance(obj.get("findings"), list):
                        best = obj
                break
if best is None:
    sys.exit(1)
json.dump(best, sys.stdout, ensure_ascii=False)
'
}

BOXES=()
while IFS= read -r d; do BOXES+=("$d"); done \
  < <(find "$IN" -mindepth 1 -maxdepth 1 -type d | sort)
if [[ $LIMIT -gt 0 && ${#BOXES[@]} -gt $LIMIT ]]; then
  BOXES=("${BOXES[@]:0:$LIMIT}")
fi
[[ ${#BOXES[@]} -gt 0 ]] || { echo "${RED}$IN 에 샘플 디렉터리가 없다${OFF}" >&2; exit 2; }

TOTAL=$(( ${#BOXES[@]} * RUNS ))
printf '%s%s%s · 샘플 %d개 × %d회 = %d건 · 제한 %ds\n' \
  "$BLD" "$AGENT" "$OFF" "${#BOXES[@]}" "$RUNS" "$TOTAL" "$TIMEOUT"
[[ $RUNS -eq 1 ]] && printf '%s⚠ n=1 — 변동을 말할 수 없다 (F8). 파일럿으로만 쓴다.%s\n' "$DIM" "$OFF"
echo

DONE=0; SKIP=0; FAIL=0; I=0
START=$(date +%s)

for box in "${BOXES[@]}"; do
  sid=$(basename "$box")
  for ((r = 0; r < RUNS; r++)); do
    ((I++))
    dest="$OUT/$sid.$r.json"
    if [[ -s "$dest" ]]; then ((SKIP++)); continue; fi

    tmp=$(mktemp -d)                       # 🔴 무작위 이름 - 상자 이름도 라벨이다
    find "$box" -mindepth 1 -maxdepth 1 -exec cp -R {} "$tmp/" \;

    if raw=$(run_agent "$tmp") && printf '%s' "$raw" | extract_json > "$dest" 2>/dev/null; then
      n=$(python3 -c 'import json,sys;print(len(json.load(open(sys.argv[1]))["findings"]))' "$dest")
      printf '  [%3d/%3d] %s%-46s%s 지적 %s건\n' "$I" "$TOTAL" "$DIM" "$sid" "$OFF" "$n"
      ((DONE++))
    else
      rm -f "$dest"                        # 남기지 않는다 - 다시 돌리면 재시도한다
      printf '  [%3d/%3d] %s%-46s 실패%s\n' "$I" "$TOTAL" "$RED" "$sid" "$OFF"
      printf '%s' "${raw-}" > "$OUT/$sid.$r.rawfail.txt"
      ((FAIL++))
    fi
    rm -rf "$tmp"
  done
done

ELAPSED=$(( $(date +%s) - START ))
printf '\n%s완료%s %d건 · 건너뜀 %d · 실패 %d · %d분 %d초\n' \
  "$GRN" "$OFF" "$DONE" "$SKIP" "$FAIL" $((ELAPSED/60)) $((ELAPSED%60))

if [[ $FAIL -gt 0 ]]; then
  printf '%s실패한 건의 원본은 %s/*.rawfail.txt 에 있다. 다시 돌리면 재시도한다.%s\n' "$DIM" "$OUT" "$OFF"
fi
cat <<NEXT

${BLD}다음${OFF}
  uv run codeproof import --from $OUT --kind agent \\
      --name $AGENT --identity "<버전${MODEL:+ · $MODEL}>"
NEXT
