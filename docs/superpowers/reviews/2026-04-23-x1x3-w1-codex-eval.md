Reading additional input from stdin...
OpenAI Codex v0.122.0 (research preview)

---

workdir: /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41
model: gpt-5.4
provider: openai
approval: never
sandbox: read-only
reasoning effort: medium
reasoning summaries: none
session id: 019db60a-9025-7b80-bdac-dab0b4cb6fb1

---

user
You are an adversarial code reviewer for QuantBridge Sprint X1+X3 Worker 1 (alert heuristic loose mode for i2_luxalgo).

## Inputs

- Plan: /Users/woosung/project/agy-project/quant-bridge/docs/superpowers/plans/2026-04-23-x1x3-w1-alert-heuristic-loose.md
- Diff (vs stage/x1-x3-indicator-ui): /tmp/w1-diff.txt (244 lines, 3 files)
- Worker self-review: /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/docs/superpowers/reviews/2026-04-23-x1x3-w1-codex-self.md

## Context

Goal: introduce PINE_ALERT_HEURISTIC_MODE env var (strict default, loose option) so i2_luxalgo "Long break of trendline" type messages classify as LONG_ENTRY in loose mode while pure INFORMATION ("Session started") still classifies as INFORMATION.

## 7 Questions (file:line evidence)

1. AC met? strict default = legacy behavior preserved (32 existing tests still pass)? loose = new behavior + 11 new tests? backend total 936 passed?
2. Spurious PASS — does any new loose test work because the old strict regex would have ALSO classified it as LONG_ENTRY? Verify boundary: e.g., test "Long break of trendline" — is strict's first-match really INFORMATION (per `\bbreak\b`/`\btrendline\b`), and loose's first match really LONG_ENTRY (per `\blong\b`)? Read `_KEYWORD_RULES` vs `_KEYWORD_RULES_LOOSE` rule order.
3. TDD evidence — were tests written FIRST and FAILED before impl?
4. Regression — strict mode (default) should be byte-identical to current behavior. \_KEYWORD_RULES untouched? Worker claims "byte-for-byte 미변경". Verify.
5. Edge cases — uppercase env, empty string, whitespace, invalid value, missing env, empty message, "Bullish breakout" (loose) — all 8 covered?
6. **Constraint check** — `classify_message()` signature unchanged? `_get_heuristic_mode()` is lazy (reads os.environ on every call so monkeypatch works in tests)?
7. Verdict: GO | GO_WITH_FIX | MAJOR_REVISION | NO_GO + confidence 1-10.
   codex
   리뷰 범위를 확인했고, 먼저 규칙 문서와 입력 산출물을 읽어 현재 구현 주장과 실제 diff를 대조하겠습니다. 이어서 관련 소스의 기존 규칙 순서와 테스트 케이스를 확인해 7개 질문에 직접 답하겠습니다.
   exec
   /bin/zsh -lc "sed -n '1,240p' /Users/woosung/project/agy-project/quant-bridge/docs/superpowers/plans/2026-04-23-x1x3-w1-alert-heuristic-loose.md" in /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41
   exec
   /bin/zsh -lc "sed -n '1,220p' AGENTS.md" in /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41
   succeeded in 0ms:

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

succeeded in 0ms:

# QuantBridge — TradingView Pine Script 전략을 백테스트·데모·라이브 트레이딩으로 연결하는 퀀트 플랫폼

> **새 프로젝트 시작 시:** `## 현재 컨텍스트` 섹션만 채우면 됩니다.
> 개인 원칙과 스택 규칙은 그대로 재사용됩니다.

---

# Golden Rules (Immutable)

> 프로젝트 전체를 관통하는 불변 제약. 어떤 상황에서도 타협 금지.

- 환경 변수·API 키·시크릿을 코드에 하드코딩 금지
- DB 접근은 지정된 레이어에서만 허용 (각 스택 규칙의 아키텍처 섹션 참조)
- `.env.example`에 없는 환경 변수를 코드에서 참조 금지
- `import` 경로 규칙 위반 금지 (각 스택 규칙 파일 참조)
- 사용자 승인 없는 git push / 배포 금지
- LLM이 생성한 규칙 파일을 검토 없이 그대로 사용 금지 — 반드시 사람이 검토·확정

---

# 개인 개발 원칙 (모든 프로젝트 공통)

---

## 1. 언어 정책

- **사고 & 계획:** 한국어
- **대화:** 한국어
- **문서:** 한국어
- **코드 네이밍:** 영어 (변수명, 함수명, 클래스명, 커밋 메시지)
- **주석:** 한국어

---

## 2. 역할 정의

- **Senior Tech Lead + System Architect** 로 행동한다.
- 유지보수 가능한 아키텍처 / 엄격한 타입 안정성 / 명확한 문서화를 최우선 가치로 둔다.
- 장황한 서론 없이 즉시 적용 가능한 **정확한 코드 스니펫과 파일 경로**를 제시한다.
- 코드 제공 시 `...` 처리로 생략하지 않고 **완전한 코드**를 제공한다.
- 복잡한 설계는 Mermaid.js로 시각화. 코드와 핵심 원리(불릿 포인트) 위주로 답변한다.

---

## 3. AI 행동 지침

### Context Sync

새 태스크 시작 시 `CLAUDE.md` (또는 `AGENTS.md`)를 먼저 읽어 전체 작업 컨텍스트를 파악한다.
`docs/README.md`가 있으면 함께 읽어 아키텍처와 프로젝트 현황을 확인한다.

### Plan Before Code

코드 작성 전 "어떤 설계 문서를 참고했고, 어떤 방향으로 수정할 것인지" 짧게 브리핑한다.

### Atomic Update

코드를 수정했다면, 동일 세션 내에 관련 문서를 **반드시 함께 수정**한다.

### Think Edge Cases

네트워크 실패 / 타입 불일치 / 빈 응답 / 권한 오류 등 예외 상황을 기본으로 고려한다.

### Fact vs Assumption

코드 분석·설계·문서 작성 시 **확인된 사실**과 **추론/가정**을 명확히 구분한다.

- 확인된 사실 → 그대로 기술
- 추론한 내용 → `[가정]` 라벨 명시
- 사용자 확인이 필요한 결정 → `[확인 필요]` 라벨 명시
- 불확실한 비즈니스 규칙을 임의로 확정하지 않는다

### Git Safety Protocol

작업 완료 후 **반드시 단계별로 사용자 승인**을 받는다. 자동 진행 금지.

1. **커밋** — "커밋할까요?" 승인 후 진행
2. **푸쉬** — "푸쉬할까요?" 승인 후 진행
3. **배포 모니터링** — "배포 결과를 확인할까요?" 승인 후 진행

> 사용자가 "커밋하고 푸쉬해줘"처럼 명시적으로 묶어 요청한 경우에만 해당 단계를 한 번에 진행할 수 있다.

### Communication

- 사용자에게 빈번하게 질문하여 작업 흐름을 끊지 않는다
- 확인이 필요한 항목은 `docs/TODO.md`에 기록하고, 자연스러운 타이밍에 한 번에 정리하여 전달한다
- 차단(blocked) 상황이 아닌 한, 작업을 계속 진행한다

---

## 4. 문서화 구조

> **Plan → Docs → Review → Implement** 루프.
> ID 체계, TODO.md 운영, Git Convention, 환경변수 → **`.ai/rules/global.md`** 참조.
> 코딩 컨벤션 → **`.ai/rules/typescript.md`** + 해당 **스택 규칙**

| docs/ 위치              | 용도                     |
| ----------------------- | ------------------------ |
| **설계 산출물 (순차)**  |                          |
| `00_project/`           | 프로젝트 개요            |
| `01_requirements/`      | PRD, 기능 명세           |
| `02_domain/`            | 도메인 모델, ERD         |
| `03_api/`               | API 명세                 |
| `04_architecture/`      | 시스템 설계              |
| `05_env/` ~ `07_infra/` | 환경 설정, CI/CD, 인프라 |
| **상시 문서**           |                          |
| `dev-log/`              | ADR (의사결정 기록)      |
| `guides/` · `TODO.md`   | 가이드, 작업 추적        |

---

## 현재 컨텍스트

> **새 프로젝트 시작 시 이 섹션을 채우세요.**

### 프로젝트 개요

- **이름:** QuantBridge
- **한 줄 설명:** TradingView Pine Script 전략 → 백테스트 → 스트레스 테스트 → 데모/라이브 트레이딩 파이프라인
- **기술 스택:** Next.js 16 (Frontend) + FastAPI (Backend) — `.ai/rules/` 참조
- **인증:** Clerk (Frontend + Backend JWT 검증)
- **DB:** PostgreSQL + TimescaleDB (시계열) + Redis (캐시/Celery 브로커)
- **비동기 작업:** Celery + Redis (백테스트, 최적화, 데이터 수집)

### 핵심 도메인

- **Strategy** — Pine Script 파싱, 전략 CRUD, Python 트랜스파일
- **Backtest** — vectorbt 기반 벡터화 백테스트, 지표 계산, 리포트
- **Stress Test** — Monte Carlo, Walk-Forward, 파라미터 안정성 분석
- **Optimizer** — Grid/Bayesian/Genetic 파라미터 최적화
- **Trading** — CCXT 기반 데모/라이브 주문 실행, 리스크 관리, Kill Switch
- **Market Data** — OHLCV 수집, TimescaleDB 저장, 실시간 가격 스트림
- **Exchange** — 거래소 계정 관리, API Key AES-256 암호화

### Operational Commands

```bash
# Frontend (Next.js 16)
cd frontend && pnpm dev          # 개발 서버 (http://localhost:3000)
cd frontend && pnpm build        # 프로덕션 빌드
cd frontend && pnpm test         # 테스트
cd frontend && pnpm lint         # 린트
cd frontend && pnpm tsc --noEmit # 타입 체크

# Backend (FastAPI)
cd backend && uvicorn src.main:app --reload --host 0.0.0.0 --port 8000  # 개발 서버
cd backend && pytest -v          # 테스트
cd backend && ruff check .       # 린트
cd backend && mypy src/          # 타입 체크
cd backend && alembic upgrade head       # 마이그레이션 적용
cd backend && alembic revision --autogenerate -m "description"  # 마이그레이션 생성

# Infrastructure
docker compose up -d             # 전체 서비스 (DB, Redis, TimescaleDB)
docker compose logs -f backend   # 백엔드 로그

# Celery
cd backend && celery -A src.tasks worker --loglevel=info --concurrency=4  # 워커
cd backend && celery -A src.tasks beat --loglevel=info                    # 스케줄러
```

### 현재 작업

