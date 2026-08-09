# Bybit mainnet 진입 runbook ([BL-003])

> **작성일 2026-08-09.** ★**이 문서의 실측에는 유효기한이 있다.**
> 코드 인용(파일:줄)은 `ce0fc927` 기준이고, Bybit 정책·UI 서술은 **미확인**이다(§8 참조).
> 착수 전 §0 을 먼저 돌려 전제를 다시 재라 — 이 레포는 「남이 적어 둔 실측」이 틀린 것을
> 반복해서 겪었다.
>
> **범위** — 이 문서는 **진입 절차 + 되돌리는 절차**다. 실행 자격(soak 168h)은 별개 축이고
> `scripts/soak-gate.sh` 가 판정한다.

---

## 0. 착수 전 재측정 (건너뛰지 마라)

```bash
# ⑴ Trigger — PASS(exit 0)만이 자격이다. UNKNOWN(2)·FAIL(1)이면 여기서 멈춘다.
ssh truewords-oracle 'bash -lc "cd ~/quantbridge && scripts/soak-gate.sh"'

# ⑵ 서버 egress IP — Bybit IP whitelist 에 넣을 값. ssh HostName 과 같은지 매번 확인해라.
ssh truewords-oracle 'bash -lc "curl -s https://api.ipify.org; echo"'

# ⑶ 아래 §2 의 코드 인용이 아직 유효한지
grep -n "ExchangeMode.live" backend/src/trading/registry.py
grep -n "AccountModeNotAllowed" backend/src/trading/services/live_session_service.py
```

**2026-08-09 실측값** (그대로 믿지 말고 위를 돌려라):

| 축             | 값                                                                      |
| -------------- | ----------------------------------------------------------------------- |
| soak gate      | `UNKNOWN 진행중` — C1 **26.54h/168h**(15.8%) · C2 15.30h/24h · 실격 0   |
| 서버 egress IP | **131.186.36.240** (ssh HostName 과 동일 — 실측)                        |
| 24h 연속 달성  | **0회 / 39세션** · 최장 19.42h ([BL-641] — MTBF 점추정은 인용하지 마라) |

---

## 1. 전제조건 체크리스트

거래소 콘솔 쪽 (사용자가 직접):

- [ ] **API 키를 새로 발급**한다 — demo 키를 재사용하지 않는다. 계정 배타성([BL-634])이
      키가 아니라 **계정** 단위라, 같은 계정을 두 곳에서 쓰면 `position_divergence` 로 죽는다.
      이 레포는 그 사고를 이미 겪었다([BL-633] 이중 호스트 오염).
- [ ] **출금 권한 OFF** — 키 권한에서 Withdraw 를 끈다. 이것 하나가 최악의 손실 상한을 정한다.
- [ ] **IP whitelist = §0⑵ 로 실측한 서버 IP 하나만.** 로컬 맥을 넣지 마라 — 넣는 순간
      [BL-633] 의 이중 호스트 구조가 다시 생긴다.
- [ ] **레버리지 1:1** — 계정 기본 레버리지를 1x 로. 데모는 2x 로 돌고 있다(실측
      `settings.leverage = 2`)지만 mainnet 첫 진입은 1x 다.
- [ ] 키 권한은 **Trade + Read 만**. Transfer/Sub-account 는 끈다.

레포 쪽:

- [ ] `scripts/soak-gate.sh` **PASS(exit 0)** — §0⑴.
- [ ] **데모 안정성 게이트** — `live_session_service.py:110-111` 이 live 경로에서만
      `_enforce_demo_stability` 를 부른다(`:194-204`). `_MIN_DEMO_STABLE_DAYS = **7**`(`:48`)이고
      재는 값은 **`user.created_at` 경과일**이다. 조회 실패는 `days_elapsed=0` 으로 **fail-closed**.
- [ ] `.env.production` 준비 완료 — §3.

---

## 2. cutover 코드 변경 — **6곳이다**

★**2026-08-09 회차는 이 변경을 하지 않았다.** 소크 창이 진행 중인 실험이라 `backend/src` 를
건드리지 않았다. 아래는 **위치와 근거**이고, 실제 변경은 cutover 회차의 일이다.

