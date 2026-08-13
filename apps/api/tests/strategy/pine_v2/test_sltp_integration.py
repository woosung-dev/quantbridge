"""SLTP 통합 진단 (Sprint 9-2 Bundle D1).

이슈 1 의 실패 경로 후보 재진단:
- (d) nan 전파 — entry 없는 bar 에서 position_avg_price=nan, nan*1.02=nan, 비교는 False
- (e) 같은 bar entry↔exit race — entry 발동 bar 에서 즉시 exit 되는지
- (f) Attribute vs Name 경로 이원화 — strategy.position_avg_price 가 양 경로 동일 값인지
- (g) close id 불일치 silent no-op — warning 없이 조용히 무시되는지

모두 mock 없이 `source → parse → interpreter → event_loop` 경로로 작성.
"""
from __future__ import annotations

import pandas as pd

from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.interpreter import BarContext, Interpreter
from src.strategy.pine_v2.parser_adapter import parse_to_ast
from src.strategy.pine_v2.runtime import PersistentStore


def _ohlcv(closes: list[float]) -> pd.DataFrame:
    opens = [closes[0], *closes[:-1]]
    return pd.DataFrame({
        "open": opens,
        "high": [c * 1.01 for c in closes],
        "low": [c * 0.99 for c in closes],
        "close": closes,
        "volume": [100.0] * len(closes),
    })


def _run_and_collect(source: str, closes: list[float]) -> tuple[Interpreter, BarContext]:
    """소스 + close 열로 run_historical 루프 실행, Interpreter 반환."""
    ohlcv = _ohlcv(closes)
    bar = BarContext(ohlcv)
    store = PersistentStore()
    interp = Interpreter(bar, store)
    tree = parse_to_ast(source)
    while bar.advance():
        store.begin_bar()
        interp.reset_transient()
        interp.begin_bar_snapshot()
        interp.execute(tree)
        store.commit_bar()
        interp.append_var_series()
    return interp, bar


# -----------------------------------------------------------------------
# 후보 (f): Attribute vs Name 경로 검증
# -----------------------------------------------------------------------

def test_position_avg_price_via_attribute_chain_matches_name_path() -> None:
    """strategy.position_avg_price 가 어느 AST 경로로 파싱되든 동일 값 반환.

    interpreter._eval_name (L841) 과 _eval_attribute (L911) 는 모두
    self.strategy.position_avg_price property 로 dispatch 되어야 한다.
    둘 중 한 쪽만 호출되어도 동일 값이어야 회귀 없음.
    """
    source = """//@version=5
strategy("t")
if bar_index == 1
    strategy.entry("L", strategy.long, qty=1.0)
avg_px = strategy.position_avg_price
pos_sz = strategy.position_size
"""
    interp, _ = _run_and_collect(source, [10.0, 20.0, 30.0])

    # 최종 bar 에서 avg_px 값 — entry 는 bar 1 close=20.0 에 체결
    # bar 2 의 avg_px 는 20.0 이어야 (현재 open long, entry_price=20)
    # Name 또는 Attribute 경로 어느 쪽이 사용되든 동일 값
    assert interp.strategy.position_size == 1.0
    assert interp.strategy.position_avg_price == 20.0


# -----------------------------------------------------------------------
# 후보 (e): 같은 bar entry ↔ exit race
# -----------------------------------------------------------------------

def test_same_bar_entry_and_close_race_behavior() -> None:
    """entry 발동 bar 에서 즉시 `if strategy.position_size > 0: strategy.close(...)`.

    현재 interpreter 는 current bar close 에 시장가 체결 →
    entry 후 position_size 즉시 1.0 → 같은 bar 에서 close 조건이 참이 되면
    그 bar close 가격으로 즉시 exit (entry_price == exit_price 수수료만 발생).

    이 동작이 Pine 표준과 맞는지 문서화. 이번 sprint 에서는
    진입 bar 에서는 same-bar exit 차단하는 guard 가 필요한지 판단 근거로 쓴다.
    """
    source = """//@version=5
strategy("t")
if bar_index == 1
    strategy.entry("L", strategy.long, qty=1.0)
if strategy.position_size > 0
    strategy.close("L", comment="EXIT")
"""
    interp, _ = _run_and_collect(source, [10.0, 20.0, 30.0, 40.0])

    # 현재 동작: entry bar 1 에서 즉시 close 되어 1건 trade (entry=exit=20.0)
    # 기대 동작: entry bar 는 exit 차단 → 다음 bar (2) 에서 close
    # 이 테스트는 "현재 동작" 을 고정해 규칙 변경 시 회귀 감지용으로 사용.
    assert len(interp.strategy.closed_trades) >= 1
    first = interp.strategy.closed_trades[0]
    # 실패 원인 (e) 진단: entry_bar == exit_bar 이면 same-bar race 확정
    if first.exit_bar == first.entry_bar:
        # 같은 bar race 재현됨
        assert first.entry_price == first.exit_price  # 수수료 전 동일
    else:
        # 다음 bar 에서 exit — race 없음
        assert first.exit_bar == first.entry_bar + 1


