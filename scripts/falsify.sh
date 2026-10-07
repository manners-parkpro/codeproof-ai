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

# 🔴 깨진 소스의 바이트코드를 남기지 않는다. 같은 크기로 깨고(`> 1` → `> 9`) 같은 초 안에 되돌리면, 깨진 소스로
#    쓴 .pyc 의 「수정 시각(초) · 크기」가 되돌린 소스와 같아 파이썬이 그것을 그대로 쓴다 - 다음 시나리오가 깨끗한
#    트리에서 거짓으로 실패했다 (pair-ladder-note · 두 번). [실측] 그 조건을 만들면 2/2 실패, 이 설정이면 2/2 통과,
#    초가 다르면 통과 (DESIGN 교훈 #66).
export PYTHONDONTWRITEBYTECODE=1

RED=$'\033[31m'; GREEN=$'\033[32m'; DIM=$'\033[2m'; BOLD=$'\033[1m'; OFF=$'\033[0m'
[[ -t 1 ]] || { RED=""; GREEN=""; DIM=""; BOLD=""; OFF=""; }

PASS=0; FAIL=0; FAILED_NAMES=()

# ── 시나리오 ───────────────────────────────────────────────────────────────
#
# 각 시나리오는 셋을 선언한다:
#   claim_X   가드가 지킨다고 주장하는 불변식
#   break_X   그 불변식을 깨는 최소 변경
#   guard_X   가드. 깨끗한 트리에서 **통과**하고 깨뜨린 뒤 **실패**해야 한다.

SCENARIOS=(layering runner registry proof-label proof-vacuous corpus-strict convention docs-tree docs-results-prose selection-headline selection-table selection-repeats fp-counts-floor pair-table pair-sentence pair-block generated figures-generated figures-beside stale-figure out-dash pairs-ladder-label pair-ladder-note agents-points landing-page landing-css landing-blob landing-numbers mutants-unknown
           readme-scoreboard scoreboard-primary misses-complement
           example-rule-slack scoreboard-interval near-miss-rule landing-highlights landing-markers
           agent-contract span-match llm-symbol import-format import-manifest import-rejected
           signed-runner pack-first-runs bundle-separators pair-difference model-pin
           docstring-neutral signed-docstrings resume-docstrings runner-docstrings compare-one-axis
           widened-twin report-widened
           model-drift multirun-views view-regrade view-copy multirun-labels run-gap short-runs
           sweep-ladder sensitivity-views report-partial report-labels pack-partial pack-leftover
           mix-decoy-unit plan-coverage plan-design
           report-collected report-packed-samples report-bundle-record report-corpus-gone
           report-half-pair compare-same-samples compare-skip-note pack-records-samples
           pack-stray-samples sarif-end sarif-category sarif-other-tool bandit-range twin-convention twin-convention-paired
           repro-unknown repro-kind race-switch-lower race-switch-restore invisible-rule invisible-lines
           ruff-target mypy-python mutant-weakening mutant-safe mutant-stale report-digests pack-records-digests
           proof-optimize pack-measured-code runner-measured-code
           pair-discovery mutant-alias template-kinds lint-exclude
           gate-directions gate-survivor gate-neutral gate-prose gate-docstring gate-twin-docstring gate-plan
           xauthor-login-shell xauthor-silent-probe xauthor-unrun xauthor-probe-collision xauthor-vacuous-loop
           xauthor-input-roles xauthor-var-tmp xauthor-verbatim xauthor-sandbox-flag
           xauthor-inventory-ids xauthor-builtin-instructions xauthor-pair-leak xauthor-pair-leak-readme
           xauthor-run-credit xauthor-run-repro xauthor-run-kind xauthor-run-budget xauthor-run-frozen
           review-unlabeled review-no-defect-claim review-self-corroboration review-static-citation
           xauthor-run-restore xauthor-audit-schema xauthor-run-refused xauthor-run-refused-kind
           xauthor-run-refused-resume xauthor-run-idle-cut scripts-typed xauthor-run-gate-output
           xauthor-run-gate-rc xauthor-run-timeout xauthor-run-kind-budget xauthor-run-interrupted
           xauthor-run-recheck xauthor-run-fix-gate xauthor-run-box-missing xauthor-box-help
           xauthor-box-gate-doc xauthor-box-metadata xauthor-s2-accepted-briefs xauthor-s2-drop-kind
           xauthor-s2-retry-briefs xauthor-s2-same-as xauthor-s2-window-cap)

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

claim_race-switch-lower() { echo "race_window 는 창을 여는 동안 전환 간격을 낮춘다 — 한 줄 안의 호출 경계 전환을 드러낸다 (G3a1)"; }
break_race-switch-lower() {
  perl -0pi -e 's/\n    sys\.setswitchinterval\(_RACE_SWITCH_INTERVAL\)//' src/codeproof_ai/corpus/proof.py
}
guard_race-switch-lower() { uv run pytest tests/corpus/test_proofs.py -q -k RaceWindowAlsoLowers; }

claim_race-switch-restore() { echo "race_window 는 낮춘 전환 간격을 되돌린다 — 뒤따르는 테스트가 낮은 간격으로 돌지 않는다 (G3a1)"; }
break_race-switch-restore() {
  perl -0pi -e 's/\n        sys\.setswitchinterval\(saved_interval\)//' src/codeproof_ai/corpus/proof.py
}
guard_race-switch-restore() { uv run pytest tests/corpus/test_proofs.py -q -k RaceWindowAlsoLowers; }

claim_invisible-rule() { echo "쌍의 파일에 원문 보이지 않는 문자가 있으면 검증기가 거부한다 — V14 (G3)"; }
break_invisible-rule() {
  perl -0pi -e 's/\n        \*_check_invisible\(rec\),//' src/codeproof_ai/corpus/decoy.py
}
guard_invisible-rule() { uv run pytest tests/corpus/test_decoy_validator.py -q -k v14; }

claim_invisible-lines() { echo "V14 는 줄을 \\n 으로만 센다 — splitlines 는 U+2028 을 줄로 끊어 먹는다 (B1)"; }
break_invisible-lines() {
  perl -0pi -e 's/path\.read_text\(encoding="utf-8"\)\.split\("\\n"\)/path.read_text(encoding="utf-8").splitlines()/' \
    src/codeproof_ai/corpus/decoy.py
}
guard_invisible-lines() { uv run pytest tests/corpus/test_decoy_validator.py -q -k v14; }

claim_ruff-target() { echo "Ruff 는 코퍼스의 파이썬 판으로 읽는다 — 없으면 3.10 으로 보고 ExceptionGroup 에 F821 (C1a)"; }
break_ruff-target() {
  perl -0pi -e 's/\n            f"--target-version=\{_TARGET\}",//' src/codeproof_ai/analysis/python/ruff.py
}
guard_ruff-target() { uv run pytest tests/analysis/test_adapters.py -q -k target_version; }

claim_mypy-python() { echo "mypy 는 코퍼스의 파이썬 판으로 읽는다 — 없으면 실행한 인터프리터 판을 따른다 (C1a)"; }
break_mypy-python() {
  perl -0pi -e 's/\n        f"--python-version=\{_PYTHON\}",//' src/codeproof_ai/analysis/python/mypy_.py
}
guard_mypy-python() { uv run pytest tests/analysis/test_adapters.py -q -k python_version; }

claim_proof-optimize() { echo "증명은 python -O 로 읽은 판도 친다 — assert 로 쓴 가드는 그 실행에서 사라진다 (G3a1)"; }
break_proof-optimize() {
  perl -0pi -e 's/    return _has_debug_code\(path\) and _hit\(attack, load_module\(path, f"\{alias\}_O", optimize=True\)\)\n/    return False  # falsify.sh\n/' \
    src/codeproof_ai/corpus/proof.py
}
guard_proof-optimize() { uv run pytest tests/corpus/test_proofs.py -q -k an_assert_guard_is_broken; }

claim_mutant-weakening() { echo "증명이 전에 잡던 약화를 놓치게 되면 변이 테스트가 운다 — 쌍의 mutants.py (G3a1)"; }
break_mutant-weakening() {
  perl -0pi -e 's/_UNKNOWN_IS_FREE = True/_UNKNOWN_IS_FREE = False/' corpus/decoys/D115-unknown-plan-read-as-free/proof.py
}
guard_mutant-weakening() { uv run pytest tests/corpus/test_mutants.py -q -k D115; }

claim_mutant-safe() { echo "증명이 주장 밖을 묻게 되면 안전한 변형이 깨져 변이 테스트가 운다 — §3.5 반대 방향"; }
break_mutant-safe() {
  perl -0pi -e 's/(S112 - 거절 방식은 묻지 않는다\n\s+)continue/$1return True/' corpus/decoys/D115-unknown-plan-read-as-free/proof.py
}
guard_mutant-safe() { uv run pytest tests/corpus/test_mutants.py -q -k D115; }

claim_mutant-stale() { echo "decoy 를 고쳐 치환이 빗나가면 변이 테스트가 운다 — 낡은 변이는 원본을 돌려 공허하게 통과한다"; }
break_mutant-stale() {
  perl -0pi -e 's/_TIERS\.get\(plan, "free"\)/_TIERS.get(plan, \x27free\x27)/' corpus/decoys/D115-unknown-plan-read-as-free/decoy.py
}
guard_mutant-stale() { uv run pytest tests/corpus/test_mutants.py -q -k D115; }

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