> ★★★**초안은 「2곳뿐」이라고 적었고 그것은 거짓이었다** (2026-08-09 codex 적대 리뷰 + 코드 대조).
> 빠진 넷 중 하나(`close_service.py:92`)는 **나갈 문을 막는다** — 그것만 놓치면 실자금 포지션을
> 열고 **§7 rollback 이 422 로 실패**한다. 아래 표가 전수다.
>
> 재현: `grep -rn "ExchangeMode.demo" backend/src/` → `environment` 기본값·docstring 을 빼면
> 게이트 **5곳**이 남고, 여기에 `registry.py` stub 을 더해 6곳이다.

| #   | 자리                                   | 풀지 않으면                                                    | 급   |
| --- | -------------------------------------- | -------------------------------------------------------------- | ---- |
| ⑴   | `trading/registry.py:43-44`            | `OrderService` dispatch 가 `ProviderError` — 수동 주문 불가    | 중   |
| ⑵   | `services/live_session_service.py:115` | **세션 등록 자체가 안 된다** (`AccountModeNotAllowed`)         | 필수 |
| ⑶   | `tasks/live_signal.py:3383`            | 세션이 열려도 **평가 워커가 skip** → 신호·주문 **0건**         | 필수 |
| ⑷   | **`services/close_service.py:92`**     | ★**청산/flatten 이 422 `live_mode_stub`** — **나갈 문이 없다** | ★★★  |
| ⑸   | `services/position_service.py:332`     | 계정 스코프 포지션 조회가 `live_mode_stub`                     | 관측 |
| ⑹   | `services/position_service.py:427`     | 세션 포지션 조회가 `live_mode_stub` → **UI 가 못 본다**        | 관측 |

★★★**순서 규약: ⑷ 를 먼저 풀어라.** 진입 경로(⑵⑶)만 열고 ⑷ 를 안 풀면 **포지션을 열 수는
있는데 앱으로 닫을 수 없다.** 그 상태에서 남는 수단은 Bybit 콘솔 수동 청산뿐이고, 그것은
원장에 `external_manual` 로 남아 대조가 깨진다.

### ⑴ `backend/src/trading/registry.py:43-44`

```python
# 현재 — 둘 다 stub 으로 간다
(ExchangeName.bybit, ExchangeMode.live, False): providers.BybitLiveProvider,
(ExchangeName.bybit, ExchangeMode.live, True): providers.BybitLiveProvider,
```

`BybitLiveProvider`(`providers.py:2248-2286`)는 **전 메서드가 `ProviderError` 를 raise 하는
stub** 이다. cutover = demo 와 같은 provider 로 교체:

```python
(ExchangeName.bybit, ExchangeMode.live, False): providers.BybitDemoProvider,
(ExchangeName.bybit, ExchangeMode.live, True): providers.BybitFuturesProvider,
```

### ⑵ `backend/src/trading/services/live_session_service.py:115-119`

```python
if account.exchange != ExchangeName.bybit or account.mode != ExchangeMode.demo:
    raise AccountModeNotAllowed(...)
```

`mode != demo` 조건을 푼다. **`exchange != bybit` 는 그대로 둬라** — OKX/Binance live 는
provider 가 없다.

### ★★★진입 자물쇠는 ⑵ 다 — ⑴ 을 안전장치로 믿지 마라

2026-08-09 실측. `registry.py` 의 stub 은 **dispatch 를 거치는 경로만** 막는다. 그런데
`BybitFuturesProvider()` 를 **직접 생성**해 registry 를 우회하는 자리가 **13곳**이다:

```
tasks/live_signal.py:621,967,2385,2898,4302
tasks/trading.py:1371,1538,1699,1919,2218
tasks/alert_rules.py:67 · tasks/conditional_entry_recovery.py:195
trading/dependencies.py:59            # module-level singleton
# 재현: grep -rn "Bybit\(Futures\|Demo\|Live\)Provider()" backend/src/
#   → 14줄이 나오고 그중 trading.py:1736 은 주석이다
```

그리고 호스트를 정하는 것은 provider **클래스**가 아니라 `Credentials.environment` 이고,
그 값은 `account_service.py:92` 에서 **`environment=account.mode`** 로 채워진다.

