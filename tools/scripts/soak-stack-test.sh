#!/usr/bin/env bash
# soak-stack Darwin 차단 하네스 — [BL-735]. 전건 통과 = 종료 코드 0.
#
# 실제 소크 `up` 은 compose를 기동하므로 절대 레포에서 실행하지 않는다. 임시 트리에 진짜
# 스크립트 사본을 두고 PATH 앞단의 가짜 uname으로 OS만 바꾼다. 세 경우 모두 고정본 없음에서
# 멈추므로 docker·네트워크 의존은 없다.

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
STACK="$ROOT/tools/scripts/soak-stack.sh"
[ -f "$STACK" ] || {
  echo "✗ 소크 스택 스크립트가 없다: $STACK" >&2
  exit 1
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0
OUT=""
RC=0
ASSERT_MAIN_CALL=""

DARWIN_REJECTION="✗ macOS는 잠들어 celery beat가 진행되지 않는다 — 소크 정본은 서버다. 서버에서 실행하거나 QB_SOAK_ALLOW_DARWIN=1로 명시적으로 우회해라"
NO_PIN_REJECTION="✗ 고정본이 없다 — 먼저 'soak-stack.sh pin' 을 해라"

_build_tree() {
  mkdir -p "$TMP/tree/tools/scripts" "$TMP/bin"
  cp "$STACK" "$TMP/tree/tools/scripts/soak-stack.sh"

  cat > "$TMP/tree/tools/scripts/assert-main-checkout.sh" << 'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" > "${QB_ASSERT_MAIN_CALL:?}"
EOF
  cat > "$TMP/bin/uname" << 'EOF'
#!/usr/bin/env bash
printf '%s\n' "${QB_FAKE_UNAME:?}"
EOF
  chmod +x "$TMP/tree/tools/scripts/soak-stack.sh" \
    "$TMP/tree/tools/scripts/assert-main-checkout.sh" "$TMP/bin/uname"
}

_run() { # _run <Darwin|Linux> <allow 빈 값|1>
  : > "$TMP/assert-main-call"
  if [ -n "$2" ]; then
    OUT="$(PATH="$TMP/bin:$PATH" \
      QB_FAKE_UNAME="$1" \
      QB_SOAK_ALLOW_DARWIN="$2" \
      QB_ASSERT_MAIN_CALL="$TMP/assert-main-call" \
      bash "$TMP/tree/tools/scripts/soak-stack.sh" up 2>&1)"
  else
    OUT="$(
      unset QB_SOAK_ALLOW_DARWIN
      PATH="$TMP/bin:$PATH" \
        QB_FAKE_UNAME="$1" \
        QB_ASSERT_MAIN_CALL="$TMP/assert-main-call" \
        bash "$TMP/tree/tools/scripts/soak-stack.sh" up 2>&1
    )"
  fi
  RC=$?
  ASSERT_MAIN_CALL="$(cat "$TMP/assert-main-call")"
}

_assert_eq() { # _assert_eq <label> <actual> <expected>
  if [ "$2" = "$3" ]; then
    PASS=$((PASS + 1))
    printf '  ✓ %s\n' "$1"
    return
  fi

  FAIL=$((FAIL + 1))
  printf '  ✗ %s\n' "$1"
  printf '      기대: [%s]\n      실제: [%s]\n' "$3" "$2"
}

echo "══ soak-stack Darwin 차단 하네스  (임시 사본 · 가짜 uname · Docker 미호출) ══"
echo "  대상: $STACK"
echo

_build_tree

# 양성: Darwin 기본값은 가장 먼저 rc=2로 거부하고 main checkout 검사에도 닿지 않는다.
_run Darwin ""
_assert_eq "Darwin 기본 거부의 종료 코드" "$RC" "2"
_assert_eq "Darwin 기본 거부 사유 전문" "$OUT" "$DARWIN_REJECTION"
_assert_eq "Darwin 기본 거부는 main checkout 검사 전" "$ASSERT_MAIN_CALL" ""

# 음성 대조: Linux는 Darwin 가드를 지나 그 다음 고정본 없음에서 멈춘다. rc만으로는
# 양성과 구별할 수 없으므로, 거부 본문 전체를 정확히 대조한다.
_run Linux ""
_assert_eq "Linux 대조의 종료 코드" "$RC" "2"
_assert_eq "Linux 대조는 고정본 없음으로 진행" "$OUT" "$NO_PIN_REJECTION"
_assert_eq "Linux 대조는 main checkout 검사를 통과" "$ASSERT_MAIN_CALL" "soak-stack.sh up"

# 탈출구: 명시적 1만 허용한다. Darwin이어도 같은 고정본 없음 단계까지 진행해야 한다.
_run Darwin 1
_assert_eq "Darwin 명시적 우회의 종료 코드" "$RC" "2"
_assert_eq "Darwin 명시적 우회는 고정본 없음으로 진행" "$OUT" "$NO_PIN_REJECTION"
_assert_eq "Darwin 명시적 우회는 main checkout 검사를 통과" "$ASSERT_MAIN_CALL" "soak-stack.sh up"

echo
if [ "$FAIL" -ne 0 ]; then
  echo "✗ soak-stack Darwin 차단 하네스 실패 (${FAIL}건 실패 / ${PASS}건 통과)" >&2
  exit 1
fi
echo "✓ soak-stack Darwin 차단 하네스 전건 통과 (${PASS}건)"
