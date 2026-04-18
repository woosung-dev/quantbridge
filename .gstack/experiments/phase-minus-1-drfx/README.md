# Phase -1 실측 — Day 1-3 N-way 비교 매트릭스

> **상세 plan:** [`docs/superpowers/plans/2026-04-18-phase-minus-1-measurement-plan.md`](../../../docs/superpowers/plans/2026-04-18-phase-minus-1-measurement-plan.md)
> **브랜치:** `experiment/phase-minus-1-drfx`
> **시작:** 2026-04-18

---

## 한 줄 권고 (Day 3 종료 시 작성 예정)

_TBD — Day 3 판단 리포트에서 continue / ADR-011 amendment / abort 권고._

---

## Day 1 — 환경 + 파서 커버리지 + 주 오라클

### 1.1 환경 구축 ✅ 완료 (2026-04-18)

| 항목 | 상태 | 비고 |
|------|:--:|------|
| `uv init` + Python 3.12.12 | ✅ | `pyproject.toml` 생성 |
| `pynescript 0.3.0` | ✅ | PyPI (LGPL) |
| `pynecore` | ✅ | `pynesys-pynecore 6.4.3` (git+, Apache 2.0). import name `pynecore` |
| `ccxt 4.5.x` + `pandas 3.0.2` + `numpy 2.4.4` + `matplotlib 3.10.8` | ✅ | |

### 1.2 API 키 상태

| 키 | 상태 | Day 2 영향 |
|----|:--:|------|
| `ANTHROPIC_API_KEY` | unset | E4 Opus (기존 변환본 재사용) + E5 Sonnet (Claude Code 내부)은 무관 |
| `OPENAI_API_KEY` | unset | **E6 GPT-5 skip 예정 (사용자 결정 대기)** |
| `GOOGLE_API_KEY` / `GEMINI_API_KEY` | unset | **E7 Gemini 2.5 skip 예정 (사용자 결정 대기)** |

→ 사용자 결정: API 키 제공 / 웹 UI로 직접 변환 후 파일 제공 / E6·E7 skip 중 하나

### 1.3 고정 OHLCV ✅ 완료

| 항목 | 값 |
|------|-----|
| 심볼 / 거래소 | BTC/USDT 현물 / Binance (CCXT) |
| 타임프레임 | 1H |
| 범위 | 2025-04-18 00:00 UTC ~ 2026-04-17 23:00 UTC |
| 총 봉 | 8,760 |
| 파일 | `ohlcv/btc_usdt_1h_frozen.csv` |
| SHA256 | `76b75ce64fc03e3e6a4e36ff711e67f5b46505f7dee9c9ac0f31d5cf2b6bede2` |

### 1.4 Pine 스크립트 `corpus/` ✅ 확보 완료 (6종, 매트릭스 확장)

| # | Track | 난이도 | 파일 | 크기 |
|:-:|:---:|:---:|------|:---:|
| S1 | strategy | 🟢 쉬움 | `s1_pbr.pine` | 828B |
| S2 | strategy | 🟠 중간 | `s2_utbot.pine` | 2.7KB |
| S3 | strategy | 🔴 어려움 | `s3_rsid.pine` | 6.5KB |
| I1 | indicator | 🟢 쉬움 | `i1_utbot.pine` | 1.7KB |
| I2 | indicator | 🟠 중간 | `i2_luxalgo.pine` | 3.9KB |
| I3 | indicator | 🔴 어려움 | `i3_drfx.pine` | 38.9KB |

### 1.5 ~~E1 PyneCore 오라클~~ — **대안 필요 판정**

**발견:** PyneCore는 Pine 런타임이지만 Pine → Python 변환은 **PyneSys 상용 API(`$8-45/mo`) 의존**. 세션 결정(vendor lock-in 거부)과 충돌.

