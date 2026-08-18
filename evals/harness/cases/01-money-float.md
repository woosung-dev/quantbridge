---
id: 01-money-float
rule: 가격·수량·수익률 등 금융 숫자는 Decimal 로 다루고 float 를 쓰지 않는다. 합산도 Decimal 공간에서 한다.
rule_source: apps/api/AGENTS.md > §2 Decimal-first 금융 숫자
expect: violation
severity: critical
---

체결 손익 계산을 float 로 처리해 부동소수 오차가 생긴다.

```diff
# apps/api/src/backtest/service.py
+def realized_pnl(entry_price: str, exit_price: str, qty: str) -> float:
+    """청산 손익 = (청산가 - 진입가) * 수량."""
+    return (float(exit_price) - float(entry_price)) * float(qty)
```
