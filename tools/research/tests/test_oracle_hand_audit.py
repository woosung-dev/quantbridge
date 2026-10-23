"""공개 규칙의 손계산으로 독립 oracle을 검사한다. 생성물·compiler·pilot 결과는 읽지 않는다.

한계: 작성자는 C compiler 작성에 참여했다. 저자 간 완전 독립을 주장하지 않는다.
예상값은 상수 수열·유한 SMA·명시한 분수로 고정하며 oracle 출력을 정답으로 복제하지 않는다.
oracle의 다른 26전략, 경제 성과, TradingView 동등성까지 검증하는 테스트가 아니다.
"""

import hashlib
import importlib.util
import math
from datetime import UTC, datetime, timedelta
from fractions import Fraction
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
ORACLE_FILE = ROOT / "tools/research/strategy_oracle.py"
if not ORACLE_FILE.exists():
    # C 워크트리에 oracle이 없을 때만 동결 control 사본을 읽기 전용으로 검사한다.
    ORACLE_FILE = ROOT.with_name("quant-bridge-sol-control") / "tools/research/strategy_oracle.py"
BEFORE_HASH = hashlib.sha256(ORACLE_FILE.read_bytes()).hexdigest()
SPEC = importlib.util.spec_from_file_location("oracle_for_hand_audit", ORACLE_FILE)
assert SPEC is not None and SPEC.loader is not None
ORACLE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ORACLE)


@pytest.fixture(scope="module", autouse=True)
def oracle_is_read_only():
    yield
    assert hashlib.sha256(ORACLE_FILE.read_bytes()).hexdigest() == BEFORE_HASH


def bars(closes, *, high=None, low=None):
    result = []
    for index, close in enumerate(closes):
        price = float(close)
        result.append(
            {
                "timestamp": (
                    datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=index)
                ).isoformat(),
                "open": str(price),
                "close": str(price),
                "high": str(high if high is not None else price + 1),
                "low": str(low if low is not None else price - 1),
                "volume": "1",
            }
        )
    return result


def action(ident, history, direction="flat", state=None):
    return ORACLE.expected_action(
        ident, history, {"direction": direction}, {} if state is None else state
    )


def math_for(history):
    result = ORACLE._Math()
    result.extend(history)
    return result


def test_ema_three_sma_seed_and_wilder_seed_by_hand():
    # EMA3 alpha=1/2: SMA(3,3,3)=3, 다음 6→4.5, 3→3.75, 0→1.875.
    # Wilder3 alpha=1/3: 3→4→11/3→22/9. 첫 값 seed나 0 초기화가 아니다.
    data = math_for(bars([3, 3, 3, 6, 3, 0]))
    ema = data.ema(3)
    rma = data.smooth("hand_rma3", data.fields["close"], 3, wilder=True)
    assert all(math.isnan(x) for x in ema[:2])
    assert ema[2:] == pytest.approx(
        [3, Fraction(9, 2), Fraction(15, 4), Fraction(15, 8)], abs=1e-12, rel=0
    )
    assert all(math.isnan(x) for x in rma[:2])
    assert rma[2:] == pytest.approx([3, 4, Fraction(11, 3), Fraction(22, 9)], abs=1e-12, rel=0)


@pytest.mark.parametrize(
    "a,b,up,expected",
    [
        ([1, 2], [1, 1], True, True),  # 이전 같음은 허용, 현재는 엄격한 상향.
        ([1, 1], [1, 1], True, False),
        ([2, 2], [1, 1], True, False),  # 이미 위에 있었으면 새 교차가 아니다.
        ([1, 0], [1, 1], False, True),
        ([0, 0], [1, 1], False, False),
        ([float("nan"), 2], [1, 1], True, False),
        ([1, 2], [float("nan"), 1], True, False),
        ([1, float("nan")], [1, 1], True, False),
        ([1], [0], True, False),
    ],
)
def test_cross_equality_strict_current_and_na(a, b, up, expected):
    assert ORACLE._cross(a, b, up=up) is expected


