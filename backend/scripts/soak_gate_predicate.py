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

# ── 방향 발산 라벨 어휘 ([BL-596]) ────────────────────────────────────────────
#
# 분류기(`backend/scripts/classify_direction_divergence.py`)가 내는 `verdicts[].label`
# 은 **셋뿐**이고, 게이트는 그 셋을 여기서 **명시적으로** 가른다. 예전에는
# `label == "phantom"` 하나만 보고 나머지를 전부 무해로 접었다 — 곧 `unattributed` 도,
# 판별식이 앞으로 낼 어떤 새 라벨도 조용히 무해였다. 방향이 **fail-open** 이다:
# 실격을 놓치면 `window_start` 가 앞당겨져 누적이 늘고 [BL-003] 통과가 쉬워진다.
# 판별식은 2026-08-05 하루에만 두 번 바뀌었으므로(봉경계식 → 재무장식 → 회복식)
# 「어휘는 안 변한다」는 가정을 코드에 둘 수 없다.
#
# ★셋째 갈래(`UNDECIDABLE` ∪ 어휘 밖)는 **무해도 실격도 아니다** — 「그게 유령이었는지
#   우리가 모른다」이므로 C5(측정 무결성)를 떨어뜨려 UNKNOWN 으로 간다. 소급 실격이
#   아닌 이유: 모르는 것을 실격으로 세면 그건 다른 방향의 거짓말이다.
HARMLESS_DIVERGENCE_LABELS: frozenset[str] = frozenset({"replay_lag"})
DISQUALIFYING_DIVERGENCE_LABELS: frozenset[str] = frozenset({"phantom"})
# 「판정하지 못했다」 — 세션 소유 체결이 없어(운영자 청산 등) 어느 식도 판정을 못 한 것.
# ★무해로 접으면 그 발산은 아무 데도 안 잡힌다. 어휘 밖 라벨과 **같은 갈래**로 떨어지되
#   보고에서는 갈라 보인다 — 조치가 다르기 때문이다(어휘 밖 = 게이트를 분류기에 맞춰라 /
#   `unattributed` = 그 발산을 사람이 봐야 한다).
UNDECIDABLE_DIVERGENCE_LABELS: frozenset[str] = frozenset({"unattributed"})
KNOWN_DIVERGENCE_LABELS: frozenset[str] = (
    HARMLESS_DIVERGENCE_LABELS | DISQUALIFYING_DIVERGENCE_LABELS | UNDECIDABLE_DIVERGENCE_LABELS
)
# 판독 불가 라벨의 출처를 라벨당 몇 건까지 보고하나. 총계는 `count` 로 따로 낸다 —
# 아카이브가 매 실행마다 로그 전량을 재분류하므로 같은 관측이 수백 건으로 불어난다.
MAX_UNREADABLE_LABEL_SAMPLES = 5

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
        label = str(obs.get("label", ""))
        if label in DISQUALIFYING_DIVERGENCE_LABELS:
            found.append(
                Disqualification(
                    parse_ts(str(obs["at"])),
                    label,
                    f"{str(obs.get('session_id', ''))[:8]} {label}",
                )
            )

    found.extend(_tick_stalls(sessions, samples, tick_bars))
    # 같은 사건이 여러 아카이브에 중복 보존된다(매 실행이 로그 전량을 다시 분류한다).
    # 판정에는 영향이 없지만 목록이 부풀어 읽는 사람을 속인다 — 여기서 접는다.
    deduped: dict[tuple[datetime, str, str], Disqualification] = {}
    for d in found:
        deduped.setdefault((d.at, d.kind, d.detail), d)
    return sorted(deduped.values(), key=lambda d: d.at)


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


def sample_gaps(
    samples: list[dict[str, Any]], window: Interval, limit: float, session_id: str
) -> list[str]:
    """그 **세션에 대해** 표본이 `limit` 초보다 드물었던 구간. 있으면 C4 를 판정할 수 없다.

    ★세션을 안 보고 표본 시각만 세면 안 된다 — 활성 세션 조회가 실패해 `sessions: []` 로
    기록된 빈 표본이 **모든 세션의 공백을 메운다**(codex P1). 표본은 그 세션의 row 를
    담고 있을 때만 그 세션에 대한 증거다.
    """
    times = sorted(
        parse_ts(str(s["at"]))
        for s in samples
        if any(str(r.get("id", "")) == session_id for r in s.get("sessions", []))
    )
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


