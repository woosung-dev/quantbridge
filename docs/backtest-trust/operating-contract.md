<!-- backtest-trust 스프린트 운영 계약 — 워커 간 와이어 계약(S0 동결) + 환경/게이트 규약 -->

# backtest-trust — 운영 계약

> 플랜 SSOT = `~/.claude/plans/backtest-trust-joyful-wirth.md`. 본 문서는 **워커가 지켜야 할 계약**만 담는다.
> S0 = 아래 §1 와이어 계약 동결. W1(be) / W2(fe) 는 이 표만 보고 병렬 진행한다 (파일 교집합 0).

---

## §1. 와이어 계약 (S0 — 동결)

### 1.1 `sharpe_convention` (신규, metrics JSONB · 마이그레이션 0)

| 값                  | 조건                                            | FE 표시                                                             |
| ------------------- | ----------------------------------------------- | ------------------------------------------------------------------- |
| `"tv_monthly_rfr2"` | 월말 샘플 ≥ 2 (달력월 경로)                     | 수치 + "무위험 2%/년 · 월간 수익률 기준"                            |
| `"tv_daily_rfr2"`   | 월말 샘플 < 2 (봉 단위 fallback)                | 수치 + "무위험 2%/년 · 봉 단위 기간 기준(2개월 미만)"               |
| `"unavailable"`     | `_periodic_returns is None` 또는 모집단 SD == 0 | **`—`** + "변동 없음 또는 기간 산출 불가" — ★`.toFixed()` 호출 금지 |
| `null` (키 부재)    | 구 run (bar t-통계량 시절)                      | 수치 + "구 기준(봉 수익률 · 무위험 0%) — 현재 기준과 비교 불가"     |

- `sharpe_ratio` **값 자체는 `Decimal` 비-옵셔널 유지**. degenerate → `Decimal("0")`. (nullable 화 금지 — `optimizer/engine/grid_search.py:249` 의 dead branch 를 되살리고 FE `.toFixed(2)` 를 깨뜨린다.)
- 등재 site: `engine/types.py BacktestMetrics` · `schemas.py BacktestMetricsOut` · `schemas.py BacktestMetricsSummary` · `serializers.py metrics_to_jsonb` / `metrics_from_jsonb` / `metrics_summary_from_jsonb`.

### 1.2 청산 관련 (신규)

| 이름                   | 위치                    | 타입                   | 비고                        |
| ---------------------- | ----------------------- | ---------------------- | --------------------------- |
| `liquidated`           | `strategy_state.Trade`  | `bool = False`         | 엔진 내부                   |
| `liq_price`            | `strategy_state.Trade`  | `float \| None = None` | entry 시 1회 계산·캐시      |
| `liquidated`           | `engine/types.RawTrade` | `bool \| None = None`  | 어댑터 전파                 |
| `liquidation_occurred` | metrics 4-site          | `bool \| None = None`  | `leverage > 1` 일 때만 채움 |
| `liquidation_count`    | metrics 4-site          | `int \| None = None`   | 동상                        |
| `exit_kind` (DB 값)    | `service.py:442` 기록값 | `"liquidation"` 문자열 | ★아래 참조                  |

**★`ExitOrderKind` enum 은 확장하지 않는다.** `exit_order_mapping.py:48 map_exit_kind` 의 `else` fall-through 가 새 값을 조용히 trigger-market 으로 빌드한다(현재는 dead code = `BL-365`, 배선 시점에 발현). 대신 **DB 문자열 컬럼에만** 기록한다:

```python
# service.py:442
exit_kind = "liquidation" if t.liquidated else (t.exit_kind.value if t.exit_kind is not None else None)
```

- 컬럼 = `models.py:188` `max_length=16` → `"liquidation"`(11자) 수용. **마이그레이션 0.**
- `v2_adapter.py:337` 은 Python `t.exit_kind is None` → `"taker"` 라우팅 = 청산은 시장가 taker. 의도한 동작.
- **FE 의무**: `trade-ledger-table.tsx:29` `EXIT_REASON_LABEL` 에 `liquidation: "강제청산"` 추가. 누락 시 `:163` 의 `?? "시그널 청산"` 폴백이 강제청산을 시그널 청산으로 **거짓 표시**한다.

### 1.2b ★마진 회계 · Trade 생성 chokepoint (codex G0 로 개정)

**`running_equity` 는 건드리지 않는다.** `interpreter.py:1322` 가 Pine `strategy.equity` 로 **그대로 반환**하므로, 마진 회계용으로 전용·차감하면 Pine 스크립트가 보는 값이 오염된다.

