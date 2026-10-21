"""평탄한 Pine 분기의 외부 포지션·동시 진입·청산 우선순위를 검증한다."""

from src.strategy.code_runtime.compiler import compile_strategy
from src.strategy.code_runtime.pine import _PineInterpreterTransport
from tests.strategy.code_runtime.test_backtest import frame


def test_flat_pine_dispatch_respects_external_position_without_entry_ids() -> None:
    def condition(op, series, value):
        return {"op": op, "left": {"series": series}, "right": {"constant": value}}

    spec = {
        "title": "flat dispatch",
        "warmup_bars": 1,
        "long_entry": condition("gte", "high", 105),
        "short_entry": condition("lte", "low", 95),
        "long_invalidation": condition("lt", "close", 103),
        "short_invalidation": condition("gt", "close", 97),
    }
    source = compile_strategy(spec, "pine")
    assert "else if" not in source
    assert "strategy.close(" not in source
    assert all(
        line.startswith("if ") for line in source.splitlines() if line.lstrip().startswith("if ")
    )
    # 첫 두 봉에는 과거 entry가 없다. 외부 보유 포지션의 무효화도 청산되어야 한다.
    cases = [
        ("long", 104, 96, "close"),
        ("short", 104, 96, "close"),
        ("flat", 106, 96, "long"),
        ("flat", 104, 94, "short"),
        ("flat", 106, 94, "hold"),
        ("long", 104, 94, "short"),
        ("short", 106, 96, "long"),
        ("long", 106, 96, "close"),
        ("short", 104, 94, "close"),
        ("long", 106, 94, "hold"),
    ]
    data = frame([(100, high, low, 100) for _, high, low, _ in cases])
    engine = _PineInterpreterTransport(data)
    try:
        assert engine.exchange({"type": "init", "protocol": 1, "source": source, "params": {}}) == {
            "ready": 1
        }
        for index, (direction, _, _, expected) in enumerate(cases):
            reply = engine.exchange(
                {
                    "type": "bar",
                    "bar": {"index": index},
                    "position": {
                        "direction": direction,
                        "size": "0" if direction == "flat" else "10",
                        "average_price": None if direction == "flat" else "100",
                    },
                }
            )
            assert reply == {"intent": {"action": expected}}, (index, direction)
    finally:
        engine.close()