⇒ **`mode=live` 계정이 존재하고 세션이 열려 있으면, 그 13곳은 registry 와 무관하게
`api.bybit.com` 을 친다.** registry stub 이 지금 무해한 이유는 「stub 이 막아서」가 아니라
**「세션 게이트(⑵)와 평가 게이트(⑶)가 live 계정을 통과시키지 않아서」**다.

**함의 셋:**

1. **⑴ 은 안전장치가 아니다.** `OrderService` 계열(HTTP 수동 주문·webhook) 경로를 여는 변경이고,
   세션 자동매매 경로는 ⑵⑶ 이 지배한다.
2. **rollback 에서 ⑴ 만 되돌리면 실자금이 계속 돈다** — §7 이 **stop 을 맨 앞에** 두는 이유다.
   코드 원복은 **이미 열린 세션을 멈추지 않는다.**
3. **진입 자물쇠와 출구 자물쇠가 다르다** — 진입은 ⑵⑶, 출구는 ⑷ 다. **⑷ 를 먼저 풀어라**(위 표).

### ★건드리면 안 되는 것 — base URL 매핑은 **이미 있다**

`providers.py:2202-2210` 의 `_apply_bybit_env` 가 이미 두 환경을 가른다:

```python
if environment == ExchangeMode.demo:
    exchange.enable_demo_trading(True)   # api-demo.bybit.com
# live 는 no-op — CCXT 기본값이 api.bybit.com 이다
```

`providers.py:2256-2257` 의 주석은 _"BybitDemoProvider/BybitFuturesProvider base URL mainnet
매핑 + 라이브 검증"_ 을 할 일로 적었지만, **매핑은 이미 존재한다**(2026-08-09 실측). 축은
`Credentials.environment`(`:108-109`)이고 `ExchangeAccount.mode` 에서 흘러온다.
⇒ **provider 본문을 새로 쓸 일이 없다.** cutover 는 위 표의 6곳에서 **`mode` 술어를 푸는 것**이
전부이고, 새로 작성할 코드는 없다.

### 회귀 방어

- `backend/tests/trading/test_live_session_commits.py:270,306` 이 `AccountModeNotAllowed` 를
  단언한다 — ⑵ 를 풀면 **이 테스트가 red 가 되는 것이 정상**이다. 함께 갱신해라.
- `backend/tests/trading/test_demo_stability_gate.py:100-108` 은 「N일 경과 → 게이트 통과 →
  live stub 도달」을 단언한다. ⑴ 을 바꾸면 stub 이 사라지므로 이 테스트도 갱신 대상이다.
- ★**둘 다 「고쳐야 할 red」이지 회귀가 아니다.** 구분해서 커밋해라.

---

## 3. 시크릿 절차

**보관처 = 오라클 서버 파일 단독** (2026-08-09 사용자 결정). 원본은 서버에 한 벌만 두고
로컬에는 두지 않는다. 서버는 이미 루트 `.env`(0600) + `backend/.env.local`(0600) 을 같은
방식으로 들고 있다(2026-08-09 실측).

### 생성

★**아래는 사용자가 자기 셸에서 직접 돌린다.** AI 세션에서 돌리지 마라 — 토큰이 평문으로
대화에 남는다.

```bash
ssh truewords-oracle
umask 077
cat > ~/quantbridge/.env.production <<'EOF'
BYBIT_SMOKE_API_KEY=여기에_실제_키를_붙여넣어라
BYBIT_SMOKE_API_SECRET=여기에_실제_시크릿을_붙여넣어라
EOF
chmod 600 ~/quantbridge/.env.production
```

> ★★★**위 두 값은 플레이스홀더다.** 문자 그대로 실행하지 마라 — 이 레포는 사용자가
> 플레이스홀더를 그대로 붙여넣은 전례가 있다(2026-08-07 FE 배포, `CLERK_SECRET_KEY`).
> `scripts/bybit-smoke.sh` 가 잡는다 — 패턴(`PASTE`/`YOUR_`/`REPLACE`/`여기에` …)뿐 아니라
> **영숫자 16자 이상**이라는 구조적 술어까지 건다. ★단 **패턴 목록은 완전할 수 없다**
> (`REPLACE_ME` 가 초판을 그대로 통과했다) — 셸을 최후 방어선으로 믿지 마라.

### ★인라인 주석을 쓰지 마라

