#!/usr/bin/env bash
# ledger-vitals.sh — 원장 활력 3축 (슬림 복귀 1호, 근거 사고: BL-643 「다음 행동」 중복 · RESOLVED 13건 역류)
# ① status.md 살아 있는 `다음 행동 =` ≤1 (파일 전체 — 취소선·인라인코드·코드펜스 제외)
# ② status.md ⓪ 표 데이터 행 ≥3
# ③ backlog.md 에 상태줄 RESOLVED 섹션 0건 (RESOLVED 는 backlog-resolved.md 소관)
# rc: 0=통과 / 1=위반 / 3=대상 파일 부재(판정 포기 — 초록 아님). bash 3.2 호환.
set -u

ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
STATUS="$ROOT/docs/status.md"
BACKLOG="$ROOT/docs/backlog.md"
# 테스트용 오버라이드(원본 무수정 red 확인 전용)는 **argv 플래그로만** 받는다 — env 오버라이드는
# 집행 경로(pre-commit)에서 가드 없이 먹는 게이트 백도어다(BL-706 계열). 플래그 사용 시
# stderr 에 test-mode 를 표기해 집행 로그와 테스트 로그가 구분되게 한다.
TESTMODE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --status-file)  [ $# -ge 2 ] || { echo "--status-file 에 값이 필요하다" >&2; exit 1; }; STATUS="$2"; TESTMODE=1; shift 2 ;;
    --backlog-file) [ $# -ge 2 ] || { echo "--backlog-file 에 값이 필요하다" >&2; exit 1; }; BACKLOG="$2"; TESTMODE=1; shift 2 ;;
    *) echo "알 수 없는 인자: $1 (지원: --status-file <f> · --backlog-file <f>)" >&2; exit 1 ;;
  esac
done
[ "$TESTMODE" -eq 1 ] && echo "⚠ test-mode: 기본 경로가 아닌 파일로 판정한다 (status=$STATUS · backlog=$BACKLOG)" >&2

for f in "$STATUS" "$BACKLOG"; do
  [ -r "$f" ] || { echo "✗ ABORT — 대상 파일이 없다: $f (측정불가는 통과가 아니다)" >&2; exit 3; }
done

FAIL=0

# ── ① 살아 있는 `다음 행동 =` — 파일 전체로 센다 (블록별로 세면 BL-643 사고가 통과한다) ──
# 매치 앞의 `~~` 가 홀수면 취소선 안(끝난 지시), 백틱이 홀수면 인라인 코드(인용) — 둘 다 제외.
live=$(awk '
  /^[ \t>]*(```|~~~)/ { fence = !fence; next }   # 들여쓰기·인용부(>) 뒤 백틱/물결 펜스도 토글 (bl-audit 계약)
  fence  { next }
  {
    s = $0; off = 0
    while (match(s, /다음 행동[ 	]*[=＝]/)) {
      pre = substr($0, 1, off + RSTART - 1)
      t = pre; nt = gsub(/~~/, "", t)
      b = pre; nb = gsub(/`/, "", b)
      if (nt % 2 == 0 && nb % 2 == 0) n++
      off += RSTART + RLENGTH - 1
      s = substr($0, off + 1)
    }
  }
  END { print n + 0 }
' "$STATUS")
if [ "$live" -gt 1 ]; then
  echo "✗ ① 살아 있는 「다음 행동 =」이 ${live}개다 (계약 ≤1) — 끝난 것은 ~~옛 문장~~ → 날짜 + 새 사실 로 바꿔라"
  FAIL=1
fi