claim_docs-results-prose() { echo "결과를 옮겨 적은 문서(RESULTS · AI-WORKFLOW)도 README 와 같은 대조를 받는다 — 구별 성공률 옆에 채점자를 적는다 (F5)"; }
break_docs-results-prose() { perl -0pi -e 's/`provable_safety` 의 「구별 성공 11\/60」/「구별 성공 11\/60」/' docs/AI-WORKFLOW.md; }
guard_docs-results-prose() { uv run pytest tests/docs/test_consistency.py -q -k bare_discrimination; }

claim_selection-headline() { echo "README 첫 화면의 「N 대 M — N배」가 생성물의 룰 선택 표와 다르면 테스트가 운다 (F5b)"; }
break_selection-headline() { perl -0pi -e 's/17 대 777/17 대 776/' README.md; }
guard_selection-headline() { uv run pytest tests/docs/test_consistency.py -q -k rule_selection_numbers; }

claim_selection-table() { echo "RESULTS 의 룰 선택 표가 생성물과 다르면 테스트가 운다 — 「같은 계산으로 다시 나온다」를 문장이 아니라 검사로 (F5b)"; }
break_selection-table() { perl -0pi -e 's/\| `ALL` \| 777 \| \*\*17\*\*/| `ALL` | 777 | **18**/' docs/RESULTS.md; }
guard_selection-table() { uv run pytest tests/docs/test_consistency.py -q -k rule_selection_numbers; }

claim_selection-repeats() { echo "「룰 선택」 표의 기본 선택 행은 헤드라인 표와 같은 실행이다 — FP 가 다르면 운다 (이름이 어긋난 채점자가 FP 0 이 되지 않게)"; }
break_selection-repeats() { perl -0pi -e 's/\| `ALL` \| 777 \| 17 \| 777 \|/| `ALL` | 777 | 17 | 0 |/' docs/MEASUREMENTS.md; }
guard_selection-repeats() { uv run pytest tests/docs/test_consistency.py -q -k selection_table_repeats; }

claim_fp-counts-floor() { echo "산문의 FP 대조가 읽는 행이 줄면 운다 — 형식이 바뀌어 공허하게 통과하지 않게"; }
break_fp-counts-floor() { perl -0pi -e 's/^provable_safety(           0   17)/provable-safety$1/m' docs/RESULTS.md; }
guard_fp-counts-floor() { uv run pytest tests/docs/test_consistency.py -q -k fp_counts; }

claim_pair-table() { echo "결과 3 의 짝 판정 표가 생성물의 짝 판정 사다리(ALL · slack 0)와 다르면 테스트가 운다 (F5b)"; }
break_pair-table() { perl -0pi -e 's/\| 1 \| 5 \| \*\*134\*\* \|/| 1 | 5 | **133** |/' docs/RESULTS.md; }
guard_pair-table() { uv run pytest tests/docs/test_consistency.py -q -k pair_verdicts; }

claim_pair-sentence() { echo "「구별 성공 · 과잉 · 미탐지 · 역전」 문장이 생성물(S · slack 0)과 다르면 테스트가 운다 (F5b)"; }
break_pair-sentence() { perl -0pi -e 's/미탐지 140 · 역전 5/미탐지 141 · 역전 5/' docs/RESULTS.md; }
guard_pair-sentence() { uv run pytest tests/docs/test_consistency.py -q -k pair_verdicts; }

claim_pair-block() { echo "결과 5 의 매칭 민감도 블록이 생성물의 사다리와 다르면 테스트가 운다 (F5b · A2a)"; }
break_pair-block() { perl -0pi -e 's/       0    1    5  134   10/       0    1    5  133   10/' docs/RESULTS.md; }
guard_pair-block() { uv run pytest tests/docs/test_consistency.py -q -k pair_verdicts; }

claim_generated() { echo "생성물을 손으로 고치면 --check 가 잡는다 — F5b"; }
break_generated() { perl -0pi -e 's/코퍼스 \*\*(\d+)쌍\*\*/코퍼스 **999쌍**/' docs/MEASUREMENTS.md; }
guard_generated() { uv run codeproof report --check; }

claim_figures-generated() { echo "생성 그림을 손으로 고쳐도 --check 가 잡는다 — 그림은 README 첫 화면에 실린다 (F5b)"; }
break_figures-generated() { perl -0pi -e 's/손으로 고치지 않는다/손으로 고친다/' docs/figures/spread.svg; }
guard_figures-generated() { uv run codeproof report --check; }

claim_figures-beside() { echo "그림은 --out 옆에 그린다 — 고정 경로면 시험 코퍼스의 report 가 저장소 그림을 덮어쓴다"; }
break_figures-beside() { perl -0pi -e 's/Path\(a\.out\)\.parent \/ "figures"/Path("docs\/figures")/' src/codeproof_ai/cli.py; }
guard_figures-beside() { uv run pytest tests/cli/test_commands.py -q -k beside_the_output; }

claim_stale-figure() { echo "더는 만들지 않는 그림이 남으면 --check 가 실패한다 — 문서가 옛 숫자를 계속 싣지 않게 (F5b)"; }
break_stale-figure() { perl -0pi -e 's/if p\.name not in drawn and /if False and /' src/codeproof_ai/cli.py; }
guard_stale-figure() { uv run pytest tests/cli/test_commands.py -q -k no_longer_drawn; }

claim_out-dash() { echo "--out - 는 그림을 그리지 않는다 — 어기면 현재 디렉터리에 figures/ 가 생긴다"; }
break_out-dash() { perl -0pi -e 's/    if out == "-" or not selections:/    if not selections:/' src/codeproof_ai/cli.py; }
guard_out-dash() { uv run pytest tests/cli/test_commands.py -q -k printing_to_stdout; }

claim_pairs-ladder-label() { echo "짝 그림은 slack 사다리에서 판정이 바뀌면 「흔들린다」고 적는다 — 막대 하나로 결론을 내지 않게 (A2a)"; }
break_pairs-ladder-label() { perl -0pi -e 's/moved = len\(set\(tops\)\) > 1/moved = len(set(tops)) > 9/' src/codeproof_ai/eval/figures.py; }
guard_pairs-ladder-label() { uv run pytest tests/eval/test_figures.py -q -k ladder_column; }

claim_pair-ladder-note() { echo "측정값 문서의 짝 판정 사다리가 흔들림을 적는다 — 판정을 바꾸면 report --check 가 운다 (A2a · F5b)"; }
break_pair-ladder-note() { perl -0pi -e 's/            if len\(tops\) > 1\n/            if len(tops) > 9\n/' src/codeproof_ai/eval/report.py; }
guard_pair-ladder-note() { uv run codeproof report --check; }

claim_agents-points() { echo "에이전트 그림은 리뷰어마다 점만 찍는다 — 두 구간을 겹쳐 보는 읽기를 권하지 않게 (F6)"; }
break_agents-points() { perl -0pi -e 's/f"\{_pct\(point\)\}%"/f"{_pct(point)}% [0, 1]"/' src/codeproof_ai/eval/figures.py; }
guard_agents-points() { uv run pytest tests/eval/test_figures.py -q -k points_and_only; }

claim_landing-page() { echo "Pages 첫 페이지가 가리키는 그림은 실제로 있다 — 받은 사람이 파일로 열어도 같다"; }
break_landing-page() { perl -0pi -e 's/src="figures\/spread\.svg"/src="figures\/nope.svg"/' docs/index.html; }
guard_landing-page() { uv run pytest tests/docs/test_consistency.py -q -k its_relative; }

claim_landing-css() { echo "첫 페이지는 CSS 로도 바깥 자원을 부르지 않는다 — 받은 사람이 파일로 열어도 같다"; }
break_landing-css() { perl -0pi -e 's/<style>\n/<style>\n  \@import url("https:\/\/example.com\/x.css");\n/' docs/index.html; }
guard_landing-css() { uv run pytest tests/docs/test_consistency.py -q -k 'TheLandingPage and outside'; }

claim_landing-blob() { echo "첫 페이지의 저장소 문서 링크가 없는 파일을 가리키면 운다 — 이름이 바뀌어도 조용히 깨지지 않게"; }
break_landing-blob() { perl -0pi -e 's/blob\/main\/docs\/VERIFY\.md/blob\/main\/docs\/VERIFY-gone.md/' docs/index.html; }
guard_landing-blob() { uv run pytest tests/docs/test_consistency.py -q -k repository_links; }

claim_landing-numbers() { echo "첫 페이지의 손으로 쓴 문장에는 숫자가 없다 — 숫자는 생성 그림이 든다 (F5b)"; }
break_landing-numbers() { perl -0pi -e 's/보안 규칙만 고르면 같아진다\./보안 규칙만 고르면 같아진다 (45.7배)./' docs/index.html; }
guard_landing-numbers() { uv run pytest tests/docs/test_consistency.py -q -k quotes_no_numbers; }

claim_landing-highlights() { echo "첫 화면의 핵심 발견 카드는 생성물이다 — 손으로 숫자를 고치면 report --check 가 운다 (F5b)"; }
break_landing-highlights() { perl -0pi -e 's/<p class="big">45\.7배<\/p>/<p class="big">45.8배<\/p>/' docs/index.html; }
guard_landing-highlights() { uv run codeproof report --check; }

