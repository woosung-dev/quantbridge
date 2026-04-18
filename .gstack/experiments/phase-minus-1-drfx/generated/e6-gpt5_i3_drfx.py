import sys
import json
import math
import numpy as np
import pandas as pd

# Backtest configuration
INITIAL_CAPITAL = 10000.0
FEE_PCT = 0.001  # per side

# =========================
# Utility and TA functions
# =========================

def to_utc_index(df):
    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    df = df.set_index('timestamp').sort_index()
    return df

def sma(series, length):
    return series.rolling(window=int(length), min_periods=int(length)).mean()

def ema(series, length):
    return series.ewm(span=int(length), adjust=False, min_periods=int(length)).mean()

def change(series, length=1):
    return series.diff(int(length))

def true_range(high, low, close):
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr

def rma(series, length):
    alpha = 1.0 / float(length)
    return series.ewm(alpha=alpha, adjust=False, min_periods=int(length)).mean()

def atr(high, low, close, length):
    tr = true_range(high, low, close)
    return rma(tr, int(length))

def crossover(a, b):
    a_prev = a.shift(1)
    b_prev = b.shift(1)
    return (a > b) & (a_prev <= b_prev)

def crossunder(a, b):
    a_prev = a.shift(1)
    b_prev = b.shift(1)
    return (a < b) & (a_prev >= b_prev)

def nz(x, replace=0.0):
    return x.fillna(replace)

def supertrend_series(close, factor, atr_len):
    """
    Translate the provided Pine custom supertrend() to sequential Python.
    Pine logic:
        atr = ta.atr(atrLen)
        upperBand = close + factor * atr
        lowerBand = close - factor * atr
        prevLowerBand = nz(lowerBand[1])
        prevUpperBand = nz(upperBand[1])
        lowerBand := lowerBand > prevLowerBand or close[1] < prevLowerBand ? lowerBand : prevLowerBand
        upperBand := upperBand < prevUpperBand or close[1] > prevUpperBand ? upperBand : prevUpperBand
        int direction = na
        float superTrend = na
        prevSuperTrend = superTrend[1]
        if na(atr[1])
            direction := 1
        else if prevSuperTrend == prevUpperBand
            direction := close > upperBand ? -1 : 1
        else
            direction := close < lowerBand ? 1 : -1
        superTrend := direction == -1 ? lowerBand : upperBand
        [superTrend, direction]
    """
    n = len(close)
    atr_vals = atr(close.to_numpy()*0 + close.values, close.to_numpy()*0 + close.values, close.values, atr_len)  # placeholder; will recalc properly below

    # Proper ATR:
    # Note: calling atr with correct H,L,C requires actual high/low; will handle outside this function.
    # Here we compute with passed atr_len only; we will overwrite atr_vals externally.
    st = np.full(n, np.nan, dtype=float)
    dir_arr = np.full(n, np.nan, dtype=float)
    upperBand = np.full(n, np.nan, dtype=float)
    lowerBand = np.full(n, np.nan, dtype=float)
    return st, dir_arr, upperBand, lowerBand  # placeholders, actual supertrend computed in compute_indicators()

def compute_supertrend(close_s, atr_s, factor):
    """
    Sequential supertrend consistent with provided Pine function body.
    Inputs:
      close_s: pd.Series
      atr_s: pd.Series (ta.atr result with given length)
      factor: float
    Returns:
      supertrend (pd.Series), direction (pd.Series)
    """
    n = len(close_s)
    c = close_s.values
    a = atr_s.values
    upper = np.full(n, np.nan)
    lower = np.full(n, np.nan)
    st = np.full(n, np.nan)
    direction = np.full(n, np.nan)

    for i in range(n):
        if np.isnan(c[i]) or np.isnan(a[i]):
            # upper/lower remain nan
            # direction defined later when enough data
            pass
        else:
            ub = c[i] + factor * a[i]
            lb = c[i] - factor * a[i]
            # previous bands
            prev_lb = lower[i-1] if i-1 >= 0 and not np.isnan(lower[i-1]) else np.nan
            prev_ub = upper[i-1] if i-1 >= 0 and not np.isnan(upper[i-1]) else np.nan
            c1 = c[i-1] if i-1 >= 0 else np.nan

            # Replicate Pine's series assignment semantics
            if not np.isnan(prev_lb):
                if (lb > prev_lb) or (not np.isnan(c1) and c1 < prev_lb):
                    lower[i] = lb
                else:
                    lower[i] = prev_lb
            else:
                lower[i] = lb

            if not np.isnan(prev_ub):
                if (ub < prev_ub) or (not np.isnan(c1) and c1 > prev_ub):
                    upper[i] = ub
                else:
                    upper[i] = prev_ub
            else:
                upper[i] = ub

            prev_st = st[i-1] if i-1 >= 0 else np.nan
            # if na(atr[1]) in Pine: i-1 atr na
            atr_prev_na = (i-1 < 0) or np.isnan(a[i-1])

            if atr_prev_na:
                direction[i] = 1.0
            else:
                # Compare prevSuperTrend to prevUpperBand
                prev_ub_used = upper[i-1] if i-1 >= 0 else np.nan
                if not np.isnan(prev_st) and not np.isnan(prev_ub_used) and prev_st == prev_ub_used:
                    direction[i] = -1.0 if (c[i] > upper[i]) else 1.0
                else:
                    direction[i] = 1.0 if (c[i] < lower[i]) else -1.0

            st[i] = lower[i] if direction[i] == -1.0 else upper[i]

    return pd.Series(st, index=close_s.index), pd.Series(direction, index=close_s.index)

