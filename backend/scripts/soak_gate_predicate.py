"""[BL-003] 「데모 1주(168h) 안정 운영」 게이트의 **순수 판정 함수**.

stdin 으로 JSON 을 받아 stdout 으로 JSON 판정을 낸다. **I/O 도 DB 도 docker 도 없다** —
수집은 `scripts/soak-gate.sh` 가 하고 여기는 계산만 한다. 그래야 같은 입력을 손으로 더한
값과 대조할 수 있다(판정기가 자기 값을 스스로 검증하면 순환이다).

낱말은 셋뿐이다 — **PASS / FAIL / UNKNOWN**. ★UNKNOWN 을 PASS 로 접지 않는다.

  PASS     C1~C5 전부 충족
  FAIL     평가 창 안에서 **실격 사건**을 관측했다 (자동 사망 · phantom · tick 정체)
  UNKNOWN  그 외 전부. 사유 낱말로 두 갈래를 구분한다:
             `진행중`   — 측정은 됐는데 시간이 모자라다
             `측정불가` — 잴 수 없었다 (C5 위반 · 표본 공백)

★창(window)과 리셋 규칙이 정의의 절반이다 — `docs/decisions/024-soak-stability-gate.md` §창.
  · 창 = 「라이브 세션 활성」 ∩ 「고정 커밋 불변」 을 동시에 만족하는 최대 구간
  · **고정되지 않은 스택은 미계상** — 어느 커밋이 돌았는지 답할 수 없으면 그 시간은 못 센다
  · 실격 사건은 **T0 를 앞으로 당긴다**(누적을 0 으로 되돌린다)
  · 재고정은 연속 창을 끊지만 누적은 잇는다
"""

from __future__ import annotations

import itertools
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# `SessionDeactivationReason` 에서 `user_stopped` 를 뺀 것 = **자동 사망**.
# 정본은 `backend/src/trading/models.py:107-142`. 여기에 하드코딩하는 이유는 이 모듈이
# 앱 코드를 import 하지 않는 순수 함수이기 때문이다 — 어긋나면
# `tests/scripts/test_soak_gate_predicate.py` 가 정본과 대조해 실패시킨다.
AUTOMATIC_DEATH_REASONS: frozenset[str] = frozenset(
    {
        "coverage_unrunnable",
        "degraded_unconsented",
        "equity_baseline_missing",
        "equity_exhausted",
        "run_live_error",
        "runtime_divergence",
        "gap_resync_position_mismatch",
        "position_divergence",
    }
)

# 유도 계측이 「판정 불가」로 떨어지는 outcome 들. 보고 전용 — 문턱 없음.
# 정본은 `backend/src/common/metrics.py:802-811`.
UNDECIDABLE_DERIVE_OUTCOMES: frozenset[str] = frozenset(
    {"overflow", "foreign_fill", "close_without_open", "duplicate_open", "unreadable"}
)

DEFAULT_REQUIRE_HOURS = 168.0
DEFAULT_REQUIRE_CONTINUOUS_HOURS = 24.0
DEFAULT_TICK_BARS = 4  # 1봉은 구조적 지연(봉이 닫혀야 평가한다) + 연속 3봉 결손 = 정체
DEFAULT_MAX_SAMPLE_GAP_SECONDS = 3600


def parse_ts(raw: str) -> datetime:
    """psql/ISO 혼합 표기를 관대하게 읽는다 (`2026-08-04 15:46:58.529434+00` 포함)."""
    text = raw.strip().replace(" ", "T")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    # `+00` / `-05` 같은 시간대만 있는 꼬리에 분을 채운다
    if len(text) >= 3 and text[-3] in "+-":
        text = text + ":00"
    return datetime.fromisoformat(text)


