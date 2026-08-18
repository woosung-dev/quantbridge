#!/usr/bin/env bash
# api-service 인스톨러 하네스 — [BL-805]. 전건 통과 = 종료 코드 0.
#
# 왜 필요한가
#   이 스크립트의 고장 모드는 **조용하다.** 유닛을 잘못 구우면 `systemctl` 상으로는 계속
#   「enabled」로 보이고, 실제로는 rc=127 로 죽는다 — [BL-744] 가 서버에서 정확히 그 모양이었고
#   41 시간 동안 아무도 몰랐다([BL-737]). 그래서 재는 것은 「설치가 됐나」가 아니라
#   **`--status` 가 낡은 설치본을 실제로 red 로 만드는가**다.
#   ★그런데 **「늘 red 인 신선도 검사」는 양성 케이스를 전건 통과한다.** 그래서
#     **음성 대조(갓 설치 → rc=0)와 양성 대조(경로를 망가뜨림 → rc=1)를 반드시 짝으로 둔다.**
#     한쪽만 있으면 판별력이 0 이다.
#
# ★판정 로직을 heredoc 에 베끼지 않는다. **진짜 스크립트**를 겨누고 `systemctl`/`loginctl` 만
#   가짜 바이너리로 가로챈다.
# ★`QB_API_UVICORN` 주입 seam 을 쓴다 — 실제 `apps/api/.venv` 유무에 의존하면 이 하네스는
#   머신마다 다른 답을 낸다(환경 의존 검사는 이 레포가 이미 밟은 함정이다).
# ★종료 코드가 판정이므로 **파이프 없이** 읽는다 (`| tail` 이 $? 를 가린다 — 실측 사고 이력).
#
# 사용법: tools/scripts/api-service-test.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
TARGET="$ROOT/tools/scripts/api-service.sh"
[ -f "$TARGET" ] || {
  echo "✗ 대상 스크립트가 없다: $TARGET" >&2
  exit 1
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0
OUT=""
RC=0

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
mkdir -p "$TMP/bin" "$TMP/xdg"

# 가짜 systemctl — 설치 경로가 리눅스 전용 분기를 타게 한다.
# ★2026-08-19: `--status` 에 **활성 상태 축**(is-active/is-failed)과 **drop-in 합성 축**
#   (show -p ExecStart)이 생겨 「전부 exit 0」 스텁으로는 그 둘을 겨눌 수 없다. 하위 명령별로
#   상태를 흉내 낸다.
#   QB_FAKE_SYSTEMCTL_FAIL=1 : 모든 하위 명령 실패 (enable 실패 재현)
#   QB_FAKE_FAIL_SUB=<하위>  : **그 하위 명령만** 실패. ★표적 변이가 찾아낸 구멍 때문에 생겼다 —
#                              「전부 실패」로는 `_uninstall` 의 rc 축 둘(disable · daemon-reload)이
#                              서로를 가려 한쪽을 지워도 케이스가 초록이었다(2026-08-19 M4 실측).
#   QB_FAKE_UNIT_STATE       : active(기본) | failed | inactive
#   QB_FAKE_EXECSTART        : `show -p ExecStart --value` 가 낼 값. 비어 있으면 **유닛 파일에서
#                              읽는다** — drop-in 이 없는 실제 systemd 와 같은 답이 된다.
#   QB_FAKE_SHOW_EMPTY=1     : show 가 아무것도 안 찍는다 (systemd 가 유닛을 안 읽은 상태)
cat > "$TMP/bin/systemctl" << 'EOF'
#!/usr/bin/env bash
if [ "${QB_FAKE_SYSTEMCTL_FAIL:-0}" = "1" ]; then exit 1; fi

sub=""
for a in "$@"; do
  case "$a" in
    --*) continue ;;
    *)
      sub="$a"
      break
      ;;
  esac
done

if [ -n "${QB_FAKE_FAIL_SUB:-}" ] && [ "$sub" = "$QB_FAKE_FAIL_SUB" ]; then exit 1; fi

state="${QB_FAKE_UNIT_STATE:-active}"
unit_file="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/quantbridge-api.service"

