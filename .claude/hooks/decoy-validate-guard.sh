#!/usr/bin/env bash
# corpus/decoys 를 편집하면 규격을 검사한다.
#
# 🔴 이 가드가 잡는 것과 못 잡는 것을 구분해야 한다.
#
#   잡는다   : 형식 위반 11종 (V2~V11) - 근거 길이 · 가드 가시성 · 짝 구조 등
#   못 잡는다: **안전 근거가 참인지.**
#              [실측] D015 를 처음 쓸 때 Semaphore(4) 를 가드로 삼았는데
#              4 스레드 동시 진입을 허용하므로 그 경쟁은 실제로 일어난다 -
#              안전 주장이 거짓이었고 **11개 규칙을 전부 통과했다.**
#              손으로 검토해야 하는 층이 남는다 (CLAUDE.md G3a).
#
# 즉 이 훅은 바닥선이지 충분조건이 아니다.
set -uo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

payload="$(cat)"
path="$(printf '%s' "$payload" | jq -r '.tool_input.file_path // .tool_response.filePath // empty' 2>/dev/null)"

# 대상이 아니면 조용히 빠진다.
case "$path" in
  *corpus/decoys/*) ;;
  *) exit 0 ;;
esac

# 템플릿 편집은 검사 대상이 아니다 - 일부러 미완성 상태다.
case "$path" in
  */corpus/decoys/_TEMPLATE/*) exit 0 ;;
esac

if [ -x "$root/.venv/bin/codeproof" ]; then
  runner=("$root/.venv/bin/codeproof")
elif command -v uv >/dev/null 2>&1; then
  runner=(uv run --project "$root" codeproof)
else
  exit 0   # 도구가 없으면 막지 않는다 - 가드가 작업을 멈추게 하지 않는다
fi

out="$("${runner[@]}" decoy validate --strict --corpus "$root/corpus/decoys" 2>&1)"
status=$?

[ "$status" -eq 0 ] && exit 0

jq -nc --arg r "decoy 규격 위반 (형식만 검사 - 안전 근거가 참인지는 손으로 봐야 한다):
$out" '{decision:"block", reason:$r}'
