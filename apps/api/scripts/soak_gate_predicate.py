"""[BL-003] 「데모 1주 안정 운영」 게이트의 **순수 판정 함수**.

★C1 문턱 = **≥24h 연속 무실격 창 3회** (2026-08-11 [BL-701] 이 「누적 168h」에서 교체).
  누적 시간은 계속 보고하지만 **판정에 쓰지 않는다** — 아래 상수 주석 참조.

stdin 으로 JSON 을 받아 stdout 으로 JSON 판정을 낸다. **I/O 도 DB 도 docker 도 없다** —
수집은 `scripts/soak-gate.sh` 가 하고 여기는 계산만 한다. 그래야 같은 입력을 손으로 더한
값과 대조할 수 있다(판정기가 자기 값을 스스로 검증하면 순환이다).

낱말은 셋뿐이다 — **PASS / FAIL / UNKNOWN**. ★UNKNOWN 을 PASS 로 접지 않는다.

  PASS     C1~C5 전부 충족
  FAIL     평가 창 안에서 **실격 사건**을 관측했다 (자동 사망 · phantom · tick 정체)
  UNKNOWN  그 외 전부. 사유 낱말로 두 갈래를 구분한다:
             `진행중`   — 측정은 됐는데 시간이 모자라다
             `측정불가` — 잴 수 없었다 (C5 위반 · 표본 공백)

★창(window)과 리셋 규칙이 정의의 절반이다 — `docs/adr/024-soak-stability-gate.md` §창.
  · 창 = 「라이브 세션 활성」 ∩ 「고정 커밋 불변」 을 동시에 만족하는 최대 구간
  · **고정되지 않은 스택은 미계상** — 어느 커밋이 돌았는지 답할 수 없으면 그 시간은 못 센다
  · 실격 사건은 **T0 를 앞으로 당긴다**(누적을 0 으로 되돌린다)
  · 재고정은 연속 창을 끊지만 누적은 잇는다
"""

from __future__ import annotations

import itertools
import json
import re
import statistics
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# `.` 뒤 숫자열 = 마이크로초. 날짜는 `-`, 시각은 `:` 로 갈리므로 첫 매치가 유일하다.
_FRAC_RE = re.compile(r"\.(\d+)")

# `SessionDeactivationReason` 에서 **사람·행정 사유**를 뺀 것 = **자동 사망**.
# 정본은 `apps/api/src/trading/models.py` 의 `SessionDeactivationReason`. 여기에 하드코딩하는
# 이유는 이 모듈이 앱 코드를 import 하지 않는 순수 함수이기 때문이다 — 어긋나면
# `tests/scripts/test_soak_gate_predicate.py` 가 정본과 대조해 실패시킨다.
#
# ★제외 목록은 **둘**이다 (2026-08-15 surface-truth):
#   `user_stopped`     — 사람이 Stop 을 눌렀다
#   `account_deleted`  — 탈퇴 웹훅이 소유자의 세션을 전량 내렸다
# 자동 사망은 「엔진·거래소 축이 스스로 무너졌다」를 세는 축이고 그것이 C3 실격의 정의다.
# 행정 이벤트를 여기 넣으면 **소크 창이 거짓으로 리셋**된다 — 탈퇴 한 건이 벌어 둔 시간을
# 통째로 지우고, 그 리셋은 원장에 「엔진이 죽었다」로 남는다.
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
# 분류기(`apps/api/scripts/classify_direction_divergence.py`)가 내는 `verdicts[].label`
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
# 정본은 `apps/api/src/common/metrics.py:802-811`.
UNDECIDABLE_DERIVE_OUTCOMES: frozenset[str] = frozenset(
    {"overflow", "foreign_fill", "close_without_open", "duplicate_open", "unreadable"}
)