이 레포 관례상 env 파일은 `KEY=value  # [필수 …]` 로 쓴다. **`.env.production` 에서는
금지다.** 값에 주석이나 한글이 섞이면 401 이 아니라 **500** 이 난다([BL-625] 2차 결함 —
SDK 가 헤더를 ascii 인코딩하며 `UnicodeEncodeError`). 증상이 달라 진단이 늦는다.
`scripts/bybit-smoke.sh` 가 이것을 사전 검사한다.

### 회전

1. Bybit 콘솔에서 **새 키 발급** (기존 키는 아직 살려 둔다).
2. 서버 `~/quantbridge/.env.production` 을 새 값으로 교체 (`umask 077` 유지).
3. `scripts/bybit-smoke.sh --env-file ~/quantbridge/.env.production --mode live --market spot`
   — dry-run 으로 형식 검사.
4. 세션을 태우는 중이면 **먼저 §7 로 내리고** 재기동한다.
5. Bybit 콘솔에서 **구 키 폐기**.

★`TRADING_ENCRYPTION_KEYS`(Fernet)는 **다른 축**이다 — DB 에 저장된 거래소 키를 암호화하는
값이고, 바꾸면 기존 암호화 키를 복호화할 수 없다. 회전 규약은 콤마 구분 `new,old`
(`.env.example:29`). mainnet 진입과 함께 바꾸지 마라 — 한 번에 둘을 고치면 서로의 증거를 가린다.

### `app_env=production` 을 켤 때

`config.py:358-407` 의 `_enforce_production_safety` 가 부팅 시점에 검사한다 —
`SECRET_KEY` / `CLERK_SECRET_KEY` / `WAITLIST_TOKEN_SECRET` placeholder + `PROMETHEUS_BEARER_TOKEN`
필수. ★**`app_env == production` 일 때만이다**([BL-625]) — development 로 두면 플레이스홀더가
어느 게이트에도 안 걸리고 `/health` 는 200 을 낸다. 목록 전문 = `backend/.env.prod.example`.

★**`app_env=production` 은 게이트를 죽인다** — bearer 강제 vs `soak-gate.sh` 의 무인증 조회.
2026-08-07 에 실측으로 밟았다. mainnet 세션과 소크 게이트를 같은 API 인스턴스에서 돌릴
계획이면 이 충돌을 **먼저** 풀어라.

---

## 4. Kill Switch — `.env` 오버라이드

2026-08-09 사용자 결정 = **`.env` 오버라이드만**. `config.py` 기본값은 건드리지 않는다
(데모 소크 창의 처치를 바꾸지 않기 위해). `KILL_SWITCH_*` 4종은 `backend/.env.example:97-100`
에 이미 있고, `Settings.model_config(case_sensitive=False)` 라 env 가 그대로 이긴다.

### ★현재 기본값은 소액에서 판별력이 0 이다

`config.py:135-157` 실측 — cumulative **10%** · daily **$500** · api_error_streak **5** ·
capital_base fallback $10,000.

셈: 자본 $3,300 에서 daily $500 은 자본의 **15%** 다. 그런데 cumulative 10%(=$330)가 **먼저**
걸린다 ⇒ **daily 는 영원히 발화하지 않는다.** 자본 $50 이면 10배 차다. 즉 기본값을 그대로
쓰면 일일 손실 가드가 **사실상 없는 채로** 실자금이 돈다.

### 단계별 값

| 항목                                  | 단계 1 (smoke · $50) | 단계 2 (세션 · ~$3,300) | 근거                                          |
| ------------------------------------- | -------------------- | ----------------------- | --------------------------------------------- |
| `KILL_SWITCH_CUMULATIVE_LOSS_PERCENT` | `5.0`                | `5.0`                   | 기본 10% → 절반. strategy-scoped              |
| `KILL_SWITCH_DAILY_LOSS_USD`          | `1.5`                | `100.0`                 | 자본의 **3%**. account-scoped                 |
| `KILL_SWITCH_API_ERROR_STREAK`        | `3`                  | `3`                     | 기본 5 → 3. IP whitelist 오설정을 빨리 잡는다 |
| `KILL_SWITCH_CAPITAL_BASE_USD`        | `50`                 | `3300`                  | fallback 전용 — 실잔고 조회가 우선이다        |