# -----------------------------------------------------------------------
# 후보 (g): close id 불일치 silent no-op
# -----------------------------------------------------------------------

def test_close_with_mismatched_id_is_silent_noop() -> None:
    """strategy.close("WrongId") 호출 시 open_trades 에 해당 id 없으면 None 반환.

    현재 구현 (strategy_state.py:189): `open_trades.pop(trade_id, None)` 로
    조용히 무시. warning 에도 기록 안 됨. 사용자 실수 탐지 불가.
    """
    source = """//@version=5
strategy("t")
if bar_index == 1
    strategy.entry("PivRevLE", strategy.long, qty=1.0)
if bar_index == 3
    strategy.close("PivRevLE_TYPO", comment="SLTP_L")
"""
    interp, _ = _run_and_collect(source, [10.0, 20.0, 30.0, 40.0, 50.0])

    # id 불일치 → close 실패 → position 그대로 open
    assert interp.strategy.position_size == 1.0
    assert len(interp.strategy.closed_trades) == 0
    # 현재는 warning 에도 기록 안 됨 — 이번 sprint 에서 개선할지 결정
    # (개선 시 assertion 반전)


# -----------------------------------------------------------------------
# 후보 (d): nan 전파
# -----------------------------------------------------------------------

def test_nan_propagation_before_any_entry() -> None:
    """entry 전 bar 에서 strategy.position_avg_price 는 nan.

    nan * 1.02 = nan, nan 비교는 False — 정상적으로 무시되어야.
    """
    source = """//@version=5
strategy("t")
avg_px = strategy.position_avg_price
pos_sz = strategy.position_size
// 이 시점 entry 없음 → pos_sz=0, avg_px=nan
"""
    interp, _ = _run_and_collect(source, [10.0, 20.0, 30.0])

    assert interp.strategy.position_size == 0.0
    # position_avg_price 는 nan 이어야 (open_trades 비었으므로)
    import math
    assert math.isnan(interp.strategy.position_avg_price)


# -----------------------------------------------------------------------
# 종합: s1_pbr_sltp 축소 fixture 로 SLTP 발동 확인
# -----------------------------------------------------------------------

def test_sltp_roundtrip_s1_pbr_like_fixture() -> None:
    """실제 e2e_v2_s1_pbr_sltp 의 핵심 로직 축소 재현.

    bar 1: entry 발동 (long qty=1, fill=100)
    bar 2: close=100 (변화 없음) → SLTP 조건 불성립
    bar 3: close=98 (2% 하락) → SL 조건 성립 (close <= avg_px * 0.99)
    기대: bar 3 에 SLTP_L comment 로 close 발동, exit_price ≈ 98
    """
    source = """//@version=5
strategy("t")
if bar_index == 1
    strategy.entry("PivRevLE", strategy.long, qty=1.0)

avg_px = strategy.position_avg_price
tp_pct = 0.02
sl_pct = 0.01
long_exit = strategy.position_size > 0 and (close >= avg_px * (1.0 + tp_pct) or close <= avg_px * (1.0 - sl_pct))
if long_exit
    strategy.close("PivRevLE", comment="SLTP_L")
"""
    # bar 0: 100, bar 1: 100 (entry fill at 100), bar 2: 100 (no exit),
    # bar 3: 98 (2% 하락 → SL 1% 이하 성립), bar 4: 97
    interp, _ = _run_and_collect(source, [100.0, 100.0, 100.0, 98.0, 97.0])

    # 최소 1건의 closed trade
    assert len(interp.strategy.closed_trades) >= 1, (
        f"SLTP close 가 발동 안 함. "
        f"open_trades={interp.strategy.open_trades}, "
        f"closed_trades={interp.strategy.closed_trades}, "
        f"warnings={interp.strategy.warnings}"
    )

    # 첫 번째 close 가 SLTP_L comment 포함
    first_closed = interp.strategy.closed_trades[0]
    assert "SLTP_L" in (first_closed.comment or ""), (
        f"SLTP_L comment 누락. actual comment={first_closed.comment!r}"
    )

    # exit 가격이 의도된 1%/2% 경계 안
    assert first_closed.exit_price is not None and first_closed.entry_price > 0
    ratio = first_closed.exit_price / first_closed.entry_price
    assert 0.97 <= ratio <= 1.03, (
        f"SLTP 경계 벗어남: entry={first_closed.entry_price}, "
        f"exit={first_closed.exit_price}, ratio={ratio}"
    )