case "$sub" in
  is-active)
    printf '%s\n' "$state"
    [ "$state" = "active" ] && exit 0
    exit 3
    ;;
  is-failed)
    printf '%s\n' "$state"
    [ "$state" = "failed" ] && exit 0
    exit 1
    ;;
  show)
    [ "${QB_FAKE_SHOW_EMPTY:-0}" = "1" ] && exit 0
    if [ -n "${QB_FAKE_EXECSTART:-}" ]; then
      printf '%s\n' "$QB_FAKE_EXECSTART"
      exit 0
    fi
    if [ -f "$unit_file" ]; then
      line="$(sed -n 's|^ExecStart=||p' "$unit_file" | head -1)"
      # systemd 실물 형식을 흉내낸다: `{ path=… ; argv[]=… ; ignore_errors=no }`
      [ -n "$line" ] \
        && printf '{ path=%s ; argv[]=%s ; ignore_errors=no }\n' "${line%% *}" "$line"
    fi
    exit 0
    ;;
  status)
    printf 'quantbridge-api.service - QuantBridge API\n   Active: %s\n' "$state"
    [ "$state" = "active" ] && exit 0
    exit 3
    ;;
esac
exit 0
EOF

# 가짜 loginctl — QB_FAKE_LINGER 로 현재 상태를, QB_FAKE_LINGER_FAIL 로 enable 실패를 흉내낸다.
cat > "$TMP/bin/loginctl" << 'EOF'
#!/usr/bin/env bash
case "${1:-}" in
  show-user) printf '%s\n' "${QB_FAKE_LINGER:-no}" ;;
  enable-linger) [ "${QB_FAKE_LINGER_FAIL:-0}" = "1" ] && exit 1; exit 0 ;;
esac
exit 0
EOF

# 가짜 uvicorn — 주입 seam 의 대상. 실제 venv 를 건드리지 않는다.
cat > "$TMP/fake-uvicorn" << 'EOF'
#!/usr/bin/env bash
exit 0
EOF
# 「존재하지만 다른 파일」 갈래(신선도 3번째 분기)용
cat > "$TMP/other-uvicorn" << 'EOF'
#!/usr/bin/env bash
exit 0
EOF

# ★shebang 축(2026-08-19)용 wrapper 3종 — **파일은 셋 다 실재·실행 가능**하고 첫 줄만 다르다.
#   이것이 `[ -x ]` 로는 셋을 구분할 수 없다는 사실 자체다.
printf '#!/bin/sh\nexit 0\n' > "$TMP/uvicorn-shebang-ok"
printf '#!%s/gone/bin/python3\nexit 0\n' "$TMP" > "$TMP/uvicorn-shebang-dead"
printf 'not-a-script\n' > "$TMP/uvicorn-no-shebang"

chmod +x "$TMP/bin/systemctl" "$TMP/bin/loginctl" "$TMP/fake-uvicorn" "$TMP/other-uvicorn" \
  "$TMP/uvicorn-shebang-ok" "$TMP/uvicorn-shebang-dead" "$TMP/uvicorn-no-shebang"

UVI="$TMP/fake-uvicorn"
XDG="$TMP/xdg"
UNIT="$XDG/systemd/user/quantbridge-api.service"

_run_as() { # _run_as <uvicorn 경로> <인자...>  — 주입 seam 을 갈아끼우고 돈다
  local u="$1"
  shift
  OUT="$(PATH="$TMP/bin:$PATH" XDG_CONFIG_HOME="$XDG" QB_API_UVICORN="$u" \
    bash "$TARGET" "$@" 2>&1)"
  RC=$?
}

_run() { # _run <인자...>  — 스텁이 걸린 PATH 로 대상 스크립트를 돈다
  _run_as "$UVI" "$@"
}

echo "══ api-service 하네스 ══"
echo "  대상: $TARGET"
echo

# ── ① 인자 방어 ────────────────────────────────────────────────────────────────
_run
_why=""
[ "$RC" -eq 1 ] || _why="인자 없음인데 rc=$RC (기대 1) "
printf '%s' "$OUT" | grep -q '서브커맨드가 없다' || _why="${_why}진단 문구가 없다 "
report "① 서브커맨드 없음 → rc=1" "$_why"

_run --bogus
_why=""
[ "$RC" -eq 1 ] || _why="알 수 없는 인자인데 rc=$RC (기대 1) "
report "② 알 수 없는 인자 → rc=1" "$_why"

_run --help
_why=""
[ "$RC" -eq 0 ] || _why="rc=$RC (기대 0) "
printf '%s' "$OUT" | grep -q 'BL-805' || _why="${_why}헤더가 안 나온다 "
printf '%s' "$OUT" | grep -q -- '--install' || _why="${_why}사용법에 --install 이 없다 "
report "③ --help → rc=0 · 헤더 출력" "$_why"

