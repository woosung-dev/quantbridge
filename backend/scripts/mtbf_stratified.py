#!/usr/bin/env python
"""소크 세션 수명을 층으로 나눠 MTBF 와 그 신뢰구간을 낸다 — [BL-641].

**왜 스크립트인가.** [BL-641] 의 Trigger 는 「소크 재기동 회차마다 재측정」이다. 손계산으로
두면 그 Trigger 는 충족될 수 없고, 실제로 2026-08-08 에 문서 두 곳이 **같은 날 안에** 낡았다
(02:47Z 표를 06:15Z 에 인용하면 살아 있는 세션 3.7h 가 빠진다).

**이 도구가 존재하는 진짜 이유는 점추정을 막는 것이다.** 층화만 하면 「수리 이후 MTBF 가
8.70h → 19.24h 로 올랐다」처럼 읽힌다. 신뢰구간을 함께 내면 그 두 층은 **구간이 겹쳐**
통계적으로 구분되지 않는다. 그래서 CI 와 겹침 검정을 **표와 같은 실행에서** 낸다 — 따로
계산하게 두면 아무도 안 한다.

입력 = `trading.live_signal_sessions` 를 `|` 로 뽑은 것 (stdin 또는 --input):

    docker exec quantbridge-db psql -U quantbridge -d quantbridge -At -F'|' \\
      -c "SELECT id, created_at, deactivated_at,
                 coalesce(deactivated_reason::text, chr(45))
            FROM trading.live_signal_sessions ORDER BY created_at"

★살아 있는 세션은 **우측 절단**이다 — 노출은 더하고 사망은 더하지 않는다. 빼면 노출을
잃어 MTBF 가 비관 쪽으로, 사망으로 세면 낙관 쪽으로 틀어진다. 어느 쪽도 하지 않는다.

★자동사망 어휘는 `soak_gate_predicate` 에서 **import** 한다. 베껴 적으면 정본이 바뀔 때
조용히 갈라진다 — 이 레포가 이미 그 계열로 여러 번 덴 자리다.
"""

from __future__ import annotations

import argparse
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scipy.stats import chi2
from soak_gate_predicate import AUTOMATIC_DEATH_REASONS

# 층 경계 — 「무엇을 고친 뒤인가」다. 날짜가 아니라 **수리**가 경계라서 상수로 둔다.
STRATA_CUTOFFS: list[tuple[str, str | None, str]] = [
    ("전 이력", None, "혼합"),
    ("2026-08-03 이후", "2026-08-03T00:00:00", "혼합 — 문서가 인용해 온 값"),
    ("[ADR-025] 수리 이후", "2026-08-05T12:44:00", "gap-resync 1 · 오염 1"),
    ("[BL-622] 수리 이후", "2026-08-07T09:30:00", "오염 1건뿐"),
]

# 방법 동결 — 2026-08-08 bl003-unblock 회차가 낸 값. 원장이 자라도 **앞 38행으로 자르면**
# 이 값이 나와야 한다. 나오지 않으면 계산법이 바뀐 것이고, 그때는 표가 아니라 이 도구를 봐라.
SELF_CHECK = [
    ("전 이력", None, 38, 107.12, 8, 13.39),
    ("2026-08-03 이후", "2026-08-03T00:00:00", 14, 60.91, 7, 8.70),
]


def _dt(text: str) -> datetime:
    parsed = datetime.fromisoformat(text.strip())
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def parse_rows(text: str, now: datetime) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) < 4:
            raise SystemExit(f"열이 4개가 아니다 (id|created|deactivated|reason): {line!r}")
        session_id, created, deactivated, reason = parts[:4]
        start = _dt(created)
        end = _dt(deactivated) if deactivated.strip() else None
        rows.append(
            {
                "id": session_id.strip()[:8],
                "start": start,
                "end": end,
                "reason": reason.strip(),
                "alive": end is None,
                "hours": ((end or now) - start).total_seconds() / 3600.0,
                "auto_death": reason.strip() in AUTOMATIC_DEATH_REASONS,
            }
        )
    return rows


def mtbf_ci(exposure: float, deaths: int) -> tuple[float, float | None]:
    """지수 모형 MTBF 의 95% 신뢰구간 (총 노출 T, 사망 d 의 카이제곱 구간).

    d 가 작으면 구간은 배수로 벌어진다 — 그 벌어짐을 보여주는 것이 이 함수의 목적이다.
    d=0 이면 상한이 없다(None). 하한만 말할 수 있다.
    """
    low = 2 * exposure / chi2.ppf(0.975, 2 * deaths + 2)
    high = None if deaths == 0 else 2 * exposure / chi2.ppf(0.025, 2 * deaths)
    return low, high


