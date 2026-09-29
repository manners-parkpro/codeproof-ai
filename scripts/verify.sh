#!/usr/bin/env bash
#
# 이 저장소의 주장이 **지금 이 기계에서 재현되는지** 확인한다.
#
#   ./scripts/verify.sh
#
# API 키가 필요 없고 30초 안에 끝난다. 전체 절차는 docs/VERIFY.md 에 있다.
#
# 🔴 이건 시연이 아니라 검증이다. 재현되지 않으면 **크게 실패하고 exit 1** 이다.
#    항상 초록불이 켜지는 스크립트는 아무것도 증명하지 못한다.
#
# 🔴 그리고 기대값을 숫자로 박지 않는다. 코퍼스가 자라면 7도 238도 바뀐다 -
#    박아 두면 **코퍼스를 늘린 다음 날 이 스크립트가 거짓말을 시작**한다.
#    대신 **관계**를 검사한다:
#
#      ALL 에서 : 두 채점자의 FP 가 서로 **다르다**   (편차가 존재한다)
#      S   에서 : 두 채점자의 FP 가 서로 **같다**     (편차가 사라진다)
#
#    숫자는 보여주되 판정은 관계로 한다. 이 저장소가 스스로에게 적용하는
#    규율과 같다 - 변동하는 측정값은 산문(이나 스크립트)이 들지 않는다.

set -uo pipefail
cd "$(dirname "$0")/.." || exit 2

B=$'\033[1m'; G=$'\033[32m'; R=$'\033[31m'; Y=$'\033[33m'; D=$'\033[2m'; O=$'\033[0m'
[[ -t 1 ]] || { B=""; G=""; R=""; Y=""; D=""; O=""; }

STEP=0; TOTAL=5; FAILED=(); SKIPPED=()

say()  { printf '\n%s[%d/%d] %s%s\n' "$B" "$((++STEP))" "$TOTAL" "$1" "$O"; }
why()  { printf '%s      %s%s\n' "$D" "$1" "$O"; }
ok()   { printf '      %s✓%s %s\n' "$G" "$O" "$1"; }
bad()  { printf '      %s✗ %s%s\n' "$R" "$1" "$O"; FAILED+=("$2"); }
skip() { printf '      %s— %s%s\n' "$Y" "$1" "$O"; SKIPPED+=("$2"); }

# measure 한 번 돌려 채점자별 FP 를 꺼낸다.
#   $1 = --ruff-select 값 · 출력: "<지적수> <ps_fp> <inj_fp>" (지적 0 이면 "0 - -")
measure_fp() {
  local out
  out=$(uv run codeproof measure --analyzers ruff --ruff-select "$1" --store none 2>/dev/null)
  local n ps inj
  n=$(printf '%s' "$out" | grep -oE '같은 지적 [0-9]+건' | head -1 | grep -oE '[0-9]+')
  ps=$(printf '%s' "$out" | awk '/^ *provable_safety/ {print $3; exit}')
  inj=$(printf '%s' "$out" | awk '/^ *injected_defect/ {print $3; exit}')
  printf '%s %s %s' "${n:-0}" "${ps:--}" "${inj:--}"
}

cat <<BANNER
${B}CodeProof AI — 재현 확인${O}
${D}이 저장소의 헤드라인이 지금 이 기계에서 재현되는지 검사한다.
API 키는 필요 없다. 전체 절차는 docs/VERIFY.md.${O}
BANNER

# ── 1. 준비 ────────────────────────────────────────────────────────────────
say "준비 — 도구가 갖춰졌는가"
why "자격증명 없이도 exit 0 이어야 한다. 키가 있어야만 재현되는 주장은 검증받을 수 없다."
if uv run codeproof doctor > /dev/null 2>&1; then
  ok "doctor exit=0 (정적분석기 경로만으로 아래가 전부 돈다)"
else
  bad "doctor 가 실패했다 — uv sync 를 먼저 돌린다" "준비"
  printf '\n%s준비가 안 돼 여기서 멈춘다.%s\n' "$R" "$O"; exit 1
fi

# ── 2. 헤드라인 ────────────────────────────────────────────────────────────
say "헤드라인 — 같은 지적을 다른 정의로 채점하면 갈리는가"
why "지적은 하나도 바꾸지 않는다. 정답 정의만 바꾼다."
read -r N_ALL PS_ALL INJ_ALL <<< "$(measure_fp ALL)"
printf '      %s--ruff-select ALL · 지적 %s건 → provable_safety FP=%s · injected_defect FP=%s%s\n' \
  "$D" "$N_ALL" "$PS_ALL" "$INJ_ALL" "$O"
