# ADR-015: Sprint 7d 회고 — OKX Adapter + Trading Sessions + Passphrase 암호화

> **상태:** 회고 (사후 기록, 2026-04-23 작성)
> **일자:** 2026-04-19 (PR #28 merge)
> **브랜치:** `feat/sprint7d-okx-sessions`
> **관련 ADR:** [ADR-007 Sprint 7a Bybit Futures](./007-sprint7a-futures-decisions.md), [ADR-008 Sprint 7c scope](./008-sprint7c-scope-decision.md)

---

## 1. 배경

Sprint 7a (ADR-007, PR #10) 에서 Bybit Futures + Cross Margin 이 완성됐다. H1 Stealth 의 "본인 dogfood" 범위에서는 Bybit 단독으로 충분하지만, **dogfood 전략의 운영 시간대를 명시적으로 지정** 하는 Trading Sessions 기능과 **OKX 어댑터** 가 함께 이연돼 있었다.

- OKX 필요성: Bybit testnet 만으론 거래소 어댑터 추상화의 **실제 다형성** 을 검증 못 함. 한 거래소만 쓰면 "CCXT 어댑터 = Bybit" 로 고정 관념 생김
- Trading Sessions 필요성: dogfood 중 "밤사이 Kill Switch 발동" 이 dogfood UX 마찰의 큰 원인 → 세션 시간대를 전략별로 제한

---

## 2. 결정 요약

### 2.1 OKX 어댑터

- **CCXT 기반 이식**: 기존 Bybit 어댑터와 인터페이스 통일 (`ExchangeAdapter` Protocol)
- **OKX 고유: passphrase** — Bybit 은 API Key + Secret 2종이지만 OKX 는 **Key + Secret + Passphrase 3종**. Passphrase 도 AES-256 암호화 저장 (기존 TRADING_ENCRYPTION_KEYS 재사용)
- **FE**: `/trading` 의 `RegisterExchangeAccountDialog` 에 `provider=okx` 선택 시 passphrase 입력 필드 조건부 노출

### 2.2 Trading Sessions

- **Sessions 스키마**: `trading_sessions` 테이블 — `strategy_id`, `timezone`, `session_chips[]` (예: `[{"day": "mon-fri", "start": "09:00", "end": "22:00"}]`)
- **체결 시점 검증**: 주문 제출 전 "현재 시각이 세션 내인가" 확인 → 아니면 `session_closed` reject
- **UI**: Strategy Edit 페이지의 `TabTrading` 에 `SessionChips` 컴포넌트 (Sprint FE-04 후속)

### 2.3 자율 병렬 실행

- **cmux 3 워커 + Option C (Stage Branch)**: 워커 A (OKX adapter), B (Sessions BE), C (FE passphrase+chips)
- **Signal 기반 IPC**: 각 워커가 `/signal/complete` 파일로 완료 통지, orchestrator 가 stage/fe-polish 로 squash merge
- **실측**: 32 분 (사용자 개입 0회, iter=1 모두 PASS)

---

## 3. 테스트 & 결과

| 항목                        | Sprint 7a 말 |            Sprint 7d 말 (PR #28)             |
| --------------------------- | :----------: | :------------------------------------------: |
| backend tests               |     524      |                823 (+45 추정)                |
| Exchange adapter 다형성     |  Bybit 단독  |              Bybit + OKX 2원화               |
| Kill Switch + Sessions 조합 |     N/A      | 세션 외 주문 시 `session_closed` 선행 reject |

---

## 4. 학습

### L-1: 자율 병렬 Option C (Stage Branch) 의 실용성

- main 직접 touch 없이 `stage/<theme>` 경유 + 사용자 수동 main merge
- deny 조작 불필요, worker 충돌 제로
- 실측 32m 은 "18h → 33x 단축" 근거 데이터로 누적 (Sprint FE B/C/D 로 일반화)

### L-2: Passphrase 도 AES-256 로 — 기존 키 관리 인프라 재사용

- OKX passphrase 를 별도 table 또는 별도 키로 다루려는 유혹을 피하고, 기존 `TRADING_ENCRYPTION_KEYS` 를 passphrase 필드에 동일 적용
- 이유: 키 rotation 정책이 분산되면 감사·사고 대응이 어려워짐
- 향후 OKX 외 passphrase 필요 거래소 (예: Coinbase Pro 과거) 에도 동일 규약 재사용

### L-3: Trading Sessions 는 dogfood UX 마찰의 큰 축

- Kill Switch 가 밤사이 발동하는 빈도가 일일 1~2건 (수면 중 이상 체결) → session chip 으로 야간 금지 가능
- 반대로 낮 시간에만 거래하면 Bybit funding rate 차이 놓치는 tradeoff 도 존재 → 전략별 커스터마이즈 필요 (기본값은 비어있음 = 24/7)

### L-4: Exchange adapter 다형성은 `ExchangeAdapter` Protocol 에서 자연스럽게

- Bybit-only 시절 `BybitAdapter` 구체 타입이 곳곳에 흩어져 있었음 — 7a 리팩토링 미진행
- 7d 에서 **OKX 추가** 를 기회로 `src/exchange/protocol.py` 의 `ExchangeAdapter` Protocol 정립
- 이후 새 거래소 추가 시 Protocol 구현만 하면 service layer 수정 최소화

---

## 5. 오픈 이슈 (Sprint 7d 이후 이연)

- **OKX demo vs testnet 분기**: OKX 는 demo 와 testnet API endpoint 가 다름. 현재는 demo 기준만 검증. Testnet full smoke 는 Path β Dogfood 에서 수행
- **Session 시간대 드리프트**: 서버 tz 가 UTC 이므로 KST session 지정 시 타임존 변환 명확해야 함. 현재 구현은 `zoneinfo` 로 처리했으나 DST 전환 경계에서 edge case 존재 가능 → dogfood 중 관찰 후보
- **Funding rate 수집**: PR-C (CCXT 확장) 에 포함 예정이었으나 Sprint 7d 에서 범위 축소 — Path γ/δ 대상

---

## 6. 영향

### 코드

- `backend/src/exchange/okx_adapter.py` 신규
- `backend/src/exchange/protocol.py` 정립 (Protocol 추출)
- `backend/src/trading/sessions/` 신규 (모델 + validator)
- FE: `TabTrading`, `SessionChips`, `RegisterExchangeAccountDialog.okxFields`

### 운영

- `.env.example` 에 OKX passphrase 관련 환경 변수 섹션 추가
- `docker-compose.yml` 은 변경 없음 (서비스 동일)

---

## 7. 다음 단계

- [x] Path β Dogfood 에서 OKX testnet 추가 (플랜 §6.1)
- [ ] Session 시간대 DST edge case 관찰 (dogfood 주간 요약)
- [ ] Funding rate 수집 (Path γ 이후)
- [ ] 3rd 거래소 고려 — Binance / Coinbase 는 H2 Build-in-Public 진입 시 재평가

---

## 8. 변경 이력

| 날짜       | 사유                  | 변경                                                   |
| ---------- | --------------------- | ------------------------------------------------------ |
| 2026-04-23 | 최초 작성 (사후 회고) | Path β Stage 0 Wave B. Sprint 7d 결정 근거와 학습 정리 |