★**금액을 바꾸면 이 표도 바꿔라.** daily 는 자본의 3% · cumulative 는 5% 라는 **비율**이
결정이고, 절대값은 그 비율의 그림자다.

---

## 5. 단계 1 — smoke ($50)

**목적** = 주문 경로(인증 → 잔고 → 주문 생성 → 취소)가 mainnet 에서 도는지 1회 확인.
**사이징·전략·세션은 검증하지 않는다.**

★**spot 으로 한다.** perp 최소 주문 0.001 BTC 는 명목 **$64.96**(2026-08-09 실측, BTC $64,957)
이고 1x 증거금이 자본 $50 을 넘는다. $50 로 linear 를 시도하면 잔고 부족으로 실패한다 —
그건 경로 검증이 아니라 잔고 검증이다.

★**spot 은 수량이 아니라 명목이 하한이다** — `min_cost = $5.0` 이고 `min_amount` 는 1e-06 BTC 라
사실상 구속하지 않는다. 셸 기본값 `--quantity 0.0002` 는 **$13**(BTC $65k) / **$10**(BTC $50k)로
그 하한 위에 있다. ★**BTC 가 $25,000 아래로 가면 0.0002 도 $5 미만이 된다** — 그때는 수량을 올려라.

> ★★[BL-003] 본문의 **「1 USDT limit-order」는 불가능하다**(2026-08-09 실측 반증) —
> spot 최소 명목이 **$5** 다. 본문은 그 제약을 모르고 쓰였다.

```bash
# ⑴ dry-run — 네트워크 호출 0건. 시크릿 파일 권한·형식만 본다.
scripts/bybit-smoke.sh --env-file ~/quantbridge/.env.production --mode live --market spot

# ⑵ ★사용자 승인 후에만 — 실제 주문이 나간다
scripts/bybit-smoke.sh --env-file ~/quantbridge/.env.production --mode live --market spot --confirm
```

통과 기준 = `smoke_success` 이벤트 + 종료 코드 **0**. `create_order` 는 best_bid −1% 라
즉시 체결되지 않고, 바로 `cancel_order` 로 지운다.

실패하면 **재시도하지 말고** 이벤트를 읽어라:

| `reason`            | 뜻                                                        |
| ------------------- | --------------------------------------------------------- |
| `zero_usdt_balance` | 입금이 안 됐거나 다른 계정을 보고 있다                    |
| `ccxt_error`        | `error` 필드를 읽어라 — IP whitelist 미등록이 여기로 온다 |
| `unexpected_error`  | 타입만 기록된다(키 노출 방지). 셸의 사전 검사부터 다시    |

---

## 6. 단계 2 — 라이브 세션 (~$3,300)

### 왜 $3,300 인가

2026-08-09 서버 DB 실측 — 소크 세션 `de3db35a` 의 `equity_baseline_usdt = 190,034.96` 이고
주문은 **0.058 BTC** 로 반복된다. 사이징은 자본 비례다
(`strategy_state.py:503-506` — `running_equity * qv / 100 / fill_price`, 레버리지 미개입).
따라서 같은 전략·같은 설정에서 최소 주문 `min_qty` 를 내려면:

```
X_min = 190,034 × (min_qty / 0.058)
      = 190,034 × (0.001 / 0.058) ≈ $3,276
```

★**BTC 가격도 `position_size_pct` 도 소거된다** — 비율만 쓰기 때문이다.
★`min_qty = 0.001 BTC` 는 **2026-08-09 실측으로 확정됐다**(`load_markets` — 공개·무인증).

### ★독립 검증 — 셈이 두 경로에서 같은 값을 낸다

위 식은 비율만 쓰므로 BTC 가격을 **안 쓴다**. 그런데 가격을 넣어 **명목 비율**로 다시 세면
같은 답이 나온다(2026-08-09 BTC $64,957 실측):

| 경로                    | 명목                        | 자본 대비 |
| ----------------------- | --------------------------- | --------- |
| 데모 (실측)             | 0.058 × 64,957 = **$3,768** | **1.98%** |
| mainnet $3,276 (계산값) | 0.001 × 64,957 = **$65**    | **2.0%**  |

두 비율이 일치한다 ⇒ **$3,276 은 「최소 주문을 겨우 내는 자본」이면서 동시에 「데모와 같은
리스크 프로필을 유지하는 자본」이다.** 우연이 아니라 같은 식의 두 표현이지만, 산수 실수가
있었다면 여기서 어긋났을 것이다.