**가용 증거금은 파생한다** (상태 중복 없음 = drift 불가):

```
Trade.margin_used: float | None      # 진입 시 notional/leverage 를 기록
available = running_equity - Σ(open_trades 의 margin_used)
통과 조건 = required <= available * 0.95
```

**★`Trade` 생성 site 는 2곳이다** — `strategy_state.py:509`(entry 시장가) + `:626`(`check_pending_fills` 의 stop 체결). **`check_pending_fills` 는 `entry()` 를 우회해 `Trade(...)` 를 직접 만든다.** 따라서 `entry()` 에만 게이트를 걸면 **stop 진입이 그대로 통과**한다. 게다가 체결가가 갭에 따라 달라져 placement 시점 검증으로 대체할 수도 없다.

→ **단일 chokepoint 헬퍼로 통합**한다:

```python
def _open_trade(self, *, trade_id, direction, qty, bar, fill_price, comment) -> Trade | None:
    """마진 게이트 → liq_price 계산 → Trade 생성. 두 생성 site 의 유일한 관문."""
```

두 site 가 모두 이 헬퍼를 호출한다. 게이트 실패 시 `None` + `warnings`. `leverage <= 1` 이면 게이트·liq 계산 모두 early-return 하여 **기존 동작 그대로**.

### 1.2c Sharpe 정렬 혼재 — 마커만으로는 안 고쳐진다 (codex G0)

`repository.py:71-77` 의 sort whitelist 는 **원시 JSONB `sharpe_ratio` 숫자만** Numeric 캐스팅한다. convention 을 보지 않으므로, 마커를 넣어도 **의미가 다른 값이 계속 한 순위로 정렬**된다. 마커는 정렬을 고치는 게 아니라 **혼재를 보이게** 만든다.

→ 채택: 정렬 자체는 그대로 두고(구 행을 숨기거나 배제하면 데이터가 사라진다), **목록이 sharpe 로 정렬 중이면서 결과에 두 컨벤션이 섞여 있으면 FE 가 고지**한다. 완전 해소(read-time recompute)는 후속 BL.

### 1.2d optimizer / stress_test 저장 sharpe 도 혼재 (codex G0)

`optimizer/serializers.py:104` · `stress_test/serializers.py:80,159` 가 각자 JSONB 에 sharpe 를 저장한다. 본 스프린트는 **backtest metrics 만** 마킹하므로 두 도메인의 과거 결과는 구·신 구분 없이 남는다. → **문서화 + 신규 BL**. 이번 스코프에 넣지 않는다(3 도메인 동시 마킹은 스코프 폭발).

### 1.2e ★★레버리지 시맨틱 = TV/MT5 컨벤션 (사용자 확정, 설계 개정)

**레버리지는 주문 수량을 바꾸지 않는다.** 필요증거금(= notional / leverage)을 정해 진입 가능 여부를 게이트하고, 청산가를 결정할 뿐이다.

1차 출처 확인:

| 플랫폼           | 수량을 바꾸나 | 표현                                                                                | 청산                                                  |
| ---------------- | ------------- | ----------------------------------------------------------------------------------- | ----------------------------------------------------- |
| TradingView      | ❌            | `margin_long/short` = 포지션 중 자기 자금 비율(%). 25% → 자본의 400% 까지 진입 가능 | **부분** 청산(마진콜). 에뮬레이터는 필요액의 4배 청산 |
| MT5              | ❌            | 계좌 레버리지 1:N → 필요증거금 = notional/N                                         | Stop Out 레벨, 손실 큰 것부터                         |
| QuantConnect     | ❌            | `SetLeverage` = 매수여력 상한                                                       | 마진콜                                                |
| 거래소 UI(Bybit) | △             | **증거금** 입력 × N = notional                                                      | 격리 **전량** 청산                                    |

어디서도 레버리지가 *notional 입력*을 곱하지 않는다. 거래소 UI 조차 곱하는 대상은 **증거금** 입력이다. 우리 `percent_of_equity` 는 notional 기준이므로 곱하면 두 컨벤션을 섞는 것이 된다.

**따라서 `compute_qty` 는 수정하지 않는다.** 이 결정이 설계를 단순화하면서 동시에 강화한다 - 레버리지>1 에서도 **Pine 사이징이 TV 와 동일**하므로 TV parity 가 유지된다(제품의 북극성, CONTEXT.md/ADR-003).