def test_catalogue_01_ema20_50_first_seed_na_and_equal_prior_cross():
    # 49번째(0-based) slow seed=(49*100+151)/50=5051/50.
    # EMA20의 직전 값100에 2/21*51을 더하면734/7이다.
    initial_jump = bars([100] * 49 + [151])
    data = math_for(initial_jump)
    assert all(math.isnan(x) for x in data.ema(50)[:49])
    assert data.ema(50)[49] == pytest.approx(float(Fraction(5051, 50)), abs=1e-12, rel=0)
    assert data.ema(20)[49] == pytest.approx(float(Fraction(734, 7)), abs=1e-12, rel=0)
    assert action("01", initial_jump) == "hold"  # 이전 slow NA는 교차가 아니다.
    base = bars([100] * 50)
    assert action("01", base) == "hold"
    assert action("01", bars([100] * 50 + [151])) == "long"
    assert action("01", bars([100] * 50 + [49])) == "short"
    assert action("01", bars([100] * 50 + [49]), "long") == "short"  # 반전 우선.
    assert action("01", bars([100] * 50 + [151, 151])) == "hold"  # 지속 추세≠재교차.


def test_catalogue_02_price_reclaim_is_not_an_ema_pair_recross():
    # E20: 100 →734/7→15388/147→323242/3087.
    # E50: 100→102→5204/51→265706/2601.
    # 103봉은 fast 아래/slow 위, 다음105는 fast 위로 복귀. 두 EMA는 계속 fast>slow.
    history = bars([100] * 50 + [151, 103, 105])
    data = math_for(history)
    assert data.ema(20)[-3:] == pytest.approx(
        [float(Fraction(734, 7)), float(Fraction(15388, 147)), float(Fraction(323242, 3087))],
        abs=1e-12,
        rel=0,
    )
    assert data.ema(50)[-3:] == pytest.approx(
        [102, float(Fraction(5204, 51)), float(Fraction(265706, 2601))], abs=1e-12, rel=0
    )
    assert action("02", history[:-1]) == "hold"
    assert action("02", history) == "long"
    assert action("01", history) == "hold"
    assert action("02", bars([100] * 50 + [49, 97, 95])) == "short"  # 200-C 대칭.
    assert action("02", bars([100] * 50 + [151, 103, 105, 100]), "long") == "close"


@pytest.mark.parametrize("ident,length", [("D02", 7), ("03", 20), ("04", 55)])
def test_channel_excludes_current_and_requires_finite_previous_channel(ident, length):
    initial = bars([8] * length + [11], high=10, low=5)
    initial[-1]["high"] = "100"
    data = math_for(initial)
    upper, lower = data.channel(length)
    assert all(math.isnan(x) for x in upper[:length])
    assert upper[-1] == 10 and lower[-1] == 5
    assert action(ident, initial) == "hold"  # 현재 상단10은 있으나 이전 상단은 NA.
    history = bars([8] * (length + 1) + [11], high=10, low=5)
    history[-1]["high"] = "100"
    assert action(ident, history) == "long"
    history[-1].update(close="4", low="1", high="10")
    assert action(ident, history) == "short"


@pytest.mark.parametrize("ident,length", [("D02", 7), ("03", 20)])
def test_channel_midpoint_exit_is_strict(ident, length):
    # 이전 채널[5,10]의 중간7.5. 현재 high/low는 이 중간 계산에 들어가지 않는다.
    history = bars([8] * (length + 1) + [Fraction(15, 2)], high=10, low=5)
    history[-1].update(high="100", low="1")
    assert action(ident, history, "long") == "hold"
    history[-1]["close"] = "7"
    assert action(ident, history, "long") == "close"
    history[-1]["close"] = "8"
    assert action(ident, history, "short") == "close"