- Stage 1: 계획 + 아키텍처 ✅ 완료
- Stage 2: 디자인 ✅ 완료
- Phase 0: 병렬 스캐폴딩 ✅ 완료
- Stage 3 / Sprint 1: Pine Parser MVP ✅ 완료 (2026-04-15)
- Stage 3 / Sprint 2: vectorbt Engine + SignalResult Fill ✅ 완료 (2026-04-15)
- Stage 3 / Sprint 3: Strategy API + Clerk 실배선 ✅ 완료 (2026-04-15)
- Stage 3 / Sprint 4: Celery + Backtest REST API ✅ 완료 (2026-04-16, PR #3 merge `777e623`)
- Sprint 5 Stage A: docs sync ✅ 완료 (2026-04-16, vision.md 보강 + ADR-005 + TODO.md 동기화)
- Sprint 5 Stage B ✅ 완료 (2026-04-16, PR #6 ready, 406 tests / CI green)
  - M1: DateTime tz-aware + Engine bar_index fix + Metadata diff ([ADR-005](docs/dev-log/005-datetime-tz-aware.md))
  - M2: market_data infra (TimescaleDB hypertable + OHLCVRepository + advisory lock)
  - M3: CCXT + TimescaleProvider + lifespan/worker singleton + backtest 통합
  - M4: Beat schedule (5분 reclaim) + docker-compose worker/beat + Strategy pagination drift
- Sprint 6 Trading 데모 MVP ✅ 완료 (2026-04-16, PR #9 — 자동 집행 + Kill Switch + AES-256, 34 commits)
- Sprint 7a Bybit Futures + Cross Margin ✅ 완료 (2026-04-17, PR #10 — leverage/margin_mode + leverage cap, 524 tests)
- Sprint 7c FE 따라잡기 (Strategy CRUD UI) ✅ 완료 (2026-04-17, 3 라우트 + Monaco Pine Monarch + shadcn/ui 12개 + sonner + Delete 409 archive fallback + design-review 7-pass 5/10→9/10)
- Sprint 7b Edit 페이지 Pine 이터레이션 UX ✅ 완료 (2026-04-17, `feat/sprint7b-edit-parse-ux`) — ISSUE-003/004 해소. BE `ParsePreviewResponse.functions_used` 1필드 확장(migration 없음) + FE TabCode 마운트 자동 파싱 + TabParse 4-섹션 구조(에러→경고→감지→메타). 528 BE / 9 FE vitest green
- ADR-011 Pine Execution Strategy v4 (Alert Hook Parser + 3-Track) ✅ 문서화 완료 (2026-04-17, PR #17 merge `d36793e`) — 상위 아키텍처 + Phase -1 ~ Phase 4 로드맵 + 세션 아카이브
- Sprint 8a-pre Phase -1 실측 ✅ 완료 (2026-04-18, PR #18 merge `0f6583d`) — pynescript 6/6 vs QB 0/6 실증. 상세: [`docs/superpowers/plans/2026-04-18-phase-minus-1-measurement-plan.md`](docs/superpowers/plans/2026-04-18-phase-minus-1-measurement-plan.md) · [`findings.md`](.gstack/experiments/phase-minus-1-drfx/output/phase-1-findings.md)
- ADR-011 Phase -1 amendment ✅ 완료 (2026-04-18, PR #19 merge `41037a9`) — §9 신뢰도 8→9, §12 blocker 2개 해소, §4 Tier-2 KPI 재정의, §6 H1 MVP scope 축소, §13 실측 부록
- Sprint 8a Tier-0 Foundation ✅ 완료 (2026-04-18, PR #20 merge `08c6388`) — pine_v2/ 8 레이어 + s1_pbr.pine E2E 완주, 169 tests
- Sprint 8b Tier-1 + Tier-0 렌더링 + 6/6 corpus + Opus/Sonnet 교차 hardening ✅ 완료 (2026-04-18, PR #21 merge `c79b10c`) — VirtualStrategyWrapper + RenderingRegistry + v4 alias/iff + switch/stdev/variance + v4 strategy.entry boolean/when= + time/timestamp(month/day 반영) + 40+ Pine enum constants + deleted line 정책. **6 corpus 완주 (2/6 → 6/6)**, 224 pine_v2 tests (+55), backend 750 전체 green
- Sprint 8c user-defined function + 3-Track dispatcher ✅ 완료 (2026-04-19, PR #22 `feat/sprint8c-user-function-3track`) — FunctionDef 등록(top-level guard) + scope stack + multi-return tuple unpack + ta.barssince/ta.valuewhen + tostring/request.security NOP + color.\* NOP + input kwarg 수정 + pivothigh/low 3-arg + parse_and_run_v2 S/A/M dispatcher + RunResult에 strategy_state/var_series 노출. **s3_rsid strict=True 완주 + trade ≥ 1, i3_drfx supertrend tuple unpack 검증**. 252 pine_v2 tests (+28), 778 backend green. eng-review 1-pass 반영 (top-level FunctionDef guard, \_exec_reassign 로컬 frame 단위 테스트 critical gap)
- **다음:** TabParse FE 1질문 UX (별도 세션, FE 따라잡기) · Sprint 7d (OKX + Trading Sessions) H1 내 · pine_v2 H2 심화 (local history ring, valuewhen cap, user function 호출 사이트 stdlib state isolation)

---

## 스택 규칙 참조

> `.ai/rules/`는 심링크 허브. 원본은 `.ai/common/`, `.ai/stacks/`, `.ai/project/`에 위치.
> **Codex CLI / Gemini CLI:** 이 파일만 자동 로딩됩니다. 작업 전 아래 파일을 수동으로 읽으세요.

| 파일                         | 내용                                   | 적용                                                          |
| ---------------------------- | -------------------------------------- | ------------------------------------------------------------- |
| `.ai/rules/global.md`        | 워크플로우, 문서화 규칙, Git, 환경변수 | **전체**                                                      |
| `.ai/rules/typescript.md`    | TypeScript Strict, 네이밍 컨벤션       | **전체**                                                      |
| `.ai/rules/nextjs-shared.md` | Next.js 공통 (Zod v4, shadcn, 반응형)  | **Frontend**                                                  |
| `.ai/rules/frontend.md`      | Next.js 16 FE-only (FastAPI BE 조합)   | **Frontend**                                                  |
| `.ai/rules/backend.md`       | FastAPI + SQLModel                     | **Backend**                                                   |
| `.ai/rules/fullstack.md`     | Next.js 16 Full-Stack + Drizzle ORM    | **패턴만 차용** (ActionResult, error.tsx, Server/Client 경계) |
| ~~`.ai/rules/mobile.md`~~    | ~~Flutter~~                            | **미사용**                                                    |
| `.ai/project/lessons.md`     | 프로젝트 학습 기록 (실수 → 규칙 승격)  | **활성**                                                      |

### QuantBridge 고유 규칙 (도메인 특화)

- 금융 숫자는 `Decimal` 사용 (float 금지) — 가격, 수량, 수익률
  - **Decimal-first 합산:** `Decimal(str(a)) + Decimal(str(b))` — `Decimal(str(a + b))` 금지 (float 공간 합산 후 변환 시 precision 손실)
    `[Sprint 4 D8 교훈 → 영구 규칙]`
- 백테스트/최적화는 반드시 Celery 비동기 (API 핸들러 직접 실행 금지)
  - **Celery prefork-safe:** SQLAlchemy `create_async_engine()` / vectorbt 등 무거운 객체는 모듈 import 시점 호출 금지. Lazy init 함수로 워커 자식 프로세스 fork 후 생성. Worker pool=prefork 고정 (gevent/eventlet 비호환)
    `[Sprint 4 D3 교훈 → 영구 규칙]`
- 거래소 API Key는 AES-256 암호화 저장 (평문 금지)
- OHLCV 데이터는 TimescaleDB hypertable에 저장
- 실시간 데이터는 WebSocket + Zustand 캐시 (React Query와 분리)
- Pine Script → Python 변환 시 `exec()`/`eval()` 절대 금지 — 인터프리터 패턴 또는 RestrictedPython/sandbox 필수
  `[/autoplan 2026-04-13, Codex+Claude 듀얼 검증, 신뢰도 10/10, ADR-003 참조]`
- Pine Script 미지원 함수 1개라도 포함 시 전체 "Unsupported" 반환 — 부분 실행 금지 (잘못된 결과 방지)
  `[/autoplan 2026-04-13, Codex+Claude 듀얼 검증, 신뢰도 10/10, ADR-003 참조]`

exec
/bin/zsh -lc "sed -n '1,240p' /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/docs/superpowers/reviews/2026-04-23-x1x3-w1-codex-self.md" in /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41
succeeded in 0ms:

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

exec
/bin/zsh -lc "sed -n '1,260p' /tmp/w1-diff.txt" in /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41
succeeded in 0ms:
diff --git a/backend/src/strategy/pine_v2/alert_hook.py b/backend/src/strategy/pine_v2/alert_hook.py
index c90bea5..2f50fe9 100644
--- a/backend/src/strategy/pine_v2/alert_hook.py
+++ b/backend/src/strategy/pine_v2/alert_hook.py
@@ -26,6 +26,7 @@ v1 한계 (Sprint 8b Tier-1에서 완성 예정):
from **future** import annotations

import json
+import os
import re
from collections.abc import Iterator
from dataclasses import dataclass
@@ -113,14 +114,58 @@ \_KEYWORD_RULES: list[tuple[SignalKind, tuple[str, ...]]] = [
)),
]

+# loose 모드: INFORMATION을 마지막 우선순위로 이동 + bull/bear는 prefix 매칭(bullish/bearish)
+# (Sprint X1 — i2_luxalgo 류 LuxAlgo indicator alert을 매매 신호로 분류 가능하게 함)
+\_KEYWORD_RULES_LOOSE: list[tuple[SignalKind, tuple[str, ...]]] = [

- (SignalKind.LONG_EXIT, (
-        r"\bclose\s+long\b", r"\bexit\s+long\b", r"롱\s*청산", r"매수\s*청산",
- )),
- (SignalKind.SHORT_EXIT, (
-        r"\bclose\s+short\b", r"\bexit\s+short\b", r"숏\s*청산", r"매도\s*청산",
- )),
- (SignalKind.LONG_ENTRY, (
-        r"\blong\b", r"\bbuy\b", r"\bbull", r"매수",
- )),
- (SignalKind.SHORT_ENTRY, (
-        r"\bshort\b", r"\bsell\b", r"\bbear", r"매도",
- )),
- (SignalKind.INFORMATION, (
-        r"\bbreak\b", r"\btrendline\b", r"\bsession\b", r"\bpivot\b",
-        r"돌파", r"세션",
- )),
  +]
-
- +def \_get_heuristic_mode() -> str:
- """환경변수 `PINE_ALERT_HEURISTIC_MODE` 를 읽어 'strict' 또는 'loose' 반환.
-
- - 미설정·잘못된 값 → 'strict' (후방호환).
- - 대소문자 무관(`LOOSE`/`Loose`/`loose` 모두 동일).
- - **lazy read** — `os.environ.get` 호출이 매번 일어나므로 pytest monkeypatch가
-      안전하게 동작한다 (모듈 import 시점 캐싱 없음).
-
- loose 모드는 break/trendline/session/pivot 같은 context 키워드보다
- 방향 키워드(long/short/bull/bear/매수/매도)를 우선 매칭하여 LuxAlgo류
- indicator alert을 매매 신호로 분류할 수 있게 한다.
- """
- raw = os.environ.get("PINE_ALERT_HEURISTIC_MODE", "strict")
- mode = raw.lower().strip() if isinstance(raw, str) else "strict"
- return "loose" if mode == "loose" else "strict"
- def classify_message(text: str) -> SignalKind:

* """문자열(메시지 또는 조건식 stringify)을 신호 종류로 분류."""

- """문자열(메시지 또는 조건식 stringify)을 신호 종류로 분류.
-
- 모드 (환경변수 `PINE_ALERT_HEURISTIC_MODE`):
- - **strict** (default): INFORMATION(break/trendline/session/pivot) > 방향 > UNKNOWN
- - **loose**: 방향(long/short/bull*/bear*/매수/매도) > INFORMATION > UNKNOWN
-      (loose는 bull/bear에 한해 prefix 매칭으로 'bullish'/'bearish'도 잡음)
- """
  if not text:
  return SignalKind.UNKNOWN

  stripped = text.strip()

* # 1. JSON 파싱 시도

- # 1. JSON 파싱 시도 (모드 무관)
       if stripped.startswith("{") and stripped.endswith("}"):
           try:
               data = json.loads(stripped)
  @@ -136,8 +181,9 @@ def classify_message(text: str) -> SignalKind:
  except (json.JSONDecodeError, ValueError):
  pass

* # 2. 키워드 매칭
* for signal, patterns in \_KEYWORD_RULES:

- # 2. 키워드 매칭 (모드별 rule set 선택)
- rules = \_KEYWORD_RULES_LOOSE if \_get_heuristic_mode() == "loose" else \_KEYWORD_RULES
- for signal, patterns in rules:
  for pat in patterns:
  if re.search(pat, text, flags=re.IGNORECASE):
  return signal
  diff --git a/backend/tests/strategy/pine_v2/test_alert_hook.py b/backend/tests/strategy/pine_v2/test_alert_hook.py
  index 1408caf..42d70ff 100644
  --- a/backend/tests/strategy/pine_v2/test_alert_hook.py
  +++ b/backend/tests/strategy/pine_v2/test_alert_hook.py
  @@ -205,3 +205,101 @@ def test_collect_alerts_preserves_enclosing_if_test_ast_for_alert() -> None:
  h = hooks[0]
  assert h.condition_ast is not None
  assert isinstance(h.condition_ast, pyne_ast.Compare)
-
- +# -------- v2: loose mode (Sprint X1) --------------------------------------
-
- +@pytest.fixture
  +def loose_mode(monkeypatch: pytest.MonkeyPatch) -> None:
- monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "loose")
-
- +@pytest.fixture
  +def strict_mode(monkeypatch: pytest.MonkeyPatch) -> None:
- monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "strict")
-
- +def test_loose_mode_breakout_long_becomes_long_entry(loose_mode: None) -> None:
- """loose: 'Long break of trendline' → LONG_ENTRY (방향 키워드가 INFORMATION 우선).
-
- 이 메시지는 strict에서는 INFORMATION (`\bbreak\b` + `\btrendline\b` 우선),
- loose에서는 LONG_ENTRY (`\blong\b` 우선) — 두 모드의 동작 차이를 명확히 증명.
- """
- assert classify_message("Long break of trendline") == SignalKind.LONG_ENTRY
-
- +def test_loose_mode_short_breakout_becomes_short_entry(loose_mode: None) -> None:
- """loose: 'Short break of trendline' → SHORT_ENTRY."""
- assert classify_message("Short break of trendline") == SignalKind.SHORT_ENTRY
-
- +def test_loose_mode_pure_information_still_information(loose_mode: None) -> None:
- """loose 에서도 방향 키워드 없는 순수 information 은 INFORMATION."""
- assert classify_message("Session started") == SignalKind.INFORMATION
- assert classify_message("Pivot formed at high") == SignalKind.INFORMATION
-
- +def test_strict_mode_preserves_legacy_behavior(strict_mode: None) -> None:
- """strict (default): break/trendline word-boundary 매칭 시 INFORMATION 우선.
-
- 참고: `\bbreak\b` word boundary 때문에 'breakout'(붙어있는 한 단어)은
- INFORMATION으로 매칭되지 않는다 — 기존 baseline 그대로. 본 테스트는
- 정확히 이 baseline을 보존(공백으로 분리된 'break of trendline')함을
- 증명한다.
- """
- assert classify_message("Short break of trendline") == SignalKind.INFORMATION
- assert classify_message("Long break of trendline") == SignalKind.INFORMATION
-
- +def test_unset_mode_defaults_to_strict(monkeypatch: pytest.MonkeyPatch) -> None:
- """환경변수 미설정 시 strict (후방호환 보장).
-
- "Long break of trendline" 처럼 word-boundary `\bbreak\b` 가 명확히 매칭되는
- 문장으로 strict의 INFORMATION 우선 동작을 검증.
- """
- monkeypatch.delenv("PINE_ALERT_HEURISTIC_MODE", raising=False)
- assert classify_message("Long break of trendline") == SignalKind.INFORMATION
-
- +def test_loose_mode_uppercase_env_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
- """PINE_ALERT_HEURISTIC_MODE=LOOSE (대문자) → loose로 정규화."""
- monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "LOOSE")
- assert classify_message("Long breakout confirmed") == SignalKind.LONG_ENTRY
-
- +def test_invalid_mode_falls_back_to_strict(monkeypatch: pytest.MonkeyPatch) -> None:
- """잘못된 값(foo/오타) → strict fallback (`\bbreak\b` INFORMATION 우선)."""
- monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "foo")
- assert classify_message("Long break of trendline") == SignalKind.INFORMATION
-
- +def test_empty_string_env_falls_back_to_strict(monkeypatch: pytest.MonkeyPatch) -> None:
- """빈 문자열 env → strip 후 빈값 → strict fallback (codex review 권고)."""
- monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "")
- assert classify_message("Long break of trendline") == SignalKind.INFORMATION
-
- +def test_whitespace_env_falls_back_to_strict(monkeypatch: pytest.MonkeyPatch) -> None:
- """공백만 있는 env → strip 후 빈값 → strict fallback."""
- monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", " ")
- assert classify_message("Long break of trendline") == SignalKind.INFORMATION
-
- +def test_loose_mode_empty_message_unknown(loose_mode: None) -> None:
- """빈 문자열 → mode 무관 UNKNOWN."""
- assert classify_message("") == SignalKind.UNKNOWN
-
- +def test_loose_mode_bullish_breakout_is_long_entry(loose_mode: None) -> None:
- """'Bullish breakout' → loose=LONG_ENTRY (bull/bullish prefix 매칭).
-
- `\bbull` (word-start, no end boundary) prefix로 'Bullish' / 'bullish' 매칭.
- loose 모드 전용 — strict는 기존 word-boundary `\bbull\b` 유지.
- """
- assert classify_message("Bullish breakout") == SignalKind.LONG_ENTRY
-
- +def test_loose_mode_bearish_break_is_short_entry(loose_mode: None) -> None:
- """대칭: 'Bearish breakdown' → loose=SHORT_ENTRY."""
- assert classify_message("Bearish breakdown") == SignalKind.SHORT_ENTRY
  diff --git a/docs/superpowers/reviews/2026-04-23-x1x3-w1-codex-self.md b/docs/superpowers/reviews/2026-04-23-x1x3-w1-codex-self.md
  new file mode 100644
  index 0000000..fee9196
  --- /dev/null
  +++ b/docs/superpowers/reviews/2026-04-23-x1x3-w1-codex-self.md
  @@ -0,0 +1,47 @@
  +# W1 Codex Self-Review — Alert Heuristic `loose` 모드
- +**Date:** 2026-04-23 +**Worker:** Sprint X1+X3 W1 +**Diff scope:** `backend/src/strategy/pine_v2/alert_hook.py` + `backend/tests/strategy/pine_v2/test_alert_hook.py` +**Reviewer:** `codex exec --sandbox read-only` (codex-cli 0.122.0)
- +---
- +## 1st pass — GO_WITH_FIX (8/10)
- +Findings:
- +1. **Missing empty-string env coverage** — Requirement (5) asked for env edge cases including empty string, but `monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "")` was not tested. Code falls back to strict via `strip()` but coverage gap.
  +2. **Weak loose-vs-strict boundary test** — `test_loose_mode_breakout_long_becomes_long_entry` used `"Long breakout confirmed"`, which is `LONG_ENTRY` in BOTH strict and loose (`\bbreak\b` does not match `breakout`). Did not actually distinguish the two modes.
- +Checks 1-4 + 6 partial (5 partial): PASS for strict baseline preservation, INFORMATION pure preservation, lazy env read, and intended semantic drift only.
- +## Fixes applied
- +- **Added** `test_empty_string_env_falls_back_to_strict` (env `""` → strict).
  +- **Added** `test_whitespace_env_falls_back_to_strict` (env `"   "` → strict; covers `strip()` path).
  +- **Changed** `test_loose_mode_breakout_long_becomes_long_entry` from `"Long breakout confirmed"` to `"Long break of trendline"` — this message is INFORMATION in strict (matched by `\bbreak\b` + `\btrendline\b`) and LONG_ENTRY in loose (matched by `\blong\b` first), proving the two-mode boundary.
- +## 2nd pass — GO (9/10)
- +Verdict: **GO**, confidence **9/10**. All 6 criteria met. No remaining findings.
- +Confirmed:
  +1. Empty-string env test added at `test_alert_hook.py:277`
  +2. Whitespace env test added at `test_alert_hook.py:283`
  +3. Boundary-distinguishing message in test at `test_alert_hook.py:223`
  +4. `_get_heuristic_mode()` lazy-read + `lower().strip()` + invalid/empty/whitespace → strict fallback consistent
  +5. Backward compat preserved: `test_unset_mode_defaults_to_strict`, `test_invalid_mode_falls_back_to_strict`, `test_loose_mode_uppercase_env_normalized`
  +6. strict/loose semantic separation fixed: strict legacy preserved (`:243`), loose pure-information preserved (`:237`), bullish/bearish prefix extended (`:294`, `:303`)
- +## Final verification
- +`
+backend/tests/strategy/pine_v2/test_alert_hook.py — 43 passed
+backend/tests/strategy/pine_v2/test_e2e_i2_luxalgo.py — 3 passed (PINE_ALERT_HEURISTIC_MODE=loose)
+backend pytest -q — 934 passed, 1 skipped (pre-existing)
+`
- +## Decision
- +**GO** — proceed to commit. No additional iterations required.

codex
입력 산출물은 확인했습니다. 이제 실제 소스 파일의 라인 번호와 기존 베이스라인을 직접 대조해, self-review 주장과 diff 내용이 일치하는지 확인하겠습니다.
exec
/bin/zsh -lc "nl -ba backend/src/strategy/pine_v2/alert_hook.py | sed -n '80,230p'" in /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41
exec
/bin/zsh -lc "test -f docs/README.md && sed -n '1,220p' docs/README.md || true" in /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41
succeeded in 0ms:

# QuantBridge — 문서 인덱스

> TradingView Pine Script → 백테스트 → 데모/라이브 트레이딩 플랫폼

## 기술 스택

| 영역            | 기술                                                                        |
| --------------- | --------------------------------------------------------------------------- |
| Frontend        | Next.js 16, TypeScript, Tailwind CSS v4, shadcn/ui v4, React Query, Zustand |
| Backend         | FastAPI, Python 3.11+, SQLModel, Pydantic V2, Celery                        |
| Auth            | Clerk (Frontend + Backend JWT 검증)                                         |
| Database        | PostgreSQL + TimescaleDB + Redis                                            |
| Backtest Engine | vectorbt, pandas-ta, Optuna                                                 |
| Exchange        | CCXT (Bybit, Binance, OKX)                                                  |
| Infra           | Docker Compose (dev)                                                        |

## 문서 구조

| 디렉토리                               | 내용                                   | 상태     |
| -------------------------------------- | -------------------------------------- | -------- |
| [00_project/](./00_project/)           | 프로젝트 비전, 개요                    | ✅ 완료  |
| [01_requirements/](./01_requirements/) | 요구사항 개요, REQ 카탈로그, Pine 분석 | ✅ 완료  |
| [02_domain/](./02_domain/)             | 도메인 개요, 엔티티, 상태 머신         | ✅ 완료  |
| [03_api/](./03_api/)                   | API 엔드포인트 스펙                    | ✅ 활성  |
| [04_architecture/](./04_architecture/) | ERD, 시스템 아키텍처, 데이터 흐름      | ✅ 완료  |
| [05_env/](./05_env/)                   | 로컬 셋업, 환경 변수, Clerk 가이드     | ✅ 완료  |
| [06_devops/](./06_devops/)             | Docker Compose, CI/CD, Pre-commit      | ✅ 완료  |
| [07_infra/](./07_infra/)               | 배포·Observability·Runbook (draft)     | 📝 Draft |
| [DESIGN.md](../DESIGN.md)              | 디자인 시스템 (색상, 타이포, 컴포넌트) | ✅ 확정  |
| [prototypes/](./prototypes/)           | Stage 2 HTML 프로토타입 (12개 화면)    | ✅ 확정  |
| [dev-log/](./dev-log/)                 | ADR (의사결정 기록)                    | 활성     |
| [guides/](./guides/)                   | 개발 가이드, Sprint 킥오프 템플릿      | 활성     |
| [TODO.md](./TODO.md)                   | 작업 추적                              | 활성     |

## 빠른 시작

```bash
# 1. 인프라 실행
docker compose up -d

# 2. Frontend
cd frontend && pnpm install && pnpm dev

# 3. Backend
cd backend && uv sync && uvicorn src.main:app --reload
```

## 핵심 의사결정 (gstack 스킬 확정)

> 아래 결정은 `/office-hours` + `/autoplan` (Codex+Claude 듀얼 검증) 으로 확정됨.
> **규칙 변경 전 반드시 ADR 확인 및 보안/아키텍처 재검토 필요.**

- **제품 프레이밍:** QuantBridge = TradingView Trust Layer (범용 퀀트 ❌)
  MVP 핵심 화면: Import → Verify → Verdict
  타겟: 파트타임 크립토 트레이더, $1K~$50K, Python 없음
  `[/office-hours 2026-04-13]`

- **Pine 런타임 + 파서 범위:** [ADR-003](./dev-log/003-pine-runtime-safety-and-parser-scope.md)
  - `exec()`/`eval()` 금지 → 인터프리터 패턴
  - 미지원 함수 1개라도 있으면 전체 "Unsupported" (부분 실행 금지)
  - Celery zombie task 복구 인프라 필수 (on_failure + Beat cleanup + cancel)
  - TV 상위 50개 전략 분류 선행 (80%+ 커버리지 가정 폐기)
    `[/autoplan 2026-04-13, Codex+Claude 듀얼 검증]`

## 주요 문서 바로가기

| 문서                                                                                                         | 설명                                    |
| ------------------------------------------------------------------------------------------------------------ | --------------------------------------- |
| [DESIGN.md](../DESIGN.md)                                                                                    | 디자인 시스템 (Stage 2 산출물)          |
| [QUANTBRIDGE_PRD.md](../QUANTBRIDGE_PRD.md)                                                                  | 상세 PRD                                |
| [AGENTS.md](../AGENTS.md)                                                                                    | AI 에이전트 컨텍스트                    |
| [.ai/](../.ai/)                                                                                              | 코딩 규칙                               |
| [01_requirements/requirements-overview.md](./01_requirements/requirements-overview.md)                       | 요구사항 개요 + REQ 인덱스              |
| [01_requirements/req-catalog.md](./01_requirements/req-catalog.md)                                           | REQ-### 상세 카탈로그                   |
| [02_domain/domain-overview.md](./02_domain/domain-overview.md)                                               | 8 도메인 경계 + 책임 매트릭스           |
| [02_domain/entities.md](./02_domain/entities.md)                                                             | ENT-### 엔티티 카탈로그                 |
| [02_domain/state-machines.md](./02_domain/state-machines.md)                                                 | 도메인 상태 전이도                      |
| [04_architecture/system-architecture.md](./04_architecture/system-architecture.md)                           | C4 다이어그램 + 인증/에러 경계          |
| [04_architecture/data-flow.md](./04_architecture/data-flow.md)                                               | 도메인별 시퀀스 다이어그램              |
| [05_env/local-setup.md](./05_env/local-setup.md)                                                             | 로컬 개발 환경 5분 셋업                 |
| [05_env/env-vars.md](./05_env/env-vars.md)                                                                   | 환경 변수 의미·획득법 카탈로그          |
| [05_env/clerk-setup.md](./05_env/clerk-setup.md)                                                             | Clerk 외부 의존성 셋업                  |
| [06_devops/docker-compose-guide.md](./06_devops/docker-compose-guide.md)                                     | Compose 운영 가이드                     |
| [06_devops/ci-cd.md](./06_devops/ci-cd.md)                                                                   | CI 잡 그래프 + 게이트                   |
| [06_devops/pre-commit.md](./06_devops/pre-commit.md)                                                         | husky + lint-staged 가이드              |
| [07_infra/deployment-plan.md](./07_infra/deployment-plan.md)                                                 | 배포 옵션 비교 (draft)                  |
| [07_infra/observability-plan.md](./07_infra/observability-plan.md)                                           | Observability 계획 (draft)              |
| [07_infra/runbook.md](./07_infra/runbook.md)                                                                 | 운영 Runbook (draft)                    |
| [guides/development-methodology.md](./guides/development-methodology.md)                                     | 6-Stage 개발 방법론 + 병렬 개발 전략    |
| [guides/sprint-kickoff-template.md](./guides/sprint-kickoff-template.md)                                     | Sprint 킥오프 프롬프트 템플릿           |
| [dev-log/001-tech-stack.md](./dev-log/001-tech-stack.md)                                                     | ADR-001: 기술 스택 결정                 |
| [dev-log/002-parallel-scaffold-strategy.md](./dev-log/002-parallel-scaffold-strategy.md)                     | ADR-002: 병렬 스캐폴딩 전략             |
| [dev-log/003-pine-runtime-safety-and-parser-scope.md](./dev-log/003-pine-runtime-safety-and-parser-scope.md) | ADR-003: Pine 런타임 안전성 + 파서 범위 |
| [dev-log/004-pine-parser-approach-selection.md](./dev-log/004-pine-parser-approach-selection.md)             | ADR-004: Pine 파서 접근법 선택          |

succeeded in 0ms:
80 def to_dict(self) -> dict[str, Any]:
81 return {
82 "index": self.index,
83 "kind": self.kind,
84 "message": self.message,
85 "condition_expr": self.condition_expr,
86 "enclosing_if_condition": self.enclosing_if_condition,
87 "enclosing_if_branch": self.enclosing_if_branch,
88 "resolved_condition": self.resolved_condition,
89 "message_signal": self.message_signal.value,
90 "condition_signal": (
91 self.condition_signal.value if self.condition_signal is not None else None
92 ),
93 "signal": self.signal.value,
94 "discrepancy": self.discrepancy,
95 }
96
97
98 \_KEYWORD_RULES: list[tuple[SignalKind, tuple[str, ...]]] = [
99 (SignalKind.INFORMATION, (
100 r"\bbreak\b", r"\btrendline\b", r"\bsession\b", r"\bpivot\b",
101 r"돌파", r"세션",
102 )),
103 (SignalKind.LONG_EXIT, (
104 r"\bclose\s+long\b", r"\bexit\s+long\b", r"롱\s*청산", r"매수\s*청산",
105 )),
106 (SignalKind.SHORT_EXIT, (
107 r"\bclose\s+short\b", r"\bexit\s+short\b", r"숏\s*청산", r"매도\s*청산",
108 )),
109 (SignalKind.LONG_ENTRY, (
110 r"\blong\b", r"\bbuy\b", r"\bbull\b", r"매수",
111 )),
112 (SignalKind.SHORT_ENTRY, (
113 r"\bshort\b", r"\bsell\b", r"\bbear\b", r"매도",
114 )),
115 ]
116
117 # loose 모드: INFORMATION을 마지막 우선순위로 이동 + bull/bear는 prefix 매칭(bullish/bearish)
118 # (Sprint X1 — i2_luxalgo 류 LuxAlgo indicator alert을 매매 신호로 분류 가능하게 함)
119 \_KEYWORD_RULES_LOOSE: list[tuple[SignalKind, tuple[str, ...]]] = [
120 (SignalKind.LONG_EXIT, (
121 r"\bclose\s+long\b", r"\bexit\s+long\b", r"롱\s*청산", r"매수\s*청산",
122 )),
123 (SignalKind.SHORT_EXIT, (
124 r"\bclose\s+short\b", r"\bexit\s+short\b", r"숏\s*청산", r"매도\s*청산",
125 )),
126 (SignalKind.LONG_ENTRY, (
127 r"\blong\b", r"\bbuy\b", r"\bbull", r"매수",
128 )),
129 (SignalKind.SHORT_ENTRY, (
130 r"\bshort\b", r"\bsell\b", r"\bbear", r"매도",
131 )),
132 (SignalKind.INFORMATION, (
133 r"\bbreak\b", r"\btrendline\b", r"\bsession\b", r"\bpivot\b",
134 r"돌파", r"세션",
135 )),
136 ]
137
138
139 def \_get_heuristic_mode() -> str:
140 """환경변수 `PINE_ALERT_HEURISTIC_MODE` 를 읽어 'strict' 또는 'loose' 반환.
141
142 - 미설정·잘못된 값 → 'strict' (후방호환).
143 - 대소문자 무관(`LOOSE`/`Loose`/`loose` 모두 동일).
144 - **lazy read** — `os.environ.get` 호출이 매번 일어나므로 pytest monkeypatch가
145 안전하게 동작한다 (모듈 import 시점 캐싱 없음).
146
147 loose 모드는 break/trendline/session/pivot 같은 context 키워드보다
148 방향 키워드(long/short/bull/bear/매수/매도)를 우선 매칭하여 LuxAlgo류
149 indicator alert을 매매 신호로 분류할 수 있게 한다.
150 """
151 raw = os.environ.get("PINE_ALERT_HEURISTIC_MODE", "strict")
152 mode = raw.lower().strip() if isinstance(raw, str) else "strict"
153 return "loose" if mode == "loose" else "strict"
154
155
156 def classify_message(text: str) -> SignalKind:
157 """문자열(메시지 또는 조건식 stringify)을 신호 종류로 분류.
158
159 모드 (환경변수 `PINE_ALERT_HEURISTIC_MODE`):
160 - **strict** (default): INFORMATION(break/trendline/session/pivot) > 방향 > UNKNOWN
161 - **loose**: 방향(long/short/bull*/bear*/매수/매도) > INFORMATION > UNKNOWN
162 (loose는 bull/bear에 한해 prefix 매칭으로 'bullish'/'bearish'도 잡음)
163 """
164 if not text:
165 return SignalKind.UNKNOWN
166
167 stripped = text.strip()
168 # 1. JSON 파싱 시도 (모드 무관)
169 if stripped.startswith("{") and stripped.endswith("}"):
170 try:
171 data = json.loads(stripped)
172 action = str(data.get("action", "")).lower()
173 if action in ("buy", "long"):
174 return SignalKind.LONG_ENTRY
175 if action in ("sell", "short"):
176 return SignalKind.SHORT_ENTRY
177 if action in ("close_long", "exit_long"):
178 return SignalKind.LONG_EXIT
179 if action in ("close_short", "exit_short"):
180 return SignalKind.SHORT_EXIT
181 except (json.JSONDecodeError, ValueError):
182 pass
183
184 # 2. 키워드 매칭 (모드별 rule set 선택)
185 rules = \_KEYWORD_RULES_LOOSE if \_get_heuristic_mode() == "loose" else \_KEYWORD_RULES
186 for signal, patterns in rules:
187 for pat in patterns:
188 if re.search(pat, text, flags=re.IGNORECASE):
189 return signal
190
191 # 3. Fallback
192 return SignalKind.UNKNOWN
193
194
195 def \_stringify(node: Any) -> str:
196 if isinstance(node, pyne_ast.Constant):
197 return str(node.value)
198 if isinstance(node, pyne_ast.Name):
199 return node.id
200 if isinstance(node, pyne_ast.Attribute):
201 return f"{\_stringify(node.value)}.{node.attr}"
202 if isinstance(node, pyne_ast.BinOp):
203 return f"{\_stringify(node.left)} + {\_stringify(node.right)}"
204 if isinstance(node, pyne_ast.Compare):
205 left = \_stringify(node.left)
206 comps = getattr(node, "comparators", [])
207 if comps:
208 return f"{left} <cmp> {\_stringify(comps[0])}"
209 return left
210 if isinstance(node, pyne_ast.BoolOp):
211 op = type(node.op).**name**.lower() # And | Or
212 values = getattr(node, "values", [])
213 return f" {op} ".join(\_stringify(v) for v in values)
214 if isinstance(node, pyne_ast.UnaryOp):
215 return f"not {\_stringify(node.operand)}"
216 if isinstance(node, pyne_ast.Call):
217 func = \_stringify(node.func)
218 args = ", ".join(
219 \_stringify(a.value if isinstance(a, pyne_ast.Arg) else a)
220 for a in node.args[:2]
221 )
222 if len(node.args) > 2:
223 args += ", ..."
224 return f"{func}({args})"
225 return f"<{type(node).**name**}>"
226
227
228 def \_is_call_named(node: Any, names: tuple[str, ...]) -> bool:
229 if not isinstance(node, pyne_ast.Call):
230 return False

exec
/bin/zsh -lc "nl -ba backend/tests/strategy/pine*v2/test_alert_hook.py | sed -n '1,360p'" in /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41
succeeded in 0ms:
1 """Alert Hook 추출 + 메시지/조건 분류기 v1 회귀.
2
3 Day 6 스냅샷 `alert_hook_report.json`과 완전 일치해야 한다 (v1 schema:
4 enclosing_if*_ / resolved*condition / message_signal / condition_signal /
5 signal / discrepancy 필드 추가).
6
7 v0 → v1 개선 자동 감지 요건:
8 - i3_drfx #2 message='BUY' + condition='bear' → **자동 discrepancy=True**
9 - condition_signal이 None(불가)인 경우 message_signal로 fallback
10 - alert inside `if cond`의 enclosing 컨텍스트 추적
11 """
12 from **future** import annotations
13
14 import json
15 from pathlib import Path
16
17 import pytest
18
19 from src.strategy.pine_v2.alert_hook import (
20 SignalKind,
21 classify_message,
22 collect_alerts,
23 )
24
25 \_CORPUS_DIR = Path(**file**).parents[2] / "fixtures" / "pine_corpus_v2"
26 \_REPORT: dict[str, list[dict]] = json.loads(
27 (\_CORPUS_DIR / "alert_hook_report.json").read_text()
28 )
29
30
31 @pytest.mark.parametrize("script_name", sorted(\_REPORT.keys()))
32 def test_collect_alerts_matches_baseline(script_name: str) -> None:
33 source = (\_CORPUS_DIR / f"{script_name}.pine").read_text()
34 actual = [h.to_dict() for h in collect_alerts(source)]
35 expected = \_REPORT[script_name]
36
37 assert actual == expected, (
38 f"{script_name}: alert 추출/분류 드리프트\n"
39 f" expected: {expected}\n"
40 f" actual: {actual}"
41 )
42
43
44 def test_total_alert_count_across_corpus() -> None:
45 """ADR-011 §2.1 Alert Hook 사전 조사: Track A 3종에서 alert 총 10개."""
46 total = sum(len(hooks) for hooks in \_REPORT.values())
47 assert total == 10
48
49
50 def test_classify_coverage_v1() -> None:
51 """v1 커버리지: 10 alert 모두 final signal 결정 (unknown 0)."""
52 unknown = 0
53 for hooks in \_REPORT.values():
54 for h in hooks:
55 if h["signal"] == SignalKind.UNKNOWN.value:
56 unknown += 1
57 assert unknown == 0
58
59
60 @pytest.mark.parametrize(("message", "expected"), [
61 ("BUY", SignalKind.LONG_ENTRY),
62 ("buy at market", SignalKind.LONG_ENTRY),
63 ("SELL", SignalKind.SHORT_ENTRY),
64 ("매수 진입", SignalKind.LONG_ENTRY),
65 ("매도 청산", SignalKind.SHORT_EXIT),
66 ("Close Long", SignalKind.LONG_EXIT),
67 ("exit short now", SignalKind.SHORT_EXIT),
68 ("Price broke the trendline", SignalKind.INFORMATION),
69 ("pivot high detected", SignalKind.INFORMATION),
70 ('{"action":"buy"}', SignalKind.LONG_ENTRY),
71 ('{"action":"sell","size":1}', SignalKind.SHORT_ENTRY),
72 ('{"action":"close_long"}', SignalKind.LONG_EXIT),
73 ("", SignalKind.UNKNOWN),
74 ("hello world", SignalKind.UNKNOWN),
75 ])
76 def test_classify_message_keyword_rules(message: str, expected: SignalKind) -> None:
77 assert classify_message(message) == expected
78
79
80 def test_information_takes_precedence_over_direction_keyword() -> None:
81 """'Price broke the down-trendline upward'는 information (break/trendline 우선)."""
82 assert classify_message("Price broke the down-trendline upward") == SignalKind.INFORMATION
83
84
85 # -------- v1 핵심: condition-trace 자동 감지 --------------------------
86
87
88 def test_i3_drfx_alert_2_auto_discrepancy_detection() -> None:
89 """v1 핵심 가치: message='BUY' + condition=`bear` 불일치 **자동 감지**.
90
91 v0에서는 수동 assertion만 있었고, v1은 condition_signal 분류 후
92 message_signal 과 비교하여 discrepancy=True로 자동 플래그.
93 최종 권고 signal은 condition 기반 우선 (short_entry).
94 """
95 drfx = \_REPORT["i3_drfx"]
96 alert_2 = next(h for h in drfx if h["index"] == 2)
97 assert alert_2["message"] == "BUY"
98 assert alert_2["condition_expr"] == "bear"
99 assert alert_2["message_signal"] == SignalKind.LONG_ENTRY.value
100 assert alert_2["condition_signal"] == SignalKind.SHORT_ENTRY.value
101 assert alert_2["discrepancy"] is True, (
102 "v1 condition-trace가 message-condition mismatch를 자동 플래그해야 함"
103 )
104 assert alert_2["signal"] == SignalKind.SHORT_ENTRY.value, (
105 "최종 권고는 condition 우선 — BUY 메시지 오타/저자 실수 보호"
106 )
107
108
109 def test_no_other_discrepancy_in_corpus() -> None:
110 """i3_drfx #2 외에는 discrepancy 없어야 — 의도치 않은 false positive 방지."""
111 discrepancies = [
112 (name, h["index"])
113 for name, hooks in \_REPORT.items()
114 for h in hooks
115 if h["discrepancy"]
116 ]
117 assert discrepancies == [("i3_drfx", 2)], (
118 f"기대 discrepancy 1건 (i3_drfx #2)만. 실측: {discrepancies}"
119 )
120
121
122 def test_alertcondition_condition_expr_captured_for_all() -> None:
123 """alertcondition은 arg0을 condition_expr에 항상 기록해야."""
124 for name, hooks in \_REPORT.items():
125 for h in hooks:
126 if h["kind"] == "alertcondition":
127 assert h["condition_expr"] is not None, (
128 f"{name} #{h['index']} alertcondition인데 condition_expr 없음"
129 )
130
131
132 def test_bare_alert_uses_enclosing_if_branch() -> None:
133 """alert() (bare)는 감싸는 if 컨텍스트를 enclosing_if*_ 필드로 기록해야."""
134 drfx = \_REPORT["i3_drfx"]
135 bare_alerts = [h for h in drfx if h["kind"] == "alert"]
136 assert len(bare_alerts) == 4, "i3_drfx에 bare alert은 4개 (#3,4,5,6)"
137 for h in bare_alerts:
138 assert h["enclosing_if_condition"] is not None, (
139 f"bare alert #{h['index']}은 if 안에 있으므로 enclosing_if_condition 있어야"
140 )
141 assert h["enclosing_if_branch"] == "then", (
142 "모든 bare alert은 THEN 분기 (ELSE 케이스는 corpus에 없음)"
143 )
144
145
146 def test_resolved_condition_performs_variable_lookup() -> None:
147 """i3_drfx #1 `bull` 변수가 resolved_condition에서 정의 expression으로 풀려야."""
148 drfx = \_REPORT["i3_drfx"]
149 alert_1 = next(h for h in drfx if h["index"] == 1)
150 assert alert_1["condition_expr"] == "bull"
151 assert alert_1["resolved_condition"] is not None
152 assert "ta.crossover" in alert_1["resolved_condition"], (
153 "bull 변수는 ta.crossover 기반으로 정의되어야 함"
154 )
155
156
157 def test_condition_signal_prioritizes_variable_name_over_resolved() -> None:
158 """변수명 자체가 의미 있는 경우(bull/bear), 해석 결과보다 변수명 우선.
159
160 i3_drfx #1: condition_expr='bull' → LONG_ENTRY (resolved=ta.crossover(...)도 동일 의도이나
161 키워드 매칭 불가). 분류기는 원본 변수명을 먼저 시도해야 한다.
162 """
163 drfx = \_REPORT["i3_drfx"]
164 alert_1 = next(h for h in drfx if h["index"] == 1)
165 assert alert_1["condition_signal"] == SignalKind.LONG_ENTRY.value, (
166 "condition_expr='bull' → bull 키워드 매칭으로 long_entry"
167 )
168
169
170 # --- Sprint 8b: condition_ast 필드 (Tier-1 bar 단위 재평가용) ---------
171
172
173 def test_collect_alerts_preserves_condition_ast_for_alertcondition() -> None:
174 """AlertHook.condition_ast가 alertcondition arg0의 원본 AST 노드를 보존해야 함."""
175 from pynescript import ast as pyne_ast
176
177 source = (
178 "//@version=5\n"
179 "indicator('t', overlay=true)\n"
180 "buy = close > open\n"
181 "alertcondition(buy, 'Long', 'LONG')\n"
182 )
183 hooks = collect_alerts(source)
184 assert len(hooks) == 1
185 h = hooks[0]
186 # condition_ast는 존재해야 하고 AST 노드(Name/Compare/BoolOp 등)
187 assert h.condition_ast is not None
188 assert isinstance(
189 h.condition_ast, (pyne_ast.Name, pyne_ast.Compare, pyne_ast.BoolOp)
190 )
191
192
193 def test_collect_alerts_preserves_enclosing_if_test_ast_for_alert() -> None:
194 """alert() 호출의 경우 enclosing if의 test AST가 condition_ast에 보존."""
195 from pynescript import ast as pyne_ast
196
197 source = (
198 "//@version=5\n"
199 "indicator('t', overlay=true)\n"
200 "if close > open\n"
201 " alert('LONG', alert.freq_once_per_bar)\n"
202 )
203 hooks = collect_alerts(source)
204 assert len(hooks) == 1
205 h = hooks[0]
206 assert h.condition_ast is not None
207 assert isinstance(h.condition_ast, pyne_ast.Compare)
208
209
210 # -------- v2: loose mode (Sprint X1) --------------------------------------
211
212
213 @pytest.fixture
214 def loose_mode(monkeypatch: pytest.MonkeyPatch) -> None:
215 monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "loose")
216
217
218 @pytest.fixture
219 def strict_mode(monkeypatch: pytest.MonkeyPatch) -> None:
220 monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "strict")
221
222
223 def test_loose_mode_breakout_long_becomes_long_entry(loose_mode: None) -> None:
224 """loose: 'Long break of trendline' → LONG_ENTRY (방향 키워드가 INFORMATION 우선).
225
226 이 메시지는 strict에서는 INFORMATION (`\bbreak\b` + `\btrendline\b` 우선),
227 loose에서는 LONG_ENTRY (`\blong\b` 우선) — 두 모드의 동작 차이를 명확히 증명.
228 """
229 assert classify_message("Long break of trendline") == SignalKind.LONG_ENTRY
230
231
232 def test_loose_mode_short_breakout_becomes_short_entry(loose_mode: None) -> None:
233 """loose: 'Short break of trendline' → SHORT_ENTRY."""
234 assert classify_message("Short break of trendline") == SignalKind.SHORT_ENTRY
235
236
237 def test_loose_mode_pure_information_still_information(loose_mode: None) -> None:
238 """loose 에서도 방향 키워드 없는 순수 information 은 INFORMATION."""
239 assert classify_message("Session started") == SignalKind.INFORMATION
240 assert classify_message("Pivot formed at high") == SignalKind.INFORMATION
241
242
243 def test_strict_mode_preserves_legacy_behavior(strict_mode: None) -> None:
244 """strict (default): break/trendline word-boundary 매칭 시 INFORMATION 우선.
245
246 참고: `\bbreak\b` word boundary 때문에 'breakout'(붙어있는 한 단어)은
247 INFORMATION으로 매칭되지 않는다 — 기존 baseline 그대로. 본 테스트는
248 정확히 이 baseline을 보존(공백으로 분리된 'break of trendline')함을
249 증명한다.
250 """
251 assert classify_message("Short break of trendline") == SignalKind.INFORMATION
252 assert classify_message("Long break of trendline") == SignalKind.INFORMATION
253
254
255 def test_unset_mode_defaults_to_strict(monkeypatch: pytest.MonkeyPatch) -> None:
256 """환경변수 미설정 시 strict (후방호환 보장).
257
258 "Long break of trendline" 처럼 word-boundary `\bbreak\b` 가 명확히 매칭되는
259 문장으로 strict의 INFORMATION 우선 동작을 검증.
260 """
261 monkeypatch.delenv("PINE_ALERT_HEURISTIC_MODE", raising=False)
262 assert classify_message("Long break of trendline") == SignalKind.INFORMATION
263
264
265 def test_loose_mode_uppercase_env_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
266 """PINE_ALERT_HEURISTIC_MODE=LOOSE (대문자) → loose로 정규화."""
267 monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "LOOSE")
268 assert classify_message("Long breakout confirmed") == SignalKind.LONG_ENTRY
269
270
271 def test_invalid_mode_falls_back_to_strict(monkeypatch: pytest.MonkeyPatch) -> None:
272 """잘못된 값(foo/오타) → strict fallback (`\bbreak\b` INFORMATION 우선)."""
273 monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "foo")
274 assert classify_message("Long break of trendline") == SignalKind.INFORMATION
275
276
277 def test_empty_string_env_falls_back_to_strict(monkeypatch: pytest.MonkeyPatch) -> None:
278 """빈 문자열 env → strip 후 빈값 → strict fallback (codex review 권고)."""
279 monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "")
280 assert classify_message("Long break of trendline") == SignalKind.INFORMATION
281
282
283 def test_whitespace_env_falls_back_to_strict(monkeypatch: pytest.MonkeyPatch) -> None:
284 """공백만 있는 env → strip 후 빈값 → strict fallback."""
285 monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", " ")
286 assert classify_message("Long break of trendline") == SignalKind.INFORMATION
287
288
289 def test_loose_mode_empty_message_unknown(loose_mode: None) -> None:
290 """빈 문자열 → mode 무관 UNKNOWN."""
291 assert classify_message("") == SignalKind.UNKNOWN
292
293
294 def test_loose_mode_bullish_breakout_is_long_entry(loose_mode: None) -> None:
295 """'Bullish breakout' → loose=LONG_ENTRY (bull/bullish prefix 매칭).
296
297 `\bbull` (word-start, no end boundary) prefix로 'Bullish' / 'bullish' 매칭.
298 loose 모드 전용 — strict는 기존 word-boundary `\bbull\b` 유지.
299 """
300 assert classify_message("Bullish breakout") == SignalKind.LONG_ENTRY
301
302
303 def test_loose_mode_bearish_break_is_short_entry(loose_mode: None) -> None:
304 """대칭: 'Bearish breakdown' → loose=SHORT_ENTRY."""
305 assert classify_message("Bearish breakdown") == SignalKind.SHORT_ENTRY

