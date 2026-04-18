import sys
import json
import numpy as np
import pandas as pd


def main(csv_path):
    # Load CSV
    df = pd.read_csv(csv_path, header=0)
    df.columns = [c.strip().lower() for c in df.columns]
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    df = df.set_index('timestamp').sort_index()
    df = df[['open', 'high', 'low', 'close', 'volume']].astype(float)

    n = len(df)
    opens = df['open'].values
    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    volumes = df['volume'].values

    # Helper: shift array by k (like pine's [k])
    def shift(arr, k, fill=np.nan):
        if k == 0:
            return arr.copy()
        result = np.empty_like(arr)
        if k > 0:
            result[:k] = fill
            result[k:] = arr[:-k]
        else:
            result[k:] = fill
            result[:k] = arr[-k:]
        return result

    def nz(arr, fill=0.0):
        result = arr.copy()
        result[np.isnan(result)] = fill
        return result

    # ta.ema
    def ema(src, length):
        result = np.full(n, np.nan)
        alpha = 2.0 / (length + 1)
        for i in range(n):
            if np.isnan(src[i]):
                continue
            if np.isnan(result[i-1]) if i > 0 else True:
                result[i] = src[i]
            else:
                result[i] = alpha * src[i] + (1 - alpha) * result[i-1]
        return result

    # ta.sma
    def sma(src, length):
        result = np.full(n, np.nan)
        for i in range(length - 1, n):
            window = src[i - length + 1:i + 1]
            if not np.any(np.isnan(window)):
                result[i] = np.mean(window)
        return result

    # ta.rma (Wilder's MA)
    def rma(src, length):
        result = np.full(n, np.nan)
        alpha = 1.0 / length
        for i in range(n):
            if np.isnan(src[i]):
                continue
            if np.isnan(result[i-1]) if i > 0 else True:
                result[i] = src[i]
            else:
                result[i] = alpha * src[i] + (1 - alpha) * result[i-1]
        return result

    # ta.tr
    def calc_tr():
        result = np.full(n, np.nan)
        for i in range(n):
            hl = highs[i] - lows[i]
            if i == 0:
                result[i] = hl
            else:
                hc = abs(highs[i] - closes[i-1])
                lc = abs(lows[i] - closes[i-1])
                result[i] = max(hl, hc, lc)
        return result

    tr_arr = calc_tr()

    # ta.atr
    def atr(length):
        return rma(tr_arr, length)

    # fixnan
    def fixnan(arr):
        result = arr.copy()
        last_valid = np.nan
        for i in range(n):
            if not np.isnan(result[i]):
                last_valid = result[i]
            elif not np.isnan(last_valid):
                result[i] = last_valid
        return result

    # ta.change
    def change(arr, length=1):
        return arr - shift(arr, length)

    # Supertrend
    def supertrend_func(close_arr, factor, atrLen):
        atr_arr = atr(atrLen)
        direction = np.full(n, np.nan)
        superTrend = np.full(n, np.nan)
        upperBand = np.full(n, np.nan)
        lowerBand = np.full(n, np.nan)

        for i in range(n):
            if np.isnan(atr_arr[i]):
                continue
            ub = close_arr[i] + factor * atr_arr[i]
            lb = close_arr[i] - factor * atr_arr[i]

            prevLB = lowerBand[i-1] if i > 0 and not np.isnan(lowerBand[i-1]) else lb
            prevUB = upperBand[i-1] if i > 0 and not np.isnan(upperBand[i-1]) else ub

            lowerBand[i] = lb if lb > prevLB or (i > 0 and close_arr[i-1] < prevLB) else prevLB
            upperBand[i] = ub if ub < prevUB or (i > 0 and close_arr[i-1] > prevUB) else prevUB

            if i == 0 or np.isnan(atr_arr[i-1]):
                direction[i] = 1
            else:
                prevST = superTrend[i-1]
                prevUB_val = upperBand[i-1] if not np.isnan(upperBand[i-1]) else upperBand[i]
                prevLB_val = lowerBand[i-1] if not np.isnan(lowerBand[i-1]) else lowerBand[i]
                if np.isnan(prevST):
                    direction[i] = 1
                elif prevST == prevUB_val:
                    direction[i] = -1 if close_arr[i] > upperBand[i] else 1
                else:
                    direction[i] = 1 if close_arr[i] < lowerBand[i] else -1

            superTrend[i] = lowerBand[i] if direction[i] == -1 else upperBand[i]

        return superTrend, direction

    # ADX / DMI
    def dirmov(length):
        up = change(highs)
        down = -change(lows)
        plusDM = np.where(
            np.isnan(up), np.nan,
            np.where((up > down) & (up > 0), up, 0.0)
        )
        minusDM = np.where(
            np.isnan(down), np.nan,
            np.where((down > up) & (down > 0), down, 0.0)
        )
        truerange = rma(tr_arr, length)
        plus = fixnan(100.0 * rma(plusDM, length) / truerange)
        minus = fixnan(100.0 * rma(minusDM, length) / truerange)
        return plus, minus

    def calc_adx(dilen, adxlen):
        plus, minus = dirmov(dilen)
        s = plus + minus
        s_safe = np.where(s == 0, 1.0, s)
        adx_val = 100.0 * rma(np.abs(plus - minus) / s_safe, adxlen)
        return adx_val

    # Compute indicators
    nsensitivity = 2.0
    atrLen_risk = 1
    atrRisk = 1

    ema200 = ema(closes, 200)
    sma9 = sma(closes, 13)

    superTrend_arr, direction_arr = supertrend_func(closes, nsensitivity * 2, 11)

    adxlen = 15
    dilen = 15
    sig = calc_adx(dilen, adxlen)
    sidewaysThreshold = 15
    isSideways = sig < sidewaysThreshold

    # bull/bear signals
    # bull = ta.crossover(close, supertrend) and close >= sma9
    # bear = ta.crossunder(close, supertrend) and close <= sma9

    def crossover(a, b):
        result = np.zeros(n, dtype=bool)
        for i in range(1, n):
            if not np.isnan(a[i]) and not np.isnan(b[i]) and not np.isnan(a[i-1]) and not np.isnan(b[i-1]):
                result[i] = (a[i-1] <= b[i-1]) and (a[i] > b[i])
        return result

    def crossunder(a, b):
        result = np.zeros(n, dtype=bool)
        for i in range(1, n):
            if not np.isnan(a[i]) and not np.isnan(b[i]) and not np.isnan(a[i-1]) and not np.isnan(b[i-1]):
                result[i] = (a[i-1] >= b[i-1]) and (a[i] < b[i])
        return result

    bull = crossover(closes, superTrend_arr) & (closes >= nz(sma9))
    bear = crossunder(closes, superTrend_arr) & (closes <= nz(sma9))

    # atrBand = ta.atr(atrLen) * atrRisk
    # trigger: countBull < countBear => long (trigger == 1 => long)
    # atrStop = trigger == 1 ? low - atrBand : high + atrBand
    atr_risk_arr = atr(atrLen_risk) * atrRisk

    # countBull = ta.barssince(bull), countBear = ta.barssince(bear)
    # trigger = nz(countBull, bar_index) < nz(countBear, bar_index) ? 1 : 0

    countBull = np.full(n, np.nan)
    countBear = np.full(n, np.nan)
    for i in range(n):
        if bull[i]:
            countBull[i] = 0
        elif i > 0 and not np.isnan(countBull[i-1]):
            countBull[i] = countBull[i-1] + 1

        if bear[i]:
            countBear[i] = 0
        elif i > 0 and not np.isnan(countBear[i-1]):
            countBear[i] = countBear[i-1] + 1

    # trigger = nz(countBull, bar_index) < nz(countBear, bar_index)
    trigger = np.zeros(n, dtype=int)
    for i in range(n):
        cb = countBull[i] if not np.isnan(countBull[i]) else i
        cbr = countBear[i] if not np.isnan(countBear[i]) else i
        trigger[i] = 1 if cb < cbr else 0

    atrStop = np.where(trigger == 1, lows - atr_risk_arr, highs + atr_risk_arr)

    # lastTrade(close) => ta.valuewhen(bull or bear, close, 0)
    # => most recent close value when bull or bear occurred
    # lastTrade(atrStop) => most recent atrStop when bull or bear occurred

    bull_or_bear = bull | bear
    lastTrade_close = np.full(n, np.nan)
    lastTrade_atrStop = np.full(n, np.nan)
    last_c = np.nan
    last_s = np.nan
    for i in range(n):
        if bull_or_bear[i]:
            last_c = closes[i]
            last_s = atrStop[i]
        lastTrade_close[i] = last_c
        lastTrade_atrStop[i] = last_s

    # TP levels (1:1, 2:1, 3:1)
    # tp1Rl_y = (lastTrade(close) - lastTrade(atrStop)) * 1 + lastTrade(close)
    # tp2RL_y = (lastTrade(close) - lastTrade(atrStop)) * 2 + lastTrade(close)
    # tp3RL_y = (lastTrade(close) - lastTrade(atrStop)) * 3 + lastTrade(close)
    tp1 = (lastTrade_close - lastTrade_atrStop) * 1 + lastTrade_close
    tp2 = (lastTrade_close - lastTrade_atrStop) * 2 + lastTrade_close
    tp3 = (lastTrade_close - lastTrade_atrStop) * 3 + lastTrade_close

    # Backtesting
    initial_capital = 10000.0
    fee_pct = 0.001

    capital = initial_capital
    position = 0  # 1=long, -1=short, 0=flat
    entry_price = np.nan
    entry_sl = np.nan
    entry_tp = np.nan
    entry_direction = 0

    equity_curve = np.full(n, np.nan)
    trades = []

    def close_trade(exit_price, reason, bar_idx):
        nonlocal capital, position, entry_price, entry_sl, entry_tp, entry_direction
        fee = exit_price * fee_pct
        if entry_direction == 1:
            pnl = (exit_price - entry_price - fee - entry_price * fee_pct) / (entry_price * (1 + fee_pct)) * capital
        else:
            pnl = (entry_price - exit_price - fee - entry_price * fee_pct) / (entry_price * (1 + fee_pct)) * capital
        # Simplified PnL: position sizing as fraction of capital
        # Entry cost: capital * fee_pct, exit cost: capital * fee_pct
        pnl_pct = (exit_price / entry_price - 1) * entry_direction
        net_pnl = capital * (pnl_pct - fee_pct - fee_pct)
        capital += net_pnl
        trades.append({
            'entry_bar': bar_idx,
            'direction': entry_direction,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl': net_pnl,
            'reason': reason
        })
        position = 0
        entry_price = np.nan
        entry_sl = np.nan
        entry_tp = np.nan
        entry_direction = 0

    for i in range(n):
        # Check exit conditions on current bar (using high/low for SL/TP checks)
        if position != 0:
            if entry_direction == 1:  # long
                # SL: price goes below entry_sl
                # TP: price goes above entry_tp
                hit_sl = lows[i] <= entry_sl
                hit_tp = highs[i] >= entry_tp
                if hit_sl and hit_tp:
                    # whichever came first - assume SL
                    close_trade(entry_sl, 'SL', i)
                elif hit_sl:
                    close_trade(entry_sl, 'SL', i)
                elif hit_tp:
                    close_trade(entry_tp, 'TP', i)
            elif entry_direction == -1:  # short
                hit_sl = highs[i] >= entry_sl
                hit_tp = lows[i] <= entry_tp
                if hit_sl and hit_tp:
                    close_trade(entry_sl, 'SL', i)
                elif hit_sl:
                    close_trade(entry_sl, 'SL', i)
                elif hit_tp:
                    close_trade(entry_tp, 'TP', i)

        # Entry signals
        if position == 0:
            if bull[i]:
                # Long entry
                if not np.isnan(lastTrade_atrStop[i]) and not np.isnan(tp1[i]):
                    sl = lastTrade_atrStop[i]
                    tp = tp1[i]  # using 1:1 TP as per indicator logic
                    if sl < closes[i] and tp > closes[i]:
                        position = 1
                        entry_direction = 1
                        entry_price = closes[i] * (1 + fee_pct)
                        entry_sl = sl
                        entry_tp = tp
            elif bear[i]:
                # Short entry
                if not np.isnan(lastTrade_atrStop[i]) and not np.isnan(tp1[i]):
                    sl = lastTrade_atrStop[i]
                    tp = tp1[i]  # for short: tp1 is entry - (entry - stop)*1 => below entry
                    if sl > closes[i] and tp < closes[i]:
                        position = -1
                        entry_direction = -1
                        entry_price = closes[i] * (1 - fee_pct)
                        entry_sl = sl
                        entry_tp = tp

        equity_curve[i] = capital if position == 0 else capital  # mark-to-market simplified

    # Compute stats
    total_trades = len(trades)
    winning_trades = sum(1 for t in trades if t['pnl'] > 0)
    losing_trades = sum(1 for t in trades if t['pnl'] <= 0)
    win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

    gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
    gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] <= 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else None

    total_return_pct = (capital - initial_capital) / initial_capital * 100.0

    # Rebuild equity curve properly
    eq = np.full(n, initial_capital)
    cap_running = initial_capital
    # recompute equity bar by bar
    cap_running = initial_capital
    position2 = 0
    ep2 = np.nan
    ed2 = 0
    eq2 = np.full(n, np.nan)
    trade_idx = 0
    trade_entry_bars = {t['entry_bar']: t for t in trades}

    # Simpler: just accumulate equity from trades
    eq_series = [initial_capital]
    running = initial_capital
    for t in trades:
        running += t['pnl']
        eq_series.append(running)

    eq_arr = np.array(eq_series)
    peak = np.maximum.accumulate(eq_arr)
    drawdown = (eq_arr - peak) / peak * 100.0
    max_drawdown_pct = float(np.min(drawdown)) if len(drawdown) > 1 else 0.0

    # Sharpe ratio using daily/bar returns
    if len(eq_series) > 1:
        rets = np.diff(eq_arr) / eq_arr[:-1]
        if len(rets) > 1 and np.std(rets) > 0:
            bars_per_year = 8760
            sharpe_ratio = float(np.mean(rets) / np.std(rets) * np.sqrt(bars_per_year))
        else:
            sharpe_ratio = 0.0
    else:
        sharpe_ratio = 0.0

    exit_reasons = {}
    for t in trades:
        r = t['reason']
        exit_reasons[r] = exit_reasons.get(r, 0) + 1

    result = {
        'total_return_pct': float(total_return_pct),
        'max_drawdown_pct': float(max_drawdown_pct),
        'sharpe_ratio': float(sharpe_ratio),
        'profit_factor': float(profit_factor) if profit_factor is not None else None,
        'total_trades': int(total_trades),
        'winning_trades': int(winning_trades),
        'losing_trades': int(losing_trades),
        'win_rate': float(win_rate),
        'exit_reasons': exit_reasons
    }

    print(json.dumps(result))


if __name__ == '__main__':
    main(sys.argv[1])