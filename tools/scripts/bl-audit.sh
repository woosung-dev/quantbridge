#!/usr/bin/env bash
# BL 상태 감사 — 원장 각 섹션의 **상태:** / **Status:** 줄을 SSOT 로 읽고,
# 인덱스 표의 ✅ 마커 · `docs/roadmap.md` 체크박스와 대조한다.
# 여기에 **우선순위 배치**를 더해 4면을 본다 (BL-637) — 인덱스 행이 실린 `## Pn` 표와
# 그 BL 섹션의 `**Priority:**` 가 갈리면 실패다.
#
# 왜 이 스크립트가 있나
#   지금까지 "공식 산식" 은 backlog.md 헤더에 박힌 **인라인 awk 주석**이었고 사람이 복붙해 돌렸다.
#   그 산식의 판정은 "섹션 본문 어딘가에 `Resolved` 문자열이 있으면 RESOLVED" 였다 —
#   즉 **cross-ref 한 줄이 항목을 지운다.** 실제로 BL-003(P0, 열려 있음)이 자기 섹션 안의
#   `BL-004 ✅ Resolved (Sprint 28)` 두 줄 때문에 RESOLVED 로 집계됐고, 그래서
#   **공식 산식이 P0 active 를 0 으로 보고하고 있었다.** BL-499·BL-535 도 같은 뿌리로 뒤집혔다.
#   그래서 판정 근거를 "문자열이 있느냐" 가 아니라 **선언된 상태 줄**로 옮기고,
#   근거가 없으면 조용히 active/resolved 어느 쪽으로도 넘기지 않고 **UNKNOWN 으로 남긴다.**
#
# 판정 우선순위 (앞이 이기고, 근거를 함께 출력한다)
#   1. `**상태:**` / `**Status:**` 줄            → 그 줄의 선두 문장만 읽는다
#   2. `**✅ …` / `🟡 **…` 볼드 리드인 줄        → 같은 어휘로 읽는다
#   3. `### BL-xxx` 헤딩에 ✅                     → RESOLVED
#   4. 본문에 ✅/Resolved 가 **비구조적으로만** 등장 → UNKNOWN (사람이 판단한다)
#   5. 아무 신호 없음                             → ACTIVE (백로그의 기본값)
#
#   ★4 가 핵심이다. 낡은 산식이 틀린 지점이 정확히 여기고, 여기서 추측하면 같은 사고가 반복된다.
#   ★`🟡 부분 Resolved` = PARTIAL 이고 **active 로 세지 않는다** (backlog.md 헤더 규칙과 동일).
#
# DEFERRED — 5번째 판정어 (2026-08-10 bl-trigger-triage, [ADR-028])
#   `⏳ **대기 (트리거 미도래)**` = **트리거 조건이 아직 안 왔다**. 종전에는 이걸 적을 낱말이
#   없어서 열린 항목이 **전부 ACTIVE** 로 떨어졌고, 그래서 "ACTIVE 159" 는 작업량이 아니라
#   **셈하는 규칙이 만든 수**였다. 경계 = 외생 조건(사용자 승인 · cutover · Beta · 소크 · 외부
#   관측 · 선행 BL)**과** 동승 조건("그 파일을 다음에 열 때" — 단독 착수 시 값이 0)을 **둘 다** 포함한다.
#   ⇒ ACTIVE 는 이제 「지금 단독으로 착수 가능」만 가리킨다.
#   ★3면에서 DEFERRED 는 **ACTIVE 와 같은 「미완」 쪽**이다 — 인덱스 표에 ✅/🟡 가 있거나
#     로드맵이 `[x]` 면 불일치다. 인덱스 표에 새 마커를 요구하지 않는다(드리프트 표면 신설 금지).
#
# 상태 근거에서 제외하는 구간 (BL-564)
#   ` ``` ` 코드펜스와 `<details>…</details>` 는 통째로 건너뛴다. 펜스 안은 예시이고
#   `<details>` 는 **폐기된 옛 판정을 접어두는 관용구**라(BL-553 에서 도입), 둘 다 SSOT 후보가
#   되면 철회된 판정이 되살아난다. ★태그는 **줄 머리에서만** 인정한다 — BL-564 자신의 산문이
#   `<details>` 를 문장 중간에 언급하므로, 아무 데서나 잡으면 그 뒤 섹션이 통째로 사라진다.
#   구간이 안 닫히면 조용히 삼키는 대신 **실패**로 보고한다.
#
# 원장은 **파일 하나가 아니다** ([BL-779], 2026-08-16)
#   `docs/backlog.md`(열린 것) + `docs/backlog-resolved.md`(RESOLVED 본문). 수명이 다른 것이
#   한 파일에 섞여 있어 분리했고, 그래서 **3면 정합이 두 파일에 걸친다** — 인덱스 표 행은
#   `backlog.md` 에 남고 그 행이 가리키는 섹션은 `backlog-resolved.md` 에 있다.
#   ★두 파일을 **하나의 원장으로** 읽는다: 섹션 id 는 파일을 가로질러 유일해야 하고
#     (한쪽에 남긴 채 복사하면 중복 섹션 헤더로 red), 카운트는 합계다.
#   ★★한쪽 파일을 못 읽으면 그 섹션들이 통째로 사라지는데 **판정은 조용히 초록**이 된다
#     (없는 것은 불일치를 못 낸다). 그래서 원장 파일이 비었거나 섹션이 0개면 rc=1 이 아니라
#     **rc=3 ABORT** 다 — 빈 입력을 「위반 0건」으로 통과시키지 않는다 ([LESSON-101]).
#     보고 머리줄이 **파일별 섹션 수**를 찍는 것도 같은 이유다(합계만 보면 이동이 누락을 가린다).
#
# 사용법
#   tools/scripts/bl-audit.sh [--list ACTIVE|DEFERRED|PARTIAL|RESOLVED|UNKNOWN] [--no-crosscheck]
#
# 종료 코드: 0 = 불일치 0 & UNKNOWN 0 & 우선순위 오배치 0 & 중복 상태줄 0 & 중복 섹션 헤더 0 / 1 = 하나 이상 (게이트에 물릴 수 있게)
#   3 = ABORT (원장 파일이 없거나 비었거나 섹션 0개 — 측정불가는 통과가 아니다)
#   ★`--list` 는 목록 출력 전용이라 **항상 0** 이다 — 게이트에는 인자 없는 형태를 쓴다.
#     ★단 ABORT(3)는 `--list` 에서도 난다. 소비자(`docs-audit`·`bl-trigger-sweep`)가 빈 stdout 을
#       「공집합」으로 읽고 계속 가는 것을 막는다.
set -uo pipefail

