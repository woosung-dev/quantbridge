#!/usr/bin/env bash
# tool-pin-audit 판별력 하네스 — [BL-785]. 전건 통과 = 종료 코드 0.
#
# 무엇을 재는가
#   「`tools/scripts/tool-pin-audit.sh` 가 핀 밖 도구 호출을 **가려낼 수 있는가**」.
#   감사기가 실제 레포에서 초록인 것은 증거가 아니다 — 판정을 통째로 지워도 초록이기 때문이다.
#   그래서 fixture 트리에 위반을 **심어서** red 가 나오는지, 위반이 아닌 것을 심어서 초록이
#   유지되는지 양쪽을 본다.
#
# ★핵심 음성 대조 = 케이스 ④·⑤·⑥.
#   `grep -c 'pnpm'` 으로 짜면 주석 · 안내문(`echo`) · 사용법 히어독이 전부 위반이 된다.
#   그러면 감사기가 상시 red 라 아무도 안 쓰고, 안 쓰는 검사기는 죽은 줄도 모르고 죽는다
#   (LESSON-078). 「부르는가」와 「이름이 있는가」를 가르지 못하는 구현은 반려 사유다.
#
# ★핵심 양성 대조 = 케이스 ②·③.
#   `timeout 120 uv run python` 과 `shutil.which("node")` 는 초판이 **둘 다 놓쳤다**.
#   앞의 것은 이 레포에 3곳, 뒤의 것은 1곳 실재한다.
#
# ★fixture 는 임시 트리에 만든다 — 실제 `tools/scripts/` 를 절대 건드리지 않는다.
#   감사기의 `QB_TOOL_PIN_ROOT` seam 으로 대상 트리만 갈아끼운다.
#
# ★종료 코드가 판정이므로 **파이프 없이** 읽는다 (`| tail` 이 $? 를 가린다 — 실측 사고 이력).
#
# 사용법: tools/scripts/tool-pin-audit-test.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
AUDIT="$ROOT/tools/scripts/tool-pin-audit.sh"
[ -f "$AUDIT" ] || { echo "✗ 감사 스크립트가 없다: $AUDIT" >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0
OUT=""
RC=0

new_tree() {
  rm -rf "$TMP/tree"
  mkdir -p "$TMP/tree/tools/scripts/lib" "$TMP/tree/.husky"
}

put() { # put <상대경로> <본문>
  local p="$TMP/tree/$1"
  mkdir -p "$(dirname "$p")"
  printf '%s\n' "$2" >"$p"
}

run() { # ★파이프 없음.
  OUT="$(QB_TOOL_PIN_ROOT="$TMP/tree" bash "$AUDIT" "$@" 2>&1)"
  RC=$?
}

report() { # report <label> <why(빈 문자열이면 통과)>
  if [ -n "$2" ]; then
    FAIL=$((FAIL + 1))
    printf '  ✗ %-56s %s\n' "$1" "$2"
    printf '%s\n' "$OUT" | sed 's/^/        | /'
  else
    PASS=$((PASS + 1))
    printf '  ✓ %-56s\n' "$1"
  fi
}

caught() { printf '%s\n' "$OUT" | grep -qF "$1"; }

PIN_LINES='. "$ROOT/tools/scripts/lib/mise-shim-path.sh"
qb_pin_tool_path || true'

echo "▶ 양성 — 핀 밖 호출은 반드시 잡힌다"

new_tree
put tools/scripts/a.sh 'cd apps/web && pnpm test'
run
report "① 핀 없는 pnpm 호출 → 위반" \
  "$( { caught 'tools/scripts/a.sh' && [ "$RC" -ne 0 ]; } || echo '안 잡혔거나 rc=0')"

new_tree
put tools/scripts/a.sh 'timeout 120 uv run python -c "pass"'
run
report "② 래퍼(timeout N) 뒤 uv 호출 → 위반" \
  "$( { caught 'tools/scripts/a.sh' && [ "$RC" -ne 0 ]; } || echo '안 잡혔거나 rc=0')"

new_tree
put tools/scripts/a.sh 'python3 - <<'"'"'PY'"'"'
node = shutil.which("node")
PY'
run
report "③ 인터프리터 히어독 안 node 조회 → 위반" \
  "$( { caught 'tools/scripts/a.sh' && [ "$RC" -ne 0 ]; } || echo '안 잡혔거나 rc=0')"

new_tree
put tools/scripts/a.sh 'echo "고치는 법: . tools/scripts/lib/mise-shim-path.sh 뒤에 qb_pin_tool_path"
cd apps/web && pnpm build'
run
report "④ 핀을 **언급만** 하고 안 부른다 → 위반 (거짓 핀 차단)" \
  "$( { caught 'tools/scripts/a.sh' && [ "$RC" -ne 0 ]; } || echo '안 잡혔거나 rc=0')"

echo
echo "▶ 음성 — 이것들은 위반이 아니다 (여기가 red 면 감사기가 상시 red 라 쓸모없다)"

new_tree
put tools/scripts/a.sh "$PIN_LINES
cd apps/web && pnpm test"
run
report "⑤ 핀이 있는 호출 → 통과" \
  "$( [ "$RC" -eq 0 ] || echo "rc=$RC")"

new_tree
put tools/scripts/a.sh '# pnpm test 로 FE 단위 테스트를 돌린다
true'
run
report "⑥ 주석 안 도구 이름 → 통과" \
  "$( [ "$RC" -eq 0 ] || echo "rc=$RC")"

new_tree
put tools/scripts/a.sh 'echo "  E2E   cd apps/web && pnpm e2e"'
run
report "⑦ 안내문(echo) 안 도구 이름 → 통과" \
  "$( [ "$RC" -eq 0 ] || echo "rc=$RC")"

new_tree
put tools/scripts/a.sh "cat <<'EOF'
  BE 테스트   cd apps/api && uv run pytest
EOF"
run
report "⑧ 사용법 히어독 본문 → 통과" \
  "$( [ "$RC" -eq 0 ] || echo "rc=$RC")"

new_tree
put tools/scripts/a.sh 'cd "$WEB" && mise exec -- pnpm build'
run
report "⑨ mise exec 경유 호출 → 통과" \
  "$( [ "$RC" -eq 0 ] || echo "rc=$RC")"

new_tree
put .husky/pre-commit 'PATH="$HOME/.local/share/mise/shims:$PATH"
export PATH
pnpm exec lint-staged'
run
report "⑩ 훅의 인라인 shim PATH → 통과" \
  "$( [ "$RC" -eq 0 ] || echo "rc=$RC")"

new_tree
put tools/scripts/soak-gate.sh 'timeout 120 uv run python -c "pass"'
run
report "⑪ 서버 실행 스크립트(soak-gate.sh) → 면제, 통과" \
  "$( { [ "$RC" -eq 0 ] && caught '서버 실행이라 면제'; } || echo "rc=$RC 또는 면제 사유 미출력")"

echo
echo "▶ 형식 — --list 는 위반 경로만 낸다"

new_tree
put tools/scripts/a.sh 'cd apps/web && pnpm test'
put tools/scripts/b.sh "$PIN_LINES
cd apps/api && uv run pytest"
run --list
report "⑫ --list = 위반 경로 1줄 (핀 있는 것은 안 나온다)" \
  "$( [ "$OUT" = "tools/scripts/a.sh" ] && [ "$RC" -ne 0 ] || echo "출력='$OUT' rc=$RC")"

echo
echo "▶ 자기검사 — 판별기가 고장나면 초록을 내지 않는다"

# ★감사기의 내부 자기검사를 깨뜨려 rc=3 이 나오는지 본다. 여기가 rc=0/1 이면 「판정 불가」를
#   「통과」로 번역하는 것이고, 그것이 이 레포가 여러 번 밟은 fail-open 이다.
sed 's/^TOOLS = .*/TOOLS = ("__nonexistent__",)/' "$AUDIT" >"$TMP/broken.sh"
OUT="$(QB_TOOL_PIN_ROOT="$TMP/tree" bash "$TMP/broken.sh" 2>&1)"; RC=$?
report "⑬ 판별기 훼손 → rc=3 (fail-closed)" \
  "$( [ "$RC" -eq 3 ] || echo "rc=$RC — 판정 불가를 통과로 번역했다")"

echo
printf '결과: %d 통과 / %d 실패\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
