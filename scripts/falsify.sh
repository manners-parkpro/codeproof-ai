#!/usr/bin/env bash
#
# 가드가 **공허하지 않은지** 확인한다.
#
# 🔴 왜 이 스크립트가 있는가.
#
# 테스트가 통과하는 것은 「가드가 있다」의 증거가 아니다. 지키려는 것을
# 깨뜨렸는데도 통과하면 그 가드는 없는 것과 같다.
#
# [실측] 문서 감사 중에 **두 개가 그랬다.** 산문-생성물 대조 정규식이 FP 열이
# 아니라 TP 열을 읽고 있었고, 패키지 트리 검사는 문서 전체에서 이름을 찾아
# 트리에서 모듈을 지워도 통과했다. 둘 다 일부러 깨뜨려 보고서야 드러났다.
# 손으로 했기 때문에 **체계가 없었다** - 이 스크립트가 그걸 반복 가능하게 만든다.
#
# 아이디어는 `corpus/decoys/*/proof.py` 와 같다. 거기서는 decoy 의 안전 주장을
# 공격으로 반증하고, 여기서는 **가드의 주장**을 위반으로 반증한다. 한 층 위다.
#
# 🔴 그러니 계약도 **두 줄**이어야 한다. proof.py 가 한 줄(attack(decoy) is False)
#    만으로는 부족해서 두 번째 줄(attack(twin) is True)을 둔 것과 같은 이유다.
#
#      guard(깨끗한 트리) == 0   - 가드가 정상 상태를 통과시킨다
#      guard(깨뜨린 트리) != 0   - 🔴 가드가 위반을 **잡을 수 있다**
#
#    [실측] 처음엔 두 번째 줄만 있었다. 그러면 가드 테스트 파일을 **이름만 바꿔도**
#    pytest 가 `exit=4`(file not found)를 내고, 스크립트가 그걸 「가드가 울었다」로
#    읽어 **통과**한다. 가드가 통째로 사라졌는데 초록불이 켜지는 것이다 -
#    proof.py 에서 `return False` 만 적어도 통과하던 것과 정확히 같은 구멍이다.
#
# 용법:
#   scripts/falsify.sh              전부
#   scripts/falsify.sh layering     하나만
#   scripts/falsify.sh --list       목록
#
# 전제: 작업 트리가 깨끗해야 한다. 이 스크립트는 소스를 **일부러 고쳤다가**
#       `git checkout` 으로 되돌리므로, 커밋 안 된 변경이 있으면 거부한다.

set -uo pipefail

cd "$(dirname "$0")/.." || exit 2

RED=$'\033[31m'; GREEN=$'\033[32m'; DIM=$'\033[2m'; BOLD=$'\033[1m'; OFF=$'\033[0m'
[[ -t 1 ]] || { RED=""; GREEN=""; DIM=""; BOLD=""; OFF=""; }

PASS=0; FAIL=0; FAILED_NAMES=()

# ── 시나리오 ───────────────────────────────────────────────────────────────
#
# 각 시나리오는 셋을 선언한다:
#   claim_X   가드가 지킨다고 주장하는 불변식
#   break_X   그 불변식을 깨는 최소 변경
#   guard_X   가드. 깨끗한 트리에서 **통과**하고 깨뜨린 뒤 **실패**해야 한다.

SCENARIOS=(layering runner registry proof-label proof-vacuous corpus-strict convention docs-tree generated
           agent-contract span-match llm-symbol import-format import-manifest model-pin
           model-drift multirun-views view-regrade view-copy multirun-labels run-gap short-runs
           sweep-ladder sensitivity-views report-partial report-labels pack-partial pack-leftover)

claim_layering() { echo "런타임(analysis)은 정답 라벨(eval)을 볼 수 없다 — A1"; }
break_layering() {
  printf '\nfrom codeproof_ai.eval.sample import Stratum  # falsify.sh\n' \
    >> src/codeproof_ai/analysis/base.py
}
guard_layering() { uv run pytest tests/architecture/test_layering.py -q; }

claim_runner() { echo "실행 경로는 run_reviewer 하나뿐이다 — E00"; }
break_runner() {
  printf '\ndef run_analyzer() -> None:  # falsify.sh\n    pass\n' \
    >> src/codeproof_ai/eval/runner.py
}
guard_runner() { uv run pytest tests/architecture/test_single_runner.py -q; }

claim_registry() { echo "cli.py 는 구현체를 직접 생성하지 않는다 — A3"; }
break_registry() {
  printf '\n_leak = RuffAnalyzer()  # falsify.sh\n' >> src/codeproof_ai/cli.py
}
guard_registry() { uv run pytest tests/architecture/test_registry.py -q -k cli; }

