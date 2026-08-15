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
# 사용법: tools/scripts/soak-watch-test.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
WATCH="$ROOT/tools/scripts/soak-watch.sh"
[ -f "$WATCH" ] || {
  echo "✗ 감시 스크립트가 없다: $WATCH" >&2
  exit 1
}
NOTIFY_LIB="$ROOT/tools/scripts/lib/notify-telegram.sh"
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

# ── 실측 캡처 ③: [BL-701] **이후** 서식 (2026-08-11 C1 문턱 교체) ──────────────
# ★위 ①·② 는 얼린 옛 캡처다. 그것만 두면 **C1 줄의 서식이 바뀌어도 하네스는 초록**이고,
#   그 사이 무인 감시는 매 실행을 「크래시」로 오판한다 — 2026-08-11 에 실제로 그럴 뻔했다.
#   서식이 바뀌는 축을 여기서 고정한다: 앵커는 라벨(`C1`)만 잡아야 한다.
_fixture_new_format() {
  cat << 'EOF'

══ [BL-003] 소크 안정 게이트 ══
판정: UNKNOWN 진행중
24h 창 1/3회 · 최장 연속 53.82h / 24h · 실격 0 (참고: 누적 69.14h)

  ✗ C1 24h 창    1 / 3회   (참고: 누적 69.1365h)
  ✓ C2 최장 연속  53.8225h / 24h
  ✓ C3 실격 사건  0건
  ✓ C4 표본 공백  0건
  ✓ C5 측정 무결  db_ok=✓ stack_pinned=✓ phantom_archive=✓ darkness_computed=✓ divergence_labels_readable=✓ aof_ok=✓

  창 시작: 2026-08-07T15:10:49.561534+00:00   현재: 2026-08-11T05:06:16.359147+00:00
  귀속 창 3개:
        · a4f1cbfb 3f8af9dfe78e 2026-08-08T02:32:42.863297+00:00 ~ 2026-08-08T17:50:45.243695+00:00  15.3007h
        · a4f1cbfb fdc53c04a929 2026-08-08T23:15:02+00:00 ~ 2026-08-08T23:15:49.858414+00:00  0.0133h
        · de3db35a fdc53c04a929 2026-08-08T23:16:52.585111+00:00 ~ 2026-08-11T05:06:13.711960+00:00  53.8225h

종료 코드 2  (0=PASS 만 · 1=FAIL · 2=UNKNOWN)
EOF
}

# ── 실측 아님: 오류 본문에만 `C1 ` 이 섞인 malformed 출력 (codex P2, 2026-08-11) ──
# ★앵커가 「어디든 C1 이 있으면 정상」이면 이걸 통과시킨다 — 게이트는 죽었는데 정상 지문이 된다.
_fixture_c1_in_error() {
  cat << 'EOF'

══ [BL-003] 소크 안정 게이트 ══
판정: UNKNOWN 측정불가
Traceback (most recent call last):
  File "<stdin>", line 9, in <module>
KeyError: 'C1 24h 창 을 계산하지 못했다'

종료 코드 2  (0=PASS 만 · 1=FAIL · 2=UNKNOWN)
EOF
}

# ── 하네스 배선 ─────────────────────────────────────────────────────────────────
_build_tree() { # _build_tree — 사본 + 가짜 게이트 + 가짜 sender
  rm -rf "$TMP/tree"
  mkdir -p "$TMP/tree/tools/scripts/lib"
  cp "$WATCH" "$TMP/tree/tools/scripts/soak-watch.sh"
  # ★lib 도 함께 옮긴다 — watch 는 `dirname $0` 옆의 `lib/notify-telegram.sh` 를 소싱하므로
  #   사본만 두면 임시 트리에서 `알림 라이브러리가 없다` 로 죽는다(2026-08-16 lib 추출 후속).
  cp "$NOTIFY_LIB" "$TMP/tree/tools/scripts/lib/notify-telegram.sh"

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
    # ★게이트가 받은 인자 개수를 남긴다. 종전 가짜 게이트는 "$@" 를 통째로 무시해서
    #   「게이트를 `--no-collect` 로 부르는」 회귀가 전건 초록으로 통과했다(2026-08-15 실측).
    #   `--no-collect` 는 phantom 아카이브를 안 남겨 C5 가 fail-open 이 된다.
    echo 'printf "%s\n" "$#" > "${QB_GATE_ARGC:-/dev/null}"'
    echo "cat <<'GATEEOF'"
    cat
    echo 'GATEEOF'
    echo "exit $1"
  } > "$TMP/tree/tools/scripts/soak-gate.sh"
  chmod +x "$TMP/tree/tools/scripts/soak-gate.sh"
}

