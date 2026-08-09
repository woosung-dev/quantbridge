#!/usr/bin/env bash
# soak-restart 갈래 하네스 — [BL-656]. 전건 통과 = 종료 코드 0.
#
# 무엇을 재나
#   `soak-restart.sh` 는 「이미 up」과 「완전 down」 두 상태에서 **다른 순서**를 밟아야 한다.
#     · 살아 있음 → ⑴ status … ⑷ down → pin → up
#     · 완전 down → ⓿ pin → up 을 **선행**하고 ⑷ 와 덤프를 건너뛴다
#   이 순서는 2026-08-09 까지 **문서로만** 있었고(:219 의 손 절차) 스크립트는 down 에서
#   `ConnectionRefusedError` 로 끝났다. 순서를 코드로 옮겼으면 **순서를 재는 것도 코드여야 한다.**
#
# ★진짜 소크를 절대 건드리지 않는다. 임시 트리에 `soak-restart.sh` **사본**을 두고 그 옆에
#   가짜 `soak-stack.sh`·`assert-main-checkout.sh`·`soak-observe.sh`·`soak-gate.sh` 와
#   PATH 앞단의 가짜 `docker`·`uv` 를 깐다(`soak-watch-test.sh` 와 같은 수법 — 스크립트가
#   `dirname $0` 옆을 부르므로 사본 옆에 두면 그 가짜를 읽는다).
#
# ★오라클은 **호출 순서 로그**다. 「down 이 안 불렸다」를 출력 문구로 재면 문구를 바꾸는 순간
#   판별력이 사라진다. 가짜들이 자기 이름을 파일에 append 하고 그 순서를 단언한다.
#
# ★음성 대조가 이 하네스의 존재 이유다 — down 갈래만 재면 「항상 pin→up 을 선행한다」는
#   구현도 통과한다. up 갈래에서 **선행이 없고 ⑷ 가 down→pin→up 을 한다**를 함께 단언한다.
#
# 사용법: scripts/soak-restart-test.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
REAL="$ROOT/scripts/soak-restart.sh"
[ -f "$REAL" ] || {
  echo "✗ 대상 스크립트가 없다: $REAL" >&2
  exit 1
}

PASS=0
FAIL=0
UUID="aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"

_ok() {
  PASS=$((PASS + 1))
  echo "  ✓ $1"
}
_no() {
  FAIL=$((FAIL + 1))
  echo "  ✗ $1" >&2
  [ -n "${2:-}" ] && printf '%s\n' "$2" | sed 's/^/      | /' >&2
}

# ── 임시 트리 ────────────────────────────────────────────────────────────────────
# `$1` = ps 종료 코드 (0 = 하나라도 running / 1 = 완전 down). 트리 경로를 echo 한다.
_make_tree() {
  local ps_rc="$1" tmp
  tmp="$(mktemp -d)"
  mkdir -p "$tmp/scripts" "$tmp/backend/scripts" "$tmp/backend/.metrics" "$tmp/bin" "$tmp/.soak"
  cp "$REAL" "$tmp/scripts/soak-restart.sh"
  : > "$tmp/backend/.env.local"

  cat > "$tmp/scripts/soak-stack.sh" << FAKE
#!/usr/bin/env bash
echo "\$1" >> "$tmp/calls.log"
[ "\$1" = ps ] && { echo "  fake-db: $([ "$ps_rc" = 0 ] && echo running || echo '(없음)')"; exit $ps_rc; }
exit 0
FAKE
  cat > "$tmp/scripts/assert-main-checkout.sh" << 'FAKE'
#!/usr/bin/env bash
exit 0
FAKE
  cat > "$tmp/scripts/soak-observe.sh" << FAKE
#!/usr/bin/env bash
echo observe >> "$tmp/calls.log"
printf 'SESSION_ID=%s\n' "$UUID" > "$tmp/.soak/session"
exit 0
FAKE
  cat > "$tmp/scripts/soak-gate.sh" << FAKE
#!/usr/bin/env bash
echo gate >> "$tmp/calls.log"
echo "판정: UNKNOWN 진행중"
exit 2
FAKE

  # ── PATH 앞단 가짜 ────────────────────────────────────────────────────────────
  # docker: `_q` 의 psql 은 값을, `logs` 는 한 줄을, `COPY` 는 헤더를 낸다.
  #   ★빈 출력은 이 스크립트에서 전부 die 다 — 가짜가 조용하면 갈래가 아니라 덤프가 재진다.
  cat > "$tmp/bin/docker" << FAKE
#!/usr/bin/env bash
echo docker >> "$tmp/calls.log"   # ★인자를 안 적는다 — SQL 이 여러 줄이라 로그가 찢어진다
case " \$* " in
  *" logs "*)  echo "2026-08-09T00:00:00Z fake worker line"; exit 0 ;;
  *"COPY "*)   echo "id,created_at"; exit 0 ;;
  *"ORDER BY created_at DESC LIMIT 1"*) echo "$UUID"; exit 0 ;;
