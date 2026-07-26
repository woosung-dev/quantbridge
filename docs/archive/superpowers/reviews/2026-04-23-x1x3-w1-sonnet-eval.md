# Sonnet Eval — W1 Alert Heuristic `loose` 모드

**Date:** 2026-04-23
**Reviewer:** Claude Sonnet 4.6 (independent, cold-start)
**Diff scope:** `backend/src/strategy/pine_v2/alert_hook.py` + `backend/tests/strategy/pine_v2/test_alert_hook.py`
**Evidence base:** `/tmp/w1-diff.txt` (diff) + worktree alert_hook.py + test_alert_hook.py (full read)

---

## Q1 — AC 달성 여부 (936 pytest pass + 14 new tests)

**PARTIAL PASS — 조건부 충족.**

정량 AC:

| AC 항목                                  | 상태             | Evidence                                                                                                                                                                                                                      |
| ---------------------------------------- | ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| strict/unset → 기존 테스트 전수 PASS     | PASS             | `_KEYWORD_RULES` 바이트 동일 유지 확인 (Q4 참조). 기존 `test_classify_message_keyword_rules` 14개 파라미터 및 condition-trace 테스트 모두 영향 없음                                                                           |
| loose 모드 → `i2_luxalgo` ≥ 1 trade      | PASS (by proxy)  | `classify_message("Long break of trendline")` → `LONG_ENTRY` in loose 확인. 실제 E2E 결과는 codex self-review에서 `test_e2e_i2_luxalgo.py — 3 passed (PINE_ALERT_HEURISTIC_MODE=loose)` 로 보고됨 (독립 검증 불가, 보고 신뢰) |
| 순수 INFORMATION 보존                    | PASS             | `test_loose_mode_pure_information_still_information` (test_alert_hook.py:237) — "Session started", "Pivot formed at high" → INFORMATION                                                                                       |
| 전체 pytest 녹색                         | PASS (보고 기준) | codex self-review: 934 passed, 1 skipped. 독립 실행 미수행                                                                                                                                                                    |
| `classify_message()` signature 변경 없음 | PASS             | diff에서 signature 변경 없음. 환경변수로만 분기                                                                                                                                                                               |

실제 신규 test 함수: **12개** (diff 기준). plan이 "14 new tests"로 언급한 것은 2개의 fixture (`loose_mode`, `strict_mode`)를 포함해 계산한 것으로 보임 — fixture ≠ test function. 이는 사소한 문서 불일치이나 기능적 결함은 아님.

---

## Q2 — Spurious PASS: 경계 메시지 strict vs loose 구분 검증

**경고: `test_loose_mode_uppercase_env_normalized` 에 spurious PASS 존재.**

- **해당 테스트** (test_alert_hook.py:265-268): `PINE_ALERT_HEURISTIC_MODE=LOOSE` 설정 후 `"Long breakout confirmed"` → `LONG_ENTRY` 기대.
- **실제**: `"Long breakout confirmed"` 은 **strict 모드에서도 LONG_ENTRY**다.
  - strict `_KEYWORD_RULES`에서 `INFORMATION` 규칙의 `\bbreak\b`는 `"breakout"` (하나의 붙은 단어)에 **매칭되지 않는다** — word boundary `\b` 때문.
  - 따라서 `\blong\b` 가 LONG_ENTRY로 선 매칭됨.
- **결론**: 이 테스트는 env 대소문자 정규화(`.lower()`) 가 동작하는지 확인하지 **못한다**. LOOSE를 설정해도 STRICT를 설정해도 동일 결과이므로 테스트가 항상 PASS됨.
- **올바른 검증 메시지**: `"Long break of trendline"` (이미 boundary test에서 사용) 또는 `"Bullish breakout"` 처럼 실제로 두 모드에서 다른 결과를 내는 메시지를 사용해야 한다.

나머지 11개 테스트는 경계가 적절히 설정됨:

- `test_loose_mode_breakout_long_becomes_long_entry` (line 223): `"Long break of trendline"` — strict=INFORMATION, loose=LONG_ENTRY ✓
- `test_strict_mode_preserves_legacy_behavior` (line 243): 동일 메시지로 역방향 검증 ✓
- `test_unset_mode_defaults_to_strict` (line 255): 동일 경계 메시지 ✓

---

## Q3 — TDD: 테스트 FAIL 선행 확인

**확인 불가 (문서 기준).**

- Codex self-review 문서(w1-codex-self.md)에 1st pass 내용과 fixes 내역이 기록되어 있음.
- 계획 §4 T1 Step 2에서 "FAIL 확인" 절차를 명시.
- 그러나 실제 FAIL 스크린샷 / 터미널 출력이 diff나 review에 포함되어 있지 않아 독립 검증 불가.

