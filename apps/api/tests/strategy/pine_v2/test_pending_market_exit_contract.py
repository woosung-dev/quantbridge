"""미체결 시장가 진입의 첫 체결 봉 보호·취소·라이브 차단 계약."""

import unittest

import pandas as pd

from src.strategy.pine_v2.event_loop import run_historical, run_live
from src.strategy.pine_v2.strategy_state import MarketIntent, StrategyState

SOURCE = """//@version=5
strategy("first fill")
if bar_index == 0
    strategy.entry("L", strategy.long, qty=2)
    strategy.exit("X", "L", stop=90)
"""


def frame(high=105.0, low=85.0, opening=100.0):
    return pd.DataFrame(
        {
            "open": [100.0, opening, 100.0],
            "high": [102.0, high, 103.0],
            "low": [98.0, low, 95.0],
            "close": [100.0, 100.0, 100.0],
            "volume": [1.0, 1.0, 1.0],
        },
        index=pd.date_range("2025-01-01", periods=3, freq="h", tz="UTC"),
    )


def queued(trade_id="L", direction="long", qty=2.0):
    s = StrategyState(fill_timing="next_bar_open")
    s.queue_market_intent(MarketIntent("entry", trade_id, direction, qty, placed_bar=0))
    return s


def fill(s, bar=1, opening=100.0):
    s.process_market_intents(bar=bar, open_=opening)


def exits(s, bar=1, high=105.0, low=85.0, opening=100.0):
    return s.check_exit_fills(bar=bar, open_=opening, high=high, low=low)


