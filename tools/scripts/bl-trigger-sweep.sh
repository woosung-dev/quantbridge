#!/usr/bin/env bash
# BL 트리거 도래 판정기 — `docs/backlog.md` 각 섹션의 `**Trigger:**` 줄을 읽어
# 「그 조건이 지금 왔는가」를 버킷으로 가르고, **기계로 판정 가능한 세 축**은 직접 판정한다.
#
# 왜 이 스크립트가 있나 (2026-08-10 bl-trigger-triage)
#   `bl-audit` 의 ACTIVE 는 「닫혔다고 선언되지 않은 것」이었고, 열린 항목 전부가 거기 떨어졌다.
#   그런데 열린 항목의 **트리거 기재율은 159/159** 다 — 즉 「지금 할 수 있는가」를 가릴 정보는
#   이미 원장에 있었고, 그걸 읽는 기계가 없었을 뿐이다.
#   ★이 스크립트가 보증하는 것은 **전량 커버리지**다. 표본으로 판정하면 그 회차는 값이 0이다
#     (2026-08-09 status-triage-mass 에서 표본 20건이 검정력 0 이었던 실측 이력).
#
# 무엇을 기계가 판정하고 무엇을 사람이 판정하나 — 이 경계를 흐리지 마라
#   기계 판정 ⑴ `BL의존`  — 참조된 BL 의 판정을 `bl-audit` 에서 되읽어 **전부 RESOLVED 일 때만 도래**
#   기계 판정 ⑵ `소크`    — `--soak PASS|FAIL|UNKNOWN`. **PASS 만 도래** ([ADR-024])
#   기계 판정 ⑶ `지금`    — 트리거 문장 자신이 도래를 선언("즉시"·"이미 발화했다"·"누적 … 검출")
#                           ★★이 축은 `--selftest` 가 **먼저 잡아서** 생겼다. 초안에는 2축뿐이라
#                             양성 대조 2건이 「판단 필요」로 떨어졌다 — 판별력 검사를 전량 스윕
#                             **앞**에 두지 않았으면 그 구멍이 159건 판정 뒤에 드러났을 것이다.
#   나머지는 **버킷만** 준다(`외생`/`동승`/`지금`/`미분류`). 최종 판정은 사람이 근거와 함께 적는다.
#   ★버킷은 판정이 아니다. 한국어 산문을 정규식으로 읽는 것은 분류지 판단이 아니고,
#     그걸 판정이라고 부르는 순간 이 스크립트는 극장이 된다.
#
# 어휘 (판정 결과가 들어갈 자리)
#   도래     → `**상태:**` 를 `⬜ Open` 계열로 유지
#   미도래   → `**상태:** ⏳ **대기 (트리거 미도래)**` + `**트리거 판정:**` 줄
#   (판정어 DEFERRED 의 계약 = `tools/scripts/bl-audit.sh` 헤더 · [ADR-028])
#
# 사용법
#   tools/scripts/bl-trigger-sweep.sh [--soak PASS|FAIL|UNKNOWN] [--include-deferred] [--selftest] [--tsv]
#
#   --include-deferred  대상에 DEFERRED 를 더해 ACTIVE ∪ PARTIAL ∪ DEFERRED 를 스윕한다.
#   --selftest  판별력 검사. **전량 스윕 전에 이걸 먼저 통과시켜라.**
#   --tsv       id/P/버킷/기계판정/트리거 를 TSV 로. 기본은 요약만.
#
# 종료 코드: 0 = 정상(또는 selftest 전건 통과) / 1 = 커버리지 결손 또는 selftest 실패
set -uo pipefail

