# Pine 코퍼스 배치 백테스트 + 엔진 개선 루프 리포트 (2026-07-12)

> **범위**: `tmp_code/pine_code` 8종 × {1h, 4h} × {2024, 최근 1년} 일괄 검증·백테스트 → 엔진 갭 5종(G1~G5) 수정 → 오라클 수계산 검증 → Playwright 실 UI 구동 + 디자인 리뷰.
> **성과 표 원본**: [`tables.md`](tables.md) (T1~T5) · 원시 데이터: [`results.json`](results.json) · 과정 기록: [`context-notes.md`](context-notes.md)

---

## 1. 요약 (TL;DR)

| 항목              | Before                             | After                                                                 |
| ----------------- | ---------------------------------- | --------------------------------------------------------------------- |
| runnable 스크립트 | 6/8                                | **7/8** (bs 합류 — array+루프 지원)                                   |
| 인터프리터 루프   | **조용히 skip** (Trust Layer 구멍) | for/while/break/continue TV 시멘틱 구현                               |
| array.\*          | 전체 미지원                        | 최소 15종 지원 (잔여는 preflight 차단 유지)                           |
| pine_v2 테스트    | 778 passed                         | **815 passed / 0 failed** (골든 바이트 동일)                          |
| OHLCV 픽스처      | **합성 (OHLC 위반 ~77%)**          | 실 Bybit perp 4세트 (frozen parquet 대조 일치)                        |
| 오라클            | —                                  | UtBot 완전일치 PASS + bs 엔진 시멘틱 일치 (TV 편차 1건 발견 → BL-405) |

**최대 발견 2건.**

