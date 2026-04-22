# W1 — Alert Heuristic `loose` 모드 (i2_luxalgo 0 trades 해소)

> **Session:** Sprint X1+X3, 2026-04-23 | **Worker:** 1 / 5
> **Branch:** `stage/x1-x3-indicator-ui` (Option C staging, 직접 push)
> **TDD Mode:** **정석 TDD** — heuristic rule은 공유 로직 + semantic drift 위험

---

## 1. Context (self-contained — 워커 cold start 전제)

QuantBridge 는 TradingView Pine Script 전략을 실행하는 플랫폼. `alert()` / `alertcondition()` 을 매매 신호로 분류하는 heuristic 이 `backend/src/strategy/pine_v2/alert_hook.py` 에 있다.

**현재 공백**: LuxAlgo Trendlines with Breaks 지표 (`i2_luxalgo`) 는 `breakout` / `trendline` / `session` 키워드를 사용하는데, 현재 `_KEYWORD_RULES` (line 97-114) 가 이를 **무조건 `INFORMATION` 으로 우선 분류** → backtest 에서 0 trades.

**해결 방향**: 환경변수 `PINE_ALERT_HEURISTIC_MODE` 도입

- `strict` (default) — 현재 동작 유지 (breakout/trendline → INFORMATION)
- `loose` — INFORMATION 우선순위를 LONG/SHORT 뒤로 이동 → breakout/trendline 문맥에서도 방향 키워드 (long/buy/bull 등) 가 있으면 LONG_ENTRY 로 분류

---

## 2. Acceptance Criteria

### 정량

- [ ] `PINE_ALERT_HEURISTIC_MODE=strict` (or unset) 기본: 기존 `test_alert_hook.py` 전수 PASS (24+ 테스트)
- [ ] `PINE_ALERT_HEURISTIC_MODE=loose` 환경에서 신규 테스트: i2_luxalgo fixture 재생 시 ≥ 1 trade 발생 (LONG_ENTRY 분류)
- [ ] 회귀 금지: loose 모드에서도 `test_information_takes_precedence_over_direction_keyword` 와 동등한 **순수 INFORMATION** ("세션 시작", "pivot formed") 은 INFORMATION 유지
- [ ] backend pytest 전체 녹색 (pine_v2 + 타 모듈 회귀 0)

### 정성

- [ ] `classify_message()` signature 변경 없음 (후방호환) — `mode` 는 `os.environ` 에서 lazy read 또는 optional 2번째 인자 (default=strict)
- [ ] 새 모드 문서화 — `alert_hook.py` docstring + inline 주석
- [ ] 사용자 memory 규칙 준수: Decimal-first 등 pine_v2 관례 유지

---

## 3. File Structure

**수정:**

- `backend/src/strategy/pine_v2/alert_hook.py` — 환경변수 읽기 + mode 분기
- `backend/tests/strategy/pine_v2/test_alert_hook.py` — mode 별 파라미터라이즈 테스트 추가

**신규 (선택):** 없음 — 기존 파일만 확장.

---

## 4. TDD Tasks

### T1. 실패 테스트 작성 (loose 모드 기대값)

**Step 1 — 테스트 추가** (`backend/tests/strategy/pine_v2/test_alert_hook.py` 끝에):