**대안 결정: B 트랙 단일 진행 (사용자 승인 2026-04-18)**
- **B 트랙:** LLM 4개(Opus/Sonnet/GPT-5/Gemini 3.1-pro) 수렴값을 quasi-oracle로 채택 (Day 2)
- ~~C 트랙 (trail_points probe)~~ **삭제** — `trail_points`/`qty_percent`/`pyramiding` 모두 H2+ scope로 이연 확정

### 1.6 E2 pynescript ✅ **6/6 파싱 성공**

| 파일 | 노드 종류 | 총 노드 |
|------|:---:|:---:|
| s1_pbr | 24 | 231 |
| s2_utbot | 27 | 734 |
| s3_rsid | 32 | 1,245 |
| i1_utbot | 25 | 587 |
| i2_luxalgo | 30 | 822 |
| i3_drfx | 40 | 10,289 |

→ `output/e2_pynescript_coverage.md` + `.json`. **Tier-0 포크 대상 결정 강하게 실증.**

### 1.7 E3 현재 QB 파서 ❌ **0/6 파싱 성공**

| 파일 | 실패 단계 |
|------|:---:|
| s1_pbr | stdlib (파싱은 성공, 미지원 함수) |
| s2_utbot | normalize |
| s3_rsid | lex |
| i1_utbot | normalize |
| i2_luxalgo | parse |
| i3_drfx | lex |

→ `output/e3_qb_parser_baseline.md` + `.json`. **ADR-004 현재 구현체로는 사용자 실 스크립트 전수 실패. Tier-0 pynescript 포크 결정 정당화.**

### 1.8 E4 Opus 4.7 변환본 재실행 ✅ (고정 CSV 기반 재현성 확보)

| 지표 | 값 |
|------|:---:|
| 총 수익률 | **-40.80%** (이전 세션 -41.26% 대비 ±0.5%p) |
| MDD | -44.06% |
| 샤프 | -4.41 |
| 프로핏 팩터 | 0.37 |
| 총 거래 | 145 (SL 108 / TP2 37, REVERSE 0) |
| 승률 | 25.52% |

→ `output/e4_opus_i3_drfx_1h.json` + `_trades.csv` + `_equity.csv`

---

## Day 2 — LLM 매트릭스 (B 트랙) 예정

- E5 Sonnet 4.6 (Claude Code 내부, 무료)
- E6 GPT-5 (OpenAI API)
- E7 Gemini 3.1-pro-preview (Google API)
- E7.5 Gemini 3.1-flash-lite-preview (Google API, 소형 스펙트럼)

각 모델 → I3 DrFX Pine → Python 변환 → 고정 CSV로 실행 → 8 지표 수렴도 분석 → quasi-oracle 도출

## Day 3 — S1/S2/S3/I1/I2 얕은 실행 + 판단 리포트 예정

- S1~I2 (4~5종) E1 PyneCore(가능 시) + E3 QB 파서만 — 파싱 성공 여부 위주
- TV 수동 스폿체크 1건 (I3 DrFX 최근 30일, Supertrend/ATR 2~3점)
- 가정 **2개** 판정 (A1 trail_points 제거, A2 KPI / A3 LLM 버그만)
- continue / ADR amend / abort 권고

---

## 디렉토리 구조

```
.gstack/experiments/phase-minus-1-drfx/
├── README.md                 # 본 파일
├── pyproject.toml            # uv
├── uv.lock
├── .python-version
├── corpus/                   # Pine 원본 (⏳ 사용자 제공 대기)
├── ohlcv/
│   ├── btc_usdt_1h_frozen.csv
│   └── btc_usdt_1h_frozen.sha256
├── scripts/
│   ├── fetch_ohlcv.py        ✅
│   ├── run_pynecore.py       (Day 1)
│   ├── parse_pynescript.py   (Day 1)
│   ├── parse_qb.py           (Day 1)
│   ├── llm_transpile.py      (Day 2)
│   └── compare_nway.py       (Day 3)
├── generated/                # LLM 변환본 (Day 2)
└── output/                   # 실행 결과 (Day 1-3)
```
