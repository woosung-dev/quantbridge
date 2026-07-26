# Sprint 7d (B) Plan — OKX Adapter + Trading Sessions

**Branch:** `feat/sprint7d-okx-trading-sessions`
**Date:** 2026-04-19
**Source spec:** `docs/next-session-sprint-bcd-autonomous.md § Sprint 7d (B)`
**Baseline:** main `18bcf45`, backend 778 green

## Scope (fixed)

1. **OKX adapter** — CCXT-based, Bybit pattern cloned. Sandbox/demo only. Spot only.
   Credentials extended with `passphrase` (OKX-specific). AES-256 via existing `EncryptionService`.
2. **Trading Sessions filter** — `asia` / `london` / `ny` UTC hour masks. `Strategy.trading_sessions: list[str]` (nullable, empty = 24h). Applied in backtest engine (bar timestamps) and executor (current time).
3. **Alembic migration** — add `exchange_accounts.passphrase_encrypted` (LargeBinary nullable), `strategies.trading_sessions` (JSONB nullable), extend `exchangename` enum with `okx`.
4. **Tests** — provider unit (CCXT mock), sessions filter unit (9/14/22 UTC allow/block), integration (strategy create persists sessions), Bybit regression green.

## Actual repo layout (spec prompt used stale paths)

- Spec says `backend/src/adapters/exchanges/okx.py` → reality is `backend/src/trading/providers.py` (Bybit pattern source). Extend in place.
- Spec says "factory 등록" → reality is `backend/src/tasks/trading.py::_build_exchange_provider`. Add `okx_demo` branch + `settings.exchange_provider` Literal.

## Changes by file

### 1. `backend/src/trading/models.py`

- `ExchangeName` enum: add `okx = "okx"`.
- `ExchangeAccount`: new column `passphrase_encrypted: bytes | None` (`LargeBinary, nullable=True`).

### 2. `backend/src/trading/schemas.py`

- `RegisterAccountRequest`: add optional `passphrase: str | None = Field(default=None, min_length=1, max_length=200)`.
- Validator: when `exchange == okx` and passphrase is None → raise `ValueError("OKX accounts require passphrase")`.

### 3. `backend/src/trading/encryption.py`

- No change — `EncryptionService` is exchange-agnostic. passphrase uses same `.encrypt()`.

### 4. `backend/src/trading/providers.py`