# ── ④ systemctl 이 없으면 명시적으로 거부한다 (macOS) ───────────────────────────
# ★PATH 에서 systemctl 만 빼는 것은 불가능하므로, 필요한 도구만 심볼릭한 **최소 PATH** 를 만든다.
#   ★그 PATH 에 systemctl 이 정말 없는지를 **먼저 단언**한다 — 없다고 가정한 채 rc=1 을 보면
#     다른 이유로 죽은 것을 「거부했다」로 오독한다.
mkdir -p "$TMP/nosys"
for _t in bash env dirname sed awk head grep mkdir rm id cat chmod; do
  _src="$(command -v "$_t" 2> /dev/null)" || continue
  ln -sf "$_src" "$TMP/nosys/$_t"
done
_why=""
if PATH="$TMP/nosys" command -v systemctl > /dev/null 2>&1; then
  _why="★최소 PATH 에 systemctl 이 남아 있다 — 이 케이스는 무증거다 "
fi
# ★**환경 온전성 대조** — 최소 PATH 로도 스크립트가 정상 동작하는지 먼저 확인한다.
#   이것이 없으면 「도구가 없어 rc≠0」을 「systemctl 을 거부했다」로 오독한다.
#   초판이 정확히 그랬다: `bash` 가 목록에 빠져 rc=127(command not found)이 나왔다.
OUT="$(PATH="$TMP/nosys" XDG_CONFIG_HOME="$XDG" QB_API_UVICORN="$UVI" \
  bash "$TARGET" --help 2>&1)"
RC=$?
[ "$RC" -eq 0 ] || _why="${_why}★최소 PATH 로 --help 조차 못 돈다 (rc=$RC) — 이 케이스는 무증거다 "
report "④a 환경 온전성: 최소 PATH 로도 --help 는 green" "$_why"

_why=""
RC=0
OUT="$(PATH="$TMP/nosys" XDG_CONFIG_HOME="$XDG" QB_API_UVICORN="$UVI" \
  bash "$TARGET" --install 2>&1)"
RC=$?
[ "$RC" -eq 1 ] || _why="${_why}systemctl 이 없는데 rc=$RC (기대 1) "
printf '%s' "$OUT" | grep -q '리눅스 전용' || _why="${_why}「리눅스 전용」 진단이 없다 "
report "④ systemctl 부재 → 명시적 거부 (rc=1)" "$_why"

# ── ⑤ 유닛이 없으면 --status 는 red ────────────────────────────────────────────
rm -rf "$XDG"
_run --status
_why=""
[ "$RC" -eq 1 ] || _why="유닛이 없는데 rc=$RC (기대 1) "
printf '%s' "$OUT" | grep -q '설치된 유닛이 없다' || _why="${_why}진단 문구가 없다 "
report "⑤ 유닛 부재 → --status rc=1" "$_why"

# ── ⑥ uvicorn 이 없으면 설치를 거부한다 (좀비 유닛 방지) ────────────────────────
OUT="$(PATH="$TMP/bin:$PATH" XDG_CONFIG_HOME="$XDG" QB_API_UVICORN="$TMP/gone/uvicorn" \
  bash "$TARGET" --install 2>&1)"
RC=$?
_why=""
[ "$RC" -eq 1 ] || _why="uvicorn 이 없는데 rc=$RC (기대 1) "
printf '%s' "$OUT" | grep -q 'uvicorn 이 없거나' || _why="${_why}진단 문구가 없다 "
[ -f "$UNIT" ] && _why="${_why}★거부했다면서 유닛을 만들었다 "
report "⑥ uvicorn 부재 → 설치 거부 · 유닛 미생성" "$_why"

# ── ⑦ --install 이 장기 실행 유닛 형태로 굽는다 ────────────────────────────────
_run --install
_why=""
[ "$RC" -eq 0 ] || _why="rc=$RC (기대 0) "
[ -f "$UNIT" ] || _why="${_why}유닛 파일이 없다 ($UNIT) "
grep -q '^Type=simple$' "$UNIT" 2> /dev/null || _why="${_why}Type=simple 이 아니다 "
grep -q '^Restart=always$' "$UNIT" 2> /dev/null || _why="${_why}Restart=always 가 없다 "
grep -q '^RestartSec=' "$UNIT" 2> /dev/null || _why="${_why}RestartSec 이 없다 "
grep -q '^WantedBy=default.target$' "$UNIT" 2> /dev/null \
  || _why="${_why}WantedBy=default.target 이 없다 "
