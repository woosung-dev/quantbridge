# TV Strategy Tester parity 통계 — sortino/calmar/excursion(run-up·drawdown)/per-side 순수 함수
"""equity 커브·RawTrade 목록만 입력받는 순수 통계 모듈 (BL-389 방향, add-only).

TV convention ground (2026-07-05 doc spike — tradingview.com/support 43000681694/97):
- Sharpe/Sortino = (MR - RFR) / SD|DD. 달력 월 수익률, RFR 기본 2%/년(월 2%/12),
  연율화 없음. 데이터가 2 달력월 미만이면 daily 기간(RFR 2%/365) fallback.
- DD(downside deviation) = 모집단 sqrt(mean(max(0, RFR - Xi)²)).
- Calmar = CAGR / |MDD| (둘 다 ratio).
에피소드/intrabar 규약은 `ExcursionStats` docstring (types.py) 이 SSOT — TV 미공개
세부는 hand-oracle(`test_golden_oracle_tv_pack.py`) 로 고정한 "TV 근사".
"""

from __future__ import annotations

import itertools
import math
from decimal import Decimal

import pandas as pd

from src.backtest.engine.types import ExcursionStats, PerSideMetrics, RawTrade, SideMetrics

_RFR_ANNUAL = 0.02  # TV 기본 risk-free rate
SHARPE_CONVENTION_MONTHLY = "tv_monthly_rfr2"
SHARPE_CONVENTION_DAILY = "tv_daily_rfr2"
SHARPE_CONVENTION_UNAVAILABLE = "unavailable"
# 자본이 0 이하로 내려간 구간이 있으면 기간 수익률의 분모가 음수가 되어 **더 잃을수록
# 수익률이 양수**가 된다. 그 위에서 계산한 위험조정수익은 아첨하는 거짓말이다.
# `unavailable` 과 분리하는 이유 = 그쪽 문구("변동이 없거나 기간이 짧아")가 여기선
# 적극적으로 틀리다. 계좌가 파산한 것과 잔잔한 것은 다른 사실이다.
SHARPE_CONVENTION_NONPOSITIVE_EQUITY = "unavailable_nonpositive_equity"


# ── sortino ──────────────────────────────────────────────────────────────────


def _has_nonpositive_equity(equity: pd.Series) -> bool:
    """자본이 한 번이라도 0 이하로 내려갔는가.

    기간 수익률은 `(cur - prev) / prev` 다. `prev` 가 음수면 부호가 뒤집혀
    **손실이 커질수록 수익률이 양수**가 된다. 실측 사례 — 초기자본 10,000 에서
    -207,968 로 끝난 실행(총수익률 -2179.68%)의 월간 수익률 13개 중 11개가
    양수였고 샤프가 +0.029 로 나왔다. `_periodic_returns` 는 `prev == 0` 만 막고
    있어서 음수 구간이 그대로 통과했다.
    """
    return bool((equity <= 0).any())


def _periodic_returns(equity: pd.Series) -> tuple[list[float], float, str] | None:
    """equity(float, DatetimeIndex) → (기간 수익률 목록, 기간 RFR, 기간 라벨).

    달력 월말 샘플 ≥ 2 → 월간(RFR 2%/12), 아니면 daily(RFR 2%/365) fallback.
    기준점 = equity 첫 값 (TV 예시: 1월 1일 100 → 2월 1일 110 = +10%).
    """
    if len(equity) < 2 or not isinstance(equity.index, pd.DatetimeIndex):
        return None
    monthly = equity.resample("ME").last().dropna()
    if len(monthly) >= 2:
        samples = [float(equity.iloc[0]), *[float(v) for v in monthly]]
        rfr = _RFR_ANNUAL / 12.0
        period = "monthly"
    else:
        samples = [float(v) for v in equity]
        rfr = _RFR_ANNUAL / 365.0
        period = "daily"
    returns: list[float] = []
    for prev, cur in itertools.pairwise(samples):
        if prev == 0 or not (math.isfinite(prev) and math.isfinite(cur)):
            return None
        returns.append((cur - prev) / prev)
    if not returns:
        return None
    return returns, rfr, period


def sortino_ratio(equity: pd.Series) -> Decimal | None:
    """TV Sortino = (MR - RFR) / downside deviation. 하방 편차 0 → None.

    자본이 0 이하로 간 구간이 있으면 산출하지 않는다 — `_has_nonpositive_equity` 참조.
    """
    if _has_nonpositive_equity(equity):
        return None
    periodic = _periodic_returns(equity)
    if periodic is None:
        return None
    returns, rfr, _ = periodic
    mean_return = sum(returns) / len(returns)
    downside_sq = [max(0.0, rfr - r) ** 2 for r in returns]
    dd = math.sqrt(sum(downside_sq) / len(downside_sq))
    if dd == 0 or not math.isfinite(dd):
        return None
    value = (mean_return - rfr) / dd
    if not math.isfinite(value):
        return None
    return Decimal(str(value))


