# Dogfood 일일/주간 체크리스트 (Path β 특화)

> **역할 구분:**
>
> - 환경 셋업 + 리스크 대응은 [`07_infra/h1-testnet-dogfood-guide.md`](../07_infra/h1-testnet-dogfood-guide.md) 이 SSOT.
> - 본 문서는 **Path β (Tier-2 Trust Layer CI 병행 dogfood)** 의 일일/주간 **관찰·기록 시트**.
> - 중복은 최소화 — 여기선 **Path β 특화 지표** (backtest predicted vs live realized 편차, Coverage Analyzer 실사용 감지) 만 추적.

> **전제 조건 (하기 전 확인):**
>
> 1. `07_infra/h1-testnet-dogfood-guide.md` §2 (환경 준비) 완료 — Demo Trading API 키 발급 포함
> 2. `scripts/bybit_demo_smoke.py` PASS 확인
> 3. Path β Stage 0 문서 완료 (ADR-013, trust-layer-architecture.md, trust-layer-requirements.md)

---

## 1. 시작 전 1회 체크

- [ ] 관찰 대상 corpus 확정 (s1_pbr + s2_utbot 기본, i2_luxalgo loose 는 OKX demo 셋업 시 추가)
- [ ] 각 전략의 **예상 metric baseline** 기록 (백테스트 recent run 의 sharpe / win_rate / max_dd)
- [ ] Kill Switch 설정 재확인 (`.env.demo` 기준값)
- [ ] `docs/dev-log/dogfood-week1-path-beta.md` 주간 리포트 파일 생성 (빈 스켈레톤)

---

## 2. 일일 체크리스트 (15분 이내)

> **시점**: 매일 저녁 1회. 오전 체크는 `07_infra/h1-testnet-dogfood-guide.md` §3 오전 체크로 갈음.

### 2.1 Kill Switch 관측

```sql
SELECT trigger_type, triggered_at, strategy_id, metadata
FROM trading.kill_switch_events
WHERE created_at::date = CURRENT_DATE;
```

| 지표                                |  측정값  |     목표     |
| ----------------------------------- | :------: | :----------: |
| 당일 Kill Switch 발동               | \_\_\_건 |   0 (D-A)    |
| False positive (정상 상황인데 발동) | \_\_\_건 |      0       |
| 의도된 발동 (실제 손실 한도 도달)   | \_\_\_건 | N/A (기록만) |

### 2.2 체결 성공률

```sql
SELECT status, COUNT(*) cnt
FROM trading.orders
WHERE created_at::date = CURRENT_DATE
GROUP BY status;
```

| 지표                                           | 측정값  |    목표     |
| ---------------------------------------------- | :-----: | :---------: |
| 당일 주문 총 수                                | \_\_\_  |     N/A     |
| filled                                         | \_\_\_  | ≥ 95% (D-B) |
| rejected + error                               | \_\_\_  |      0      |
| 체결 성공률 = filled / (filled+rejected+error) | \_\_\_% |    ≥ 95%    |

### 2.3 Predicted vs Realized 편차 (Path β 핵심)

**핵심 Path β 관찰**: 백테스트가 예측한 metric 과 실거래 결과의 편차. Trust Layer CI 가 잡는 것은 "QB 내부 consistency" 이지만, **QB vs 실시장** 의 편차는 CI 로 잡을 수 없다 — dogfood 로만 확인 가능.

**일일 기록 (단순 비교)**:

| Corpus                    | 오늘 trade 수 | 오늘 realized PnL | 최근 backtest 일평균 PnL 예상 | 편차 (%) |
| ------------------------- | :-----------: | :---------------: | :---------------------------: | :------: |
| s1_pbr                    |    \_\_\_     |    \_\_\_ USDT    |          \_\_\_ USDT          | \_\_\_%  |
| s2_utbot                  |    \_\_\_     |    \_\_\_ USDT    |          \_\_\_ USDT          | \_\_\_%  |
| (i2_luxalgo, OKX 적용 후) |    \_\_\_     |    \_\_\_ USDT    |          \_\_\_ USDT          | \_\_\_%  |

**단일 일자는 소수 샘플이므로 절대 편차가 크더라도 즉시 액션 하지 않음**. 주간 집계로 판단.

### 2.4 UX 마찰 메모 (자유 서술)

> 오늘 Dogfood 도중 "불편했던" 것 1~3건 메모. Trust Layer CI 외의 개선 후보.

- [ ] 메모 1: **\*\***\_\_\_\_**\*\***
- [ ] 메모 2: **\*\***\_\_\_\_**\*\***
- [ ] 메모 3: **\*\***\_\_\_\_**\*\***

→ 주간 집계 시 Sprint Y2 candidate 판정 후보.

### 2.5 Coverage Analyzer 사용 감지