@dataclass(frozen=True)
class Interval:
    start: datetime
    end: datetime

    @property
    def seconds(self) -> float:
        return max(0.0, (self.end - self.start).total_seconds())

    def clip(self, lo: datetime, hi: datetime) -> Interval | None:
        start = max(self.start, lo)
        end = min(self.end, hi)
        return Interval(start, end) if end > start else None

    def intersect(self, other: Interval) -> Interval | None:
        return self.clip(other.start, other.end)


@dataclass
class Disqualification:
    at: datetime
    kind: str  # auto_death | phantom | tick_stall
    detail: str


@dataclass
class Verdict:
    verdict: str
    reason_word: str
    summary: str
    conditions: dict[str, Any] = field(default_factory=dict)
    detail: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "reason_word": self.reason_word,
            "summary": self.summary,
            "conditions": self.conditions,
            "detail": self.detail,
        }


# ---------------------------------------------------------------- 창 계산


def attribution_intervals(pin_events: list[dict[str, Any]], now: datetime) -> list[Interval]:
    """「어느 커밋이 돌았는지 답할 수 있는」 구간들.

    `up` 이 구간을 열고, 그 다음 어떤 이벤트(`pin`/`up`/`down`)든 닫는다.
    ★`pin` 이 구간을 여는 게 아니다 — 스냅샷을 다시 떠도 **이미 돌고 있는 프로세스**는
    구 모듈을 쥐고 있다. 그래서 `pin` 은 열지 않고 **닫는다**(귀속이 흐려지는 시점이므로).
    """
    events = sorted(pin_events, key=lambda e: parse_ts(str(e["at"])))
    intervals: list[Interval] = []
    open_at: datetime | None = None
    for event in events:
        at = parse_ts(str(event["at"]))
        if open_at is not None and at > open_at:
            intervals.append(Interval(open_at, at))
        open_at = at if str(event.get("event", "")) == "up" else None
    if open_at is not None and now > open_at:
        intervals.append(Interval(open_at, now))
    return intervals


def sha_at(pin_events: list[dict[str, Any]], moment: datetime) -> str | None:
    """그 시각에 떠 있던 고정 커밋."""
    events = sorted(pin_events, key=lambda e: parse_ts(str(e["at"])))
    current: str | None = None
    for event in events:
        if parse_ts(str(event["at"])) > moment:
            break
        current = str(event.get("sha", "")) if str(event.get("event", "")) == "up" else None
    return current


def session_intervals(sessions: list[dict[str, Any]], now: datetime) -> list[tuple[str, Interval]]:
    """세션이 살아 있던 구간. ★판정은 `deactivated_at` — `is_active` 도 `reason` 도 아니다.

    실측 25세션 중 12세션이 `is_active=false` 인데 `deactivated_reason IS NULL` 이었다.
    """
    out: list[tuple[str, Interval]] = []
    for sess in sessions:
        start = parse_ts(str(sess["created_at"]))
        raw_end = sess.get("deactivated_at")
        end = parse_ts(str(raw_end)) if raw_end else now
        if end > start:
            out.append((str(sess["id"]), Interval(start, end)))
    return out


# ---------------------------------------------------------------- 실격 사건


def tick_lag_seconds(sess: dict[str, Any], at: datetime) -> float | None:
    raw = sess.get("last_evaluated_bar_time")
    if not raw:
        return None
    return (at - parse_ts(str(raw))).total_seconds()


def find_disqualifications(
    sessions: list[dict[str, Any]],
    phantom_observations: list[dict[str, Any]],
    samples: list[dict[str, Any]],
    tick_bars: int,
) -> list[Disqualification]:
    """자동 사망 · phantom · tick 정체 — 셋 다 창을 끊고 T0 를 앞으로 당긴다."""
    found: list[Disqualification] = []

    for sess in sessions:
        reason = sess.get("deactivated_reason")
        dead_at = sess.get("deactivated_at")
        if reason and str(reason) in AUTOMATIC_DEATH_REASONS and dead_at:
            found.append(
                Disqualification(parse_ts(str(dead_at)), "auto_death", f"{sess['id'][:8]} {reason}")
            )

    for obs in phantom_observations:
        if str(obs.get("label", "")) == "phantom":
            found.append(
                Disqualification(
                    parse_ts(str(obs["at"])),
                    "phantom",
                    f"{str(obs.get('session_id', ''))[:8]} phantom",
                )
            )

    found.extend(_tick_stalls(sessions, samples, tick_bars))
    found.sort(key=lambda d: d.at)
    return found