⇒ [BL-003] 본문이 제안한 **"소액 $10~50" 은 이 경로에서 반박된다** — 그 자본으로는 세션이
주문을 한 건도 못 낸다. 더 적게 넣으려면 자본이 아니라 **전략의 사이징을 바꿔야 하고**,
그러면 리스크 프로필이 데모(≈2%)와 달라져 **데모 소크를 대조군으로 쓸 수 없게 된다.**

### 순서

1. §4 의 단계-2 값을 `.env` 에 반영하고 워커를 재시작한다.
2. §2 의 코드 변경 **6곳**을 적용하고 **테스트를 갱신**한다(§2 표 + 회귀 방어).
   ★**⑷ `close_service.py:92` 를 먼저 풀어라** — 나갈 문이다.
3. mainnet `ExchangeAccount` 를 `mode=live` 로 등록한다.
4. **세션 1개만** 연다. `max_active_per_user` 는 **5**(`live_session_service.py:71`)지만 첫 회는 1이다.
5. `backend/scripts/live_session_admin.py status --symbol <SYMBOL>` 로 확인 —
   `EXCLUSIVE=YES` 여야 한다. 아니면 §7 로 즉시 내려라.

---

## 7. ★되돌리는 절차 (rollback)

**진입 절차만 있는 runbook 은 절반이다.** 아래는 위에서 아래로, 중간에서 멈추지 않는다.

```bash
cd ~/quantbridge/backend

# ⑴ 세션을 먼저 멈춘다 — flatten 보다 stop 이 앞이다.
#    ★순서가 실측으로 갈렸다: 세션을 살린 채 flatten 만 하면 엔진이 재무장해
#    EXCLUSIVE=NO 가 된다(2026-08-08 P0/P7 대조).
#    ★session_id 는 **positional** 이고 --confirm 은 **required** 다
#      (`live_session_admin.py:409-415`). `--session-id` 로 쓰면 실행되지 않는다.
uv run python scripts/live_session_admin.py stop <SESSION_UUID> --confirm

# ⑵ 포지션 청산 — reduce-only 시장가. 원장에 남는다.
#    ★★★live 계정에서는 `close_service.py:92` 가 **422 live_mode_stub 으로 거부한다.**
#      §2⑷ 를 풀지 않았다면 이 명령은 실패한다 — 그 경우 Bybit 콘솔 수동 청산뿐이고
#      원장에는 `external_manual` 로 남는다.
uv run python scripts/live_session_admin.py flatten <SESSION_UUID> --confirm

# ⑶ 확인 — FLAT=YES · RESTING_CONDITIONAL=0 · QUIET=YES 여야 한다
#    ★★flatten 이 「✓ 이미 flat (no_open_position)」을 내고 **exit 0** 이어도 끝난 게 아니다.
#      `close_service.py:102-104` 는 **포지션만** 보고 조건부 주문은 안 본다. 미체결 조건부
#      진입이 남아 있으면 나중에 체결된다 — RESTING_CONDITIONAL 을 **반드시 눈으로** 확인해라.
uv run python scripts/live_session_admin.py status --symbol <SYMBOL>
```

그 다음:

4. **코드 원복** — §2 의 2곳을 되돌린다. `git revert` 로 한 커밋에 묶어 두면 여기서 싸다.
   ★**원복이 ⑴~⑶ 을 대신하지 못한다** — §2 의 「자물쇠는 ⑵ 하나뿐」 참조. 코드를 되돌려도
   **이미 열린 세션은 멈추지 않고**, registry 를 우회하는 10곳은 `account.mode` 만 보고 mainnet 을
   친다. 그래서 stop 이 맨 앞이다.
5. **키 폐기** — Bybit 콘솔에서 mainnet 키를 삭제한다. 서버
   `~/quantbridge/.env.production` 도 지운다(`shred -u` 또는 `rm`).
6. **잔고 회수** — 출금 권한을 껐으므로 **콘솔에서 수동 출금**해야 한다. 이것이 §1 의
   "출금 권한 OFF" 가 사는 대가다. 알고 골라라.