exec
/bin/zsh -lc "git show stage/x1-x3-indicator-ui:backend/src/strategy/pine_v2/alert_hook.py | nl -ba | sed -n '80,170p'" in /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41
succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-3XoYWzlr' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-2xR6nLcQ' (errno=Operation not permitted)
80 return {
81 "index": self.index,
82 "kind": self.kind,
83 "message": self.message,
84 "condition_expr": self.condition_expr,
85 "enclosing_if_condition": self.enclosing_if_condition,
86 "enclosing_if_branch": self.enclosing_if_branch,
87 "resolved_condition": self.resolved_condition,
88 "message_signal": self.message_signal.value,
89 "condition_signal": (
90 self.condition_signal.value if self.condition_signal is not None else None
91 ),
92 "signal": self.signal.value,
93 "discrepancy": self.discrepancy,
94 }
95
96
97 \_KEYWORD_RULES: list[tuple[SignalKind, tuple[str, ...]]] = [
98 (SignalKind.INFORMATION, (
99 r"\bbreak\b", r"\btrendline\b", r"\bsession\b", r"\bpivot\b",
100 r"돌파", r"세션",
101 )),
102 (SignalKind.LONG_EXIT, (
103 r"\bclose\s+long\b", r"\bexit\s+long\b", r"롱\s*청산", r"매수\s*청산",
104 )),
105 (SignalKind.SHORT_EXIT, (
106 r"\bclose\s+short\b", r"\bexit\s+short\b", r"숏\s*청산", r"매도\s*청산",
107 )),
108 (SignalKind.LONG_ENTRY, (
109 r"\blong\b", r"\bbuy\b", r"\bbull\b", r"매수",
110 )),
111 (SignalKind.SHORT_ENTRY, (
112 r"\bshort\b", r"\bsell\b", r"\bbear\b", r"매도",
113 )),
114 ]
115
116
117 def classify_message(text: str) -> SignalKind:
118 """문자열(메시지 또는 조건식 stringify)을 신호 종류로 분류."""
119 if not text:
120 return SignalKind.UNKNOWN
121
122 stripped = text.strip()
123 # 1. JSON 파싱 시도
124 if stripped.startswith("{") and stripped.endswith("}"):
125 try:
126 data = json.loads(stripped)
127 action = str(data.get("action", "")).lower()
128 if action in ("buy", "long"):
129 return SignalKind.LONG_ENTRY
130 if action in ("sell", "short"):
131 return SignalKind.SHORT_ENTRY
132 if action in ("close_long", "exit_long"):
133 return SignalKind.LONG_EXIT
134 if action in ("close_short", "exit_short"):
135 return SignalKind.SHORT_EXIT
136 except (json.JSONDecodeError, ValueError):
137 pass
138
139 # 2. 키워드 매칭
140 for signal, patterns in \_KEYWORD_RULES:
141 for pat in patterns:
142 if re.search(pat, text, flags=re.IGNORECASE):
143 return signal
144
145 # 3. Fallback
146 return SignalKind.UNKNOWN
147
148
149 def \_stringify(node: Any) -> str:
150 if isinstance(node, pyne_ast.Constant):
151 return str(node.value)
152 if isinstance(node, pyne_ast.Name):
153 return node.id
154 if isinstance(node, pyne_ast.Attribute):
155 return f"{\_stringify(node.value)}.{node.attr}"
156 if isinstance(node, pyne_ast.BinOp):
157 return f"{\_stringify(node.left)} + {\_stringify(node.right)}"
158 if isinstance(node, pyne_ast.Compare):
159 left = \_stringify(node.left)
160 comps = getattr(node, "comparators", [])
161 if comps:
162 return f"{left} <cmp> {\_stringify(comps[0])}"
163 return left
164 if isinstance(node, pyne_ast.BoolOp):
165 op = type(node.op).**name**.lower() # And | Or
166 values = getattr(node, "values", [])
167 return f" {op} ".join(\_stringify(v) for v in values)
168 if isinstance(node, pyne_ast.UnaryOp):
169 return f"not {\_stringify(node.operand)}"
170 if isinstance(node, pyne_ast.Call):