if [[ "$N_ALL" -gt 0 && "$PS_ALL" != "-" && "$PS_ALL" != "$INJ_ALL" ]]; then
  ok "두 정의가 갈린다 — 같은 지적인데 FP 가 ${PS_ALL} 대 ${INJ_ALL}"
else
  bad "편차가 재현되지 않는다 (지적 ${N_ALL}건 · FP ${PS_ALL}/${INJ_ALL})" "헤드라인"
fi

# ── 3. 손잡이 ⭐ ───────────────────────────────────────────────────────────
say "손잡이 — 그 편차가 **설정의 함수**인가"
why "이 저장소의 논지다. 헤드라인이 성립하지 않는 설정이 있다고 문서가 먼저 말한다."
read -r N_S PS_S INJ_S <<< "$(measure_fp S)"
printf '      %s--ruff-select S   · 지적 %s건 → provable_safety FP=%s · injected_defect FP=%s%s\n' \
  "$D" "$N_S" "$PS_S" "$INJ_S" "$O"
if [[ "$N_S" -gt 0 && "$PS_S" != "-" && "$PS_S" == "$INJ_S" ]]; then
  ok "보안 룰만 고르면 두 정의가 일치한다 — 편차가 사라진다"
  why "→ 편차는 채점자만의 성질이 아니라 (채점자 x 룰 선택)의 성질이다."
else
  bad "S 에서 일치가 재현되지 않는다 (FP ${PS_S}/${INJ_S})" "손잡이"
fi

# ── 4. 가드 반증 ⭐ ────────────────────────────────────────────────────────
say "가드 반증 — 테스트가 공허하지 않은가"
why "불변식을 일부러 깨고 가드가 우는지 본다. 깨뜨렸는데 통과하면 그 가드는 없는 것과 같다."
if ! git diff --quiet || ! git diff --cached --quiet; then
  skip "작업 트리가 더러워 건너뛴다 (falsify.sh 는 소스를 고쳤다 되돌린다)" "가드 반증"
  why "커밋하거나 stash 한 뒤 ./scripts/falsify.sh 를 직접 돌린다."
elif out=$(./scripts/falsify.sh 2>&1); then
  ok "$(printf '%s' "$out" | tail -1)"
  why "각 시나리오는 두 줄 계약이다 — 깨끗한 트리에서 통과하고 깨뜨리면 실패한다."
else
  printf '%s' "$out" | grep -E '침묵|깨끗한 트리' | head -3 | sed 's/^/      /'
  bad "침묵한 가드가 있다 — 공허한 가드다" "가드 반증"
fi

# ── 5. 라벨과 생성물 ───────────────────────────────────────────────────────
say "라벨 — 「증명된 음성」이 정말 안전한가"
why "코퍼스 라벨이 거짓이면 위의 숫자가 통째로 무의미해진다. 쌍마다 실행 가능한 반증이 있다."
if uv run pytest tests/corpus/test_proofs.py -q > /dev/null 2>&1; then
  ok "모든 쌍에서 attack(decoy)=False 이고 attack(twin)=True"
  why "두 번째 조건이 핵심이다 — 없으면 return False 만 적어도 통과한다."
else
  bad "반증 실행이 실패했다 — 안전 근거가 거짓인 쌍이 있다" "라벨"
fi
if uv run codeproof report --check > /dev/null 2>&1; then
  ok "docs/MEASUREMENTS.md 가 코퍼스와 일치한다 (생성물이 최신)"
else
  bad "생성물이 낡았다 — codeproof report 로 다시 만든다" "생성물"
fi

# ── 요약 ───────────────────────────────────────────────────────────────────
printf '\n%s%s%s\n' "$D" "────────────────────────────────────────────────────────" "$O"
if [[ ${#FAILED[@]} -eq 0 ]]; then
  printf '%s재현됨.%s 헤드라인도, 그것이 설정의 함수라는 것도, 가드가 공허하지 않다는 것도.\n' "$G" "$O"
  [[ ${#SKIPPED[@]} -gt 0 ]] && printf '%s건너뛴 단계: %s%s\n' "$Y" "${SKIPPED[*]}" "$O"
  cat <<NEXT

${B}다음에 볼 것${O}
  docs/VERIFY.md   T4(라벨을 직접 공격) · ${B}면접관용 질문 7개${O} · ${B}이 도구가 확인해 주지 못하는 것 6가지${O}
  ./scripts/falsify.sh --list   어떤 불변식을 검사하는지
NEXT
  exit 0
fi
printf '%s재현되지 않았다: %s%s\n' "$R" "${FAILED[*]}" "$O"
printf '%s이게 옳은 동작이다 — 주장이 성립하지 않으면 이 스크립트는 실패해야 한다.%s\n' "$D" "$O"
exit 1