**[가정]** Worker가 계획 절차를 따랐다고 가정 — codex self-review가 2-pass 구조로 수행된 것이 간접 증거. 그러나 TDD 준수 여부는 artifact 기반 확인 불가.

---

## Q4 — Regression: `_KEYWORD_RULES` 원본 바이트 동일 여부

**PASS — 바이트 동일 확인.**

diff 확인 결과 `_KEYWORD_RULES` (alert_hook.py:97-114 기준, 워크트리 파일 line 98-115) 는 **삭제·추가·변경 없이 그대로 유지**됨. diff 헝크에는 `_KEYWORD_RULES` 정의 자체가 포함되지 않음.

직접 파일 read로 확인:

```python
# alert_hook.py lines 98-115 (worktree)
_KEYWORD_RULES: list[tuple[SignalKind, tuple[str, ...]]] = [
    (SignalKind.INFORMATION, (
        r"\bbreak\b", r"\btrendline\b", r"\bsession\b", r"\bpivot\b",
        r"돌파", r"세션",
    )),
    (SignalKind.LONG_EXIT, ...),
    ...
]
```

원본 main 브랜치의 `alert_hook.py` (read 확인)와 동일한 내용. `_KEYWORD_RULES` 수정 없음.

---

## Q5 — Edge Cases 8가지 커버 여부

| Edge Case            | 테스트 존재 여부 | 테스트 함수                                                           | 비고                                                    |
| -------------------- | ---------------- | --------------------------------------------------------------------- | ------------------------------------------------------- |
| 대문자 env (`LOOSE`) | PARTIAL          | `test_loose_mode_uppercase_env_normalized` (line 265)                 | **spurious PASS** — 메시지가 mode-independent (Q2 참조) |
| 빈 문자열 env (`""`) | PASS             | `test_empty_string_env_falls_back_to_strict` (line 277)               | Codex 1st pass 피드백으로 추가됨                        |
| 공백 env (`"   "`)   | PASS             | `test_whitespace_env_falls_back_to_strict` (line 283)                 | 동일                                                    |
| 잘못된 값 (`foo`)    | PASS             | `test_invalid_mode_falls_back_to_strict` (line 271)                   |                                                         |
| 미설정 (unset)       | PASS             | `test_unset_mode_defaults_to_strict` (line 255)                       |                                                         |
| 빈 메시지 (`""`)     | PASS             | `test_loose_mode_empty_message_unknown` (line 289)                    |                                                         |
| `"Bullish breakout"` | PASS             | `test_loose_mode_bullish_breakout_is_long_entry` (line 294)           | loose=LONG_ENTRY (`\bbull` prefix)                      |
| JSON `action="buy"`  | 암묵적 PASS      | 기존 `test_classify_message_keyword_rules` param `'{"action":"buy"}'` | **loose 모드에서 명시적 재검증 없음** (Q8 참조)         |

총 8개 중 6개 명확 PASS, 1개 spurious PASS (대문자 env), 1개 암묵적(JSON loose).

---

## Q6 — Lazy env read: `_get_heuristic_mode()` 호출 시점

**PASS — 완벽한 lazy read 구현.**

`alert_hook.py` lines 139-153:

```python
def _get_heuristic_mode() -> str:
    raw = os.environ.get("PINE_ALERT_HEURISTIC_MODE", "strict")
    mode = raw.lower().strip() if isinstance(raw, str) else "strict"
    return "loose" if mode == "loose" else "strict"
```

- 모듈 수준에 환경변수를 캐싱하는 코드 없음.
- `classify_message()` 내에서 `_get_heuristic_mode()` 를 매 호출마다 실행 (line 185).
- pytest `monkeypatch.setenv` / `delenv` 가 안전하게 동작하는 구조.
- `isinstance(raw, str)` guard는 `os.environ.get` 반환값이 항상 `str | None` 이므로 불필요하지만 무해.

---

## Q7 — 최종 판정

**GO_WITH_FIX — 신뢰도 8/10**

이유:

- 핵심 기능(loose 모드 방향 키워드 우선)은 정확하게 구현됨
- strict baseline 회귀 없음
- lazy read 완벽
- spurious PASS 1건 (Q2) — 대문자 env 정규화 기능 자체는 코드에서 올바르게 구현되어 있으나 테스트가 이를 증명하지 못함
- JSON + loose 모드 교차 검증 누락 (Q8 참조)

**필수 fix:**

1. `test_loose_mode_uppercase_env_normalized` 의 메시지를 `"Long break of trendline"` 등 mode-sensitive 메시지로 교체
2. (권고) loose 모드 + JSON action 교차 테스트 추가

