#!/usr/bin/env bash
# soak-watch 알림 판단 하네스 — [BL-003] 무인 감시. 전건 통과 = 종료 코드 0.
#
# 왜 필요한가
#   알림 스크립트의 고장 모드는 **둘 다 조용하다.** 안 쏘면 소크가 죽어도 모르고, 늘 쏘면
#   사람이 30 분마다 오는 알림을 무시하게 되어 결국 같은 결과가 된다. 그런데 「늘 쏘는 알림」은
#   **양성 케이스를 전건 통과한다** — FAIL 에도 쏘고, 실격에도 쏘고, C5 위반에도 쏜다.
#   ★그래서 **음성 대조가 이 하네스의 존재 이유다.** 「무변화 → 무발화」와 「정상 UNKNOWN(exit 2)
#   → 무발화」를 단언하지 않으면 판별력이 0 이다.
#
# ★판정 로직을 heredoc 에 베끼지 않는다. 임시 트리에 `soak-watch.sh` **사본**과 **가짜
#   `soak-gate.sh`** 를 나란히 두고 진짜 스크립트를 겨눈다(`bl-audit-test.sh` 와 같은 수법 —
#   watch 는 `dirname $0` 옆의 게이트를 부르므로 사본 옆에 두면 그 가짜를 읽는다).
#
# ★픽스처는 **실측 캡처**다. 정상 = 2026-08-07 13:11Z 오라클 서버 실행 전문,
#   크래시 = 같은 날 09:10:53 journal 전문(판정기가 낡은 체크아웃에서 죽었을 때).
#   변형은 그 한 벌에서 **해당 줄만 sed 로 바꿔** 파생한다 — 손으로 다시 쓰면 앵커가 갈린다.
#
# ★종료 코드가 판정이므로 **파이프 없이** 읽는다 (`| tail` 이 $? 를 가린다 — 실측 사고 이력).
#
# 사용법: scripts/soak-watch-test.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
WATCH="$ROOT/scripts/soak-watch.sh"
[ -f "$WATCH" ] || {
  echo "✗ 감시 스크립트가 없다: $WATCH" >&2
  exit 1
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0
OUT=""
RC=0
SENT=""

# ── 실측 캡처 ①: 정상 (2026-08-07T13:11:39Z 오라클) ─────────────────────────────
_fixture_normal() {
  cat << 'EOF'

══ [BL-003] 소크 안정 게이트 ══
판정: UNKNOWN 진행중
누적 3.59h / 168h (2.1%) · 최장 연속 3.52h / 24h · 실격 0

  ✗ C1 누적       3.5929h / 168h
  ✗ C2 최장 연속  3.5213h / 24h
  ✓ C3 실격 사건  0건
  ✓ C4 표본 공백  0건
  ✓ C5 측정 무결  db_ok=✓ stack_pinned=✓ phantom_archive=✓ darkness_computed=✓ divergence_labels_readable=✓ aof_ok=✓

  창 시작: 2026-08-06T20:31:48.126468+00:00   현재: 2026-08-07T13:11:39.137261+00:00
  귀속 창 2개:
        · 913c8681 0c9ccc683ac1 2026-08-07T09:35:06.318096+00:00 ~ 2026-08-07T09:39:24.071518+00:00  0.0716h
        · 39484a2c 0c9ccc683ac1 2026-08-07T09:39:38.744077+00:00 ~ 2026-08-07T13:10:55.463607+00:00  3.5213h
  ★귀속 불가 시간(계상 안 함): 101.53h
  ★phantom 미검증이라 잘려나간 시간: 0.0121h
  어둠 비율(보고 전용): 70.6%  (173/245)
  전 이력 실격 사건 8건
        · 2026-08-05T09:12:53.799957+00:00 auto_death a16aa640 position_divergence
        · 2026-08-06T20:31:48.126468+00:00 auto_death c160a1a9 gap_resync_position_mismatch

종료 코드 2  (0=PASS 만 · 1=FAIL · 2=UNKNOWN)
EOF
}

# ── 실측 캡처 ②: 크래시 (2026-08-07T09:10:53Z journal) ──────────────────────────
# ★헤더는 찍히고 `판정:` 이 **빈 값**이며 종료 코드가 **1** 이다 — 진짜 FAIL 과 구분되지 않는다.
#   판별자는 C1 앵커 줄의 부재뿐이다.
_fixture_crash() {
  cat << 'EOF'

══ [BL-003] 소크 안정 게이트 ══
판정:
Traceback (most recent call last):
  File "<stdin>", line 3, in <module>
  File "/usr/lib/python3.10/json/__init__.py", line 346, in loads
    return _default_decoder.decode(s)
json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)

종료 코드 1  (0=PASS 만 · 1=FAIL · 2=UNKNOWN)
EOF
}

