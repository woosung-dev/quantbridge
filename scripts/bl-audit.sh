#!/usr/bin/env bash
# BL 상태 감사 — `docs/backlog.md` 각 섹션의 **상태:** / **Status:** 줄을 SSOT 로 읽고,
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
# 상태 근거에서 제외하는 구간 (BL-564)
#   ` ``` ` 코드펜스와 `<details>…</details>` 는 통째로 건너뛴다. 펜스 안은 예시이고
#   `<details>` 는 **폐기된 옛 판정을 접어두는 관용구**라(BL-553 에서 도입), 둘 다 SSOT 후보가
#   되면 철회된 판정이 되살아난다. ★태그는 **줄 머리에서만** 인정한다 — BL-564 자신의 산문이
#   `<details>` 를 문장 중간에 언급하므로, 아무 데서나 잡으면 그 뒤 섹션이 통째로 사라진다.
#   구간이 안 닫히면 조용히 삼키는 대신 **실패**로 보고한다.
#
# 사용법
#   scripts/bl-audit.sh [--list ACTIVE|PARTIAL|RESOLVED|UNKNOWN] [--no-crosscheck]
#
# 종료 코드: 0 = 불일치 0 & UNKNOWN 0 & 우선순위 오배치 0 & 중복 상태줄 0 & 중복 섹션 헤더 0 / 1 = 하나 이상 (게이트에 물릴 수 있게)
#   ★`--list` 는 목록 출력 전용이라 **항상 0** 이다 — 게이트에는 인자 없는 형태를 쓴다.
set -uo pipefail

LIST=""; CROSSCHECK=1
while [ $# -gt 0 ]; do
  case "$1" in
    --list) [ $# -ge 2 ] || { echo "--list 에 값이 필요하다" >&2; exit 1; }; LIST="$2"; shift 2 ;;
    --no-crosscheck) CROSSCHECK=0; shift ;;
    -h|--help) sed -n '2,34p' "$0"; exit 0 ;;
    *) echo "알 수 없는 인자: $1" >&2; exit 1 ;;
  esac
done
case "$LIST" in
  ""|ACTIVE|PARTIAL|RESOLVED|UNKNOWN) ;;
  *) echo "--list 는 ACTIVE|PARTIAL|RESOLVED|UNKNOWN 중 하나" >&2; exit 1 ;;
esac

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
BACKLOG="$ROOT/docs/backlog.md"
ROADMAP="$ROOT/docs/roadmap.md"
for f in "$BACKLOG" "$ROADMAP"; do
  [ -r "$f" ] || { echo "✗ 읽을 수 없다: $f" >&2; exit 1; }
done

# ★awk 는 두 파일을 이 순서로 읽는다 — backlog 먼저(NR==FNR), roadmap 나중.
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
  cur = ""
}
function reset(id, ln) {
  cur = id; sec_line[id] = ln
  order[++n] = id
  st_txt = ""; st_line = 0; st_dup = 0
  mk_txt = ""; mk_line = 0
  hd_check = 0; has_check = 0; has_res = 0
}

# ── 1) docs/backlog.md ───────────────────────────────────────────
NR == FNR {
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
  if ($0 ~ /^\|[ ]*\[BL-[0-9]+\]\(#bl-[0-9]+\)/) {
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
  } else if (mk_txt == "" && is_marker($0)) {
    mk_txt = $0; mk_line = FNR
  }
  if (index($0, "✅") > 0)     has_check = 1
  if (index($0, "Resolved") > 0) has_res = 1
  next
}

# ── 2) docs/roadmap.md — 체크박스 ────────────────────────────────
{
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
    for (i = 1; i <= n; i++) { id = order[i]; if (verdict[id] == LIST) printf "%s\t%s\t:%d\n", id, prio[id], sec_line[id] }
    exit 0
  }

  printf "══ bl-audit  backlog=docs/backlog.md  roadmap=docs/roadmap.md  섹션=%d ══\n", n

  printf "\n▶ 판정 (섹션 상태 줄이 SSOT · PARTIAL 은 active 로 세지 않는다)\n"
  for (i = 1; i <= n; i++) { id = order[i]; cnt[verdict[id]]++; pc[prio[id] "/" verdict[id]]++; pset[prio[id]] = 1 }
  split("ACTIVE PARTIAL RESOLVED UNKNOWN", vs, " ")
  for (k = 1; k <= 4; k++) printf "  %-9s %4d\n", vs[k], cnt[vs[k]] + 0
  printf "  %-9s %4d   (= ACTIVE)\n", "active", cnt["ACTIVE"] + 0
  printf "  %-9s %4d\n", "전체", n

  printf "\n▶ P별 내역\n"
  printf "  %-6s %8s %8s %9s %8s\n", "", "ACTIVE", "PARTIAL", "RESOLVED", "UNKNOWN"
  split("P0 P1 P2 P3", ps, " ")
  for (k = 1; k <= 4; k++) {
    p = ps[k]; if (!(p in pset)) continue
    printf "  %-6s %8d %8d %9d %8d\n", p, pc[p "/ACTIVE"] + 0, pc[p "/PARTIAL"] + 0, pc[p "/RESOLVED"] + 0, pc[p "/UNKNOWN"] + 0
  }
  for (p in pset) if (p !~ /^P[0-3]$/) printf "  %-6s %8d %8d %9d %8d   ★우선순위 파싱 실패\n", (p == "" ? "(없음)" : p), pc[p "/ACTIVE"] + 0, pc[p "/PARTIAL"] + 0, pc[p "/RESOLVED"] + 0, pc[p "/UNKNOWN"] + 0

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
      if (id in rowline) {
        if (v == "ACTIVE"   && ((id in rowmark) || (id in rowpart)))   { m++; printf "  %-8s 표 행에 ✅/🟡 인데 섹션은 ACTIVE          표:%d 섹션:%d\n", id, rowline[id], sec_line[id] }
        if (v == "RESOLVED" && !(id in rowmark))                       { m++; printf "  %-8s 섹션은 RESOLVED 인데 표 행에 ✅ 없음     표:%d 섹션:%d\n", id, rowline[id], sec_line[id] }
        if (v == "PARTIAL"  && !((id in rowmark) || (id in rowpart)))  { m++; printf "  %-8s 섹션은 PARTIAL 인데 표 행에 🟡 없음      표:%d 섹션:%d\n", id, rowline[id], sec_line[id] }
      }
      if (id in rmmark) {
        if (v == "ACTIVE"   && rmmark[id] == "x")    { m++; printf "  %-8s 로드맵 [x] 인데 섹션은 ACTIVE            로드맵:%d 섹션:%d\n", id, rmline[id], sec_line[id] }
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
  if (bad > 0) { printf "✗ UNKNOWN %d 건 + 불일치 %d 건 + 우선순위 배치 %d 건 + 중복 상태줄 %d 건 + 중복 섹션 헤더 %d 건 + 서식 오류 %d 건 — 표기 수치를 갱신하기 전에 이것부터 정리해라.\n", u, m, q, d, h, o; exit 1 }
  # ★성공 줄에서 리터럴 `3면` 을 빼지 마라 — `scripts/bl-audit-test.sh` ② 가 "정상 원장 → exit 0"
  #   의 증거로 그 문자열을 grep 한다. 축이 늘어도 "3면 + <새 축>" 꼴로 적어 하네스를 살려둔다.
  printf "✓ 4면 정합 — 3면(섹션 · 인덱스 표 · 로드맵) + 우선순위 배치. active=%d / 전체=%d\n", cnt["ACTIVE"] + 0, n
  exit 0
}
' "$BACKLOG" "$ROADMAP"