# 🔴 쌍을 고정하지 않는다. 계약(attack(twin) is True)이 모든 쌍에 성립하므로
#    twin 을 decoy 자리에 넣으면 **어느 쌍이든** 공격이 성공해야 한다.
_pair() { ls -d corpus/decoys/D*/ 2>/dev/null | head -1; }

claim_proof-label() { echo "「증명된 음성」 라벨이 거짓이면 반증이 잡는다 — G3a1"; }
break_proof-label() { local p; p=$(_pair); cp "$p/twin.py" "$p/decoy.py"; }
guard_proof-label() { uv run pytest tests/corpus/test_proofs.py -q; }

claim_proof-vacuous() { echo "결함을 못 잡는 공격은 안전을 증명하지 못한다 — G3a1"; }
break_proof-vacuous() {
  local p; p=$(_pair)
  cat > "$p/proof.py" <<'EOF'
"""falsify.sh - 의도적으로 무능한 공격."""
from types import ModuleType


def attack(mod: ModuleType) -> bool:
    return False
EOF
}
guard_proof-vacuous() { uv run pytest tests/corpus/test_proofs.py -q; }

# 경고만 내는 위반이어야 한다 - 오류면 엄격하지 않은 테스트도 울어서 이 가드를 시험하지 못한다.
# 이미 수용 표기가 있는 decoy 는 피한다 (키가 겹치면 TOML 로드 오류가 된다).
_unacked() { for m in corpus/decoys/D*/meta.toml; do grep -q acknowledged_warnings "$m" || { echo "$m"; return; }; done; }

claim_corpus-strict() { echo "코퍼스 테스트가 훅과 같은 기준(--strict)이다 — 경고도 센다 (G3c)"; }
break_corpus-strict() {
  local m; m=$(_unacked)
  [[ -n $m ]] && perl -0pi -e 's/\A/acknowledged_warnings = ["W2"]  # falsify.sh\n/' "$m"
}
guard_corpus-strict() { uv run pytest tests/corpus/test_decoy_validator.py -q -k repo_corpus_is_clean; }

claim_docs-tree() { echo "DESIGN 의 패키지 트리가 실제 모듈을 전부 싣는다 — F5b"; }
break_docs-tree() { perl -0pi -e 's/^.*mix\.py.*\n//m' docs/DESIGN.md; }
guard_docs-tree() { uv run pytest tests/docs/test_consistency.py -q -k package_tree; }

claim_generated() { echo "생성물을 손으로 고치면 --check 가 잡는다 — F5b"; }
break_generated() { perl -0pi -e 's/코퍼스 \*\*(\d+)쌍\*\*/코퍼스 **999쌍**/' docs/MEASUREMENTS.md; }
guard_generated() { uv run codeproof report --check; }

# ── 에이전트 층 (A2b · DESIGN §7.10) - 첫 전체 실행에서 조용히 틀렸던 자리들 ──

claim_agent-contract() { echo "에이전트 출력 규격은 model_api 스키마의 칸을 전부 싣는다 — A2b"; }
break_agent-contract() {
  perl -0pi -e 's/    names = item\["required"\]\n/    names = [n for n in item["required"] if n != "quoted_code"]  # falsify.sh\n/' \
    src/codeproof_ai/eval/export.py
}
guard_agent-contract() { uv run pytest tests/eval/test_export.py -q; }

claim_span-match() { echo "위치 매칭은 지적의 보고 범위로 한다 — A2a"; }
break_span-match() {
  perl -0pi -e 's/        return self\.start\.line <= hi and max\(self\.start\.line, last\) >= lo\n/        return lo <= self.start.line <= hi  # falsify.sh\n/' \
    src/codeproof_ai/domain/location.py
}
guard_span-match() { uv run pytest tests/eval/test_llm_findings.py -q -k ReportedRange; }

claim_llm-symbol() { echo "모델·에이전트 지적도 둘러싼 함수를 얻는다 — E00"; }
break_llm-symbol() {
  perl -0pi -e 's/    if reviewer\.kind is ReviewerKind\.STATIC:\n        return list\(findings\)\n/    return list(findings)  # falsify.sh\n/' \
    src/codeproof_ai/eval/runner.py
}
guard_llm-symbol() { uv run pytest tests/eval/test_llm_findings.py -q -k SameFinding; }