# ── systemd 갈래 배선 (설치본 신선도 축, [BL-737]) ──────────────────────────────
#    ★맥에는 systemctl 이 없다. 가짜 systemctl 을 PATH 앞에 세우고 유닛 디렉터리를
#      XDG_CONFIG_HOME 으로 격리하면, **유닛 파일 산출물 자체**를 실측할 수 있다.
_build_systemd_seam() {
  rm -rf "$TMP/xdg" "$TMP/bin"
  mkdir -p "$TMP/bin"
  cat > "$TMP/bin/systemctl" << 'EOF'
#!/usr/bin/env bash
# 하네스용 no-op. is-enabled 만 1(비활성)을 내 게이트 타이머 disable 분기를 건너뛴다.
case "$*" in
  *is-enabled*) exit 1 ;;
esac
exit 0
EOF
  chmod +x "$TMP/bin/systemctl"
  printf 'TELEGRAM_BOT_TOKEN=x\nTELEGRAM_CHAT_ID=y\n' > "$TMP/fake.env"
}

_sd_env() { # 공통 환경 — 유닛 디렉터리·systemctl·env 파일을 전부 임시 트리로 가둔다
  XDG_CONFIG_HOME="$TMP/xdg" PATH="$TMP/bin:$PATH" \
    QB_SOAK_ENV_FILE="$TMP/fake.env" QB_SOAK_WATCH_STATE="$TMP/state" "$@"
}

_run_install() {
  OUT="$(_sd_env bash "$TMP/tree/tools/scripts/soak-watch.sh" --install 2>&1)"
  RC=$?
  SENT=""
}

_run_status() {
  OUT="$(_sd_env bash "$TMP/tree/tools/scripts/soak-watch.sh" --status 2>&1)"
  RC=$?
  SENT=""
}

UNIT_SVC="$TMP/xdg/systemd/user/dev.quantbridge.soak-watch.service"
ALARM_SVC="$TMP/xdg/systemd/user/dev.quantbridge.soak-watch-alarm.service"
TREE_REAL=""  # _build_tree 뒤에 채운다 (트리가 있어야 pwd -P 가 의미를 갖는다)