# ★timer 형제(oneshot)를 베끼지 않았는지 음성으로도 잰다.
grep -q '^Type=oneshot' "$UNIT" 2> /dev/null && _why="${_why}★oneshot 을 베꼈다 "
[ -f "$XDG/systemd/user/quantbridge-api.timer" ] && _why="${_why}★timer 를 만들었다 "
report "⑦ --install: Type=simple · Restart=always · WantedBy=default.target" "$_why"

# ── ⑧ 유닛 내용이 서버 실측값과 맞는가 ─────────────────────────────────────────
_why=""
grep -qF "ExecStart=$UVI src.main:app --no-server-header --host 127.0.0.1 --port 8100" "$UNIT" 2> /dev/null \
  || _why="ExecStart 가 서버 실측 형태가 아니다 "
grep -qF "WorkingDirectory=$ROOT/apps/api" "$UNIT" 2> /dev/null \
  || _why="${_why}WorkingDirectory 가 다르다 "
grep -qF "Environment=PROMETHEUS_MULTIPROC_DIR=$ROOT/apps/api/.metrics" "$UNIT" 2> /dev/null \
  || _why="${_why}PROMETHEUS_MULTIPROC_DIR 이 없다 "
grep -q '^Environment=QB_METRICS_ROLE=api$' "$UNIT" 2> /dev/null \
  || _why="${_why}QB_METRICS_ROLE 이 없다 "
report "⑧ 유닛 내용 = 서버 실측값 (ExecStart · WorkingDirectory · Environment)" "$_why"

# ── ⑨ 유닛 이름이 `quantbridge-api.service` 다 (dev.quantbridge.* 예외) ─────────
_why=""
[ -f "$XDG/systemd/user/quantbridge-api.service" ] || _why="이름이 quantbridge-api.service 가 아니다 "
[ -f "$XDG/systemd/user/dev.quantbridge.api.service" ] \
  && _why="${_why}★형제 규칙 이름으로 만들었다 — 서버 실물과 달라진다 "
report "⑨ 유닛 이름 = quantbridge-api.service (서버 실물)" "$_why"

# ── ⑩ 음성 대조: 갓 설치한 것은 green ──────────────────────────────────────────
# ★이것이 이 하네스의 존재 이유의 절반이다. 여기가 red 면 아래 양성 대조는 아무 뜻이 없다
#   (늘 red 인 검사기도 양성은 전건 통과한다).
_run --status
_why=""
[ "$RC" -eq 0 ] || _why="★갓 설치했는데 rc=$RC (기대 0) "
printf '%s' "$OUT" | grep -q "✓ ExecStart = $UVI" || _why="${_why}green 진단이 없다 "
report "⑩ 음성 대조: 갓 설치 → --status rc=0" "$_why"

# ── ⑪ 양성 대조 A: ExecStart 가 없는 경로 → red + rc=127 진단 ──────────────────
sed -i.bak "s|^ExecStart=.*|ExecStart=$TMP/gone/bin/uvicorn src.main:app|" "$UNIT"
_run --status
_why=""
[ "$RC" -eq 1 ] || _why="★없는 경로인데 rc=$RC (기대 1) "
printf '%s' "$OUT" | grep -q 'rc=127' || _why="${_why}rc=127 진단이 없다 "
report "⑪ 양성 대조 A: 없는 ExecStart → rc=1 + rc=127 진단" "$_why"
mv "$UNIT.bak" "$UNIT"

# ── ⑫ 양성 대조 B: 존재하지만 다른 venv → red + 설치본/현재본 병기 ─────────────
# ★재배치([ADR-029]) 재현 — 옛 체크아웃의 uvicorn 은 **실재**하므로 ⑪ 의 분기로는 안 잡힌다.
sed -i.bak "s|^ExecStart=.*|ExecStart=$TMP/other-uvicorn src.main:app|" "$UNIT"
_run --status
_why=""
[ "$RC" -eq 1 ] || _why="★다른 venv 인데 rc=$RC (기대 1) "
printf '%s' "$OUT" | grep -q '재설치해라' || _why="${_why}재설치 지시가 없다 "
printf '%s' "$OUT" | grep -qF "설치본: $TMP/other-uvicorn" || _why="${_why}설치본 병기가 없다 "
printf '%s' "$OUT" | grep -qF "현재본: $UVI" || _why="${_why}현재본 병기가 없다 "
report "⑫ 양성 대조 B: 다른 venv(실재) → rc=1 + 설치본/현재본 병기" "$_why"
mv "$UNIT.bak" "$UNIT"

