"""포지션 복원의 경계·반익절·반전·부호·원장 오류 회귀."""

import unittest
from decimal import getcontext

from tools.research.mtf_validation_v1 import callback_positions


CONTEXT = {key: getattr(getcontext(), key) for key in ("prec", "rounding", "Emin", "Emax", "capitals", "clamp")}


def bar(hour):
    return {"timestamp": f"2026-01-01T{hour:02d}:00:00+00:00"}


def fill(when, kind, quantity, generation=1, direction="long", price="100"):
    return {"timestamp": f"2026-01-01T{when}+00:00", "kind": kind, "quantity": quantity,
            "generation": generation, "direction": direction, "price": price}


class CallbackPositionTests(unittest.TestCase):
    def test_next_open_is_not_visible_to_previous_callback(self):
        actual = callback_positions([bar(0), bar(1), bar(2)], [fill("01:00:00", "entry", "2"),
                                    fill("01:30:00", "partial_tp", "1"), fill("02:00:00", "close", "1")], "1h", CONTEXT)
        self.assertEqual(actual, [{"size": "0", "direction": "flat", "average_price": None},
                                  {"size": "1", "direction": "long", "average_price": "100"},
                                  {"size": "0", "direction": "flat", "average_price": None}])

    def test_short_size_remains_unsigned_and_reversal_keeps_trace_order(self):
        actual = callback_positions([bar(0), bar(1)], [fill("00:00:00", "entry", "3"), fill("01:00:00", "close", "3"),
                                    fill("01:00:00", "entry", "2", 2, "short", "200")], "1h", CONTEXT)
        self.assertEqual(actual[-1], {"size": "2", "direction": "short", "average_price": "200"})

    def test_partial_rounding_matches_recorded_decimal_context(self):
        context = {**CONTEXT, "prec": 28}
        actual = callback_positions([bar(0)], [fill("00:00:00", "entry", "0.2335139174294787969362974033"),
                                    fill("00:30:00", "partial_tp", "0.1167569587147393984681487016")], "1h", context)
        self.assertEqual(actual[0]["size"], "0.1167569587147393984681487017")

    def test_invalid_ledger_is_rejected(self):
        cases = [[fill("00:00:00", "entry", "1"), fill("00:01:00", "entry", "1", 2)],
                 [fill("00:00:00", "entry", "1"), fill("00:01:00", "close", "2")],
                 [fill("00:00:00", "entry", "1"), fill("00:01:00", "close", "1", 2)],
                 [fill("00:00:00", "entry", "NaN")], [fill("01:00:00", "entry", "1")],
                 [fill("00:30:00", "entry", "1"), fill("00:00:00", "close", "1")]]
        for events in cases:
            with self.subTest(events=events), self.assertRaises(ValueError):
                callback_positions([bar(0)], events, "1h", CONTEXT)


if __name__ == "__main__":
    unittest.main()