def summarize(
    rows: list[dict[str, Any]], name: str, cutoff: str | None, note: str
) -> dict[str, Any]:
    bound = _dt(cutoff) if cutoff else None
    sel = [r for r in rows if bound is None or r["start"] >= bound]
    exposure = sum(r["hours"] for r in sel)
    deaths = sum(1 for r in sel if r["auto_death"])
    low, high = mtbf_ci(exposure, deaths)
    mtbf = exposure / deaths if deaths else None
    return {
        "name": name,
        "note": note,
        "n": len(sel),
        "exposure": exposure,
        "deaths": deaths,
        "censored": sum(1 for r in sel if r["alive"]),
        "longest": max((r["hours"] for r in sel), default=0.0),
        "reached_24h": sum(1 for r in sel if r["hours"] >= 24),
        "mtbf": mtbf,
        "ci_low": low,
        "ci_high": high,
        "p168": math.exp(-168 / mtbf) if mtbf else None,
        "p168_ci_high": math.exp(-168 / high) if high else 1.0,
    }


def run_self_check(rows: list[dict[str, Any]]) -> bool:
    """계산법이 2026-08-08 회차와 같은지 — 원장 앞 38행으로 잘라 재현한다."""
    frozen = [r for r in rows if not r["alive"]][:38]
    if len(frozen) < 38:
        print("  (자료가 38행 미만 — self-check 를 건너뛴다)")
        return True
    ok = True
    for name, cutoff, want_n, want_exp, want_deaths, want_mtbf in SELF_CHECK:
        stratum = summarize(frozen, name, cutoff, "")
        hit = (
            stratum["n"] == want_n
            and abs(stratum["exposure"] - want_exp) < 0.02
            and stratum["deaths"] == want_deaths
            and stratum["mtbf"] is not None
            and abs(stratum["mtbf"] - want_mtbf) < 0.02
        )
        ok = ok and hit
        print(
            f"  {'✓' if hit else '✗'} {name:18} n={stratum['n']}/{want_n} "
            f"노출={stratum['exposure']:.2f}/{want_exp} 사망={stratum['deaths']}/{want_deaths} "
            f"MTBF={stratum['mtbf']:.2f}/{want_mtbf}"
        )
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="psql `|` 출력 파일 (없으면 stdin)")
    parser.add_argument(
        "--now",
        help="관측 마감 ISO8601 (기본 = 현재). 살아 있는 세션의 노출을 어디서 끊을지",
    )
    args = parser.parse_args()

    now = _dt(args.now) if args.now else datetime.now(UTC)
    text = args.input.read_text() if args.input else sys.stdin.read()
    rows = parse_rows(text, now)
    if not rows:
        raise SystemExit("입력이 비었다")

    strata = [summarize(rows, name, cut, note) for name, cut, note in STRATA_CUTOFFS]

    print(f"관측 마감 {now.isoformat()}   원장 {len(rows)}행")
    print("\n▶ 층별 MTBF — ★점추정만 인용하지 마라. CI 를 같이 읽어라\n")
    header = (
        f"{'창':22} {'n':>3} {'노출':>9} {'절단':>4} {'사망':>4} "
        f"{'MTBF':>8}  {'95% CI':>18}  {'P(168h)':>10}  {'CI상한 P':>9}"
    )
    print(header)
    print("-" * len(header))
    for s in strata:
        mtbf = f"{s['mtbf']:.2f}h" if s["mtbf"] else "—"
        ci = (
            f"[{s['ci_low']:.2f}, {s['ci_high']:.2f}]"
            if s["ci_high"]
            else f"[{s['ci_low']:.2f}, ∞)"
        )
        p168 = f"{s['p168']:.3e}" if s["p168"] else "—"
        print(
            f"{s['name']:22} {s['n']:>3} {s['exposure']:>8.2f}h {s['censored']:>4} "
            f"{s['deaths']:>4} {mtbf:>8}  {ci:>18}  {p168:>10}  {s['p168_ci_high'] * 100:>8.2f}%"
        )

    print("\n▶ 구간 겹침 — 겹치면 그 두 층은 **구분되지 않는다**")
    separated = 0
    for i in range(len(strata)):
        for j in range(i + 1, len(strata)):
            a, b = strata[i], strata[j]
            a_high = a["ci_high"] or math.inf
            b_high = b["ci_high"] or math.inf
            overlap = a["ci_low"] <= b_high and b["ci_low"] <= a_high
            separated += 0 if overlap else 1
            print(f"  {'겹침 ' if overlap else '분리★'} {a['name']} ↔ {b['name']}")
    if separated == 0:
        print("\n  ⇒ ★★★어느 두 층도 분리되지 않는다 — 「수리로 MTBF 가 올랐다」는 말할 수 없다.")

    print("\n▶ 점추정이 아닌 셈 (여기가 결론의 근거다)")
    print(
        f"  24h 도달 {sum(1 for r in rows if r['hours'] >= 24)}건 / {len(rows)}세션"
        f"  ·  최장 {max(r['hours'] for r in rows):.2f}h"
        f"  ·  C1 요구치 168h = 최장의 {168 / max(r['hours'] for r in rows):.1f}배"
    )
    for r in rows:
        if r["alive"]:
            print(f"  ★살아 있는(절단) 세션 {r['id']} — 진행 {r['hours']:.4f}h")

    print("\n▶ self-check — 앞선 회차(2026-08-08 bl003-unblock)와 계산법이 같은가")
    if not run_self_check(rows):
        print("\n✗ self-check 실패 — 표를 인용하기 전에 계산법 변경을 확인해라.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