1. 기존 `BTCUSDT_1h.csv` 는 Sprint 4 합성 데이터 — 8,760봉 중 ~77%가 OHLC 불변식 위반. 이 데이터로는 전략 성과 측정이 무의미했다 (실데이터 교체 완료, PR #421).
2. 인터프리터가 for/while 루프를 **조용히 무시**하고 있었다 — coverage 도 못 잡는 이중 침묵 (G1 수정, PR #422).

---

## 2. 검증 매트릭스 (8종)

| 스크립트                  | Track | Before          | After            | 비고                                           |
| ------------------------- | ----- | --------------- | ---------------- | ---------------------------------------------- |
| DrFX_strategy_quantbridge | S     | ✅              | ✅               | coverage-clean. UI E2E 대표 주자               |
| LuxAlgo_indicator_medium  | A     | ✅ (0 트레이드) | ✅ (0 트레이드)  | 설계된 결과 — §4.1                             |
| PbR_strategy_easy         | S     | ✅              | ✅               | stop 주문 경로 검증                            |
| RsiD_strategy_hard        | S     | ✅              | ✅               | valuewhen/barssince/pivot                      |
| UtBot_indicator_easy      | A     | ✅ degraded     | ✅ degraded      | heikinashi·security·timeframe.period           |
| UtBot_strategy_medium     | S     | ✅ degraded     | ✅ degraded      | indicator 와 트레이드 완전 동일 (Track parity) |
| bs_indicator_medium       | A     | ❌ array 8종    | **✅ 실행 가능** | G1+G2+G4+G5 산물                               |
| DrFXGOD_indicator_hard    | A     | ❌              | ❌ (정직 종결)   | 잔여 5종 BL-406                                |

**성과 수치는 [`tables.md`](tables.md) T2~T5 참조.** 헤드라인만 요약하면 — 2024 국면(상승장)에서 4h 가 1h 보다 일관되게 우수(PbR 4h +343% vs 1h -1337%, RsiD 4h +244% vs 1h -412%), 최근 1년 국면(2025-07~2026-07)에서는 DrFX 4h(+25.9%)만 플러스. 전 스크립트가 국면·TF 민감도가 극심해 **그대로 라이브 투입 가능한 전략은 없음**이 정직한 결론.

### 성과 해석 주의 (3중 각주)

1. **사이징 왜곡**: qty 미선언 스크립트(PbR/UtBot)는 TV parity 기본 qty=1 BTC → 자본 10k 대비 4~10배 노출 → -2000%대 수치는 "청산 모델 없는 가상 손실". DrFX(percent_of_equity 100)만 실질 스케일.
2. **Sharpe/Sortino 는 bar-count 스케일** — TF 간 직접 비교 금지. CAGR 만 비교 가능.
3. bs 는 Track A 가상 트레이드 — TP/SL alert("🎯 Final TP" 등)는 방향 무관 텍스트라 미매핑, 플립 진입만 반영.

---

## 3. 엔진 개선 루프 (G1~G5) — PR #422

| 갭                                            | 발견 경로                          | 수정                                                                                                                     |
| --------------------------------------------- | ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| **G1** for/while silent skip                  | bs 실행 시도 → 플랜 단계 코드 정독 | TV 시멘틱 (inclusive 양끝·**방향 자동** `for i = 1 to 0` = 2회·`by` 는 양수 크기), cap 100k, ForIn 포함. 19 테스트       |
| **G2** array.\* 전체 미지원                   | bs/DrFXGOD coverage                | `_names.ARRAY_FUNCTIONS` 15종 SSOT + Python list 참조 시멘틱. 잔여(avg/sort/matrix/map)는 preflight 차단 유지. 18 테스트 |
| **G3** bare `security` degraded 누락          | coverage 정독                      | `_DEGRADED_FUNCTIONS` 1줄 + 테스트. UI 422 카드에 security 표시로 E2E 재확인                                             |
| **G4** `table.new(pos, cols, rows)` TypeError | bs 첫 실행 크래시                  | rendering NOP \*args 흡수                                                                                                |
| **G5** `label.style_*` coverage↔runtime drift | bs 두 번째 크래시                  | `_eval_attribute` prefix fallback                                                                                        |

- 회귀 검증: pine_v2 스위트 **815 passed / 0 failed** — trust-layer parity·골든 포함 (runnable 코퍼스에 루프/array 사용 0건 → 기존 결과 바이트 동일).
- 알려진 한계 (문서화): array 는 var 시리즈 히스토리에서 참조 공유(`arr[1]` 히스토리 미지원 — Pine 도 동일), 루프 반환값(loop-as-expression) 미지원 (기존 if-as-expression 한계와 동일 클래스).

## 4. 정직성 검증

### 4.1 LuxAlgo 0 트레이드 — 침묵 수용 금지 규명

upos/dnos 플립은 실존(4h 308/112 bars), alert 2종 수집도 정상. 원인 = 기본 `strict` alert 휴리스틱이 `\btrendline\b` → INFORMATION 을 방향 키워드보다 우선 매칭 (보수적 설계 의도, trust-layer 베이스라인도 strict 0 트레이드로 동결). `PINE_ALERT_HEURISTIC_MODE=loose` opt-in 시 `\bupward\b` → LONG_ENTRY 로 트레이드 생성 가능. **엔진 버그 아님** — 단 사용자에게 이 모드 존재가 UI 로 노출되지 않는 점은 개선 여지.

### 4.2 비순환 오라클 (§7.3 — 엔진 코드 미사용 순수 pandas 수계산)

| 오라클          | 방법                                                         | 결과                                                                                                                                                                                         |
| --------------- | ------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ① UtBot 4h 2024 | Wilder ATR(10) 시드=SMA + 트레일링 스탑 iff 체인 독립 재구현 | 첫 시그널 **bar 14 short @ 43736.2** — 엔진과 바/방향/가격 3항목 **완전 일치 PASS**                                                                                                          |
| ② bs 4h 2024    | ta.ema(SMA 시드) + EMA(5/13) 크로스 + 양봉 확인              | 엔진 시멘틱(nan→False) 수계산 **bar 12 long — 완전 일치**. 단 TV na-전파 시멘틱으로는 첫 시그널이 bar 15 short — ~~워밍업 경계 스퓨리어스 시그널 1건 발견 → BL-405~~ **(아래 erratum 참조)** |

> **⚠️ Erratum (2026-07-12, A+B+C Trust 번들):** 오라클 ②의 "TV na-전파 시멘틱 → bar 15" 는 **잘못된 전제**였다. TradingView 공식 문서 검증 결과 **Pine 의 bool 은 절대 na 가 아니며, 비교 연산은 na 피연산자에 concrete `false` 를 반환**한다(na 전파 아님 — na 전파는 산술만). 즉 엔진의 bar 12 동작이 TV 정답이고, 오라클이 가정한 "bool na 전파 → bar 15" 는 존재하지 않는 시멘틱이었다. **BL-405 는 not-a-bug 로 재분류(폐기)** 되었고, TV-정합 회귀 테스트(`tests/strategy/pine_v2/test_na_bool_tv_parity.py` 13건)로 잠갔다. bar12↔bar15 실측 편차가 (실제 TV 대비) 존재한다면 그 원인은 bool-na 가 아니라 **ta.ema 워밍업 시딩 → BL-409** 로 분리 추적한다. 상세: `docs/backlog.md` BL-405/BL-409.

### 4.3 데이터 신뢰

- 4세트 모두: 봉수 정확(8784/2196/8760/2190) + 갭 0 + OHLC 위반 0 + 1h→4h 리샘플 크로스체크 통과.
- 2024 1~6월 구간이 기존 trust-layer `corpus_ohlcv_frozen.parquet` 과 **전 컬럼 완전 일치** — 신뢰 소스 동일성 증명.

## 5. Playwright 실 UI 구동 (스크린샷: `screenshots/`)

| 단계                                                       | 결과                                                                   |
| ---------------------------------------------------------- | ---------------------------------------------------------------------- |
| Clerk 로그인 (dev instance)                                | ✅                                                                     |
| 전략 등록 위저드 (DrFX 붙여넣기 → 실시간 파싱 "변환 완료") | ✅ `01`, `02`                                                          |
| 1h 백테스트 2024 전체 → COMPLETED → 리포트 렌더            | ✅ `03` — **142 트레이드 = CLI 하니스와 동일**                         |
| 4h 백테스트 (신규 `BTCUSDT_4h.csv` FixtureProvider 서빙)   | ✅ `04` — 수수료 717.78/슬리피지 358.89 **CLI 와 정확 일치**           |
| UtBot 제출 → degraded 422 카드                             | ✅ `05` — heikinashi/**security(G3 검증)**/timeframe.period 3항목 표시 |
| 콘솔 에러                                                  | 0건 (의도된 422 네트워크 로그 제외)                                    |
| 라이트 테마                                                | ✅ `06` — 회귀 없음                                                    |

## 6. 디자인/AI-slop 리뷰

**총평: Precision Instrument 시스템 정상 유지 — AI-slop 판정 아님.** 다크 카본 디폴트 + 코퍼 액센트 + mono/tabular 수치 + TV 어트리뷰션 차트가 일관 적용. 이모지 카피/보라 그라디언트/균일 radius 류 슬롭 마커 미검출.

시각 검토 발견 (스크린샷 기반).

1. **[P2 실버그] 백테스트 폼 strategy Select 트리거에 raw UUID 노출** — 옵션 실클릭 후에도 이름 대신 `4d1451e8-…` 표시. BL-164(SelectWithDisplayName SSOT) 미적용 사이트 — **기존 BL-402(optimizer picker 동일 클래스)에 사이트 확장 등재**.
2. **[P3] 낙폭 차트 Y축 눈금 전부 "-0.1%" 동일 표기** — MDD -59.91% 인데 축 라벨이 단위/정밀도 문제로 뭉개짐. → BL-407
3. **[P3] 벤치마킹 미니차트 우하단 라벨("현재/최소")이 막대와 겹침** — 좁은 폭에서 클리핑 (BL-407 처리 시 동반 확인).

(소스 레벨 감사 발견은 아래 §6.1 에 병합.)

### 6.1 소스 레벨 감사 (스코프: strategies/new 위저드 + backtests/[id] 리포트 + backtests/new 폼)

**클린 판정 (위반 0)**: raw hex 0건(Monaco 웰 4건은 공인 예외) · Tailwind 팔레트 클래스 0건(시맨틱 유틸만) · `chipPop` 고아 키프레임 제거 확인 · 다크 디폴트 + 소비 CSS 변수 36종 양 테마 완비(미정의 0) · 이모지/Lorem/인디고 그라디언트/shadow 남용 0. 위저드 step-method 에는 "AI Slop #2 교정" 이력 주석까지 보존.

**발견 (심각도순)**.

| #   | 심각도 | 위치                                                                                                                                                                      | 내용                                                                                                                                                                                              |
| --- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | P1     | `backtests/_components/forms/backtest-form.tsx:84-106`                                                                                                                    | 전략 Select 가 raw `Select`+자식 없는 `SelectValue` → 트리거에 **UUID 노출** (런타임 관측과 원인 일치). `SelectWithDisplayName` 교체 — `equity-chart-with-compare.tsx:76` 선례. → **BL-402 확장** |
| 2   | P2     | `report/trade-ledger-table.tsx:98-125`, `trades/trade-filter-row.tsx:116-141,202-211`                                                                                     | 방향/결과 필터 Select 동일 클래스 (value≠label + bare SelectValue) → 선택 후 raw 토큰("all") 노출 추정 → BL-402 묶음                                                                              |
| 3   | P2     | `charts/chart-legend.tsx:51`, `charts/equity-pane.tsx:78`                                                                                                                 | aria-label "실선 녹색" stale — 실제 equity 색은 코퍼. 스크린리더에 틀린 색 전달 (W6 known leftover 잔존) → BL-408                                                                                 |
| 4   | P3     | key-stats-strip/performance-chart `rounded-xl` 2건, chart-legend 글래스 1건, MetricTile 레이블 어휘, 원장 mono/tabular 혼용, `--destructive-light` alias, 영문 aria-label | 폴리시 잔여물 팩 → BL-408                                                                                                                                                                         |

**종합 판정 (감사 에이전트 원문)**: "두 페이지는 Precision Instrument 시스템을 실질적으로 체화… AI-slop 판정은 **명백한 부정(슬롭 아님)**. 다만 신뢰를 직접 훼손하는 실버그 1건(전략 Select UUID)만큼은 '정직한 계측기' 컨셉과 정면 충돌 — 즉시 수정 필요."

## 7. BL 등재

- **BL-405** (P2, pine_v2): bool 시리즈 na→False 실체화 — indicator 워밍업 경계 스퓨리어스 시그널 (TV parity 편차, bs 오라클 실측).
- **BL-406** (P3, pine_v2): DrFXGOD 잔여 미지원 5종 — ta.alma/ta.dmi/time() 호출형(feasible) + ticker.new/request.security_lower_tf(멀티심볼·멀티TF 패러다임 밖).
- **BL-407** (P3, frontend): 낙폭 차트 Y축 눈금 포맷터 정밀도/단위 버그.
- **BL-408** (P3, frontend): 디자인 폴리시 잔여물 팩 — stale aria-label 색명(코퍼인데 "녹색")·radius·글래스·레이블 어휘 6건.
- **BL-402 확장** (기존 P2, frontend): strategy picker UUID 실측+원인 확정 + 원장/필터 Select 2파일 — 3사이트 추가.

## 8. PR 구성

| PR                | 내용                                                         | 상태                              |
| ----------------- | ------------------------------------------------------------ | --------------------------------- |
| #421 `feat(qa)`   | 실데이터 4세트 + fetch/배치 스크립트 + QA 문서 (엔진 diff 0) | Open — base `stage/pine-batch-qa` |
| #422 `feat(pine)` | G1~G5 엔진 확장 + 테스트 41건 (815 그린 증빙)                | Open — base #421 (순차 머지)      |
| #423 `docs(qa)`   | 본 리포트 v2 + BL 등재 + 스크린샷 + 디자인 findings          | 본 커밋                           |

stage→main 은 사용자 수동 머지 (Option C 관례).

## 9. 한계와 다음 단계 제안

- **청산/증거금 모델 부재** — qty 미선언 전략의 -2000%대 수치가 그대로 노출. TV 는 마진콜 시뮬. 장기적으로 sizing 정규화 리런 옵션(`--normalized`) 또는 리포트 경고 강화 고려.
- bs 의 TP/SL alert 미매핑 (방향 무관 exit) — Track A SignalKind 에 direction-agnostic EXIT 매핑 추가 검토 여지.
- DrFXGOD 지원은 ta.alma/ta.dmi 구현 시 재평가 (BL-406).
- `_PINE_V6_COLLECTION_NAMESPACES` 는 실사용 없는 문서용 중복 상수 (실 동작 = `_KNOWN_NAMESPACES`) — 선재 사항, 미삭제 기록만.