claim_landing-markers() { echo "첫 화면의 생성 구간 표시는 있어야 한다 — 표시가 사라지면 report 가 조용히 채우기를 멈춘다"; }
break_landing-markers() { perl -0pi -e 's/<!-- \/생성물: 핵심 발견 -->//' docs/index.html; }
guard_landing-markers() { uv run pytest tests/docs/test_consistency.py -q -k highlights_are_generated; }

claim_mutants-unknown() { echo "decoy mutants 는 없는 쌍 접두사를 거절한다 — 맞는 쌍 0개로 공허하게 통과하지 않게"; }
break_mutants-unknown() { perl -0pi -e 's/if unknown := \[p for p in prefixes if p not in names\]:/if unknown := []:/' src/codeproof_ai/cli.py; }
guard_mutants-unknown() { uv run pytest tests/cli/test_commands.py -q -k matches_no_pair; }

# ── 점수판 · 예시 (eval/glance.py) - README 첫 화면의 숫자와 그 숫자를 고른 규칙 ──

claim_readme-scoreboard() { echo "README 첫 화면의 점수판 숫자는 생성물 「점수판」과 같다 — 손으로 옮긴 숫자는 다시 재면 낡는다 (F5b)"; }
break_readme-scoreboard() { perl -0pi -e 's/Claude 64\.7% · Codex 46\.9%/Claude 64.8% · Codex 46.9%/' README.md; }
guard_readme-scoreboard() { uv run pytest tests/docs/test_consistency.py -q -k scoreboard_numbers_match; }

claim_scoreboard-primary() { echo "점수판의 주 지표 줄은 「에이전트 비교」의 주 지표와 같은 계산이다 — 한쪽만 채점을 바꾸면 운다"; }
break_scoreboard-primary() {
  perl -0pi -e 's/verdicts_by_run\(b\.outcomes, samples, ProvableSafetyGrader\(overlap_slack=s\)\)/verdicts_by_run(b.outcomes, samples, ProvableSafetyGrader(overlap_slack=s + 1))/' \
    src/codeproof_ai/eval/glance.py && uv run codeproof report > /dev/null
}
guard_scoreboard-primary() { uv run pytest tests/docs/test_consistency.py -q -k repeats_the_primary; }

claim_misses-complement() { echo "점수판의 「놓쳤다」는 「짚었다」의 여집합이다 — 판정 묶음이 어긋나면 운다"; }
break_misses-complement() {
  perl -0pi -e 's/^MISSED = \(PairVerdict\.UNDER_FLAG, PairVerdict\.REVERSED\)$/MISSED = (PairVerdict.UNDER_FLAG, PairVerdict.REVERSED, PairVerdict.OVER_FLAG)/m' \
    src/codeproof_ai/eval/glance.py && uv run codeproof report > /dev/null
}
guard_misses-complement() { uv run pytest tests/docs/test_consistency.py -q -k complement_of_catches; }

claim_example-rule-slack() { echo "예시 짝은 모든 slack · 모든 회차에서 판정이 같은 짝만 고른다 — slack 0 만 보면 매칭 정책의 산물(D140)이 예시가 된다"; }
break_example-rule-slack() { perl -0pi -e 's/for pair in ladder\.values\(\) for run/for pair in list(ladder.values())[:1] for run/' src/codeproof_ai/eval/glance.py; }
guard_example-rule-slack() { uv run pytest tests/eval/test_glance.py -q; }

claim_near-miss-rule() { echo "첫 화면의 「놓침」 사례는 모든 회차가 한 칸 넓힌 매칭에서 「짚음」으로 옮겨 간 짝이다 — 그 조건을 빼면 운다"; }
break_near-miss-rule() { perl -0pi -e 's/        and all\(run\[p\] in CAUGHT for run in ladder\[step\]\[side\]\)\n//' src/codeproof_ai/eval/glance.py; }
guard_near-miss-rule() { uv run pytest tests/eval/test_glance.py -q -k NearMiss; }

claim_scoreboard-interval() { echo "점수판은 리뷰어마다의 구간을 싣지 않는다 — 구간은 주 지표의 같은 짝 위 차이에만 있다 (F6)"; }
break_scoreboard-interval() { perl -0pi -e 's/f"\{_pct\(share\.strict\)\}%"\)/f"{_pct(share.strict)}% [0, 1]")/' src/codeproof_ai/eval/figures.py; }
guard_scoreboard-interval() { uv run pytest tests/eval/test_figures.py -q -k only_the_primary_difference; }

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

claim_import-rejected() { echo "SARIF · bandit 파서가 버린 지적도 센다 — 버린 것은 미탐지와 구별되지 않는다 (I)"; }
break_import-rejected() {
  perl -0pi -e 's/rejected\.append\(f"\[\{i\}\] \{got\}"\)/pass  # falsify.sh/' \
    src/codeproof_ai/reviewers/formats.py
}
guard_import-rejected() { uv run pytest tests/cli/test_commands.py -q -k sarif_findings_on_other_paths; }

claim_signed-runner() { echo "실행기 판(runner_version)도 설정 지문에 싣는다 — 다른 실행기의 출력을 가른다 (F1)"; }
break_signed-runner() {
  perl -0pi -e 's/\n    "runner_version",//' src/codeproof_ai/reviewers/imported.py
}
guard_signed-runner() { uv run pytest tests/reviewers/test_imported.py -q -k runner_version; }

claim_pack-first-runs() { echo "앞 N회만 묶으면 N회 너머는 묶음에 들어가지 않는다 — N 은 결과를 보기 전에 정한다 (DESIGN §7.10b)"; }
break_pack-first-runs() {
  perl -0pi -e 's/ and \(runs is None or int\(m\["run"\]\) < runs\)//' \
    src/codeproof_ai/reviewers/imported.py
}
guard_pack-first-runs() { uv run pytest tests/cli/test_commands.py -q -k first_runs_packs_only; }

claim_bundle-separators() { echo "묶음은 \\n 으로만 자른다 — 지적 문구 안의 U+2028 이 한 회차를 조각내지 않게 (F6)"; }
break_bundle-separators() {
  perl -0pi -e 's/\.read_text\(encoding="utf-8"\)\.split\("\\n"\):/.read_text(encoding="utf-8").splitlines():/' \
    src/codeproof_ai/reviewers/imported.py
}
guard_bundle-separators() { uv run pytest tests/reviewers/test_imported.py -q -k line_separators; }

claim_pair-difference() { echo "리뷰어 비교는 같은 짝으로 함께 복원추출한다 — 짝이 어긋나면 자기 자신과의 차이에도 폭이 생긴다"; }
break_pair-difference() {
  perl -0pi -e 's/diffs = \[sa\[p\] - sb\[p\] for p in sa\]/diffs = [sa[p] - sb[q] for p, q in zip(sa, reversed(list(sb)), strict=True)]/' \
    src/codeproof_ai/eval/multirun.py
}
guard_pair-difference() { uv run pytest tests/eval/test_multirun.py -q -k against_itself_has_no_width; }

claim_docstring-neutral() { echo "neutral 은 모듈 docstring 의 기전을 실제로 지운다 — 줄 수는 그대로 (DESIGN §7.10c)"; }
break_docstring-neutral() {
  perl -0pi -e 's/\n    tree = ast\.parse\(source\)\n    first = /\n    return source\n    tree = ast.parse(source)\n    first = /' \
    src/codeproof_ai/eval/export.py
}
guard_docstring-neutral() { uv run pytest tests/eval/test_export.py -q -k keeps_its_lines; }

claim_signed-docstrings() { echo "docstring 손잡이도 설정 지문에 싣는다 — keep 과 neutral 이 한 설정으로 읽히지 않게 (F1)"; }
break_signed-docstrings() {
  perl -0pi -e 's/\n    "docstrings",[^\n]*//' src/codeproof_ai/reviewers/imported.py
}
guard_signed-docstrings() { uv run pytest tests/reviewers/test_imported.py -q -k docstring_knob; }

claim_resume-docstrings() { echo "손잡이가 다른 실행은 한 출력 디렉터리에 이어 쓰지 않는다 — 섞이면 한 실행이 아니다 (F1)"; }
break_resume-docstrings() {
  perl -0pi -e 's/\n    "docstrings",[^\n]*//' scripts/agent_output.py
}
guard_resume-docstrings() { uv run pytest tests/scripts/test_agent_output.py -q -k different_docstring_knob; }

claim_runner-docstrings() { echo "손잡이 이전의 내보내기로는 돌지 않는다 — 빈 값을 기록하면 keep 과 neutral 이 같아진다"; }
break_runner-docstrings() {
  perl -0pi -e 's/\n\[\[ -n \$DOCSTRINGS \]\] \|\| die[^\n]*//' scripts/review-with-agent.sh
}
guard_runner-docstrings() { uv run pytest tests/scripts/test_agent_output.py -q -k without_the_knob_is_refused; }

claim_compare-one-axis() { echo "리뷰어와 손잡이가 둘 다 다른 실행은 비교하지 않는다 — 어느 쪽 효과인지 말할 수 없다 (DESIGN §7.10c)"; }
break_compare-one-axis() {
  perl -0pi -e 's/\(a\.docstrings != b\.docstrings\) == 1/(a.docstrings != b.docstrings) >= 1/' \
    src/codeproof_ai/eval/report.py
}
guard_compare-one-axis() { uv run pytest tests/cli/test_commands.py -q -k one_axis_only; }