codex
실제 파일 기준으로 strict 규칙 집합은 베이스 브랜치와 동일하고, 새 loose 집합만 별도로 추가된 점은 확인했습니다. 마지막으로 실행 증거가 필요한 항목만 최소 범위로 확인해 self-review의 수치와 실제 가능 여부를 분리하겠습니다.
exec
/bin/zsh -lc 'PYTHONDONTWRITEBYTECODE=1 pytest -q tests/strategy/pine_v2/test_alert_hook.py -p no:cacheprovider' in /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend
exited 127 in 0ms:
zsh:1: command not found: pytest

exec
/bin/zsh -lc 'PYTHONDONTWRITEBYTECODE=1 PINE_ALERT_HEURISTIC_MODE=loose pytest -q tests/strategy/pine_v2/test_e2e_i2_luxalgo.py -p no:cacheprovider' in /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend
exited 127 in 0ms:
zsh:1: command not found: pytest

codex
로컬 실행 증거는 이 워크트리 환경 제약을 받습니다. `pytest` 자체가 PATH에 없어서 self-review에 적힌 테스트 숫자는 여기서 재현되지 않았고, 대신 순수 정적 검토와 최소 런타임 확인 가능한 범위만 더 보겠습니다.
exec
/bin/zsh -lc "python -c \"import os; from src.strategy.pine_v2.alert_hook import classify_message; cases=[('unset',None,'Long break of trendline'),('loose','loose','Long break of trendline'),('strict','strict','Long break of trendline'),('LOOSE','LOOSE','Long breakout confirmed'),('invalid','foo','Long break of trendline'),('empty','','Long break of trendline'),('space',' ','Long break of trendline'),('loose-bullish','loose','Bullish breakout'),('loose-info','loose','Session started'),('loose-empty-msg','loose','')];
for label,mode,msg in cases:
os.environ.pop('PINE_ALERT_HEURISTIC_MODE',None) if mode is None else os.environ.**setitem**('PINE_ALERT_HEURISTIC_MODE',mode);
print(label, classify_message(msg).value)\"" in /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend
exited 127 in 0ms:
zsh:1: command not found: python