class PendingProtectionTests(unittest.TestCase):
    def test_original_three_bar_stop_red(self):
        r = run_historical(SOURCE, frame(), fill_timing="next_bar_open")
        self.assertEqual(r.errors, [])
        self.assertEqual(len(r.strategy_state.closed_trades), 1)
        t = r.strategy_state.closed_trades[0]
        self.assertEqual(
            (t.entry_bar, t.exit_bar, t.entry_price, t.exit_price, t.qty), (1, 1, 100.0, 90.0, 2.0)
        )

    def test_short_first_bar_stop(self):
        code = SOURCE.replace("strategy.long", "strategy.short").replace("stop=90", "stop=110")
        r = run_historical(code, frame(high=115.0, low=95.0), fill_timing="next_bar_open")
        self.assertEqual([t.exit_price for t in r.strategy_state.closed_trades], [110.0])

    def test_partial_tp_and_remaining_protection_cost_conservation(self):
        s = queued()
        s.configure_sizing(initial_capital=1000.0, taker_cost_rate=0.001)
        s.place_exit(from_entry="L", exit_id="A", bar=0, stop=90, limit=110, qty_percent=50)
        s.place_exit(from_entry="L", exit_id="B", bar=0, stop=90)
        fill(s)
        exits(s, high=115.0, low=95.0)
        self.assertEqual([(t.qty, t.exit_price) for t in s.closed_trades], [(1.0, 110.0)])
        self.assertEqual(s.open_trades["L"].qty, 1.0)
        self.assertEqual({x.exit_id for x in s.pending_exits["L"]}, {"B"})
        exits(s, bar=2, high=103.0, low=85.0)
        self.assertEqual(sum(t.qty for t in s.closed_trades), 2.0)
        self.assertAlmostEqual(s.gate_equity, 999.6)

    def test_reservation_clamps_at_actual_fill_quantity(self):
        s = queued()
        for name in ["A", "B"]:
            s.place_exit(from_entry="L", exit_id=name, bar=0, stop=90, qty_percent=70)
        fill(s)
        self.assertEqual(
            [(x.exit_id, x.qty) for x in s.pending_exits["L"]], [("A", 1.4), ("B", 0.6)]
        )

    def test_frozen_submission_and_activation_bars(self):
        s = queued()
        s.place_exit(from_entry="L", exit_id="X", bar=0, stop=90)
        fill(s, bar=3)
        leg = s.pending_exits["L"][0]
        self.assertEqual((leg.placed_bar, s.open_trades["L"].entry_bar, leg.stop_price), (0, 3, 90))
        self.assertEqual(s.open_trades["L"].entry_phase, "bar_open")
        self.assertFalse(s.pending_market_exits)

    def test_same_exit_id_replaces_template(self):
        s = queued()
        s.place_exit(from_entry="L", exit_id="X", bar=0, stop=80)
        s.place_exit(from_entry="L", exit_id="X", bar=0, stop=90)
        fill(s)
        exits(s)
        self.assertEqual([t.exit_price for t in s.closed_trades], [90.0])

    def test_cancel_exit_keeps_pending_entry(self):
        s = queued()
        s.place_exit(from_entry="L", exit_id="X", bar=0, stop=90)
        s.cancel("X")
        fill(s)
        exits(s)
        self.assertEqual(len(s.open_trades), 1)
        self.assertFalse(s.pending_exits)
        self.assertFalse(getattr(s, "pending_market_exits", {}))

    def test_cancel_entry_then_same_id_reentry_does_not_inherit(self):
        s = queued()
        s.place_exit(from_entry="L", exit_id="X", bar=0, stop=90)
        old = s.pending_market_intents[0].exit_generation
        s.cancel("L")
        s.queue_market_intent(MarketIntent("entry", "L", qty=2, placed_bar=0))
        self.assertNotEqual(old, s.pending_market_intents[0].exit_generation)
        fill(s)
        exits(s)
        self.assertEqual(len(s.open_trades), 1)
        self.assertFalse(s.pending_exits)
        self.assertFalse(s.pending_market_exits)

    def test_cancel_all_keeps_open_position(self):
        s = queued()
        s.entry("old", "long", qty=1, bar=0, fill_price=100)
        s.place_exit(from_entry="L", exit_id="X", bar=0, stop=90)
        s.cancel_all()
        fill(s)
        self.assertEqual(set(s.open_trades), {"old"})
        self.assertFalse(getattr(s, "pending_market_exits", {}))

    def test_reversal_removes_old_protection_and_uses_new_direction(self):
        s = queued()
        s.place_exit(from_entry="L", exit_id="X", bar=0, stop=90)
        fill(s)
        s.queue_market_intent(MarketIntent("entry", "S", "short", 2, placed_bar=1))
        s.place_exit(from_entry="S", exit_id="Y", bar=1, stop=110)
        fill(s, bar=2)
        exits(s, bar=2, high=115.0, low=95.0)
        self.assertEqual(
            [(t.id, t.exit_price) for t in s.closed_trades], [("L", 100.0), ("S", 110.0)]
        )
        self.assertFalse(s.pending_exits)

    def test_closed_id_reentry_has_no_stale_template(self):
        s = queued()
        s.place_exit(from_entry="L", exit_id="X", bar=0, stop=90)
        fill(s)
        exits(s)
        s.queue_market_intent(MarketIntent("entry", "L", qty=2, placed_bar=1))
        fill(s, bar=2)
        self.assertEqual(len(s.closed_trades), 1)
        self.assertEqual(len(s.open_trades), 1)
        self.assertFalse(s.pending_exits)

    def test_epoch_preserves_only_still_pending_entry_protection(self):
        s = queued()
        s.entry("old", "long", qty=1, bar=0, fill_price=100)
        s.place_exit(from_entry="old", exit_id="oldx", bar=0, stop=90)
        s.place_exit(from_entry="L", exit_id="X", bar=0, stop=90)
        s.discard_state_before_epoch()
        fill(s)
        exits(s)
        self.assertEqual([(t.id, t.exit_price) for t in s.closed_trades], [("L", 90.0)])
        self.assertFalse(s.pending_exits)

    def test_gap_stop_uses_open_not_signal_price(self):
        s = queued()
        s.place_exit(from_entry="L", exit_id="X", bar=0, stop=90)
        fill(s, opening=85.0)
        exits(s, opening=85.0, low=80.0, high=100.0)
        self.assertEqual([(t.entry_price, t.exit_price) for t in s.closed_trades], [(85.0, 85.0)])

    def test_rejected_entry_consumes_template_without_activation(self):
        s = queued(qty=1000.0)
        s.configure_sizing(initial_capital=1.0, leverage=2.0)
        s.place_exit(from_entry="L", exit_id="X", bar=0, stop=90)
        fill(s)
        self.assertFalse(s.open_trades)
        self.assertFalse(s.pending_exits)
        self.assertFalse(s.pending_market_exits)

    def test_same_id_multiple_pending_entries_are_explicitly_rejected(self):
        s = queued()
        s.queue_market_intent(MarketIntent("entry", "L", qty=1))
        with self.assertRaisesRegex(ValueError, "multiple pending"):
            s.place_exit(from_entry="L", exit_id="X", bar=0, stop=90)

    def test_second_same_id_entry_after_protected_intent_is_rejected(self):
        s = queued()
        s.place_exit(from_entry="L", exit_id="X", bar=0, stop=90)
        with self.assertRaisesRegex(ValueError, "multiple pending"):
            s.queue_market_intent(MarketIntent("entry", "L", qty=1))

    def test_live_single_literal_pending_bracket_is_blocked_from_first_signal(self):
        for count in [1, 2]:
            r = run_live(SOURCE, frame().iloc[:count], fill_timing="next_bar_open")
            self.assertFalse(r.signals)
            self.assertFalse(r.pending_orders)
            self.assertTrue(any("pending_market_exit_unsupported_live" in str(e) for e in r.errors))

    def test_barclose_single_bracket_v1_live_is_unchanged(self):
        r = run_live(SOURCE, frame().iloc[:1], fill_timing="bar_close")
        self.assertEqual(r.errors, [])
        self.assertEqual(len(r.signals), 1)
        self.assertEqual(str(r.signals[0].stop_loss), "90.0")

    def test_barclose_does_not_use_signal_bar_prior_low(self):
        r = run_historical(SOURCE, frame(), fill_timing="bar_close")
        self.assertEqual(
            [(t.entry_bar, t.exit_bar) for t in r.strategy_state.closed_trades], [(0, 1)]
        )

    def test_trailing_activation_can_close_in_first_entry_bar(self):
        s = queued()
        s.place_exit(from_entry="L", exit_id="X", bar=0, stop=90, trail_price=120, trail_offset=5)
        fill(s)
        exits(s, high=125.0, low=100.0)
        self.assertEqual([t.exit_price for t in s.closed_trades], [120.0])

    def test_session_delay_preserves_template_until_actual_fill(self):
        from datetime import UTC, datetime

        s = queued()
        s.sessions_allowed = ("london",)
        s.place_exit(from_entry="L", exit_id="X", bar=0, stop=90)
        s.process_market_intents(bar=1, open_=100.0, bar_ts=datetime(2025, 1, 1, 7, tzinfo=UTC))
        self.assertFalse(s.open_trades)
        s.process_market_intents(bar=2, open_=100.0, bar_ts=datetime(2025, 1, 1, 8, tzinfo=UTC))
        s.check_exit_fills(
            bar=2, open_=100.0, high=105.0, low=85.0, bar_ts=datetime(2025, 1, 1, 8, tzinfo=UTC)
        )
        self.assertEqual(
            [(t.entry_bar, t.exit_bar, t.exit_price) for t in s.closed_trades], [(2, 2, 90.0)]
        )

    def test_close_intent_precedes_first_bar_intrabar_exit_check(self):
        s = queued()
        s.place_exit(from_entry="L", exit_id="X", bar=0, stop=90)
        s.queue_market_intent(MarketIntent("close", "L", placed_bar=0))
        fill(s)
        exits(s)
        self.assertEqual([t.exit_price for t in s.closed_trades], [100.0])
        self.assertFalse(s.pending_exits)
        self.assertFalse(getattr(s, "pending_market_exits", {}))

    def test_mixed_conditional_entry_after_protected_market_is_rejected(self):
        s = queued()
        s.place_exit(from_entry="L", exit_id="X", bar=0, stop=90)
        with self.assertRaisesRegex(ValueError, "mixed conditional"):
            s.entry("L", "long", qty=1, bar=0, fill_price=100.0, stop=101.0)

    def test_mixed_conditional_entry_before_market_template_is_rejected(self):
        s = queued()
        s.entry("L", "long", qty=1, bar=0, fill_price=100.0, stop=101.0)
        with self.assertRaisesRegex(ValueError, "mixed conditional"):
            s.place_exit(from_entry="L", exit_id="X", bar=0, stop=90)

    def test_old_nextbar_entry_only_live_remains_enabled(self):
        code = SOURCE.split("    strategy.exit")[0]
        r = run_live(code, frame().iloc[:2], fill_timing="next_bar_open")
        self.assertEqual(r.errors, [])
        self.assertEqual([x.action for x in r.signals], ["entry"])

    def test_no_exit_and_missing_target_preserve_existing_behavior(self):
        s = queued()
        s.place_exit(from_entry="missing", exit_id="X", bar=0, stop=90)
        fill(s)
        exits(s)
        self.assertEqual(len(s.open_trades), 1)
        self.assertFalse(s.pending_exits)


if __name__ == "__main__":
    unittest.main(verbosity=2)