def sharpe_ratio(equity: pd.Series) -> tuple[Decimal, str]:
    """TV Sharpe = (MR - RFR) / 모집단 표준편차. 연율화하지 않는다.

    형제 `sortino_ratio`는 `Decimal | None`을 반환하지만, Sharpe는 의도적으로
    비-옵셔널 `Decimal`을 반환한다. None을 반환하면
    `optimizer/engine/grid_search.py:249`의 현재 dead branch
    `metrics.sharpe_ratio is None`이 되살아나 degenerate 셀이 급증하고, FE
    `key-stats-strip.tsx`의 `.toFixed(2)`가 깨진다. degenerate는 값 0과
    convention `"unavailable"`로 구분한다.

    daily fallback은 sub-daily 타임프레임을 "1 bar = 1 day"로 센다. 이는
    `_periodic_returns`가 이미 가진 선재 결함이며 `sortino_ratio`도 동일하게
    영향받는다. 이 슬라이스에서는 고치지 않는다. 고치면 Sortino baseline까지
    흔들린다.
    """
    # 파산한 계좌에 위험조정수익을 매기지 않는다. 이걸 막지 않으면 분모 부호가
    # 뒤집혀 **손실이 클수록 좋아 보이는** 숫자가 나온다 — BL-398 이 없애려던
    # 거짓말의 다른 얼굴이다(구 수식은 수식 때문에, 이쪽은 분모 부호 때문에).
    if _has_nonpositive_equity(equity):
        return Decimal("0"), SHARPE_CONVENTION_NONPOSITIVE_EQUITY
    periodic = _periodic_returns(equity)
    if periodic is None:
        return Decimal("0"), SHARPE_CONVENTION_UNAVAILABLE
    returns, rfr, period = periodic
    mean_return = sum(returns) / len(returns)
    sd = math.sqrt(sum((r - mean_return) ** 2 for r in returns) / len(returns))
    if sd == 0 or not math.isfinite(sd):
        return Decimal("0"), SHARPE_CONVENTION_UNAVAILABLE
    value = (mean_return - rfr) / sd
    if not math.isfinite(value):
        return Decimal("0"), SHARPE_CONVENTION_UNAVAILABLE
    convention = SHARPE_CONVENTION_MONTHLY if period == "monthly" else SHARPE_CONVENTION_DAILY
    return Decimal(str(value)), convention


# ── calmar ───────────────────────────────────────────────────────────────────


def calmar_ratio(annual_return_pct: Decimal | None, max_drawdown: Decimal | None) -> Decimal | None:
    """Calmar = CAGR / |MDD| (ratio/ratio). MDD 0 또는 CAGR None → None."""
    if annual_return_pct is None or max_drawdown is None or max_drawdown == 0:
        return None
    try:
        return annual_return_pct / abs(max_drawdown)
    except ArithmeticError:
        return None


# ── excursion (run-up / drawdown 에피소드) ───────────────────────────────────


def _bar_hours(index: pd.Index) -> Decimal | None:
    """equity index 간격(중앙값) → 시간. days 환산용. 판별 불가 시 None."""
    if not isinstance(index, pd.DatetimeIndex) or len(index) < 2:
        return None
    diffs = index.to_series().diff().dropna()
    if diffs.empty:
        return None
    median = diffs.median()
    seconds = median.total_seconds()
    if seconds <= 0:
        return None
    return Decimal(str(seconds / 3600.0))


def _to_days(bars: Decimal | None, bar_hours: Decimal | None) -> Decimal | None:
    if bars is None or bar_hours is None:
        return None
    return bars * bar_hours / Decimal("24")


def _drawdown_episodes(values: list[Decimal]) -> list[tuple[Decimal, int, int, int]]:
    """(depth_abs, duration_bars, trough_idx, recovery_idx|-1) 목록.

    에피소드 = running peak 아래 연속 bar 구간. 회복 bar (equity ≥ peak) 미포함.
    미회복 에피소드는 recovery_idx = -1.
    """
    episodes: list[tuple[Decimal, int, int, int]] = []
    peak = values[0]
    in_episode = False
    depth = Decimal("0")
    duration = 0
    trough_idx = 0
    for i, v in enumerate(values):
        if v >= peak:
            if in_episode:
                episodes.append((depth, duration, trough_idx, i))
                in_episode = False
            peak = v
        else:
            d = peak - v
            if not in_episode:
                in_episode = True
                depth = d
                duration = 1
                trough_idx = i
            else:
                duration += 1
                if d > depth:
                    depth = d
                    trough_idx = i
    if in_episode:
        episodes.append((depth, duration, trough_idx, -1))
    return episodes


def _runup_episodes(values: list[Decimal]) -> list[tuple[Decimal, Decimal, int]]:
    """(height_abs, trough_base, duration_bars) 목록.

    에피소드 = running trough 위 연속 bar 구간. 신저점 bar (equity ≤ trough) 에서 종료.
    """
    episodes: list[tuple[Decimal, Decimal, int]] = []
    trough = values[0]
    in_episode = False
    height = Decimal("0")
    base = trough
    duration = 0
    for v in values:
        if v <= trough:
            if in_episode:
                episodes.append((height, base, duration))
                in_episode = False
            trough = v
        else:
            h = v - trough
            if not in_episode:
                in_episode = True
                height = h
                base = trough
                duration = 1
            else:
                duration += 1
                if h > height:
                    height = h
    if in_episode:
        episodes.append((height, base, duration))
    return episodes