SOAK="UNKNOWN"; MODE="summary"; INCLUDE_DEFERRED=0
while [ $# -gt 0 ]; do
  case "$1" in
    --soak) [ $# -ge 2 ] || { echo "--soak 에 값이 필요하다" >&2; exit 1; }; SOAK="$2"; shift 2 ;;
    --include-deferred) INCLUDE_DEFERRED=1; shift ;;
    --selftest) MODE="selftest"; shift ;;
    --tsv) MODE="tsv"; shift ;;
    # ★범위는 헤더 끝(`# 종료 코드:` 줄)까지다 — 헤더에 줄을 더하면 **여기도 늘려라**.
    #   2026-08-15 에 `--include-deferred` 설명을 넣고 이 숫자를 안 고쳐 종료 코드 줄이 잘렸다.
    -h|--help) sed -n '2,35p' "$0"; exit 0 ;;
    *) echo "알 수 없는 인자: $1" >&2; exit 1 ;;
  esac
done
case "$SOAK" in PASS|FAIL|UNKNOWN) ;; *) echo "--soak 는 PASS|FAIL|UNKNOWN 중 하나" >&2; exit 1 ;; esac

ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
export QB_ROOT="$ROOT" QB_SOAK="$SOAK" QB_MODE="$MODE" QB_INCLUDE_DEFERRED="$INCLUDE_DEFERRED"

python3 - <<'PY'
import os, re, subprocess, sys
from collections import Counter

ROOT = os.environ["QB_ROOT"]
SOAK = os.environ["QB_SOAK"]
MODE = os.environ["QB_MODE"]
INCLUDE_DEFERRED = os.environ["QB_INCLUDE_DEFERRED"] == "1"
# ★원장은 **파일 하나가 아니다** ([BL-779], 2026-08-16). `backlog.md` 만 읽으면
#   `backlog-resolved.md` 로 내려간 섹션의 `**Trigger:**`·`**트리거 판정:**` 이 통째로
#   「없음」이 되고, 그러면 selftest 의 양성 픽스처(BL-438)는 red 로 죽고 음성 픽스처
#   (BL-022 — 판정줄이 없는 섹션)는 **항진명제로 초록**이 된다. 같은 사고를 #618 docs-diet
#   에서 이미 한 번 밟았다(BL-451 픽스처가 본문 접힘으로 죽었다 — CASES 주석 참조).
BACKLOGS = [
    os.path.join(ROOT, "docs", "backlog.md"),
    os.path.join(ROOT, "docs", "backlog-resolved.md"),
]


def verdicts():
    """bl-audit 이 정본이다 — 판정을 여기서 다시 계산하지 않는다."""
    out = {}
    for v in ("ACTIVE", "DEFERRED", "PARTIAL", "RESOLVED", "UNKNOWN"):
        r = subprocess.run(
            ["bash", os.path.join(ROOT, "tools", "scripts", "bl-audit.sh"), "--list", v],
            capture_output=True, text=True,
        )
        for line in r.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                out[parts[0]] = (v, parts[1])
    return out


def section_field(prefix):
    """섹션별 `<prefix>` 로 시작하는 **첫 줄**. 펜스/<details> 제외 규칙은 bl-audit 과 같다."""
    out = {}
    for backlog in BACKLOGS:
        cur, fence, details = None, False, 0
        for line in open(backlog, encoding="utf-8"):
            line = line.rstrip("\n")
            if re.match(r"^[ \t>]*```", line):
                fence = not fence
                continue
            if fence:
                continue
            if re.match(r"^[ \t>]*<details", line):
                details += 1
            if re.match(r"^[ \t>]*</details>", line):
                details = max(0, details - 1)
                continue
            if details:
                continue
            m = re.match(r"^### (BL-\d+)", line)
            if m:
                cur = m.group(1)
                continue
            if re.match(r"^#{1,2} ", line):
                cur = None
                continue
            if cur and line.startswith(prefix) and cur not in out:
                out[cur] = re.sub(r"\s+", " ", line[len(prefix):].strip())
    return out


def triggers():
    return section_field("**Trigger:**")


def human_verdicts():
    """섹션별 `**트리거 판정:**` 줄 — **사람이 이미 판정했는가**.

    ★기계의 「판단 필요」와 「아무도 판정하지 않았다」는 **다른 말**이다. 기계 3축은 한국어
      산문을 못 읽으므로 같은 항목에 매 회차 「판단 필요」를 낸다 — 원장에 근거와 함께 사람
      판정이 이미 적혀 있어도 그렇다. 그 둘을 안 가르면 회차마다 같은 목록을 다시 판정하려
      들고(2026-08-15 에 실제로 그러려다 19건 전부 이미 판정돼 있는 것을 발견했다), 진짜
      미판정 항목은 그 19건 뒤에 묻힌다.
    """
    return section_field("**트리거 판정:**")