- `Credentials` dataclass: add `passphrase: str | None = None` (default None; Bybit ignores). `__repr__` masks passphrase.
- New `OkxDemoProvider` class:
  - Bybit pattern. `ccxt.async_support.okx({apiKey, secret, password: passphrase, options: {defaultType: "spot"}})`.
  - `exchange.set_sandbox_mode(True)` after construction (OKX-specific CCXT API for demo vs. Bybit's `testnet` option).
  - Same finally→close, same ProviderError wrapping, `_map_ccxt_status` reuse.

### 5. `backend/src/trading/service.py`

- `ExchangeAccountService.register()`: encrypt `req.passphrase` if present → store in `passphrase_encrypted`.
- `get_credentials_for_order()`: decrypt passphrase if present, pass into `Credentials(passphrase=...)`.

### 6. `backend/src/core/config.py`

- `exchange_provider` Literal: append `"okx_demo"`.

### 7. `backend/src/tasks/trading.py`

- `_build_exchange_provider()`: add `okx_demo` branch → `OkxDemoProvider()`.

### 8. `backend/src/strategy/trading_sessions.py` (NEW)

- `class TradingSession(StrEnum)`: `asia`, `london`, `ny`.
- `SESSION_UTC_HOURS: dict[TradingSession, tuple[int, int]]` (closed start, open end):
  - asia: (0, 7) — UTC 00:00–06:59
  - london: (8, 16) — UTC 08:00–15:59
  - ny: (13, 20) — UTC 13:00–19:59 (13:30 start rounded to hour — simpler, validated by test)
  - Note: 13:30 NYSE open → hour-granular spec rounds to 13:00. Doc string + test pins this behavior.
- `is_allowed(sessions: list[str], ts: datetime) -> bool`:
  - If `sessions` is empty → return True (24h).
  - Require tz-aware; if naive raise ValueError.
  - Convert to UTC, extract `.hour`.
  - Return True if hour is within any listed session's range.
- `SESSION_VALUES: frozenset[str]` (for Pydantic validator).

### 9. `backend/src/strategy/models.py`

- `Strategy`: add `trading_sessions: list[str] = Field(default_factory=list, sa_column=Column(JSONB, nullable=True, server_default=text("'[]'::jsonb")))`.
- Note: `None` loaded from DB (from pre-migration rows) → normalise at read sites (empty list = 24h).

### 10. `backend/src/strategy/schemas.py`

- `CreateStrategyRequest` / `UpdateStrategyRequest`: add `trading_sessions: list[str] = Field(default_factory=list)` with validator allowing only `{"asia", "london", "ny"}`.
- `StrategyResponse` / `StrategyListItem`: expose `trading_sessions: list[str]`.

### 11. `backend/src/strategy/service.py`

- `StrategyService.create()` / `update()`: set `trading_sessions` from request.

### 12. `backend/src/backtest/engine/__init__.py`

- `run_backtest(..., config)`: if `config.trading_sessions` is non-empty, mask `parse.result.entries` by bar timestamps (only keep entries where `is_allowed(sessions, bar_ts)` True). `config.trading_sessions: list[str] = field(default_factory=list)` added to `BacktestConfig`.
- Minimal change: apply mask between `parse.result` and `to_portfolio_kwargs`.

### 13. `backend/src/backtest/engine/types.py`

- `BacktestConfig`: `trading_sessions: list[str] = field(default_factory=list)`.

### 14. `backend/src/backtest/service.py` (optional wire-through)

- Not required for MVP — engine accepts from config; service can remain unchanged. Strategy.trading_sessions → BacktestConfig.trading_sessions wiring is a follow-up (out of scope, noted below).

### 15. `backend/src/trading/service.py::OrderService.execute()`

- After leverage cap, before `begin_nested`: if we have a strategy with sessions, reject outside allowed hours.
- Impl: repository helper `StrategyRepository.get_by_id(strategy_id)` — check in router or load via service. For MVP:
  - Add `StrategySessionsPort` protocol (single method `async def get_sessions(strategy_id) -> list[str]`) to avoid cross-domain repo coupling. Constructor injection; default None = skip check.
  - Production DI wires a concrete impl from `src.strategy.repository`.
- Out of hours → raise new `TradingSessionClosed` exception (HTTP 422 at router).

### 16. Alembic migration — `backend/alembic/versions/20260419_*_sprint7d_okx_sessions.py`

- Revision ID: fresh UUID, down_revision = `edc2c1c4c313`.
- `upgrade()`:
  - `ALTER TYPE exchangename ADD VALUE IF NOT EXISTS 'okx'` (wrapped in DO block). Must be in its own transaction; use `op.execute()` with `with op.get_context().autocommit_block()`.
  - `op.add_column("exchange_accounts", Column("passphrase_encrypted", LargeBinary(), nullable=True), schema="trading")`.
  - `op.add_column("strategies", Column("trading_sessions", JSONB, nullable=True))`.
- `downgrade()`:
  - drop `trading_sessions` column from strategies.
  - drop `passphrase_encrypted` column from trading.exchange_accounts.
  - Enum value `okx` cannot be dropped in PostgreSQL (documented; leave in place).

### 17. Tests

- `backend/tests/trading/test_providers_okx_demo.py`:
  - ccxt_mock AsyncMock on `ccxt.async_support.okx`.
  - `test_okx_demo_uses_credentials_with_passphrase` — checks apiKey/secret/password config, set_sandbox_mode(True), options.defaultType="spot".
  - `test_okx_demo_close_called_on_exchange_error` — finally close guarantee.
  - `test_okx_demo_non_ccxt_exception_wrapped_safely` — ProviderError wrap without chaining.
  - `test_okx_demo_cancel_order`.

- `backend/tests/trading/test_providers_credentials_passphrase.py`:
  - Credentials dataclass accepts optional passphrase; `repr` masks it.

- `backend/tests/strategy/test_trading_sessions.py`:
  - Parametrize: hour 9 UTC → asia ✓, london ✗; hour 14 → london ✓, ny ✓; hour 22 → all ✗.
  - Empty list → always True.
  - Naive datetime → ValueError.
  - Tz-aware non-UTC (e.g. KST) → converted to UTC correctly.

- `backend/tests/strategy/test_service_trading_sessions.py`:
  - Integration (in-process, existing conftest): create strategy with `trading_sessions=["asia"]` → reload → equal.
  - Invalid session name → 422 via pydantic validator.

- `backend/tests/trading/test_service_orders_trading_sessions.py`:
  - `OrderService.execute()` with strategy sessions port returning `["asia"]` and current time 14 UTC → raises `TradingSessionClosed`.
  - Empty sessions → allowed.

- `backend/tests/backtest/test_engine_trading_sessions.py`:
  - Run backtest with `BacktestConfig(trading_sessions=["asia"])` on hourly OHLCV spanning 24h → only asia-hour entries fire.

### 18. Regression — Bybit paths unchanged

- All `test_providers_bybit_*` green.
- All `test_service_orders_*` green; OrderService path for Bybit without sessions: no regression (sessions port default None).

## Security

- `Credentials.__repr__` masks passphrase same as secret: show nothing.
- Passphrase never logged.
- `non-CCXT error` messages hide payload (same pattern as Bybit).
- Passphrase column stored only as AES-256 ciphertext, never plaintext at rest.

## Explicit Out-of-Scope

- OKX Futures / Perpetuals (follow-up sprint).
- Live trading (sandbox only).
- Wiring `Strategy.trading_sessions` → `BacktestConfig.trading_sessions` in `BacktestService` (engine accepts it; wiring in a later sprint).
- Frontend UI for trading_sessions selection.

## Execution order

1. Migration + models + enum value.
2. Schemas + service for Strategy.trading_sessions.
3. Trading sessions module + strategy-level tests.
4. Providers passphrase + OkxDemoProvider + factory + config Literal.
5. Backtest engine filter.
6. OrderService strategy-sessions port + executor tests.
7. Integration tests.
8. `uv run ruff check . && uv run mypy src/ && uv run pytest -v`.

## Self-verification

- `uv run ruff check .` → 0 issues
- `uv run mypy src/` → 0 errors
- `uv run pytest -v` → all existing 778 green + new ~15-20 tests green

## Evaluator gate

On self-verify green: dispatch `Agent(subagent_type=superpowers:code-reviewer, isolation=worktree)` with the SSOT evaluator template. PASS → PR create; FAIL ≤3 iter → fix; 3× FAIL → blocked.

## PR

Title: `feat(sprint7d): OKX 어댑터 + Trading Sessions 필터`
No merge from worker (orchestrator responsibility).