_run() { # _run [sender]  → $OUT / $RC / $SENT
  : > "$TMP/sent"
  # ★파이프 없음. 명령 치환의 종료 코드가 곧 스크립트의 종료 코드다.
  OUT="$(QB_SOAK_WATCH_STATE="$TMP/state" \
    QB_SOAK_NOTIFY_CMD="${1:-$TMP/fake-sender.sh}" \
    QB_FAKE_SENT="$TMP/sent" \
    bash "$TMP/tree/tools/scripts/soak-watch.sh" 2>&1)"
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
_build_systemd_seam
export QB_GATE_ARGC="$TMP/gate-argc"
# ★스크립트는 `pwd -P` 로 심볼릭을 해소한다 — 맥의 `/var` 는 `/private/var` 다.
#   기대값도 같은 방식으로 해소하지 않으면 ⑭ 가 **경로 표기만으로** red 를 낸다.
TREE_REAL="$(cd "$TMP/tree" && pwd -P)"

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

# ── ⑪ [BL-701] C1 줄의 **서식**이 바뀌어도 크래시로 오판하지 않는다 ────────────
#    ★재는 것은 「그 줄이 있나」이지 「무엇이라 적혀 있나」가 아니다. 앵커에 서식을 넣으면
#      문턱을 바꾸는 회차마다 무인 감시가 조용히 죽는다(2026-08-11 에 그럴 뻔했다).
_reset_state
_fixture_new_format | _set_gate 2
_run
# 4번째 인자 = **없어야 할** 마커. 서식이 바뀌었다고 크래시로 읽으면 여기서 죽는다.
assert_sent "⑪ 신 서식 → 정상 지문 · 크래시로 오판 안 함" 0 "감시 시작" "크래시"

_run
assert_silent "⑪ 신 서식 재실행 → 무발화" 0

# ── ⑫ 오류 본문의 `C1 ` 을 정상 판정으로 읽지 않는다 (앵커가 너무 넓으면 여기서 죽는다) ──
_reset_state
_fixture_c1_in_error | _set_gate 2
_run
assert_sent "⑫ 조건 줄 없이 오류 본문에만 C1 → 크래시로 읽는다" 0 "크래시" "-"

# ── ⑬ 게이트를 **인자 없이** 부른다 (수집 모드 보존) ────────────────────────────
#    ★`--no-collect` 를 더하면 phantom 아카이브가 안 남아 C5 가 fail-open 이 된다.
#      종전 하네스는 가짜 게이트가 "$@" 를 무시해 이 회귀를 전건 초록으로 통과시켰다.
_reset_state
rm -f "$QB_GATE_ARGC"
_fixture_normal | _set_gate 2
_run
_why=""
[ -f "$QB_GATE_ARGC" ] || _why="게이트가 안 불렸다 "
[ "$(cat "$QB_GATE_ARGC" 2>/dev/null)" = "0" ] \
  || _why="${_why}★게이트가 인자 $(cat "$QB_GATE_ARGC" 2>/dev/null)개로 불렸다(기대 0) "
report "⑬ 게이트를 인자 0개로 부른다 (수집 모드)" "$_why"

# ── ⑭ [BL-737] `--install` 이 굽는 유닛이 **지금 이 파일**을 가리킨다 ───────────
#    ★2026-08-13 재배치가 스크립트를 옮기자 서버 유닛은 옛 경로를 가리킨 채 41시간 동안
#      rc=127 로 죽었다. 재는 것은 「유닛이 있나」가 아니라 「무엇을 가리키나」다.
_run_install
_why=""
[ "$RC" -eq 0 ] || _why="종료코드=$RC(기대 0) "
if [ ! -f "$UNIT_SVC" ]; then
  _why="${_why}★watch 유닛이 안 만들어졌다 "
else
  grep -qxF "ExecStart=/bin/bash $TREE_REAL/tools/scripts/soak-watch.sh" "$UNIT_SVC" \
    || _why="${_why}★ExecStart 가 이 파일이 아니다: $(sed -n 's/^ExecStart=//p' "$UNIT_SVC" | head -1) "
  grep -qxF "OnFailure=dev.quantbridge.soak-watch-alarm.service" "$UNIT_SVC" \
    || _why="${_why}★OnFailure 가 없다 — watch 가 죽어도 조용하다 "
fi
report "⑭ --install 의 ExecStart = 현재 스크립트 + OnFailure" "$_why"

# ⑭d 타이머 위상은 **벽시계에 고정**돼야 한다 (강제 발화가 표본 간격을 밀지 못하게)
#    ★`OnUnitActiveSec` 은 마지막 활성화 기준이라, 사람이 한 번 손으로 돌리면 위상이 밀린다.
#      최악 59분(= 29 + 30)이고 C4 한계가 60분이라 여유가 1분뿐인데 systemd 기본
#      `AccuracySec` 이 1분이다 — 2026-08-15 에 실제로 53분까지 벌어졌다.
#    ★**존재 확인이 아니라 집합 동등**으로 잰다 (codex P2). 「`OnCalendar` 가 있나」만 보면
#      `AccuracySec` 이 지워져도, 두 번째 `OnCalendar=*:15/30` 이 **추가**돼도(= 15분마다 발화)
#      통과한다. 발화 스케줄을 정하는 것은 한 줄이 아니라 `[Timer]` 섹션 **전체**다.
_why=""
_tmr="$TMP/xdg/systemd/user/dev.quantbridge.soak-watch.timer"
if [ ! -f "$_tmr" ]; then
  _why="★타이머 유닛이 안 만들어졌다 "
else
  _got="$(sed -n '/^\[Timer\]/,/^\[Install\]/p' "$_tmr" | grep -E '^[A-Za-z]+=' | sort | tr '\n' ' ')"
  _want="AccuracySec=30s OnBootSec=2min OnCalendar=*:00/30 Persistent=true "
  [ "$_got" = "$_want" ] || _why="★[Timer] 키 집합이 다르다: [$_got] (기대 [$_want]) "
fi
report "⑭d 타이머 [Timer] 집합 동등 — 벽시계 고정" "$_why"

_why=""
if [ ! -f "$ALARM_SVC" ]; then
  _why="★실패 알림 유닛이 안 만들어졌다 "
else
  grep -q -- "$TMP/fake.env" "$ALARM_SVC" || _why="${_why}★env 파일 경로가 안 박혔다 "
  # 시크릿 하드코딩 금지 회귀 — 토큰 **값**이 유닛에 들어가면 안 된다(변수 참조만 허용).
  grep -q 'TELEGRAM_BOT_TOKEN=x' "$ALARM_SVC" && _why="${_why}★토큰 값이 유닛에 박혔다 "
  # ★`--fail` 이 없으면 텔레그램 400 에도 curl 이 rc=0 이라 유닛이 `Finished` 로 남는다.
  #   그러면 「알람이 돌았다」와 「알람이 도착했다」가 구분되지 않는다 — 이 회차의 주제 그 자체다.
  grep -q -- '--fail' "$ALARM_SVC" || _why="${_why}★curl 에 --fail 이 없다 (HTTP 오류가 성공으로 보인다) "
  # ★`--show-error` 는 실패 메시지에 URL(경로에 토큰)을 실을 수 있다.
  grep -q -- '--show-error' "$ALARM_SVC" && _why="${_why}★--show-error 가 있다 (토큰 유출 경로) "
  # ★★systemd 는 ExecStart 의 `${VAR}` 를 **자기 환경으로 먼저 확장**하고 미정의는 빈 문자열로
  #   만든다(작은따옴표도 못 막는다). 그러면 URL 이 `…/bot/sendMessage` 가 되어 텔레그램이
  #   404 를 준다 — 2026-08-15 서버에서 실측했다. 리터럴 `$` 는 `$$` 다.
  #   ☹ 이 하네스가 재는 것은 **생성된 텍스트**이지 systemd 의 확장 자체가 아니다 —
  #     그 축은 서버 실증(알람 유닛 강제 발화 → HTTP 200)으로만 닫힌다.
  grep -qF 'chat_id=$${TELEGRAM_CHAT_ID}' "$ALARM_SVC" \
    || _why="${_why}★chat_id 가 \$\$ 이스케이프가 아니다 (systemd 가 빈 값으로 확장한다) "
  grep -qF 'bot$${TELEGRAM_BOT_TOKEN}' "$ALARM_SVC" \
    || _why="${_why}★봇 토큰이 \$\$ 이스케이프가 아니다 "
  grep -qE '[^$]\$\{TELEGRAM' "$ALARM_SVC" \
    && _why="${_why}★단일 \$ 형태의 TELEGRAM 참조가 남아 있다 "
fi
report "⑭b 실패 알림 유닛 · 토큰 미포함 · --fail 있음" "$_why"

# ⑭c 작은따옴표가 든 env 경로는 유닛을 깨뜨린다 → install 이 거부해야 한다
_why=""
_odd="$TMP/it's.env"
printf 'TELEGRAM_BOT_TOKEN=x\nTELEGRAM_CHAT_ID=y\n' > "$_odd"
_out="$(XDG_CONFIG_HOME="$TMP/xdg2" PATH="$TMP/bin:$PATH" QB_SOAK_ENV_FILE="$_odd" \
  bash "$TMP/tree/tools/scripts/soak-watch.sh" --install 2>&1)"; _rc=$?
[ "$_rc" -ne 0 ] || _why="작은따옴표 경로인데 rc=$_rc (기대 ≠0) "
printf '%s' "$_out" | grep -q "작은따옴표" || _why="${_why}진단 문구가 없다 "
rm -rf "$TMP/xdg2" "$_odd"
report "⑭c 작은따옴표가 든 env 경로 → install 거부" "$_why"

# ── ⑮ [BL-737] `--status` 가 낡은 설치본을 red 로 판정한다 ──────────────────────
#    ★음성 대조가 앞에 온다 — 늘 red 인 검사기는 판별력이 0 이다.
_run_status
_why=""
[ "$RC" -eq 0 ] || _why="★정상 설치본인데 rc=$RC (기대 0 — 판별력 없는 검사기) "
printf '%s' "$OUT" | grep -q "설치본 신선도" || _why="${_why}신선도 절이 출력에 없다 "
report "⑮ --status 음성 대조: 갓 설치한 것은 green" "$_why"

# 이번 사고를 그대로 재현한다 — ExecStart 만 옛 경로로 되돌린다.
sed -i.bak "s|^ExecStart=/bin/bash .*|ExecStart=/bin/bash $TMP/tree/scripts/soak-watch.sh|" "$UNIT_SVC"
_run_status
_why=""
[ "$RC" -eq 1 ] || _why="★낡은 ExecStart 인데 rc=$RC (기대 1) "
printf '%s' "$OUT" | grep -q "rc=127" || _why="${_why}rc=127 진단이 없다 "
report "⑮b 옛 경로 ExecStart → red (2026-08-13 사고 재현)" "$_why"
mv "$UNIT_SVC.bak" "$UNIT_SVC"

# 알림 유닛이 사라지면 watch 의 죽음이 다시 안 보인다 — 그것도 red 다.
mv "$ALARM_SVC" "$ALARM_SVC.hidden"
_run_status
_why=""
[ "$RC" -eq 1 ] || _why="★알림 유닛이 없는데 rc=$RC (기대 1) "
printf '%s' "$OUT" | grep -q "실패 알림 유닛이 없다" || _why="${_why}진단 문구가 없다 "
report "⑮c 실패 알림 유닛 부재 → red" "$_why"
mv "$ALARM_SVC.hidden" "$ALARM_SVC"

echo
echo "══════════════════════════════════════════"
printf '  통과 %d · 실패 %d\n' "$PASS" "$FAIL"
echo "══════════════════════════════════════════"
[ "$FAIL" -eq 0 ] || exit 1
echo "✓ 전건 통과  (★실제 텔레그램은 한 번도 쏘지 않았다 — QB_SOAK_NOTIFY_CMD 주입)"
exit 0
