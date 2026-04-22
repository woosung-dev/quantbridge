# W1 Codex Self-Review — Alert Heuristic `loose` 모드

**Date:** 2026-04-23
**Worker:** Sprint X1+X3 W1
**Diff scope:** `backend/src/strategy/pine_v2/alert_hook.py` + `backend/tests/strategy/pine_v2/test_alert_hook.py`
**Reviewer:** `codex exec --sandbox read-only` (codex-cli 0.122.0)

---

## 1st pass — GO_WITH_FIX (8/10)

Findings:

1. **Missing empty-string env coverage** — Requirement (5) asked for env edge cases including empty string, but `monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "")` was not tested. Code falls back to strict via `strip()` but coverage gap.
2. **Weak loose-vs-strict boundary test** — `test_loose_mode_breakout_long_becomes_long_entry` used `"Long breakout confirmed"`, which is `LONG_ENTRY` in BOTH strict and loose (`\bbreak\b` does not match `breakout`). Did not actually distinguish the two modes.

Checks 1-4 + 6 partial (5 partial): PASS for strict baseline preservation, INFORMATION pure preservation, lazy env read, and intended semantic drift only.

## Fixes applied

- **Added** `test_empty_string_env_falls_back_to_strict` (env `""` → strict).
- **Added** `test_whitespace_env_falls_back_to_strict` (env `"   "` → strict; covers `strip()` path).
- **Changed** `test_loose_mode_breakout_long_becomes_long_entry` from `"Long breakout confirmed"` to `"Long break of trendline"` — this message is INFORMATION in strict (matched by `\bbreak\b` + `\btrendline\b`) and LONG_ENTRY in loose (matched by `\blong\b` first), proving the two-mode boundary.

## 2nd pass — GO (9/10)

Verdict: **GO**, confidence **9/10**. All 6 criteria met. No remaining findings.

Confirmed:

1. Empty-string env test added at `test_alert_hook.py:277`
2. Whitespace env test added at `test_alert_hook.py:283`
3. Boundary-distinguishing message in test at `test_alert_hook.py:223`
4. `_get_heuristic_mode()` lazy-read + `lower().strip()` + invalid/empty/whitespace → strict fallback consistent
5. Backward compat preserved: `test_unset_mode_defaults_to_strict`, `test_invalid_mode_falls_back_to_strict`, `test_loose_mode_uppercase_env_normalized`
6. strict/loose semantic separation fixed: strict legacy preserved (`:243`), loose pure-information preserved (`:237`), bullish/bearish prefix extended (`:294`, `:303`)

## Final verification

```
backend/tests/strategy/pine_v2/test_alert_hook.py — 43 passed
backend/tests/strategy/pine_v2/test_e2e_i2_luxalgo.py — 3 passed (PINE_ALERT_HEURISTIC_MODE=loose)
backend pytest -q — 934 passed, 1 skipped (pre-existing)
```

## Decision

**GO** — proceed to commit. No additional iterations required.