# ── 버킷 문법 ──────────────────────────────────────────────────────────
# ★순서가 계약이다. `지금` 을 맨 앞에 두는 이유 = "즉시"·"이미 발화했다" 는 **자기 자신이
#   도래를 선언한 문장**이라, 뒤의 조건어 정규식에 물리면 조용히 미도래로 뒤집힌다.
SOAK_P = r"소크|soak|안정 운영|안정화|1주 (안정|운영)"
NOW_P = r"^즉시|이미 발화|누적 (위반|누락)"
EXO_P = (
    r"실자금|mainnet|메인넷|cutover|사용자[^)]{0,12}(승인|결정|요청|등장|수요|불편|보고|호출)"
    r"|외부 사용자|본인 의지|self-assess|Beta|베타|프로덕션 배포|고객"
    r"|접수 시|잦아|재발|흔해질|실사례|확인될 때|검출될|보고되|관측되|관측될|실측될|실관측|눈에 띌"
    r"|나올 때|생길 때|요구가|늘 때|등록 시|등장 시"
)
RIDE_P = (
    r"할 때|손댈 때|손볼|열 때|만들 때|추가 시|추가될 때|도입 시|도입할|변경 시|지원할|지원 시"
    r"|쓸 때|쓰려|쓰기|쓰이기|사이클|후속|정비 시|sprint|Sprint|검토 시|작업 시|강화|편집할"
    r"|커밋|착수|바꿀 때|늘리|판단하기|판단할|필요해질|생겼을|생기거나|열지|굴릴|돌릴|돌리기"
    r"|정기|필요 시|가능해질|묶음|동승|하려|회차|기 전|사용 시"
)


def bucket(t):
    if re.search(NOW_P, t):
        return "지금"
    if re.search(SOAK_P, t):
        return "소크"
    if re.search(r"BL-\d+", t):
        return "BL의존"
    if re.search(EXO_P, t):
        return "외생"
    if re.search(RIDE_P, t):
        return "동승"
    return "미분류"


def machine(bk, t, vd):
    """기계 판정 3축만. 나머지는 '판단 필요' — 여기서 추측하면 이 스크립트는 극장이 된다."""
    if bk == "지금":
        # ★추론이 아니라 **낭독**이다 — 트리거 문장 자신이 "즉시"·"이미 발화했다"·"누적 …
        #   검출" 로 도래를 선언했다. 선언을 읽는 것과 조건을 추정하는 것은 다르다.
        return "도래", "트리거가 스스로 도래를 선언"
    if bk == "소크":
        return ("도래" if SOAK == "PASS" else "미도래",
                f"soak-gate={SOAK} (PASS 만 도래 · ADR-024)")
    if bk == "BL의존":
        refs = sorted(set(re.findall(r"BL-\d+", t)))
        states = [(r, vd.get(r, ("없음", "-"))[0]) for r in refs]
        # ★섹션이 없는 BL 은 **모른다**. 아카이브된 Resolved 일 수도, 오타일 수도 있다 —
        #   "없음" 을 미해결로 읽으면 근거 없이 미도래를 단정하게 된다.
        unknown = [r for r, s in states if s == "없음"]
        if unknown:
            return "판단 필요", "선행 " + " · ".join(unknown) + " 섹션 없음 — 기계가 못 읽는다"
        open_ = [f"{r}={s}" for r, s in states if s != "RESOLVED"]
        if open_:
            return "미도래", "선행 " + " · ".join(open_)
        # ★★선행 BL 이 다 닫혔다고 트리거가 다 온 것이 아니다 — 트리거는 대개 **절의 접속**이고
        #   BL 참조는 그중 하나일 뿐이다. 남은 절(외생·동승)을 안 보고 "도래" 를 내면
        #   기계가 **반쪽만 읽고 전체를 단정**한다. 초판이 정확히 이걸로 5건을 잘못 올렸다
        #   (BL-409·654·669·681·685 — 예: BL-669 는 [BL-517] 종결 **+ 거래소 접촉 검증이
        #   가능한 회차** 인데 뒷절은 사용자 승인이다).
        rest = re.sub(r"\[?BL-\d+\]?(\([^)]*\))?", " ", t)
        if re.search(EXO_P, rest) or re.search(RIDE_P, rest):
            return "판단 필요", ("선행(" + " · ".join(r for r, _ in states)
                                 + ") 은 RESOLVED 지만 다른 절이 남았다")
        return "도래", "선행 전건 RESOLVED (" + " · ".join(r for r, _ in states) + ")"
    return "판단 필요", ""