claim_import-format() { echo "형식 착오를 「지적 0건」으로 읽지 않는다 — A2b"; }
break_import-format() {
  perl -0pi -e 's/        if not self\._parser\.recognizes\(payload\):\n/        if False:  # falsify.sh\n/' \
    src/codeproof_ai/reviewers/imported.py
}
guard_import-format() { uv run pytest tests/cli/test_commands.py -q -k wrong_format; }

claim_import-manifest() { echo "가져온 에이전트 실행의 effort 를 리뷰어가 신고한다 — E01"; }
break_import-manifest() {
  perl -0pi -e 's/    def manifest_fields\(self\)/    def _manifest_fields_off(self)/' \
    src/codeproof_ai/reviewers/imported.py
}
guard_import-manifest() { uv run pytest tests/cli/test_commands.py -q -k run_record_is_the_manifest; }

claim_model-pin() { echo "고정한 모델이 아닌 모델의 답은 실패로 센다 — A2b"; }
break_model-pin() {
  perl -0pi -e 's/    if model not in seen:\n/    if False:  # falsify.sh\n/' scripts/agent_output.py
}
guard_model-pin() { uv run pytest tests/scripts -q -k substituted; }

claim_model-drift() { echo "벤더 최상위가 바뀌면 실행기가 멈춘다 — DESIGN §7.10"; }
break_model-drift() {
  perl -0pi -e 's/    if isinstance\(prev, dict\) and prev\.get\("model"\) != model and not accept:\n/    if False:  # falsify.sh\n/' \
    scripts/agent_output.py
}
guard_model-drift() { uv run pytest tests/scripts -q -k ModelDrift; }

# ── 다회 실행 (F3 · F6) - 합집합과 미측정이 숫자를 조용히 바꾸는 자리 ──

claim_multirun-views() { echo "다회 실행은 관점을 골라 센다 — 합집합으로 접지 않는다 (F6)"; }
break_multirun-views() {
  perl -0pi -e 's/observed=pick\(o\.observations\)/observed=o.observations.observed/' \
    src/codeproof_ai/eval/runner.py
}
guard_multirun-views() { uv run pytest tests/eval/test_multirun.py -q -k ViewsAreDifferentNumbers; }

claim_view-regrade() { echo "관점별 숫자는 관점의 지적으로 다시 묶어 채점한다 — 합집합 짝의 판정을 걸러내지 않는다 (F6)"; }
break_view-regrade() {
  perl -0pi -e 's/\(by_id\[o\.sample_id\], obs\) for o, obs in viewed/(by_id[o.sample_id], o.observations) for o, obs in viewed/' \
    src/codeproof_ai/eval/runner.py
}
guard_view-regrade() { uv run pytest tests/eval/test_multirun.py -q -k ViewsMatchRunningAlone; }

claim_view-copy() { echo "관점 재채점은 채점자 복사본을 묶는다 — 넘겨받은 채점자의 바인딩을 바꾸지 않는다"; }
break_view-copy() {
  perl -0pi -e 's/bound = \[copy\.copy\(g\) for g in graders\]/bound = list(graders)/' \
    src/codeproof_ai/eval/runner.py
}
guard_view-copy() { uv run pytest tests/eval/test_multirun.py -q -k leaves_the_given_grader_unbound; }

claim_multirun-labels() { echo "다회 실행의 짝 채점은 라벨 붙은 관점으로 찍는다 — F3"; }
break_multirun-labels() {
  perl -0pi -e 's/^        if n > 1:\n/        if False:  # falsify.sh\n/m' src/codeproof_ai/cli.py
}
guard_multirun-labels() { uv run pytest tests/cli/test_commands.py -q -k short_runs_drop_their_pair; }

claim_run-gap() { echo "끊긴 회차를 이어진 것으로 세지 않는다 — 미측정은 미탐지가 아니다 (F4)"; }
break_run-gap() {
  perl -0pi -e 's|        n = 0\n        while \(self\.root / f"\{sample_id\}\.\{n\}\.json"\)\.is_file\(\):\n            n \+= 1\n|        n = len(list(self.root.glob(f"{sample_id}.*.json")))  # falsify.sh\n|' \
    src/codeproof_ai/reviewers/imported.py
}
guard_run-gap() { uv run pytest tests/reviewers/test_imported.py -q -k gap; }

claim_short-runs() { echo "N회에 모자란 샘플은 채점하지 않는다 — 출현 빈도가 거짓이 된다 (F6)"; }
break_short-runs() {
  perl -0pi -e 's/available_runs\(s\.sample_id\) == runs\}/available_runs(s.sample_id) > 0}  # falsify.sh/' \
    src/codeproof_ai/cli.py
}
guard_short-runs() { uv run pytest tests/cli/test_commands.py -q -k short_runs_are_refused; }

