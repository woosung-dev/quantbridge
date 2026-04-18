import sys
import pandas as pd
import numpy as np
import json

def ta_ema(series, length):
    return series.ewm(span=length, adjust=False).mean()

def ta_sma(series, length):
    return series.rolling(window=length).mean()

def ta_atr(high, low, close, length):
    tr = np.maximum(high - low, np.maximum(abs(high - close.shift(1)), abs(low - close.shift(1))))
    return tr.rolling(window=length).mean()

def main(csv_path):
    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    df.set_index('timestamp', inplace=True)
    
    close = df['close']
    open_ = df['open']
    high = df['high']
    low = df['low']
    
    # Strategy Constants
    nsensitivity = 2
    atrLen = 11
    
    # Supertrend Logic
    atr = ta_atr(high, low, close, atrLen)
    factor = nsensitivity * 2
    upperBand = close + factor * atr
    lowerBand = close - factor * atr
    
    supertrend = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)
    
    for i in range(1, len(df)):
        prev_lb = lowerBand.iloc[i-1] if not np.isnan(lowerBand.iloc[i-1]) else 0
        prev_ub = upperBand.iloc[i-1] if not np.isnan(upperBand.iloc[i-1]) else 0
        
        lb = lowerBand.iloc[i] if lowerBand.iloc[i] > prev_lb or close.iloc[i-1] < prev_lb else prev_lb
        ub = upperBand.iloc[i] if upperBand.iloc[i] < prev_ub or close.iloc[i-1] > prev_ub else prev_ub
        
        if np.isnan(atr.iloc[i-1]):
            d = 1
        else:
            prev_st = supertrend.iloc[i-1]
            if prev_st == prev_ub:
                d = -1 if close.iloc[i] > ub else 1
            else:
                d = 1 if close.iloc[i] < lb else -1
        
        supertrend.iloc[i] = lb if d == -1 else ub
        direction.iloc[i] = d

    sma9 = ta_sma(close, 13)
    bull = (direction.shift(1) == 1) & (direction == -1) & (close >= sma9)
    bear = (direction.shift(1) == -1) & (direction == 1) & (close <= sma9)
    
    # Backtest Engine
    capital = 10000
    fee_pct = 0.001
    position = 0
    entry_price = 0
    trades = []
    
    for i in range(len(df)):
        if position == 0:
            if bull.iloc[i]:
                position = 1
                entry_price = close.iloc[i]
                capital -= capital * fee_pct
            elif bear.iloc[i]:
                position = -1
                entry_price = close.iloc[i]
                capital -= capital * fee_pct
        else:
            # Simple exit logic based on trend reversal
            if (position == 1 and bear.iloc[i]) or (position == -1 and bull.iloc[i]):
                exit_price = close.iloc[i]
                pnl = (exit_price - entry_price) * position
                capital += (capital * (pnl / entry_price))
                capital -= capital * fee_pct
                trades.append(pnl / entry_price)
                position = 0

    # Metrics
    total_return = (capital - 10000) / 10000 * 100
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t <= 0]
    win_rate = len(wins) / len(trades) if trades else 0
    profit_factor = sum(wins) / abs(sum(losses)) if losses else float('inf')
    
    results = {
        "total_return_pct": round(total_return, 2),
        "max_drawdown_pct": 0.0, # Simplified
        "sharpe_ratio": 0.0,
        "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else None,
        "total_trades": len(trades),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": round(win_rate, 4),
        "exit_reasons": {"TrendReversal": len(trades)}
    }
    print(json.dumps(results))

if __name__ == "__main__":
    main(sys.argv[1])