vd = verdicts()
tg = triggers()
hv = human_verdicts()
# ★기본 대상은 ACTIVE **와 PARTIAL** 둘 다다 ([BL-703], 2026-08-11).
#   종전에는 ACTIVE 만이었고, 그래서 PARTIAL 24건이 이 판정기의 **구조적 사각지대**였다 —
#   그 안에 P0 1건 + P1 4건이 있었는데 판정 대상이 아니라서 아무도 세지 않았다.
#   `--include-deferred` 는 DEFERRED 를 **추가로** 읽는다. RESOLVED/UNKNOWN 은 대상이 아니다
#   (닫혔거나 상태줄 자체가 없다).
BASE_TARGET_VERDICTS = ("ACTIVE", "PARTIAL")


def target_verdicts(include_deferred: bool):
    return BASE_TARGET_VERDICTS + (("DEFERRED",) if include_deferred else ())


def compute_targets(include_deferred: bool):
    wanted = target_verdicts(include_deferred)
    return sorted((b for b, (v, _) in vd.items() if v in wanted),
                  key=lambda x: int(x[3:]))


TARGET_VERDICTS = target_verdicts(INCLUDE_DEFERRED)
targets = compute_targets(INCLUDE_DEFERRED)

# ── selftest — 판별력. 전량 스윕보다 **먼저** 통과해야 한다 ────────────
if MODE == "selftest":
    # 양성 2 + 음성 4. 한쪽만 있으면 판별력이 아니라 편향이다.
    # ★음성 4 중 2건은 **판정기 자신의 오판**에서 왔다 — 초판이 도래로 올린 것을 되잡는다.
    CASES = [
        # ★BL-451 → BL-438 재지정 (2026-08-13): BL-451 은 Resolved + docs-diet 본문 접힘으로
        #   Trigger 줄 자체가 사라져 픽스처가 죽었다(판별력 상실은 이 회차가 아니라 #618 에서 발생).
        ("BL-438", "도래", "조건어 없음 (`즉시`)"),
        ("BL-591", "도래", "트리거가 스스로 발화를 선언"),
        ("BL-015", "미도래", "소크 축 — PASS 아님"),
        ("BL-403", "미도래", "선행 BL-395 미해결"),
        # ★음성 대조 ⑵ — **과다 포획** 검사. 초판은 이 건을 "도래" 로 올렸다:
        #   [BL-517] 은 실제로 종결됐지만 뒷절("거래소 접촉 검증이 가능한 회차")이 남아 있다.
        #   선행 BL 만 보고 도래를 단정하면 안 된다는 것을 이 케이스가 고정한다.
        ("BL-669", "판단 필요", "선행은 닫혔지만 뒷절(거래소 접촉)이 남았다"),
        # ★음성 대조 ⑶ — 섹션 없는 선행을 미해결로 읽지 않는다.
        ("BL-373", "판단 필요", "선행 BL-365 섹션 없음 — 모르는 것을 단정하지 않는다"),
    ]
    fails = 0
    print("══ bl-trigger-sweep --selftest  (판별력 = 참/거짓을 실제로 가르는가) ══")
    print(f"  soak={SOAK}\n")
    for bl, want, why in CASES:
        t = tg.get(bl, "")
        bk = bucket(t)
        got, ev = machine(bk, t, vd)
        ok = got == want
        fails += 0 if ok else 1
        print(f"  {'✓' if ok else '✗'} {bl}  기대={want:6} 실제={got:8} 버킷={bk:6} {why}")
        if ev:
            print(f"      근거: {ev}")
        if not ok:
            print(f"      트리거: {t[:100]}")

    # ── 대상 집합 검사 ([BL-703], 2026-08-11) ─────────────────────────
    # ★위 CASES 는 `machine()` 을 id 로 **직접** 부르므로 `targets` 를 좁혀도 전건 통과한다.
    #   즉 2026-08-11 이전의 selftest 는 「무엇을 판정 대상으로 삼는가」에 대해 **판별력이 0**
    #   이었고, `대상=ACTIVE` 로 PARTIAL 24건이 조용히 빠져 있던 것을 못 잡았다.
    #   판정 로직만 재고 대상 집합을 안 재면, 스윕은 옳은 답을 **틀린 모집단**에 대해 낸다.
    print("  ── 대상 집합 (판정 로직이 아니라 **모집단**을 잰다) ──")
    default_targets = compute_targets(False)
    deferred_targets = compute_targets(True)
    SET_CASES = [
        ("기본 모드에 PARTIAL 이 든다", any(vd.get(b, ("", ""))[0] == "PARTIAL" for b in default_targets)),
        ("기본 모드에 ACTIVE 가 남아 있다", any(vd.get(b, ("", ""))[0] == "ACTIVE" for b in default_targets)),
        # ★음성 대조 — 빈 대상은 「위반 0건」이 아니라 **측정 실패**다 ([LESSON-101]).
        ("기본 모드 대상이 비어 있지 않다", len(default_targets) > 0),
        # ★양성/음성 대조 — 이 두 검사가 없으면 include 축을 지워도 selftest 가 녹색이다.
        ("확장 모드에 DEFERRED 가 든다", any(vd.get(b, ("", ""))[0] == "DEFERRED" for b in deferred_targets)),
        ("기본 모드에 DEFERRED 가 없다", all(vd.get(b, ("", ""))[0] != "DEFERRED" for b in default_targets)),
        # ★사람 판정 축 — 양성/음성 한 쌍. 한쪽만 두면 「전부 있다」/「전부 없다」로 답하는
        #   파서도 통과한다(이 레포가 빈 입력 초록으로 다섯 번 속았다).
        ("판정 줄이 있는 섹션을 읽는다 (BL-547)", bool(hv.get("BL-547"))),
        ("판정 줄이 없는 섹션을 없다고 한다 (BL-022)", not hv.get("BL-022")),
    ]
    # ★CLI 배선 — 위 케이스는 전부 python 함수를 **직접** 부르므로 `--include-deferred` 파서를
    #   통째로 지워도 13/13 이 나온다(2026-08-15 codex 적대 리뷰 P3). [LESSON-092] §2 의 판이다:
    #   순수 함수의 정확성은 배선의 증거가 아니다. 그래서 **이 스크립트를 실제로 두 모드로
    #   재실행**해 대상 수가 갈리는지 본다 — 파서가 죽으면 두 수가 같아진다.
    SELF = os.path.join(ROOT, "tools", "scripts", "bl-trigger-sweep.sh")

    def _rows(extra):
        r = subprocess.run(["bash", SELF, *extra, "--tsv"], capture_output=True, text=True)
        return len([ln for ln in r.stdout.splitlines() if ln.strip()])

    cli_base, cli_ext = _rows([]), _rows(["--include-deferred"])
    SET_CASES += [
        (f"CLI 배선 — 기본 {cli_base}건 · 확장 {cli_ext}건 이 실제로 갈린다", cli_ext > cli_base),
        (f"CLI 배선 — 기본 실행이 함수 계산({len(default_targets)}건)과 같다",
         cli_base == len(default_targets)),
    ]

    for label, ok in SET_CASES:
        fails += 0 if ok else 1
        print(f"  {'✓' if ok else '✗'} {label}")
    if not default_targets:
        print("      기본 모드 대상이 0건이다 — bl-audit 이 죽었거나 TARGET_VERDICTS 가 잘못됐다")

    total = len(CASES) + len(SET_CASES)
    print()
    if fails:
        print(f"✗ 판별력 없음 — {fails}건이 안 갈렸다. **전량 스윕으로 가지 마라.**")
        sys.exit(1)
    print(f"✓ {total}/{total} — 판정 6(양성 2 · 음성 4) + 대상 집합 5 + 사람 판정 2 + CLI 배선 2. 전량 스윕 가능.")
    sys.exit(0)