esac
echo "$UUID"
exit 0
FAKE
  # uv: live_session_admin.py 의 status/start 만 흉내낸다. metrics 렌더는 한 줄로 대체.
  cat > "$tmp/bin/uv" << 'FAKE'
#!/usr/bin/env bash
case " $* " in
  *" status "*) printf 'FLAT=YES\nEXCLUSIVE=YES\nRESTING_CONDITIONAL=0\n'; exit 0 ;;
  *" start "*)  printf '✓ 세션 등재: aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee\n'; exit 0 ;;
esac
echo "qb_fake_metric 1"
exit 0
FAKE
  chmod +x "$tmp"/scripts/*.sh "$tmp"/bin/*
  printf '%s' "$tmp"
}

_run() { # _run <ps_rc> <추가 인자...> → stdout+stderr, calls.log 는 $LAST_CALLS
  local tree rc
  tree="$(_make_tree "$1")"
  shift
  OUT="$(cd "$tree" && PATH="$tree/bin:$PATH" bash "$tree/scripts/soak-restart.sh" "$@" 2>&1)"
  rc=$?
  # ★순서 단언은 **스택 호출만** 본다 — 사이사이 끼는 `docker exec psql` 은 이 질문과 무관하고,
  #   그걸 안 걸러내면 인접 패턴(`ps pin up`)이 DB 조회 한 줄에 깨진다(첫 판에 실제로 깨졌다).
  LAST_CALLS="$(grep -vx docker "$tree/calls.log" 2>/dev/null | tr '\n' ' ' | tr -s ' ')"
  LAST_RC="$rc"
  rm -rf "$tree"
}

echo "══ soak-restart 갈래 하네스 ([BL-656]) ══"
echo
echo "── ① dry-run 이 갈래를 고른다 (변이 M) ──"

_run 1
case "$OUT" in
  *"완전 down"*"pin → up 을 선행"*) _ok "ps=down → dry-run 이 down 갈래를 고른다" ;;
  *) _no "ps=down 인데 down 갈래를 안 골랐다" "$OUT" ;;
esac

_run 0
case "$OUT" in
  *"살아 있다"*) _ok "ps=up → dry-run 이 up 갈래를 고른다 (음성 대조)" ;;
  *) _no "ps=up 인데 up 갈래를 안 골랐다" "$OUT" ;;
esac

echo
echo "── ② 집행 순서 — 로그가 오라클이다 ──"

_run 1 --confirm
case "$LAST_CALLS" in
  "ps pin up "*) _ok "완전 down: pin → up 을 선행한다" ;;
  *) _no "완전 down 인데 pin → up 선행이 없다" "$LAST_CALLS" ;;
esac
case "$LAST_CALLS" in
  *" down "*) _no "완전 down 인데 down 을 불렀다 — 내릴 것이 없다" "$LAST_CALLS" ;;
  *) _ok "완전 down: down 을 부르지 않는다" ;;
esac
case "$OUT" in
  *"⑷ (건너뜀"*) _ok "완전 down: ⑷ 와 덤프를 건너뛴다" ;;
  *) _no "완전 down 인데 ⑷ 를 건너뛰지 않았다" "$OUT" ;;
esac
[ "$LAST_RC" = 0 ] && _ok "완전 down: 끝까지 갔다 (rc=0)" || _no "완전 down 경로가 rc=$LAST_RC 로 끝났다" "$OUT"

_run 0 --confirm
case "$LAST_CALLS" in
  "ps down pin up "*) _ok "이미 up: ⑷ 가 down → pin → up 을 그대로 한다 (음성 대조)" ;;
  *) _no "이미 up 인데 ⑷ 순서가 down → pin → up 이 아니다" "$LAST_CALLS" ;;
esac
case "$LAST_CALLS" in
  "ps pin"*) _no "이미 up 인데 pin 을 선행했다 — ⓿ 가 새 나갔다" "$LAST_CALLS" ;;
  *) _ok "이미 up: ⓿ 가 pin/up 을 선행하지 않는다" ;;
esac
case "$OUT" in
  *"⑷-0 down 직전 원자료 덤프"*) _ok "이미 up: 덤프가 여전히 down 앞에 있다" ;;
  *) _no "이미 up 인데 덤프 단계가 사라졌다" "$OUT" ;;
esac
[ "$LAST_RC" = 0 ] && _ok "이미 up: 끝까지 갔다 (rc=0)" || _no "이미 up 경로가 rc=$LAST_RC 로 끝났다" "$OUT"

echo
echo "── ③ dry-run 이 자기 설명문을 실행하지 않는다 (결함 ① 회귀 방지) ──"
#
# ★2026-08-08 에 「수리했고 정적 카운트 0건으로 동결」이라 기록됐지만 **동결 장치가 없었다** —
#   2026-08-09 실측으로 백틱 1쌍이 되돌아와 dry-run 이 `ConnectionRefusedError` 를 명령으로
#   실행하고(stderr: command not found) 그 낱말이 출력에서 사라져 있었다. 여기서 센다.
HEREDOC="$(awk '/^  cat << EOF$/{f=1;next} /^EOF$/{f=0} f' "$REAL")"
BAD="$(printf '%s' "$HEREDOC" | grep -c '`' || true)"
[ "$BAD" = 0 ] && _ok "unquoted heredoc 안 백틱 0건" || _no "unquoted heredoc 안 백틱 $BAD 줄 — dry-run 이 그것을 실행한다"
BAD="$(printf '%s' "$HEREDOC" | grep -c '\$(' || true)"
[ "$BAD" = 0 ] && _ok "unquoted heredoc 안 \$( 0건" || _no "unquoted heredoc 안 \$( $BAD 줄"

_run 0
case "$OUT" in
  *"command not found"*) _no "dry-run 이 자기 설명문을 실행했다" "$OUT" ;;
  *) _ok "dry-run 실행 출력에 command not found 0건" ;;
esac

echo
echo "── ④ stop 이 flatten 보다 먼저다 (실측으로 갈린 순서) ──"
# 세션이 살아 있는 채로 flatten 하면 엔진이 다음 tick 에 재무장한다. 안내문 순서가 정본이다.
S="$(grep -n 'live_session_admin.py stop' "$REAL" | head -1 | cut -d: -f1)"
F="$(grep -n 'live_session_admin.py flatten' "$REAL" | head -1 | cut -d: -f1)"
if [ -n "$S" ] && [ -n "$F" ] && [ "$S" -lt "$F" ]; then
  _ok "stop($S) 이 flatten($F) 보다 앞에 있다"
else
  _no "stop/flatten 순서가 뒤집혔다 (stop=$S flatten=$F)"
fi

echo
echo "════════════════════════════════════"
echo "통과 ${PASS} · 실패 ${FAIL}"
[ "$FAIL" -eq 0 ] || exit 1
echo "✓ 전건 통과"