LIST=""; CROSSCHECK=1
while [ $# -gt 0 ]; do
  case "$1" in
    --list) [ $# -ge 2 ] || { echo "--list 에 값이 필요하다" >&2; exit 1; }; LIST="$2"; shift 2 ;;
    --no-crosscheck) CROSSCHECK=0; shift ;;
    -h|--help) sed -n '2,59p' "$0"; exit 0 ;;   # ★헤더 주석에 줄을 더하면 이 범위를 함께 옮겨라
    *) echo "알 수 없는 인자: $1" >&2; exit 1 ;;
  esac
done
case "$LIST" in
  ""|ACTIVE|DEFERRED|PARTIAL|RESOLVED|UNKNOWN) ;;
  *) echo "--list 는 ACTIVE|DEFERRED|PARTIAL|RESOLVED|UNKNOWN 중 하나" >&2; exit 1 ;;
esac

ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
# ★원장 = 이 목록 전체다. 파일을 더할 때는 여기 한 줄만 더한다 — 파서는 파일 수를 모른다.
LEDGERS=("$ROOT/docs/backlog.md" "$ROOT/docs/backlog-resolved.md")
ROADMAP="$ROOT/docs/roadmap.md"

# ★★ABORT 축 — 측정불가는 통과가 아니다. 원장 한쪽이 비면 그 섹션들이 통째로 사라지는데
#   판정은 「불일치 0건」으로 초록이 된다(없는 것은 불일치를 못 낸다). 이 레포는 빈 입력이
#   「원하는 답」으로 새는 사고를 다섯 번 이상 밟았다 ([LESSON-101]).
for f in "${LEDGERS[@]}"; do
  [ -r "$f" ]                    || { echo "✗ ABORT — 원장을 읽을 수 없다: ${f#"$ROOT/"}" >&2; exit 3; }
  [ -s "$f" ]                    || { echo "✗ ABORT — 원장이 비어 있다: ${f#"$ROOT/"} — 빈 입력을 「위반 0건」으로 통과시키지 않는다" >&2; exit 3; }
  grep -qE '^### BL-[0-9]+' "$f" || { echo "✗ ABORT — 원장에 '### BL-<n>' 섹션이 0개다: ${f#"$ROOT/"}" >&2; exit 3; }