claim_widened-twin() { echo "보조 정의의 twin 정답은 미끼까지 넓어진다 — decoy 의 미끼~가드와 대칭 (DESIGN §7.10c ③)"; }
break_widened-twin() {
  perl -0pi -e 's/        out\.extend\(j1 \+ \(ln - 1 - i1\) \+ 1 for ln in range\(start, end \+ 1\) if i1 < ln <= i2\)/        pass/' \
    src/codeproof_ai/corpus/decoy.py
}
guard_widened-twin() { uv run pytest tests/eval/test_widened_twin.py -q -k changes_some_twins; }

claim_report-widened() { echo "에이전트 비교는 보조 정의의 짝 차이도 싣는다 — 선언한 보조를 빼먹지 않는다 (DESIGN §7.10c)"; }
break_report-widened() {
  perl -0pi -e 's/    if not widened:\n        return \[\]\n    g = /    if True:\n        return []\n    g = /' \
    src/codeproof_ai/eval/report.py
}
guard_report-widened() { uv run pytest tests/cli/test_commands.py -q -k two_agents_get_a_paired; }

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
  perl -0pi -e 's/available_runs\(s\.sample_id\) >= runs\}/available_runs(s.sample_id) > 0}  # falsify.sh/' \
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
  perl -0pi -e 's/(collected, box, name=src\.name, kind=ReviewerKind\.AGENT, )allow_partial=False$/${1}allow_partial=True  # falsify.sh/m' \
    src/codeproof_ai/cli.py
}
guard_report-partial() { uv run pytest tests/cli/test_commands.py -q -k short_agent_runs; }

claim_pack-partial() { echo "모자란 회차는 묶지 않는다 — 묶고 나면 report 에 가서야 걸린다 (F6)"; }
break_pack-partial() {
  perl -0pi -e 's/(labeled, src, name=out\.name, kind=ReviewerKind\.AGENT, )allow_partial=False, first_runs=runs/${1}allow_partial=True, first_runs=runs  # falsify.sh/' \
    src/codeproof_ai/cli.py
}
guard_pack-partial() { uv run pytest tests/cli/test_commands.py -q -k pack_refuses_short; }

claim_pack-leftover() { echo "묶음 자리에 옛 파일이 있으면 묶지 않는다 — 섞이면 그대로 커밋된다"; }
break_pack-leftover() {
  perl -0pi -e 's/^    if extra:\n/    if False:  # falsify.sh\n/m' src/codeproof_ai/cli.py
}
guard_pack-leftover() { uv run pytest tests/cli/test_commands.py -q -k pack_does_not_mix; }

claim_mix-decoy-unit() { echo "분류 간 차이는 decoy 단위로 판정한다 — 한 decoy 의 지적 여럿을 독립 시행으로 세지 않는다 (F5a)"; }
break_mix-decoy-unit() {
  perl -0pi -e 's/tuple\(\(k\.sample_rate\.successes, k\.sample_rate\.total\) for k in self\.kinds if k\.samples\)/tuple((k.rate.successes, k.rate.total) for k in self.kinds if k.samples)/' \
    src/codeproof_ai/eval/mix.py
}
guard_mix-decoy-unit() { uv run pytest tests/eval/test_mix.py -q -k loud_decoy; }

claim_plan-coverage() { echo "새 쌍은 계획한 빈 칸에만 들어간다 — 도출한 가드 위치로 센다 (DESIGN §3.5)"; }
break_plan-coverage() {
  perl -0pi -e 's/TrapKind\.CALLER_HELD_LOCK: \{GuardShape\.CALLER: 10\}/TrapKind.CALLER_HELD_LOCK: {GuardShape.CALLER: 3}/' \
    src/codeproof_ai/corpus/plan.py
}
guard_plan-coverage() { uv run pytest tests/corpus/test_plan.py -q -k planned_cell; }

claim_plan-design() { echo "DESIGN 의 칸별 목표는 corpus/plan.py 와 같다 — 편차를 한쪽에만 적지 않는다 (DESIGN §3.5)"; }
break_plan-design() { perl -0pi -e 's/(caller_held_lock` \| \S+ \| 4\S+?\*\*)10(\*\*)/${1}9$2/' docs/DESIGN.md; }
guard_plan-design() { uv run pytest tests/docs/test_consistency.py -q -k design_table_targets; }

claim_report-collected() { echo "에이전트 실행은 잰 샘플로만 재생한다 — 코퍼스가 자라도 숫자가 그대로다 (F6)"; }
break_report-collected() {
  perl -0pi -e 's/^(\s+)collected, box, name=src\.name/${1}samples, box, name=src.name/m' src/codeproof_ai/cli.py
}
guard_report-collected() { uv run pytest tests/cli/test_commands.py -q -k stay_on_the_samples; }

claim_report-packed-samples() { echo "잰 샘플 기록이 없는 묶음은 싣지 않는다 — 늘어난 코퍼스와 끊긴 실행을 가를 수 없다 (F6)"; }
break_report-packed-samples() {
  perl -0pi -e 's/    if not \(isinstance\(packed, list\)/    if False and not (isinstance(packed, list)/' src/codeproof_ai/cli.py
}
guard_report-packed-samples() { uv run pytest tests/cli/test_commands.py -q -k without_packed_samples; }

claim_report-bundle-record() { echo "묶음의 행은 잰 샘플 기록과 같아야 한다 — 빠지면 끊긴 실행, 남으면 늘어난 쌍으로 잘못 적힌다 (F6)"; }
break_report-bundle-record() { perl -0pi -e 's/^    if rows != listed:$/    if False:  # falsify.sh/m' src/codeproof_ai/cli.py; }
guard_report-bundle-record() { uv run pytest tests/cli/test_commands.py -q -k differs_from_its_record; }

claim_report-corpus-gone() { echo "잰 샘플이 코퍼스에서 빠지면 싣지 않는다 — 빼고 재생하면 비교 대상이 조용히 준다 (F6)"; }
break_report-corpus-gone() { perl -0pi -e 's/^    if gone:$/    if False:  # falsify.sh/m' src/codeproof_ai/cli.py; }
guard_report-corpus-gone() { uv run pytest tests/cli/test_commands.py -q -k missing_from_the_corpus; }

claim_report-half-pair() { echo "잰 샘플 목록 안에서 짝이 닫혀 있어야 한다 — 반쪽 짝은 채점에서 조용히 빠진다 (F5 · F6)"; }
break_report-half-pair() { perl -0pi -e 's/^    if half:$/    if False:  # falsify.sh/m' src/codeproof_ai/cli.py; }
guard_report-half-pair() { uv run pytest tests/cli/test_commands.py -q -k half_pair_in_the_record; }

claim_compare-same-samples() { echo "잰 샘플이 다른 두 실행은 비교하지 않는다 — 한쪽에만 있는 짝을 빼면 비교 대상이 바뀐다 (F6)"; }
break_compare-same-samples() {
  perl -0pi -e 's/return _one_axis\(a, b\) and _measured\(a\) == _measured\(b\)/return _one_axis(a, b)/' src/codeproof_ai/eval/report.py
}
guard_compare-same-samples() { uv run pytest tests/cli/test_commands.py -q -k different_samples; }

claim_compare-skip-note() { echo "잰 샘플이 달라 뺀 비교는 생성물에 적는다 — 말없이 빼면 비교가 왜 없는지 모른다"; }
break_compare-skip-note() {
  perl -0pi -e 's/if _one_axis\(a, b\) and _measured\(a\) != _measured\(b\)/if False/' src/codeproof_ai/eval/report.py
}
guard_compare-skip-note() { uv run pytest tests/cli/test_commands.py -q -k different_samples; }

claim_pack-records-samples() { echo "pack 은 묶은 샘플을 기록에 적는다 — report 가 그 샘플로만 재생한다 (F6)"; }
break_pack-records-samples() { perl -0pi -e 's/^    record\["packed_samples"\] = .*\n//m' src/codeproof_ai/cli.py; }
guard_pack-records-samples() { uv run pytest tests/cli/test_commands.py -q -k records_the_samples; }

claim_report-digests() { echo "잰 뒤 코드가 바뀐 샘플이 든 묶음은 싣지 않는다 — 옛 지적이 새 코드로 채점된다 (DESIGN §9 의 5)"; }
break_report-digests() {
  perl -0pi -e 's/^    if not \(isinstance\(digests, dict\) and set\(digests\) == listed\):$/    return None  # falsify.sh\n$&/m' src/codeproof_ai/cli.py
}
guard_report-digests() { uv run pytest tests/cli/test_commands.py -q -k "changed_after_measuring or without_packed_digests"; }

claim_pack-records-digests() { echo "pack 은 묶은 샘플마다 잰 코드의 지문을 적는다 — 없으면 report 가 바뀐 코드를 알아보지 못한다 (DESIGN §9 의 5)"; }
break_pack-records-digests() { perl -0pi -e 's/^    record\["packed_digests"\] = .*\n//m' src/codeproof_ai/cli.py; }
guard_pack-records-digests() { uv run pytest tests/cli/test_commands.py -q -k records_the_samples; }

claim_pack-measured-code() { echo "pack · import 는 지금 코드로 잰 것이 아닌 회차를 싣지 않는다 — 옛 출력이 새 지문으로 묶인다 (DESIGN §9 의 5)"; }
break_pack-measured-code() { perl -0pi -e 's/^        if not words or words\[0\] != current\[sid\]:$/        if False:  # falsify.sh/m' src/codeproof_ai/cli.py; }
guard_pack-measured-code() { uv run pytest tests/cli/test_commands.py -q -k "not_measured_on_this_code or measured_on_other_code"; }