# ★C1 의 문턱은 **누적 시간이 아니라 창의 개수**다 (2026-08-11 사용자 결정 · [ADR-024] §C1).
#   종전 `C1 ≥ 168h` 는 실질적으로 「168시간 연속 무실격」이었고(실격이 창을 리셋한다)
#   P(그 사건) = 4.115e-09 였다 — 39세션 중 24h 도달 0건. **P0 이 영구히 안 닫히는 문턱**이다.
#   새 문턱 = 「`require_continuous_hours` 이상인 연속 무실격 창을 N회 달성」.
# ★N=3 은 `[가정]`이다 ([ADR-024] §C1 Superseded 블록) — 근거가 생기면 여기만 바꾼다.
# ★창의 단위는 **C2 가 재는 것과 같다**(귀속 구간별 병합 후의 interval). 두 축이 같은 단위를
#   쓰므로 C2 = 「그런 창이 1개 이상」, C1 = 「3개 이상」이 된다. 단위를 갈라놓으면 같은
#   게이트가 두 가지 「창」을 말하게 된다.
DEFAULT_REQUIRE_WINDOWS = 3
# ★아래는 **참고 전용**이다 — 더 이상 C1 의 문턱이 아니다. 누적 시간은 계속 보고한다
#   (창이 얼마나 쌓였는지는 여전히 읽을 값이다). 판정에 쓰지 마라.
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
    # ★소수점 이하를 정확히 6자리로 맞춘다. Postgres 는 뒤 0 을 지워 `.79648`(5자리)로 내보내는데
    # `fromisoformat` 이 임의 자릿수를 받아주기 시작한 것은 **Python 3.11** 부터다. 3.10 은
    # 3자리/6자리만 허용해 ValueError 로 죽는다 — 게이트가 조용히 3.11+ 전용이었다
    # (2026-08-07 실측: 맥 3.14.6 통과 / Ubuntu 22.04 의 3.10.12 크래시).
    # 날짜는 `-`, 시각은 `:` 로 갈리므로 `.` 뒤 숫자는 마이크로초뿐이다.
    text = _FRAC_RE.sub(lambda m: "." + m.group(1)[:6].ljust(6, "0"), text, count=1)
    return datetime.fromisoformat(text)


# ★기대 방향: 이 검사는 PASS 를 더 어렵게 만드는 것이 의도다. 게이트가 덜 재고도 초록에
# 가까워지는 것을 막는다 — 퇴보로 읽고 되돌리지 마라.
def parse_log_coverage(
    entries: list[dict[str, Any]],
) -> tuple[list[Interval], list[dict[str, Any]]]:
    """분류 성공 아카이브만 읽고, 시각을 못 읽은 항목은 따로 돌려준다.

    판독 불가 항목은 커버리지에서 제외해 그 시간을 credit 하지 않는다. 원본 문자열과
    출처는 판정 결과가 운영자에게 실제 수집 고장을 가리키도록 보존한다.
    """
    coverage: list[Interval] = []
    unreadable: list[dict[str, Any]] = []
    for entry in entries:
        if entry.get("classifier_ok") is not True:
            continue
        raw_from = str(entry["from"])
        raw_to = str(entry["to"])
        try:
            coverage.append(Interval(parse_ts(raw_from), parse_ts(raw_to)))
        except ValueError:
            unreadable_entry = {"from": raw_from, "to": raw_to}
            if entry.get("archive"):
                unreadable_entry["archive"] = entry["archive"]
            unreadable.append(unreadable_entry)
    return coverage, unreadable