# -----------------------------------------------------------------------
# 결정적 테스트: 실제 e2e_v2_s1_pbr_sltp pine 원문을 그대로 실행
# -----------------------------------------------------------------------

REAL_S1_PBR_SLTP_SOURCE = """//@version=6
strategy("Pivot Reversal Strategy SL1/TP2", overlay=true)
leftBars = input(4, "Pivot Lookback Left")
rightBars = input(2, "Pivot Lookback Right")
swh = ta.pivothigh(leftBars, rightBars)
swl = ta.pivotlow(leftBars, rightBars)
swh_cond = not na(swh)
hprice = 0.0
hprice := swh_cond ? swh : hprice[1]
le = false
le := swh_cond ? true : (le[1] and high > hprice ? false : le[1])
if (le)
        strategy.entry("PivRevLE", strategy.long, comment="PivRevLE", stop=hprice + syminfo.mintick)
swl_cond = not na(swl)
lprice = 0.0
lprice := swl_cond ? swl : lprice[1]
se = false
se := swl_cond ? true : (se[1] and low < lprice ? false : se[1])
if (se)
        strategy.entry("PivRevSE", strategy.short, comment="PivRevSE", stop=lprice - syminfo.mintick)

// --- SL=1% / TP=2% (entry id별 strategy.close) ---
avg_px = strategy.position_avg_price
tp_pct = 0.02
sl_pct = 0.01
long_exit  = strategy.position_size > 0 and (close >= avg_px * (1.0 + tp_pct) or close <= avg_px * (1.0 - sl_pct))
short_exit = strategy.position_size < 0 and (close <= avg_px * (1.0 - tp_pct) or close >= avg_px * (1.0 + sl_pct))
if long_exit
    strategy.close("PivRevLE", comment="SLTP_L")
if short_exit
    strategy.close("PivRevSE", comment="SLTP_S")
"""


def _synthetic_ohlcv_with_pivots(n_bars: int = 60) -> pd.DataFrame:
    """pivot high/low 가 여러 번 발생하는 synthetic OHLCV.

    정현파 + 노이즈 형태 → 주기적 local max/min.
    strategy.entry stop 주문이 체결될 만큼 변동성 있음.
    """
    import math
    closes = []
    base = 100.0
    for i in range(n_bars):
        # 주기 10 bar 의 사인파 + 선형 노이즈
        sig = math.sin(i / 10 * 2 * math.pi) * 10
        drift = -0.05 * i  # 약간 하락 트렌드
        close = base + sig + drift
        closes.append(close)
    opens = [closes[0], *closes[:-1]]
    # high/low 는 close 주변 ±2%
    return pd.DataFrame({
        "open": opens,
        "high": [c * 1.02 for c in closes],
        "low": [c * 0.98 for c in closes],
        "close": closes,
        "volume": [1000.0] * n_bars,
    })


def test_real_s1_pbr_sltp_pine_executes_and_sltp_fires() -> None:
    """실제 dogfood pine 소스를 그대로 실행 → SLTP_L 또는 SLTP_S close 최소 1건 기대.

    실패 시 어떤 경로에서 SLTP 가 막혔는지 warnings 및 trades 목록으로 진단.
    """
    ohlcv = _synthetic_ohlcv_with_pivots(n_bars=80)
    result = run_historical(REAL_S1_PBR_SLTP_SOURCE, ohlcv, strict=False)

    state = result.strategy_state
    assert state is not None

    # 1) 진단 출력 (실패 시 원인 확인용)
    entry_count = len([t for t in state.closed_trades if t.entry_price]) + len(state.open_trades)
    sltp_closes = [t for t in state.closed_trades if "SLTP" in (t.comment or "")]
    other_closes = [t for t in state.closed_trades if "SLTP" not in (t.comment or "")]

    diag = (
        f"\n=== s1_pbr_sltp 실행 진단 ===\n"
        f"bars: {result.bars_processed}, errors: {len(result.errors)}\n"
        f"entries (total): {entry_count}\n"
        f"SLTP closes: {len(sltp_closes)}\n"
        f"other closes: {len(other_closes)}\n"
        f"open_trades: {len(state.open_trades)}\n"
        f"warnings: {state.warnings[:5]}\n"
        f"first 3 closed trades: "
        f"{[(t.id, t.comment, t.entry_price, t.exit_price) for t in state.closed_trades[:3]]}\n"
    )

    # 2) 실패 경로 a) entry 자체가 안 됨
    assert entry_count > 0, f"entry 자체가 한 번도 발생 안 함.{diag}"

    # 3) 실패 경로 b) entry 는 되는데 SLTP close 가 안 됨
    assert len(sltp_closes) >= 1, f"SLTP close 가 한 번도 발동 안 함.{diag}"


