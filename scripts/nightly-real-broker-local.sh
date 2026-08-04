#!/usr/bin/env bash
#
# real_broker E2E 를 **로컬에서** 매일 돌린다 (BL-024 안 B).
#
# 왜 로컬인가 — GitHub Actions 러너에서는 **Bybit 이 지리 차단한다**:
#     403 Forbidden — The Amazon CloudFront distribution is configured to
#                     block access from your country.
#   같은 키가 로컬(한국)에서는 된다(실측: fetch_balance 190,352 USDT / load_markets 3,091).
#   ⇒ 코드로 못 고친다. `nightly-real-broker.yml` 의 `schedule:` 은 그래서 꺼져 있고,
#   이 스크립트가 그 자리를 대신한다. 상세 = issue #540 · `docs/status.md` §다음 스프린트.
#
# 설치:  scripts/nightly-real-broker-local.sh --install     (launchd, 매일 03:00 KST)
# 해제:  scripts/nightly-real-broker-local.sh --uninstall
# 수동:  scripts/nightly-real-broker-local.sh                (지금 한 번 돈다)
# 상태:  scripts/nightly-real-broker-local.sh --status
#
# 종료 코드: 0 = 통과 또는 **의도된 skip** / 1 = 실패 / 2 = 전제 미충족(측정 못 함)
#   ★0 이 「검증됐다」를 뜻하지 않는다 — skip 도 0 이다. 무엇이었는지는 로그 마지막 줄이 말한다.
#     그래서 `last-result` 파일에 **판정 낱말**을 따로 남긴다: PASS / SKIP / FAIL / BLOCKED.

set -uo pipefail

LABEL="dev.quantbridge.nightly-real-broker"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
LOGDIR="$HOME/Library/Logs/quantbridge"
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"

mkdir -p "$LOGDIR"

# ---------------------------------------------------------------- 설치/해제/상태

_install() {
  # ★launchd 는 로그인 셸 환경을 물려받지 않는다. PATH 를 명시하지 않으면
  #   uv / docker / git 을 못 찾아 **조용히 실패**한다.
  local paths="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
  cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${ROOT}/scripts/nightly-real-broker-local.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>3</integer><key>Minute</key><integer>0</integer></dict>
  <key>RunAtLoad</key><false/>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>${paths}</string></dict>
  <key>StandardOutPath</key><string>${LOGDIR}/launchd.out.log</string>
  <key>StandardErrorPath</key><string>${LOGDIR}/launchd.err.log</string>
  <key>WorkingDirectory</key><string>${ROOT}</string>
</dict>
</plist>
PLIST_EOF
  launchctl unload "$PLIST" 2>/dev/null || true
  launchctl load "$PLIST" || { echo "✗ launchctl load 실패"; exit 1; }
  echo "✓ 설치 완료 — 매일 03:00 (로컬 시간대) 실행"
  echo "  plist : $PLIST"
  echo "  로그  : $LOGDIR"
  echo "  ★Mac 이 그 시각에 잠들어 있으면 launchd 가 **깨어난 직후** 한 번 돌린다(누락되지 않는다)."
  exit 0
}

_uninstall() {
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "✓ 해제 완료 (로그는 남긴다: $LOGDIR)"
  exit 0
}

_status() {
  echo "── launchd ──"
  launchctl list 2>/dev/null | grep -F "$LABEL" || echo "  (등록 안 됨)"
  [ -f "$PLIST" ] && echo "  plist 있음: $PLIST" || echo "  plist 없음"
  echo "── 최근 결과 ──"
  if [ -f "$LOGDIR/last-result" ]; then cat "$LOGDIR/last-result"; else echo "  (아직 실행 기록 없음)"; fi
  echo "── 로그 파일 (최근 5개) ──"
  ls -1t "$LOGDIR"/run-*.log 2>/dev/null | head -5 | sed 's/^/  /' || echo "  (없음)"
  exit 0
}

case "${1:-}" in
  --install) _install ;;
  --uninstall) _uninstall ;;
  --status) _status ;;
  "") : ;;
  *) echo "알 수 없는 인자: $1 (--install / --uninstall / --status / 인자없음)" >&2; exit 1 ;;
esac

# ---------------------------------------------------------------- 실행

STAMP="$(date +%Y%m%d-%H%M%S)"
LOG="$LOGDIR/run-${STAMP}.log"