def _tick_stalls(
    sessions: list[dict[str, Any]],
    samples: list[dict[str, Any]],
    tick_bars: int,
) -> list[Disqualification]:
    """평가가 멈춘 구간.

    ★「lag 이 크다」만으로 판정하지 않는다 — 재기동 직후에는 정상적으로 뒤처져 있다가
    **따라잡는다**. 따라서 정체 = 「lag 이 문턱을 넘었고 **bar time 이 전진하지 않았다**」다.
    표본이 없는 과거 세션은 종단 lag 만으로 판정한다(따라잡던 중이었을 가능성은 남는다 —
    그래서 이 판정은 **과대계상 쪽으로만** 틀린다).
    """
    stalls: list[Disqualification] = []

    # ① 표본 사이 정체 — 연속 두 표본에서 bar time 이 그대로이고 lag 이 문턱 초과
    by_session: dict[str, list[tuple[datetime, str | None]]] = {}
    for sample in samples:
        at = parse_ts(str(sample["at"]))
        for row in sample.get("sessions", []):
            raw = row.get("last_evaluated_bar_time")
            by_session.setdefault(str(row["id"]), []).append((at, str(raw) if raw else None))

    interval_of = {str(s["id"]): int(s.get("interval_seconds", 60)) for s in sessions}
    for sid, points in by_session.items():
        limit = tick_bars * interval_of.get(sid, 60)
        points.sort(key=lambda p: p[0])
        for (prev_at, prev_bar), (cur_at, cur_bar) in itertools.pairwise(points):
            if prev_bar is None or cur_bar is None or prev_bar != cur_bar:
                continue
            if (cur_at - parse_ts(cur_bar)).total_seconds() > limit:
                stalls.append(
                    Disqualification(
                        cur_at,
                        "tick_stall",
                        f"{sid[:8]} bar time 정지 {prev_at.isoformat()}~{cur_at.isoformat()}",
                    )
                )
                break  # 세션당 1건이면 창을 끊기에 충분하다

    # ② 종단 lag — 세션이 **끝난** 시점에 얼마나 뒤처져 있었나
    #
    # ★살아 있는 세션에는 적용하지 않는다. 재기동 직후에는 정상적으로 여러 봉 뒤처졌다가
    #   한 봉씩 따라잡으므로(실측 2026-08-04: 5봉 뒤처짐 → 정상 복귀), 그 순간을 찍으면
    #   **거짓 실격**이 되고 실격은 누적을 0 으로 되돌린다. 살아 있는 세션은 ①(연속 두 표본에서
    #   bar time 이 얼어붙음)로만 판정한다 — 그쪽은 따라잡는 중을 구조적으로 통과시킨다.
    for sess in sessions:
        raw_end = sess.get("deactivated_at")
        if not raw_end:
            continue
        sid = str(sess["id"])
        end = parse_ts(str(raw_end))
        limit = tick_bars * int(sess.get("interval_seconds", 60))
        lag = tick_lag_seconds(sess, end)
        if lag is None:
            # 한 번도 평가되지 않았다 — 세션이 문턱보다 오래 살았다면 정체다
            if (end - parse_ts(str(sess["created_at"]))).total_seconds() > limit:
                stalls.append(Disqualification(end, "tick_stall", f"{sid[:8]} 평가 기록 없음"))
            continue
        if lag > limit and not _catching_up(by_session.get(sid, [])):
            stalls.append(
                Disqualification(end, "tick_stall", f"{sid[:8]} 종단 lag {lag / 60:.1f}분")
            )
    return stalls


