---
id: 02-service-direct-db
rule: DB 접근은 Repository 층에서만 한다. Service 는 AsyncSession 을 보유하거나 session.execute 를 직접 호출하면 안 된다.
rule_source: apps/api/AGENTS.md > §3 Architecture (AsyncSession은 Repository만 보유)
expect: violation
severity: critical
---

Service 가 Repository 를 거치지 않고 AsyncSession 을 직접 쥐고 session.execute 를 호출한다.

```diff
# apps/api/src/strategy/service.py
+from sqlalchemy import select
+from sqlalchemy.ext.asyncio import AsyncSession
+
+from src.strategy.models import Strategy
+
+class StrategyService:
+    def __init__(self, session: AsyncSession) -> None:
+        self.session = session
+
+    async def list_active(self) -> list[Strategy]:
+        result = await self.session.execute(
+            select(Strategy).where(Strategy.is_active.is_(True))
+        )
+        return list(result.scalars().all())
```
