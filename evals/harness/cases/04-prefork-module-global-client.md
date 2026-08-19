---
id: 04-prefork-module-global-client
rule: Celery task 모듈 전역에서 외부 클라이언트(ccxt 등)·loop-bound 객체를 생성하지 않는다. 클라이언트는 호출 시점에 지연 생성한다 (prefork-safe).
rule_source: apps/api/AGENTS.md > §9 Celery prefork-safe 패턴
expect: violation
severity: critical
---

Celery 태스크 모듈이 import 시점(모듈 전역)에 ccxt async 클라이언트를 만들어 모든 task 가 재사용한다 — prefork fork 후 자식이 부모의 커넥션/loop 바인딩을 물려받아 2번째 task 부터 silent fail 한다.

```diff
# apps/api/src/tasks/live_signal.py
+import ccxt.async_support as ccxt
+from celery import shared_task
+
+# 모듈 로드 시점에 한 번만 만들어 모든 task 가 재사용한다
+_EXCHANGE = ccxt.bybit()
+
+@shared_task(name="trading.live_signal")
+def live_signal_entry(payload: str) -> dict:
+    from src.tasks._worker_loop import run_in_worker_loop
+
+    return run_in_worker_loop(_fetch_and_signal(_EXCHANGE, payload))
```