claim_runner-measured-code() { echo "실행기는 지문 없는 내보내기로 출력을 쓰지 않는다 — 무엇을 쟀는지 모르는 출력이 남는다 (DESIGN §9 의 5)"; }
break_runner-measured-code() { perl -0pi -e 's/^    raise RefusedError\(msg\)\n\n\ndef last_findings_object/    return "0" * 64  # falsify.sh\n\n\ndef last_findings_object/m' scripts/agent_output.py; }
guard_runner-measured-code() { uv run pytest tests/scripts/test_agent_output.py -q -k "without_a_digest or every_box_needs or without_sample_digests"; }

claim_pack-stray-samples() { echo "pack 은 코퍼스 밖 샘플이 섞인 실행을 묶지 않는다 — 검증 안 된 샘플이 기록에 실린다 (F6)"; }
break_pack-stray-samples() { perl -0pi -e 's/^    if stray:$/    if False:  # falsify.sh/m' src/codeproof_ai/cli.py; }
guard_pack-stray-samples() { uv run pytest tests/cli/test_commands.py -q -k samples_outside_the_corpus; }

claim_sarif-end() { echo "가져온 SARIF 지적도 보고 범위의 끝까지 싣는다 — 시작 줄만 남으면 직접 실행과 다른 자리가 된다 (A2a)"; }
break_sarif-end() {
  perl -0pi -e 's/^    if end_column >= 1:$/    if False:  # falsify.sh/m; s/^    elif end_line > line:$/    elif False:  # falsify.sh/m' \
    src/codeproof_ai/reviewers/formats.py
}
guard_sarif-end() { uv run pytest tests/reviewers/test_formats.py -q -k "end_of_region or end_line_without"; }

claim_sarif-category() { echo "가져온 Ruff SARIF 도 직접 실행과 같은 출처의 분류를 쓴다 — OTHER 로 두면 관례 주장이 FP · 탐지가 된다 (F4a)"; }
break_sarif-category() {
  perl -0pi -e 's/category=known\.get\(rule_id, Category\.OTHER\),/category=Category.OTHER,  # falsify.sh/' \
    src/codeproof_ai/reviewers/formats.py
}
guard_sarif-category() { uv run pytest tests/reviewers/test_unified.py -q -k every_finding_and_judgment; }

claim_sarif-other-tool() { echo "다른 도구가 낸 SARIF 는 룰 id 가 같아도 Ruff 의 분류를 빌려 오지 않는다 — 모르는 도구는 결함 주장이다 (F4a)"; }
break_sarif-other-tool() {
  perl -0pi -e 's/known = self\._categories\.get\(str\(driver\.get\("name"\) or ""\)\.lower\(\), \{\}\)/known = next(iter(self._categories.values()), {})  # falsify.sh/' \
    src/codeproof_ai/reviewers/formats.py
}
guard_sarif-other-tool() { uv run pytest tests/reviewers/test_formats.py -q -k another_tool_with_the_same_rule_id; }

claim_bandit-range() { echo "bandit 지적의 범위는 line_range 다 — 대표 줄에 다른 줄의 열을 붙이지 않는다 (A2a · B1)"; }
break_bandit-range() { perl -0pi -e 's/^    if not lines:$/    if True:  # falsify.sh/m' src/codeproof_ai/reviewers/formats.py; }
guard_bandit-range() { uv run pytest tests/reviewers/test_formats.py -q -k "reported_range_is or first_line_of_the_range"; }

claim_twin-convention() { echo "twin 쪽에서도 관례 주장을 탐지로 세지 않는다 — 결함 구간에 걸린 docstring 지적이 「구별 성공」이 된다 (F4a)"; }
break_twin-convention() {
  perl -0pi -e 's/^        if not o\.finding\.category\.is_defect_claim:  # twin 쪽도 같다 \(F4a\)$/        if False:  # falsify.sh/m' \
    src/codeproof_ai/eval/grading/safety.py
}
guard_twin-convention() { uv run pytest tests/eval/test_convention_claims.py -q -k twin_defect_is_not_a_detection; }

claim_twin-convention-paired() { echo "paired_fix 도 twin 쪽 관례 주장을 탐지로 세지 않는다 — 두 채점자의 경계가 같다 (F4a)"; }
break_twin-convention-paired() {
  perl -0pi -e 's/^        if not o\.finding\.category\.is_defect_claim:  # twin 쪽도 같다 \(F4a\)$/        if False:  # falsify.sh/m' \
    src/codeproof_ai/eval/grading/paired.py
}
guard_twin-convention-paired() { uv run pytest tests/eval/test_convention_claims.py -q -k positive_is_not_a_detection; }

claim_repro-unknown() { echo "저장 기록에는 리뷰어 종류가 없다 — history --repro 는 갈라진 결과를 한쪽 해석으로 짐작하지 않는다 (F1)"; }
break_repro-unknown() { perl -0pi -e 's/_print_repro\(check, None\)/_print_repro(check, False)  # falsify.sh/' src/codeproof_ai/cli.py; }
guard_repro-unknown() { uv run pytest tests/cli/test_commands.py -q -k repro_does_not_guess; }

claim_repro-kind() { echo "재현성 해석은 리뷰어가 신고한 종류로 고른다 — 정적분석기가 갈라지면 드리프트다 (F1 · A2)"; }
break_repro-kind() { perl -0pi -e 's/_print_repro\(check, kind\.is_deterministic\)/_print_repro(check, False)  # falsify.sh/' src/codeproof_ai/cli.py; }
guard_repro-kind() { uv run pytest tests/cli/test_commands.py -q -k "diverged_static_runs or diverged_imported_runs"; }

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
  # 고친 상태의 FP 는 20 이하다 [실측 · 150쌍 · 17]. 회귀를 넣으면 수백 건으로 뛴다 [실측 · 150쌍 · 258].
  # 착수 조건: 쌍이 늘어 고친 상태가 20 을 넘으면 깨끗한 트리에서 울어 「가드 고장」으로 보고된다 - 그때 상대 비교로 바꾼다.
  local fp
  fp=$(uv run codeproof measure --analyzers ruff --ruff-select ALL --store none 2>/dev/null \
       | awk '/^ *provable_safety/ {print $3; exit}')
  echo "회귀 상태의 provable_safety FP: ${fp}건 (고친 상태의 값은 docs/MEASUREMENTS.md · 문턱 20)"
  [[ -n "$fp" && "$fp" -le 20 ]]   # 20 이하로 남아 있으면 회귀가 재현되지 않은 것 → 가드 침묵
}

# ── 코퍼스가 둘이 된 뒤 (DESIGN §7.10d) - 접두사 · 목록이 다른 코퍼스를 조용히 건너뛰는 자리 ──

claim_pair-discovery() { echo "쌍은 접두사가 아니라 폴더 구조로 찾는다 — D* 만 찾으면 codex 코퍼스(XC…)에서 변이 0개로 공허하게 통과한다 (DESIGN §7.10d)"; }
break_pair-discovery() {
  perl -0pi -e 's/if p\.is_dir\(\) and not p\.name\.startswith\("_"\)\)/if p.is_dir() and p.name.startswith("D"))  # falsify.sh/' \
    src/codeproof_ai/corpus/decoy.py
}
guard_pair-discovery() { uv run pytest tests/corpus/test_decoy_validator.py tests/cli/test_commands.py -q -k structure_not_prefix; }

claim_mutant-alias() { echo "변이 별칭은 쌍 이름 전체로 만든다 — 앞 4글자로 자르면 XC001~XC009 가 한 별칭을 나눠 쓴다 (DESIGN §7.10d)"; }
break_mutant-alias() { perl -0pi -e 's/pair_dir\.name\.replace\("-", "_"\), \*map/pair_dir.name[:4], *map/' src/codeproof_ai/corpus/mutants.py; }
guard_mutant-alias() { uv run pytest tests/corpus/test_mutants.py -q -k whole_pair_name; }

claim_template-kinds() { echo "템플릿은 분류를 전부 적는다 — 템플릿을 보고 쓰는 저자는 빠진 분류를 모른다 (DESIGN §7.10d)"; }
break_template-kinds() { perl -0pi -e 's/^#   frozen_after_init .*\n//m' corpus/decoys/_TEMPLATE/meta.toml; }
guard_template-kinds() { uv run pytest tests/docs/test_consistency.py -q -k template_lists_every_kind; }

claim_lint-exclude() { echo "코퍼스는 린트하지 않는다 — 제외에서 빠진 코퍼스는 ruff --fix 가 쌍을 고쳐 쓴다 (G2 · DESIGN §7.10d)"; }
break_lint-exclude() { perl -0pi -e 's/"corpus\/xauthor", //' pyproject.toml; }
guard_lint-exclude() { uv run pytest tests/corpus/test_not_linted.py -q; }

# ── codex 가 쓴 쌍의 관문 (DESIGN §7.10d) - 규칙마다 한 줄을 무력화하면 그 규칙의 시험이 운다 ──
_GATE=src/codeproof_ai/eval/gate.py