# ── ⑬ 복원 확인 — ⑪⑫ 가 유닛을 되돌려 놨는가 (다음 케이스의 전제) ─────────────
_run --status
_why=""
[ "$RC" -eq 0 ] || _why="★변이 복원 후인데 rc=$RC (기대 0) — 앞 케이스가 유닛을 망가뜨린 채 뒀다 "
report "⑬ 변이 복원 확인: --status 가 다시 green" "$_why"

# ── ⑭ lingering 을 못 켜도 설치는 유지한다 (경고만) ────────────────────────────
rm -rf "$XDG"
OUT="$(PATH="$TMP/bin:$PATH" XDG_CONFIG_HOME="$XDG" QB_API_UVICORN="$UVI" \
  QB_FAKE_LINGER=no QB_FAKE_LINGER_FAIL=1 bash "$TARGET" --install 2>&1)"
RC=$?
_why=""
[ "$RC" -eq 0 ] || _why="★lingering 실패로 설치가 죽었다 rc=$RC (기대 0) "
[ -f "$UNIT" ] || _why="${_why}유닛이 없다 "
printf '%s' "$OUT" | grep -q 'lingering' || _why="${_why}경고가 없다 "
report "⑭ lingering 실패 → 경고만 · 설치 유지" "$_why"

# ── ⑮ systemctl enable 이 실패하면 설치는 실패한다 ─────────────────────────────
rm -rf "$XDG"
OUT="$(PATH="$TMP/bin:$PATH" XDG_CONFIG_HOME="$XDG" QB_API_UVICORN="$UVI" \
  QB_FAKE_SYSTEMCTL_FAIL=1 bash "$TARGET" --install 2>&1)"
RC=$?
_why=""
[ "$RC" -eq 1 ] || _why="★enable 이 실패했는데 rc=$RC (기대 1) "
report "⑮ systemctl 실패 → 설치 실패 (fail-closed)" "$_why"

# ── ⑯ --uninstall 이 유닛을 지운다 (⑯ = ㉗ 의 음성 대조) ───────────────────────
rm -rf "$XDG"
_run --install
_run --uninstall
_why=""
[ "$RC" -eq 0 ] || _why="rc=$RC (기대 0) "
[ -f "$UNIT" ] && _why="${_why}★유닛이 남아 있다 "
printf '%s' "$OUT" | grep -q '✓ 해제 완료' || _why="${_why}완료 문구가 없다 "
report "⑯ 음성 대조: 정상 --uninstall → 유닛 삭제 · rc=0" "$_why"

# ═══ 2026-08-19 적대 리뷰 4건 수용분 (⑰~㉘) ═══════════════════════════════════
# ★네 축 전부 **음성 대조(정상 → green)와 양성 대조(변조 → red)를 짝으로** 둔다.
#   한쪽만 있으면 판별력이 0 이라는 것이 이 하네스 머리말의 전제다.

# ── ⑰ shebang 음성 대조: 인터프리터가 실재하면 green ───────────────────────────
rm -rf "$XDG"
_run_as "$TMP/uvicorn-shebang-ok" --install
_run_as "$TMP/uvicorn-shebang-ok" --status
_why=""
[ "$RC" -eq 0 ] || _why="★shebang 이 멀쩡한데 rc=$RC (기대 0) "
printf '%s' "$OUT" | grep -q '✓ shebang 인터프리터 = /bin/sh' || _why="${_why}green 진단이 없다 "
report "⑰ 음성 대조: shebang 인터프리터 실재 → --status rc=0" "$_why"