def unreadable_labels(observations: list[dict[str, Any]]) -> dict[str, Any]:
    """무해(`replay_lag`)도 실격(`phantom`)도 아닌 라벨을 두 갈래로 갈라 돌려준다 ([BL-596]).

    ★**라벨 이름만으로는 조치를 못 고른다** — 어휘 밖 라벨이면 frozenset 을 갱신해야 하고,
    구판 아카이브가 남긴 것이면 `.soak/superseded-<판>/` 로 옮겨야 하는데 **둘 다 라벨은
    똑같이 「모르는 것」으로 보인다.** 그래서 `sources` 에 **어느 아카이브 · 어느 판 · 언제 ·
    어느 세션**을 같이 낸다(`scripts/soak-gate.sh` 가 합병 때 붙인다). 없는 필드는 뺀다 —
    손으로 만든 payload 나 옛 아카이브에는 출처가 없을 수 있다.
    ★폭주 방지: 라벨당 표본 `MAX_UNREADABLE_LABEL_SAMPLES` 건 + `count` 로 총계.

    ★**창으로 좁히지 않는다 — 코퍼스 전량을 본다.** 판독 못 하는 라벨의 위험은 「지금 창
    안에서 FAIL 을 놓친다」만이 아니다. `window_start` 는 **전 이력의 마지막 실격 시각**이고
    (`evaluate` 의 T0 계산), 기본 실행의 위반 스캔은 `window_start` **이전**으로도 뻗는다
    (열려 있는 귀속 구간 전체). 그래서 창 밖의 한 건이라도 실은 `phantom` 이었다면 T0 가
    앞당겨진 채 계산된다 — 좁히면 fail-open 이 그대로 남는다.

    ★결과적으로 한 건만 나와도 게이트는 그 아카이브가 정리될 때까지 UNKNOWN 에 머문다.
      그게 의도다 — 어휘가 갈렸다는 것은 **사람이 게이트를 분류기에 맞춰야 한다**는 뜻이고,
      해소 경로는 둘 다 이미 있다: 위 frozenset 에 라벨을 제 갈래로 등재하거나, 옛 판의
      아카이브를 `.soak/superseded-<판>/` 로 옮긴다([ADR-024] §아카이브 판).
    """
    sources: dict[str, dict[str, Any]] = {}
    for obs in observations:
        label = str(obs.get("label", ""))
        if label in HARMLESS_DIVERGENCE_LABELS or label in DISQUALIFYING_DIVERGENCE_LABELS:
            continue
        entry = sources.setdefault(label, {"count": 0, "samples": []})
        entry["count"] += 1
        if len(entry["samples"]) < MAX_UNREADABLE_LABEL_SAMPLES:
            sample = {
                "archive": obs.get("archive"),
                "predicate_version": obs.get("predicate_version"),
                "at": obs.get("at"),
                "session": str(obs.get("session_id", ""))[:8] or None,
            }
            entry["samples"].append({k: v for k, v in sample.items() if v})
    seen = set(sources)
    return {
        "undecidable": sorted(seen & UNDECIDABLE_DIVERGENCE_LABELS),
        "unknown": sorted(seen - KNOWN_DIVERGENCE_LABELS),
        "sources": {label: sources[label] for label in sorted(sources)},
    }