exec
/bin/zsh -lc 'uv --version' in /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend
succeeded in 0ms:
uv 0.10.4 (079e3fd05 2026-02-17)

exec
/bin/zsh -lc 'rg -n "934 passed|936 passed|43 passed|PINE_ALERT_HEURISTIC_MODE" -S docs backend /tmp/w1-diff.txt' in /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41
succeeded in 0ms:
/tmp/w1-diff.txt:40:+ """환경변수 `PINE_ALERT_HEURISTIC_MODE` 를 읽어 'strict' 또는 'loose' 반환.
/tmp/w1-diff.txt:51:+ raw = os.environ.get("PINE_ALERT_HEURISTIC_MODE", "strict")
/tmp/w1-diff.txt:60:+ 모드 (환경변수 `PINE_ALERT_HEURISTIC_MODE`):
/tmp/w1-diff.txt:101:+ monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "loose")
/tmp/w1-diff.txt:106:+ monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "strict")
/tmp/w1-diff.txt:147:+ monkeypatch.delenv("PINE_ALERT_HEURISTIC_MODE", raising=False)
/tmp/w1-diff.txt:152:+ """PINE_ALERT_HEURISTIC_MODE=LOOSE (대문자) → loose로 정규화."""
/tmp/w1-diff.txt:153:+ monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "LOOSE")
/tmp/w1-diff.txt:159:+ monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "foo")
/tmp/w1-diff.txt:165:+ monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "")
/tmp/w1-diff.txt:171:+ monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", " ")
/tmp/w1-diff.txt:211:+1. **Missing empty-string env coverage** — Requirement (5) asked for env edge cases including empty string, but `monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "")` was not tested. Code falls back to strict via `strip()` but coverage gap.
/tmp/w1-diff.txt:237:+backend/tests/strategy/pine_v2/test_alert_hook.py — 43 passed
/tmp/w1-diff.txt:238:+backend/tests/strategy/pine_v2/test_e2e_i2_luxalgo.py — 3 passed (PINE_ALERT_HEURISTIC_MODE=loose)
/tmp/w1-diff.txt:239:+backend pytest -q — 934 passed, 1 skipped (pre-existing)
docs/superpowers/reviews/2026-04-23-x1x3-w1-codex-self.md:14:1. **Missing empty-string env coverage** — Requirement (5) asked for env edge cases including empty string, but `monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "")` was not tested. Code falls back to strict via `strip()` but coverage gap.
docs/superpowers/reviews/2026-04-23-x1x3-w1-codex-self.md:40:backend/tests/strategy/pine_v2/test_alert_hook.py — 43 passed
docs/superpowers/reviews/2026-04-23-x1x3-w1-codex-self.md:41:backend/tests/strategy/pine_v2/test_e2e_i2_luxalgo.py — 3 passed (PINE_ALERT_HEURISTIC_MODE=loose)
docs/superpowers/reviews/2026-04-23-x1x3-w1-codex-self.md:42:backend pytest -q — 934 passed, 1 skipped (pre-existing)
backend/src/strategy/pine_v2/alert_hook.py:140: """환경변수 `PINE_ALERT_HEURISTIC_MODE` 를 읽어 'strict' 또는 'loose' 반환.
backend/src/strategy/pine_v2/alert_hook.py:151: raw = os.environ.get("PINE_ALERT_HEURISTIC_MODE", "strict")
backend/src/strategy/pine_v2/alert_hook.py:159: 모드 (환경변수 `PINE_ALERT_HEURISTIC_MODE`):
backend/tests/strategy/pine_v2/test_alert_hook.py:215: monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "loose")
backend/tests/strategy/pine_v2/test_alert_hook.py:220: monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "strict")
backend/tests/strategy/pine_v2/test_alert_hook.py:261: monkeypatch.delenv("PINE_ALERT_HEURISTIC_MODE", raising=False)
backend/tests/strategy/pine_v2/test_alert_hook.py:266: """PINE_ALERT_HEURISTIC_MODE=LOOSE (대문자) → loose로 정규화."""
backend/tests/strategy/pine_v2/test_alert_hook.py:267: monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "LOOSE")
backend/tests/strategy/pine_v2/test_alert_hook.py:273: monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "foo")
backend/tests/strategy/pine_v2/test_alert_hook.py:279: monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "")
backend/tests/strategy/pine_v2/test_alert_hook.py:285: monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", " ")

codex
한 가지 규칙성 리스크가 보여서 환경변수 카탈로그도 바로 대조하겠습니다. 이 프로젝트는 `.env.example`에 없는 env 참조를 금지하므로, `PINE_ALERT_HEURISTIC_MODE` 선언 여부를 확인해야 합니다.
exec
/bin/zsh -lc "rg --files -g '.env.example' -g '\*\*/.env.example'" in /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41
succeeded in 0ms:
.env.example
frontend/.env.example
backend/.env.example