def test_catalogue_04_twenty_bar_exit_is_neither_55_bar_breakout_nor_midpoint():
    # 직전55창은[1,20], 직전20창은[8,12]. 마지막 현재봉은 어느 창에도 포함하지 않는다.
    early = bars([10] * 36, high=20, low=1)
    recent = bars([10] * 20, high=12, low=8)
    history = bars([10] * 56 + [9])
    for target, source in zip(history[:56], early + recent, strict=True):
        target.update(high=source["high"], low=source["low"])
    history[-1].update(high="13", low="6")
    assert action("04", history, "long") == "hold"  # 9<55중간10.5이지만 exit low8은 안 깼다.
    history[-1]["close"] = "8"
    assert action("04", history, "long") == "hold"
    history[-1]["close"] = "7"
    assert action("04", history, "long") == "close"  # 55봉 short breakout은 아니다.
    history[-1]["close"] = "13"
    assert action("04", history, "short") == "close"


def test_dev_01_sma_seed_and_equal_prior_cross_hand_means():
    first = bars([10] * 7 + [18])
    data = math_for(first)
    assert all(math.isnan(x) for x in data.sma(8)[:7])
    assert data.sma(3)[-1] == pytest.approx(float(Fraction(38, 3)), abs=1e-12, rel=0)
    assert data.sma(8)[-1] == 11
    assert action("D01", first) == "hold"  # 이전SMA8 NA.
    assert action("D01", bars([10] * 8 + [18])) == "long"
    assert action("D01", bars([10] * 8 + [2])) == "short"
    assert action("D01", bars([10] * 9)) == "hold"


def test_dev_03_rsi_wilder_seed_flat_policy_and_ema_filter_hand_values():
    # 0/0 RSI는 공개 계약의100이다(수학적으로 유일한 값 또는 TV 보장이라는 뜻은 아님).
    # 15개100 뒤93: Wilder7 gain0/loss1→RSI0, EMA15=100-7/8=793/8.
    # 다음100: gain1/loss6/7→RSI700/13, EMA15=6351/64.
    history = bars([100] * 15 + [93, 100])
    data = math_for(history)
    rsi = data.rsi(7)
    assert all(math.isnan(x) for x in rsi[:7])
    assert rsi[7:15] == [100] * 8
    assert rsi[-2:] == pytest.approx([0, float(Fraction(700, 13))], abs=1e-12, rel=0)
    assert all(math.isnan(x) for x in data.ema(15)[:14])
    assert data.ema(15)[-2:] == pytest.approx(
        [float(Fraction(793, 8)), float(Fraction(6351, 64))], abs=1e-12, rel=0
    )
    assert action("D03", history[:-1]) == "short"
    assert action("D03", history) == "long"
    assert action("D03", bars([100] * 15)) == "hold"
    assert action("D03", bars([100] * 15 + [93, 100, 100])) == "hold"


def test_dev_04_macd_signal_sma_seed_and_two_crosses_by_hand():
    # 15개100 뒤108: EMA3=104, EMA7=102, MACD2, signal2=(2/3)*2=4/3.
    # 다음100: EMA3=102, EMA7=101.5, MACD1/2, signal=(2/3)*(1/2)+(1/3)*(4/3)=7/9.
    history = bars([100] * 15 + [108, 100])
    data = math_for(history)
    line, signal = data.macd(3, 7, 2)
    assert all(math.isnan(x) for x in line[:6])
    assert line[6:15] == [0] * 9
    assert all(math.isnan(x) for x in signal[:7])
    assert signal[7:15] == [0] * 8
    assert line[-2:] == [2, Fraction(1, 2)]
    assert signal[-2:] == pytest.approx(
        [float(Fraction(4, 3)), float(Fraction(7, 9))], abs=1e-12, rel=0
    )
    assert data.ema(15)[-2:] == [101, 100.875]
    assert action("D04", history[:-1]) == "long"
    assert action("D04", history) == "short"


def test_prefix_queries_do_not_look_ahead_and_incremental_state_matches_prefixes():
    history = bars([100] * 50 + [151])
    state = {}
    assert action("01", history[:49], state=state) == "hold"
    assert action("01", history[:50], state=state) == "hold"
    assert action("01", history, state=state) == "long"
    assert action("01", history[:50], state=state) == "hold"  # 축소 입력은 새 상태로 재구성.