**체크**: 오늘 새 strategy 등록 또는 parse_preview 요청 시 `coverage.unsupported_builtins` 가 반환된 적이 있는가?

- [ ] 있음 → 해당 함수명 기록 → P-2 SSOT 반영 필요 여부 판단
- [ ] 없음

### 2.6 일일 기록 저장

`docs/dev-log/dogfood-week1-path-beta.md` 의 "Day N" 섹션에 위 테이블을 append.

---

## 3. 주간 요약 (30분, 매 일요일)

### 3.1 집계 대상

- **Kill Switch**: 총 발동 건수 / false positive 건수 → **D-A 판정**
- **체결 성공률**: 주간 평균 → **D-B 판정**
- **Predicted vs Realized**: Sharpe ratio (주간 realized vs backtest 예측) → **D-C 판정**
- **UX 마찰**: 누적 메모 3~5건 → 상위 3건만 **D-D ticket 화**
- **Coverage SSOT drift**: 주간에 발견된 unsupported 함수명 → 주간 PR 으로 SSOT 업데이트 예정 여부

### 3.2 주간 리포트 템플릿

```markdown
# Dogfood Path β Week N Summary

## D-A Kill Switch 오작동

- 발동 건수: X (목표 0)
- False positive: Y (목표 0)
- 판정: ✅ / ❌ / ⚠️

## D-B 체결 성공률

- 주간 평균: X%
- 목표 95% 달성: YES/NO

## D-C Predicted vs Realized Sharpe 편차

- s1_pbr: backtest Sharpe X, live Sharpe Y, 편차 Z%
- s2_utbot: ...
- 판정: ✅ (<5%) / ⚠️ (5~10%) / ❌ (>10%)

## D-D UX 마찰

- 발견 Ticket 후보 (상위 3):
  1. ...
  2. ...
  3. ...

## Coverage SSOT Drift

- 발견된 unsupported: [...]
- 차주 계획: P-2 test 강화 or stdlib 추가 or 유지

## 다음 주 액션

- [ ] ...
- [ ] ...
```

### 3.3 Path β 진행 결정

> **Sample size 주의 (opus Gate-0 W3 반영):** D-C 의 **Sharpe 편차는 통계적으로 noisy**. s1_pbr 기준 일 1~3 신호 → 주 7~21 trade 로 variance 가 매우 크다. 아래 매트릭스는 **3주차부터 판정 유효**. 1~2주차는 **관찰 전용**이며 이상 징후만 기록.

| 주차 말 상태                | 조치                                                               | 판정 유효 시점 |
| --------------------------- | ------------------------------------------------------------------ | :------------: |
| D-A ❌ (Kill Switch 오작동) | **즉시** dogfood 중단 → bug ticket 최우선 (sample size 무관)       |   1주차부터    |
| D-B < 95% 지속              | CCXT 에러 pattern 분석 → Sprint 7d 이후 어댑터 개선                |   2주차부터    |
| D-C > 10% (Sharpe 편차)     | backtest engine 검토 → 잠재적 stdlib regression 확인 (P-3 로 curb) | **3주차부터**  |
| D-D > 3건 누적              | Sprint Y2 candidate 로 등록, Path β 는 그대로 진행                 |   1주차부터    |
| D-A/B/C/D 모두 ✅           | Stage 2 완료 여부 확인 → Path β 완료 선언                          |   3주차부터    |

**대안 지표 (small sample robust, 참고용)**: Sharpe 대신 **누적 PnL / max DD (Calmar proxy)** 가 작은 sample 에선 더 robust. 3주차에도 variance 가 크면 Calmar 로 전환 검토 (Stage 1 opus W3 오픈 이슈).

---

## 4. 본 체크리스트 외 참고

| 상황                       | 참고 문서                                                               |
| -------------------------- | ----------------------------------------------------------------------- |
| Bybit/OKX demo 환경 재셋업 | `07_infra/h1-testnet-dogfood-guide.md` §2                               |
| Kill Switch 발동 시 대응   | `07_infra/h1-testnet-dogfood-guide.md` §5                               |
| CI 가 잡는 regression 기준 | `04_architecture/trust-layer-architecture.md` §3                        |
| SLO 상세                   | `01_requirements/trust-layer-requirements.md` §3                        |
| 주간 리포트 파일 위치      | `docs/dev-log/dogfood-week1-path-beta.md`, `dogfood-week2-path-beta.md` |

---

## 5. 변경 이력

| 날짜       | 사유                | 변경                                                                 |
| ---------- | ------------------- | -------------------------------------------------------------------- |
| 2026-04-23 | 최초 작성           | Path β Stage 0. `07_infra/h1-testnet-dogfood-guide.md` 와 역할 분리  |
| 2026-04-24 | Testnet → Demo 전환 | OKX/Bybit testnet → demo 참조 업데이트, `.env.testnet` → `.env.demo` |