# ── ⑱ shebang 양성 대조: 죽은 인터프리터 → red ─────────────────────────────────
# ★재배치된 venv 재현 — wrapper 파일은 **실재·실행 가능**하고 경로 축도 초록이다.
#   그래서 이 red 를 만들 수 있는 것은 shebang 축 하나뿐이다.
sed -i.bak "s|^ExecStart=.*|ExecStart=$TMP/uvicorn-shebang-dead src.main:app|" "$UNIT"
_run_as "$TMP/uvicorn-shebang-dead" --status
_why=""
[ "$RC" -eq 1 ] || _why="★shebang 이 죽었는데 rc=$RC (기대 1) "
printf '%s' "$OUT" | grep -q '203/EXEC' || _why="${_why}203/EXEC 진단이 없다 "
printf '%s' "$OUT" | grep -qF "shebang : $TMP/gone/bin/python3" || _why="${_why}shebang 경로 병기가 없다 "
# ★경로 축은 초록이어야 한다 — 아니면 이 케이스는 shebang 축을 안 겨눈 것이다.
printf '%s' "$OUT" | grep -qF "✓ ExecStart = $TMP/uvicorn-shebang-dead" \
  || _why="${_why}★경로 축이 초록이 아니다 — 이 red 는 shebang 축의 것이 아니다 "
report "⑱ 양성 대조: 죽은 shebang → rc=1 + 203/EXEC (경로 축은 초록)" "$_why"
mv "$UNIT.bak" "$UNIT"

# ── ⑲ shebang 판정 불가 2갈래를 **인쇄**한다 (조용히 통과 금지) ────────────────
rm -rf "$XDG"
_run_as "$TMP/fake-uvicorn" --install
_run_as "$TMP/fake-uvicorn" --status
_why=""
[ "$RC" -eq 0 ] || _why="rc=$RC (기대 0) "
printf '%s' "$OUT" | grep -q 'env\` 를 경유' || _why="${_why}env 경유 판정 불가를 안 알린다 "
rm -rf "$XDG"
_run_as "$TMP/uvicorn-no-shebang" --install
_run_as "$TMP/uvicorn-no-shebang" --status
[ "$RC" -eq 0 ] || _why="${_why}shebang 없는 파일인데 rc=$RC (기대 0) "
printf '%s' "$OUT" | grep -q 'shebang 이 없다' || _why="${_why}shebang 부재 판정 불가를 안 알린다 "
report "⑲ shebang 판정 불가(env · 부재)는 인쇄한다 — 조용히 통과 아님" "$_why"

# ── ⑳ 활성 음성 대조: active 면 green ──────────────────────────────────────────
rm -rf "$XDG"
_run --install
OUT="$(PATH="$TMP/bin:$PATH" XDG_CONFIG_HOME="$XDG" QB_API_UVICORN="$UVI" \
  QB_FAKE_UNIT_STATE=active bash "$TARGET" --status 2>&1)"
RC=$?
_why=""
[ "$RC" -eq 0 ] || _why="★active 인데 rc=$RC (기대 0) "
printf '%s' "$OUT" | grep -q '✓ active' || _why="${_why}green 진단이 없다 "
report "⑳ 음성 대조: 유닛 active → --status rc=0" "$_why"

# ── ㉑ 활성 양성 대조: failed 면 red (경로 축이 전부 초록이어도) ────────────────
OUT="$(PATH="$TMP/bin:$PATH" XDG_CONFIG_HOME="$XDG" QB_API_UVICORN="$UVI" \
  QB_FAKE_UNIT_STATE=failed bash "$TARGET" --status 2>&1)"
RC=$?
_why=""
[ "$RC" -eq 1 ] || _why="★유닛이 failed 인데 rc=$RC (기대 1) "
printf '%s' "$OUT" | grep -q '유닛이 failed 다' || _why="${_why}failed 진단이 없다 "
printf '%s' "$OUT" | grep -q 'journalctl' || _why="${_why}다음 행동 지시가 없다 "
printf '%s' "$OUT" | grep -qF "✓ ExecStart = $UVI" \
  || _why="${_why}★경로 축이 초록이 아니다 — 이 red 는 활성 축의 것이 아니다 "
report "㉑ 양성 대조: 유닛 failed → rc=1 (경로 축은 초록)" "$_why"

# ── ㉒ inactive 는 failed 와 **다른 상태**로 인쇄한다 ───────────────────────────
OUT="$(PATH="$TMP/bin:$PATH" XDG_CONFIG_HOME="$XDG" QB_API_UVICORN="$UVI" \
  QB_FAKE_UNIT_STATE=inactive bash "$TARGET" --status 2>&1)"