claim_gate-directions() { echo "관문은 약화와 안전한 변형을 하나 이상씩 요구한다 — 약화만 있으면 증명이 주장 대신 구현을 묻는지 못 본다 (§3.5)"; }
break_gate-directions() { perl -0pi -e 's/if not any\(m\.expect_broken for m in mutants\) or all\(m\.expect_broken for m in mutants\):/if not mutants:  # falsify.sh/' "$_GATE"; }
guard_gate-directions() { uv run pytest tests/eval/test_gate.py -q -k both_directions; }

claim_gate-survivor() { echo "관문은 증명이 놓친 약화를 실패로 센다 — 경쟁 약화는 race_runs 번 모두 깨져야 한다 (§7.10d)"; }
break_gate-survivor() { perl -0pi -e 's/        if broke != \(runs if mutant\.expect_broken else 0\):/        if False:  # falsify.sh/' "$_GATE"; }
guard_gate-survivor() { uv run pytest tests/eval/test_gate.py -q -k weakening_that_survives; }

claim_gate-neutral() { echo "관문은 neutral 내보내기가 모듈 docstring 한 줄만 바꾸는지 본다 — 줄 번호가 정답 구간이다 (§7.10c)"; }
break_gate-neutral() { perl -0pi -e 's/        if problem:\n            problems\.append/        if False:  # falsify.sh\n            problems.append/' "$_GATE"; }
guard_gate-neutral() { uv run pytest tests/eval/test_gate.py -q -k "test_neutral and not problem"; }

claim_gate-prose() { echo "관문은 산문 주석을 단서로 거부한다 — 도구 지시만 받는다 (§7.10d 단서)"; }
break_gate-prose() { perl -0pi -e 's/if tok\.type == tokenize\.COMMENT and not _DIRECTIVE\.match\(tok\.string\)/if False  # falsify.sh/' "$_GATE"; }
guard_gate-prose() { uv run pytest tests/eval/test_gate.py -q -k "cues_prose_comment or test_prose_comments"; }

claim_gate-docstring() { echo "관문은 guard_lines 밖의 함수 · 클래스 docstring 을 단서로 거부한다 (§7.10d 단서)"; }
break_gate-docstring() { perl -0pi -e 's/    outside = \[start for start, end, _ in decoy_docs if end < guard\.start or start > guard\.end\]/    outside: list[int] = []  # falsify.sh/' "$_GATE"; }
guard_gate-docstring() { uv run pytest tests/eval/test_gate.py -q -k docstring_outside_the_guard; }

claim_gate-twin-docstring() { echo "관문은 twin 이 decoy 에 없는 docstring 을 더하면 거부한다 — 지켜지지 않는 약속이 단서다 (§7.10c)"; }
break_gate-twin-docstring() { perl -0pi -e 's/if added := \[start for start, _, text in twin_docs if text not in known\]:/if added := []:  # falsify.sh/' "$_GATE"; }
guard_gate-twin-docstring() { uv run pytest tests/eval/test_gate.py -q -k twin_adds_a_docstring; }

claim_gate-plan() { echo "관문은 분류가 정한 칸 밖의 가드 위치를 거부한다 — 이름만 그 분류인 쌍이다 (corpus/plan.py)"; }
break_gate-plan() { perl -0pi -e 's/    if shape in cells:/    if True:  # falsify.sh/' "$_GATE"; }
guard_gate-plan() { uv run pytest tests/eval/test_gate.py -q -k test_plan; }

# ── 정답 없는 코드의 리뷰 보고서 (codeproof review) - 지적과 근거만 낸다 ──
_REV=src/codeproof_ai/review.py

claim_review-unlabeled() { echo "정답이 없는 샘플은 채점하지 않는다 — 결함 라벨이 없다고 음성으로 채점하면 지적이 전부 FP 가 된다 (F4)"; }
break_review-unlabeled() { perl -0pi -e 's/    if graders and unlabeled:/    if False:/' src/codeproof_ai/eval/runner.py; }
guard_review-unlabeled() { uv run pytest tests/review/test_review.py -q -k unlabeled_samples_are_not_graded; }

claim_review-no-defect-claim() { echo "리뷰 보고서는 결함 확인이라고 쓰지 않는다 — 지적과 근거일 뿐이다 (F4 · E2)"; }
break_review-no-defect-claim() { perl -0pi -e 's/"> 결함을 확인하는 보고서가 아니다\. 리뷰어의 지적과, 지적마다 모은 근거를 보여 준다\.",/"> 확인된 결함과 근거다.",/' "$_REV"; }
guard_review-no-defect-claim() { uv run pytest tests/review/test_review.py -q -k never_claims; }

claim_review-self-corroboration() { echo "교차 확인자에는 다른 도구의 지적만 넘긴다 — 자기 확인은 항등식이다 (F7)"; }
break_review-self-corroboration() { perl -0pi -e 's/if other != name for f in fs\]/for f in fs]/' "$_REV"; }
guard_review-self-corroboration() { uv run pytest tests/review/test_review.py -q -k only_by_another_tool; }

claim_review-static-citation() { echo "정적분석기의 지적에는 인용 검증을 걸지 않는다 — 파일을 직접 읽어 늘 맞으니 근거를 부풀린다"; }
break_review-static-citation() { perl -0pi -e 's/        if not kinds\[name\]\.is_deterministic:/        if True:/' "$_REV"; }
guard_review-static-citation() { uv run pytest tests/review/test_review.py -q -k reviewed_without_grading; }

_XA=scripts/xauthor.py
_XR=scripts/xauthor_run.py

claim_xauthor-login-shell() { echo "저자 exec 는 로그인 셸을 끈다 — path_helper 가 venv 를 /usr/bin 뒤로 밀어 python3 가 시스템 판이 된다 (§7.10d 수집 전 수정 ⑤)"; }
break_xauthor-login-shell() { perl -0pi -e 's/        "-c", "allow_login_shell=false",\n//' "$_XA"; }
guard_xauthor-login-shell() { uv run pytest tests/scripts/test_xauthor.py -q -k login_shell; }

claim_xauthor-silent-probe() { echo "점검표 항목이 아무것도 찍지 않으면 통과가 아니다 — 막힌 것과 안 돈 것이 같아 보인다 (§7.10d 상자)"; }
break_xauthor-silent-probe() { perl -0pi -e 's/return "OK" if f"CANARY-OK-\{name\}" in lines and /return "OK" if /' "$_XA"; }
guard_xauthor-silent-probe() { uv run pytest tests/scripts/test_xauthor.py -q -k "TestJudgeCheck or marker_in_the_command"; }

claim_xauthor-unrun() { echo "카나리에서 시킨 명령이 보이지 않으면 「안 돌림」이다 — 건너뛰거나 고친 명령을 「막혔다」로 읽지 않는다 (§7.10d 상자)"; }
break_xauthor-unrun() { perl -0pi -e 's/verdict_of\(name, out\) if mine else "안 돌림"/verdict_of(name, out) if mine else "OK"/' "$_XA"; }
guard_xauthor-unrun() { uv run pytest tests/scripts/test_xauthor.py -q -k skipped_command; }

claim_xauthor-probe-collision() { echo "카나리는 명령을 표지로도 가른다 — ls <홈> 은 ls <홈>/.codex 안에도 있어 남의 출력을 읽는다 (§7.10d 상자)"; }
break_xauthor-probe-collision() { perl -0pi -e 's/ and marker\.search\(cmd\)/  # falsify.sh/' "$_XA"; }
guard_xauthor-probe-collision() { uv run pytest tests/scripts/test_xauthor.py -q -k inside_another_command; }

claim_xauthor-vacuous-loop() { echo "쓰기 가능 폴더를 하나도 시도하지 않은 점검은 성립하지 않는다 — 시도 0 은 「쓴 곳 없음」과 같아 보인다 (§7.10d 상자)"; }
break_xauthor-vacuous-loop() { perl -0pi -e 's/ and w == 0 and n > 0/ and w == 0/' "$_XA"; }
guard_xauthor-vacuous-loop() { uv run pytest tests/scripts/test_xauthor.py -q -k "tried-nothing or loop-did-not-run"; }

claim_xauthor-input-roles() { echo "카나리는 developer 입력의 흔적도 센다 — 기억 · 지시 파일은 그 자리로 들어온다 (§7.10d 상자)"; }
break_xauthor-input-roles() { perl -0pi -e 's/\("developer", "user", "system"\)/("user", "system")/' "$_XA"; }
guard_xauthor-input-roles() { uv run pytest tests/scripts/test_xauthor.py -q -k developer_input; }

claim_xauthor-var-tmp() { echo "프로필은 /private/var/tmp 를 막는다 — 빼면 그곳만 쓰기 · 읽기가 됐다 (§7.10d 상자)"; }
break_xauthor-var-tmp() { perl -0pi -e 's/\x27"\/private\/var\/tmp"="none"\}\x27/\x27}\x27/' "$_XA"; }
guard_xauthor-var-tmp() { uv run pytest tests/scripts/test_xauthor.py -q -k declared_allowlist; }

claim_xauthor-verbatim() { echo "점검표에는 따옴표 · \$ 가 없다 — codex 가 그대로 보고하는 것을 본 모양은 홑따옴표로 감싼 명령뿐이다 (§7.10d 상자)"; }
break_xauthor-verbatim() { perl -0pi -e 's/\("BOX-WRITE", "touch probe\.txt", True\)/("BOX-WRITE", "touch \$TMPDIR\/probe.txt", True)/' "$_XA"; }
guard_xauthor-verbatim() { uv run pytest tests/scripts/test_xauthor.py -q -k no_quotes; }