# ── ② ⓪ 표 데이터 행 ≥3 — 후보가 3개 미만이면 「고르는 자리」가 아니다 ──
rows=$(awk '
  /^[ \t>]*(```|~~~)/ { fence = !fence; next }   # 들여쓰기·인용부(>) 뒤 백틱/물결 펜스도 토글 (bl-audit 계약)
  fence  { next }
  /^###/ { inzero = (index($0, "⓪") > 0); sep = 0; next }
  {
    if (!inzero) next
    line = $0; sub(/^[ 	]+/, "", line)
    if (substr(line, 1, 1) != "|") { sep = 0; next }  # 표가 끊기면 다음 표는 새로 판정
    if (line ~ /^\|[ 	:|-]*$/) { sep = 1; next }      # 구분행(하이픈 행)
    if (!sep) next        # 구분행 이전의 파이프 행 = 머리행 — 첫 칸 리터럴이 아니라 구조로 skip
    n++
  }
  END { print n + 0 }
' "$STATUS")
if [ "$rows" -lt 3 ]; then
  echo "✗ ② ⓪ 다음 후보 표의 데이터 행이 ${rows}개다 (계약 ≥3) — 고를 수 없는 표는 진입점이 아니다"
  FAIL=1
fi

# ── ③ backlog.md 안 RESOLVED 섹션 0건 — 원장 3분할(BL-779): RESOLVED 는 backlog-resolved.md 로 ──
# 판정 = harness-v1 bl-audit.sh 상태줄 판정과 동치 — lead() 로 첫 문장만 절단(`:**`·`—`·`.` 중
# 최선두)한 뒤 DEFERRED → ACTIVE → PARTIAL → RESOLVED 순으로 어휘를 대조한다(앞이 이긴다).
# 대소문자만 추가로 무시한다(toupper) — 대문자 RESOLVED 상태줄이 안 세지던 결함의 수리.
# 취소선(`~~`) 상태줄은 철회 표기라 근거에서 제외하고, 슬롯을 소비하지 않아 다음 상태줄이
# 자리를 잇는다(bl-audit 이 st_txt 로 첫 **유효** 줄만 잡는 것과 동일). RESOLVED 판정만 역류로 센다.
bad=$(awk '
  function lead(s,   p, q) {
    sub(/^\*\*(Status|상태)[ ]*[:：]?[ ]*(\*\*)?/, "", s)
    p = 0
    q = index(s, ":**");  if (q > 0 && (p == 0 || q < p)) p = q
    q = index(s, "—");    if (q > 0 && (p == 0 || q < p)) p = q
    q = index(s, ".");    if (q > 0 && (p == 0 || q < p)) p = q
    if (p > 0) s = substr(s, 1, p - 1)
    return s
  }
  function verdict_of(t) {
    t = toupper(t)
    if (t ~ /미도래|DEFERRED/)                            return "DEFERRED"
    if (t ~ /열려|열림|미해결|미실시|미착수|OPEN/)        return "ACTIVE"
    if (t ~ /부분 RESOLVED|부분 해결|부분 완료|PARTIAL/)  return "PARTIAL"
    if (t ~ /RESOLVED|해결 완료|완료/)                    return "RESOLVED"
    return "UNKNOWN"
  }
  /^### BL-[0-9]+/ { id = $2; seen = 0; next }
  seen || id == "" { next }
  /^\*\*(Status|상태)[ ]*[:：]/ {
    if ($0 ~ /~~/) next
    seen = 1
    if (verdict_of(lead($0)) == "RESOLVED") { n++; print id " (" NR "행)" > "/dev/stderr" }
  }
  END { print n + 0 }
' "$BACKLOG" 2>"${TMPDIR:-/tmp}/lv-resolved.$$")
if [ "$bad" -gt 0 ]; then
  echo "✗ ③ backlog.md 에 RESOLVED 섹션이 ${bad}건 있다 (계약 0건) — backlog-resolved.md 로 옮겨라: $(tr '\n' ' ' < "${TMPDIR:-/tmp}/lv-resolved.$$")"
  FAIL=1
fi
rm -f "${TMPDIR:-/tmp}/lv-resolved.$$"

[ "$FAIL" -eq 0 ] && echo "✓ ledger-vitals 3축 통과 (다음 행동=${live} · ⓪ 행=${rows} · 역류=0)"
exit "$FAIL"