# -----------------------------------------------------------------------
# 후보 (l) 확정: opposite-direction entry 시 기존 포지션 flip 안 됨 →
#                net position_size=0 → SLTP 전체 무효화
# -----------------------------------------------------------------------

def test_opposite_direction_entry_should_flip_existing_position() -> None:
    """Pine Script 표준 (pyramiding=1): opposite direction entry 는 기존 포지션을 자동 close.

    현재 버그: LONG id="A" open 상태에서 SHORT id="B" entry 호출 시
    두 포지션이 동시에 유지됨 → position_size = 1 + (-1) = 0.
    → `if strategy.position_size > 0:` 같은 SLTP long 조건 False → SL/TP 전체 무효화.

    기대 동작: SHORT entry 가 들어올 때 기존 LONG 자동 close → 순수 SHORT 1개만 open.
    """
    source = """//@version=5
strategy("t")
if bar_index == 1
    strategy.entry("A", strategy.long, qty=1.0)
if bar_index == 3
    strategy.entry("B", strategy.short, qty=1.0)
"""
    interp, _ = _run_and_collect(source, [10.0, 20.0, 30.0, 40.0, 50.0])

    state = interp.strategy

    # Pine 표준: LONG 이 SHORT 로 flip 될 때 기존 LONG 은 close 되어야.
    # 기대: closed_trades 에 "A" 1건, open_trades 에 "B" SHORT 만 있음.
    long_opens = [t for t in state.open_trades.values() if t.direction == "long"]
    short_opens = [t for t in state.open_trades.values() if t.direction == "short"]

    assert len(long_opens) == 0, (
        f"LONG open 이 SHORT entry 에 의해 flip 되지 않음 (Pine pyramiding=1 위반). "
        f"long_opens={long_opens}, short_opens={short_opens}, "
        f"net_position_size={state.position_size}"
    )
    assert state.position_size == -1.0, (
        f"net position 이 -1 (SHORT 1) 이어야 함. actual={state.position_size}. "
        f"현재 버그: LONG + SHORT 동시 유지로 net=0 → SLTP 조건 모두 False"
    )
    assert len(state.closed_trades) == 1 and state.closed_trades[0].id == "A"


def test_sltp_with_opposite_entries_still_fires() -> None:
    """real s1_pbr_sltp 축소: LONG entry 중 SHORT entry 개입 → SLTP 는 여전히 작동해야.

    bar 1: LONG entry at 100
    bar 2: SHORT entry at 120 (기존 LONG flip 되어야)
    bar 3: close=130 → SHORT 이 1% 이상 올랐으므로 SL 성립 → close 예상
    """
    source = """//@version=5
strategy("t")
if bar_index == 1
    strategy.entry("LONG", strategy.long, qty=1.0)
if bar_index == 2
    strategy.entry("SHORT", strategy.short, qty=1.0)

avg_px = strategy.position_avg_price
long_exit = strategy.position_size > 0 and (close >= avg_px * 1.02 or close <= avg_px * 0.99)
short_exit = strategy.position_size < 0 and (close >= avg_px * 1.01 or close <= avg_px * 0.98)
if long_exit
    strategy.close("LONG", comment="SLTP_L")
if short_exit
    strategy.close("SHORT", comment="SLTP_S")
"""
    # bar 0: 100, bar 1: 100 (LONG entry fill=100), bar 2: 120 (SHORT entry fill=120),
    # bar 3: 130 (SHORT 대비 +8.3% → SL 1% 이상), bar 4: 140
    interp, _ = _run_and_collect(source, [100.0, 100.0, 120.0, 130.0, 140.0])

    sltp_closes = [t for t in interp.strategy.closed_trades if "SLTP" in (t.comment or "")]
    assert len(sltp_closes) >= 1, (
        f"opposite entry 혼재 시 SLTP 발동 실패. "
        f"closed_trades={[(t.id, t.comment, t.entry_price, t.exit_price) for t in interp.strategy.closed_trades]}, "
        f"open_trades={[(t.id, t.direction, t.entry_price) for t in interp.strategy.open_trades.values()]}"
    )