# ── 하네스 배선 ─────────────────────────────────────────────────────────────────
_build_tree() { # _build_tree — 사본 + 가짜 게이트 + 가짜 sender
  rm -rf "$TMP/tree"
  mkdir -p "$TMP/tree/scripts"
  cp "$WATCH" "$TMP/tree/scripts/soak-watch.sh"

  cat > "$TMP/fake-sender.sh" << 'EOF'
#!/usr/bin/env bash
cat >> "$QB_FAKE_SENT"
EOF
  cat > "$TMP/fail-sender.sh" << 'EOF'
#!/usr/bin/env bash
cat > /dev/null
exit 1
EOF
  chmod +x "$TMP/fake-sender.sh" "$TMP/fail-sender.sh"
}

_set_gate() { # stdin = 게이트가 낼 stdout,  $1 = 게이트 종료 코드
  {
    echo '#!/usr/bin/env bash'
    echo "cat <<'GATEEOF'"
    cat
    echo 'GATEEOF'
    echo "exit $1"
  } > "$TMP/tree/scripts/soak-gate.sh"
  chmod +x "$TMP/tree/scripts/soak-gate.sh"
}

_run() { # _run [sender]  → $OUT / $RC / $SENT
  : > "$TMP/sent"
  # ★파이프 없음. 명령 치환의 종료 코드가 곧 스크립트의 종료 코드다.
  OUT="$(QB_SOAK_WATCH_STATE="$TMP/state" \
    QB_SOAK_NOTIFY_CMD="${1:-$TMP/fake-sender.sh}" \
    QB_FAKE_SENT="$TMP/sent" \
    bash "$TMP/tree/scripts/soak-watch.sh" 2>&1)"
  RC=$?
  SENT="$(cat "$TMP/sent" 2>/dev/null)"
}

_reset_state() { rm -f "$TMP/state"; }

report() { # report <label> <why(빈 문자열이면 통과)>
  if [ -n "$2" ]; then
    FAIL=$((FAIL + 1))
    printf '  ✗ %-52s %s\n' "$1" "$2"
    printf '%s\n' "SENT=[$SENT] RC=$RC OUT=[$OUT]" | sed 's/^/        | /'
  else
    PASS=$((PASS + 1))
    printf '  ✓ %-52s\n' "$1"
  fi
}

assert_sent() { # assert_sent <label> <기대 rc> <있어야 할 마커|-> <없어야 할 마커|->
  local why=""
  [ "$RC" -eq "$2" ] || why="${why}종료코드=$RC(기대 $2) "
  [ -n "$SENT" ] || why="${why}★알림이 안 나갔다 "
  if [ "$3" != "-" ] && ! printf '%s' "$SENT" | grep -q -- "$3"; then
    why="${why}'$3' 마커 없음 "
  fi
  if [ "$4" != "-" ] && printf '%s' "$SENT" | grep -q -- "$4"; then
    why="${why}★'$4' 가 잘못 발화 "
  fi
  report "$1" "$why"
}

assert_silent() { # assert_silent <label> <기대 rc>
  local why=""
  [ "$RC" -eq "$2" ] || why="${why}종료코드=$RC(기대 $2) "
  [ -z "$SENT" ] || why="${why}★침묵해야 하는데 발화했다 "
  report "$1" "$why"
}

echo "══ soak-watch 알림 판단 하네스  (임시 트리 · 실측 캡처 픽스처 · 진짜 스크립트) ══"
echo "  대상: $WATCH"
echo

_build_tree

# ── ① 첫 실행은 알린다. 그 다음 **같은 상태면 침묵**한다 ─────────────────────────
#    이게 음성 대조의 본체다 — 「늘 쏘는 알림」은 여기서만 죽는다.
_reset_state
_fixture_normal | _set_gate 2
_run
assert_sent "① 첫 실행 → 첫 지문 알림" 0 "감시 시작" "지문 변화"

_run
assert_silent "① 같은 상태 재실행 → **무발화**" 0

_run
assert_silent "① 3회 연속 정상 → 여전히 무발화" 0

# ── ② UNKNOWN → FAIL ────────────────────────────────────────────────────────────
_fixture_normal | sed 's/^판정: UNKNOWN 진행중/판정: FAIL 실격/' | _set_gate 1
_run
assert_sent "② UNKNOWN→FAIL → FAIL 알림" 0 "판정 FAIL" "게이트 크래시"

# ── ③ 실격 +1 ───────────────────────────────────────────────────────────────────
_reset_state
_fixture_normal | _set_gate 2
_run # prime (실격 0)
_fixture_normal | sed 's/C3 실격 사건  0건/C3 실격 사건  1건/' | _set_gate 2
_run
assert_sent "③ 실격 0→1 → '실격 +1'" 0 "실격 +1" "-"