RC=$?
_why=""
[ "$RC" -eq 1 ] || _why="★활성이 아닌데 rc=$RC (기대 1) "
printf '%s' "$OUT" | grep -q '활성이 아니다 (inactive)' || _why="${_why}inactive 문구가 없다 "
printf '%s' "$OUT" | grep -q '유닛이 failed 다' && _why="${_why}★inactive 를 failed 로 인쇄했다 "
report "㉒ inactive ≠ failed — 문구를 구분해 인쇄" "$_why"

# ── ㉓ drop-in 음성 대조: 합성값 = 파일값이면 green ─────────────────────────────
_run --status
_why=""
[ "$RC" -eq 0 ] || _why="★drop-in 이 없는데 rc=$RC (기대 0) "
printf '%s' "$OUT" | grep -q 'drop-in 없음' || _why="${_why}drop-in 부재를 안 알린다 "
printf '%s' "$OUT" | grep -qF "✓ 합성 후 ExecStart = $UVI" || _why="${_why}합성 green 진단이 없다 "
report "㉓ 음성 대조: drop-in 없음 · 합성값 일치 → rc=0" "$_why"

# ── ㉔ drop-in 양성 대조: 합성값만 옛 체크아웃 → red ────────────────────────────
# ★**원본 유닛 파일은 손대지 않는다.** 파일 축은 초록인 채 합성 축만 red 여야 한다 —
#   그것이 이 finding(원본만 읽으면 drop-in 재지정을 못 본다)의 본체다.
OUT="$(PATH="$TMP/bin:$PATH" XDG_CONFIG_HOME="$XDG" QB_API_UVICORN="$UVI" \
  QB_FAKE_EXECSTART="{ path=$TMP/OLD-CHECKOUT/uvicorn ; argv[]=$TMP/OLD-CHECKOUT/uvicorn src.main:app ; ignore_errors=no }" \
  bash "$TARGET" --status 2>&1)"
RC=$?
_why=""
[ "$RC" -eq 1 ] || _why="★drop-in 이 ExecStart 를 재지정했는데 rc=$RC (기대 1) "
printf '%s' "$OUT" | grep -q '합성 후 ExecStart 가 이 트리의 venv 가 아니다' \
  || _why="${_why}합성 불일치 진단이 없다 "
printf '%s' "$OUT" | grep -qF "합성본: $TMP/OLD-CHECKOUT/uvicorn" || _why="${_why}합성본 병기가 없다 "
printf '%s' "$OUT" | grep -qF "✓ ExecStart = $UVI" \
  || _why="${_why}★파일 축이 초록이 아니다 — 이 red 는 합성 축의 것이 아니다 "
report "㉔ 양성 대조: drop-in 이 ExecStart 재지정 → rc=1 (파일 축은 초록)" "$_why"

# ── ㉕ drop-in 파일의 **존재 자체**를 인쇄한다 ──────────────────────────────────
mkdir -p "$XDG/systemd/user/quantbridge-api.service.d"
printf '[Service]\nExecStart=\nExecStart=%s/OLD/uvicorn src.main:app\n' "$TMP" \
  > "$XDG/systemd/user/quantbridge-api.service.d/override.conf"
_run --status
_why=""
printf '%s' "$OUT" | grep -q 'drop-in: override.conf' || _why="★drop-in 파일명을 안 알린다 "
report "㉕ drop-in .conf 존재를 인쇄한다" "$_why"
rm -rf "$XDG/systemd/user/quantbridge-api.service.d"

# ── ㉖ 합성 판정 불가 2갈래를 인쇄한다 (미확장 지정자 · 빈 합성값) ──────────────
# ★`show -p ExecStart` 는 **확장 _전_** 문자열이다 (`docs/lessons.md` 2026-08-15 반증).
#   `${VAR}` 가 남아 있으면 문자열 대조는 무의미하므로 red 가 아니라 **판정 불가**여야 한다.
OUT="$(PATH="$TMP/bin:$PATH" XDG_CONFIG_HOME="$XDG" QB_API_UVICORN="$UVI" \
  QB_FAKE_EXECSTART='{ path=${QB_VENV}/bin/uvicorn ; ignore_errors=no }' \
  bash "$TARGET" --status 2>&1)"
RC=$?
_why=""
[ "$RC" -eq 0 ] || _why="미확장 지정자는 판정 불가여야 하는데 rc=$RC (기대 0) "
printf '%s' "$OUT" | grep -q '미확장 지정자' || _why="${_why}판정 불가 사유를 안 알린다 "
OUT="$(PATH="$TMP/bin:$PATH" XDG_CONFIG_HOME="$XDG" QB_API_UVICORN="$UVI" \
  QB_FAKE_SHOW_EMPTY=1 bash "$TARGET" --status 2>&1)"