def _catching_up(points: list[tuple[datetime, str | None]]) -> bool:
    """마지막 두 표본에서 bar time 이 전진했으면 따라잡는 중이다(정체가 아니다)."""
    usable = [p for p in points if p[1] is not None]
    if len(usable) < 2:
        return False
    usable.sort(key=lambda p: p[0])
    return parse_ts(str(usable[-1][1])) > parse_ts(str(usable[-2][1]))


# ---------------------------------------------------------------- 표본·커버리지


def restrict(target: Interval, coverage: list[Interval]) -> list[Interval]:
    """`target` 중 `coverage` 가 실제로 덮는 부분만 남긴다.

    ★boolean 이 아니라 **자르기**인 이유 — 워커 로그의 마지막 줄은 언제나 `now` 보다 조금
    앞선다(celery 가 매초 찍지 않는다). boolean 이면 그 수십 초 때문에 매번 UNKNOWN 이 되고,
    허용 오차를 두면 그만큼이 **검증 없이 credit** 된다. 자르면 둘 다 안 생긴다 —
    **증명된 시간만 센다.**
    """
    out: list[Interval] = []
    for iv in sorted(coverage, key=lambda i: i.start):
        piece = target.intersect(iv)
        if piece is not None:
            out.append(piece)
    return _merge(out)


def _merge(intervals: list[Interval]) -> list[Interval]:
    merged: list[Interval] = []
    for iv in sorted(intervals, key=lambda i: i.start):
        if merged and iv.start <= merged[-1].end:
            merged[-1] = Interval(merged[-1].start, max(merged[-1].end, iv.end))
        else:
            merged.append(iv)
    return merged


def sample_gaps(samples: list[dict[str, Any]], window: Interval, limit: float) -> list[str]:
    """창 안에서 표본이 `limit` 초보다 드물었던 구간. 있으면 C4 를 판정할 수 없다."""
    times = sorted(parse_ts(str(s["at"])) for s in samples)
    inside = [t for t in times if window.start <= t <= window.end]
    gaps: list[str] = []
    cursor = window.start
    for t in inside:
        if (t - cursor).total_seconds() > limit:
            gaps.append(f"{cursor.isoformat()}~{t.isoformat()}")
        cursor = t
    if (window.end - cursor).total_seconds() > limit:
        gaps.append(f"{cursor.isoformat()}~{window.end.isoformat()}")
    return gaps


# ---------------------------------------------------------------- 판정


