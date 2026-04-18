# Phase -1 실측 — Day 1-3 N-way 비교 매트릭스

> **상세 plan:** [`docs/superpowers/plans/2026-04-18-phase-minus-1-measurement-plan.md`](../../../docs/superpowers/plans/2026-04-18-phase-minus-1-measurement-plan.md)
> **브랜치:** `experiment/phase-minus-1-drfx`
> **시작:** 2026-04-18

---

## 한 줄 권고 ✅ 확정 (Day 3, 2026-04-18)

> **CONTINUE to Sprint 8a (Tier-0 pynescript 포크 착수). ADR-011 본문은 유지. H1 MVP scope 확정(trail_points/qty_percent/pyramiding → H2+ 이연). Tier-5 LLM은 보조 전용 재확인 (원샷 변환은 프로덕션 불가).**

**상세:** [`output/phase-1-findings.md`](./output/phase-1-findings.md)
**매트릭스:** [`output/nway_diff_matrix.md`](./output/nway_diff_matrix.md) + `.csv`

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

### 1.8 E4 Opus 4.7 변환본 재실행 ✅ (1H + 4H 모두, 재현성 확보)

| TF | 총 수익률 | MDD | 샤프 | 프로핏 팩터 | 거래수 | 승률 | exit reasons |
|:--:|---------:|------:|------:|:---:|:----:|:----:|-----|
| **1H** | **-40.80%** | -44.06% | -4.41 | 0.37 | 145 | 25.52% | SL:108 / TP2:37 |
| **4H** | **-10.13%** | -13.84% | -0.89 | 0.71 | 37 | 32.43% | SL:25 / TP2:12 |

→ `output/e4_opus_i3_drfx_{1h,4h}.{json,_trades.csv,_equity.csv}`

이전 세션 값 (1H -41.26%, 4H -10.14%) 재현 성공. 고정 CSV 기반 결정론적 reproducibility 확보.

---

## Day 2 ✅ — LLM 매트릭스 (B 트랙) 완료

**I3 DrFX 심층 변환 + 1H/4H 실행:**

| 엔진 | 모델 | 1H 수익률 | 4H 수익률 | 상태 |
|:----:|------|--------:|--------:|:--:|
| E4 | Claude Opus 4.7 | -40.80% | -10.13% | ✅ |
| E5 | Claude Sonnet 4.6 | -52.21% | -20.51% | ✅ |
| E6 | GPT-5 | 0.00% (진입실패) | 0.00% (진입실패) | ⚠️ LLM 변환 구조 미흡 |
| E7a | Gemini 3.1-pro-preview | — | — | ❌ 429 quota (사용자 키 무료 tier) |
| E7b | Gemini 3.1-flash-lite | -0.10% (진입실패) | -0.10% (진입실패) | ⚠️ LLM 변환 구조 미흡 |

**핵심 발견:** 수익률 범위 **-52.21%p ~ 0%p** (1H) / **-20.51%p ~ 0%p** (4H). LLM 단독 원샷 변환은 수렴하지 않음 → quasi-oracle 불가. **A2 가정(<0.1% KPI) 반증.**

**타임프레임 부산물:** 작동 엔진 2개에서 4H가 1H 대비 30%p 이상 유리. 145 → 37 trades로 수수료 누적 감소 + 노이즈 감소가 주요 요인. 단 두 TF 모두 절대 수익 음수 — DrFX 전략의 TP 2:1 × 승률 32%는 구조적 적자 (세션 §5 확인 일치).

→ `output/nway_diff_matrix.{csv,md}` + `e{4,5,6,7b}-*_i3_drfx_{1h,4h}.json`

## Day 3 ✅ — 최종 판정 리포트 + N-way 매트릭스 완료

**Phase -1 가정 판정:**

| 가정 | 판정 | 근거 |
|------|:--:|------|
| ~~A1: trail_points 지원~~ | N/A | scope 축소 (H2+ 이연) |
| **A2:** <0.1% KPI 현실성 | ❌ **반증** | LLM 간 수익률 ~52%p 범위 |
| **A3:** LLM 변환 버그 재현성 | ✅ **실증** | 모델별 구조적 차이, 2개 엔진 0 trades |

→ 상세: [`output/phase-1-findings.md`](./output/phase-1-findings.md)

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
