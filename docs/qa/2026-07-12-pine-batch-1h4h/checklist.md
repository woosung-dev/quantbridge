# Pine 코퍼스 배치 백테스트 + 엔진 개선 — 체크리스트

> 플랜: `~/.claude/plans/users-woosung-project-agy-project-quant-iridescent-walrus.md`
> 브랜치: `stage/pine-batch-qa` (main @f087b5a 분기)

## Phase 0 — 베이스라인 락

- [x] `stage/pine-batch-qa` 브랜치 생성
- [x] `pytest tests/strategy/pine_v2` 그린 — **778 passed, 16 skipped (207.6s)**
- [x] 8종 coverage before 매트릭스 실측 (context-notes 기록)
- [x] QA 디렉토리 + checklist/context-notes 초기화

## Phase 1 — 데이터 확보

- [ ] `resample_fixture_4h.py` → `BTCUSDT_4h.csv` (2,190봉)
- [ ] 4h 검증: 봉수/첫 timestamp/OHLC 불변식/수동 집계 대조/Bybit 스팟체크
- [ ] `fetch_recent_ohlcv.py` → `BTCUSDT_1h_recent.csv` + `BTCUSDT_4h_recent.csv`
- [ ] recent 검증: 봉수/구간/단조 index

## Phase 2 — 배치 하니스 + 리포트 v1

- [ ] `batch_pine_backtest.py` (8 × {1h,4h} × {2024,recent})
- [ ] `results.json` + `report.md` T1~T5
- [ ] UtBot 1h 상반기 트레이드 수 ≈ 베이스라인 433 정합
- [ ] LuxAlgo 0-트레이드 시 원인 규명 노트

## Phase 3 — 엔진 개선 루프

- [ ] G1: for/while/break/continue 인터프리터 지원 (TDD, 반복 상한)
- [ ] G2: array.\* 서브셋 (PineArray + \_names SSOT + coverage)
- [ ] G3: bare `security` → `_DEGRADED_FUNCTIONS` 추가
- [ ] 매 수정 후 pine_v2 suite 그린 + 골든 베이스라인 바이트 동일
- [ ] 오라클 ①: UtBot 4h ATR 트레일링 스탑 수계산 대조
- [ ] 오라클 ②: bs 첫 EMA 크로스 + tpLevels 수계산 대조
- [ ] 하니스 재실행 → before/after 표
- [ ] BL 등재: ta.alma / ta.dmi / time() / ticker.new / security_lower_tf

## Phase 4 — UI 구동 + 디자인 리뷰

- [ ] 백엔드 `OHLCV_PROVIDER=fixture` 재기동
- [ ] Playwright MCP Clerk 로그인
- [ ] DrFX 전략 등록 → 1h 백테스트 COMPLETED → 리포트 렌더
- [ ] 4h 백테스트 (신규 픽스처 서빙 검증)
- [ ] UtBot degraded 422 카드 UX 확인
- [ ] 스크린샷 저장
- [ ] 디자인/AI-slop 리뷰 (DESIGN.md v3 기준) → 수정 or BL

## Phase 5 — 산출물 + PR

- [ ] report.md v2 (오라클 + before/after 포함)
- [ ] BL-405~ 등재
- [ ] PR-1 feat(qa): 데이터 + 하니스
- [ ] PR-2 feat(pine): 루프 지원
- [ ] PR-3 feat(pine): array + security fix
- [ ] PR-4 docs(qa): 리포트 + 디자인 findings