**레버리지 노출을 키우는 법** = 사이징 %를 100 초과로 올린다(TV 와 동일). ★실측 확인: `default_qty_value` 는 **상한이 없다**(BE `gt=0` 만 / FE `min={0}`, max 없음 / zod `positive()`). 즉 `strategy.percent_of_equity = 1000` 은 **지금도 입력 가능**하며 **사이징 스키마 변경은 불필요**하다.
※ `position_size_pct`(BE `le=100`)는 **Live Settings 미러 전용**이고 Live 설정 자체가 `le=100` 이라 이 상한은 올바르다. 올리면 미러 시맨틱이 깨진다 - S9 영역이지 본 항목이 아니다.

**청산은 TV 의 부분청산이 아니라 Bybit isolated 전량 청산을 쓴다.** 우리 사용자는 크립토 무기한 트레이더이고 `liquidation.py` 가 그 모델이다. **의도적 divergence 이므로 UI 에 고지**한다.

**leverage=1 은 마진 모델 없음(현행 유지).** 1x 에서 자본 초과 사이징이 가능한 것은 선재 갭이고 `mdd_exceeds_capital` 이 그 플래그다. 여기에 게이트를 켜면 byte-identity 가 깨지므로 **`leverage > 1` 게이트 뒤에 둔다**. 1x 마진 모델은 후속 BL.

**R3(anti-dead-gate)는 청산이 담당한다** — 1x 는 IMR=1 이라 청산가가 `entry x 0.005`(사실상 도달 불가 = 현물 정합)지만, 3x 는 `entry x 0.672` 라 33% 역행에 청산된다. corpus 는 대형 낙폭이 있으므로 반드시 트리거된다.

### 1.3 청산 모델 파라미터 (고정 + 고지 대상)

`IMR = 1/leverage` · long `liq = entry × (1 − IMR + MMR)` · short `liq = entry × (1 + IMR − MMR)` · `MMR = 0.005`(플랫, 단일 tier) · isolated · Bybit 기준. 파산수수료·펀딩·tier 계단 **미반영** → UI 고지 대상이지 구현 대상이 아니다(BL-186b).

---

## §2. 환경 (★포트를 손으로 적지 말 것)

```bash
# BE 테스트 — 3-env 를 통째로 export. .env.local 이 SSOT.
cd backend && set -a; source .env.local; set +a && uv run pytest -q
```

- env 없이 돌리면 conftest 가 `localhost:5432` 로 폴백해 **400+ errors** 가 난다.
- `docs/perf-surface/*` · `docs/money-path-accuracy/*` 의 **5436 표기는 stale**. 2026-07-25 포트 정렬로 현재는 `.env.local` 값(5433)이다.
- **8100 백엔드**: 2026-07-24 기동 프로세스가 닫힌 5436 을 향해 모든 API 가 실패하고 브라우저엔 CORS 로 보였다. **CORS 문제가 아니다.** Makefile 은 이미 정정돼 있으므로 `pkill -f "uvicorn src.main:app.*8100"` 후 `make be-isolated` 로 해소. (본 스프린트 §0 에서 해소 완료 — 401/26ms 확인.)
- **FE 테스트는 `pnpm test`** (= `vitest run`). `pnpm test --run` 은 `Unknown option: 'run'` 으로 죽는데 **exit code 0** 이라 조용히 통과한 것처럼 보인다.
- **Docker VM 디스크** — 포화 시 Postgres 가 `PANIC: No space left` 무한 크래시 루프. 회복은 **`docker builder prune -f` 만**. 볼륨·이미지 금지(캐시는 재생성되지만 볼륨은 아니다).

---

## §3. 감사 규약 (baseline 오염 차단)

- **R1** — baseline regen 커밋은 **sharpe 변경만** 포함한다. 다른 metric 이 함께 바뀌면 게이트가 새는 것이다.
- **R2** — B2(레버리지) 브랜치에서 아래가 **빈 출력**이어야 한다:
  ```bash
  git diff --name-only <base>...HEAD -- backend/tests/fixtures/pine_corpus_v2/ backend/tests/backtest/engine/golden/
  ```
  `leverage=1.0` byte-identical 불변식의 **구조적** 강제다(단순 if 문 신뢰 금지).