# ── ④ 활성 세션 0 (귀속 창 0개) ─────────────────────────────────────────────────
_reset_state
_fixture_normal | _set_gate 2
_run # prime
_fixture_normal | sed 's/^  귀속 창 2개:/  귀속 창 0개:/' | _set_gate 2
_run
assert_sent "④ 귀속 창 0 → '세션 0 = 시계 0'" 0 "활성 귀속 창 0" "-"

# ── ⑤ C5 위반 ───────────────────────────────────────────────────────────────────
_reset_state
_fixture_normal | _set_gate 2
_run # prime
_fixture_normal | sed 's/darkness_computed=✓/darkness_computed=✗/' | _set_gate 2
_run
assert_sent "⑤ C5 ✗ → 'C5 측정 무결 위반'" 0 "C5 측정 무결 위반" "-"

# ── ⑥ C5 복구 ───────────────────────────────────────────────────────────────────
#    ★복구도 알려야 한다. 안 그러면 사람이 「아직 깨져 있다」로 남겨둔다.
_fixture_normal | _set_gate 2
_run
assert_sent "⑥ C5 복구 → 지문 변화 알림" 0 "지문 변화" "C5 측정 무결 위반"

# ── ⑦ 게이트 exit 2 는 **정상**이다 (UNKNOWN = 아직 진행중) ─────────────────────
#    ★게이트의 기본 상태가 exit 2 다. 이걸 이상으로 읽으면 30분마다 알림이 온다.
_reset_state
_fixture_normal | _set_gate 2
_run # prime
_run
assert_silent "⑦ 게이트 exit 2(정상 UNKNOWN) → **무발화**" 0

# ── ⑧ 크래시 — 실측 캡처. **FAIL 로 보고하면 안 된다** ──────────────────────────
_reset_state
_fixture_crash | _set_gate 1
_run
assert_sent "⑧ 크래시(실측 캡처) → '게이트 크래시'" 0 "게이트 크래시" "판정 FAIL"

# ── ⑧b 빈 출력도 크래시다 ───────────────────────────────────────────────────────
_reset_state
printf '' | _set_gate 1
_run
assert_sent "⑧b 빈 출력 → '게이트 크래시'" 0 "게이트 크래시" "판정 FAIL"

# ── ⑨ 텔레그램 전송 실패 → **감시자 종료 코드 1** ───────────────────────────────
#    ★게이트 판정이 아니라 「알림이 깨졌다」를 뜻한다. systemd 의 빨간불이 이 뜻이어야 한다.
_reset_state
_fixture_normal | _set_gate 2
_run "$TMP/fail-sender.sh"
_why=""
[ "$RC" -eq 1 ] || _why="종료코드=$RC(기대 1) "
report "⑨ 텔레그램 실패 → 감시자 exit 1" "$_why"

# ── ⑨b 전송 실패 뒤에도 상태를 남겨 **같은 알림을 다시 시도**하지 않는가? ────────
#    지문은 저장하되 heartbeat 날짜는 전진시키지 않는다(그날의 heartbeat 를 잃지 않게).
_why=""
grep -q '^FINGERPRINT=UNKNOWN' "$TMP/state" 2>/dev/null || _why="지문이 저장되지 않았다 "
grep -q '^HEARTBEAT_DATE=$' "$TMP/state" 2>/dev/null || _why="${_why}heartbeat 날짜가 전진했다 "
report "⑨b 전송 실패 시 heartbeat 날짜 미전진" "$_why"

# ── ⑩ 상태 파일을 `.` 로 소싱해도 안전한가 (맨 값 사고 재발 방지) ───────────────
#    ★`.soak/session` 이 맨 uuid 로 쓰여 `command not found` 로 죽어 있던 것을 실측했다.
#      여기 상태 파일은 소싱하지 않지만, 형식이 key=value 인지는 단언해 둔다.
_why=""
if [ -f "$TMP/state" ]; then
  while IFS= read -r _l; do
    case "$_l" in
      *=*) ;;
      "") ;;
      *) _why="key=value 가 아닌 줄이 있다: $_l " ;;
    esac
  done < "$TMP/state"
else
  _why="상태 파일이 없다 "
fi
report "⑩ 상태 파일이 key=value 형식" "$_why"

echo
echo "══════════════════════════════════════════"
printf '  통과 %d · 실패 %d\n' "$PASS" "$FAIL"
echo "══════════════════════════════════════════"
[ "$FAIL" -eq 0 ] || exit 1
echo "✓ 전건 통과  (★실제 텔레그램은 한 번도 쏘지 않았다 — QB_SOAK_NOTIFY_CMD 주입)"
exit 0