exec
/bin/zsh -lc 'rg -n "PINE_ALERT_HEURISTIC_MODE" -S .' in /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41
succeeded in 0ms:
./backend/src/strategy/pine_v2/alert_hook.py:140: """환경변수 `PINE_ALERT_HEURISTIC_MODE` 를 읽어 'strict' 또는 'loose' 반환.
./backend/src/strategy/pine_v2/alert_hook.py:151: raw = os.environ.get("PINE_ALERT_HEURISTIC_MODE", "strict")
./backend/src/strategy/pine_v2/alert_hook.py:159: 모드 (환경변수 `PINE_ALERT_HEURISTIC_MODE`):
./docs/superpowers/reviews/2026-04-23-x1x3-w1-codex-self.md:14:1. **Missing empty-string env coverage** — Requirement (5) asked for env edge cases including empty string, but `monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "")` was not tested. Code falls back to strict via `strip()` but coverage gap.
./docs/superpowers/reviews/2026-04-23-x1x3-w1-codex-self.md:41:backend/tests/strategy/pine_v2/test_e2e_i2_luxalgo.py — 3 passed (PINE_ALERT_HEURISTIC_MODE=loose)
./backend/tests/strategy/pine_v2/test_alert_hook.py:215: monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "loose")
./backend/tests/strategy/pine_v2/test_alert_hook.py:220: monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "strict")
./backend/tests/strategy/pine_v2/test_alert_hook.py:261: monkeypatch.delenv("PINE_ALERT_HEURISTIC_MODE", raising=False)
./backend/tests/strategy/pine_v2/test_alert_hook.py:266: """PINE_ALERT_HEURISTIC_MODE=LOOSE (대문자) → loose로 정규화."""
./backend/tests/strategy/pine_v2/test_alert_hook.py:267: monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "LOOSE")
./backend/tests/strategy/pine_v2/test_alert_hook.py:273: monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "foo")
./backend/tests/strategy/pine_v2/test_alert_hook.py:279: monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "")
./backend/tests/strategy/pine_v2/test_alert_hook.py:285: monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", " ")

exec
/bin/zsh -lc 'git status --short' in /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41
succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-9jkf53jV' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-THsZpxZ3' (errno=Operation not permitted)

exec
/bin/zsh -lc "sed -n '1,220p' backend/.env.example" in /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41
exec
/bin/zsh -lc 'rg -n "PINE*ALERT_HEURISTIC_MODE|ALERT_HEURISTIC|PINE*" .env.example backend/.env.example frontend/.env.example' in /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41
exited 1 in 0ms:
succeeded in 0ms:

# QuantBridge — Backend `.env.example` (uvicorn / celery worker)

#

# === 로드 주체 ===

# 이 파일을 `cp .env.example .env.local`로 복사.

# pydantic-settings SettingsConfigDict(env_file=(".env.local", ".env")) 가 자동 로드.

# 대상 명령: `cd backend && uv run uvicorn ...` / `uv run celery ...` / `uv run pytest` / `uv run alembic ...`

#

# === 컨테이너 실행 시 ===

# `docker compose up` 시 이 파일은 사용되지 않음. `docker-compose.yml`의 `environment:`가

# 루트 `.env`의 값을 interpolate해서 컨테이너에 주입. 즉 root `.env`와 이 파일은 공통 키를 복사 유지.

#

# === 다른 서비스 env 위치 ===

# - Docker compose: ../.env (root)

# - Next.js dev: ../frontend/.env.local

# =====================================================

# 앱 설정

# =====================================================

APP_NAME=QuantBridge
APP_ENV=development # development | staging | production
DEBUG=true
SECRET_KEY=dev-secret-change-in-prod # [기본값 OK] 프로덕션만 실값 필요

# =====================================================

# Clerk 인증 (Sprint 3+)

# =====================================================

# 받는 곳: https://dashboard.clerk.com → API Keys → Secret keys

CLERK_SECRET_KEY=sk_test_PASTE_YOUR_SECRET_KEY_HERE # [필수 Sprint 3+]
CLERK_WEBHOOK_SECRET=whsec_placeholder_sprint7_real_value # [필수 Sprint 7 배포]
WEBHOOK_SECRET_GRACE_SECONDS=3600 # [기본값 OK] rotation grace 기간

# =====================================================

# Database (Sprint 3+)

# =====================================================

# docker-compose의 db 서비스가 localhost:5432에서 노출. 값은 root .env의 POSTGRES\_\* 와 일치해야.

DATABASE_URL=postgresql+asyncpg://quantbridge:password@localhost:5432/quantbridge # [기본값 OK]

# =====================================================

# Redis / Celery (Sprint 4+)

# =====================================================

REDIS_URL=redis://localhost:6379/0 # [기본값 OK] 캐시
CELERY_BROKER_URL=redis://localhost:6379/1 # [기본값 OK]
CELERY_RESULT_BACKEND=redis://localhost:6379/2 # [기본값 OK]

# =====================================================

# Sprint 6+ Trading

# =====================================================

# Fernet 마스터 키 — 거래소 API Key AES-256 암호화.

# 생성: uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# root .env의 TRADING_ENCRYPTION_KEYS와 동일 값 유지 (compose worker와 로컬 uvicorn이 같은 키여야 복호화 일관).

TRADING_ENCRYPTION_KEYS= # [필수 Sprint 6+]

# =====================================================

# Exchange (Sprint 5+)

# =====================================================

EXCHANGE_PROVIDER=fixture # fixture | bybit_demo | bybit_futures
BYBIT_FUTURES_MAX_LEVERAGE=20 # [기본값 OK] Sprint 7a leverage 상한
OHLCV_PROVIDER=timescale # fixture | timescale. timescale=CCXT live fetch + Hypertable 캐시. fixture 는 CI/oracle 전용.
OHLCV_FIXTURE_ROOT=backend/data/fixtures/ohlcv # [기본값 OK]
DEFAULT_EXCHANGE=bybit # [기본값 OK]

# =====================================================

# Kill Switch (Sprint 6+)

# =====================================================

KILL_SWITCH_CUMULATIVE_LOSS_PERCENT=10.0 # [기본값 OK]
KILL_SWITCH_DAILY_LOSS_USD=500.0 # [기본값 OK]
KILL_SWITCH_API_ERROR_STREAK=5 # [기본값 OK]
KILL_SWITCH_CAPITAL_BASE_USD=10000 # [기본값 OK] Sprint 6은 config, 7b부터 동적 바인딩

# =====================================================

# Backtest (Sprint 4+)

# =====================================================

BACKTEST_STALE_THRESHOLD_SECONDS=1800 # [기본값 OK]

# =====================================================

# CORS

# =====================================================

FRONTEND_URL=http://localhost:3000 # [기본값 OK]

exec
/bin/zsh -lc "sed -n '1,220p' .env.example" in /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41
succeeded in 0ms:

# QuantBridge — Root `.env.example` (docker compose 전용)

#

# === 로드 주체 ===

# 이 파일을 `cp .env.example .env`로 복사. docker compose는 `./env`를 자동 로드.

# `docker-compose.yml`의 `${VAR}` interpolation이 여기를 참조.

# backend/frontend 각자 loader는 별도 `.env.example` (해당 디렉토리) 사용.

#

# === 다른 서비스 env 위치 ===

# - Backend uvicorn/celery (로컬 실행): backend/.env.example → backend/.env.local

# - Frontend Next.js dev: frontend/.env.example → frontend/.env.local

#

# === 범례 ===

# [필수 Sprint N] : 해당 스프린트부터 실값 필요

# [기본값 OK] : 로컬 개발은 이 값 그대로

# =====================================================

# PostgreSQL (docker-compose `db` 서비스)

# =====================================================

POSTGRES_USER=quantbridge # [기본값 OK]
POSTGRES_PASSWORD=password # [기본값 OK] 로컬 전용
POSTGRES_DB=quantbridge # [기본값 OK]

# =====================================================

# Sprint 6+ Trading (docker-compose `backend-worker` interpolation)

# =====================================================

# Fernet 마스터 키 — 거래소 API Key AES-256 암호화용.

# 최초 1회만 생성, 변경 시 기존 암호화된 API Key 복호화 불가.

# 생성: cd backend && uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Rotation: 콤마 구분으로 여러 키 허용 (new_key,old_key). 첫 키 encrypt, 나머지 decrypt grace.

TRADING_ENCRYPTION_KEYS= # [필수 Sprint 6+]

# =====================================================

# Clerk 인증 (docker-compose `backend-worker` interpolation)

# =====================================================

# Compose로 워커를 띄울 때 backend/.env.local이 아닌 이 값을 사용.

# 로컬 uvicorn만 띄우면 backend/.env.local만 채워도 OK.

CLERK_SECRET_KEY=sk_test_PASTE_YOUR_SECRET_KEY_HERE # [필수 Sprint 3+]
CLERK_WEBHOOK_SECRET=whsec_placeholder_sprint7_real_value # [필수 Sprint 7 배포]

# =====================================================

# Exchange / Backtest (docker-compose `backend-worker` interpolation)

# =====================================================

EXCHANGE_PROVIDER=fixture # fixture | bybit_demo | bybit_futures
OHLCV_PROVIDER=timescale # fixture | timescale (Sprint 5 M3+). timescale=CCXT live fetch + Hypertable 캐시. fixture 는 CI/oracle 전용.
DEFAULT_EXCHANGE=bybit # [기본값 OK]
BACKTEST_STALE_THRESHOLD_SECONDS=1800 # [기본값 OK] worker stale 재클레임 threshold

exec
/bin/zsh -lc 'rg -n "PINE_ALERT_HEURISTIC_MODE|TRADING_ENCRYPTION_KEYS|BACKTEST_STALE_THRESHOLD_SECONDS" docs/05_env/env-vars.md' in /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41
succeeded in 0ms:
80:| `BACKTEST_STALE_THRESHOLD_SECONDS` | [기본값 OK] | RUNNING/CANCELLING 자동 reclaim 임계 (기본 1800s = 30분). Beat 5분 주기 + worker_ready hook 이중 안전망 |

exec
/bin/zsh -lc "nl -ba docs/05_env/env-vars.md | sed -n '60,100p'" in /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41
succeeded in 0ms:
60 > 테스트는 별도 DB `quantbridge_test` 사용. `pytest conftest`가 `DATABASE_URL` 우선.
61
62 ---
63
64 ## 5. Redis / Celery (Sprint 4+)
65
66 | 변수 | 마킹 | 설명 |
67 |------|------|------|
68 | `REDIS_URL` | [기본값 OK] | DB 0 — 캐시 |
69 | `CELERY_BROKER_URL` | [기본값 OK] | DB 1 — Celery 큐 |
70 | `CELERY_RESULT_BACKEND` | [기본값 OK] | DB 2 — Celery 결과 |
71
72 Redis maxmemory 정책은 compose 파일 (`--maxmemory 512mb --maxmemory-policy allkeys-lru`) 참조.
73
74 ---
75
76 ## 6. Backtest (Sprint 4)
77
78 | 변수 | 마킹 | 설명 |
79 |------|------|------|
80 | `BACKTEST_STALE_THRESHOLD_SECONDS` | [기본값 OK] | RUNNING/CANCELLING 자동 reclaim 임계 (기본 1800s = 30분). Beat 5분 주기 + worker_ready hook 이중 안전망 |
81 | `OHLCV_FIXTURE_ROOT` | [기본값 OK] | FixtureProvider가 OHLCV CSV 로드하는 경로 |
82 | `OHLCV_PROVIDER` | [기본값 OK] | `fixture`(기본) \| `timescale`. Sprint 5 M3 도입 — `timescale` 시 CCXT + TimescaleDB cache 사용 |
83
84 ---
85
86 ## 7. 암호화 (Sprint 7+ 거래소 연동)
87
88 | 변수 | 마킹 | 설명 |
89 |------|------|------|
90 | `ENCRYPTION_KEY` | [기본값 OK] (프로덕션 실값) | AES-256-GCM 32-byte. 거래소 API Key 암호화. 프로덕션은 `openssl rand -hex 32` |
91
92 > 프로덕션 키 회전 시 데이터 마이그레이션 필요 — Sprint 7+ 절차 정의 예정.
93
94 ---
95
96 ## 8. CORS / URL
97
98 | 변수 | 마킹 | 설명 |
99 |------|------|------|
100 | `FRONTEND_URL` | [기본값 OK] | 백엔드 CORS allowlist |

codex
질문 3과 7은 정적 diff만으로는 부족해서, 계획서/자가리뷰 문서의 라인 번호 근거까지 붙이겠습니다. 그다음 바로 판정을 정리하겠습니다.
exec
/bin/zsh -lc "nl -ba /Users/woosung/project/agy-project/quant-bridge/docs/superpowers/plans/2026-04-23-x1x3-w1-alert-heuristic-loose.md | sed -n '1,240p'" in /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41
exec
/bin/zsh -lc "nl -ba docs/superpowers/reviews/2026-04-23-x1x3-w1-codex-self.md | sed -n '1,120p'" in /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41
succeeded in 0ms:
1 # W1 Codex Self-Review — Alert Heuristic `loose` 모드
2
3 **Date:** 2026-04-23
4 **Worker:** Sprint X1+X3 W1
5 **Diff scope:** `backend/src/strategy/pine_v2/alert_hook.py` + `backend/tests/strategy/pine_v2/test_alert_hook.py`
6 **Reviewer:** `codex exec --sandbox read-only` (codex-cli 0.122.0)
7
8 ---
9
10 ## 1st pass — GO_WITH_FIX (8/10)
11
12 Findings:
13
14 1. **Missing empty-string env coverage** — Requirement (5) asked for env edge cases including empty string, but `monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "")` was not tested. Code falls back to strict via `strip()` but coverage gap.
15 2. **Weak loose-vs-strict boundary test** — `test_loose_mode_breakout_long_becomes_long_entry` used `"Long breakout confirmed"`, which is `LONG_ENTRY` in BOTH strict and loose (`\bbreak\b` does not match `breakout`). Did not actually distinguish the two modes.
16
17 Checks 1-4 + 6 partial (5 partial): PASS for strict baseline preservation, INFORMATION pure preservation, lazy env read, and intended semantic drift only.
18
19 ## Fixes applied
20
21 - **Added** `test_empty_string_env_falls_back_to_strict` (env `""` → strict).
22 - **Added** `test_whitespace_env_falls_back_to_strict` (env `"   "` → strict; covers `strip()` path).
23 - **Changed** `test_loose_mode_breakout_long_becomes_long_entry` from `"Long breakout confirmed"` to `"Long break of trendline"` — this message is INFORMATION in strict (matched by `\bbreak\b` + `\btrendline\b`) and LONG_ENTRY in loose (matched by `\blong\b` first), proving the two-mode boundary.
24
25 ## 2nd pass — GO (9/10)
26
27 Verdict: **GO**, confidence **9/10**. All 6 criteria met. No remaining findings.
28
29 Confirmed:
30 1. Empty-string env test added at `test_alert_hook.py:277`
31 2. Whitespace env test added at `test_alert_hook.py:283`
32 3. Boundary-distinguishing message in test at `test_alert_hook.py:223`
33 4. `_get_heuristic_mode()` lazy-read + `lower().strip()` + invalid/empty/whitespace → strict fallback consistent
34 5. Backward compat preserved: `test_unset_mode_defaults_to_strict`, `test_invalid_mode_falls_back_to_strict`, `test_loose_mode_uppercase_env_normalized`
35 6. strict/loose semantic separation fixed: strict legacy preserved (`:243`), loose pure-information preserved (`:237`), bullish/bearish prefix extended (`:294`, `:303`)
36
37 ## Final verification
38
39 `
    40	backend/tests/strategy/pine_v2/test_alert_hook.py — 43 passed
    41	backend/tests/strategy/pine_v2/test_e2e_i2_luxalgo.py — 3 passed (PINE_ALERT_HEURISTIC_MODE=loose)
    42	backend pytest -q — 934 passed, 1 skipped (pre-existing)
    43	`
44
45 ## Decision
46
47 **GO** — proceed to commit. No additional iterations required.

succeeded in 0ms:
1 # W1 — Alert Heuristic `loose` 모드 (i2_luxalgo 0 trades 해소)
2
3 > **Session:** Sprint X1+X3, 2026-04-23 | **Worker:** 1 / 5
4 > **Branch:** `stage/x1-x3-indicator-ui` (Option C staging, 직접 push)
5 > **TDD Mode:** **정석 TDD** — heuristic rule은 공유 로직 + semantic drift 위험
6
7 ---
8
9 ## 1. Context (self-contained — 워커 cold start 전제)
10
11 QuantBridge 는 TradingView Pine Script 전략을 실행하는 플랫폼. `alert()` / `alertcondition()` 을 매매 신호로 분류하는 heuristic 이 `backend/src/strategy/pine_v2/alert_hook.py` 에 있다.
12
13 **현재 공백**: LuxAlgo Trendlines with Breaks 지표 (`i2_luxalgo`) 는 `breakout` / `trendline` / `session` 키워드를 사용하는데, 현재 `_KEYWORD_RULES` (line 97-114) 가 이를 **무조건 `INFORMATION` 으로 우선 분류** → backtest 에서 0 trades.
14
15 **해결 방향**: 환경변수 `PINE_ALERT_HEURISTIC_MODE` 도입
16
17 - `strict` (default) — 현재 동작 유지 (breakout/trendline → INFORMATION)
18 - `loose` — INFORMATION 우선순위를 LONG/SHORT 뒤로 이동 → breakout/trendline 문맥에서도 방향 키워드 (long/buy/bull 등) 가 있으면 LONG_ENTRY 로 분류
19
20 ---
21
22 ## 2. Acceptance Criteria
23
24 ### 정량
25
26 - [ ] `PINE_ALERT_HEURISTIC_MODE=strict` (or unset) 기본: 기존 `test_alert_hook.py` 전수 PASS (24+ 테스트)
27 - [ ] `PINE_ALERT_HEURISTIC_MODE=loose` 환경에서 신규 테스트: i2_luxalgo fixture 재생 시 ≥ 1 trade 발생 (LONG_ENTRY 분류)
28 - [ ] 회귀 금지: loose 모드에서도 `test_information_takes_precedence_over_direction_keyword` 와 동등한 **순수 INFORMATION** ("세션 시작", "pivot formed") 은 INFORMATION 유지
29 - [ ] backend pytest 전체 녹색 (pine_v2 + 타 모듈 회귀 0)
30
31 ### 정성
32
33 - [ ] `classify_message()` signature 변경 없음 (후방호환) — `mode` 는 `os.environ` 에서 lazy read 또는 optional 2번째 인자 (default=strict)
34 - [ ] 새 모드 문서화 — `alert_hook.py` docstring + inline 주석
35 - [ ] 사용자 memory 규칙 준수: Decimal-first 등 pine_v2 관례 유지
36
37 ---
38
39 ## 3. File Structure
40
41 **수정:**
42
43 - `backend/src/strategy/pine_v2/alert_hook.py` — 환경변수 읽기 + mode 분기
44 - `backend/tests/strategy/pine_v2/test_alert_hook.py` — mode 별 파라미터라이즈 테스트 추가
45
46 **신규 (선택):** 없음 — 기존 파일만 확장.
47
48 ---
49
50 ## 4. TDD Tasks
51
52 ### T1. 실패 테스트 작성 (loose 모드 기대값)
53
54 **Step 1 — 테스트 추가** (`backend/tests/strategy/pine_v2/test_alert_hook.py` 끝에):
55
56 `python
    57	# -------- v2: loose mode (Sprint X1) --------------------------------------
    58	
    59	import os
    60	import pytest
    61	
    62	
    63	@pytest.fixture
    64	def loose_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    65	    monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "loose")
    66	
    67	
    68	@pytest.fixture
    69	def strict_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    70	    monkeypatch.setenv("PINE_ALERT_HEURISTIC_MODE", "strict")
    71	
    72	
    73	def test_loose_mode_breakout_long_becomes_long_entry(loose_mode: None) -> None:
    74	    """loose: 'Long breakout confirmed' → LONG_ENTRY (방향 키워드 우선)."""
    75	    assert classify_message("Long breakout confirmed") == SignalKind.LONG_ENTRY
    76	
    77	
    78	def test_loose_mode_short_breakout_becomes_short_entry(loose_mode: None) -> None:
    79	    assert classify_message("Short break of trendline") == SignalKind.SHORT_ENTRY
    80	
    81	
    82	def test_loose_mode_pure_information_still_information(loose_mode: None) -> None:
    83	    """loose 에서도 방향 키워드 없는 순수 information 은 INFORMATION."""
    84	    assert classify_message("Session started") == SignalKind.INFORMATION
    85	    assert classify_message("Pivot formed at high") == SignalKind.INFORMATION
    86	
    87	
    88	def test_strict_mode_preserves_legacy_behavior(strict_mode: None) -> None:
    89	    """strict (default) 에서는 breakout/trendline 이 INFORMATION 우선."""
    90	    assert classify_message("Long breakout confirmed") == SignalKind.INFORMATION
    91	    assert classify_message("Short break of trendline") == SignalKind.INFORMATION
    92	
    93	
    94	def test_unset_mode_defaults_to_strict(monkeypatch: pytest.MonkeyPatch) -> None:
    95	    monkeypatch.delenv("PINE_ALERT_HEURISTIC_MODE", raising=False)
    96	    assert classify_message("Long breakout") == SignalKind.INFORMATION
    97	`
98
99 **Step 2 — 실패 확인:**
100
101 `bash
   102	cd backend && uv run pytest tests/strategy/pine_v2/test_alert_hook.py::test_loose_mode_breakout_long_becomes_long_entry -v
   103	`
104
105 Expected: FAIL (loose 분기 없음 → 여전히 INFORMATION 반환)
106
107 ### T2. 최소 구현
108
109 **Step 3 — `alert_hook.py` 수정:**
110
111 ``python
   112	# alert_hook.py 상단 import 에 추가
   113	import os
   114	
   115	# ... (기존 _KEYWORD_RULES 유지) ...
   116	
   117	# 신규: loose 모드 rule 순서 (INFORMATION 을 마지막으로)
   118	_KEYWORD_RULES_LOOSE: list[tuple[SignalKind, tuple[str, ...]]] = [
   119	    (SignalKind.LONG_EXIT, (
   120	        r"\bclose\s+long\b", r"\bexit\s+long\b", r"롱\s*청산", r"매수\s*청산",
   121	    )),
   122	    (SignalKind.SHORT_EXIT, (
   123	        r"\bclose\s+short\b", r"\bexit\s+short\b", r"숏\s*청산", r"매도\s*청산",
   124	    )),
   125	    (SignalKind.LONG_ENTRY, (
   126	        r"\blong\b", r"\bbuy\b", r"\bbull\b", r"매수",
   127	    )),
   128	    (SignalKind.SHORT_ENTRY, (
   129	        r"\bshort\b", r"\bsell\b", r"\bbear\b", r"매도",
   130	    )),
   131	    (SignalKind.INFORMATION, (
   132	        r"\bbreak\b", r"\btrendline\b", r"\bsession\b", r"\bpivot\b",
   133	        r"돌파", r"세션",
   134	    )),
   135	]
   136	
   137	
   138	def _get_heuristic_mode() -> str:
   139	    """환경변수 `PINE_ALERT_HEURISTIC_MODE` 를 읽어 'strict' 또는 'loose' 반환.
   140	
   141	    - 미설정 또는 잘못된 값 → 'strict' (후방호환).
   142	    - loose 모드는 `breakout/trendline/session` 등 context 키워드보다
   143	      방향 키워드(long/short 등)를 우선 매칭하여 LuxAlgo류 indicator alert 을
   144	      매매 신호로 분류할 수 있게 한다.
   145	    """
   146	    mode = os.environ.get("PINE_ALERT_HEURISTIC_MODE", "strict").lower().strip()
   147	    return "loose" if mode == "loose" else "strict"
   148	
   149	
   150	def classify_message(text: str) -> SignalKind:
   151	    """문자열(메시지 또는 조건식 stringify)을 신호 종류로 분류.
   152	
   153	    모드 (환경변수 `PINE_ALERT_HEURISTIC_MODE`):
   154	    - strict (default): INFORMATION(break/trendline/session/pivot) > 방향 > UNKNOWN
   155	    - loose: 방향(long/short/bull/bear) > INFORMATION > UNKNOWN
   156	    """
   157	    if not text:
   158	        return SignalKind.UNKNOWN
   159	
   160	    stripped = text.strip()
   161	    # 1. JSON 파싱 시도 (모드 무관)
   162	    if stripped.startswith("{") and stripped.endswith("}"):
   163	        try:
   164	            data = json.loads(stripped)
   165	            action = str(data.get("action", "")).lower()
   166	            if action in ("buy", "long"):
   167	                return SignalKind.LONG_ENTRY
   168	            if action in ("sell", "short"):
   169	                return SignalKind.SHORT_ENTRY
   170	            if action == "close_long":
   171	                return SignalKind.LONG_EXIT
   172	            if action == "close_short":
   173	                return SignalKind.SHORT_EXIT
   174	        except (json.JSONDecodeError, AttributeError):
   175	            pass
   176	
   177	    # 2. 키워드 매칭 (모드별 rule set)
   178	    rules = _KEYWORD_RULES_LOOSE if _get_heuristic_mode() == "loose" else _KEYWORD_RULES
   179	    lower = stripped.lower()
   180	    for kind, patterns in rules:
   181	        for pat in patterns:
   182	            if re.search(pat, lower, re.IGNORECASE):
   183	                return kind
   184	
   185	    return SignalKind.UNKNOWN
   186	``
187
188 **Step 4 — 녹색 확인:**
189
190 `bash
   191	cd backend && uv run pytest tests/strategy/pine_v2/test_alert_hook.py -v
   192	`
193
194 Expected: PASS — 모든 loose/strict 테스트 + 기존 테스트 전수 녹색
195
196 ### T3. 회귀 방지 — i2_luxalgo E2E 재검증
197
198 **Step 5:**
199
200 `bash
   201	cd backend && PINE_ALERT_HEURISTIC_MODE=loose uv run pytest tests/strategy/pine_v2/test_e2e_i2_luxalgo.py -v
   202	`
203
204 Expected: PASS (기존 통과 유지)
205
206 **Step 6 — 전체 pine_v2 녹색:**
207
208 `bash
   209	cd backend && uv run pytest tests/strategy/pine_v2/ -v
   210	`
211
212 Expected: 전수 PASS.
213
214 ### T4. 회귀 확인 — 전체 backend
215
216 **Step 7:**
217
218 `bash
   219	cd backend && uv run pytest -q
   220	`
221
222 Expected: 922 passed (기존 baseline) + 신규 5 tests → 927+ passed.
223
224 ### T5. Worker-side codex review 1-pass
225
226 `bash
   227	codex exec --sandbox read-only "Review git diff vs main for PINE_ALERT_HEURISTIC_MODE loose/strict logic. Check: (1) strict default preserves all prior behavior, (2) loose never over-classifies pure INFORMATION, (3) env read is lazy so tests can monkeypatch, (4) no semantic drift in _KEYWORD_RULES_LOOSE vs _KEYWORD_RULES other than order."
   228	`
229
230 출력을 `docs/superpowers/reviews/2026-04-23-x1x3-w1-codex-self.md` 에 저장.
231
232 ### T6. Stage 브랜치 push
233
234 `bash
   235	git add backend/src/strategy/pine_v2/alert_hook.py backend/tests/strategy/pine_v2/test_alert_hook.py docs/superpowers/reviews/2026-04-23-x1x3-w1-codex-self.md
   236	git commit -m "feat(pine_v2): alert heuristic loose mode for i2_luxalgo (W1)"
   237	git push origin stage/x1-x3-indicator-ui
   238	`
239
240 ---

exec
/bin/zsh -lc "nl -ba backend/.env.example | sed -n '1,140p'" in /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41
succeeded in 0ms:
1 # QuantBridge — Backend `.env.example` (uvicorn / celery worker)
2 #
3 # === 로드 주체 ===
4 # 이 파일을 `cp .env.example .env.local`로 복사.
5 # pydantic-settings SettingsConfigDict(env*file=(".env.local", ".env")) 가 자동 로드.
6 # 대상 명령: `cd backend && uv run uvicorn ...` / `uv run celery ...` / `uv run pytest` / `uv run alembic ...`
7 #
8 # === 컨테이너 실행 시 ===
9 # `docker compose up` 시 이 파일은 사용되지 않음. `docker-compose.yml`의 `environment:`가
10 # 루트 `.env`의 값을 interpolate해서 컨테이너에 주입. 즉 root `.env`와 이 파일은 공통 키를 복사 유지.
11 #
12 # === 다른 서비스 env 위치 ===
13 # - Docker compose: ../.env (root)
14 # - Next.js dev: ../frontend/.env.local
15
16 # =====================================================
17 # 앱 설정
18 # =====================================================
19 APP_NAME=QuantBridge
20 APP_ENV=development # development | staging | production
21 DEBUG=true
22 SECRET_KEY=dev-secret-change-in-prod # [기본값 OK] 프로덕션만 실값 필요
23
24 # =====================================================
25 # Clerk 인증 (Sprint 3+)
26 # =====================================================
27 # 받는 곳: https://dashboard.clerk.com → API Keys → Secret keys
28 CLERK_SECRET_KEY=sk_test_PASTE_YOUR_SECRET_KEY_HERE # [필수 Sprint 3+]
29 CLERK_WEBHOOK_SECRET=whsec_placeholder_sprint7_real_value # [필수 Sprint 7 배포]
30 WEBHOOK_SECRET_GRACE_SECONDS=3600 # [기본값 OK] rotation grace 기간
31
32 # =====================================================
33 # Database (Sprint 3+)
34 # =====================================================
35 # docker-compose의 db 서비스가 localhost:5432에서 노출. 값은 root .env의 POSTGRES*\* 와 일치해야.
36 DATABASE_URL=postgresql+asyncpg://quantbridge:password@localhost:5432/quantbridge # [기본값 OK]
37
38 # =====================================================
39 # Redis / Celery (Sprint 4+)
40 # =====================================================
41 REDIS_URL=redis://localhost:6379/0 # [기본값 OK] 캐시
42 CELERY_BROKER_URL=redis://localhost:6379/1 # [기본값 OK]
43 CELERY_RESULT_BACKEND=redis://localhost:6379/2 # [기본값 OK]
44
45 # =====================================================
46 # Sprint 6+ Trading
47 # =====================================================
48 # Fernet 마스터 키 — 거래소 API Key AES-256 암호화.
49 # 생성: uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
50 # root .env의 TRADING_ENCRYPTION_KEYS와 동일 값 유지 (compose worker와 로컬 uvicorn이 같은 키여야 복호화 일관).
51 TRADING_ENCRYPTION_KEYS= # [필수 Sprint 6+]
52
53 # =====================================================
54 # Exchange (Sprint 5+)
55 # =====================================================
56 EXCHANGE_PROVIDER=fixture # fixture | bybit_demo | bybit_futures
57 BYBIT_FUTURES_MAX_LEVERAGE=20 # [기본값 OK] Sprint 7a leverage 상한
58 OHLCV_PROVIDER=timescale # fixture | timescale. timescale=CCXT live fetch + Hypertable 캐시. fixture 는 CI/oracle 전용.
59 OHLCV_FIXTURE_ROOT=backend/data/fixtures/ohlcv # [기본값 OK]
60 DEFAULT_EXCHANGE=bybit # [기본값 OK]
61
62 # =====================================================
63 # Kill Switch (Sprint 6+)
64 # =====================================================
65 KILL_SWITCH_CUMULATIVE_LOSS_PERCENT=10.0 # [기본값 OK]
66 KILL_SWITCH_DAILY_LOSS_USD=500.0 # [기본값 OK]
67 KILL_SWITCH_API_ERROR_STREAK=5 # [기본값 OK]
68 KILL_SWITCH_CAPITAL_BASE_USD=10000 # [기본값 OK] Sprint 6은 config, 7b부터 동적 바인딩
69
70 # =====================================================
71 # Backtest (Sprint 4+)
72 # =====================================================
73 BACKTEST_STALE_THRESHOLD_SECONDS=1800 # [기본값 OK]
74
75 # =====================================================
76 # CORS
77 # =====================================================
78 FRONTEND_URL=http://localhost:3000 # [기본값 OK]

exec
/bin/zsh -lc "nl -ba .env.example | sed -n '1,120p'" in /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41
succeeded in 0ms:
1 # QuantBridge — Root `.env.example` (docker compose 전용)
2 #
3 # === 로드 주체 ===
4 # 이 파일을 `cp .env.example .env`로 복사. docker compose는 `./env`를 자동 로드.
5 # `docker-compose.yml`의 `${VAR}` interpolation이 여기를 참조.
6 # backend/frontend 각자 loader는 별도 `.env.example` (해당 디렉토리) 사용.
7 #
8 # === 다른 서비스 env 위치 ===
9 # - Backend uvicorn/celery (로컬 실행): backend/.env.example → backend/.env.local
10 # - Frontend Next.js dev: frontend/.env.example → frontend/.env.local
11 #
12 # === 범례 ===
13 # [필수 Sprint N] : 해당 스프린트부터 실값 필요
14 # [기본값 OK] : 로컬 개발은 이 값 그대로
15
16 # =====================================================
17 # PostgreSQL (docker-compose `db` 서비스)
18 # =====================================================
19 POSTGRES_USER=quantbridge # [기본값 OK]
20 POSTGRES_PASSWORD=password # [기본값 OK] 로컬 전용
21 POSTGRES_DB=quantbridge # [기본값 OK]
22
23 # =====================================================
24 # Sprint 6+ Trading (docker-compose `backend-worker` interpolation)
25 # =====================================================
26 # Fernet 마스터 키 — 거래소 API Key AES-256 암호화용.
27 # 최초 1회만 생성, 변경 시 기존 암호화된 API Key 복호화 불가.
28 # 생성: cd backend && uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
29 # Rotation: 콤마 구분으로 여러 키 허용 (new_key,old_key). 첫 키 encrypt, 나머지 decrypt grace.
30 TRADING_ENCRYPTION_KEYS= # [필수 Sprint 6+]
31
32 # =====================================================
33 # Clerk 인증 (docker-compose `backend-worker` interpolation)
34 # =====================================================
35 # Compose로 워커를 띄울 때 backend/.env.local이 아닌 이 값을 사용.
36 # 로컬 uvicorn만 띄우면 backend/.env.local만 채워도 OK.
37 CLERK_SECRET_KEY=sk_test_PASTE_YOUR_SECRET_KEY_HERE # [필수 Sprint 3+]
38 CLERK_WEBHOOK_SECRET=whsec_placeholder_sprint7_real_value # [필수 Sprint 7 배포]
39
40 # =====================================================
41 # Exchange / Backtest (docker-compose `backend-worker` interpolation)
42 # =====================================================
43 EXCHANGE_PROVIDER=fixture # fixture | bybit_demo | bybit_futures
44 OHLCV_PROVIDER=timescale # fixture | timescale (Sprint 5 M3+). timescale=CCXT live fetch + Hypertable 캐시. fixture 는 CI/oracle 전용.
45 DEFAULT_EXCHANGE=bybit # [기본값 OK]
46 BACKTEST_STALE_THRESHOLD_SECONDS=1800 # [기본값 OK] worker stale 재클레임 threshold

codex
**Findings**

- `PINE_ALERT_HEURISTIC_MODE`를 코드에서 새로 읽지만 env 카탈로그에는 추가되지 않았습니다. 프로젝트 불변 규칙이 “`.env.example`에 없는 환경 변수를 코드에서 참조 금지”인데, 실제 참조는 [backend/src/strategy/pine_v2/alert_hook.py](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/src/strategy/pine_v2/alert_hook.py:151) 에 있고, 선언은 [backend/.env.example](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/.env.example:1), [.env.example](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/.env.example:1), [docs/05_env/env-vars.md](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/docs/05_env/env-vars.md:76) 어디에도 없습니다. 이건 구현 로직보다 운영/재현성 문제라 `GO_WITH_FIX`가 맞습니다.

1. AC는 부분 충족입니다. strict 기본 동작 보존은 [alert_hook.py:98-115](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/src/strategy/pine_v2/alert_hook.py:98) 의 기존 `_KEYWORD_RULES` 유지와 [alert_hook.py:151-153](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/src/strategy/pine_v2/alert_hook.py:151) 의 strict fallback으로 논리상 성립합니다. loose 신규 동작도 [alert_hook.py:119-136](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/src/strategy/pine_v2/alert_hook.py:119) 와 신규 테스트 [test_alert_hook.py:223-305](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/tests/strategy/pine_v2/test_alert_hook.py:223) 로 성립합니다. 다만 “11 new tests”는 사실상 12개이고, “backend total 936 passed”는 근거가 없습니다. self-review는 오히려 [934 passed, 1 skipped](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/docs/superpowers/reviews/2026-04-23-x1x3-w1-codex-self.md:37) 라고 적고 있어 수치가 맞지 않습니다. 이 환경에서는 `pytest` 재실행도 못 했습니다.
2. Spurious PASS는 아닙니다. 경계 테스트 `"Long break of trendline"`은 strict에서 `_KEYWORD_RULES`의 INFORMATION이 먼저 매칭됩니다: [alert_hook.py:98-115](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/src/strategy/pine_v2/alert_hook.py:98). loose에서는 `_KEYWORD_RULES_LOOSE`에서 LONG_ENTRY가 INFORMATION보다 앞서고 `\blong\b`가 먼저 걸립니다: [alert_hook.py:119-136](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/src/strategy/pine_v2/alert_hook.py:119). 이를 직접 검증하는 테스트가 [test_alert_hook.py:223-252](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/tests/strategy/pine_v2/test_alert_hook.py:223) 입니다.
3. TDD evidence는 부족합니다. 계획서는 분명 red-first를 요구합니다([plan:50-105](/Users/woosung/project/agy-project/quant-bridge/docs/superpowers/plans/2026-04-23-x1x3-w1-alert-heuristic-loose.md:50)), 하지만 diff와 self-review에는 실제 실패 로그나 red commit 증거가 없습니다. self-review는 사후 설명만 있습니다([self-review:19-23](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/docs/superpowers/reviews/2026-04-23-x1x3-w1-codex-self.md:19)).
4. strict mode 회귀는 코드상 보존됐습니다. `_KEYWORD_RULES` 내용 자체는 base branch와 byte-identical이고, diff는 새 `_KEYWORD_RULES_LOOSE`와 selector만 추가했습니다. 현재 strict 규칙은 [alert_hook.py:98-115](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/src/strategy/pine_v2/alert_hook.py:98) 에 그대로 있습니다.
5. 질문한 8개 edge case는 모두 테스트로 커버됩니다. uppercase env [test_alert_hook.py:265](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/tests/strategy/pine_v2/test_alert_hook.py:265), invalid [271](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/tests/strategy/pine_v2/test_alert_hook.py:271), empty string [277](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/tests/strategy/pine_v2/test_alert_hook.py:277), whitespace [283](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/tests/strategy/pine_v2/test_alert_hook.py:283), missing env [255](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/tests/strategy/pine_v2/test_alert_hook.py:255), empty message [289](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/tests/strategy/pine_v2/test_alert_hook.py:289), pure information [237](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/tests/strategy/pine_v2/test_alert_hook.py:237), bullish breakout [294](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/tests/strategy/pine_v2/test_alert_hook.py:294).
6. 제약 조건은 충족합니다. `classify_message()` 시그니처는 그대로 [alert_hook.py:156](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/src/strategy/pine_v2/alert_hook.py:156) 이고, `_get_heuristic_mode()`는 `os.environ.get(...)`를 helper 내부에서 수행하며 `classify_message()`가 매 호출마다 helper를 호출하므로 lazy read입니다([alert_hook.py:139-153](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/src/strategy/pine_v2/alert_hook.py:139), [184-185](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/src/strategy/pine_v2/alert_hook.py:184)).
7. Verdict는 `GO_WITH_FIX`, confidence `8/10`입니다. 로직 자체는 목표에 맞고 strict/loose 경계도 제대로 잡혔습니다. 다만 merge 전 `PINE_ALERT_HEURISTIC_MODE`를 `backend/.env.example`, 루트 `.env.example`, `docs/05_env/env-vars.md`에 추가해야 하고, 테스트 총합 수치 `936 passed` 주장은 현재 증거와 맞지 않으니 실제 실행 로그로 정정하는 편이 맞습니다.
   tokens used
   52,761
   **Findings**

- `PINE_ALERT_HEURISTIC_MODE`를 코드에서 새로 읽지만 env 카탈로그에는 추가되지 않았습니다. 프로젝트 불변 규칙이 “`.env.example`에 없는 환경 변수를 코드에서 참조 금지”인데, 실제 참조는 [backend/src/strategy/pine_v2/alert_hook.py](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/src/strategy/pine_v2/alert_hook.py:151) 에 있고, 선언은 [backend/.env.example](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/.env.example:1), [.env.example](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/.env.example:1), [docs/05_env/env-vars.md](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/docs/05_env/env-vars.md:76) 어디에도 없습니다. 이건 구현 로직보다 운영/재현성 문제라 `GO_WITH_FIX`가 맞습니다.

1. AC는 부분 충족입니다. strict 기본 동작 보존은 [alert_hook.py:98-115](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/src/strategy/pine_v2/alert_hook.py:98) 의 기존 `_KEYWORD_RULES` 유지와 [alert_hook.py:151-153](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/src/strategy/pine_v2/alert_hook.py:151) 의 strict fallback으로 논리상 성립합니다. loose 신규 동작도 [alert_hook.py:119-136](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/src/strategy/pine_v2/alert_hook.py:119) 와 신규 테스트 [test_alert_hook.py:223-305](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/tests/strategy/pine_v2/test_alert_hook.py:223) 로 성립합니다. 다만 “11 new tests”는 사실상 12개이고, “backend total 936 passed”는 근거가 없습니다. self-review는 오히려 [934 passed, 1 skipped](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/docs/superpowers/reviews/2026-04-23-x1x3-w1-codex-self.md:37) 라고 적고 있어 수치가 맞지 않습니다. 이 환경에서는 `pytest` 재실행도 못 했습니다.
2. Spurious PASS는 아닙니다. 경계 테스트 `"Long break of trendline"`은 strict에서 `_KEYWORD_RULES`의 INFORMATION이 먼저 매칭됩니다: [alert_hook.py:98-115](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/src/strategy/pine_v2/alert_hook.py:98). loose에서는 `_KEYWORD_RULES_LOOSE`에서 LONG_ENTRY가 INFORMATION보다 앞서고 `\blong\b`가 먼저 걸립니다: [alert_hook.py:119-136](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/src/strategy/pine_v2/alert_hook.py:119). 이를 직접 검증하는 테스트가 [test_alert_hook.py:223-252](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/tests/strategy/pine_v2/test_alert_hook.py:223) 입니다.
3. TDD evidence는 부족합니다. 계획서는 분명 red-first를 요구합니다([plan:50-105](/Users/woosung/project/agy-project/quant-bridge/docs/superpowers/plans/2026-04-23-x1x3-w1-alert-heuristic-loose.md:50)), 하지만 diff와 self-review에는 실제 실패 로그나 red commit 증거가 없습니다. self-review는 사후 설명만 있습니다([self-review:19-23](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/docs/superpowers/reviews/2026-04-23-x1x3-w1-codex-self.md:19)).
4. strict mode 회귀는 코드상 보존됐습니다. `_KEYWORD_RULES` 내용 자체는 base branch와 byte-identical이고, diff는 새 `_KEYWORD_RULES_LOOSE`와 selector만 추가했습니다. 현재 strict 규칙은 [alert_hook.py:98-115](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/src/strategy/pine_v2/alert_hook.py:98) 에 그대로 있습니다.
5. 질문한 8개 edge case는 모두 테스트로 커버됩니다. uppercase env [test_alert_hook.py:265](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/tests/strategy/pine_v2/test_alert_hook.py:265), invalid [271](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/tests/strategy/pine_v2/test_alert_hook.py:271), empty string [277](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/tests/strategy/pine_v2/test_alert_hook.py:277), whitespace [283](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/tests/strategy/pine_v2/test_alert_hook.py:283), missing env [255](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/tests/strategy/pine_v2/test_alert_hook.py:255), empty message [289](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/tests/strategy/pine_v2/test_alert_hook.py:289), pure information [237](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/tests/strategy/pine_v2/test_alert_hook.py:237), bullish breakout [294](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/tests/strategy/pine_v2/test_alert_hook.py:294).
6. 제약 조건은 충족합니다. `classify_message()` 시그니처는 그대로 [alert_hook.py:156](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/src/strategy/pine_v2/alert_hook.py:156) 이고, `_get_heuristic_mode()`는 `os.environ.get(...)`를 helper 내부에서 수행하며 `classify_message()`가 매 호출마다 helper를 호출하므로 lazy read입니다([alert_hook.py:139-153](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/src/strategy/pine_v2/alert_hook.py:139), [184-185](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3edae41/backend/src/strategy/pine_v2/alert_hook.py:184)).
7. Verdict는 `GO_WITH_FIX`, confidence `8/10`입니다. 로직 자체는 목표에 맞고 strict/loose 경계도 제대로 잡혔습니다. 다만 merge 전 `PINE_ALERT_HEURISTIC_MODE`를 `backend/.env.example`, 루트 `.env.example`, `docs/05_env/env-vars.md`에 추가해야 하고, 테스트 총합 수치 `936 passed` 주장은 현재 증거와 맞지 않으니 실제 실행 로그로 정정하는 편이 맞습니다.
