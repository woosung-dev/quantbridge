# Phase -1 실측 계획 (Sprint 8a-pre, Day 1-3 N-way 비교 매트릭스)

> **일자:** 2026-04-18
> **관련 ADR:** [ADR-011 Pine Execution Strategy v4](../../dev-log/011-pine-execution-strategy-v4.md)
> **관련 아키텍처:** [`04_architecture/pine-execution-architecture.md`](../../04_architecture/pine-execution-architecture.md) §5 Phase -1
> **세션 아카이브:** [`docs/superpowers/specs/2026-04-17-pine-execution-v4-design.md`](../specs/2026-04-17-pine-execution-v4-design.md)
> **브랜치:** `experiment/phase-minus-1-drfx` (PR #17 머지 이후 `main` 기준)
> **작업 디렉토리:** `.gstack/experiments/phase-minus-1-drfx/` (격리)

---

## 1. Context — 왜 N-way 비교인가

초기 Phase -1 설계는 "LLM 변환 Python vs PyneCore vs TV 수동"의 **3-way**였다. 2026-04-18 세션 논의에서 두 가지 취약점 발견:

1. **LLM 모델 편향:** 기존 `/tmp/drfx_test/drfx_backtest.py`는 단일 모델(Claude Opus 추정)로 생성. 다른 모델(Sonnet / GPT-5 / Gemini)은 같은 버그(SL 기준점, float `==`, look-ahead)를 재현하지 않을 수 있어 "LLM 80~90%" 프레이밍 검증에 편향 존재.
2. **2-way diff 해석 모호성:** PyneCore ↔ LLM 변환본 diff가 크면 "PyneCore가 옳은가 LLM이 옳은가" 판별이 어려움. 3번째 이상의 기준점(QB 파서 baseline, 다른 LLM 모델들)이 있으면 수렴 방향 해석 가능.

**해결:** 세션 아카이브 §2(16 아키텍처) · §3(13 프로젝트) · §5(LLM 벤치마크)에 이미 정리된 자원을 Day 1-3 실측에 직접 투입하여 N-way 매트릭스 구성.

**부수 효과:** Phase -1 가정 3개 중 2개(PyneCore `trail_points` 지원 여부 / LLM 버그 3개의 영향)는 DrFX 심층 실측으로, 1개(상대 오차 <0.1% KPI 현실성)는 N-way 교차 검증으로 더 강하게 실증.

---

## 2. 실측 후보 (8 엔진 + 3 조건부)

### 2.1 주후보 (Day 1-3 범위 내 실행)

| # | 후보 | 라이선스 | 역할 | Day |
|:--:|------|:--:|------|:---:|
| **E1** | **PyneCore v6.4.2** | Apache 2.0 | **주 오라클** — Pine을 Python에서 결정론적으로 실행 | 1-3 |
| E2 | pynescript v0.3.0 | LGPL | 파서 커버리지 — AST 생성 성공률 측정 | 1 |
| **E3** | **현재 QB 파서** (`backend/src/strategy/pine`) | 내부 | **ADR-004 AST 인터프리터 baseline** — 파싱·실행 실패 지점 확인 | 1 |
| E4 | Claude Opus 4.7 변환본 | Anthropic | 기존 `/tmp/drfx_test/drfx_backtest.py` 재실행 (비용 0) | 1-2 |
| E5 | Claude Sonnet 4.6 변환본 | Anthropic | Claude Code 내부 생성 (비용 0) — 모델 크기 영향 | 2 |
| E6 | GPT-5 변환본 | OpenAI | API 키 존재 시 자동 시도, 부재 시 skip | 2 |
| E7 | Gemini 2.5 Pro 변환본 | Google | API 키 존재 시 자동 시도, 부재 시 skip | 2 |
| E8 | TV 수동 스폿체크 | - | ground truth (1구간, Supertrend/ATR 2-3점) | 3 |

### 2.2 조건부 후보

| # | 후보 | 리스크 | 처리 |
|:--:|------|------|------|
| C1 | PineTS (Node.js, QuantForge/LuxAlgo) | AGPL-3.0 SaaS 조항 — 코드 참조 금지. 로컬 실행 + 결과값 비교만은 통상 허용되나 라이선스 리스크 | **Day 1-3 제외**, Day 4+ 재평가 |
| C2 | PinePyConvert | 문서 부족, 실험적 | Day 4+ 파싱만 확인 |
| C3 | Pineify / PineGenius 상용 SaaS | 유료 계정 | Day 4+ 저우선 |

### 2.3 제외

| 후보 | 제외 사유 |
|------|----------|
| A5 LLVM JIT / A8 MLIR / A10 Futamura | 3주+ 구현 시간 — Day 1-3 불가 |
| A4 바이트코드 VM | 2~3개월 투자 — Phase -1 밖 |
| OpenPineScript | v2만 — 2026 실사용 불가 |
| pine-transpiler (Opus-Aether) | `strategy.*` 미지원 |
| pyine | 2026-02 archived |
| PineConnector / 3Commas | webhook only, 백테스트 아님 |
| QuantConnect LEAN | Pine 거부 공식화 |
| PyneSys SaaS $45/mo | 세션 결정: vendor lock-in 확정 거부 |

---

## 3. 스크립트 매트릭스 (5종)

**사용자 확정:** strategy 2 + indicator 3 = 5 스크립트. LuxAlgo Trendlines 실행 비교는 Day 4+로 이연.

| # | Track | 난이도 | 스크립트 | 비교 깊이 | Day |
|:--:|:---:|:---:|---------|:---:|:---:|
| **S1** | S | 🟢 쉬움 | RTB EMA crossover | 얕음(E1 + E3) | 3 |
| **S2** | S | 🟠 중간 | (사용자 제공) | 얕음(E1 + E3) | 3 |
| **I1** | A/M | 🟢 쉬움 | (사용자 제공) | 얕음(E1 + E3) | 3 |
| **I2** | A/M | 🟠 중간 | (사용자 제공) | 얕음(E1 + E3) | 3 |
| **I3** | A | 🔴 어려움 | DrFX Diamond Algo | **심층(E1~E7)** | 1-2 |

**비교 깊이 구분:**
- **심층:** E1~E7 (최대 7 엔진) × 8 지표 × bar-by-bar diff
- **얕음:** E1 PyneCore + E3 QB 파서 중심 (파싱 성공 여부가 주 관심사)

**8 지표:** 총수익률, MDD, 샤프, 프로핏팩터, 총거래수, 승률, SL/TP 분포, REVERSE 건수

---

## 4. Day별 체크리스트

### Day 1 — 환경 + I3 DrFX PyneCore + 파서 커버리지

- [ ] `.gstack/experiments/phase-minus-1-drfx/` 생성 + `uv init`
- [ ] `uv add pynecore pynescript ccxt pandas numpy matplotlib` (Apache 2.0 + LGPL 격리)
- [ ] OpenAI / Google API 키 환경변수 존재 확인 → `README.md` skip 사유 기록
- [ ] 사용자 제공 5개 `.pine` → `corpus/{s1,s2,i1,i2,i3}_*.pine` 저장
- [ ] **E1:** PyneCore로 **I3 DrFX** 실행 → `output/e1_pynecore_i3_drfx_1h.json`
- [ ] **E2:** pynescript로 5종 파싱 → AST 노드 카운트 → `output/e2_pynescript_coverage.md`
- [ ] **E3:** QB `parse_and_run` 5종 파싱 → 실패 지점 → `output/e3_qb_parser_baseline.md`
- [ ] **E4 재실행:** `/tmp/drfx_test/drfx_backtest.py` 를 **고정 OHLCV CSV** 입력으로 재실행
- [ ] BTCUSDT 1H 2025-04-18 ~ 2026-04-17 CCXT 수집 → `ohlcv/btc_usdt_1h_frozen.csv` (SHA256 README 기록)
- [ ] `README.md` Day 1 섹션 — E1~E4 상태표 + 파서 커버리지 요약

### Day 2 — LLM 매트릭스 (E5~E7) + trail_points probe

- [ ] **LLM 변환 생성 (I3 DrFX만 심층):**
  - E4: 기존 변환본 재사용
  - E5 Sonnet: Claude Code 내부 생성 → `generated/e5_sonnet_i3_drfx.py`
  - E6 GPT-5: `$OPENAI_API_KEY` 있으면 호출, 없으면 skip
  - E7 Gemini 2.5: `$GOOGLE_API_KEY` 또는 `$GEMINI_API_KEY` 있으면 호출, 없으면 skip
- [ ] 각 변환본을 고정 OHLCV CSV로 실행 → `output/e{N}_i3_drfx_1h.json`
- [ ] 8 지표 수치 비교표 (`output/i3_drfx_indicator_table.csv`)
- [ ] bar-by-bar entry/exit bar index Jaccard 계수 (E1 oracle 대비)
- [ ] LLM 버그 3개 재현성 체크 (SL 기준점 / float `==` / look-ahead) — 모델별 PASS/FAIL 표
- [ ] **trail_points / qty_percent probe:**
  - I3 DrFX AST `strategy.exit trail_points` 사용 여부 grep
  - 미사용 시 `corpus/probe_trail.pine` 합성 (3~5줄) → PyneCore 실행 → trailing stop 로그
  - `qty_percent` 분할 익절 probe 1건
- [ ] `README.md` Day 2 섹션

### Day 3 — 얕은 실행 + TV 스폿체크 + 판단

- [ ] **S1/S2/I1/I2 얕은 실행:** 각 스크립트에 대해 E1 PyneCore + E3 QB 파서. 실행 수치는 bonus
- [ ] N-way 매트릭스 CSV (`output/nway_diff_matrix.csv`):
  - 축1: 엔진 최대 7종 (E1/E3/E4/E5/E6/E7 + 파싱-only E2)
  - 축2: 스크립트 5종
  - 축3: 8 지표 + 파싱성공 bool
- [ ] 상대 오차 계산(I3 심층 기준): `|candidate - E1| / |E1|`
- [ ] **TV 수동 스폿체크 1건:** I3 DrFX 1H 최근 30일 1구간, Supertrend/ATR 값 2-3점
- [ ] 가정 3개 실증 결과표 → ✅/🟡/❌
- [ ] `README.md` 상단 **한 줄 권고**: continue / ADR-011 amend / abort
- [ ] 사용자 승인 후 Day 4+ 이행 (어려운 indicator 실행 비교 + TV 스크립트 15~20개 프로파일링)

---

## 5. 산출물 구조

```
.gstack/experiments/phase-minus-1-drfx/
├── README.md                          # Day별 기록 + 상단 판단 권고
├── pyproject.toml                     # uv
├── corpus/
│   ├── s1_rtb_ema_crossover.pine     # 사용자 제공
│   ├── s2_[name].pine                # 사용자 제공
│   ├── i1_[name].pine                # 사용자 제공
│   ├── i2_[name].pine                # 사용자 제공
│   ├── i3_drfx_diamond_algo.pine     # 사용자 제공
│   └── probe_trail.pine              # 합성 (Day 2, 필요 시)
├── ohlcv/
│   └── btc_usdt_1h_frozen.csv        # 고정 + SHA256
├── scripts/
│   ├── fetch_ohlcv.py                # CCXT → CSV
│   ├── run_pynecore.py               # E1
│   ├── parse_pynescript.py           # E2
│   ├── parse_qb.py                   # E3
│   ├── llm_transpile.py              # E5/E6/E7 — 모델별 API 래퍼
│   └── compare_nway.py               # 최종 매트릭스 계산기
├── generated/
│   ├── e4_opus_i3_drfx.py            # /tmp/drfx_test 복사본
│   ├── e5_sonnet_i3_drfx.py
│   ├── e6_gpt5_i3_drfx.py            # 조건부
│   └── e7_gemini_i3_drfx.py          # 조건부
└── output/
    ├── e1_pynecore_i3_drfx_1h.json
    ├── e2_pynescript_coverage.md
    ├── e3_qb_parser_baseline.md
    ├── e4_opus_i3_drfx_1h.json
    ├── e5_sonnet_i3_drfx_1h.json
    ├── e6_gpt5_i3_drfx_1h.json       # 조건부
    ├── e7_gemini_i3_drfx_1h.json     # 조건부
    ├── i3_drfx_indicator_table.csv   # Day 2 8-지표 비교
    ├── nway_diff_matrix.csv          # 최종 매트릭스
    ├── nway_diff_summary.md          # 인간-readable
    └── tv_spot_check_30d.md          # Day 3
```

### 5.1 재사용 자산

- `/tmp/drfx_test/drfx_backtest.py` — E4 variant (재현성 위해 고정 CSV 입력으로 1줄 수정)
- `docs/superpowers/specs/2026-04-17-pine-execution-v4-design.md` §2/§3/§5 — 후보 선정 근거
- `backend/src/strategy/pine/` — E3 baseline (읽기만, 변경 금지)

### 5.2 변경 금지 (Phase -1 기간)

- `backend/src/**`, `frontend/src/**`
- `docs/dev-log/011-*`, `docs/04_architecture/pine-execution-architecture.md` 본문 (Day 6-7 ADR amendment 단계까지 freeze)

---

## 6. 사용자 확정 사항 (2026-04-18 세션)

1. **PR #17 merge:** `--squash` 완료 (`d36793e`)
2. **스크립트:** strategy 2(쉬움 + 중간) + indicator 3(쉬움 + 중간 + 어려움=DrFX) = **5종**. LuxAlgo 제외
3. **LLM 모델:** Opus + Sonnet 무조건 포함. GPT-5 + Gemini 2.5는 **API 키 존재 시 자동 시도, 없거나 크레딧 부족 시 skip**
4. **PineTS:** Day 1-3 제외. Day 4+ 재평가
5. **TV 수동 스폿체크:** I3 DrFX 1H 최근 30일 1구간, Supertrend/ATR 2~3점
6. **브랜치 전략:** `experiment/phase-minus-1-drfx` 하나에서 **docs 커밋 먼저 → 실측 산출물 커밋 순차** → 최종 PR 1개

---

## 7. 가정 실증 결과표 (Day 3 채움)

| # | 가정 | 실증 방법 | 판정 |
|:--:|------|---------|:--:|
| A1 | PyneCore가 `strategy.exit trail_points/trail_offset` 지원 | Day 2 probe (DrFX 사용 여부 or 합성 `.pine`) | ✅/🟡/❌ |
| A2 | LLM 변환본 vs PyneCore 상대 오차 <0.1% MVP KPI 현실적 | Day 2 N-way 8-지표 + bar-by-bar Jaccard | ✅/🟡/❌ |
| A3 | LLM 변환 버그 3개(SL/float==/look-ahead)가 수익률에 실질 영향 | Day 2 모델별 재현성 + equity delta 분해 | ✅/🟡/❌ |

**판정별 후속:**
- ✅ 3개 전부 → Day 4+ 계속 (원안대로)
- 🟡 혼재 → ADR-011 amendment (KPI 완화 or trail_points 자체 구현 +2주 계획)
- ❌ 2개 이상 → Phase -1 abort + v4 아키텍처 재설계 세션 진입

---

## 8. Day 4+ 예고 (scope 밖)

- **Day 4-5:** TV 공개 스크립트 15~20개 alert 패턴 프로파일링 → Track S/A/M 실제 비율 확정
- **Day 6-7:** ADR-011 amendment 세션 (본 실측 결과 반영)
- **Day 8-10:** Tier-0 `pynescript` 포크 착수

**본 plan 종료 시점:** Day 3 판단 리포트 + 사용자 승인. Day 4+는 별도 plan 파일 또는 본 문서 amendment.

---

## 9. Amendment History

| 날짜 | 사유 | 변경 |
|------|------|------|
| 2026-04-18 | 최초 작성 | N-way 5 스크립트 × 7 엔진 × 8 지표로 확장 |
| (Day 3 완료 후) | 실측 반영 | 가정 3개 판정 + Day 4+ 계획 |