def compute_excursion_stats(
    equity: pd.Series,
    equity_high: list[Decimal] | None,
    equity_low: list[Decimal] | None,
) -> ExcursionStats | None:
    """close-기준 equity 에피소드 통계 + (선택) intrabar 근사 극값.

    equity = Decimal object Series (엔진 close 커브). 2 bar 미만 → None.
    """
    if len(equity) < 2:
        return None
    values = [v if isinstance(v, Decimal) else Decimal(str(v)) for v in equity]
    bar_hours = _bar_hours(equity.index)

    dd_eps = _drawdown_episodes(values)
    ru_eps = _runup_episodes(values)

    max_runup_abs: Decimal | None = None
    max_runup_pct: Decimal | None = None
    avg_runup_abs: Decimal | None = None
    avg_runup_bars: Decimal | None = None
    if ru_eps:
        best = max(ru_eps, key=lambda e: e[0])
        max_runup_abs = best[0]
        max_runup_pct = best[0] / best[1] if best[1] > 0 else None
        avg_runup_abs = sum((e[0] for e in ru_eps), start=Decimal("0")) / len(ru_eps)
        avg_runup_bars = Decimal(sum(e[2] for e in ru_eps)) / len(ru_eps)

    avg_dd_abs: Decimal | None = None
    avg_dd_bars: Decimal | None = None
    max_dd_abs: Decimal | None = None
    recovery_bars: int | None = None
    if dd_eps:
        avg_dd_abs = sum((e[0] for e in dd_eps), start=Decimal("0")) / len(dd_eps)
        avg_dd_bars = Decimal(sum(e[1] for e in dd_eps)) / len(dd_eps)
        worst = max(dd_eps, key=lambda e: e[0])
        max_dd_abs = worst[0]
        if worst[3] >= 0:
            recovery_bars = worst[3] - worst[2]

    # intrabar 근사 — 커브 미전달 시 None 유지.
    ru_intra_abs: Decimal | None = None
    ru_intra_pct: Decimal | None = None
    dd_intra_abs: Decimal | None = None
    dd_intra_pct: Decimal | None = None
    if equity_high is not None and equity_low is not None and len(equity_high) == len(values):
        run_min_low = equity_low[0]
        run_max_high = equity_high[0]
        for hi, lo in zip(equity_high, equity_low, strict=True):
            run_min_low = min(run_min_low, lo)
            run_max_high = max(run_max_high, hi)
            up = hi - run_min_low
            if ru_intra_abs is None or up > ru_intra_abs:
                ru_intra_abs = up
                ru_intra_pct = up / run_min_low if run_min_low > 0 else None
            down = run_max_high - lo
            if dd_intra_abs is None or down > dd_intra_abs:
                dd_intra_abs = down
                dd_intra_pct = down / run_max_high if run_max_high > 0 else None

    return ExcursionStats(
        max_runup_abs=max_runup_abs,
        max_runup_pct=max_runup_pct,
        avg_runup_abs=avg_runup_abs,
        avg_runup_duration_bars=avg_runup_bars,
        avg_runup_duration_days=_to_days(avg_runup_bars, bar_hours),
        avg_drawdown_abs=avg_dd_abs,
        avg_drawdown_duration_bars=avg_dd_bars,
        avg_drawdown_duration_days=_to_days(avg_dd_bars, bar_hours),
        max_drawdown_abs=max_dd_abs,
        max_drawdown_recovery_bars=recovery_bars,
        max_drawdown_recovery_days=(
            _to_days(Decimal(recovery_bars), bar_hours) if recovery_bars is not None else None
        ),
        max_runup_intrabar_abs=ru_intra_abs,
        max_runup_intrabar_pct=ru_intra_pct,
        max_drawdown_intrabar_abs=dd_intra_abs,
        max_drawdown_intrabar_pct=dd_intra_pct,
    )


# ── per-side ─────────────────────────────────────────────────────────────────


def _side_metrics(closed: list[RawTrade]) -> SideMetrics | None:
    if not closed:
        return None
    net = sum((t.pnl for t in closed), start=Decimal("0"))
    gross_profit = sum((t.pnl for t in closed if t.pnl > 0), start=Decimal("0"))
    gross_loss = sum((-t.pnl for t in closed if t.pnl < 0), start=Decimal("0"))
    return SideMetrics(
        net_profit_abs=net,
        gross_profit_abs=gross_profit,
        gross_loss_abs=gross_loss,
        profit_factor=gross_profit / gross_loss if gross_loss > 0 else None,
        avg_trade_abs=net / len(closed),
    )


def compute_side_metrics(closed: list[RawTrade]) -> PerSideMetrics | None:
    """closed trades → long/short 분리 팩. closed 0건 → None."""
    if not closed:
        return None
    return PerSideMetrics(
        long=_side_metrics([t for t in closed if t.direction == "long"]),
        short=_side_metrics([t for t in closed if t.direction == "short"]),
    )
