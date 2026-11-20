"""미래 OHLCV·달력 경계·같은 시간봉 초기화 회귀. 전략 코드는 실행하지 않는다."""

import unittest
from datetime import timedelta

from tools.research.mtf_v1.feeds import CausalFeeds, FeedCursor, canonical_timeframe, end_time, instant


def row(when, close="100"):
    return {"timestamp": when, "open": "100", "high": "999", "low": "1", "close": close, "volume": "4"}


class CausalFeedTests(unittest.TestCase):
    def test_unclosed_extremes_and_next_open_are_absent(self):
        rows = [row("2024-01-01T00:00:00+00:00", "321"), row("2024-01-01T04:00:00+00:00", "654")]
        rows[1]["open"] = "777"
        feeds = CausalFeeds("60", {"240": FeedCursor(rows, "240")})
        packets = [feeds.for_bar(row(f"2024-01-01T0{i}:00:00+00:00"))["feeds"]["240"] for i in range(4)]
        for packet in packets[:3]:
            self.assertEqual(packet["new_closed"], [])
            self.assertEqual(set(packet["current"]), {"timestamp", "end_timestamp", "open"})
            self.assertEqual(packet["current"]["open"], "100")
        self.assertEqual([x["close"] for x in packets[3]["new_closed"]], ["321"])
        self.assertEqual(packets[3]["current"]["open"], "100")

    def test_future_remote_mutation_preserves_prefix(self):
        packets = []
        for future in ("1040", "50"):
            feeds = CausalFeeds("60", {"240": FeedCursor([row("2024-01-01T00:00:00+00:00", future)], "240")})
            packets.append([feeds.for_bar(row(f"2024-01-01T0{i}:00:00+00:00")) for i in range(3)])
        self.assertEqual(*packets)

    def test_same_timeframe_has_no_extra_seed(self):
        feeds = CausalFeeds("60", {"chart": FeedCursor([row("2023-12-31T23:00:00+00:00"), row("2024-01-01T00:00:00+00:00")], "60")})
        packet = feeds.for_bar(row("2024-01-01T00:00:00+00:00"))["feeds"]["chart"]
        self.assertEqual(len(packet["new_closed"]), 1)
        self.assertEqual(packet["new_closed"][0]["timestamp"], "2024-01-01T00:00:00+00:00")

    def test_lower_timeframe_intrabar_order_and_membership(self):
        start = instant("2024-01-01T00:00:00+00:00")
        rows = [row((start + timedelta(minutes=i)).isoformat(), str(i)) for i in range(-2, 61)]
        packet = CausalFeeds("60", {"1": FeedCursor(rows, "1")}).for_bar(row(start.isoformat()))["feeds"]["1"]
        self.assertEqual(len(packet["new_closed"]), 62)
        self.assertEqual([x["close"] for x in packet["intrabars"]], [str(i) for i in range(60)])
        self.assertEqual(packet["current"]["timestamp"], start.isoformat())

    def test_seed_limit_does_not_truncate_later_deltas(self):
        start = instant("2024-01-01T00:00:00+00:00")
        rows = [row((start + timedelta(hours=i)).isoformat()) for i in range(-10, 8)]
        feeds = CausalFeeds("240", {"60": FeedCursor(rows, "60", initial_closed_limit=3)})
        first = feeds.for_bar(row(start.isoformat()))["feeds"]["60"]
        second = feeds.for_bar(row((start + timedelta(hours=4)).isoformat()))["feeds"]["60"]
        self.assertEqual(len(first["new_closed"]), 7)
        self.assertEqual(len(first["intrabars"]), 4)
        self.assertEqual(len(second["new_closed"]), 4)

    def test_missing_remote_bar_is_not_synthesized(self):
        feeds = CausalFeeds("60", {"60": FeedCursor([row("2024-01-01T01:00:00+00:00")], "60")})
        packet = feeds.for_bar(row("2024-01-01T00:00:00+00:00"))["feeds"]["60"]
        self.assertEqual(packet["new_closed"], [])
        self.assertIsNone(packet["current"])

    def test_calendar_ends_follow_leap_year_and_year_change(self):
        cases = [("2024-02-01T00:00:00+00:00", "M", "2024-03-01T00:00:00+00:00"),
                 ("2023-12-01T00:00:00+00:00", "1M", "2024-01-01T00:00:00+00:00"),
                 ("2024-02-26T00:00:00+00:00", "W", "2024-03-04T00:00:00+00:00")]
        for start, tf, expected in cases:
            self.assertEqual(end_time(instant(start), tf), instant(expected))

    def test_semantic_units_are_not_aliased(self):
        self.assertEqual(canonical_timeframe("", "60"), "60")
        self.assertEqual(canonical_timeframe("D"), "1D")
        self.assertNotEqual(canonical_timeframe("1440"), canonical_timeframe("D"))
        for value in ("M15", "0", "1441", "13M", "1h"):
            with self.assertRaises(ValueError):
                canonical_timeframe(value)

    def test_nonmonotone_parents_and_remote_rows_rejected(self):
        now = instant("2024-01-01T00:00:00+00:00")
        cursor = FeedCursor([row(now.isoformat()), row(now.isoformat())], "60")
        with self.assertRaisesRegex(ValueError, "원격 봉"):
            cursor.advance(now, now + timedelta(hours=1))
        cursor = FeedCursor([], "60")
        cursor.advance(now, now + timedelta(hours=1))
        with self.assertRaisesRegex(ValueError, "부모 봉"):
            cursor.advance(now, now + timedelta(hours=1))


if __name__ == "__main__":
    unittest.main()