```python
# -------- v2: loose mode (Sprint X1) --------------------------------------

import os
import pytest


@pytest.fixture
def loose_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "loose")


@pytest.fixture
def strict_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "strict")


def test_loose_mode_breakout_long_becomes_long_entry(loose_mode: None) -> None:
    """loose: 'Long breakout confirmed' → LONG_ENTRY (방향 키워드 우선)."""
    assert classify_message("Long breakout confirmed") == SignalKind.LONG_ENTRY


def test_loose_mode_short_breakout_becomes_short_entry(loose_mode: None) -> None:
    assert classify_message("Short break of trendline") == SignalKind.SHORT_ENTRY


def test_loose_mode_pure_information_still_information(loose_mode: None) -> None:
    """loose 에서도 방향 키워드 없는 순수 information 은 INFORMATION."""
    assert classify_message("Session started") == SignalKind.INFORMATION
    assert classify_message("Pivot formed at high") == SignalKind.INFORMATION


def test_strict_mode_preserves_legacy_behavior(strict_mode: None) -> None:
    """strict (default) 에서는 breakout/trendline 이 INFORMATION 우선."""
    assert classify_message("Long breakout confirmed") == SignalKind.INFORMATION
    assert classify_message("Short break of trendline") == SignalKind.INFORMATION


def test_unset_mode_defaults_to_strict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PINE_ALERT_HEURISTIC_MODE", raising=False)
    assert classify_message("Long breakout") == SignalKind.INFORMATION
```

**Step 2 — 실패 확인:**

```bash
cd backend && uv run pytest tests/strategy/pine_v2/test_alert_hook.py::test_loose_mode_breakout_long_becomes_long_entry -v
```

Expected: FAIL (loose 분기 없음 → 여전히 INFORMATION 반환)

### T2. 최소 구현

**Step 3 — `alert_hook.py` 수정:**

```python
# alert_hook.py 상단 import 에 추가
import os

# ... (기존 _KEYWORD_RULES 유지) ...

# 신규: loose 모드 rule 순서 (INFORMATION 을 마지막으로)
_KEYWORD_RULES_LOOSE: list[tuple[SignalKind, tuple[str, ...]]] = [
    (SignalKind.LONG_EXIT, (
        r"\bclose\s+long\b", r"\bexit\s+long\b", r"롱\s*청산", r"매수\s*청산",
    )),
    (SignalKind.SHORT_EXIT, (
        r"\bclose\s+short\b", r"\bexit\s+short\b", r"숏\s*청산", r"매도\s*청산",
    )),
    (SignalKind.LONG_ENTRY, (
        r"\blong\b", r"\bbuy\b", r"\bbull\b", r"매수",
    )),
    (SignalKind.SHORT_ENTRY, (
        r"\bshort\b", r"\bsell\b", r"\bbear\b", r"매도",
    )),
    (SignalKind.INFORMATION, (
        r"\bbreak\b", r"\btrendline\b", r"\bsession\b", r"\bpivot\b",
        r"돌파", r"세션",
    )),
]


def _get_heuristic_mode() -> str:
    """환경변수 `PINE_ALERT_HEURISTIC_MODE` 를 읽어 'strict' 또는 'loose' 반환.

    - 미설정 또는 잘못된 값 → 'strict' (후방호환).
    - loose 모드는 `breakout/trendline/session` 등 context 키워드보다
      방향 키워드(long/short 등)를 우선 매칭하여 LuxAlgo류 indicator alert 을
      매매 신호로 분류할 수 있게 한다.
    """
    mode = os.environ.get("PINE_ALERT_HEURISTIC_MODE", "strict").lower().strip()
    return "loose" if mode == "loose" else "strict"


def classify_message(text: str) -> SignalKind:
    """문자열(메시지 또는 조건식 stringify)을 신호 종류로 분류.

    모드 (환경변수 `PINE_ALERT_HEURISTIC_MODE`):
    - strict (default): INFORMATION(break/trendline/session/pivot) > 방향 > UNKNOWN
    - loose: 방향(long/short/bull/bear) > INFORMATION > UNKNOWN
    """
    if not text:
        return SignalKind.UNKNOWN

    stripped = text.strip()
    # 1. JSON 파싱 시도 (모드 무관)
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            data = json.loads(stripped)
            action = str(data.get("action", "")).lower()
            if action in ("buy", "long"):
                return SignalKind.LONG_ENTRY
            if action in ("sell", "short"):
                return SignalKind.SHORT_ENTRY
            if action == "close_long":
                return SignalKind.LONG_EXIT
            if action == "close_short":
                return SignalKind.SHORT_EXIT
        except (json.JSONDecodeError, AttributeError):
            pass

    # 2. 키워드 매칭 (모드별 rule set)
    rules = _KEYWORD_RULES_LOOSE if _get_heuristic_mode() == "loose" else _KEYWORD_RULES
    lower = stripped.lower()
    for kind, patterns in rules:
        for pat in patterns:
            if re.search(pat, lower, re.IGNORECASE):
                return kind

    return SignalKind.UNKNOWN
```

