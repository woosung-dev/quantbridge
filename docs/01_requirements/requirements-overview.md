# QuantBridge — 요구사항 개요

> **목적:** PRD 핵심을 응축하고, 상세 REQ-### 카탈로그(`req-catalog.md`)의 진입점 역할.
> **SSOT:** 상세 비즈니스 규칙은 [`QUANTBRIDGE_PRD.md`](../../QUANTBRIDGE_PRD.md), 비전은 [`00_project/vision.md`](../00_project/vision.md).

---

## 1. 제품 프레이밍

QuantBridge는 **TradingView Trust Layer**다. TradingView 사용자가 작성/임포트한 Pine Script 전략을, 더 엄격한 백테스트와 스트레스 테스트로 검증한 뒤 데모/라이브 트레이딩까지 연결한다.

- 범용 퀀트 플랫폼 ❌
- TV 기존 사용자의 신뢰도 보강 도구 ✅
- `[/office-hours 2026-04-13]` 확정

## 2. 타겟 사용자 (Persona)

| 페르소나 | 특징 | Pain Point |
|----------|------|------------|
| **Primary — 파트타임 크립토 트레이더** | $1K~$50K 자본, Python 미경험, TradingView 유료 사용자 | TV 백테스터 신뢰 부족, 자동 실행 부재 |
| Secondary — 개인 퀀트 입문자 | Python 가능, 백테스팅 정식 도구 부족 | vectorbt 셋업 부담, 결과 시각화 부재 |
| Tertiary — Bybit/Binance 자동매매 사용자 | 거래소 API 직접 사용 경험 있음 | 전략 검증·리스크 관리 인프라 부재 |

## 3. 핵심 사용 시나리오 (MVP 핵심 화면)

> Import → Verify → Verdict 3단 흐름. 각 단계는 별도 화면으로 매핑.

### 시나리오 A: Import (전략 가져오기)
1. 사용자가 TradingView Pine Script 코드를 붙여넣기 (또는 라이브러리에서 선택)
2. 백엔드가 파싱 → 지원 함수 검증 → "Supported / Unsupported" 판정 즉시 반환
3. Supported 시 전략 저장 (`Strategy.status=DRAFT`)

### 시나리오 B: Verify (백테스트 + 스트레스 테스트)
1. 저장된 전략으로 백테스트 실행 (심볼/기간/캐피털/수수료 입력)
2. 결과 리포트: equity curve, win rate, Sharpe, max drawdown, trades 목록
3. (Sprint 6+) 스트레스 테스트: Monte Carlo 1000회, Walk-Forward 분석

### 시나리오 C: Verdict (데모 → 라이브)
1. 검증 통과 시 거래소 데모 환경에 1클릭 전환
2. (Sprint 7+) 데모 결과가 백테스트 기대치 ±X% 이내면 라이브 승급 가능
3. Kill Switch / 일일 최대 손실 한도 / 포지션 사이즈 가드

## 4. MVP 범위 (Phase 1~4)

PRD §구현 순서를 sprint 단위로 매핑.

| Phase | 기간 (계획) | 핵심 산출물 | 진행 상태 |
|-------|-------------|-------------|-----------|
| Phase 0 | 1주 | 스캐폴딩 (Next.js 16 + FastAPI + Docker + Clerk) | ✅ 2026-04-15 완료 |
| Phase 1 | 4주 | Pine 파서 + 백테스트 + 전략 CRUD + 백테스트 리포트 UI | 🔄 BE 완료, FE 진행 예정 |
| Phase 2 | 4주 | 스트레스 테스트 + 파라미터 최적화 | ⏳ Sprint 6+ |
| Phase 3 | 4주 | 데모 트레이딩 (Bybit/Binance), 리스크 관리 | ⏳ Sprint 7+ |
| Phase 4 | 4주 | 라이브 트레이딩, 멀티 거래소, 알림 | ⏳ Sprint 8+ |

진행 중 상세는 [`docs/TODO.md`](../TODO.md) §"Stage 3 / Sprint *" 참조.

## 5. KPI (Vision 인용)

| 지표 | 목표 | 측정 시점 |
|------|------|-----------|
| Pine Script 파싱 성공률 | 80%+ (상위 50개 전략) | Sprint 1+ 회귀 |
| 단일 심볼 1Y/1H 백테스트 | < 10초 | Sprint 2+ 회귀 |
| 데모 주문 체결 레이턴시 | < 2초 | Sprint 7+ |
| 백테스트 정확도 (vectorbt 직접 실행 대비) | 99%+ | Sprint 2+ snapshot |
| 임포트 → 첫 백테스트 결과 | < 5분 | UX 측정 (Sprint 5 FE 이후) |
| 백테스트 → 데모 트레이딩 전환 | 3클릭 이내 | Sprint 7+ |
| 데모 → 라이브 전환 | 2클릭 이내 (확인 포함) | Sprint 8+ |