claim_xauthor-sandbox-flag() { echo "저자 exec 에 --sandbox 를 주지 않는다 — 주면 프로필 대신 옛 workspace-write 가 조용히 걸린다 (§7.10d 수집 전 수정 ⑥)"; }
break_xauthor-sandbox-flag() { perl -0pi -e 's/        "--color", "never", "-C", str\(box\),/        "--sandbox", "workspace-write", "--color", "never", "-C", str(box),/' "$_XA"; }
guard_xauthor-sandbox-flag() { uv run pytest tests/scripts/test_xauthor.py -q -k sandbox_flag; }

claim_xauthor-inventory-ids() { echo "카나리 공개 요약의 session_meta 는 키만 싣는다 — 계정 식별자가 든다 (§7.10d 수집 전 수정 ⑦)"; }
break_xauthor-inventory-ids() { perl -0pi -e 's/line = f"\{kind\} \(\{len\(text\)\}자\): 키 \{\x27, \x27\.join\(sorted\(payload\)\)\}"/line = f"{kind} ({len(text)}자): {text[:160]}"/' "$_XA"; }
guard_xauthor-inventory-ids() { uv run pytest tests/scripts/test_xauthor.py -q -k account_ids; }

claim_xauthor-builtin-instructions() { echo "카나리 흔적 집계는 codex 내장 지시만 뺀다 — session_meta 를 통째로 빼면 그 밖의 흔적을 놓친다 (§7.10d 수집 전 수정 ⑦)"; }
break_xauthor-builtin-instructions() { perl -0pi -e 's/rest = \{k: v for k, v in payload\.items\(\) if k != "base_instructions"\}/rest = {}/' "$_XA"; }
guard_xauthor-builtin-instructions() { uv run pytest tests/scripts/test_xauthor.py -q -k builtin_instructions; }

claim_xauthor-pair-leak() { echo "저자가 상자에서 읽는 하네스 소스에 claude 쌍 번호 · 이름이 없다 — venv 는 읽기 허용이다 (§7.10d 「쓰는 입력」)"; }
break_xauthor-pair-leak() { perl -0pi -e 's/\[실측\] 두 단계 건너 부르는 가드가/[실측] D051 처럼 두 단계 건너 부르는 가드가/' src/codeproof_ai/corpus/shape.py; }
guard_xauthor-pair-leak() { uv run pytest tests/scripts/test_xauthor.py -q -k claude_pair; }

claim_xauthor-pair-leak-readme() { echo "README 도 저자 상자에서 읽힌다(wheel METADATA) — claude 쌍 번호가 들어가면 운다 (§7.10d)"; }
break_xauthor-pair-leak-readme() { perl -0pi -e 's/^# CodeProof AI/# CodeProof AI D051/' README.md; }
guard_xauthor-pair-leak-readme() { uv run pytest tests/scripts/test_xauthor.py -q -k claude_pair; }

claim_xauthor-run-credit() { echo "크레딧으로 끊긴 세션은 시도로 세지 않는다 — 못 보면 끊긴 시도가 쌍을 버리게 한다 (§7.10d 「시도 · 렌즈」)"; }
break_xauthor-run-credit() { perl -0pi -e 's/CREDITS = "out of credits"/CREDITS = "credits exhausted"/' "$_XR"; }
guard_xauthor-run-credit() { uv run pytest tests/scripts/test_xauthor_run.py -q -k credit_cut; }

claim_xauthor-run-repro() { echo "재현은 마지막 줄이 정확히 REPRODUCED 일 때만 — NOT REPRODUCED 를 세면 맞는 쌍을 버린다 (§7.10d)"; }
break_xauthor-run-repro() { perl -0pi -e 's/lines\[-1\] == "REPRODUCED"/lines[-1].endswith("REPRODUCED")/' "$_XR"; }
guard_xauthor-run-repro() { uv run pytest tests/scripts/test_xauthor_run.py -q -k exact_last_line; }

claim_xauthor-run-kind() { echo "하네스는 맡긴 분류인지 본다 — 안 보면 저자가 다른 분류로 칸을 채운다 (§7.10d)"; }
break_xauthor-run-kind() { perl -0pi -e 's/if meta\.get\("trap_kind"\) != kind:/if False:/' "$_XR"; }
guard_xauthor-run-kind() { uv run pytest tests/scripts/test_xauthor_run.py -q -k different_kind; }

claim_xauthor-run-budget() { echo "1단계는 크레딧 창 여섯 개를 넘게 쓰면 멈춘다 (§7.10d 「1단계 · 타당성」)"; }
break_xauthor-run-budget() { perl -0pi -e 's/return windows_used\(out\) > MAX_WINDOWS/return windows_used(out) > MAX_WINDOWS + 1/' "$_XR"; }
guard_xauthor-run-budget() { uv run pytest tests/scripts/test_xauthor_run.py -q -k seventh; }

claim_xauthor-run-frozen() { echo "저자 프롬프트는 커밋한 판에서 바꾸지 않는다 (§7.10d 「쓰는 입력」)"; }
break_xauthor-run-frozen() { perl -0pi -e 's/\z/\n- 하나 더.\n/' results/xauthor/author_prompt.md; }
guard_xauthor-run-frozen() { uv run pytest tests/scripts/test_xauthor_run.py -q -k committed_ones; }

claim_xauthor-run-restore() { echo "끊긴 세션은 그 세션 전의 상자로 되돌린다 — 안 되돌리면 「처음부터 다시」가 아니다 (§7.10d)"; }
break_xauthor-run-restore() { perl -0pi -e 's/        shutil\.rmtree\(box, ignore_errors=True\)\n        shutil\.copytree\(snap, box, symlinks=True\)\n/        pass\n/' "$_XR"; }
guard_xauthor-run-restore() { uv run pytest tests/scripts/test_xauthor_run.py -q -k box_restored; }

claim_xauthor-run-refused() { echo "안전 필터 거절은 1급 기록이다 — 못 보면 감사 결과를 못 읽어 멈추거나 거절된 쓰기를 시도로 센다 (§7.10d 수집 중 보정)"; }
break_xauthor-run-refused() { perl -0pi -e 's/REFUSED = "content was flagged"/REFUSED = "content was blocked"/' "$_XR"; }
guard_xauthor-run-refused() { uv run pytest tests/scripts/test_xauthor_run.py -q -k refus; }

claim_xauthor-run-refused-kind() { echo "거절 하나로 그 분류를 닫는다 — 안 닫으면 같은 쓰기 요청을 다시 보낸다 (§7.10d 수집 중 보정)"; }
break_xauthor-run-refused-kind() { perl -0pi -e 's/    refused = "refused" in outcomes\n/    refused = False\n/' "$_XR"; }
guard_xauthor-run-refused-kind() { uv run pytest tests/scripts/test_xauthor_run.py -q -k kind_done; }

claim_xauthor-run-refused-resume() { echo "끝난 세션이 거절이면 이어 돌 때도 거절로 읽는다 — 못 읽으면 거절을 모르던 기록(XC010)이 다시 멈춘다 (§7.10d 수집 중 보정)"; }
break_xauthor-run-refused-resume() { perl -0pi -e 's/        if done\.refused:\n            _refused\(p, step, done\.refused\)\n//' "$_XR"; }
guard_xauthor-run-refused-resume() { uv run pytest tests/scripts/test_xauthor_run.py -q -k old_runner; }

claim_xauthor-run-idle-cut() { echo "충전 전 재시도의 끊김은 창으로 세지 않는다 — 세면 늦은 충전 하나가 멈춤 규칙(창 여섯 개)을 건다 (§7.10d 수집 중 보정)"; }
break_xauthor-run-idle-cut() { perl -0pi -e 's/        idle = not window_has_sessions\(p\.out\)\n/        idle = False\n/' "$_XR"; }
guard_xauthor-run-idle-cut() { uv run pytest tests/scripts/test_xauthor_run.py -q -k refill; }

claim_scripts-typed() { echo "scripts/ 도 타입 검사를 받는다 — 빠지면 외부 출력을 읽는 실행기의 None · 비목록 경로가 조용히 산다"; }
break_scripts-typed() { perl -0pi -e 's/def windows_used\(out: Path\) -> int:/def windows_used(out: Path) -> str:/' "$_XR"; }
guard_scripts-typed() { uv run mypy; }

claim_xauthor-run-gate-output() { echo "관문은 검사 출력이 끝까지 찍혀야 통과다 — 종료 코드만 보면 쌍의 코드가 SystemExit(0) 으로 끝낸 관문이 통과한다 (§7.10d 관문)"; }
break_xauthor-run-gate-output() { perl -0pi -e 's/            elif rc == 0 and not gate_output_ok\(stdout\):/            elif False:/' "$_XR"; }
guard_xauthor-run-gate-output() { uv run pytest tests/scripts/test_xauthor_run.py -q -k ends_the_gate_early; }

claim_xauthor-run-gate-rc() { echo "관문이 실패한 시도는 실패다 — rc 를 안 보면 관문을 못 넘은 쌍이 감사로 간다 (§7.10d 「시도 · 렌즈」)"; }
break_xauthor-run-gate-rc() { perl -0pi -e 's/_json\(record, \{"pass": not problems and rc == 0,/_json(record, {"pass": not problems,/' "$_XR"; }
guard_xauthor-run-gate-rc() { uv run pytest tests/scripts/test_xauthor_run.py -q -k failing_the_gate_three_times; }