def summarize_unreadable_log_coverage(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """판독 불가 로그 커버리지의 총계와 중복을 뺀 한정 표본을 만든다."""
    samples: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for entry in entries:
        key = (str(entry["from"]), str(entry["to"]))
        if key in seen:
            continue
        seen.add(key)
        if len(samples) < MAX_UNREADABLE_LABEL_SAMPLES:
            samples.append(entry)
    return {"count": len(entries), "samples": samples}


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
            lag = (cur_at - parse_ts(cur_bar)).total_seconds()
            if lag > limit:
                stalls.append(
                    Disqualification(
                        cur_at,
                        "tick_stall",
                        f"{sid[:8]} bar time 정지 {prev_at.isoformat()}~{cur_at.isoformat()}"
                        f" lag {lag / 60:.1f}분{_resolution_note(lag, _sample_gaps(points))}",
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


def _sample_gaps(points: list[tuple[datetime, str | None]]) -> list[float]:
    """연속 표본 사이의 간격(초). 점이 2개 미만이면 빈 리스트다."""
    ats = sorted(p[0] for p in points)
    return [(b - a).total_seconds() for a, b in itertools.pairwise(ats)]


def _resolution_note(size_seconds: float, gaps: list[float]) -> str:
    """정체 크기 옆에 **그것을 잰 자의 해상도**를 적는다 ([BL-653] 처방 ⑶).

    ★**판정을 바꾸지 않는다 — 거짓 확신만 뺀다.** 실격 여부·건수·귀속은 이 문자열과
    무관하다(귀속 매칭 키는 `(at, kind)` 이고 `detail` 을 보지 않는다).

    이 축이 왜 필요한가 — ① 표본 기반 정체는 「표본을 언제 떴나」에 양자화된다. 2026-08-08
    실측(서버 표본 125건)에서 표본 간격이 **중앙 13.9분 · 최대 31.0분**인데 관측된 정체 크기
    다수가 **31.0분 = 표본 최대 간격과 정확히 일치**했다 — 그 숫자는 현상의 크기가 아니라
    **관측 격자의 크기**다. 크기가 최대 간격의 **2배 미만**이면 그 정체를 가로지르는 표본이
    두 개도 안 되므로 크기는 하한일 뿐이다 ⇒ 「구분 불가」.

    ★②(종단 lag)에는 붙이지 않는다 — 그쪽은 `deactivated_at` 과 `last_evaluated_bar_time`
    **둘 다 DB 값**이라 표본 해상도에 의존하지 않는다. 아무 데나 붙이면 정확한 값까지
    「구분 불가」로 깎아 이 표시 자체가 무의미해진다.
    """
    if not gaps:
        return ""
    biggest = max(gaps)
    ratio = size_seconds / biggest if biggest else 0.0
    tag = ", 구분 불가" if ratio < 2.0 else ""
    return (
        f" (표본 간격 중앙 {statistics.median(gaps) / 60:.1f}분"
        f"/최대 {biggest / 60:.1f}분 · 크기 {ratio:.1f}배{tag})"
    )


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
    # ★[BL-626] — `count` 를 **관측 단위로 dedup 한다.** 매 게이트 실행이 워커 로그 전량을
    #   다시 분류해 `.soak/phantom-*.json` 을 하나씩 더 남기므로, 같은 한 건의 관측이
    #   아카이브 수만큼 들어온다. dedup 없이 세면 `총 N건` 이 **아카이브 개수에 비례해
    #   부풀고**(실측 2026-08-09: 메인 체크아웃에 228벌), 읽는 사람은 「관측이 늘고 있다」로
    #   읽는다. 실격 목록은 원래 `(at, kind, detail)` 로 접히는데(`find_disqualifications`)
    #   이 요약만 안 접혀 있었다 — 같은 코퍼스에서 두 숫자가 어긋난다.
    # ★키에 `archive` 를 넣지 않는다 — 그게 바로 부풀리는 축이다. 세는 것은 **관측**이다.
    counted: dict[str, set[tuple[str, str, str]]] = {}
    for obs in observations:
        label = str(obs.get("label", ""))
        if label in HARMLESS_DIVERGENCE_LABELS or label in DISQUALIFYING_DIVERGENCE_LABELS:
            continue
        entry = sources.setdefault(label, {"count": 0, "samples": []})
        key = (label, str(obs.get("at", "")), str(obs.get("session_id", "")))
        seen_keys = counted.setdefault(label, set())
        if key in seen_keys:
            continue
        seen_keys.add(key)
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


# ---------------------------------------------------------------- 실격 귀속 ([BL-641])
#
# ★★★**이 축은 판정에 참여하지 않는다.** C1~C5 는 원장이 있든 없든 **비트 단위로 같다**.
#   게이트를 관대하게 만드는 변경은 [ADR-024] 가 (f)·(g) 에서 두 번 거부했고 여기서 셋째를
#   만들지 않는다. 원장이 사는 것은 **MTBF 층화의 재현성**이다 — 지금은 창 4개를 사람이 손으로
#   자르고, 그래서 같은 날 안에 낡았다([BL-641] Trigger 「회차마다 재측정」이 그래서 못 지켜진다).
# ★★**반사실 C1(「운영 귀속을 빼면 몇 시간」)은 여기서 내지 않는다.** 낼 수 있는 척하면 다음
#   사람이 그 숫자를 인용하고, 그것이 곧 문턱 완화의 입구다. 반사실은 층화 도구의 몫이다.
# ★★**`undecided` 는 `code_defect` 와 똑같이 다룬다**(엄격 쪽). 등재를 빠뜨려도, 원장이 깨져도,
#   미지 `cause_class` 를 만나도 **관대해지지 않는다** — 이것이 이 축의 fail-open 봉쇄다.
CAUSE_CLASS_LENIENT = "operational"  # 유일하게 「코드 결함이 아니다」를 주장하는 낱말
KNOWN_CAUSE_CLASSES: frozenset[str] = frozenset({"code_defect", CAUSE_CLASS_LENIENT, "undecided"})


def attribute_disqualifications(
    disq: list[Disqualification], ledger: list[dict[str, Any]] | None
) -> dict[str, Any]:
    """실격을 원장의 `cause_class` 로 분류한다 — **보고 전용**.

    매칭 키는 `(at, kind)` 다. `detail` 은 세션 축약이라 판별식이 바뀌면 흔들린다.
    ★매칭된 행은 **꺼낸다**(`pop`) — 남은 행은 「원장에 있는데 실격에는 없는 것」이고,
      그것은 원장이 낡았거나 아카이브가 옮겨졌다는 신호다. 조용히 두면 다음 사람이
      원장을 현행으로 읽는다.
    """
    rows: dict[tuple[datetime, str], str] = {}
    invalid = 0
    for row in ledger or []:
        if not isinstance(row, dict) or "_comment" in row:
            continue
        raw_at, kind, cause = row.get("at"), row.get("kind"), row.get("cause_class")
        if not raw_at or not kind or cause not in KNOWN_CAUSE_CLASSES:
            invalid += 1
            continue
        try:
            at = parse_ts(str(raw_at))
        except ValueError:
            invalid += 1
            continue
        rows[(at, str(kind))] = str(cause)

    counts = dict.fromkeys(sorted(KNOWN_CAUSE_CLASSES), 0)
    unregistered: list[str] = []
    lenient_events: list[str] = []
    for d in disq:
        cause = rows.pop((d.at, d.kind), None)
        if cause is None:
            cause = "undecided"
            unregistered.append(f"{d.at.isoformat()} {d.kind} {d.detail}")
        counts[cause] += 1
        if cause == CAUSE_CLASS_LENIENT:
            lenient_events.append(f"{d.at.isoformat()} {d.kind} {d.detail}")

    return {
        "total": len(disq),
        "counts": counts,
        "operational_events": lenient_events,
        "unregistered": unregistered,
        "stale_ledger_rows": sorted(f"{at.isoformat()} {kind}" for at, kind in rows),
        "invalid_ledger_rows": invalid,
        "note": "보고 전용 — C1~C5 판정에 참여하지 않는다. 미등재·판독 불가는 undecided(엄격 쪽).",
    }


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
    require_windows = int(thresholds.get("require_windows", DEFAULT_REQUIRE_WINDOWS))
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
    log_coverage, unreadable_log_coverage = parse_log_coverage(payload.get("log_coverage", []))
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
    # ★C1 의 새 문턱 — **자격 창의 개수**를 센다 ([ADR-024] §C1, 2026-08-11 사용자 결정).
    #   ★합을 세지 않는 것이 핵심이다: 23.9h 짜리 창 3개는 합이 71.7h 라 「누적」 셈으로는
    #     그럴듯해 보이지만 **한 번도 24h 를 연속으로 버틴 적이 없으므로 0/3** 이다.
    #     그 음성 대조가 이 술어의 판별력이고 테스트로 박혀 있다.
    #   ★★**귀속 구간당 최대 1개**로 센다 — `merged` 를 평평하게 훑으면 안 된다(codex P1).
    #     `restrict()` 가 커버리지 안 덮인 구간을 잘라내므로 **커버리지에 내부 공백이 있으면
    #     하나의 실행이 여러 조각**이 된다. 옛 C1(합)에서는 무해했고 C2(max)에서는 오히려
    #     보수적이었지만, 개수를 세는 순간 그것이 **셈을 부풀린다**: 단일 74h 실행이
    #     `0~24 · 25~49 · 50~74` 커버리지에서 **3회로 위조**돼 PASS 가 났다(재현 테스트 있음).
    #     ⇒ 「측정이 나쁠수록 점수가 오른다」는 fail-open 이고, 문턱의 뜻도 무너진다 —
    #     「3회」는 **세 번의 독립된 생존 시행**이지 한 실행을 관측 공백으로 토막 낸 것이 아니다.
    #     창을 가르는 것은 `down`/`up`·재고정·실격 같은 **운영 사건**이다(= 귀속 구간의 경계).
    qualifying_windows = [
        group
        for group in per_attribution_verified
        if max((iv.seconds for iv in group), default=0.0) >= require_continuous * 3600.0
    ]
    attributed_hours = sum(iv.seconds for group in per_attribution_all for iv in group) / 3600.0
    unverified_hours = max(0.0, attributed_hours - cumulative_hours)

    # ── 자격 판정 — 「지금 새 창을 열어도 손실이 0인가」 (보고 전용) ──────────
    #
    # ★새 판정식을 만들지 않는다 — 위 `qualifying_windows` 와 **같은 부등식**을 지금 열려
    #   있는 구간 하나에 적용할 뿐이다. 식을 복제하면 화면과 판정이 다른 말을 하게 된다.
    # ★`soak-stack.sh up` 은 **진행 중인 귀속 구간을 닫는다.** 자격(연속 24h + 실격 0)을
    #   얻기 **전에** 누르면 그때까지 번 시간은 창 0회로 소멸하고, 얻은 **뒤에** 누르면 그 창은
    #   1회로 확정돼 남는다(닫힌 구간도 `countable` 에 그대로 남으므로). 이 차이를 매 회차
    #   사람이 손으로 풀고 있었다 — 27.4h 를 돌리고도 C1 이 0/3 이던 실측이 그 값이다.
    # ★열린 구간이 `countable` 에 없을 수 있다 — 그 구간 안에서 실격이 나면 `window_start` 가
    #   당겨져 통째로 빠진다. 그때 자격은 0 이고 잃을 것도 이미 잃은 뒤다.
    open_index = next((i for i, a in enumerate(countable) if a is open_window), None)
    open_group = per_attribution_verified[open_index] if open_index is not None else []
    open_longest = max((iv.seconds for iv in open_group), default=0.0) / 3600.0
    window_eligibility = {
        # ★「열린 구간이 없다」는 「눌러도 된다」가 아니라 **판정 불가**다 ([BL-748] 계열).
        "open": open_window is not None,
        "longest_hours": round(open_longest, 4),
        "required_hours": require_continuous,
        "qualified": (
            open_window is not None and not violations and open_longest >= require_continuous
        ),
        "remaining_hours": round(max(0.0, require_continuous - open_longest), 4),
        # 지금 실격이 나면 잃는 것 — 이 창의 시간뿐 아니라 **이미 확정된 자격 창 전부**다
        # (실격은 T0 를 당겨 그 전에 시작한 귀속 구간을 `countable` 에서 통째로 뺀다).
        "at_risk_hours": round(open_longest, 4),
        "at_risk_windows": len(qualifying_windows),
        "disqualified_in_window": bool(violations),
    }

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
        # ★`is not None` 이 아니라 `isinstance(dict)` 다 ([BL-748], 2026-08-15). 종전에는 dict 가
        #   아닌 값(문자열 등)이 오면 C5 는 ✓ 인데 `_darkness_report` 는 None 을 내서 셸이
        #   「어둠 비율: ✗ 계산 실패 (C5 위반)」을 찍었다 — **판정과 표시가 서로 다른 말을 한다.**
        "darkness_computed": isinstance(darkness, dict),
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
        # ── C1 = 자격 창의 **개수** ([ADR-024] §C1, 2026-08-11) ──
        "C1_qualifying_windows": len(qualifying_windows),
        "C1_required_windows": require_windows,
        "C1_window_hours": require_continuous,
        "C1_ok": len(qualifying_windows) >= require_windows,
        # ★아래 둘은 **참고 전용**이다 — 판정에 쓰지 마라. 소비자가 `C1_required` 를
        #   문턱으로 읽던 시절이 있었으므로 이름을 `legacy_` 로 바꿔 오독을 막는다.
        "C1_cumulative_hours": round(cumulative_hours, 4),
        "C1_legacy_required_hours": require_hours,
        "C2_longest_hours": round(longest_hours, 4),
        "C2_required": require_continuous,
        "C2_ok": longest_hours >= require_continuous,
        "C3_violations": [f"{d.at.isoformat()} {d.kind} {d.detail}" for d in violations],
        "C3_ok": not violations,
        "C4_sample_gaps": gaps,
        # ★`clean` 이 비면 위 루프가 0회고 `gaps == []` 라 **「볼 창이 없다」가 「이상 없다」로**
        #   보고됐다([BL-748], 2026-08-15). 이 fail-open 은 조용하다 — 2026-08-15 판독이
        #   「C4 표본 공백 0건 ✓」와 「최대 간격 326.4분」을 같은 출력에 찍고 있었고, 실제로
        #   상위 공백 5개(최대 1524.5분)가 전부 귀속 구간 **바깥**이라 한 건도 세지지 않았다.
        #   귀속 창이 없으면 tick 연속성은 「정상」이 아니라 **판정 불가**다(아래 분기가 UNKNOWN 으로 보낸다).
        "C4_no_window": not clean,
        "C4_ok": bool(clean) and not gaps,
        "C5": integrity,
        "C5_ok": all(integrity.values()),
    }
    detail = {
        "window_start": window_start.isoformat(),
        "now": now.isoformat(),
        "windows": clean,
        "unattributed_hours": round(unattributed / 3600.0, 4),
        "unverified_hours": round(unverified_hours, 4),
        # ★`conditions` 에는 넣지 않는다 — 이 축은 판정을 한 글자도 바꾸지 않는다.
        #   판정은 「지났는가」를 묻고 이것은 「지금 눌러도 되는가」를 묻는다(다른 질문이다).
        "window_eligibility": window_eligibility,
        "disqualifications_all_time": [f"{d.at.isoformat()} {d.kind} {d.detail}" for d in disq],
        "divergence_labels": label_buckets,
        "darkness": _darkness_report(darkness),
        "thresholds_are_default": (
            require_hours == DEFAULT_REQUIRE_HOURS
            and require_continuous == DEFAULT_REQUIRE_CONTINUOUS_HOURS
            # ★새 문턱도 여기 들어와야 한다 — 빠뜨리면 `require_windows=1` 로 낮춘 실행이
            #   「기본 문턱이었다」고 보고한다(문턱을 낮춰 통과시킨 것이 안 보인다).
            and require_windows == DEFAULT_REQUIRE_WINDOWS
        ),
    }
    # ★[BL-653] — 「C3 실격 0」은 「정지가 없었다」가 아니라 **「이 해상도로는 못 봤다」**다.
    #   실격이 0건이면 위의 정체별 주석이 한 줄도 안 나오므로, 무엇으로 쟀는지를 여기 적는다.
    #   표본이 있을 때만 키를 넣는다 — 빈 입력의 판정 JSON 을 종전과 바이트 단위로 유지한다.
    gate_gaps = _sample_gaps([(parse_ts(str(s["at"])), None) for s in samples])
    if gate_gaps:
        detail["sample_resolution"] = {
            "samples": len(samples),
            "median_seconds": round(statistics.median(gate_gaps), 1),
            "max_seconds": round(max(gate_gaps), 1),
        }
    # 깨끗한 입력의 JSON을 수리 전과 바이트 단위로 같게 하려고 오염이 있을 때만 넣는다.
    if unreadable_log_coverage:
        detail["unreadable_log_coverage"] = summarize_unreadable_log_coverage(
            unreadable_log_coverage
        )
    # ★같은 이유로 원장을 **실은 실행에서만** 키를 넣는다 — 안 실으면 판정 JSON 이 종전과
    #   바이트 단위로 같다. 이 축은 `conditions` 를 한 글자도 건드리지 않는다([BL-641]).
    if payload.get("disqualification_ledger") is not None:
        detail["disqualification_attribution"] = attribute_disqualifications(
            disq, payload.get("disqualification_ledger")
        )

    if violations:
        first = violations[0]
        return Verdict(
            "FAIL",
            "실격",
            f"실격 사건 {len(violations)}건 — 최초 {first.at.isoformat()} {first.kind} ({first.detail}). T0 가 앞으로 당겨지고 누적이 0 으로 리셋된다.",
            conditions,
            detail,
        )

    # C3 뒤인 이유 = 래칫. 오염된 아카이브 한 건이 진짜 실격을 UNKNOWN 으로 덮으면 「죽었는데 안 죽은 걸로 보인다」가 된다. 실격은 무엇에도 덮이지 않는다.
    # 일반 C5 앞인 이유 = 이것이 원인이고 C5 항들은 증상이다. 커버리지가 전부 읽히지 않으면 log_coverage 가 비어 phantom_archive 가 false 로 떨어지는데, 그 낱말은 운영자를 「분류기를 보라」로 보낸다. 진짜 고장은 docker logs 였다.
    if unreadable_log_coverage:
        report = detail["unreadable_log_coverage"]
        return Verdict(
            "UNKNOWN",
            "측정불가",
            f"판독 불가 로그 커버리지 {report['count']}건 — 그 시간은 계상하지 않는다.",
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

    if not conditions["C4_ok"]:
        if gaps:
            why = f"표본 공백 {len(gaps)}건 (한계 {max_gap / 60:.0f}분) — 그 구간은 tick 연속성을 판정할 수 없다. 최초: {gaps[0]}"
        else:
            # ★공백 0건이 아니라 **볼 창이 0개**다 ([BL-748]). 이 둘을 같은 문장으로 찍으면
            #   운영자가 「이상 없다」로 읽는다 — 그것이 이 결함이 오래 산 이유다.
            why = (
                "귀속 창이 0개다 — 표본 공백을 잴 자리가 없어 tick 연속성을 판정할 수 없다. "
                "세션이 살아 있어도 `soak-stack.sh up` 이 연 귀속 구간 밖이면 시간이 계상되지 않는다."
            )
        return Verdict("UNKNOWN", "측정불가", why, conditions, detail)

    # ★문구에 **문턱을 하나만** 쓴다 ([BL-701]). 종전에는 새 문턱이 결정되고도 출력이
    #   `누적 … / 168h` 를 찍어 **같은 게이트가 두 문턱을 말했다** — 다음 회차는 그 출력을
    #   그대로 읽고 「아직 41% 다」로 판단한다. 누적은 `(참고)` 로 내리고 판정어에서 뺀다.
    n_win = len(qualifying_windows)
    if not conditions["C1_ok"] or not conditions["C2_ok"]:
        return Verdict(
            "UNKNOWN",
            "진행중",
            f"{require_continuous:.0f}h 창 {n_win}/{require_windows}회 · 최장 연속 {longest_hours:.2f}h / {require_continuous:.0f}h · 실격 0 (참고: 누적 {cumulative_hours:.2f}h)",
            conditions,
            detail,
        )

    return Verdict(
        "PASS",
        "",
        f"{require_continuous:.0f}h 창 {n_win} ≥ {require_windows}회 · 최장 연속 {longest_hours:.2f}h ≥ {require_continuous:.0f}h · 실격 0 · 측정 무결 (참고: 누적 {cumulative_hours:.2f}h)",
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