claim_sweep-ladder() { echo "slack 사다리가 좁으면 전이점을 놓쳐 거짓 「안정」이 나온다 — A2a · DESIGN #31"; }
break_sweep-ladder() {
  perl -0pi -e 's/^DEFAULT_SWEEP: tuple\[int, \.\.\.\] = \(0, 2, 5, 10\)$/DEFAULT_SWEEP: tuple[int, ...] = (0, 2, 5)  # falsify.sh/m' \
    src/codeproof_ai/eval/sensitivity.py
}
guard_sweep-ladder() { uv run pytest tests/eval/test_sensitivity.py -q -k slack_sensitive; }

claim_sensitivity-views() { echo "다회 실행의 매칭 민감도는 관점마다 낸다 — 라벨 없는 합집합이 아니다 (F6)"; }
break_sensitivity-views() {
  perl -0pi -e 's/    if run\.manifest\.sample_n > 1:\n        _print_sensitivity_views/    if False:  # falsify.sh\n        _print_sensitivity_views/' \
    src/codeproof_ai/cli.py
}
guard_sensitivity-views() { uv run pytest tests/cli/test_commands.py -q -k sensitivity_is_labeled; }

claim_report-partial() { echo "생성물에는 모든 회차가 있는 에이전트 실행만 싣는다 — F6"; }
break_report-partial() {
  perl -0pi -e 's/(samples, box, name=src\.name, kind=ReviewerKind\.AGENT, )allow_partial=False$/${1}allow_partial=True  # falsify.sh/m' \
    src/codeproof_ai/cli.py
}
guard_report-partial() { uv run pytest tests/cli/test_commands.py -q -k short_agent_runs; }

claim_pack-partial() { echo "모자란 회차는 묶지 않는다 — 묶고 나면 report 에 가서야 걸린다 (F6)"; }
break_pack-partial() {
  perl -0pi -e 's/(labeled, src, name=out\.name, kind=ReviewerKind\.AGENT, )allow_partial=False\) is None:/${1}allow_partial=True) is None:  # falsify.sh/' \
    src/codeproof_ai/cli.py
}
guard_pack-partial() { uv run pytest tests/cli/test_commands.py -q -k pack_refuses_short; }

claim_pack-leftover() { echo "묶음 자리에 옛 파일이 있으면 묶지 않는다 — 섞이면 그대로 커밋된다"; }
break_pack-leftover() {
  perl -0pi -e 's/^    if extra:\n/    if False:  # falsify.sh\n/m' src/codeproof_ai/cli.py
}
guard_pack-leftover() { uv run pytest tests/cli/test_commands.py -q -k pack_does_not_mix; }

claim_report-labels() { echo "생성물의 다회 실행 숫자는 관점마다 라벨을 붙인다 — F3 · F6"; }
break_report-labels() {
  perl -0pi -e 's/    views = thresholds\(n\)\n/    views = thresholds(1)  # falsify.sh\n/' \
    src/codeproof_ai/eval/report.py
}
guard_report-labels() { uv run pytest tests/cli/test_commands.py -q -k agent_runs_get_a_labeled; }

# 🔴 이건 가드 테스트가 아니라 **회귀 재현**이다. 관례 주장을 결함 주장으로
#    세면 FP 가 폭발한다 - 발표했던 결론 두 개를 철회하게 만든 바로 그 버그다.
#    「가드가 운다」가 아니라 「숫자가 움직인다」를 본다.
claim_convention() { echo "관례 주장(docstring 누락)을 FP 로 세지 않는다 — F4a"; }
break_convention() {
  perl -0pi -e 's/        return self is not Category\.STYLE/        return True  # falsify.sh/' \
    src/codeproof_ai/domain/finding.py
}
guard_convention() {
  # 고친 상태의 FP 는 한 자릿수다. 회귀를 넣으면 수십 건으로 뛴다.
  local fp
  fp=$(uv run codeproof measure --analyzers ruff --ruff-select ALL --store none 2>/dev/null \
       | awk '/^ *provable_safety/ {print $3; exit}')
  echo "회귀 상태의 provable_safety FP: ${fp}건 (고친 상태는 한 자릿수다)"
  [[ -n "$fp" && "$fp" -le 20 ]]   # 20 이하로 남아 있으면 회귀가 재현되지 않은 것 → 가드 침묵
}

# ── 하네스 ─────────────────────────────────────────────────────────────────

