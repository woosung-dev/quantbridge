<!-- functional-parity 스프린트 중 내려진 결정과 근거의 누적 기록 (append-only) -->

# functional-parity 컨텍스트 노트

## 2026-07-23 W0 — 스프린트 성립 결정

1. **범위 확정 (사용자)**: Tier A+B. Tier C(WS/포지션동기화/알림/펀딩) 전부 제외. 전략 상세 화면 신설 금지(프로토타입 부재) — 대시보드 링크 edit 재조준.
2. **실측 반전 — 기구현 5건**: 계획 후보였던 screen-06 필터+CSV / screen-07 진단 / screen-10 안정성(grid) / sprint55 e2e / BL-402 는 main @ 88faccd 에 이미 구현 완료(#464 부채 마감 슬라이스). `docs/c-language-port/checklist.md` §FIX 는 그 픽스 이전 기록이었음. → **문서만 보고 재구현 착수하면 안 되고, 계획 시 main 실측이 선행이어야 한다** (§7.1 baseline preflight 의 재확인).
3. **A2 전제 반전**: 이식 당시 "주문 취소 API unbacked" 미렌더 결정(`orders-blotter.tsx:4-5` 주석)은 **잘못된 전제** — BE `POST /orders/{id}/cancel` 은 CF4 로 완전 구현돼 있었음. 미렌더 결정의 근거 주석이 코드 현실과 어긋난 채 캐논처럼 작동한 사례.
4. **B1 집계 방식**: 저장 컬럼+migration 대신 read-time GROUP BY. 근거 = denorm drift 회피 / 목록 ≤20건 / BacktestRepository 가 이미 strategy service 에 cross-inject. 정의 = COMPLETED 기준 (FE `STRATEGY_BACKTEST_COUNT_HINT` 가 "완료된 백테스트 수"로 선제 등재돼 있어 문구-데이터 정합).
5. **B2 캐논 복원**: S9 의 "전체+툴팁" 은 state 필터 부재로 인한 잠정치로 재해석 — 소스 신설로 `_KIT.md` §4.6(미체결 수) 복원. `ORDER_FILTER_HINT.navCount` 문구 반전 필수(정직성 연쇄).
6. **A7 축소**: 이력 리스트 화면은 프로토타입 부재로 defer. 기능 격차의 본질 = 리로드 시 스트레스 결과 소실(`useState` 만) → `?backtest_id=&limit=1` 최신 복원(A7-lite)로 해소.
7. **워크트리 정리**: stale 13개 제거 + merged 브랜치 대량 정리. **wf_b2f8516a-320-1/2/3 은 미커밋 변경(pine_v2 na-safe 실험, BL-374/PR #373 계열 잔재) 있어 보류** — 사용자 판단 대기.
8. **평가자 = Claude**: 생성자가 codex 이므로 리뷰어를 Claude 로 교차 (c-port 는 반대 방향). codex read-only 는 최종 누적 diff 1회만.