# -----------------------------------------------------------------------
# codex Q2 blind spot: same-bar dual stop trigger 결정성
# -----------------------------------------------------------------------

def test_same_bar_dual_stop_trigger_is_deterministic() -> None:
    """long stop 과 short stop 이 같은 bar 에서 둘 다 trigger 시 체결 순서가
    dict insertion order 가 아닌 "bar open 가격과 fill_price 거리 오름차순"으로 결정.

    s1_pbr 는 bar 마다 pivot high/low 에서 long/short pending stop 을 각각 낸다.
    BTCUSDT 1h 같이 wide-range bar 에선 같은 bar 에 양 쪽 stop 이 동시에 trigger 될 수 있다.
    이전 구현은 dict insertion order 의존 → 비결정적.

    시나리오: bar open=100, high=130, low=80. long_stop=120 (open+20), short_stop=85 (open-15).
    거리: |120-100|=20, |85-100|=15 → short stop 이 먼저 체결.
    결과: short open 후 long stop 이 flip (short close) → long open.
    즉 first close 는 short (의도된 순서).
    """
    import pandas as pd

    from src.strategy.pine_v2.event_loop import run_historical

    source = """//@version=5
strategy("t")
if bar_index == 0
    strategy.entry("L", strategy.long, qty=1.0, stop=120.0)
    strategy.entry("S", strategy.short, qty=1.0, stop=85.0)
"""
    # bar 0 (placed_bar): stop 주문만 place, 체결은 다음 bar 부터
    # bar 1: open=100, high=140, low=60 — 두 stop 모두 trigger
    #   long stop=120 → high=140 >= 120 → fill_price=120, |120-100|=20
    #   short stop=85 → low=60 <= 85 → fill_price=85, |85-100|=15
    #   거리 기반 ordering: short 먼저 체결 → long 이 flip 으로 short close
    #   최종: short "S" 는 closed, long "L" 만 open
    ohlcv = pd.DataFrame({
        "open":   [100.0, 100.0],
        "high":   [101.0, 140.0],
        "low":    [ 99.0,  60.0],
        "close":  [100.0, 130.0],
        "volume": [1000.0, 1000.0],
    })
    result = run_historical(source, ohlcv, strict=True)
    state = result.strategy_state
    assert state is not None

    # 거리 기반 ordering 검증: short (|85-100|=15) 가 long (|120-100|=20) 보다 먼저
    assert len(state.closed_trades) == 1, (
        f"거리 기반 ordering 실패. closed_trades count mismatch. "
        f"actual={[(t.id, t.direction) for t in state.closed_trades]}, "
        f"open={[(tid, t.direction) for tid, t in state.open_trades.items()]}"
    )
    assert state.closed_trades[0].id == "S", (
        f"먼저 close 된 id 는 'S' 여야 함 (|85-100|<|120-100|). "
        f"actual={state.closed_trades[0].id}"
    )
    assert "L" in state.open_trades and state.open_trades["L"].direction == "long"


def test_flip_does_not_pollute_user_entry_comment() -> None:
    """codex Q1: _flip_opposite_positions 가 닫는 trade 의 comment 에 'FLIP' 을 덮어쓰면 안 됨.

    사용자가 entry 시 지정한 comment (예: "PivRevLE") 가 flip close 이후에도 보존되어야 한다.
    TradingView 는 reverse close 에 synthetic comment 를 부여하지 않음.
    """
    source = """//@version=5
strategy("t")
if bar_index == 1
    strategy.entry("A", strategy.long, qty=1.0, comment="PivRevLE")
if bar_index == 3
    strategy.entry("B", strategy.short, qty=1.0, comment="PivRevSE")
"""
    interp, _ = _run_and_collect(source, [10.0, 20.0, 30.0, 40.0, 50.0])

    # Flip 으로 닫힌 "A" 의 comment 는 entry comment 그대로 유지
    assert len(interp.strategy.closed_trades) == 1
    flipped = interp.strategy.closed_trades[0]
    assert flipped.id == "A"
    assert flipped.comment == "PivRevLE", (
        f"flip close 가 사용자 comment 를 오염시킴. actual={flipped.comment!r}. "
        f"TradingView 는 reverse trade 에 synthetic comment 를 부여하지 않아야 한다."
    )
    # 'FLIP' 토큰은 어떤 trade 의 comment 에도 나타나면 안 됨
    assert "FLIP" not in (flipped.comment or "")