claim_xauthor-run-timeout() { echo "시간 상한으로 끊긴 세션은 시도로 센다 — 크레딧 끊김처럼 되돌리면 공짜 재시도가 된다 (§7.10d 「시도 · 렌즈」)"; }
break_xauthor-run-timeout() { perl -0pi -e 's/    if s\.cut:\n/    if s.cut or s.timed_out:\n/' "$_XR"; }
guard_xauthor-run-timeout() { uv run pytest tests/scripts/test_xauthor_run.py -q -k time_limit; }

claim_xauthor-run-kind-budget() { echo "분류마다 실패한 쌍은 넷까지다 — 넘기면 한 분류에 크레딧을 쏟는다 (§7.10d 「시도 · 렌즈」)"; }
break_xauthor-run-kind-budget() { perl -0pi -e 's/outcomes\.count\("failed"\) >= FAILED_PER_KIND/outcomes.count("failed") > FAILED_PER_KIND/' "$_XR"; }
guard_xauthor-run-kind-budget() { uv run pytest tests/scripts/test_xauthor_run.py -q -k four_failed; }

claim_xauthor-run-interrupted() { echo "하네스가 중단한 세션은 세지 않고 그 전 상자로 다시 돈다 — 안 되돌리면 반쯤 쓴 파일 위에서 다시 쓴다 (§7.10d ⑩ (c))"; }
break_xauthor-run-interrupted() { perl -0pi -e 's/        abandon\(d, step, "interrupted", box, snap\)\n//' "$_XR"; }
guard_xauthor-run-interrupted() { uv run pytest tests/scripts/test_xauthor_run.py -q -k interrupted_session; }

claim_xauthor-run-recheck() { echo "재확인에서 재현되는 문제가 남으면 그 쌍은 실패다 (§7.10d 「시도 · 렌즈」)"; }
break_xauthor-run-recheck() { perl -0pi -e 's/    elif audit\(p, "recheck"\):/    elif False:/' "$_XR"; }
guard_xauthor-run-recheck() { uv run pytest tests/scripts/test_xauthor_run.py -q -k left_at_the_recheck; }

claim_xauthor-run-fix-gate() { echo "고친 뒤 관문을 넘지 못하면 그 쌍은 실패다 (§7.10d 「시도 · 렌즈」)"; }
break_xauthor-run-fix-gate() { perl -0pi -e 's/    if not gate\(p, "gate-fix"\):/    if not gate(p, "gate-fix") and False:/' "$_XR"; }
guard_xauthor-run-fix-gate() { uv run pytest tests/scripts/test_xauthor_run.py -q -k breaks_the_gate; }

claim_xauthor-run-box-missing() { echo "쓴 기록이 있는데 상자가 없으면 사람을 부른다 — 새 상자로 이어 쓰면 앞 시도를 잃는다 (rc 4)"; }
break_xauthor-run-box-missing() { perl -0pi -e 's/            raise Stop\(HUMAN, f"\{p\.pid\} 의 상자가 없다 - \{p\.box\}"\)/            pass/' "$_XR"; }
guard_xauthor-run-box-missing() { uv run pytest tests/scripts/test_xauthor_run.py -q -k missing_box; }

claim_xauthor-box-help() { echo "저자가 돌리는 도움말에 실험의 목적이 없다 — 1단계 저자 15/15 가 「codex 가 쓴 쌍의 관문」을 봤다 (§7.10d 2단계 전 보정)"; }
break_xauthor-box-help() { perl -0pi -e 's/"gate", help="쌍의 관문 - 기계로 보는 것만"/"gate", help="codex 가 쓴 쌍의 관문 - 기계로 보는 것만"/' src/codeproof_ai/cli.py; }
guard_xauthor-box-help() { uv run pytest tests/scripts/test_xauthor.py -q -k help_the_author_runs; }

claim_xauthor-box-gate-doc() { echo "관문 모듈의 문서에 실험의 목적이 없다 — 저자는 모듈 문서를 읽는다 (§7.10d 2단계 전 보정)"; }
break_xauthor-box-gate-doc() { perl -0pi -e 's/"""쌍의 관문 - 기계로 보는 것만 \(DESIGN 「관문」\)\./"""codex 가 쓴 쌍의 관문 - 기계로 보는 것만 (DESIGN 「관문」)./' src/codeproof_ai/eval/gate.py; }
guard_xauthor-box-gate-doc() { uv run pytest tests/scripts/test_xauthor.py -q -k gate_module; }

claim_xauthor-box-metadata() { echo "상자용 wheel 은 README 를 METADATA 에 싣지 않는다 — README 에 가설이 적혀 있다 (§7.10d 2단계 전 보정)"; }
break_xauthor-box-metadata() { perl -0pi -e 's/"--out-dir", str\(out\), str\(tree\)\]/"--out-dir", str(out)]/' "$_XA"; }
guard_xauthor-box-metadata() { uv run pytest tests/scripts/test_xauthor.py -q -k long_description; }

claim_xauthor-s2-accepted-briefs() { echo "2단계 쓰기 과제에는 받아들여진 쌍의 요약만 싣는다 — 버린 쌍은 주지 않는다 (§7.10d ⑩ (e))"; }
break_xauthor-s2-accepted-briefs() { perl -0pi -e 's/    found = \(brief_of\(d\) for d in mine if outcome_of\(d\) == "accepted"\)/    found = (brief_of(d) for d in mine)/' "$_XR"; }
guard_xauthor-s2-accepted-briefs() { uv run pytest tests/scripts/test_xauthor_run.py -q -k only_accepted_pairs; }

claim_xauthor-s2-drop-kind() { echo "한 바퀴를 못 채운 분류는 이후 바퀴에서 쓰지 않는다 — 8쌍이 될 수 없는 분류에 크레딧을 쓴다 (§7.10d 2단계)"; }
break_xauthor-s2-drop-kind() { perl -0pi -e 's/    return all\(/    return True or all(/' "$_XR"; }
guard_xauthor-s2-drop-kind() { uv run pytest tests/scripts/test_xauthor_run.py -q -k kind_that_misses_a_round; }

claim_xauthor-s2-retry-briefs() { echo "앞 쌍 요약은 재시도 과제에도 싣는다 — 시도마다 새 세션이라 없으면 같은 기전을 다시 쓴다 (§7.10d 2단계 시작 전 보정)"; }
break_xauthor-s2-retry-briefs() { perl -0pi -e 's/        f"\{_prior_block\(prior\)\}\\n"\n//' "$_XR"; }
guard_xauthor-s2-retry-briefs() { uv run pytest tests/scripts/test_xauthor_run.py -q -k every_attempt_carries; }

claim_xauthor-s2-same-as() { echo "2단계는 실행을 가르는 항목이 1단계와 같아야 시작한다 — 「같은 방식으로」 (§7.10d 2단계)"; }
break_xauthor-s2-same-as() { perl -0pi -e 's/    if diffs := \[k for k in SIGNED if prior\.get\(k\) != fields\[k\]\]:/    if diffs := []:/' "$_XR"; }
guard_xauthor-s2-same-as() { uv run pytest tests/scripts/test_xauthor_run.py -q -k settings_that_differ; }

claim_xauthor-s2-window-cap() { echo "2단계는 크레딧 창 스무 개를 넘게 쓰면 멈추고 묻는다 — 승인한 예산의 상한 (§7.10d 2단계 시작 전 보정)"; }
break_xauthor-s2-window-cap() { perl -0pi -e 's/        if windows_used\(out\) > STAGE2_MAX_WINDOWS:/        if False:/' "$_XR"; }
guard_xauthor-s2-window-cap() { uv run pytest tests/scripts/test_xauthor_run.py -q -k past_its_window_budget; }

claim_xauthor-audit-schema() { echo "감사 exec 은 저자 exec 에 스키마 하나만 더한다 — 감사 카나리가 감사 인자 그대로를 본다 (§7.10d 상자)"; }
break_xauthor-audit-schema() { perl -0pi -e 's/        args \+= \["--output-schema", str\(schema\)\]\n/        args += ["--output-schema", str(schema), "--skip-git-repo-check"]\n/' "$_XA"; }
guard_xauthor-audit-schema() { uv run pytest tests/scripts/test_xauthor.py -q -k only_the_audit; }

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
  local before; before=$(git status --porcelain --untracked-files=all)
  "break_$name" || { echo "  ${RED}깨뜨리지 못했다${OFF} — 시나리오가 낡았다"; ((FAIL++)); FAILED_NAMES+=("$name"); restore; return; }
  # 🔴 perl · sed 는 치환할 곳이 없어도 0 을 낸다 - 그러면 아무것도 깨지 않은 채 가드가 통과하고
  #    「공허한 가드」로 잘못 보고된다. [실측] 겨누던 줄을 고치자 short-runs · pack-partial 이 그렇게 침묵했다.
  if [[ "$(git status --porcelain --untracked-files=all)" == "$before" ]]; then
    printf '  결과 : %s깨뜨리지 못했다 — 바꾼 곳이 없다 (깨는 패턴이 낡았다)%s\n\n' "$RED" "$OFF"
    ((FAIL++)); FAILED_NAMES+=("$name"); restore; return
  fi

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
  printf ' · %s%d개가 실패했다: %s%s\n' "$RED" "$FAIL" "${FAILED_NAMES[*]}" "$OFF"
  exit 1
fi
printf '\n'
