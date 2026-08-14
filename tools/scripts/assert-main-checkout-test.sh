#!/usr/bin/env bash
#
# `assert-main-checkout.sh` 의 판별력 하네스 ([BL-722]).
#
# ★진짜 가드를 겨눈다 — 사본이 아니다. 임시 git 레포와 그 worktree 위에서 원본 스크립트를
#   직접 실행한다. 실제 레포의 worktree·컨테이너·DB 는 1바이트도 건드리지 않는다.
# ★위험한 실패 방향은 worktree 를 메인으로 통과시키는 것이다. 따라서 메인 양성 대조뿐 아니라
#   worktree 거부를 별도 케이스로 고정한다.
# ★비-git 은 판정 불가라서 의도적으로 통과한다. 이를 거부로 바꾸면 CI·컨테이너의 정상 타깃까지
#   죽으므로, 이 케이스의 기대 rc 는 **0** 이다.
#
# 사용법: tools/scripts/assert-main-checkout-test.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
TARGET="$ROOT/tools/scripts/assert-main-checkout.sh"
SB="$(mktemp -d "${TMPDIR:-/tmp}/assert-main-checkout-test.XXXXXX")"
trap 'rm -rf "$SB"' EXIT
SB="$(cd "$SB" && pwd -P)"

MAIN="$SB/main"
WORKTREE="$SB/worktree"
NONGIT="$SB/non-git"

git init -q "$MAIN" || { echo "✗ 임시 git 레포를 만들지 못했다"; exit 2; }
git -C "$MAIN" config user.name "Assert Main Checkout Test" || exit 2
git -C "$MAIN" config user.email "assert-main-checkout-test@example.invalid" || exit 2
git -C "$MAIN" commit --allow-empty -qm "fixture" || { echo "✗ 임시 git 레포 초기 커밋에 실패했다"; exit 2; }
git -C "$MAIN" worktree add -q -b guard-fixture "$WORKTREE" HEAD || {
  echo "✗ 임시 git worktree 를 만들지 못했다"
  exit 2
}
mkdir -p "$NONGIT"

FAIL=0

show_output() {  # $1=stdout $2=stderr
  if [ -s "$1" ]; then
    echo "      stdout:"
    sed 's/^/        | /' "$1"
  fi
  if [ -s "$2" ]; then
    echo "      stderr:"
    sed 's/^/        | /' "$2"
  fi
}

run_case() {  # $1=케이스 설명 $2=실행 경로 $3=기대 rc(0|nonzero) $4=stderr 포함 문자열(선택)
  local description="$1" dir="$2" expected="$3" needle="${4:-}"
  local stdout="$SB/case-$CASE.out" stderr="$SB/case-$CASE.err" rc rc_ok=yes stderr_ok=yes expected_label

  (cd "$dir" && bash "$TARGET" "fixture") >"$stdout" 2>"$stderr"
  rc=$?

  case "$expected" in
    0) expected_label=0; [ "$rc" -eq 0 ] || rc_ok=no ;;
    nonzero) expected_label='≠0'; [ "$rc" -ne 0 ] || rc_ok=no ;;
    *) echo "✗ 하네스 내부 오류: 알 수 없는 기대 rc '$expected'"; exit 2 ;;
  esac
  if [ -n "$needle" ] && ! grep -Fq "$needle" "$stderr"; then
    stderr_ok=no
  fi

  if [ "$rc_ok" = yes ] && [ "$stderr_ok" = yes ]; then
    printf '  ✓ %s\n' "$description"
  else
    printf '  ✗ %s\n      rc=%s (기대 %s)\n' "$description" "$rc" "$expected_label"
    [ "$stderr_ok" = yes ] || printf '      stderr에 기대 경로 없음: %s\n' "$needle"
    show_output "$stdout" "$stderr"
    FAIL=1
  fi
  CASE=$((CASE + 1))
}

echo "▶ assert-main-checkout — 메인/worktree/비-git/오류 경로 판별력 4케이스"
CASE=1
run_case "⑴ 임시 git 레포 메인 체크아웃 → rc=0" "$MAIN" 0
run_case "⑵ 임시 git worktree → rc≠0 (위험한 통과 방향 차단)" "$WORKTREE" nonzero
run_case "⑶ 비-git 디렉터리 → rc=0 (판정 불가를 의도적으로 통과)" "$NONGIT" 0
run_case "⑷ worktree stderr에 메인 체크아웃 경로 포함 → rc≠0" "$WORKTREE" nonzero "$MAIN"

if [ "$FAIL" != 0 ]; then
  echo "✗ assert-main-checkout 하네스 실패 — 메인/worktree 판별력이 깨졌다"
  exit 1
fi
echo "✓ assert-main-checkout 하네스 4/4 전건 통과"