done
[ -r "$ROADMAP" ] || { echo "✗ ABORT — 읽을 수 없다: ${ROADMAP#"$ROOT/"}" >&2; exit 3; }

# ★awk 는 원장 전량을 먼저 읽고 roadmap 을 마지막에 읽는다. 구분은 **파일 순서가 아니라**
#   인자 사이에 낀 `ROADMAP=1` 대입이다 — `NR==FNR` 은 첫 파일이 0줄이면 다음 파일로 새고
#   (하네스는 실제로 빈 roadmap 을 쓴다), 파일이 셋 이상이면 애초에 성립하지 않는다.
awk -v LIST="$LIST" -v CROSSCHECK="$CROSSCHECK" '
# ── 상태 어휘 ────────────────────────────────────────────────────
# lead = 상태 선언의 **첫 문장**. 상태 줄은 대개 한 문단이라 통째로 훑으면
#        본문 서술의 "아직"·"미실시" 가 판정을 뒤집는다. 그래서 잘라서 본다.
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
  # ★DEFERRED 를 ACTIVE 앞에 둔다 — "미도래" 를 적은 줄이 뒤에서 다른 어휘에 물리면
  #   조용히 ACTIVE 로 되돌아가고, 그러면 이 어휘를 신설한 이유가 통째로 사라진다.
  if (t ~ /미도래|Deferred/)                            return "DEFERRED"
  if (t ~ /열려|열림|미해결|미실시|미착수|Open/)        return "ACTIVE"
  if (t ~ /부분 Resolved|부분 해결|부분 완료|Partial/)  return "PARTIAL"
  if (t ~ /Resolved|해결 완료|완료/)                     return "RESOLVED"
  return "UNKNOWN"
}
# 볼드 리드인 = 줄 앞머리 12바이트 안에 ✅/🟡 가 있는 줄 (`**✅ Resolved …`, `🟡 **부분 …`)
# ★`~~취소선~~` 은 이 레포에서 **철회** 표기다 (BL-536 의 `~~✅ 판정 「축소」~~ (위에서 철회)`).
#   그걸 근거로 읽으면 철회된 판정이 되살아난다 — 그래서 상태 근거에서 제외한다.
function is_marker(s,   h) {
  if (index(s, "~~") > 0) return 0
  h = substr(s, 1, 12); return (index(h, "✅") > 0 || index(h, "🟡") > 0)
}

function finalize(   t, v) {
  if (cur == "") return
  if (st_txt != "")      { v = verdict_of(lead(st_txt)); ev = "상태줄 :" st_line }
  else if (mk_txt != "") { v = verdict_of(lead(mk_txt)); ev = "볼드 리드인 :" mk_line }
  else if (hd_check)     { v = "RESOLVED";               ev = "헤딩 ✅" }
  else if (has_check || has_res) { v = "UNKNOWN";        ev = "상태 줄 없음 + 본문 ✅/Resolved 가 cross-ref 위치에만" }
  else                   { v = "ACTIVE";                 ev = "상태 줄 없음 + 해결 신호 없음" }
  if (v == "UNKNOWN" && st_txt != "") ev = ev " (어휘 미해석)"
  verdict[cur] = v; evid[cur] = ev
  # ★중복 상태줄은 **섹션 서수(n)** 로 키를 잡는다 — id 로 잡으면 같은 id 섹션이 둘일 때
  #   뒤 섹션이 앞 섹션의 줄번호를 덮어써 "어느 섹션이 문제인가" 가 뒤바뀐다.
  #   여기서 `sec_line[cur]` 는 아직 **이 섹션**의 줄이다(다음 reset 전에 finalize 가 돈다).
  if (st_dup > 0) { dupn[n] = st_dup; dupid[n] = cur; dupsec[n] = sec_line[cur] }
  if (tg_txt ~ /미도래/) { trig_def[cur] = 1; trig_line[cur] = tg_line }
  if (tg_dup > 0) { tgdupn[n] = tg_dup; tgdupid[n] = cur; tgdupsec[n] = sec_line[cur] }
  cur = ""
}
function reset(id, ln) {
  cur = id; sec_line[id] = ln; sec_src[id] = fn
  order[++n] = id
  st_txt = ""; st_line = 0; st_dup = 0
  tg_txt = ""; tg_line = 0; tg_dup = 0
  mk_txt = ""; mk_line = 0
  hd_check = 0; has_check = 0; has_res = 0
}

