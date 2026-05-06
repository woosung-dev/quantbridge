# dogfood Day 7 — Sprint 36 종료 self-assess

**날짜:** 2026-05-06 (Sprint 36 PR #157 merged 직후)
**환경:** isolated docker (5433/6380) + `make dev-isolated` (3100/8100)
**점수:** **≤6/10 (gate (a) FAIL)**
**Day 추적:** Day 3=4 → Day 4=5 → Day 5=6~7 → Day 6=5 → Day 6.5 PASS → Day 7(Sprint 35)=6 → **Day 7(Sprint 36)=≤6**

---

## 1. Playwright 자동화 결과 (P-1 ~ P-6 + A ~ C)

### P 시나리오 (6/6 PASS)

| #   | 시나리오                     | 결과 | 비고                                     |
| --- | ---------------------------- | ---- | ---------------------------------------- |
| P-1 | Equity chart + BH curve 렌더 | ✅   | 파란 점선 BH 정상 (BL-178 fix 확인)      |
| P-2 | 성과 지표 표시               | ✅   | 18개 항목, 14개 실값                     |
| P-3 | Walk-Forward                 | ✅   | 20/38 folds · In/Out-of-sample 막대      |
| P-4 | Monte Carlo fan chart        | ✅   | Y축 0~140,000 USDT (BL-150 fix 확인)     |
| P-5 | 거래 목록                    | ✅   | 200/200건, 정렬·필터·CSV                 |
| P-6 | 가정 박스 5개                | ✅   | 초기자본·레버리지·수수료·슬리피지·펀딩비 |

### A~C 추가 시나리오

| #   | 시나리오              | 결과 | 비고                                                           |
| --- | --------------------- | ---- | -------------------------------------------------------------- |
| A   | 거래 분석 탭          | ✅   | 방향분포·방향별성과·승패비율·월별수익률·평균수익vs손실         |
| B   | MC 요약 통계          | ⚠️   | fan chart만 렌더, CI 95%/median/MDD p95 숫자 테이블 **미노출** |
| C   | equity chart 인터랙션 | ✅   | hover crosshair + Equity/BH 양 시리즈 동시 값 표시             |

---

## 2. Day 7 gate (a) FAIL 근거

**점수: ≤6/10** (이전 6/10이 후한 측정이었음)

1. **BL-183 발견** — MC fan chart 시각은 정상이지만 CI 95% 하한/상한·median_final_equity·MDD p95 숫자 테이블 미노출. BE `MonteCarloResult`에 계산값 있으나 FE에서 미렌더. "수치 기반 의사결정" 불가 = Surface Trust 갭.
2. **성과 지표 CAGR·Sortino·Calmar `—`** — 이 전략 특성상 null 정상이나 처음 보는 사용자가 "미구현?"으로 오인 가능.
3. **스트레스 테스트 결과 비영속** — 탭 이동 후 돌아오면 결과 초기화, 재실행 필요. 결과 캐싱 미구현.

---

## 3. PASS 확인 항목 (Sprint 35→36 개선 효과)

- BH curve null → 정상 렌더 (BL-178 root cause Docker worker stale 확정 + rebuild)
- MC fan chart 천조 → 0~140,000 USDT 정상 범위 (BL-150 sign-flip fix)
- equity chart crosshair Equity + BH 동시 값 표시
- 거래 분석 탭 5섹션 완전 렌더
- 거래 목록 200건 + 정렬/필터/CSV

---

## 4. 신규 등록 BL

| ID         | 내용                                                            | Priority | Est      |
| ---------- | --------------------------------------------------------------- | -------- | -------- |
| **BL-183** | MC 요약 통계 FE 미노출 (CI 95% 하한/상한·median·MDD p95 테이블) | P2       | S (1-2h) |

---

## 5. Sprint 37 방향

**gate (a) FAIL → Sprint 37 = polish iter 5 + Day 7 재측정**

우선순위 후보:

1. BL-183 (MC 요약 통계 FE) — Day 7 점수 직접 영향
2. 사용자 추가 피드백 기반 BL (다음 세션 office-hours 결정)
3. BL-181 (Docker worker auto-rebuild) — ops 안정성

---

## Cross-link

- Sprint 36 retro: 미작성 (Sprint 37 kickoff 시 작성 예정)
- BL-183: `docs/REFACTORING-BACKLOG.md` P2 테이블
- PR #157 (BL-150 + BL-176): merged `main` 2026-05-06
- dogfood Day 6.5: `docs/dev-log/2026-05-05-dogfood-day-6.5.md`