def evaluate(payload: dict[str, Any]) -> Verdict:
    now = parse_ts(str(payload["now"]))
    sessions: list[dict[str, Any]] = payload.get("sessions", [])
    pin_events: list[dict[str, Any]] = payload.get("pin_events", [])
    phantoms: list[dict[str, Any]] = payload.get("phantom_observations", [])
    samples: list[dict[str, Any]] = payload.get("samples", [])
    thresholds: dict[str, Any] = payload.get("thresholds", {})

    require_hours = float(thresholds.get("require_hours", DEFAULT_REQUIRE_HOURS))
    require_continuous = float(
        thresholds.get("require_continuous_hours", DEFAULT_REQUIRE_CONTINUOUS_HOURS)
    )
    tick_bars = int(thresholds.get("tick_bars", DEFAULT_TICK_BARS))
    max_gap = float(thresholds.get("max_sample_gap_seconds", DEFAULT_MAX_SAMPLE_GAP_SECONDS))

    disq = find_disqualifications(sessions, phantoms, samples, tick_bars)

    # ── 평가 창의 시작 ──────────────────────────────────────────────────────
    override = payload.get("since")
    if override:
        window_start = parse_ts(str(override))
    elif disq:
        window_start = disq[-1].at
    elif sessions:
        window_start = min(parse_ts(str(s["created_at"])) for s in sessions)
    else:
        window_start = now

    # ── 귀속 가능한 clean 창 ────────────────────────────────────────────────
    # 창 = 「세션 활성」 ∩ 「고정 커밋 불변」 ∩ 「T0 이후」 ∩ **「phantom 관측이 덮은 구간」**.
    # 마지막 조건이 자르기인 이유는 `restrict()` docstring 참조 — 증명된 시간만 센다.
    log_coverage = [
        Interval(parse_ts(str(c["from"])), parse_ts(str(c["to"])))
        for c in payload.get("log_coverage", [])
    ]
    attribution = attribution_intervals(pin_events, now)

    # ── C3 — 실격 사건 ──────────────────────────────────────────────────────
    #
    # ★기본 실행에서는 **지금 열려 있는 귀속 구간 안**의 사건만 본다.
    #   「`d.at > window_start`」로 두면 `window_start` 가 곧 마지막 사건 시각이라
    #   **기본 실행이 FAIL 을 낼 수 없다** — 방금 죽었는데 조용히 0 으로 리셋된다
    #   (실측 2026-08-04: 소크가 38분 만에 죽었는데 판정이 `UNKNOWN 진행중` 이었다).
    #   지금 도는 구간 안의 사건은 **운영자가 스택을 다시 올릴 때까지** FAIL 로 남는다 —
    #   재기동이 곧 「인지했고 새 창을 연다」는 명시적 행위다.
    # ★`--since` 로 창을 강제한 회고 실행에서는 그 창 전체를 본다(다른 질문이다).
    open_window = attribution[-1] if attribution and attribution[-1].end == now else None
    if override:
        violations = [d for d in disq if window_start <= d.at <= now]
    elif open_window is not None:
        violations = [d for d in disq if open_window.start <= d.at <= open_window.end]
    else:
        violations = []

    clean: list[dict[str, Any]] = []
    attributed_seconds = 0.0
    for sid, s_iv in session_intervals(sessions, now):
        for a_iv in attribution:
            inter = s_iv.intersect(a_iv)
            if inter is None:
                continue
            clipped = inter.clip(window_start, now)
            if clipped is None:
                continue
            attributed_seconds += clipped.seconds
            for verified in restrict(clipped, log_coverage):
                clean.append(
                    {
                        "session": sid[:8],
                        "sha": (sha_at(pin_events, verified.start) or "")[:12],
                        "from": verified.start.isoformat(),
                        "to": verified.end.isoformat(),
                        "hours": round(verified.seconds / 3600.0, 4),
                        "_iv": verified,
                    }
                )

    # ★합산은 **원본 초**로 한다 — 표시용으로 반올림한 `hours` 를 더하면 창이 늘수록
    #   오차가 쌓인다(4자리 = 창당 최대 0.18초).
    cumulative_hours = sum(c["_iv"].seconds for c in clean) / 3600.0
    longest_hours = max((c["_iv"].seconds for c in clean), default=0.0) / 3600.0
    unverified_hours = max(0.0, attributed_seconds / 3600.0 - cumulative_hours)

    # ── 귀속 불가 시간 (보고 전용 — 절대 C1 에 더하지 않는다) ───────────────
    unattributed = 0.0
    for _, s_iv in session_intervals(sessions, now):
        covered = sum((s_iv.intersect(a) or Interval(now, now)).seconds for a in attribution)
        unattributed += max(0.0, s_iv.seconds - covered)

    # ── C5 측정 무결성 ──────────────────────────────────────────────────────
    # ★phantom 커버리지는 여기 없다 — boolean 이 아니라 **자르기**로 강제된다(위 clean 계산).
    #   덮이지 않은 시간은 「위반」이 되는 게 아니라 **애초에 안 세어진다.** 구조적 방어가
    #   문턱보다 강하다. 대신 잘려나간 양을 `unverified_hours` 로 **보고**한다.
    darkness = payload.get("darkness")
    integrity: dict[str, Any] = {
        "db_ok": bool(payload.get("db_ok", False)),
        "stack_pinned": bool(payload.get("stack_pinned", False)),
        "phantom_archive": bool(log_coverage),
        "darkness_computed": darkness is not None,
    }

    # ── C4 표본 공백 (귀속 창 안에서만 묻는다) ──────────────────────────────
    gaps: list[str] = []
    for entry in clean:
        gaps.extend(sample_gaps(samples, entry["_iv"], max_gap))
    for entry in clean:
        entry.pop("_iv", None)

    conditions = {
        "C1_cumulative_hours": round(cumulative_hours, 4),
        "C1_required": require_hours,
        "C1_ok": cumulative_hours >= require_hours,
        "C2_longest_hours": round(longest_hours, 4),
        "C2_required": require_continuous,
        "C2_ok": longest_hours >= require_continuous,
        "C3_violations": [f"{d.at.isoformat()} {d.kind} {d.detail}" for d in violations],
        "C3_ok": not violations,
        "C4_sample_gaps": gaps,
        "C4_ok": not gaps,
        "C5": integrity,
        "C5_ok": all(integrity.values()),
    }
    detail = {
        "window_start": window_start.isoformat(),
        "now": now.isoformat(),
        "windows": clean,
        "unattributed_hours": round(unattributed / 3600.0, 4),
        "unverified_hours": round(unverified_hours, 4),
        "disqualifications_all_time": [f"{d.at.isoformat()} {d.kind} {d.detail}" for d in disq],
        "darkness": _darkness_report(darkness),
        "thresholds_are_default": (
            require_hours == DEFAULT_REQUIRE_HOURS
            and require_continuous == DEFAULT_REQUIRE_CONTINUOUS_HOURS
        ),
    }

    if violations:
        first = violations[0]
        return Verdict(
            "FAIL",
            "실격",
            f"실격 사건 {len(violations)}건 — 최초 {first.at.isoformat()} {first.kind} ({first.detail}). T0 가 앞으로 당겨지고 누적이 0 으로 리셋된다.",
            conditions,
            detail,
        )

    if not conditions["C5_ok"]:
        missing = [k for k, v in integrity.items() if not v]
        return Verdict(
            "UNKNOWN",
            "측정불가",
            f"측정 무결성 미충족: {', '.join(missing)}",
            conditions,
            detail,
        )

    if gaps:
        return Verdict(
            "UNKNOWN",
            "측정불가",
            f"표본 공백 {len(gaps)}건 (한계 {max_gap / 60:.0f}분) — 그 구간은 tick 연속성을 판정할 수 없다. 최초: {gaps[0]}",
            conditions,
            detail,
        )

    if not conditions["C1_ok"] or not conditions["C2_ok"]:
        pct = (cumulative_hours / require_hours * 100.0) if require_hours else 0.0
        return Verdict(
            "UNKNOWN",
            "진행중",
            f"누적 {cumulative_hours:.2f}h / {require_hours:.0f}h ({pct:.1f}%) · 최장 연속 {longest_hours:.2f}h / {require_continuous:.0f}h · 실격 0",
            conditions,
            detail,
        )

    return Verdict(
        "PASS",
        "",
        f"누적 {cumulative_hours:.2f}h ≥ {require_hours:.0f}h · 최장 연속 {longest_hours:.2f}h ≥ {require_continuous:.0f}h · 실격 0 · 측정 무결",
        conditions,
        detail,
    )


def _darkness_report(darkness: Any) -> Any:
    if not isinstance(darkness, dict):
        return None
    total = float(darkness.get("total", 0) or 0)
    undecidable = float(darkness.get("undecidable", 0) or 0)
    return {
        "undecidable": undecidable,
        "total": total,
        "ratio": round(undecidable / total, 4) if total else None,
        "note": "보고 전용 — 문턱 없음 (사용자 확정 2026-08-05)",
    }


def main() -> int:
    payload = json.load(sys.stdin)
    verdict = evaluate(payload)
    json.dump(verdict.to_json(), sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if verdict.verdict == "PASS" else (1 if verdict.verdict == "FAIL" else 2)


if __name__ == "__main__":
    raise SystemExit(main())