- **R3 anti-dead-gate** — R1/R2 만으로는 게이트를 `if False:` 로 바꿔도 전부 green 이다. `leverage=3.0` 에서 최소 1 corpus 결과가 달라짐을 **반드시 함께 단언**한다.
- **R6 (codex G0)** — 기본 config golden 의 diff 0 은 게이트 증명으로 **불충분**하다. 이미 요청값 1~125 가 DB config 에 저장되고 `config_mapper.py:103` 이 이를 복원하며, **재실행·optimizer(`optimizer/service.py:248`)·stress_test(`stress_test/service.py:335`) 가 그 경로로 엔진에 비-1 leverage 를 넣는다.** 저장된 `leverage != 1` 백테스트를 재실행/최적화하는 회귀를 **명시적으로** 추가한다.
- **R4 anti-circular** — Sharpe 기대값은 **사람이 전개한 산술 상수**로 고정한다. 엔진 산출값을 기대값으로 쓰지 않는다.
- **R5** — stale 주석 정정 시 **숫자를 다시 적지 않는다**("24 필드"→"48 필드" 는 즉시 다시 stale). "필드 수 SSOT = dataclass + `test_metrics_field_parity` tripwire" 로 표현.

---

## §4. 워커 규약

| 워커      | 디렉토리      | 금지                    |
| --------- | ------------- | ----------------------- |
| **W1 be** | `backend/**`  | `frontend/**` 수정 금지 |
| **W2 fe** | `frontend/**` | `backend/**` 수정 금지  |

- 워커는 **git 조작 금지**(커밋은 오케스트레이터가 워커당 1개). FE worktree 는 사전 `pnpm install`.
- **codex 샌드박스는 로컬 DB 포트 접속을 막는다** → 워커는 DB 비의존 테스트만 돌릴 수 있다. **전체 스위트는 평가자가 메인 venv 로 직접** 돌린다. 워커 자기보고 신뢰 금지.
- **★★`codex exec` 는 백그라운드에서 stdin 이 열려 있으면 무한 대기한다.** 로그에 `Reading additional input from stdin...` 만 찍히고 프롬프트를 인자로 넘겼는데도 영원히 진행되지 않는다(CPU 0%, 프로세스는 살아 있어 "생각 중"으로 오인하기 쉽다). **반드시 `< /dev/null` 을 붙여라.** 이번 스프린트에서 워커 2기가 각각 52분/38분을 이 상태로 낭비했고 산출물은 0이었다.
- **출력을 `| tail -N` 으로 파이프하면 완료 전까지 아무것도 안 보인다**(버퍼링). 진행 관측이 필요하면 `> file 2>&1` 로 직접 리다이렉트하라. 위 stdin 정체를 조기에 못 잡은 이유가 이것이다.
- **★`codex exec` 의 쓰기 루트 = 실행 시점 cwd.** 셸 cwd 가 `backend/` 인 채로 FE 워커를 띄우면 `frontend/` 를 못 건드리고 "쓰기 권한 없음" 으로 끝난다. **레포 루트에서 띄워라**(`cd <repo> && codex exec ...`). 이번에 FE 워커가 이 이유로 1회 공전했다(다만 워커가 정직하게 거부하고 backend 를 안 건드린 것은 올바른 동작).
- 평가자(Claude 서브에이전트)는 4축으로 적대 평가하고 **게이트를 직접 실행**한다: BE `ruff` · `mypy` · `pytest`(3-env) / FE `pnpm test` · `pnpm typecheck` · `pnpm lint`.
- `ruff format` 은 이 레포의 게이트가 **아니다**(단 pre-commit 훅은 돌린다 → 커밋 후 재게이트 의무).

---

## §5. 스코프 배제 (과설계 차단 — 명시적으로 하지 않는다)

1. **BL-389** finance-math 추출 / `src/finance/` 신설 — `leverage_model.py` 는 `pine_v2` 내부 모듈이지 신규 최상위 도메인이 아니다.
2. **`_periodic_returns` daily fallback 의 sub-daily resample 수정** — sortino baseline 까지 흔들려 R1 이 깨진다. 백로그 신규 등재만.
3. **`ExitOrderKind` 확장 / `BacktestTrade.exit_reason` 컬럼 신설** — §1.2 참조.
4. **BacktestMetrics SSOT 메타프로그래밍 파생** — 사용자 명시 거부. B3 는 tripwire 2건 + 주석 정정 + 백로그 마킹뿐.
5. **cross margin / tier 계단 MMR / 파산수수료 / 펀딩-청산 상호작용** — 고지 대상이지 구현 대상 아님(BL-186b).
6. **`close()` 의 fee-net `running_equity` 전환** — L=1 byte-identity 파괴. 근사로 문서화만.
7. **1x 마진 게이트 활성화** — byte-identity 상위 불변식과 충돌. 후속 백로그.
8. **Track A 에 `check_exit_fills`/`process_market_intents` 추가** — 청산 배선과 별개 문제.