7. **데모 복귀** — `mode=demo` 계정으로 세션을 다시 연다. 소크 창은 별개 축이라
   영향받지 않는다(`.soak/src` 는 `git archive` 스냅샷 mount).

★**⑴~⑶ 중간에 멈추면 고아 포지션이 남는다.** 2026-08-07 에 고아 포지션이 14시간 방치된
전례가 있다. 실자금에서는 그 14시간이 손실이다.

---

## 8. 한계 — **[확인 필요]** 목록

이 문서가 **재지 않고 쓴 것들**이다. cutover 전에 하나씩 닫아라.

| #   | 항목                                                               | 상태                                                                                             |
| --- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| 1   | **perp `min_qty`** — §6 의 $3,276 이 여기 걸려 있다                | ✅ **2026-08-09 실측 = 0.001 BTC**(가정과 일치) · min_cost 없음 · 명목 **$64.96**                |
| 2   | **spot `min_qty` / 최소 명목** — §5 의 `--quantity` 기본값 근거    | ✅ **2026-08-09 실측** — `min_amount` 1e-06 은 무의미하고 **`min_cost = $5.0`** 이 진짜 하한이다 |
| 3   | **Bybit 정책 화면** — IP whitelist·출금권한 UI 의 실제 위치와 이름 | ⬜ 미확인. 계정이 없다 → 콘솔을 열어 화면 이름을 이 문서에 적어라                                |
| 4   | **mainnet 수수료** — 데모 실측은 taker 0.055% 단일이다([BL-603])   | ⬜ 미확인. mainnet 계정 등급을 모른다 → 콘솔 Fee tier                                            |
| 5   | **`app_env=production` ↔ soak-gate 충돌**의 실제 해                | ⬜ 미확인. §3 마지막 문단                                                                        |

**1·2 를 닫은 방법** (재현 가능 · 공개 엔드포인트 · 인증 없음 · **주문 없음**):

```python
import asyncio, ccxt.async_support as ccxt_async
async def main():
    ex = ccxt_async.bybit({"enableRateLimit": True})   # ★demo 로 전환하지 않는다 = mainnet
    try:
        await ex.load_markets()
        for s in ("BTC/USDT", "BTC/USDT:USDT"):
            m, t = ex.market(s), await ex.fetch_ticker(s)
            print(s, m["type"], m["limits"]["amount"]["min"],
                  (m["limits"].get("cost") or {}).get("min"), t["last"])
    finally:
        await ex.close()
asyncio.run(main())
```

**2026-08-09 출력** (BTC **$64,957** — ★**명목값은 가격을 따라 움직인다. 수량 하한은 안 움직인다**):

| 심볼            | type | `min_amount` | `min_cost` | 최소 명목  |
| --------------- | ---- | ------------ | ---------- | ---------- |
| `BTC/USDT`      | spot | 1e-06        | **$5.0**   | **$5**     |
| `BTC/USDT:USDT` | swap | **0.001**    | (없음)     | **$64.96** |

★★**항목 1 은 「가정이 맞았다」로 닫혔지만, 같은 조회가 두 가지를 새로 뒤집었다** —
초판의 「perp 명목 ~$100」은 실제 **$65** 였고(BTC 를 $100k 로 어림했다), [BL-003] 본문의
**「1 USDT limit-order」는 spot `min_cost = $5` 때문에 애초에 불가능**하다.
**가정을 확인하러 간 조회가 확인 밖의 것을 고쳤다 — 이것이 재는 이유다.**

★**Bybit UI 는 문서와 어긋난 전례가 있다** — 2026-08-07 Cloudflare 회차에서 공식 문서의
메뉴 이름 3개가 실제 화면과 달랐고 검증 메시지 표시 버그까지 있었다. **화면을 보고
이 표를 갱신해라.**

---

## 관련

- [BL-003] `docs/backlog.md#bl-003` — 이 문서의 원장
- [ADR-024] `docs/decisions/024-soak-stability-gate.md` — Trigger 판정 규약
- [BL-634]/[BL-633] — 계정 배타성. §1 의 "키를 새로 발급" 이 여기서 나왔다
- [BL-625] — 플레이스홀더 시크릿이 development 에서 안 걸린다. §3
- `scripts/bybit-smoke.sh` · `backend/scripts/bybit_smoke.py` — §5 의 도구