---

## Q8 — 테스트 커버리지 충분성 (Sonnet 추가 질문)

### (a) EXIT 우선순위 — `_KEYWORD_RULES_LOOSE` 에서 LONG_EXIT이 LONG_ENTRY 앞인가?

**PASS (코드 수준) / MISSING (테스트 수준).**

코드: `_KEYWORD_RULES_LOOSE` (alert_hook.py:119-136) 에서 LONG_EXIT이 LONG_ENTRY보다 선순위:

```
1. LONG_EXIT   ← 먼저
2. SHORT_EXIT
3. LONG_ENTRY  ← 이후
4. SHORT_ENTRY
5. INFORMATION
```

파이썬으로 검증:

- `"close long now"` → loose 모드 → `LONG_EXIT` (LONG_ENTRY의 `\blong\b`보다 LONG_EXIT의 `\bclose\s+long\b` 가 선 매칭됨) ✓

그러나 14개 신규 테스트 중 **loose 모드에서 "close long" → LONG_EXIT** 을 명시적으로 검증하는 테스트가 없다. 기존 `test_classify_message_keyword_rules` 의 `"Close Long"` 파라미터는 strict 모드에서 검증되며, loose 모드에서 EXIT 규칙이 ENTRY보다 우선함을 증명하지 않는다.

### (b) JSON action="buy" loose/strict 모두 LONG_ENTRY인지

**코드 정확 / 테스트 누락.**

JSON 파싱은 `classify_message()` 에서 키워드 매칭 이전에 실행되며 (line 168-181), `_get_heuristic_mode()` 호출 전에 JSON path로 return한다. 따라서 모드에 무관하게 `action="buy"` → LONG_ENTRY는 보장됨.

그러나 신규 14개 테스트에서 **loose 모드 상태에서 JSON action 메시지를 전달하는 테스트가 없다.** 미래에 JSON path 로직이 mode 분기 아래로 이동되면 회귀가 발생할 수 있고, 테스트가 이를 잡지 못한다.

### 어느 쪽이 production 결함 가능성 더 높은가?

**(a) EXIT 우선순위 누락이 더 높은 위험.**

- **이유**: loose 모드는 "방향 키워드를 먼저 보는" 동작이므로, `"close long"` 류 메시지가 LONG_EXIT 대신 LONG_ENTRY로 잘못 분류될 경우 **포지션을 닫아야 할 시점에 오히려 진입 신호가 발생**하는 금전적 위험이 있음.
- (b) JSON path는 모드 독립적으로 보호되어 있어 현재 구조에서 실제 결함 가능성은 낮음. 단, 미래 코드 변경 시 취약.

**권고**: 두 시나리오 모두 테스트를 추가하되, (a)를 먼저 추가할 것.

추가 권고 테스트:

```python
def test_loose_mode_close_long_is_long_exit(loose_mode: None) -> None:
    """loose 모드에서 EXIT 규칙이 ENTRY보다 선순위임을 보장."""
    assert classify_message("close long") == SignalKind.LONG_EXIT
    assert classify_message("exit long position") == SignalKind.LONG_EXIT

def test_json_action_buy_mode_independent(monkeypatch: pytest.MonkeyPatch) -> None:
    """JSON action='buy'는 strict/loose 무관하게 LONG_ENTRY."""
    for mode in ("strict", "loose"):
        monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", mode)
        assert classify_message('{"action":"buy"}') == SignalKind.LONG_ENTRY
```

---

## 요약 스코어카드

| 항목             | 결과            | 비고                                                                      |
| ---------------- | --------------- | ------------------------------------------------------------------------- |
| AC 달성          | PARTIAL PASS    | 14 = 12 test + 2 fixture 혼동. 기능적 AC는 충족                           |
| Spurious PASS    | 경고 1건        | `test_loose_mode_uppercase_env_normalized` — mode-independent 메시지 사용 |
| TDD              | 확인 불가       | FAIL 선행 artifact 없음                                                   |
| Regression       | PASS            | `_KEYWORD_RULES` 원본 유지 확인                                           |
| Edge Cases       | PARTIAL         | 8/8 커버되나 1건 spurious, 1건 암묵적                                     |
| Lazy env read    | PASS            | 완벽한 per-call os.environ.get                                            |
| **최종**         | **GO_WITH_FIX** | **신뢰도 8/10**                                                           |
| Q8 EXIT 우선순위 | MISSING TEST    | 코드는 맞으나 loose 모드 명시적 EXIT 테스트 없음 — production risk        |
| Q8 JSON + loose  | MISSING TEST    | 현재 결함 낮으나 회귀 보호 부재                                           |
