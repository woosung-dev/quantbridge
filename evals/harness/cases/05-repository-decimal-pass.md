---
id: 05-repository-decimal-pass
rule: (오탐 방지) Repository 는 AsyncSession 유일 보유자로서 session.execute 를 쓰는 것이 정상이고, Decimal 공간 합산은 Decimal-first 룰의 표준 패턴이다.
rule_source: apps/api/AGENTS.md > §3 Architecture · §2 Decimal-first — 정상 코드
expect: pass
severity: none
---

Repository 층이 AsyncSession 을 쥐고 session.execute 로 체결 수량을 Decimal 공간에서 합산한다. "DB 직접 접근 + 돈 합산"처럼 보이지만 Repository 안이므로 정상이다. (실제 레포 패턴)

```python
# apps/api/src/order/repository.py
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.order.models import Fill


class FillRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def sum_filled_qty(self, order_id: int) -> Decimal:
        result = await self.session.execute(
            select(Fill.qty).where(Fill.order_id == order_id)
        )
        total = Decimal("0")
        for qty in result.scalars():
            total += Decimal(str(qty))
        return total
```
