#!/usr/bin/env bash
# header-audit 판별력 하네스 — [BL-307]. 전건 통과 = 종료 코드 0.
#
# ★이 파일은 구현보다 **먼저** 쓰였다(G1 수용 기준 동결). 생성자는 이 계약을 통과시키는
#   `tools/scripts/header-audit.sh` 만 쓴다. 생성자가 테스트를 쓰면 그 테스트는 구현의 거울이 된다 —
#   정본 = `docs/reference/operations/workflows/generator-evaluator-pipeline.md` §1.
#
# 무엇을 재는가
#   「소스 파일 첫 3줄에 **한국어 주석**이 있는가」. 근거는 루트 `AGENTS.md:23`
#   (「사고/계획/대화/문서/주석 = 한국어」). 원장이 「근거였던 전역 §6 는 소멸」이라 적었지만
#   2026-08-10 G0 실측으로 **반증**됐다 — 규칙은 죽은 것이 아니라 그 파일로 이사했다.
#
# ★핵심 음성 대조 = 케이스 ⑨ **한글 문자열 리터럴**.
#   `head -3 | grep '[가-힣]'` 로 짜면 이 케이스가 조용히 통과한다. 첫 줄이
#   `MESSAGE = "백테스트 실패"` 인 파일은 한글이 있지만 **헤더 주석이 없다.**
#   이 케이스가 red 를 유지하지 못하는 구현은 「한글 존재 검사」이지 「한국어 주석 검사」가
#   아니다 — 반려 사유다.
#   ★[가정 아님] 2026-08-10 실측 — **현재 레포에 이 패턴은 0건이다.** 즉 이 케이스는 관측된
#     결함의 재현이 아니라 **선제 가드**다. 그렇다고 빼면 안 되는 이유: 순진한 구현이 타는
#     지름길이 정확히 이것이고, 지금 0건이라는 것은 **미래에도 0건이라는 뜻이 아니다.**
#     (같은 회차에 내가 이 자리에 「실재한다」고 적었다가 실측 0건으로 반증당했다 — 그 정정이
#      이 줄이다. 근거 없는 강화를 남기지 않는다.)
#
# ★fixture 는 임시 트리에 만든다 — 실제 `apps/api/`·`apps/web/` 를 절대 건드리지 않는다.
#   `header-audit.sh` 는 `dirname $0/..` 를 ROOT 로 잡고 그 아래 두 디렉터리를 훑으므로,
#   스크립트 사본을 `$TMP/tree/tools/scripts/` 에 두면 그 옆의 fixture 소스를 읽는다.
#
# ★종료 코드가 판정이므로 **파이프 없이** 읽는다 (`| tail` 이 $? 를 가린다 — 실측 사고 이력).
#
# 사용법: tools/scripts/header-audit-test.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
AUDIT="$ROOT/tools/scripts/header-audit.sh"
[ -f "$AUDIT" ] || {
  echo "✗ 감사 스크립트가 없다: $AUDIT" >&2
  echo "  (G1 동결 시점에는 이것이 정상 red 다 — 생성자가 G2 에서 만든다)" >&2
  exit 1
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0
OUT=""
RC=0

# fixture 트리를 새로 만든다. 인자로 받은 "경로:본문" 쌍을 그대로 심는다.
new_tree() {
  rm -rf "$TMP/tree"
  mkdir -p "$TMP/tree/tools/scripts" "$TMP/tree/apps/api/src" "$TMP/tree/apps/web/src"
  cp "$AUDIT" "$TMP/tree/tools/scripts/header-audit.sh"
}

put() { # put <상대경로> <본문>
  local p="$TMP/tree/$1"
  mkdir -p "$(dirname "$p")"
  printf '%s\n' "$2" >"$p"
}

run() { # 인자 그대로 감사기에 넘긴다. ★파이프 없음.
  OUT="$(bash "$TMP/tree/tools/scripts/header-audit.sh" "$@" 2>&1)"
  RC=$?
}

report() { # report <label> <why(빈 문자열이면 통과)>
  if [ -n "$2" ]; then
    FAIL=$((FAIL + 1))
    printf '  ✗ %-52s %s\n' "$1" "$2"
    printf '%s\n' "$OUT" | sed 's/^/        | /'
  else
    PASS=$((PASS + 1))
    printf '  ✓ %-52s\n' "$1"
  fi
}

# 위반으로 잡혔는지 = 경로가 출력에 있고 rc≠0
caught() { printf '%s\n' "$OUT" | grep -qF "$1"; }

echo "▶ 양성 — 위반은 반드시 잡힌다"

new_tree
put apps/api/src/a.py 'import os'
run
report "① BE .py 주석 없음 → 위반" \
  "$( { caught 'apps/api/src/a.py' && [ "$RC" -ne 0 ]; } || echo '안 잡혔거나 rc=0')"

new_tree
put apps/api/src/b.py '# provider registry — factory dispatch'
run
report "② BE .py 주석이 영어뿐 → 위반" \
  "$( { caught 'apps/api/src/b.py' && [ "$RC" -ne 0 ]; } || echo '영어 주석을 통과시켰다')"

new_tree
put apps/web/src/c.tsx 'export const C = () => null;'
run
report "③ FE .tsx 주석 없음 → 위반" \
  "$( { caught 'apps/web/src/c.tsx' && [ "$RC" -ne 0 ]; } || echo '안 잡혔거나 rc=0')"

new_tree
put apps/web/src/d.tsx '// equity chart pane'
run
report "④ FE .tsx 주석이 영어뿐 → 위반" \
  "$( { caught 'apps/web/src/d.tsx' && [ "$RC" -ne 0 ]; } || echo '영어 주석을 통과시켰다')"

new_tree
put apps/api/src/e.py 'import os
import sys

# 한국어 주석이지만 4번째 줄이다'
run
report "⑤ 한국어 주석이 4번째 줄 → 위반 (첫 3줄 규칙)" \
  "$( { caught 'apps/api/src/e.py' && [ "$RC" -ne 0 ]; } || echo '3줄 경계가 안 지켜졌다')"

echo
echo "▶ 음성 — 정당한 파일을 잡으면 안 된다"

new_tree
put apps/api/src/ok1.py '# 백테스트 실행 태스크 — celery 진입점'
run
report "⑥ BE 첫 줄 한국어 주석 → 통과" \
  "$( { ! caught 'apps/api/src/ok1.py' && [ "$RC" -eq 0 ]; } || echo '정당한 파일을 잡았다')"

new_tree
put apps/web/src/ok2.tsx '/**
 * 자산 곡선 차트 — 백테스트 상세 화면
 */'
run
report "⑦ FE 블록 주석 안 한국어(2번째 줄) → 통과" \
  "$( { ! caught 'apps/web/src/ok2.tsx' && [ "$RC" -eq 0 ]; } || echo '정당한 파일을 잡았다')"

# ★⑧ 과 ⑧b 를 **나눈다.** 면제는 두 가족이다 — basename 규칙과 경로 규칙.
#   초판은 한 케이스에 몰아넣었는데, fixture 5개가 **전부 basename 으로도 면제**돼서
#   경로 규칙을 지워도 red 가 되지 않았다(2026-08-10 변이 M1 이 탈출해 드러났다).
#   한쪽 검사가 다른 쪽을 대신 잡아주면 그 축은 게이트가 아니다.
new_tree
put apps/api/src/f/__init__.py ''
put apps/web/src/g/index.ts 'export * from "./g";'
put apps/web/src/h.d.ts 'declare module "x";'
put apps/api/src/j/test_x.py 'import pytest'
put apps/web/src/k/i.test.tsx 'it("x", () => {});'
run
report "⑧ 면제 — basename 규칙 (test_*·__init__·index·d.ts)" \
  "$( [ "$RC" -eq 0 ] || echo 'basename 면제 대상을 잡았다')"

# ★basename 으로는 절대 면제되지 않는 이름만 쓴다. 그래야 경로 규칙만 이 케이스를 지탱한다.
new_tree
put apps/api/src/tests/helpers.py 'import os'
put apps/web/src/__tests__/util.ts 'export const u = 1;'
put apps/api/src/generated/schema.py 'X = 1'
run
report "⑧b 면제 — 경로 규칙 (/tests/·/__tests__/·/generated/)" \
  "$( [ "$RC" -eq 0 ] || echo '경로 면제가 작동하지 않는다')"

# ★★ 이 하네스의 핵심. 「한글 존재」와 「한국어 주석」을 가른다.
new_tree
put apps/api/src/lit.py 'MESSAGE = "백테스트 실패"'
put apps/web/src/lit.tsx 'export const LABEL = "전략 목록";'
run
report "⑨ ★한글 **문자열 리터럴**뿐 → 위반 (주석이 아니다)" \
  "$( { caught 'apps/api/src/lit.py' && caught 'apps/web/src/lit.tsx' && [ "$RC" -ne 0 ]; } || echo '한글 존재만 보고 통과시켰다 — 주석 판정이 없다')"

new_tree
put apps/api/src/core/config.py 'import os'
put apps/web/src/x.config.ts 'export default {};'
run
report "⑩ config 경로 면제 (원장 exempt list) → 통과" \
  "$( [ "$RC" -eq 0 ] || echo 'config 를 잡았다')"

# ★정상 대상 파일을 **반드시 하나 섞는다.** 초판은 .md/.json 만 뒀는데, 그러면 이 케이스가
#   요구하는 상태가 「대상 0건」이라 **ROOT 가 깨져 아무것도 못 읽은 상태와 구별되지 않는다.**
#   빈 입력이 초록으로 새는 것 — 이 회차가 이미 세 번 밟은 함정이라 계약에서 막는다.
new_tree
put apps/api/src/notes.md '# just a doc'
put apps/web/src/data.json '{}'
put apps/api/src/real.py '# 정상 헤더 — 이 파일이 있어야 스캔이 실제로 돌았음이 증명된다'
run
report "⑪ .md·.json 은 대상 아님 (정상 .py 1건 동반) → 통과" \
  "$( [ "$RC" -eq 0 ] || echo '대상 아닌 확장자를 잡았다')"

echo
echo "▶ 회귀 — 2026-08-10 /code-review 가 잡은 오탐 3종"

# ★`put` 은 항상 개행을 붙이므로 이 케이스만 직접 쓴다. 개행 없는 마지막 줄을 `read` 가
#   버려서 **정상 헤더 파일이 전부 위반**으로 잡히던 오탐.
new_tree
mkdir -p "$TMP/tree/apps/web/src"
printf '// 한국어 주석 (파일 끝에 개행 없음)' >"$TMP/tree/apps/web/src/nonl.tsx"
run
report "⑭ 마지막 줄에 개행이 없어도 헤더를 읽는다" \
  "$( { ! caught 'apps/web/src/nonl.tsx' && [ "$RC" -eq 0 ]; } || echo '개행 없는 헤더를 버렸다')"

# ★한 줄에 주석 구간이 둘. 종전 구현은 첫 구간만 보고 나머지를 코드로 흘렸다.
new_tree
put apps/web/src/two.tsx '/* eslint-disable */ // 한국어 설명
export const T = 1;'
put apps/api/src/two.py '"""x"""  # 한국어 설명
X = 1'
run
report "⑮ 한 줄에 주석 구간이 둘이어도 뒤쪽을 읽는다" \
  "$( { ! caught 'apps/web/src/two.tsx' && ! caught 'apps/api/src/two.py' && [ "$RC" -eq 0 ]; } || echo '닫는 구분자 뒤 주석을 못 봤다')"

# ★shadcn 벤더 산출물. `apps/web/AGENTS.md:232` 가 직접 수정을 금지하므로 면제해야 한다 —
#   면제하지 않으면 게이트가 금지된 수정을 영구히 강제한다.
new_tree
put apps/web/src/components/ui/button.tsx 'export const Button = () => null;'
run
report '⑯ components/ui/ (shadcn 벤더) 면제 → 통과' \
  "$( [ "$RC" -eq 0 ] || echo '벤더 파일 수정을 강제하고 있다')"

echo
echo "▶ 계약 — 종료 코드와 --list"

new_tree
put apps/api/src/ok3.py '# 정상 헤더'
run
report "⑫ 위반 0건 → rc=0" \
  "$( [ "$RC" -eq 0 ] || echo "rc=$RC (0 이어야 한다)")"

new_tree
put apps/api/src/v1.py 'import os'
put apps/web/src/v2.tsx 'export const V = 1;'
run --list
report "⑬ --list 는 위반 경로만 한 줄씩 낸다" \
  "$( { caught 'apps/api/src/v1.py' && caught 'apps/web/src/v2.tsx' \
        && [ "$(printf '%s\n' "$OUT" | grep -c .)" -eq 2 ]; } || echo '경로 2줄이 아니다')"

echo
if [ "$FAIL" -eq 0 ]; then
  printf '✓ header-audit 하네스 %d/%d 통과\n' "$PASS" "$((PASS + FAIL))"
  exit 0
else
  printf '✗ header-audit 하네스 %d/%d 실패\n' "$FAIL" "$((PASS + FAIL))"
  exit 1
fi
