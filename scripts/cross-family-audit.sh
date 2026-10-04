#!/usr/bin/env bash
#
# 교차 패밀리 라벨 감사 — 쌍 하나를 Codex 에 한 번 묻는다 (DESIGN §9 의 5).
#
#   scripts/cross-family-audit.sh <쌍 디렉터리 이름> <머리말 파일> <출력 디렉터리>
#
# 🔴 유료다 (Codex 크레딧) — 돌리기 전에 승인을 받는다. 크레딧이 떨어지면 그 쌍의 .err 에
#    「out of credits」가 남는다 — 거기서 멈추고 잰 쌍까지만 싣는다 (선언).
#
# 🔴 프로토콜을 이 파일 한 곳에 둔다. [실측] 처음에는 세션 scratch 에만 있어서 정리와 함께
#    사라졌고, 대화 기록에서 되살려 기록된 prompt_sha256 과 맞춰 본 뒤에야 이어 쟀다.
#    라운드마다 세 번째 렌즈로 돌리므로 다시 만든 판이 꼴을 바꾸면 「같은 방식」이 조용히 깨진다.
#
#  - 격리는 실행기(review-with-agent.sh)와 같다 — 사용자 설정 · 규칙 무시 · 세션 안 남김 ·
#    읽기 전용 샌드박스 · 빈 작업 디렉터리. 코드는 실행시키지 않고 프롬프트에 넣는다.
#  - 모델 · effort · CLI 판은 고정이다 — 바꾸면 다른 측정이다. 판이 다르면 거부한다.
#  - 프롬프트는 scripts/cross_family_prompt.py 가 만든다. 머리말은 결과 디렉터리
#    (results/cross-family-*/prompt_head.md)의 것을 쓰고, 그 해시를 RUN.json 에 적는다.
#
# 남기는 것 (출력 디렉터리): <id>.prompt.md · <id>.jsonl (이벤트) · <id>.last.json (마지막 답) · <id>.err

set -uo pipefail

MODEL="gpt-6-astra"
EFFORT="high"
CODEX_VERSION="codex-cli 0.158.0"

if [ $# -ne 3 ]; then
    echo "쓰기: $0 <쌍 디렉터리 이름> <머리말 파일> <출력 디렉터리>" >&2
    exit 2
fi
REPO=$(cd "$(dirname "$0")/.." && pwd)
pair="$REPO/corpus/decoys/$1"
id="${1%%-*}"
head_file="$2"
out="$3"
schema="$REPO/results/cross-family-audit/schema.json"
[ -d "$pair" ] || { echo "없는 쌍: $1" >&2; exit 2; }
[ -f "$head_file" ] || { echo "없는 머리말: $head_file" >&2; exit 2; }
got=$(codex --version 2>/dev/null)
if [ "$got" != "$CODEX_VERSION" ]; then
    echo "codex 판이 다르다: '$got' (잰 판 $CODEX_VERSION) — npm install --prefix <dir> @openai/codex@0.158.0 뒤 <dir>/node_modules/.bin 을 PATH 앞에 둔다" >&2
    exit 2
fi

mkdir -p "$out/boxes"
box=$(mktemp -d "$out/boxes/$id.XXXX")
prompt=$(python3 "$REPO/scripts/cross_family_prompt.py" "$pair" "$head_file") || exit 2
printf '%s' "$prompt" > "$out/$id.prompt.md"
start=$(date +%s)
( cd "$box" && timeout 900 codex exec \
    --ignore-user-config --ignore-rules --ephemeral --skip-git-repo-check \
    --sandbox read-only --color never \
    -m "$MODEL" -c "model_reasoning_effort=\"$EFFORT\"" \
    --output-schema "$schema" --json -o "$out/$id.last.json" \
    "$prompt" < /dev/null > "$out/$id.jsonl" 2> "$out/$id.err" )
rc=$?
echo "$id rc=$rc $(( $(date +%s) - start ))s · 상자 파일 $(find "$box" -type f | wc -l | tr -d ' ')개"
rmdir "$box" 2>/dev/null || true
exit $rc