## 6. 도메인 ↔ 요구사항 매핑

| 도메인 | 주요 REQ-### 카테고리 | 구현 sprint |
|--------|------------------------|-------------|
| Auth | REQ-AUTH-* (Clerk JWT, Webhook) | Sprint 3 ✅ |
| Strategy | REQ-STR-* (CRUD, Pine 파싱, 트랜스파일) | Sprint 1, 3 ✅ |
| Backtest | REQ-BT-* (제출, 진행, 취소, 결과 조회) | Sprint 2, 4 ✅ |
| Market Data | REQ-MD-* (OHLCV 수집, 캐싱) | Sprint 5 (예정) |
| Stress Test | REQ-ST-* (Monte Carlo, Walk-Forward) | Sprint 6+ (예정) |
| Optimizer | REQ-OPT-* (Grid, Bayesian) | Sprint 6+ (예정) |
| Trading | REQ-TRD-* (데모/라이브, Risk Mgmt, Kill Switch) | Sprint 7+ (예정) |
| Exchange | REQ-EX-* (계정 관리, API Key 암호화) | Sprint 7+ (예정) |

상세는 [`req-catalog.md`](./req-catalog.md) 참조.

## 7. 비범위 (MVP 제외)

PRD에서 명시되지 않았거나 의식적으로 제외한 항목:

- 멀티 사용자 협업 (전략 공유는 templates만, 실시간 공동 편집 없음)
- 모바일 네이티브 앱 (반응형 웹만)
- 옵션/선물 외 파생상품 (Spot + Perpetual Futures 한정)
- 알고리즘 마켓플레이스 (Phase 5+)
- 회계/세무 리포트 (외부 도구 연동 권장)

## 8. 핵심 비즈니스 규칙 (CLAUDE.md 인용)

> 도메인 특화 규칙 — 위반 시 데이터 정합성/보안 사고 직결. 변경은 ADR 필수.

- 금융 숫자는 `Decimal` 사용 (`float` 금지) — 가격, 수량, 수익률
- 백테스트/최적화는 반드시 **Celery 비동기** (API 핸들러 직접 실행 금지)
- 거래소 API Key는 **AES-256 암호화** 저장 (평문 금지)
- OHLCV 데이터는 **TimescaleDB hypertable** 저장 (Sprint 5 도입)
- 실시간 데이터는 **WebSocket + Zustand 캐시** (React Query와 분리)
- Pine Script → Python 변환 시 `exec()`/`eval()` **절대 금지** — 인터프리터 패턴 또는 RestrictedPython 필수
  ([ADR-003](../dev-log/003-pine-runtime-safety-and-parser-scope.md))
- Pine Script 미지원 함수 1개라도 포함 시 전체 "Unsupported" 반환 — 부분 실행 금지

## 9. 의사결정 트레일

- **Trust Layer 프레이밍** — `[/office-hours 2026-04-13]`
- **기술 스택** — [ADR-001](../dev-log/001-tech-stack.md)
- **병렬 스캐폴딩** — [ADR-002](../dev-log/002-parallel-scaffold-strategy.md)
- **Pine 런타임 안전성 + 파서 범위** — [ADR-003](../dev-log/003-pine-runtime-safety-and-parser-scope.md) `[/autoplan 2026-04-13]`
- **Pine 파서 접근법 선택** — [ADR-004](../dev-log/004-pine-parser-approach-selection.md)

## 10. 미해결 질문 (Open Questions)

`docs/TODO.md` §Questions에서 이관:

| ID | 질문 | 영향 도메인 | 상태 |
|----|------|-------------|------|
| Q-001 | DB 호스팅: Self-hosted vs Neon Serverless | Infrastructure | TimescaleDB 요구사항 → self-hosted 유리, 최종 결정 미정 (`07_infra/deployment-plan.md` 이관) |
| Q-002 | 배포 전략: Vercel+Cloud Run vs K8s | Infrastructure | MVP 단계 결정 미정 (`07_infra/deployment-plan.md` 이관) |
| Q-003 | Socket.IO vs 순수 FastAPI WebSocket | Realtime | Sprint 7+ 데모 트레이딩 시점 결정 |

---

## 변경 이력

- **2026-04-16** — 초안 작성 (Sprint 5 Stage A, PRD + vision.md 응축)