# ── 1) 원장 파일들 (docs/backlog.md · docs/backlog-resolved.md) ──
ROADMAP != 1 {
  # ★파일별 섹션 수를 따로 센다 — 합계만 보면 「한쪽 파일을 못 읽는다」가 이동 누락과
  #   구분되지 않는다. 머리줄이 이 수를 찍는 것이 AC 의 음성 대조 표면이다.
  if (FNR == 1) { fn = FILENAME; sub(/^.*\//, "", fn); forder[++nf] = fn }
  # ★코드펜스 / <details> 구간은 상태 근거에서 제외한다 (BL-564).
  #   인용부호(`> `) 안의 펜스도 같다. 태그는 **줄 머리**에서만 인정한다(산문 언급 오탐 차단).
  if ($0 ~ /^[ \t>]*```/)          { fence = !fence; next }
  if (fence)                        next
  if ($0 ~ /^[ \t>]*<details/)     { details++ }
  if ($0 ~ /^[ \t>]*<\/details>/)  { if (details > 0) details--; next }
  if (details > 0)                  next

  # ★인덱스 표 행이 **어느 H2 아래**에 실려 있는지 기억한다 (BL-637). 종전 파서는 행을 정규식으로만
  #   잡고 소속 섹션을 안 봤다 — 그래서 `**Priority:** P1` 인 BL 이 **P2 표**에 실려 있어도
  #   "✓ 정합 · exit 0" 이 나왔다. 배치가 곧 사람이 읽는 우선순위이므로 이건 조용한 오보다.
  # ★`## Deferred` · `## Beta 오픈 번들` · `## Cross-reference` 처럼 **P 섹션이 아닌 표**의 행은
  #   배치 대상이 아니다(Deferred 표의 BL 은 섹션 자체가 없다 — 의도). cursec 을 비워 제외한다.
  if ($0 ~ /^## /) {
    cursec = ""
    if (match($0, /^## P[0-9]/)) cursec = substr($0, 4, RLENGTH - 3)
  }

  # 인덱스 표 행:  | [BL-543](#bl-543) | 제목 … |
  # ★파일 접두사를 허용한다 — 섹션이 `backlog-resolved.md` 로 내려간 뒤에도 행을 **원본에**
  #   남기는 것이 [BL-779] ⑵ 의 계약이다. 접두사를 안 받으면 그 행이 파서에서 사라지고,
  #   그러면 「표 행에 ✅ 인데 섹션은 …」 대조가 **조용히 꺼진다**(없는 행은 불일치를 못 낸다).
  if ($0 ~ /^\|[ ]*\[BL-[0-9]+\]\([A-Za-z0-9._-]*#bl-[0-9]+\)/) {
    match($0, /BL-[0-9]+/); rid = substr($0, RSTART, RLENGTH)
    rowline[rid] = FNR
    rowsec[rid] = cursec
    if (index($0, "✅") > 0) rowmark[rid] = 1
    if (index($0, "🟡") > 0) rowpart[rid] = 1
  }
  if ($0 ~ /^### BL-[0-9]+/) {
    finalize()
    match($0, /BL-[0-9]+/); id = substr($0, RSTART, RLENGTH)
    # ★섹션 헤더 중복 = 실패. 이 파서는 **id 로 키를 잡으므로**(verdict/evid/sec_line/rowline)
    #   두 번째 벌이 첫 벌을 조용히 덮어쓴다 — 첫 벌은 판정에서 사라지지만 `order[]` 에는
    #   남아 카운트에는 잡혀서, 숫자만 보면 정상으로 읽힌다. 중복 상태줄과 같은 계약이다.
    if (id in secfirst) secdup[id] = secdup[id] " :" FNR; else secfirst[id] = FNR
    filecnt[fn]++
    reset(id, FNR)
    if (index($0, "✅") > 0) hd_check = 1
    next
  }
  # ★섹션은 다음 `### BL-` 또는 H1/H2 에서만 끝난다. **H3 부제목에서 끊으면 안 된다** —
  #   BL-535 는 본문에 `### 실주행 검증 …` 을 갖고 있어서, H3 에서 끊으면 그 아래의
  #   `★미실시` 와 ✅ 가 통째로 안 보이고 항목이 조용히 ACTIVE 로 떨어졌다(실측 확인).
  if ($0 ~ /^#{1,2} /) { finalize(); next }
  if (cur == "") next

  if ($0 ~ /^\*\*(Priority|우선순위)[ ]*[:：]/) {
    if (match($0, /P[0-9]/)) prio[cur] = substr($0, RSTART, RLENGTH)
  } else if ($0 ~ /^\*\*(Status|상태)[ ]*[:：]/ && index($0, "~~") == 0) {
    if (st_txt == "") { st_txt = $0; st_line = FNR } else st_dup++
  } else if ($0 ~ /^\*\*(트리거 판정|Trigger verdict)[ ]*[:：]/ && index($0, "~~") == 0) {
    # ★취소선 제외는 상태줄과 **같은 계약**이다 — 이 레포에서 `~~` 는 철회 표기이므로
    #   `**트리거 판정:** ~~미도래 …~~` 는 「미도래를 철회했다」는 뜻이다 (BL-547 이 그 판).
    #   그걸 미도래로 읽으면 도래한 항목을 DEFERRED 로 몰아 원장이 조용히 얼어붙는다.
    # ★★중복 줄을 **첫 줄만 보고 버리면 그것이 곧 이 축의 우회 경로다**(2026-08-15 codex P1).
    #   `**트리거 판정:** 도래` 뒤에 `**트리거 판정:** 미도래` 가 오면 첫 줄만 읽어 통과했다.
    #   상태줄이 `st_dup` 으로 중복을 **실패**시키는 것과 같은 이유로 여기서도 SSOT 를 강제한다:
    #   판정은 첫 줄로 하되(그 줄이 이긴다는 사실을 고정), **중복 자체를 실패로 올린다.**
    if (tg_txt == "") { tg_txt = $0; tg_line = FNR } else tg_dup++
  } else if (mk_txt == "" && is_marker($0)) {
    mk_txt = $0; mk_line = FNR
  }
  if (index($0, "✅") > 0)     has_check = 1
  if (index($0, "Resolved") > 0) has_res = 1
  next
}

# ── 2) docs/roadmap.md — 체크박스 ────────────────────────────────
ROADMAP == 1 {
  if ($0 !~ /^[ \t]*- \[[ x]\]/) next
  match($0, /^[ \t]*- \[[ x]\]/)
  mark = substr($0, RSTART + RLENGTH - 2, 1)
  # ★주어는 우선순위 태그 `[P1]` **앞**까지다. 뒤쪽 BL 참조는 서술이지 체크박스의 주어가 아니다
  #   (예: `- [ ] **BL-535** [P1] … (BL-530 이 라이브만 정렬 — …)` 에서 BL-530 을 접으면
  #    이미 [x] 인 BL-530 이 [ ] 로 뒤집혀 유령 불일치가 난다 — 실측으로 확인).
  #   `[P` 가 없는 줄(Beta 묶음 등)은 "—" 앞까지로 대신한다.
  p = index($0, " [P"); if (p == 0) p = index($0, "—")
  head = (p > 0) ? substr($0, 1, p - 1) : $0
  rest = head
  while (match(rest, /BL-[0-9]+/)) {
    rid = substr(rest, RSTART, RLENGTH)
    nxt = substr(rest, RSTART + RLENGTH, 1)
    rest = substr(rest, RSTART + RLENGTH)
    if (nxt ~ /[a-z]/) continue          # BL-186a / BL-186b 는 별개 항목 — 접지 않는다
    if (rid in rmmark && rmmark[rid] != mark) rmconf[rid] = rmconf[rid] " :" FNR
    rmmark[rid] = mark; rmline[rid] = FNR
  }
}

# ── 3) 보고 ──────────────────────────────────────────────────────
END {
  finalize()
  if (LIST != "") {
    # ★4번째 칸(원장 파일)은 [BL-779] 분할에서 붙였다. 소비자는 앞 두 칸만 읽으므로 안전하고,
    #   사람은 이 칸으로 「이 섹션이 어느 파일에 있나」를 grep 없이 안다.
    for (i = 1; i <= n; i++) { id = order[i]; if (verdict[id] == LIST) printf "%s\t%s\t:%d\t%s\n", id, prio[id], sec_line[id], sec_src[id] }
    exit 0
  }

  # ★파일별 섹션 수를 **합계와 함께** 찍는다. 한쪽 파일이 파서에서 빠지면 합계만 보고는
  #   「그 회차에 섹션이 준 것」과 구분되지 않는다 — 그 상태의 게이트는 초록이다 ([BL-779]).
  per = ""
  for (i = 1; i <= nf; i++) per = per (i > 1 ? " + " : "") sprintf("%s(%d)", forder[i], filecnt[forder[i]] + 0)
  printf "══ bl-audit  원장=%s  roadmap=docs/roadmap.md  섹션=%d ══\n", per, n

  printf "\n▶ 판정 (섹션 상태 줄이 SSOT · PARTIAL/DEFERRED 는 active 로 세지 않는다)\n"
  for (i = 1; i <= n; i++) { id = order[i]; cnt[verdict[id]]++; pc[prio[id] "/" verdict[id]]++; pset[prio[id]] = 1 }
  split("ACTIVE DEFERRED PARTIAL RESOLVED UNKNOWN", vs, " ")
  for (k = 1; k <= 5; k++) printf "  %-9s %4d\n", vs[k], cnt[vs[k]] + 0
  printf "  %-9s %4d   (= ACTIVE · 지금 단독 착수 가능한 것만)\n", "active", cnt["ACTIVE"] + 0
  printf "  %-9s %4d\n", "전체", n

  printf "\n▶ P별 내역\n"
  printf "  %-6s %8s %9s %8s %9s %8s\n", "", "ACTIVE", "DEFERRED", "PARTIAL", "RESOLVED", "UNKNOWN"
  split("P0 P1 P2 P3", ps, " ")
  for (k = 1; k <= 4; k++) {
    p = ps[k]; if (!(p in pset)) continue
    printf "  %-6s %8d %9d %8d %9d %8d\n", p, pc[p "/ACTIVE"] + 0, pc[p "/DEFERRED"] + 0, pc[p "/PARTIAL"] + 0, pc[p "/RESOLVED"] + 0, pc[p "/UNKNOWN"] + 0
  }
  for (p in pset) if (p !~ /^P[0-3]$/) printf "  %-6s %8d %9d %8d %9d %8d   ★우선순위 파싱 실패\n", (p == "" ? "(없음)" : p), pc[p "/ACTIVE"] + 0, pc[p "/DEFERRED"] + 0, pc[p "/PARTIAL"] + 0, pc[p "/RESOLVED"] + 0, pc[p "/UNKNOWN"] + 0

  printf "\n▶ P0 전량 (blocker 버킷은 항상 펼친다)\n"
  for (i = 1; i <= n; i++) { id = order[i]; if (prio[id] == "P0") printf "  %-9s %-8s :%-5d %s\n", verdict[id], id, sec_line[id], evid[id] }

  bad = 0
  printf "\n▶ UNKNOWN — 근거가 없어 판정하지 않았다 (추측 금지, 사람이 정한다)\n"
  u = 0
  for (i = 1; i <= n; i++) { id = order[i]; if (verdict[id] == "UNKNOWN") { u++; bad++; printf "  %-8s %-4s :%-5d %s\n", id, prio[id], sec_line[id], evid[id] } }
  if (u == 0) printf "  없음\n"

  printf "\n▶ 불일치 — 섹션 상태 ↔ 인덱스 표 ✅ ↔ 로드맵 체크박스\n"
  m = 0
  if (CROSSCHECK == 1) {
    for (i = 1; i <= n; i++) {
      id = order[i]; v = verdict[id]
      if (v == "UNKNOWN") continue
      # ★DEFERRED 는 ACTIVE 와 **같은 「미완」 쪽**이다 (2026-08-10, [ADR-028]). 여기서 빼면
      #   새 어휘가 crosscheck 를 **끄는 통로**가 된다 — 상태줄 어휘 하나로 3면 계약이 꺼진다.
      undone = (v == "ACTIVE" || v == "DEFERRED")
      if (id in rowline) {
        if (undone          && ((id in rowmark) || (id in rowpart)))   { m++; printf "  %-8s 표 행에 ✅/🟡 인데 섹션은 %-8s      표:%d 섹션:%d\n", id, v, rowline[id], sec_line[id] }
        if (v == "RESOLVED" && !(id in rowmark))                       { m++; printf "  %-8s 섹션은 RESOLVED 인데 표 행에 ✅ 없음     표:%d 섹션:%d\n", id, rowline[id], sec_line[id] }
        if (v == "PARTIAL"  && !((id in rowmark) || (id in rowpart)))  { m++; printf "  %-8s 섹션은 PARTIAL 인데 표 행에 🟡 없음      표:%d 섹션:%d\n", id, rowline[id], sec_line[id] }
      }
      if (id in rmmark) {
        if (undone          && rmmark[id] == "x")    { m++; printf "  %-8s 로드맵 [x] 인데 섹션은 %-8s        로드맵:%d 섹션:%d\n", id, v, rmline[id], sec_line[id] }
        if (v == "RESOLVED" && rmmark[id] == " ")    { m++; printf "  %-8s 로드맵 [ ] 인데 섹션은 RESOLVED          로드맵:%d 섹션:%d\n", id, rmline[id], sec_line[id] }
      }
    }
    for (id in rowline) if (!(id in verdict)) { m++; printf "  %-8s 인덱스 표 행만 있고 섹션이 없다             표:%d\n", id, rowline[id] }
    for (id in rmconf)                        { m++; printf "  %-8s 로드맵 안에서 체크 상태가 갈린다           로드맵:%s\n", id, rmconf[id] }
  }
  if (m == 0) printf "  없음\n"
  bad += m

  # ★우선순위 배치 (BL-637) — 인덱스 행이 실린 `## Pn` 표 ↔ 그 섹션의 `**Priority:**`.
  #   ★Priority 를 못 읽은 BL 도 **실패로 센다**(fail-closed). 못 읽으면 오배치 여부를 확인할
  #     수 없는데, "확인 못 했다" 를 통과로 쓰면 표기를 P 없이 적는 것만으로 이 축이 꺼진다.
  #     지금 원장은 199 섹션 전량이 P0~P3 로 파싱되므로 이 선택의 즉시 비용은 0 이다.
  q = 0
  if (CROSSCHECK == 1) {
    for (i = 1; i <= n; i++) {
      id = order[i]
      if (!(id in rowline) || rowsec[id] == "") continue
      if (prio[id] == "") {
        if (q++ == 0) printf "\n▶ 우선순위 배치 — 인덱스 표의 `## Pn` ↔ 섹션 `**Priority:**`\n"
        printf "  %-8s %s 표에 실렸는데 섹션에서 우선순위를 못 읽었다   표:%d 섹션:%d\n", id, rowsec[id], rowline[id], sec_line[id]
      } else if (prio[id] != rowsec[id]) {
        if (q++ == 0) printf "\n▶ 우선순위 배치 — 인덱스 표의 `## Pn` ↔ 섹션 `**Priority:**`\n"
        printf "  %-8s %s 표에 실렸는데 섹션은 %s                     표:%d 섹션:%d\n", id, rowsec[id], prio[id], rowline[id], sec_line[id]
      }
    }
  }
  bad += q

  # ★트리거 정합 (BL-725, 2026-08-15) — `**트리거 판정:** … 미도래` ↔ 상태줄 판정.
  #   [ADR-028] 은 「트리거 미도래 = DEFERRED」이고 상태줄 리드인이 `⏳ **대기 (트리거 미도래)**`
  #   여야 한다고 정한다. 그런데 감사기는 **상태줄만** SSOT 로 읽었으므로, 본문에 「트리거도
  #   미도래」를 적어 놓고 리드인만 `⬜ Open` 인 섹션이 조용히 **ACTIVE 로 세졌다** — ⓪ 표가
  #   그 항목을 다음 회차 후보로 올리고, 열어 보면 할 일이 없다. BL-725 가 정확히 그 판이었다.
  #   ★ACTIVE 만 잡는다. PARTIAL/RESOLVED 는 판정어가 다르므로 불일치가 아니다
  #     (부분 해결은 트리거와 무관하게 이미 착수된 것이고, 해결은 트리거를 넘어선 것이다).
  t = 0
  if (CROSSCHECK == 1) {
    for (i = 1; i <= n; i++) {
      id = order[i]
      if (!(id in trig_def) || verdict[id] != "ACTIVE") continue
      if (t++ == 0) printf "\n▶ 트리거 정합 — `**트리거 판정:** 미도래` ↔ 상태줄 판정 ([ADR-028])\n"
      printf "  %-8s 트리거는 미도래인데 상태줄이 ACTIVE 다 — 리드인을 `⏳ **대기 (트리거 미도래)**` 로   트리거:%d 섹션:%d\n", id, trig_line[id], sec_line[id]
    }
  }
  # ★중복 트리거 판정 줄 = 실패 (2026-08-15 codex P1). 첫 줄로 판정하므로, 뒤에 오는 줄이
  #   조용히 무시된다 — `**트리거 판정:** 도래` 다음에 `… 미도래` 를 적으면 위 축이 **통째로
  #   우회**된다. 상태줄(`st_dup`)과 같은 계약으로 SSOT 를 하나로 강제한다.
  tg = 0
  for (k in tgdupn) { if (tg++ == 0) printf "\n▶ 중복 트리거 판정 줄 — SSOT 는 하나여야 한다 (첫 줄로 판정했다)\n"; printf "  %-8s +%d 줄  섹션:%d\n", tgdupid[k], tgdupn[k], tgdupsec[k] }
  bad += tg
  bad += t

  # ★중복 상태줄 = 실패 (BL-564). SSOT 는 하나여야 한다 — 둘이면 어느 쪽이 이기는지가
  #   서식 순서에 달리고, 폐기된 판정이 첫 줄이면 조용히 그게 이긴다.
  #   폐기 보존이 목적이면 `<details>` 로 접어라 (파서가 건너뛴다).
  d = 0
  for (k in dupn) { if (d++ == 0) printf "\n▶ 중복 상태 줄 — SSOT 는 하나여야 한다 (첫 줄로 판정했다)\n"; printf "  %-8s +%d 줄  섹션:%d\n", dupid[k], dupn[k], dupsec[k] }
  bad += d

  # ★중복 섹션 헤더 = 실패 (BL-569). id 가 키라서 뒤 섹션이 앞 섹션의 판정을 통째로 덮어쓴다 —
  #   상태줄은 각자 하나씩이라 위의 `dup` 은 0 이고, 그래서 이 사고가 조용히 exit 0 을 유지했다.
  h = 0
  for (id in secdup) { if (h++ == 0) printf "\n▶ 중복 섹션 헤더 — `### BL-<n>` 은 하나여야 한다 (뒤 섹션이 앞 섹션 판정을 덮어썼다)\n"; printf "  %-8s 첫:%d  중복%s\n", id, secfirst[id], secdup[id] }
  bad += h

  # ★구간이 안 닫히면 그 뒤가 통째로 안 읽힌다 — 조용히 삼키지 말고 실패로 올린다.
  o = 0
  if (fence)      { o++; printf "\n▶ 서식 오류 — ``` 코드펜스가 닫히지 않았다 (그 뒤 본문이 통째로 무시됐다)\n" }
  if (details > 0) { o++; printf "\n▶ 서식 오류 — <details> %d 개가 닫히지 않았다 (그 뒤 본문이 통째로 무시됐다)\n", details }
  bad += o

  printf "\n════════════════════════════════════════\n"
  if (bad > 0) { printf "✗ UNKNOWN %d 건 + 불일치 %d 건 + 우선순위 배치 %d 건 + 트리거 정합 %d 건 + 중복 트리거줄 %d 건 + 중복 상태줄 %d 건 + 중복 섹션 헤더 %d 건 + 서식 오류 %d 건 — 표기 수치를 갱신하기 전에 이것부터 정리해라.\n", u, m, q, t, tg, d, h, o; exit 1 }
  # ★성공 줄에서 리터럴 `3면` 을 빼지 마라 — `tools/scripts/bl-audit-test.sh` ② 가 "정상 원장 → exit 0"
  #   의 증거로 그 문자열을 grep 한다. 축이 늘어도 "3면 + <새 축>" 꼴로 적어 하네스를 살려둔다.
  printf "✓ 5면 정합 — 3면(섹션 · 인덱스 표 · 로드맵) + 우선순위 배치 + 트리거 정합. active=%d / deferred=%d / 전체=%d\n", cnt["ACTIVE"] + 0, cnt["DEFERRED"] + 0, n
  exit 0
}
' "${LEDGERS[@]}" ROADMAP=1 "$ROADMAP"