**Step 4 — 녹색 확인:**

```bash
cd backend && uv run pytest tests/strategy/pine_v2/test_alert_hook.py -v
```

Expected: PASS — 모든 loose/strict 테스트 + 기존 테스트 전수 녹색

### T3. 회귀 방지 — i2_luxalgo E2E 재검증

**Step 5:**

```bash
cd backend && PINE_ALERT_HEURISTIC_MODE=loose uv run pytest tests/strategy/pine_v2/test_e2e_i2_luxalgo.py -v
```

Expected: PASS (기존 통과 유지)

**Step 6 — 전체 pine_v2 녹색:**

```bash
cd backend && uv run pytest tests/strategy/pine_v2/ -v
```

Expected: 전수 PASS.

### T4. 회귀 확인 — 전체 backend

**Step 7:**

```bash
cd backend && uv run pytest -q
```

Expected: 922 passed (기존 baseline) + 신규 5 tests → 927+ passed.

### T5. Worker-side codex review 1-pass

```bash
codex exec --sandbox read-only "Review git diff vs main for PINE_ALERT_HEURISTIC_MODE loose/strict logic. Check: (1) strict default preserves all prior behavior, (2) loose never over-classifies pure INFORMATION, (3) env read is lazy so tests can monkeypatch, (4) no semantic drift in _KEYWORD_RULES_LOOSE vs _KEYWORD_RULES other than order."
```

출력을 `docs/superpowers/reviews/2026-04-23-x1x3-w1-codex-self.md` 에 저장.

### T6. Stage 브랜치 push

```bash
git add backend/src/strategy/pine_v2/alert_hook.py backend/tests/strategy/pine_v2/test_alert_hook.py docs/superpowers/reviews/2026-04-23-x1x3-w1-codex-self.md
git commit -m "feat(pine_v2): alert heuristic loose mode for i2_luxalgo (W1)"
git push origin stage/x1-x3-indicator-ui
```

---

## 5. Edge Cases 필수 커버

- `PINE_ALERT_HEURISTIC_MODE=LOOSE` (대문자) → `.lower()` 로 정규화
- `PINE_ALERT_HEURISTIC_MODE=foo` (잘못된 값) → strict fallback
- 환경변수 미설정 → strict (기존 baseline 유지)
- 메시지가 빈 문자열 → UNKNOWN (mode 무관)
- `"Bullish breakout"` → loose=LONG_ENTRY (bull 이 방향), strict=INFORMATION

---

## 6. 3-Evaluator 공용 질문

1. AC 정량 기준 (5개 정성 포함) 실제 달성 evidence?
2. spurious PASS: 테스트가 강제로 녹색되도록 설계됐나? (e.g. env 전역 오염)
3. TDD: step 2 에서 실제 FAIL 재현 확인 후 step 4 에서 녹색 전환?
4. 회귀 표면: `alert_hook.py` 다른 callers (collect_alerts 등) 영향 검토?
5. edge case 누락 (대문자 / 공백 / 오타 / unicode)?
6. memory 규칙: Decimal-first, LESSON-004, pine_v2 stdlib 관례 위반?
7. GO / GO_WITH_FIX / MAJOR_REVISION / NO_GO + 신뢰도 1-10

---

## 7. Verification

```bash
# Unit
cd backend && uv run pytest tests/strategy/pine_v2/test_alert_hook.py -v
# Loose E2E
cd backend && PINE_ALERT_HEURISTIC_MODE=loose uv run pytest tests/strategy/pine_v2/test_e2e_i2_luxalgo.py -v
# 전체 회귀
cd backend && uv run pytest -q
```
