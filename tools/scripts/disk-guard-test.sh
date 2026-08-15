#!/usr/bin/env bash
# disk-guard 발화 판단 하네스 — [BL-768]. 전건 통과 = 종료 코드 0.
#
# 왜 필요한가
#   경보 스크립트의 고장 모드는 **둘 다 조용하다.** 안 쏘면 디스크가 차도 모르고, 늘 쏘면
#   사람이 매시간 오는 알림을 무시하게 되어 결국 같은 결과가 된다. 그런데 「늘 쏘는 경보」는
#   **양성 케이스를 전건 통과한다** — 80% 에도 쏘고 95% 에도 쏜다.
#   ★그래서 **음성 대조가 이 하네스의 존재 이유다.** 「임계 미만 → 무발화」와
#   「WARN 유지 → 같은 날 재발화 안 함」을 단언하지 않으면 판별력이 0 이다.
#
# ★판정 로직을 heredoc 에 베끼지 않는다. **진짜 스크립트**를 겨누고 `df` 만 스텁으로 가로챈다.
#   실제 디스크 사용률에 의존하면 이 하네스는 CI 머신마다 다른 답을 낸다.
#
# ★종료 코드가 판정이므로 **파이프 없이** 읽는다 (`| tail` 이 $? 를 가린다 — 실측 사고 이력).
#
# 사용법: tools/scripts/disk-guard-test.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
GUARD="$ROOT/tools/scripts/disk-guard.sh"
NOTIFY_LIB="$ROOT/tools/scripts/lib/notify-telegram.sh"
[ -f "$GUARD" ] || {
  echo "✗ 경보 스크립트가 없다: $GUARD" >&2
  exit 1
}
[ -f "$NOTIFY_LIB" ] || {
  echo "✗ 알림 라이브러리가 없다: $NOTIFY_LIB" >&2
  exit 1
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0
OUT=""
RC=0
SENT=""

report() { # report <이름> <실패사유(빈 문자열이면 통과)>
  if [ -z "$2" ]; then
    PASS=$((PASS + 1))
    printf '  ✓ %s\n' "$1"
  else
    FAIL=$((FAIL + 1))
    printf '  ✗ %s — %s\n' "$1" "$2"
    printf '     rc=%s\n' "$RC"
    printf '%s\n' "$OUT" | sed 's/^/     | /' | head -12
  fi
}

# ── 배선 ────────────────────────────────────────────────────────────────────────
mkdir -p "$TMP/bin"

# 가짜 df — QB_FAKE_PCT 를 그대로 5번째 필드로 돌려준다.
# QB_FAKE_DF_BROKEN=1 이면 판독 실패를 흉내낸다(빈 출력 + rc=1).
cat > "$TMP/bin/df" << 'EOF'
#!/usr/bin/env bash
if [ "${QB_FAKE_DF_BROKEN:-0}" = "1" ]; then
  exit 1
fi
cat << INNER
Filesystem     1024-blocks     Used Available Capacity Mounted on
/dev/sda1        101425200 39953128  61455688      ${QB_FAKE_PCT}% /
INNER
EOF

# 가짜 systemctl — 설치 경로가 리눅스 전용 분기를 타게 한다.
cat > "$TMP/bin/systemctl" << 'EOF'
#!/usr/bin/env bash
exit 0
EOF

cat > "$TMP/fake-sender.sh" << 'EOF'
#!/usr/bin/env bash
cat >> "$QB_FAKE_SENT"
EOF
cat > "$TMP/fail-sender.sh" << 'EOF'
#!/usr/bin/env bash
cat > /dev/null
exit 1
EOF
chmod +x "$TMP/bin/df" "$TMP/bin/systemctl" "$TMP/fake-sender.sh" "$TMP/fail-sender.sh"

printf 'TELEGRAM_BOT_TOKEN=x\nTELEGRAM_CHAT_ID=y\n' > "$TMP/fake.env"

STATE="$TMP/state"

_run() { # _run <사용률%> [sender]
  : > "$TMP/sent"
  OUT="$(PATH="$TMP/bin:$PATH" \
    QB_FAKE_PCT="$1" \
    QB_DISK_STATE="$STATE" \
    QB_SOAK_ENV_FILE="$TMP/fake.env" \
    QB_DISK_NOTIFY_CMD="${2:-$TMP/fake-sender.sh}" \
    QB_FAKE_SENT="$TMP/sent" \
    bash "$GUARD" 2>&1)"
  RC=$?
  SENT="$(cat "$TMP/sent" 2> /dev/null)"
}

_reset() { rm -f "$STATE" "$TMP/sent"; }

echo "══ disk-guard 하네스 ══"
echo "  대상: $GUARD"
echo

# ── ① 음성 대조: 임계 미만 → 무발화 ────────────────────────────────────────────
# ★이것이 이 하네스의 존재 이유다. 여기가 초록이 아니면 나머지 통과는 아무 뜻이 없다.
_reset
_run 40
_why=""
[ "$RC" -eq 0 ] || _why="rc=$RC (기대 0) "
[ -z "$SENT" ] || _why="${_why}★임계 미만인데 알림이 나갔다 "
report "① 40% (임계 80) → 무발화" "$_why"

# ── ② 양성 대조: 임계 초과 → 발화 ──────────────────────────────────────────────
_reset
_run 85
_why=""
[ "$RC" -eq 0 ] || _why="rc=$RC (기대 0) "
[ -n "$SENT" ] || _why="${_why}★임계를 넘었는데 알림이 없다 "
printf '%s' "$SENT" | grep -q '85%' || _why="${_why}본문에 사용률이 없다 "
printf '%s' "$SENT" | grep -q '여유' || _why="${_why}본문에 여유 용량이 없다 "
report "② 85% → 발화 (사용률·여유 포함)" "$_why"

# ── ③ 경계값: PCT == 임계 → WARN (>= 판정) ─────────────────────────────────────
_reset
_run 80
_why=""
[ -n "$SENT" ] || _why="★경계값 80% 가 무발화다 (>= 이어야 한다) "
report "③ 경계값 80% == 임계 → 발화" "$_why"

# ── ④ WARN 유지 + 같은 날 → 재발화 안 함 ───────────────────────────────────────
# 늘 쏘는 경보는 사람이 무시하게 되므로 이것도 결함이다.
_reset
_run 85
_run 86
_why=""
[ -z "$SENT" ] || _why="★같은 날 WARN 이 이어지는데 또 쐈다 "
report "④ WARN 유지 · 같은 날 → 무발화" "$_why"

# ── ⑤ WARN 유지 + 날짜가 바뀌면 → 재고지 ───────────────────────────────────────
_reset
_run 85
printf 'LEVEL=WARN\nNOTIFIED_DATE=2000-01-01\n' > "$STATE"
_run 85
_why=""
[ -n "$SENT" ] || _why="★날이 바뀌었는데 재고지가 없다 "
printf '%s' "$SENT" | grep -q '재고지' || _why="${_why}재고지 문구가 없다 "
report "⑤ WARN 유지 · 날짜 변경 → 재고지" "$_why"

# ── ⑥ WARN → OK 전이 → 회복 알림 ───────────────────────────────────────────────
_reset
_run 85
_run 40
_why=""
[ -n "$SENT" ] || _why="★회복했는데 알림이 없다 "
printf '%s' "$SENT" | grep -q '회복' || _why="${_why}회복 문구가 없다 "
report "⑥ WARN → OK → 회복 알림" "$_why"

# ── ⑦ OK 유지 → 무발화 (회복 알림이 반복되지 않는다) ───────────────────────────
_reset
_run 85
_run 40
_run 41
_why=""
[ -z "$SENT" ] || _why="★OK 가 이어지는데 알림이 나갔다 "
report "⑦ OK 유지 → 무발화" "$_why"

# ── ⑧ df 판독 실패 → rc=1 ──────────────────────────────────────────────────────
# ★fail-open 을 막는 축이다. df 가 죽었는데 0 을 내면 「디스크는 괜찮다」로 읽힌다.
_reset
: > "$TMP/sent"
OUT="$(PATH="$TMP/bin:$PATH" \
  QB_FAKE_DF_BROKEN=1 \
  QB_DISK_STATE="$STATE" \
  QB_SOAK_ENV_FILE="$TMP/fake.env" \
  QB_DISK_NOTIFY_CMD="$TMP/fake-sender.sh" \
  QB_FAKE_SENT="$TMP/sent" \
  bash "$GUARD" 2>&1)"
RC=$?
_why=""
[ "$RC" -eq 1 ] || _why="★df 판독 실패인데 rc=$RC (기대 1) "
printf '%s' "$OUT" | grep -q '판독 실패' || _why="${_why}진단 문구가 없다 "
report "⑧ df 판독 실패 → red (fail-open 아님)" "$_why"

# ── ⑨ 전송 실패 → rc=1 · 날짜 미전진 ───────────────────────────────────────────
# ★알림을 상태 저장보다 먼저 하는지를 재는 축이다. 저장이 앞서면 「보냈다」로 기록되고
#   다음 주기에 재고지가 사라진다 — 조용한 실패가 된다.
_reset
_run 85 "$TMP/fail-sender.sh"
_why=""
[ "$RC" -eq 1 ] || _why="★전송 실패인데 rc=$RC (기대 1) "
grep -q '^NOTIFIED_DATE=$' "$STATE" 2> /dev/null \
  || _why="${_why}전송 실패인데 NOTIFIED_DATE 가 전진했다: $(sed -n 's/^NOTIFIED_DATE=//p' "$STATE" 2> /dev/null) "
report "⑨ 전송 실패 → rc=1 · 날짜 미전진" "$_why"

# ── ⑩ 상태 파일이 key=value 형식 (소싱하지 않는 계약) ──────────────────────────
_reset
_run 85
_why=""
grep -Eq '^LEVEL=(OK|WARN)$' "$STATE" || _why="LEVEL 줄이 없다 "
grep -q '^NOTIFIED_DATE=' "$STATE" || _why="${_why}NOTIFIED_DATE 줄이 없다 "
[ "$(wc -l < "$STATE" | tr -d ' ')" = "2" ] || _why="${_why}줄 수가 2 가 아니다 "
report "⑩ 상태 파일 key=value 2줄" "$_why"

# ── ⑪ --dry-run 은 한 번도 안 쏜다 ─────────────────────────────────────────────
_reset
: > "$TMP/sent"
OUT="$(PATH="$TMP/bin:$PATH" QB_FAKE_PCT=95 \
  QB_DISK_STATE="$STATE" QB_SOAK_ENV_FILE="$TMP/fake.env" \
  QB_DISK_NOTIFY_CMD="$TMP/fake-sender.sh" QB_FAKE_SENT="$TMP/sent" \
  bash "$GUARD" --dry-run 2>&1)"
RC=$?
SENT="$(cat "$TMP/sent" 2> /dev/null)"
_why=""
[ -z "$SENT" ] || _why="★dry-run 인데 알림이 나갔다 "
printf '%s' "$OUT" | grep -q 'dry-run' || _why="${_why}dry-run 표시가 없다 "
[ -f "$STATE" ] && _why="${_why}★dry-run 이 상태 파일을 썼다 "
report "⑪ --dry-run → 무발화 · 상태 미기록" "$_why"

# ── ⑫ 임계 override 가 실제로 먹는가 ───────────────────────────────────────────
# ★양성 대조의 판별력 확인 — 임계가 안 먹으면 ①②가 우연히 통과했을 수 있다.
_reset
: > "$TMP/sent"
OUT="$(PATH="$TMP/bin:$PATH" QB_FAKE_PCT=40 QB_DISK_WARN_PCT=30 \
  QB_DISK_STATE="$STATE" QB_SOAK_ENV_FILE="$TMP/fake.env" \
  QB_DISK_NOTIFY_CMD="$TMP/fake-sender.sh" QB_FAKE_SENT="$TMP/sent" \
  bash "$GUARD" 2>&1)"
RC=$?
SENT="$(cat "$TMP/sent" 2> /dev/null)"
_why=""
[ -n "$SENT" ] || _why="★임계 30 · 사용률 40 인데 무발화 (override 가 안 먹는다) "
report "⑫ QB_DISK_WARN_PCT override 가 먹는다" "$_why"

# ── ⑬ 임계가 숫자가 아니면 거부 ────────────────────────────────────────────────
_reset
OUT="$(PATH="$TMP/bin:$PATH" QB_FAKE_PCT=40 QB_DISK_WARN_PCT=eighty \
  QB_DISK_STATE="$STATE" QB_SOAK_ENV_FILE="$TMP/fake.env" \
  QB_DISK_NOTIFY_CMD="$TMP/fake-sender.sh" \
  bash "$GUARD" 2>&1)"
RC=$?
_why=""
[ "$RC" -eq 1 ] || _why="★비숫자 임계인데 rc=$RC (기대 1) "
report "⑬ 비숫자 임계 → red" "$_why"

# ── ⑭ --install 유닛: --fail · \$\$ 이스케이프 · 토큰 미포함 ───────────────────
XDG="$TMP/xdg"
rm -rf "$XDG"
OUT="$(PATH="$TMP/bin:$PATH" XDG_CONFIG_HOME="$XDG" \
  QB_SOAK_ENV_FILE="$TMP/fake.env" \
  bash "$GUARD" --install 2>&1)"
RC=$?
UNIT_SVC="$XDG/systemd/user/dev.quantbridge.disk-guard.service"
ALARM_SVC="$XDG/systemd/user/dev.quantbridge.disk-guard-alarm.service"
TIMER="$XDG/systemd/user/dev.quantbridge.disk-guard.timer"
_why=""
[ "$RC" -eq 0 ] || _why="rc=$RC (기대 0) "
[ -f "$UNIT_SVC" ] || _why="${_why}service 유닛이 없다 "
[ -f "$TIMER" ] || _why="${_why}timer 유닛이 없다 "
grep -q "^ExecStart=/bin/bash $GUARD\$" "$UNIT_SVC" 2> /dev/null \
  || _why="${_why}ExecStart 가 현재 스크립트가 아니다 "
grep -q "^OnFailure=dev.quantbridge.disk-guard-alarm.service\$" "$UNIT_SVC" 2> /dev/null \
  || _why="${_why}OnFailure 가 없다 "
report "⑭ --install: ExecStart + OnFailure" "$_why"

_why=""
[ -f "$ALARM_SVC" ] || _why="알람 유닛이 없다 "
grep -q -- '--fail' "$ALARM_SVC" 2> /dev/null \
  || _why="${_why}★알람 curl 에 --fail 이 없다 (404 에도 rc=0 이 된다) "
# ★`-F` 로 고정 문자열 비교한다 (`soak-watch-test.sh:450` 과 같은 패턴). 중괄호까지 포함해야
#   한다 — `$$TELEGRAM_BOT_TOKEN` 만 찾으면 실제 유닛의 `$${TELEGRAM_BOT_TOKEN}` 을 놓친다.
grep -qF 'bot$${TELEGRAM_BOT_TOKEN}' "$ALARM_SVC" 2> /dev/null \
  || _why="${_why}★\$\$ 이스케이프가 없다 (systemd 가 빈 문자열로 확장한다) "
grep -qF 'chat_id=$${TELEGRAM_CHAT_ID}' "$ALARM_SVC" 2> /dev/null \
  || _why="${_why}★chat_id 의 \$\$ 이스케이프가 없다 "
grep -q 'TELEGRAM_BOT_TOKEN=x' "$ALARM_SVC" 2> /dev/null \
  && _why="${_why}★토큰 값이 유닛에 박혔다 "
report "⑭b 알람 유닛: --fail · \$\$ 이스케이프 · 토큰 미포함" "$_why"

# 타이머는 벽시계 고정이어야 한다 — OnUnitActiveSec 은 위상이 밀린다([BL-737] 실측).
_why=""
grep -q '^OnCalendar=' "$TIMER" 2> /dev/null || _why="OnCalendar 가 없다 "
grep -q '^OnUnitActiveSec=' "$TIMER" 2> /dev/null \
  && _why="${_why}★OnUnitActiveSec 이 있다 (위상이 밀린다) "
grep -q '^Persistent=true$' "$TIMER" 2> /dev/null || _why="${_why}Persistent=true 가 없다 "
report "⑭c 타이머 벽시계 고정 (OnCalendar · Persistent)" "$_why"

# ── ⑮ --status 신선도: 갓 설치 → green / 옛 경로 → red ─────────────────────────
OUT="$(PATH="$TMP/bin:$PATH" XDG_CONFIG_HOME="$XDG" QB_FAKE_PCT=40 \
  QB_DISK_STATE="$STATE" QB_SOAK_ENV_FILE="$TMP/fake.env" \
  bash "$GUARD" --status 2>&1)"
RC=$?
_why=""
[ "$RC" -eq 0 ] || _why="★갓 설치했는데 rc=$RC (기대 0) "
report "⑮ --status 음성 대조: 갓 설치한 것은 green" "$_why"

sed -i.bak "s|^ExecStart=/bin/bash .*|ExecStart=/bin/bash $TMP/gone/disk-guard.sh|" "$UNIT_SVC"
OUT="$(PATH="$TMP/bin:$PATH" XDG_CONFIG_HOME="$XDG" QB_FAKE_PCT=40 \
  QB_DISK_STATE="$STATE" QB_SOAK_ENV_FILE="$TMP/fake.env" \
  bash "$GUARD" --status 2>&1)"
RC=$?
_why=""
[ "$RC" -eq 1 ] || _why="★낡은 ExecStart 인데 rc=$RC (기대 1) "
printf '%s' "$OUT" | grep -q 'rc=127' || _why="${_why}rc=127 진단이 없다 "
report "⑮b 옛 경로 ExecStart → red (재배치 사고 재현)" "$_why"
mv "$UNIT_SVC.bak" "$UNIT_SVC"

mv "$ALARM_SVC" "$ALARM_SVC.hidden"
OUT="$(PATH="$TMP/bin:$PATH" XDG_CONFIG_HOME="$XDG" QB_FAKE_PCT=40 \
  QB_DISK_STATE="$STATE" QB_SOAK_ENV_FILE="$TMP/fake.env" \
  bash "$GUARD" --status 2>&1)"
RC=$?
_why=""
[ "$RC" -eq 1 ] || _why="★알람 유닛이 없는데 rc=$RC (기대 1) "
printf '%s' "$OUT" | grep -q '실패 알림 유닛이 없다' || _why="${_why}진단 문구가 없다 "
report "⑮c 실패 알림 유닛 부재 → red" "$_why"
mv "$ALARM_SVC.hidden" "$ALARM_SVC"

echo
echo "══════════════════════════════════════════"
printf '  통과 %d · 실패 %d\n' "$PASS" "$FAIL"
echo "══════════════════════════════════════════"
[ "$FAIL" -eq 0 ] || exit 1
echo "✓ 전건 통과  (★실제 텔레그램은 한 번도 쏘지 않았다 — QB_DISK_NOTIFY_CMD 주입)"
exit 0