_verdict() {  # _verdict <PASS|SKIP|FAIL|BLOCKED> <한 줄 사유> <exit code>
  printf '%s  %s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$1" "$2" > "$LOGDIR/last-result"
  printf '\n══ 판정: %s — %s ══\n' "$1" "$2" | tee -a "$LOG"
  exit "$3"
}

exec > >(tee -a "$LOG") 2>&1
echo "══ real_broker E2E (로컬) — $(date '+%Y-%m-%d %H:%M:%S %Z') ══"
echo "  repo: $ROOT"

# 1) 메인 체크아웃인가 — 워크트리에서는 컨테이너·앱 DB 를 공유해 다른 벌을 깬다
bash "$ROOT/scripts/assert-main-checkout.sh" "nightly-real-broker-local" \
  || _verdict BLOCKED "메인 체크아웃이 아니다" 2

# 2) env 소싱 — ★`cd backend && set -a; . ./.env.local` 형태 금지.
#    이미 backend 면 `cd` 가 실패해 `set -a` 만 건너뛰고 나머지가 실행돼 대량 거짓 red 가 난다.
[ -f "$ROOT/backend/.env.local" ] || _verdict BLOCKED "backend/.env.local 이 없다" 2
set -a; . "$ROOT/backend/.env.local"; set +a

# 3) 자격증명 — 없으면 「측정 안 했다」이지 「이상 없다」가 아니다
if [ -z "${BYBIT_DEMO_API_KEY_TEST:-}" ] || [ -z "${BYBIT_DEMO_API_SECRET_TEST:-}" ]; then
  _verdict BLOCKED "BYBIT_DEMO_API_KEY_TEST / _SECRET_TEST 가 비어 있다 — 실거래소를 1바이트도 재지 않았다" 2
fi

# 4) 테스트 DB 가 살아 있나 (conftest 의 `_test` DSN 하드가드가 그 뒤를 본다)
docker exec quantbridge-db pg_isready -U quantbridge >/dev/null 2>&1 \
  || _verdict BLOCKED "quantbridge-db 컨테이너가 응답하지 않는다 (make up-isolated 필요)" 2

# 5) ★소크 충돌 가드 — 같은 Bybit 계정(uid 558689281)을 쓴다.
#    소크가 포지션을 들고 있으면 이 스위트의 「진입 전 flat」 단언이 **소크 때문에** 깨진다.
#    그건 결함이 아니라 **측정 불가**다 — 혼란스러운 residual 대신 명시적으로 끊는다.
ACTIVE="$(docker exec quantbridge-db psql -U quantbridge -d quantbridge -Atc \
  "SELECT count(*) FROM trading.live_signal_sessions WHERE is_active = true;" 2>/dev/null || echo "?")"
if [ "$ACTIVE" = "?" ]; then
  _verdict BLOCKED "활성 라이브 세션 수를 읽지 못했다 — 판정 불가를 「이상 없음」으로 접지 않는다" 2
fi
if [ "$ACTIVE" != "0" ]; then
  _verdict SKIP "소크가 돌고 있다 (활성 세션 ${ACTIVE}개) — 같은 Bybit 계정이라 포지션을 공유한다" 0
fi
echo "  ✓ 전제: 메인 체크아웃 · 자격증명 있음 · DB 응답 · 활성 세션 0"

# 6) 실행 — ★`2>&1` 은 파이프 **앞**에. `tee` 는 stdout 만 받는다(하네스의 RESIDUAL 은 stderr 다).
#    ★파이프로 감싸도 exit code 를 잃지 않게 PIPESTATUS 로 받는다.
cd "$ROOT/backend"
uv run pytest tests/real_broker/ \
  --run-real-broker \
  -v --tb=short \
  --timeout=600 --timeout-method=signal 2>&1
RC=${PIPESTATUS[0]}
echo "  pytest exit=$RC"

# 7) 지리 차단은 「고장」이 아니라 「측정 불가」다 — 갈라서 기록한다
if [ "$RC" -ne 0 ] && grep -qi "block access from your country\|CloudFront distribution is configured" "$LOG"; then
  _verdict BLOCKED "Bybit 이 이 위치를 차단했다 (VPN/네트워크 확인) — 고장이 아니라 측정 불가" 2
fi

[ "$RC" -eq 0 ] && _verdict PASS "real_broker 스위트 통과" 0
_verdict FAIL "real_broker 스위트 실패 — 로그를 봐라: $LOG" 1