RC=$?
[ "$RC" -eq 0 ] || _why="${_why}빈 합성값은 판정 불가여야 하는데 rc=$RC (기대 0) "
printf '%s' "$OUT" | grep -q '합성 ExecStart 가 비었다' || _why="${_why}빈 합성값을 안 알린다 "
report "㉖ 합성 판정 불가(미확장 지정자 · 빈 값)는 인쇄한다 — 조용한 red 아님" "$_why"

# ── ㉗ uninstall 양성 대조: disable 실패를 삼키지 않는다 ────────────────────────
# ★Restart=always 라 stop 이 실패하면 API 는 계속 도는데 유닛 파일만 사라진다.
#   그것을 「✓ 해제 완료 · rc=0」으로 인쇄하는 것이 이 finding 의 본체다.
# ★**하위 명령 하나씩만** 실패시킨다. 「전부 실패」로 재면 두 rc 축이 서로를 가려
#   한쪽을 지워도 케이스가 초록이다 — 2026-08-19 표적 변이 M4 가 그 구멍을 실제로 찾아냈다.
rm -rf "$XDG"
_run --install
OUT="$(PATH="$TMP/bin:$PATH" XDG_CONFIG_HOME="$XDG" QB_API_UVICORN="$UVI" \
  QB_FAKE_FAIL_SUB=disable bash "$TARGET" --uninstall 2>&1)"
RC=$?
_why=""
[ "$RC" -eq 1 ] || _why="★disable 이 실패했는데 rc=$RC (기대 1) "
printf '%s' "$OUT" | grep -q 'disable --now 실패' || _why="${_why}무엇이 실패했는지 안 알린다 "
printf '%s' "$OUT" | grep -q 'Restart=always' || _why="${_why}계속 돌 수 있다는 경고가 없다 "
printf '%s' "$OUT" | grep -q '✓ 해제 완료' && _why="${_why}★실패해 놓고 완료라고 인쇄했다 "
report "㉗ 양성 대조: disable --now 만 실패 → rc=1 · 완료 문구 없음" "$_why"

# ── ㉘ uninstall 양성 대조 B: daemon-reload 실패도 삼키지 않는다 ────────────────
rm -rf "$XDG"
_run --install
OUT="$(PATH="$TMP/bin:$PATH" XDG_CONFIG_HOME="$XDG" QB_API_UVICORN="$UVI" \
  QB_FAKE_FAIL_SUB=daemon-reload bash "$TARGET" --uninstall 2>&1)"
RC=$?
_why=""
[ "$RC" -eq 1 ] || _why="★daemon-reload 가 실패했는데 rc=$RC (기대 1) "
printf '%s' "$OUT" | grep -q 'daemon-reload 실패' || _why="${_why}무엇이 실패했는지 안 알린다 "
printf '%s' "$OUT" | grep -q 'disable --now 실패' && _why="${_why}★disable 은 성공했는데 실패라 인쇄했다 "
printf '%s' "$OUT" | grep -q '✓ 해제 완료' && _why="${_why}★실패해 놓고 완료라고 인쇄했다 "
report "㉘ 양성 대조: daemon-reload 만 실패 → rc=1 · 완료 문구 없음" "$_why"

# ── ㉙ 죽은 shebang wrapper 로는 설치를 거부한다 (좀비 유닛 방지) ───────────────
rm -rf "$XDG"
_run_as "$TMP/uvicorn-shebang-dead" --install
_why=""
[ "$RC" -eq 1 ] || _why="★shebang 이 죽었는데 rc=$RC (기대 1) "
printf '%s' "$OUT" | grep -q '203/EXEC' || _why="${_why}203/EXEC 진단이 없다 "
[ -f "$UNIT" ] && _why="${_why}★거부했다면서 유닛을 만들었다 "
report "㉙ 죽은 shebang → --install 거부 · 유닛 미생성" "$_why"

echo
echo "══════════════════════════════════════════"
printf '  통과 %d · 실패 %d\n' "$PASS" "$FAIL"
echo "══════════════════════════════════════════"
[ "$FAIL" -eq 0 ] || exit 1
echo "✓ 전건 통과  (★실제 systemd 는 한 번도 안 건드렸다 — systemctl/loginctl 스텁 + XDG 격리)"
exit 0