restore() { git checkout -- . 2>/dev/null; }
# 🔴 trap 은 여기서 걸지 않는다 - require_clean_tree 를 통과한 **뒤**에 건다 (아래).
#    [실측] 여기 걸려 있을 때 `--list` 가 끝나며 EXIT trap 이 `git checkout -- .` 를
#    돌려 **커밋 안 된 작업이 전부 지워졌다.** 목록만 보려던 명령이었다.
#    깨끗한 트리 검사는 소스를 고치는 경로에만 있었고, 되돌리기는 모든 경로에 있었다.

require_clean_tree() {
  if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "${RED}거부한다${OFF} — 커밋되지 않은 변경이 있다." >&2
    echo "이 스크립트는 소스를 일부러 고쳤다가 ${BOLD}git checkout${OFF} 으로 되돌린다." >&2
    echo "그 되돌리기가 당신의 변경을 지운다. 커밋하거나 stash 하고 다시 돌려라." >&2
    exit 2
  fi
  # 🔴 미추적 파일도 본다 - `git checkout` 은 그것을 되돌리지 못한다.
  #    시나리오가 미추적 파일을 깨뜨리면 깨진 채로 남는다.
  if [[ -n $(git status --porcelain --untracked-files=all -- src scripts tests docs) ]]; then
    echo "${RED}거부한다${OFF} — 추적되지 않는 파일이 있다 (git checkout 이 되돌리지 못한다)." >&2
    git status --porcelain --untracked-files=all -- src scripts tests docs | head -5 >&2
    exit 2
  fi
}

run_one() {
  local name=$1
  printf '%s─── %s ───%s\n' "$BOLD" "$name" "$OFF"
  printf '  주장 : %s\n' "$("claim_$name")"

  # ① 🔴 깨끗한 트리에서 가드가 **통과**하는가.
  #    이 줄이 없으면 가드가 사라져 생긴 에러(pytest exit=4 등)를
  #    「가드가 울었다」로 잘못 읽는다.
  if ! "guard_$name" > /dev/null 2>&1; then
    printf '  결과 : %s깨끗한 트리에서도 운다 — 가드가 고장났거나 시나리오가 낡았다%s\n\n' "$RED" "$OFF"
    ((FAIL++)); FAILED_NAMES+=("$name"); restore; return
  fi

  # ② 불변식을 깬다.
  "break_$name" || { echo "  ${RED}깨뜨리지 못했다${OFF} — 시나리오가 낡았다"; ((FAIL++)); FAILED_NAMES+=("$name"); restore; return; }

  local out rc
  out=$("guard_$name" 2>&1); rc=$?

  if [[ $rc -ne 0 ]]; then
    printf '  결과 : %s가드가 울었다%s %s\n' "$GREEN" "$OFF" "$DIM(exit=$rc)$OFF"
    local msg
    msg=$(echo "$out" | grep -m1 -E 'AssertionError|낡았다|회귀 상태의' | sed 's/^E *//;s/^ *//')
    [[ -n "$msg" ]] && printf '         %s%s%s\n' "$DIM" "${msg:0:110}" "$OFF"
    ((PASS++))
  else
    printf '  결과 : %s가드가 침묵했다 — 공허한 가드다%s\n' "$RED" "$OFF"
    ((FAIL++)); FAILED_NAMES+=("$name")
  fi

  restore
  echo
}

case "${1-}" in
  --list)
    for s in "${SCENARIOS[@]}"; do printf '%-16s %s\n' "$s" "$("claim_$s")"; done
    exit 0 ;;
esac

require_clean_tree
trap 'restore' EXIT INT TERM   # 🔴 깨끗함을 확인한 뒤에만 - 지울 것이 없을 때만 되돌린다

TARGETS=("${SCENARIOS[@]}")
[[ $# -gt 0 ]] && TARGETS=("$@")

echo "${BOLD}가드를 반증한다${OFF} — 불변식을 깨고 가드가 우는지 본다."
echo "${DIM}깨뜨렸는데 통과하면 그 가드는 없는 것과 같다.${OFF}"
echo

for s in "${TARGETS[@]}"; do
  declare -F "claim_$s" > /dev/null || { echo "${RED}모르는 시나리오: $s${OFF}" >&2; exit 2; }
  run_one "$s"
done

printf '%s%d개 가드가 울었다%s' "$GREEN" "$PASS" "$OFF"
if [[ $FAIL -gt 0 ]]; then
  printf ' · %s%d개가 침묵했다: %s%s\n' "$RED" "$FAIL" "${FAILED_NAMES[*]}" "$OFF"
  exit 1
fi
printf '\n'