def first_source_note(buckets: dict[str, Any]) -> str:
    """요약 줄에 붙일 **첫 출처 한 건**. 나머지는 `detail.divergence_labels` 에 있다."""
    for label in buckets["undecidable"] + buckets["unknown"]:
        entry = buckets["sources"].get(label, {})
        samples = entry.get("samples") or []
        if not samples:
            continue
        first = samples[0]
        where = " ".join(
            str(first[k]) for k in ("archive", "predicate_version", "at", "session") if first.get(k)
        )
        tail = f", 총 {entry['count']}건" if entry.get("count", 0) > 1 else ""
        return f" 첫 출처: {where}{tail}"
    return ""


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
    # ★분류기가 **성공한** 아카이브만 커버리지로 인정한다.
    #   분류기가 깨져도(의존성·DB·인자) 껍데기 JSON 은 만들어지고 verdicts 는 빈 배열이 된다.
    #   그걸 커버리지로 받으면 「phantom 0건 + 검증된 로그」로 읽혀 그 시간이 credit 되고
    #   진짜 phantom 도 숨는다 — 정확히 fail-open 이다(codex P1). 실제로 이 회차에서 시스템
    #   python3 로 돌려 verdicts 가 늘 0 이었던 전례가 있다.
    log_coverage = [
        Interval(parse_ts(str(c["from"])), parse_ts(str(c["to"])))
        for c in payload.get("log_coverage", [])
        if c.get("classifier_ok") is True
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

    # ★실격 사건 **이후에 열린** 귀속 구간만 센다.
    #   실격 시점에 이미 열려 있던 구간은 「인지 전」이다 — 그 시간을 credit 하면 운영자가
    #   사망을 알아채기 전까지 흐른 시간이 PASS 누적에 들어간다(codex P1). 새 창을 여는
    #   `soak-stack.sh up` 이 곧 인지 행위이므로, **그 뒤에 시작한 구간**만 유효하다.
    countable = [a for a in attribution if a.start >= window_start]

    # ★귀속 구간별로 **합집합**을 낸다 — 세션을 그냥 합산하면 동시 활성 세션 2개가
    #   84시간 만에 168h 를 만든다(user 당 active ≤ 5 이므로 실제로 도달 가능하다, codex P1).
    #   구간을 넘나드는 병합은 하지 않는다 — 재고정 경계를 지워 연속 창을 부풀린다.
    sess_ivs = session_intervals(sessions, now)
    clean: list[dict[str, Any]] = []
    per_attribution_verified: list[list[Interval]] = []
    per_attribution_all: list[list[Interval]] = []

    for a_iv in countable:
        attributed_pieces: list[Interval] = []
        verified_pieces: list[Interval] = []
        for sid, s_iv in sess_ivs:
            inter = s_iv.intersect(a_iv)
            if inter is None:
                continue
            clipped = inter.clip(window_start, now)
            if clipped is None:
                continue
            attributed_pieces.append(clipped)
            for verified in restrict(clipped, log_coverage):
                verified_pieces.append(verified)
                clean.append(
                    {
                        "session": sid[:8],
                        "sha": (sha_at(pin_events, verified.start) or "")[:12],
                        "from": verified.start.isoformat(),
                        "to": verified.end.isoformat(),
                        "hours": round(verified.seconds / 3600.0, 4),
                        "_iv": verified,
                        "_sid": sid,
                    }
                )
        per_attribution_all.append(_merge(attributed_pieces))
        per_attribution_verified.append(_merge(verified_pieces))

    merged = [iv for group in per_attribution_verified for iv in group]
    cumulative_hours = sum(iv.seconds for iv in merged) / 3600.0
    longest_hours = max((iv.seconds for iv in merged), default=0.0) / 3600.0
    attributed_hours = sum(iv.seconds for group in per_attribution_all for iv in group) / 3600.0
    unverified_hours = max(0.0, attributed_hours - cumulative_hours)

    # ── 귀속 불가 시간 (보고 전용 — 절대 C1 에 더하지 않는다) ───────────────
    unattributed = 0.0
    for _, s_iv in session_intervals(sessions, now):
        covered = sum((s_iv.intersect(a) or Interval(now, now)).seconds for a in attribution)
        unattributed += max(0.0, s_iv.seconds - covered)

    # ── C5 측정 무결성 ──────────────────────────────────────────────────────
    # ★phantom 커버리지는 여기 없다 — boolean 이 아니라 **자르기**로 강제된다(위 clean 계산).
    #   덮이지 않은 시간은 「위반」이 되는 게 아니라 **애초에 안 세어진다.** 구조적 방어가
    #   문턱보다 강하다. 대신 잘려나간 양을 `unverified_hours` 로 **보고**한다.
    #
    # ★`aof_ok` = redis 가 **지금 재기동하면 뜨는가** ([BL-594]). healthcheck 는 떠 있는
    #   프로세스에만 묻고 AOF 는 기동 시에만 읽히므로, 「살아 있다」는 재기동 가능의 증거가
    #   아니다(실측 2026-08-05: 판독 불가 AOF 위에서 6일 연속 가동). 창 안에 재부팅이 들어오면
    #   그때 워커가 안 뜬다 — 168h 짜리 달력 시간에 직접 걸린다.
    #   ★키 부재는 `False` 다 — 수집이 죽었는데 초록으로 남으면 fail-open 이다.
    darkness = payload.get("darkness")
    # ★라벨 어휘는 **여기**에 건다 ([BL-596]) — 무해도 실격도 아닌 셋째 갈래이므로.
    #   실격으로 세면 「모른다」를 「유령이었다」로 바꾸는 것이고, 무해로 접으면 fail-open 이다.
    #   판정 순서상 FAIL 이 C5 보다 먼저라(아래) **진짜 실격을 UNKNOWN 으로 덮지 않는다** = 래칫.
    label_buckets = unreadable_labels(phantoms)
    integrity: dict[str, Any] = {
        "db_ok": bool(payload.get("db_ok", False)),
        "stack_pinned": bool(payload.get("stack_pinned", False)),
        "phantom_archive": bool(log_coverage),
        "darkness_computed": darkness is not None,
        # ★두 라벨 목록만 본다 — `any(values())` 로 쓰면 `sources` 같은 보고용 항이 늘 때
        #   판정이 조용히 따라 움직인다.
        "divergence_labels_readable": not (
            label_buckets["undecidable"] or label_buckets["unknown"]
        ),
        "aof_ok": bool(payload.get("aof_ok", False)),
    }

    # ── C4 표본 공백 (귀속 창 안에서만, **세션별로** 묻는다) ────────────────
    gaps: list[str] = []
    for entry in clean:
        gaps.extend(sample_gaps(samples, entry["_iv"], max_gap, str(entry["_sid"])))
    for entry in clean:
        entry.pop("_iv", None)
        entry.pop("_sid", None)

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
        "divergence_labels": label_buckets,
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
        # 라벨은 키 이름만으로 알 수 없다 — 어느 라벨인지가 곧 다음 조치다(위 frozenset 등재 vs 사람 조사).
        # `label` 키 자체가 없는 옛 아카이브는 `""` 로 읽힌다 — 빈 낱말로 찍지 않는다.
        unreadable = label_buckets["undecidable"] + label_buckets["unknown"]
        offending = [lab or "(라벨 없음)" for lab in unreadable]
        suffix = (
            f" (판독 불가 라벨: {', '.join(offending)}.{first_source_note(label_buckets)})"
            if offending
            else ""
        )
        return Verdict(
            "UNKNOWN",
            "측정불가",
            f"측정 무결성 미충족: {', '.join(missing)}{suffix}",
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