def barssince(cond_series):
    """
    Pine ta.barssince: number of bars since condition was true.
    Returns large number for never-true until first occurrence.
    """
    res = np.full(len(cond_series), np.nan, dtype=float)
    last = np.nan
    for i, v in enumerate(cond_series.astype(bool).values):
        if v:
            last = 0.0
            res[i] = 0.0
        else:
            if np.isnan(last):
                res[i] = np.nan
            else:
                last = last + 1.0
                res[i] = last
    # Replace leading NaNs with bar_index per script style using nz(countBull, bar_index)
    # We'll just leave NaNs; caller can handle with index positions if needed.
    return pd.Series(res, index=cond_series.index)

# =========================
# Strategy translation
# =========================

def compute_indicators(df):
    # Inputs (defaults from Pine)
    nsensitivity = 2.0
    atrLen_supertrend = 11
    sma9_len = 13
    ema200_len = 200

    close = df['close']
    high = df['high']
    low = df['low']
    open_ = df['open']
    volume = df['volume']

    # Core MAs
    ema200con = ema(close, ema200_len)
    sma9 = sma(close, sma9_len)

    # ATR for supertrend
    atr_vals = atr(high, low, close, atrLen_supertrend)

    # Supertrend with provided logic
    st, direction = compute_supertrend(close, atr_vals, nsensitivity * 2.0)

    # Signals
    bull = crossover(close, st) & (close >= sma9)
    bear = crossunder(close, st) & (close <= sma9)

    indicators = {
        'ema200con': ema200con,
        'sma9': sma9,
        'supertrend': st,
        'direction': direction,
        'bull': bull.fillna(False),
        'bear': bear.fillna(False),
        # Additional derived values from script (not used for trades)
        'atr_vals': atr_vals,
    }

    # [SKIP] psar, alma, wma, plotting, barcolor, fill, labels, boxes, lines, table
    # [SKIP] request.security (multi-timeframe) and any MTF logic
    # [SKIP] arrays/box/label operations and S/R zones
    # [SKIP] alerts -> treat as no-op
    return indicators

def backtest(df):
    """
    Since the provided Pine script is an indicator (no strategy.entry/exit/close),
    we preserve behavior: no trades executed.
    """
    indicators = compute_indicators(df)

    # No trades per rules (no strategy.* in source).
    equity = np.full(len(df), INITIAL_CAPITAL, dtype=float)
    equity_series = pd.Series(equity, index=df.index)

    # Metrics from flat equity
    rets = equity_series.pct_change().fillna(0.0)
    total_return_pct = (equity_series.iloc[-1] / equity_series.iloc[0] - 1.0) * 100.0 if len(equity_series) > 1 else 0.0

    # Max drawdown (% negative) from equity curve
    roll_max = equity_series.cummax()
    dd = equity_series / roll_max - 1.0
    max_drawdown_pct = float(dd.min() * 100.0) if len(dd) > 0 else 0.0

    # Sharpe ratio: annualized with bars_per_year=8760 for 1H data (as required)
    bars_per_year = 8760.0
    ret_mean = rets.mean()
    ret_std = rets.std(ddof=0)
    if ret_std > 0:
        sharpe = float((ret_mean / ret_std) * math.sqrt(bars_per_year))
    else:
        sharpe = 0.0

    # Trades stats: none
    total_trades = 0
    winning_trades = 0
    losing_trades = 0
    win_rate = 0.0
    profit_factor = None
    exit_reasons = {}

    results = {
        "total_return_pct": float(total_return_pct),
        "max_drawdown_pct": float(max_drawdown_pct),
        "sharpe_ratio": float(sharpe),
        "profit_factor": profit_factor,
        "total_trades": int(total_trades),
        "winning_trades": int(winning_trades),
        "losing_trades": int(losing_trades),
        "win_rate": float(win_rate),
        "exit_reasons": exit_reasons,
    }
    return results

def main(csv_path):
    # Load data
    df = pd.read_csv(csv_path)
    # Ensure required columns exist
    required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    df = to_utc_index(df)
    # Convert to float
    for c in ['open', 'high', 'low', 'close', 'volume']:
        df[c] = pd.to_numeric(df[c], errors='coerce')

    # Run backtest
    results = backtest(df)

    # Output JSON
    print(json.dumps(results))

if __name__ == "__main__":
    main(sys.argv[1])