# ── 전량 스윕 ──────────────────────────────────────────────────────────
rows, missing = [], []
for b in targets:
    t = tg.get(b)
    if t is None:
        missing.append(b)
        continue
    bk = bucket(t)
    got, ev = machine(bk, t, vd)
    rows.append((b, vd[b][1], bk, got, ev, t))

if MODE == "tsv":
    for b, p, bk, got, ev, t in rows:
        print(f"{b}\t{p}\t{bk}\t{got}\t{ev}\t{t}")
else:
    scope = " ∪ ".join(TARGET_VERDICTS)
    print(f"══ bl-trigger-sweep  대상={scope} {len(targets)}건  soak={SOAK} ══\n")
    print("▶ 버킷 분포")
    for k, v in Counter(r[2] for r in rows).most_common():
        print(f"  {k:8} {v:4}")
    print("\n▶ 기계 판정 (3축만 — 나머지는 사람이 근거와 함께 정한다)")
    for k, v in Counter(r[3] for r in rows).most_common():
        print(f"  {k:8} {v:4}")
    print(f"\n▶ 커버리지  {len(rows)}/{len(targets)}")
    # ★「기계가 못 가린 것」과 「아무도 판정하지 않은 것」을 가른다 (2026-08-15 ledger-thaw).
    #   이 둘을 합쳐 보면 매 회차 같은 목록을 다시 판정하려 들고, 진짜 미판정은 그 뒤에 묻힌다.
    need = [r for r in rows if r[3] == "판단 필요"]
    unjudged = [r for r in need if not hv.get(r[0])]
    print(f"\n▶ 사람 판정 — 「판단 필요」 {len(need)}건 중 "
          f"판정 줄 있음 {len(need) - len(unjudged)} · **없음 {len(unjudged)}**")
    for r in unjudged[:20]:
        print(f"        · {r[0]}  {r[5][:70]}")
    if not unjudged and need:
        print("        (전건 판정돼 있다 — 기계의 「판단 필요」는 3축이 못 읽는다는 뜻이지 미판정이 아니다)")
    # ★확장 모드의 산출물은 「DEFERRED 중 **지금 도래한 것**」이다 — 그것이 다음 회차들의
    #   후보 풀이다. 전체 분포에 섞어 찍으면 기본 대상 25건과 구분이 안 돼 밖에서 판정어를
    #   다시 조인해야 한다(2026-08-15 에 실제로 그랬다). **0건이면 0건이 답이다.**
    if INCLUDE_DEFERRED:
        dfr = [r for r in rows if vd[r[0]][0] == "DEFERRED"]
        print(f"\n▶ DEFERRED {len(dfr)}건만 따로 (이번에 새로 열린 축)")
        for k, v in Counter(r[3] for r in dfr).most_common():
            print(f"  {k:8} {v:4}")
        arrived = [r for r in dfr if r[3] == "도래"]
        print(f"  ▶ 그중 **도래 {len(arrived)}건** — 다음 회차 후보 풀"
              + ("" if arrived else " (기계 3축으로는 없다 — 나머지는 사람이 본다)"))
        for r in arrived:
            print(f"        · {r[0]}  {r[5][:80]}")

if missing:
    print(f"\n✗ `**Trigger:**` 줄이 없는 대상 {len(missing)}건 — "
          f"판정 대상에서 조용히 빠진다: {' '.join(missing)}")
    sys.exit(1)
sys.exit(0)
PY
