---
id: 03-api-key-hardcoded
rule: API 키 등 시크릿을 코드에 하드코딩하지 않는다. 설정은 SecretStr 로 받고 .env.example 에 있는 환경 변수만 참조한다.
rule_source: 루트 AGENTS.md > Golden Rules (시크릿 하드코딩 금지) · apps/api/AGENTS.md > §2 SecretStr
expect: violation
severity: critical
---

거래소 API 키/시크릿이 문자열 리터럴로 코드에 박혀 있다.

```diff
# apps/api/src/trading/services/exchange_client.py
+import ccxt
+
+BYBIT_API_KEY = "bybit-demo-3f8a2c91d4e5"
+BYBIT_API_SECRET = "sk-demo-9d2f81a7c3b64e0f"
+
+def create_bybit_client() -> ccxt.bybit:
+    return ccxt.bybit({"apiKey": BYBIT_API_KEY, "secret": BYBIT_API_SECRET})
```
