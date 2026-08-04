# QuantBridge — Status

> **업데이트:** 2026-08-04 (5차 — **핸들러를 보이게 만들고, nightly 가 거짓말을 멈췄다**)
>
> **★갈래 A — `live_signal.py` 해체 (행위 변경 0).** 4차가 [BL-580] 12곳의 감싸는 핸들러를
> 통째로 오판한 것이 **두 회차 연속**이라, 수리가 아니라 **보이게 만드는 구조 작업**을 먼저 했다.
> `_reconcile_conditional_entries` **876줄 / try 본문 845줄 / 중첩 3 → 46줄 / 8줄 / 1**,
> `_evaluate_session_inner` **796 / 770 / 2 → 17 / 1 / 1**. 본체 운반자(`_inner`·`_with_engine`)에는
> **`try` 가 하나도 없다** — 모든 핸들러가 이름 붙은 헬퍼로 옮겨졌다. 함수 45 → 71개,
> **새 `.py` 소스 파일 0개**(파일 내부 분할만 — 그래야 래칫 9곳 중 1곳만 건드린다).
> ★★★**codex 가 「행위 변경 0」을 한 번 반증했다** — lazy import 를 헬퍼로 옮기자 **실패 시점이
> 커밋 뒤로 밀렸다**(`get_ccxt_provider_for_worker` 가 `order_repo.commit()` 뒤, `run_live` 가
> `try_claim_bar` 뒤). 복원 후 재확인. ★**다중집합 비교는 문장 순서를 구조적으로 못 본다.**
>
> **★갈래 B — [BL-024] nightly real-broker.** 「skeleton 을 채운다」는 전제가 **실측으로 뒤집혔다**:
> nightly 는 07-25~08-03 **10/10 실패**했고 지점은 pytest 가 아니라 `alembic upgrade head` 였다
> (`secrets.TRADING_ENCRYPTION_KEYS_TEST` 부재 → 빈 문자열 → Settings ValidationError).
> ⇒ **pytest 는 한 번도 실행된 적이 없고, `flaky-real-broker` 이슈 89건은 broker flakiness 의
> 증거가 아니다.** 워크플로 9건 수리 + 계약 감사 13테스트(매 PR) + 자기정리 2층 하네스.
> ★**실거래소는 1바이트도 검증되지 않았다** — 차단 사유 = Bybit demo 전용 키 2종 미발급.
>
> **게이트(통합본 실측):** BE **4030 passed / 45 skipped**(= 4013 + contract 13 + 가시성 래칫 4 − 삭제 1) ·
> ruff 0 · mypy 0 (216) · bl-audit active **154** · bl-audit-test 5/0 · docs-audit clean ·
> census **len 40 / sum 84 불변** · FE typecheck·lint 0 · vitest 1242 · e2e design-canon 32 · authed 69.
> **celery 실주행**: 워커가 통합 코드로 재기동(md5 일치) 후 `evaluate_all` 2회 ·
> `sweep_conditional_entries` 12회 성공 · 에러 0 · `live_signal.*` 4태스크 전부 등록.
> ★단 `due_count: 0` 이라 **`_evaluate_session_inner` 본체는 미검증**이다(활성 세션 0).
>
> **★교훈을 게이트로 동결했다** — `tests/tasks/test_live_signal_handler_visibility.py` 4테스트:
> 해체한 28함수 **중첩 1** · 잔여 중첩 **5개 정확값 동결**(늘 수도 조용히 줄 수도 없다) ·
> `try` 본문 천장 **845 → 225** · ★**공허화 방지**(헬퍼 이름이 바뀌면 나머지가 검사 대상 없이 통과).
>
> **★nightly 실검증 — 11회 만에 처음 green** (run `30914689208`). `Alembic migrate` **success**
> (10회 연속 죽던 자리) · `Run real_broker E2E` **skipped** · `Flaky detection` **skipped**
> ⇒ **새 이슈 0건**. `flaky-real-broker` **89건 전부 종료**(OPEN 0 / CLOSED 89).
> ★근거는 로그 표본이 아니라 **코드 이력**이다 — 워크플로는 **생성 시점(04-25)부터** 없는 secret 을
> 참조했고 `alembic/env.py:24` 의 `Settings` import(04-15)·빈 Fernet 거부(04-17)가 **둘 다 먼저**다.
> (오래된 로그는 **HTTP 410 만료**라 로그로는 확인 불가 — 그래서 구성 논증으로 대체했다.)
>
> **★이전 회차 (4차 — 소크를 내리고 축을 옮겼다)**
> **★소크는 중단됐다 (사용자 결정)** — `stop` → `flatten` 으로 **활성 세션 0 · FLAT=YES**.
> ⇒ **`backend/src` 편집·BE pytest 전면 허용.** 아래 「소크가 돌고 있다」 문단들은 **낡았다.**
> 근거: 08-01 이후 종료 7건 중 **5건이 `user_stopped`**(내가 코드 작업하려고 멈춘 것)이고
> 자동 사망은 **0건**이다 — **소크가 짧은 건 결함이 아니라 교착 때문이었다.**
> 「1주 안정 운영」([BL-003])은 역대 최장이 **15.3h = 9%** 라 11배 남았다.
>
> **★발산 축 = 동결.** [BL-591] 슬라이스 A(관측 전용)는 **전사만 남긴 채 보류**하고,
> 축을 **[BL-580] 계측 가드 잔여**로 옮겼다. 재개 조건 = **`phantom` 재발**.
> 전향 예측은 **최종 미판정**(post-fix 누적 **7.24h · phantom 0** · 95% 상계 **0.41/h**).
>
> **★[BL-580] — `_reconcile_conditional_entries` 12곳 전건 수리, census 96 → 84.**
> ★★★**「12곳 전부 같은 형태」라는 내 판정을 기존 회귀 테스트가 반증했다** —
> `unrepresentable_key` 는 **안쪽 발주 `except`** 에 잡혀 `conditional_place`(= 발주 실패)로
> **오기록**되고 있었다(발주 시도조차 없었는데). **함수 하나를 통째로 한 형태로 보지 마라.**
> 게이트: **BE 4013 passed / 46 skipped**(= 3993 + 신규 20) · ruff 0 · mypy 0 (216) ·
> bl-audit active 154 · docs-audit clean · census 84.
>
> **업데이트(3차):** 2026-08-04 — **표적 채널이 한 겹 더 갈렸다**
> **★★★`direction` 은 한 현상이 아니다.** 워커 로그 41시간의 관측 **11건 전량**을 원장과 대조하니
> 부호가 반대인 **두 현상**이었다 — 무해 **`replay_lag` 7**(조건부가 봉 중간에 체결되고 **엔진이**
> 못 따라온다 · 반전 28건 중 7건 = 25% · 7/7 자가치유) : 치명 **`phantom` 4**(엔진 시뮬이 체결로
> 친 주문이 **거래소에 없다** · 자가치유 0 · **사망 2/2**). 체결 경과 시간이 **24.7초 vs 909초**로
> **37배 벌어져 겹침이 0**이다. 산술도 닫힌다 — 11 = `transient` +9 + 킬 2.
> ⇒ **스프린트가 물으라던 「거래소가 못 따라오는 구간」은 이 채널의 4/11 뿐이다.**
>
> **★[ADR-023] 의 긴급도 근거가 정정된다.** 「살아 있는 채널 ≈0.5/h」는 ⑴ **다수가 무해**이고
> ⑵ **벽시계 rate** 였다(노출 기준 1.27/h). 치명 갈래만 노출로 재면 [BL-590] 수리 전 **1.40/h** →
> 수리 후 **0건/6.12h**(기대 8.6건). ★**그래도 「닫혔다」고 쓰지 마라 — 95% 상계 0.49/h** 다.
>
> **★사용자 판정(이번 회차)** — ⑴ **라벨 분해 먼저 · [ADR-023] 은 Proposed 보류**, 긴급도 하향
> ⑵ `phantom` 확정 시 킬을 **인과 판정으로 교체**(phantom 즉시 킬 / `replay_lag` 무시). 근거는
> **판별식이 한쪽으로만 틀린다**는 것 — `Order.filled_at` 이 우리 관측시각이라 `phantom` 을
> **과소계상**할 뿐 과대계상하지 않으므로 **거짓 사망을 만들지 않는다.**
>
> **★이번 회차는 `backend/src` 0줄이다** — 소크가 살아 있어 편집·변이·BE pytest 전면 금지였다.
> 새 파일은 오라클 **`backend/scripts/classify_direction_divergence.py`** 하나뿐이다.
> ⇒ **BE baseline 3993/46 skipped 는 이번 회차에 재확인되지 않았다**(PR #539 의 CI 통과값).
>
> **★사전등록 판정 = 미판정.** 직전 회차 예측(`engine_only` 안 오름 / `direction_transient`
> 오름)은 counter 3종 모두 불변(314·21·24)이었으나 **노출이 1.40h 로 문턱(5h/2h) 미달**이라
> **판별력이 없다.** 「안 올랐다」를 판정으로 쓰지 않았다.
>
> ~~소크가 돌고 있다~~ — 세션 `bbea6da4` 는 4차에서 **중단됐다**(최종 생존 **4.5h**,
> 직전 사망 2건의 65분·105분을 모두 넘겼다). **위 4차 블록이 최신이다.**
>
> **★연장에서 전향 예측을 한 번 더 쟀다 = 미판정**(노출 0.149h, 문턱 6h). 누적 post-fix 는
> 약 **6.8h / phantom 0** 이라 95% 상계가 0.49 → **0.44/h**. **0.25/h 로 낮추려면 총 12h —
> 약 5시간이 더 필요하다.** 그동안 판별식을 **20 테스트로 경계까지 고정**했다.
>
> **업데이트(이전):** 2026-08-04 (후속 회차 — 축이 바뀌었다) — ★**아래 블록의 숫자는 그 회차
> 시점이다.** 소크 생존 시간·사전등록 예측은 **위 3차 블록이 최신**이다.
> **★★★[ADR-023](decisions/023-engine-state-ssot.md) 신설 = Proposed.** 사망 경로의 수리 축이
> **원장 주입(C)에서 「엔진에 영속 상태를 주고 거래소 현실을 되먹인다」로 옮겨간다.**
> 근거: ④=0 에 더해 **유도가 사망 시점에 이미 판정 불가**였고(veto 절반까지 꺼짐), veto 는
> **원장==거래소·엔진만 거짓말**인 사망 경로에서 애초에 발화하지 않으며, 방향도 반대다
> (`engine_only` **314** vs `exchange_only` **21**). ★**사용자 판정 대기 — Accepted 아니다.**
> 선행연구(NautilusTrader·Freqtrade) 대조로 **우리가 내린 기각 3건이 순환**임을 확인했다.
>
> **★[BL-591] 슬라이스 1(계측) = PR #539 **OPEN(미머지)** — 그리고 사전등록 V1 이 발동해
> 슬라이스 2 를 착수하지 않는다.**
> 근거 전문은 [`ADR-022 §슬라이스 1 실측`](decisions/022-engine-position-ssot.md) ·
> 회고는 [dev-log](dev-log/2026-08-04-engine-position-ssot.md). 마이그레이션 **0** · FE **0**.
>
> **④ = 0.** ① 연역 상계 — 주입은 엔진이 완전히 비었을 때만 작동하므로(`strategy_state.py:357`)
> **주입이 값을 넣는 tick ⊆ `exchange_only` tick** ② 모집단(스냅샷 차분 **17.06h**) —
> `exchange_only` **+1** vs 하드 `direction` 킬 **+2** ③ 부검 **2/2** — 사망 세션 2건의 상류에
> `exchange_only` **0건**(유일한 1건은 세션 첫 tick 의 먼지 잔여 `-0.001`, 원장이 비어 주입 대상
> 아님) ④ 최악 상계 **≤1/21**. ⇒ 사망 경로는 **반전**이고 반전은 tick 경계에서 flat 을 거치지
> 않는다 — **C 의 전제가 사망 경로에서 구조적으로 밟히지 않는다.**
>
> ★★★**그보다 큰 것 — net 은 맞고 legs 는 틀리다.** 과거 29세션 재생: 판정 불가 **27.6%**
> (전량 `duplicate_open`). 외부 오라클 11건(로그에 남은 거래소 실측) 대조: **오답 0** 인데
> 적중 4 중 **3건이 `legs=2`** — 거래소는 단일 포지션이다(나머지 1건은 반전이 없던 먼지
> 세션이라 `legs=1` 로 정확했다 — ★**깨지는 것은 반전일 때다**). **`trade_id` 는 trade 가 아니라 Pine
> 진입 규칙 이름**(`PivRevSE` 56체결/19세션)이고 **반전은 `:close:` 키를 만들지 않는다**(배수량
> 진입 하나로 나간다). **슬라이스 1 은 net 으로 `agree` 를 판정하고 슬라이스 2 는 legs 를
> 주입한다 — 계측이 초록이어도 주입될 값은 틀렸다.**
>
> 소크 세션 `bbea6da4` · equity baseline `190359.77569871`. ★**생존 시간은 위 3차 블록을 봐라**
> (이 줄의 「1.53h」는 후속 회차 04:26Z 기준이라 이미 낡았다).
>
> ★**사전등록 예측 = 적중.** `duplicate_open` 은 예측대로 **2번째 `PivRevSE` 체결**(`03:48:16`)
> 에서 발화했다. 첫 읽기가 0 이었던 것은 **호스트 `/metrics` 지연**(상비 참조의 기록된 함정).
> ⇒ ADR-022 §슬라이스 1 의 기전 설명은 **반증되지 않았다.**
> ★★**그리고 판정 불가는 「비율」이 아니라 흡수 상태다** — `since = sess.created_at` 이라 한 번
> 들어가면 세션 끝까지 나오지 못한다. 프로덕션 실증: `open` **44.0 에서 완전 정지**,
> `duplicate_open` **36 연속**. 라이브 시간의 **19.0%** 가 어둡고 진입까지 median **26.6분**이며,
> ★**`position_divergence` 사망 2건이 모두 이미 어두운 뒤에 죽었다.**
>
> ★★**브랜치 전략 — `stage/engine-position-ssot` 이 통합 브랜치다.** **PR #539 는 열어 둔 채**
> 검증이 다 끝나면 **한 번에** `main` 으로 머지한다(사용자 확정 2026-08-04). 다음 회차는
> **이 브랜치에 커밋을 얹거나**, 새 브랜치를 만들어 **이 브랜치로 PR** 을 올린다.
> ★`main` 으로 머지하지 마라. **최근 `main` 머지는 PR #538 @ `70127fdd`(2026-08-03)** 이다.
> 게이트: BE **3993 passed / 46 skipped** · ruff 0 · mypy 0 (**216**) · bl-audit active **154** ·
> docs-audit clean · 사전등록 변이 **M1~M5 전건 판별**.

---

## 다음 스프린트 — **[BL-580] 잔여 84곳 수리** (이제 핸들러가 보인다) + **[BL-024] 실주문 leg**

> ★**이것이 다음 세션의 유일한 진입점이다.** 별도 킥오프 파일을 만들지 않는다.

### ★★첫 3 step — 이것부터 해라 (순서 있음)

**Step 1 — 현재 위치 확인 (5분).**

```bash
QB=/Users/woosung/project/agy-project/quant-bridge
git -C $QB log --oneline -1                     # 83b4492b 여야 한다
git -C $QB rev-list --count origin/main..origin/stage/engine-position-ssot   # 30
gh pr view 539 --json state,title
docker exec quantbridge-db psql -U quantbridge -d quantbridge -Atc \
  "SELECT count(*) FROM trading.live_signal_sessions WHERE is_active=true;"  # 0 = 소크 내려감
```

**Step 2 — ★PR #539 의 표류를 먼저 결정해라 (이게 안 정해지면 뒤가 다 막힌다).**

`stage/engine-position-ssot` 는 이제 `main` 보다 **30커밋** 앞이고, PR #539 의 제목·본문은
**「엔진 포지션 SSOT 슬라이스 1」한 회차만** 설명한다. 그 사이에 3회차가 더 들어갔다
(direction 채널 분해 · BL-580 12곳 · **이번 회차 16커밋**).
⇒ **PR 본문이 브랜치 내용을 더 이상 설명하지 못한다.** 세 갈래 중 하나를 사용자와 정해라:

| 안                 | 내용                                              | 대가                                      |
| ------------------ | ------------------------------------------------- | ----------------------------------------- |
| **A. 본문 재작성** | #539 를 「4회차 통합」으로 다시 쓰고 그대로 머지  | 리뷰 단위가 30커밋으로 크다               |
| **B. 분할**        | 회차별로 PR 을 새로 끊는다                        | 브랜치가 이미 선형이라 되감기 비용이 크다 |
| **C. 지금 머지**   | 검증이 끝났으니 `main` 으로 보내고 #539 를 닫는다 | 「1주 안정 운영」 전에 main 이 움직인다   |

★**사용자 확정 규칙은 「검증이 다 끝난 뒤 한 번에 main」**이다. 이번 회차로 게이트는 전건 통과했지만
**실거래소·`_evaluate_session_inner` 본체는 여전히 미검증**이다 — 그 둘을 「검증 끝」에 포함할지가 판단의 핵심이다.

**Step 3 — 본 작업 착수.** 아래 두 축 중 **자격증명 유무로 갈린다**:

- Bybit demo 키 **있으면** → [BL-024] 실주문 leg (§아래) — 이게 소크를 자동화로 대체하는 축이다
- **없으면** → [BL-580] 잔여 수리 (§아래) — 이번 회차가 그 선행 조건을 만들어 놨다

### ★무엇이 달라졌나 — 이번 회차가 만든 **선행 조건**

[BL-580] 잔여 84곳 중 `live_signal.py` **34곳**은 이제 **이름 붙은 헬퍼 안**에 있다.
운반자 함수(`_reconcile_conditional_entries_inner`·`_evaluate_session_with_engine`)에는
**`try` 가 하나도 없고**, 감싸는 핸들러는 각 헬퍼가 소유하며 **docstring 에 적혀 있다**.
⇒ 4차·3차가 두 번 연속 밟은 **「함수 하나 = 한 형태」 오판의 물리적 조건이 사라졌다.**
★**그래도 산문으로 분류하지 마라** — 누적 판정 42곳에서 「가드 없이 유지」가 **0곳**이다. 주입으로 시작해라.

### ★남은 구조 부채 (이번 회차가 **안 한 것**)

- `_evaluate_session_with_engine` **506줄** — Kind B 추출(E8~E14) 미완. 프롬프트의 「200줄 이하」를
  운반자 기준으로는 못 채웠다. ★단 **목표는 줄 수가 아니라 핸들러 가시성**이었고 그건 달성됐다
  (최대 `try` 본문 845 → 8).
- `_place_planned_entry` 236줄 · `_reconcile_conditional_entries_inner` 203줄 — 경계선.
- `_async_dispatch_event` 256줄 · 최대 `try` 본문 **225줄** — ★**이번 범위 밖**이었다. 이제 이게 최대다.

### ★[BL-580] 잔여 84곳 — 어디부터, 어떻게

**분포(실측)**: `live_signal.py` **34** · `trading.py` 14 · `conditional_entry_janitor.py` 5 ·
`_ws_circuit_breaker.py` 4 · `redlock.py`/`websocket_task.py`/`state_handler.py` 각 3 · 나머지 18.

**권장 순서** — `live_signal.py` 34곳부터. 이번 회차가 그 34곳을 **이름 붙은 헬퍼 안**으로 옮겨
감싸는 핸들러가 docstring 에 적혀 있게 만들었다. 한 회차에 **한 헬퍼 계열**로 끊어라.

**방법(이전 4회차가 확립한 것 — 바꾸지 마라):**

1. 자리마다 **감싸는 핸들러를 코드로 확인**하고, 해악을 (a) 오기록 (b) 조용한 중단 으로 갈라 적는다
2. **고장 주입으로 판정**한다 — 산문으로 「~라서 안전하다」 쓰지 마라(누적 42곳에서 그 산문 **전건 반증**)
3. 주입 판정이 안 되면 **「판정 보류」로 적고 하네스를 짓지 마라**(4회 연속 판별력 0 을 밟았다)
4. 구조적 방어는 `tests/common/test_metric_guard_census.py` 의 AST 동결(**현재 40키 / 84**)

★**census 숫자가 줄면 그만큼 `_FROZEN_CENSUS` 를 낮춰라** — 안 낮추면 다음 회차가 그 자리를 다시 판정한다.

### ★[BL-024] — 사용자 액션이 차단 사유다

실주문 leg(S2~S13)은 **Bybit demo 전용 API 키 2종**이 없어 착수 불가다.
필요: 전용 서브계정(소크 계정과 **분리**) · 잔고 ≥200 USDT · Contract Trade+Read, Withdraw 금지 ·
IP 제한 없음. 배치처 = `backend/.env.local` + repo secret `BYBIT_DEMO_API_KEY_TEST` /
`BYBIT_DEMO_API_SECRET_TEST`. ★`TRADING_ENCRYPTION_KEYS_TEST` 는 **이제 불필요**하다(워크플로 리터럴).
★**착수 전에 적대 검증이 남긴 것 3건을 먼저 봐라** — `_harness.py` 함수 본문의 **93%가 미실행**(F3),
`flatten_one` 이 `submitted`→`filled` 대기 없이 `fetch_open_positions` 를 불러 **거짓 residual** 가능(F12),
감사가 스텝 **순서**·`timeout-minutes` 를 안 본다(F6).

### ★방법론 — 이번 회차가 실측으로 배운 것

- **다중집합 비교는 문장 순서를 구조적으로 못 본다.** codex 가 그 축에서 MAJOR 를 냈다.
  「정규 동치 0」을 「행위 변경 0」으로 갈음하지 마라.
- **재적재의 지문은 `watchfiles` 로그가 아니라 celery 기동 배너**(`Connected to redis`→`mingle`→`ready.`)다.
  `watchfiles` 는 조용하다. md5 일치는 **파일**의 증거이지 **프로세스**의 증거가 아니다.
- **검증 도구를 먼저 적대 검증에 걸어라.** CONTROL 도구가 42건 주입 중 **16건 거짓 음성**이었다
  (가장 큰 것: `except`/`else`/`finally` 구역 site 24개가 감싸는 `try` 를 통째로 잃음).
  > ★**`AGENTS.md` 는 읽지 마라 — 자동 로드된다.** `CONTEXT.md` 는 반대다(읽어야 들어온다).
  > ★★**브랜치 규칙(사용자 확정)** — `stage/engine-position-ssot` 이 통합 브랜치다. **`main`
  > 머지는 검증이 다 끝난 뒤 한 번에** 한다. PR #539 는 **열어 둔다.**

### ★소크는 내려가 있다 (사용자 결정 2026-08-04)

**활성 세션 0 · 거래소 FLAT=YES.** `backend/src` 편집·BE pytest **전면 허용**이다.
다시 굴리기 전에 **§소크 재개 조건**을 먼저 읽어라.

### ★발산 축 = **동결** (재개 조건 명시)

`direction` 관측성 추가([BL-591] 슬라이스 A)를 **하지 않는다.** 근거:

- [BL-589]/[BL-590] 수리 후 **자동 사망 0건** — 방어는 이미 서 있다
- 슬라이스 A 는 **관측 전용**이고 킬 정책을 바꾸지 않는다 ⇒ 방어를 늘리지 않는다
- 치명 갈래(`phantom`)는 post-fix **0건 / 7.24h**(95% 상계 **0.41/h**)

★**동결이지 폐기가 아니다.** 설계·판별식·**20 테스트**·오라클은 전부 레포에 있고
**전사(轉寫)만 남았다** — [BL-591] §슬라이스 설계. **재개 조건 = `phantom` 이 1건이라도
재발**하면 즉시 착수하고 [ADR-023] 긴급도를 되올린다.

★**전향 예측은 창을 닫으며 최종 미판정**이다(문턱 6h 추가를 못 채웠다). ★**누적 기준이라
다음 소크에서 이어 잰다** — 재기동해도 안 잃는다. 판정 도구:
`backend/scripts/classify_direction_divergence.py --log <워커로그>`.

### 본 작업 — [BL-580] 잔여 **84곳**

2026-08-04 에 `_reconcile_conditional_entries` **12곳**을 전건 수리해 census **96 → 84**.
다음 단위 후보는 `_evaluate_session_inner` **21** · `_async_sweep_conditional_entries` **4** ·
`_async_evaluate_all` 2 · `_async_evaluate_session` 2 · `_async_dispatch_pending` 1.
★`_async_dispatch_event` **4곳은 판정 보류 — 손대지 마라.**

★★★**함수 하나를 통째로 한 형태로 취급하지 마라.** 2026-08-04 에 내가 12곳을 전부
「바깥 fail-open `except` 안」으로 적었는데 **기존 회귀 테스트가 반증했다** —
`unrepresentable_key` 는 **안쪽 발주 `except`** 에 잡혀 `conditional_place`(= 발주 실패)로
**오기록**되고 있었다. 직전 회차도 8곳 중 1곳에서 같은 실수를 했다.
⇒ **자리마다 감싸는 핸들러를 확인하고, 해악을 (a) 오기록 / (b) 조용한 중단 으로 갈라 적어라.**

★**주입 판정이 안 되면 「판정 보류」로 적고 하네스를 짓지 마라.** 2026-08-04 에 시도한
주입 2건이 **판별력 0**(하나는 다른 갈래로 샘, 하나는 자체 `except` 에 잡힘)이라 **커밋하지
않고 지웠다.** 구조적 방어는 `tests/common/test_metric_guard_census.py` 의 **AST 동결(84)** 이다.

### 소크 재개 조건 (다시 굴릴 때 읽어라)

★**교착의 원인은 물리 제약이 아니다** — `docker-compose.isolated.yml:29` 가 **작업 트리를
그대로 mount** 하고 watchfiles 로 celery 를 감싼다. 그래서 소크가 살아 있으면 `src` 편집이
워커를 재기동시키고, **중간 상태가 깨져 있으면 워커가 죽는다**(실측: 08-03 16:57
`ModuleNotFoundError` → 16:58 `process already dead`).
⇒ **다시 굴리기 전에 「소크용 `src` 고정 사본 mount + watchfiles 제거」를 먼저 검토해라.**
그러면 편집과 소크가 구조적으로 분리되고 **소크 위생도 좋아진다**(움직이는 트리를 소크하면
「무엇을 검증했는가」가 불명확하다).

★**BE pytest 는 소크 중에도 안전하다**(2026-08-04 실증) — `_test_engine` 은 autouse 가
아니고 대상이 `quantbridge_test` 다. 위험한 것은 **`DATABASE_URL` 단독 주입**뿐이다.
★**「1주 안정 운영」([BL-003] 게이트)은 아직 멀다** — 역대 최장 **15.3h = 9%**.
★**소크 전후로 거래소를 flat 으로 맞춰라** — `live_session_admin.py` **`stop` → `flatten`**.

### 비목표

[BL-591] 슬라이스 A(동결) · 슬라이스 B · [ADR-023] 구현(Proposed 보류) ·
슬라이스 2([ADR-022] 재개 조건 미충족) · [BL-592] 수리 · [BL-578] · mainnet.

## ⛔ 종료 — **[ADR-023] 슬라이스 설계 회차** (완료 · 참고자료)

> ★**진입점은 여기가 아니라 위 블록이다.** 이 절의 내용은 전부 다른 곳으로 승격됐다 —
> 남겨두면 다음 사람이 낡은 예측을 현행으로 읽는다.

- **표적 = `direction`** 으로 옮긴 근거(`engine_only` **157배 감소**, 18.8/h → 0.12/h) →
  [ADR-023 §분해 완료](decisions/023-engine-state-ssot.md). **`engine_only` 는 다시 캐지 마라.**
- **그 회차의 사전등록 예측** → 2026-08-04 3차에서 **미판정**으로 닫혔다(노출 1.40h, 문턱 5h/2h
  미달). 경위는 [dev-log §1](dev-log/2026-08-04-direction-channel-decomposition.md).
- **「반전 tick 에서 거래소가 못 따라오는 구간」이라는 물음** → 3차가 답했다. 그 전제는 채널의
  **4/11 에만** 해당한다 — [ADR-023 §재분해](decisions/023-engine-state-ssot.md).
- **「이 개편을 할 것인가」 사용자 판정** → **보류**(라벨 분해 먼저). 위 블록 참조.

## ⛔ 종료 — **engine-position-ssot 슬라이스 1** (완료 · 참고자료)

> ★**진입점은 여기가 아니라 위 블록이다.** 상세는
> [dev-log](dev-log/2026-08-04-engine-position-ssot.md) · [ADR-022](decisions/022-engine-position-ssot.md).

### 무엇을 했나

- **슬라이스 1(계측) = PR #539 OPEN** — `trading/ledger_position.py` 신설(원장 → 열린 포지션 유도, 순수 함수) +
  `run_live` **직전**에서 계산만 하고 counter·tick jsonb 에 기록. 판정·발주 경로 무변경.
  부수로 `backend/scripts/live_session_admin.py`(운영자 청산 도구, [BL-593] 구멍을 닫는다).
  ★**「동작 변경 0」이 아니다** — 거래소 조회가 tick 당 **2회**가 된다.
- **수확과 판정** — ④ = 0 ⇒ **슬라이스 2 미착수 확정**(사전등록 V1). 그리고 **net 은 맞고 legs 는
  틀리다**는 더 큰 발견.

### 수확표 — 창과 n 을 지우지 마라

| #   | 지표                          | 실측                               | 창 / n                        |
| --- | ----------------------------- | ---------------------------------- | ----------------------------- |
| ①   | 주입 가능 tick 수             | 9/19 — ★**라벨이 과대계상**(아래)  | 19 tick — **판별력 없음**     |
| ②   | veto 발동률                   | 1/19 = 5.3%                        | 19 tick — **판별력 없음**     |
| ③   | veto 해소 tick 분포           | `bucket="1"` **1건**               | n=1 — **상한 계수 근거 없음** |
| ④   | `exchange_only` → `direction` | **0** (최악 상계 ≤1/21)            | 스냅샷 17.06h + 로그 38h      |
| ⑤   | 유도 판정 불가 비율           | **27.6%**(세션) / 63.6%(발산 사건) | 과거 **29세션** 재생          |

★**①의 라벨은 「주입 가능」을 세지 못한다** — `veto_total{agree,engine_flat="true"}` 는 원장도
거래소도 flat 인 무의미 tick 을 포함한다(실측 9건 전부 `no_fills`). 실제로 값이 들어가는 tick 은
**원장 non-flat + 엔진 flat + agree** 인데 그 교차는 현재 counter 로 못 센다.

★**소크 19 tick 짜리 ①②③⑤ 를 「측정했다」로 읽지 마라.** ⑤는 같은 19 tick 에서 **0/19** 였고
과거 29세션에서 **27.6%** 였다 — **작은 창의 0 은 0 이 아니다.**

### 증명한 것과 못 한 것 (합쳐 말하지 마라)

| 층                   | 무엇이 증명하나                  | 결과                          |
| -------------------- | -------------------------------- | ----------------------------- |
| ④ 모집단·부검        | 스냅샷 차분 17h + 워커 로그 38h  | ④ = 0 · 최악 상계 ≤1/21       |
| ⑤ 판정 불가율        | 과거 29세션 재생 (**같은 함수**) | 27.6% — ★정확성은 검증 안 됨  |
| 유도 함수 **정확성** | 외부 오라클 11건(거래소 실측)    | **오답 0** · **legs 는 틀림** |
| ①②③                  | 이 소크 19 tick                  | ★**미측정과 같다**            |

### 이번 회차 인계 (2026-08-04 engine-position-ssot)

- **소크가 돌고 있다** — 세션 `bbea6da4` · T0 `2026-08-04T02:54:15Z`. 앵커는 `.soak/session`.
  회차 내내 생존했고 **`src` 편집 0 · 변이 0 · BE pytest 0** 이었다.
- 게이트 baseline: BE **3993 / 46 skipped** · ruff 0 · mypy 0 (**216**) · bl-audit active **154** ·
  마이그레이션 head `20260801_0001`. ★이번 회차는 코드 diff 0 이라 BE pytest 를 **돌리지 않았다**
  (소크 중 `drop_all` 위험). 숫자는 PR #539 의 CI 통과값이다.
- ★**`ruff format --check` 는 게이트가 아니다** — 레포 695 파일 중 **393 파일이 미정렬**이고
  집행자는 `lint-staged`(스테이징된 파일만)다. 커밋할 파일이 이미 미정렬이면 훅이 무관한 줄까지
  건드리니 **미리 적용해 diff 에 드러내라.**
- 회고 재생·오라클 스크립트는 scratchpad 에만 있다(레포 미등재). **방법은 dev-log §4 에 있다** —
  원장 + 워커 로그만 쓰므로 인증이 필요 없다.
- **[BL-581] 이 소크 창의 상한이 됐다** — `.metrics` **14,905/20,000 파일** · **+175 파일/h** ⇒
  약 **29시간** 뒤 Trigger. 스크레이프 **2.67초**.

---

## 📌 소크 운영 상비 참조 (창이 도는 동안 계속 유효)

> 아래는 특정 회차가 아니라 **소크를 굴릴 때마다 다시 밟는 함정**들이다. 회차별 숫자는
> dev-log 로 갔다 — 여기에 낡은 T0/baseline 을 남겨두면 다음 사람이 죽은 세션을 현행으로 읽는다
> (2026-08-03 실측 사고: 이 절이 이미 죽은 세션의 창 종료 시각을 가리키고 있었다).
> ★**`AGENTS.md` 는 읽지 마라 — 자동 로드된다.** `CONTEXT.md`·`.ai/rules/*.md` 는 반대다(읽어야 들어온다).

### 판정 지표가 그 창에서 **발화 가능한지 먼저 계산해라**

두 회차 연속 같은 계산이 필요했다. 2026-08-03 오전 `close_position_flat` 은 회차마다 고쳐져
**07-28 15건 → 07-29 3건 → 07-30 1건 → 07-31 0건** 으로 감소 중이었고 30분 기대값이 ≈**0.02건**
이었다 — 기다려서는 못 잰다. 같은 날 오후 `position_divergence` 사망은 **전 이력 25세션 중 1건**
이라 「N분 무사고」가 아무 증거도 아니었다.

⇒ **발화 안 하면 창을 늘리는 게 아니라 (a) 발화 조건을 만들거나 (b) 구현과 독립된 오라클로 과거
원장을 재생한다.** 둘 다 실제로 통했다(전자 = H8 유도 주입, 후자 = BL-589 재생 오라클 29건).

### 증명한 것과 못 한 것을 **합쳐 말하지 마라**

프로덕션 유도는 분기의 **도달·종결**만 증명한다. 계측 실패 봉쇄 같은 것은 **오프라인 결정론
테스트**가 증명하며, 프로덕션에서 유도하려면 multiproc 디렉터리를 망가뜨려야 해서 소크 중 금지다.
층을 나눠 표로 적어라 — 한 줄로 합치면 다음 사람이 「검증 완료」로 읽는다.

### ★착수 전 반드시 읽을 것

1. ★★★**데스크 회차가 반증하는 것은 「내가 적은 산문」이고, 소크가 반증하는 것은 「코드가
   실제로 하는 일」이다.** 재가동 직전 5회차는 전자만 했다. 계측 부채는 무한(96곳)하고
   오프라인에서 검증 가능하지만 소크는 느리고 위험하다 — 그래서 **이 루프는 자기 지속된다.**
2. ★★**`roadmap.md` 가 2026-07-26 에 스스로 세운 규칙** — 「이후 스프린트는 **전부 실주행
   dogfood 를 포함**한다」.
3. ★★**소크 전후로 거래소를 flat 으로 맞춰라.** 세션 `DELETE` 204 는 **아무것도 flat 하지
   않는다**(0.03 포지션 + 조건부 1건 잔존 전례). T0 직전엔 `FLAT=YES` 확인했다.
4. ★★**호스트 `/metrics` 는 워커 증가를 몇 초 늦게 비춘다**(T0 실측 — 호스트 14, 같은 시각
   컨테이너 15). **이벤트 직후 읽기로 판정하지 마라.** 하루 1회 관측엔 영향 없다.
5. ★**`idle` 은 완료가 아니다** · **Clerk JWT 는 60초** · **`:3000` 은 다른 앱(Kairos)** ·
   API 는 `:8100`, DB 는 `:5433`(격리 스택).
6. ★★**게이트를 파이프에 넣지 마라** · **`cd backend && set -a; . ./.env.local` 금지**(아래 참조).
7. ★**세션 등재는 HTTP 로 헤드리스 불가**(Clerk 가 `azp` 를 요구). 서비스 계층 직접 호출이
   유일한 길이다(`backend/scripts/seed_dogfood.py:11-19` 선례). **손 INSERT 는 금지** —
   `equity_baseline_usdt` 를 건너뛰어 첫 tick 에 자동 비활성화된다.

### 현행 소크 눈금 (숫자는 「이번 회차 인계」에 있다)

★**counter 절대값을 비교하지 마라 — 출생일이 다르다.** 원본 스냅샷은 `.soak/snap-*.txt` 에 있고
**차분은 거기서 뜬다**(`soak-observe.sh` §4 가 자동으로 한다). 상시 확인 대상:
`qb_metrics_mutation_failed_total`([BL-580] Trigger, 아직 실측 0) ·
`/metrics` 파일 수([BL-581] Trigger 20000 — ★**소크 창의 상한이 아니다**, 아래 정정) ·
★**[BL-589] 수리 관측축 정정(2026-08-04)** — 종전의 「`breach_with_resting` 이 증가할 때
`market_converted` 동시 증가」는 **코드상 구조적으로 성립 불가**다. `conditional_entry_planner.py:447`
이 `breached and (resting_could_have_fired or not allow_market_conversion)` 일 때만 그 갈래를 타므로
**같은 leg 에서 둘이 함께 오를 수 없다.** 볼 것은 counter 가 아니라 **`live_conditional_plan_drop`
로그의 `resting_could_have_fired`** 다 — **`false`** 인 건이 [BL-589] 결함 형태이고, `true` 면
「발화 가능한 대기 주문이 정당하게 막았다」라 **전환하지 않는 것이 옳다**(실측 `03:03:14` 건은
`true` 였고 그 대기 주문이 **57초 뒤 실제 체결**됐다 — 전환했으면 이중 진입이었다) ·
`qb_live_conditional_guard_total{recovery_placed}`([BL-590] 수리 관측축 — 증가하면 그 시점
원장에 `condmkt` 주문이 짝으로 있는지 확인해라. `recovery_expired` 가 증가하면 **브로커 적체**다) ·
`qb_live_ledger_derive_total` / `qb_live_ledger_veto_total` / `qb_live_ledger_hold_resolved_total`
([BL-591] 슬라이스 1 계측 — ★`derive_total` 이 **증가 중**인지가 「계측이 돌고 있다」의 유일한 증거다.
「코드가 mount 됐다」와 다르다. 교차 확인은
`live_signal_states.last_strategy_state_report._qb_ledger_shadow` 의 `updated_at`.
★**`derive_total{duplicate_open}` 이 오르기 시작하면 그 세션의 계측은 끝난 것이다** — 흡수
상태라 되돌아오지 않는다) ·
마이그레이션 head `20260801_0001`.

★**`qb_live_conditional_reconcile_errors_total{stage="terminal_write_back_*"}` 는 에러가 아니다**
(2026-08-04 판정). `live_signal.py:1310` 이 `f"terminal_write_back_{won}"` 로 라벨을 만드는데 `won` 은
**전이 경합에서 이겼을 때의 terminal 상태명**이다(`:958` docstring) — 즉 **[BL-560] 수리가 성공한
횟수**가 "reconciliation failures" counter 에 계상된다. 소비자는 전부 `stage` 라벨 단위라 자동
판정은 안 깨지고 피해는 **사람의 오독**이다. 상세는 [BL-566] 계열. **차분에서 보이면 무시해라.**

★**[BL-581] 은 소크 창의 상한이 아니다**(2026-08-04 정정). 워커 커맨드가
`uv run watchfiles --filter python celery … /app/src` 이고 `/metrics` 파일은 **PID 당** 생기므로,
증가 드라이버는 **`backend/src` 편집으로 인한 워커 재기동**이다. 실측: 편집 세션 시간대 **~600/h**
(08-03 08시 584 · 17시 829 · 08-04 01시 595) vs **조용한 소크 시간대 ~4–5/h**(08-04 00시 4개 ·
최근 90분 5개 = 워커 자식 1회 재활용). 남은 5,091 파일 기준 **약 42일**이다. ⇒ 상한은 소크 시간이
아니라 **개발 재기동 예산**이다.

> ★★**`cd backend && set -a; . ./.env.local; set +a` 를 쓰지 마라.** 이미 `backend` 에 있으면
> `cd` 가 실패해 **`set -a` 만 건너뛰고** 나머지는 `;` 로 계속 실행된다 — env 가 export 되지
> 않은 채 pytest 가 5432 로 붙어 `InvalidPasswordError` **대량 거짓 red**.
> **`QB=…; set -a; . $QB/backend/.env.local; set +a; cd $QB/backend`** 로 써라.
> ★**브랜치 접두사는 `stage/`** · `QB_PRE_PUSH_BYPASS=1` 금지.
> ★**pre-commit 이 `ruff format`·`prettier --write` 를 돌린다** — **커밋 후 게이트를 다시 재라**.
> ★**표적 변이는 CONTROL 이 직접 집행**(`git checkout` 금지, sha256 복원 대조). 치환 문자열이
> 다른 함수와 겹치는지 **먼저 세라**.

### 보류 — [BL-580] 잔여 96곳 (P2, 재개 조건 명시)

방법은 검증됐다(주입 판정 **42/42 전건 유해**). 다만 **Trigger 가 실측 0** 이라 P0 보다 뒤다.
재개하면 다음 단위는 **`_reconcile_conditional_entries` 12곳** — 그 함수의 바깥 `except` 가
fail-open(예외를 `stage="reconcile"` 로 계상하고 정상과 똑같이 `None` 반환)이라 **H8 조건이
함수 전체 규모로** 있다. 그 외 잔여: `_evaluate_session_inner` 21 ·
`_async_sweep_conditional_entries` 4 · `_async_dispatch_event` **4(판정 보류 — 손대지 마라)** ·
`_async_evaluate_all` 2 · `_async_evaluate_session` 2 · `_async_dispatch_pending` 1.
★**판정 라벨은 누적 8종** — H1~H7 + **H8**(fail-open `except` 가 삼켜 거절이 집행으로 뒤집힌다).
★**도달 경로를 못 적으면 「판정 보류」다 — 하네스를 만들지 마라.**

## 완료 이력

- 직전 회차 — [`direction-channel-decomposition`](dev-log/2026-08-04-direction-channel-decomposition.md)
  (**`backend/src` 0줄 · 소크 무중단 · 오라클 1파일**. ★★★**`direction` 은 두 현상이었다** —
  무해 `replay_lag` **7**(조건부가 봉 중간에 체결되고 **엔진이** 못 따라온다) : 치명 `phantom`
  **4**(엔진 시뮬이 체결로 친 주문이 거래소에 없다). 체결 경과 **24.7초 vs 909초**로 **37배
  벌어져 겹침 0**, 사망 **2/2** 가 후자, 산술도 닫힌다(11 = `transient` +9 + 킬 2).
  ⇒ **스프린트가 물으라던 「거래소가 못 따라오는 구간」은 4/11 뿐이다.**
  ★★★**[ADR-023] 의 「≈0.5/h」가 두 번 정정됐다** — ⑴ 다수가 무해 ⑵ **벽시계 rate**(노출 기준
  1.27/h). 같은 문서가 `engine_only` 는 노출로 재라고 요구하면서 `direction` 만 벽시계로 쟀다.
  ★★★**판별식이 한쪽으로만 틀린다** — `Order.filled_at` 이 우리 관측시각이라 `phantom` 을
  **과소계상**할 뿐이라서 **`phantom` 즉시 킬이 거짓 사망을 만들지 않는다**(슬라이스 B 근거).
  ★★**적합은 검증이 아니다** — 판별식을 그 11건에서 유도했으므로 독립적인 것은 **사망 상관 2/2**
  하나뿐. ★★**있는 계측이 죽어 있었다** — 슬라이스 1 shadow 가 흡수 상태(`duplicate_open` 155)라
  판별기로 못 쓴다. ★**신규 잠재 결함 2건**(D1 strike TTL 부재 · D2 시장가 반전이 발주 전 strike
  를 연다 — [BL-590] 복구가 그 가드에게 60초를 받는다). ★**내 계측기 2번 오류**(발산 시각을 초로
  잘라 갈래가 바뀜 · `2>&1` 을 리다이렉트 앞에 씀))
- 그 앞 — [`engine-state-ssot`](dev-log/2026-08-04-engine-state-ssot.md)
  (**[ADR-023] Proposed 신설 · 코드 0줄 · 소크 무중단**. ★★★**사망 경로의 축이 바뀐다** — ④=0 은
  주입 절반을 막았고, 이번에 **veto 절반까지** 막혔다: 유도가 **흡수 상태**라 사망 2건 모두 이미
  어두운 뒤 죽었고(`a201a47b` 17.3분→104.9분 · `04097fdc` 26.1분→65.0분), veto 는
  **원장==거래소·엔진만 거짓말**인 사망 경로에서 발화하지 않으며, 방향도 반대다(`engine_only` 314
  vs `exchange_only` 21). ★★★**선행연구가 우리 기각 3건을 순환으로 판정** — NautilusTrader 는
  「reconciliation 은 라이브 전용」이라 엔진을 포크할 필요가 없고, 합성 주문은 **꼬리표**로 격리하며,
  우리가 죽이는 `direction` 을 **Position side flip** 으로 이름 붙여 조정 주문을 낸다. 우리
  `duplicate_open` 의 해법(**zero-crossing 생애주기**)도 문서화돼 있다. ★★**Trust Layer 23 테스트가
  `run_live` 를 0회 호출** ⇒ 라이브가 갈라져도 CI 는 구조적으로 green. ★★**새 위험 R1 — replay 가
  우연히 float 오차 청소부였다.** ★사전등록 예측 **적중** · 관측 2건 판정(`breach_with_resting` 은
  정상이고 확인식이 구조적 불가 · `terminal_write_back_*` 는 **성공인데 errors counter**))
- 그 앞 — [`engine-position-ssot`](dev-log/2026-08-04-engine-position-ssot.md)
  (슬라이스 1(계측) **PR #539 OPEN** · **슬라이스 2 미착수 확정**. ★★★**계측이 초록인데 주입될
  값이 틀렸다** — 유도 함수의 **net 은 맞고 legs 는 틀리다**(외부 오라클 11건: 오답 0, 적중 4가
  3건이 `legs=2` 인데 거래소는 단일 포지션 — 나머지 1건은 반전 없는 먼지 세션이라 정확했다).
  슬라이스 1 은 net 으로 `agree` 를 판정하고 슬라이스 2 는
  legs 를 주입한다. ★★★**④ = 0** — 사망 2건의 상류에 `exchange_only` 0건, 최악 상계 ≤1/21.
  사망 경로는 **반전**이고 반전은 tick 경계에서 flat 을 거치지 않는다. ★★**작은 창의 0 은 0 이
  아니다** — ⑤가 소크 19 tick 에서 0/19, 과거 29세션에서 **27.6%**. ★`trade_id` 는 trade 가 아니라
  Pine 진입 규칙 이름이고 **반전은 `:close:` 키를 만들지 않는다**)
- 그 앞 — [`breach-rejection-recovery`](dev-log/2026-08-03-breach-rejection-recovery.md)
  ([BL-590] **Resolved**. ★★★**가드가 뚫린 게 아니라 거절 뒤 복구가 없었다** — 계획기는
  발주 시각에 옳았고(카운터 차분이 연역 증명) 거래소가 2.1초 뒤 자기 시각으로 거절했다.
  ★★**이 클래스는 `110093` 단독이 아니다** — 거울 코드 `110092` 가 원장 4건 중 2건.
  ★★**격리 실행이 거짓말했다** — 두 파일만 돌리면 24 passed 인데 전체 스위트는 8 failed
  (내 fixture 가 시각을 **모듈 import 시점**에 고정). ★★**두 안전한 것이 합쳐져 결함이 됐다**
  — codex 가 「flake 아님」으로 판정한 값이 내가 만료 가드를 넣으면서 load-bearing 이 됐다.
  ★변이 **8/8** · 유도 주입으로 프로덕션 발화 확인)
- 그 앞 — [`soak-divergence-root`](dev-log/2026-08-03-soak-divergence-root.md)
  ([BL-589] **Resolved**. ★★★**엔진은 취소를 못 본 게 아니라 주문을 아예 모른다** — 포지션 출처가
  `run_live` 시뮬이라 「되돌리는 경로」가 애초에 없다. 뿌리는 계획기가 「대기 주문이 있다」만으로
  시장가 전환을 껐다는 것이고 **그 주문은 발화 불가**였다. ★★**한 번에 둘을 고치면 서로의 증거를
  가린다** — 술어만 먼저 넣으니 눈금 붕괴 구멍이 독립 red 로 남았다. ★★**boolean 판정을 피한
  대체 술어도 검증 대상**(`deactivated_reason` 이 25건 중 12건에서 거짓말))
- 그 앞 — [`metric-guard-residual-sweep`](dev-log/2026-08-03-metric-guard-residual-sweep.md)
  (발주 outbox **12곳** 판정 — **수리함 8 · 판정 보류 4**, census 104→96.
  ★★★**같은 함수·같은 metric·전부 「commit 뒤」인데 한 자리만 fail-open `try` 안**이라 계측
  실패가 **거절을 집행으로 뒤집었다** — 거래소가 flat 이라 거부한 청산에 실주문이 나갔다(신규
  라벨 **H8**). ★변이 M4 가 코드가 아니라 **오라클 구멍**을 드러냄(1578건 판별력 0) → 5종으로
  확장. **BL-584 현재 코퍼스 도달 불가 확정**)
- 그 앞 — [`metric-guard-residual-close`](dev-log/2026-08-03-metric-guard-residual-close.md)
  (BL-580 잔여 **25곳** 판정 — **수리함 23 · 판정 보류 2**, census 129→104.
  ★**산문 2줄이 25곳을 잘못 뺐다** — 「blast radius 0」은 10/10 이 도메인 예외 대신 OSError 를
  탈출시켰고, 「already_synced 수렴」은 7곳 중 1곳만 성립. ★**반쪽 수리는 사이트 주입 29건을
  전부 통과**한다(변이 M5). 신규 **BL-584**)
- 그 앞 — [`gate-trustworthiness`](dev-log/2026-08-03-gate-trustworthiness.md)
  (「전부 통과」를 증거로 만든다. ★**순서는 랜덤이 아니었다** — `pytest-randomly` 미설치로
  `-p no:randomly` 는 no-op, 흔들린 것은 **수집 집합**이다. 뿌리 = 정의 모듈 패치 창의 첫 적재가
  가짜를 **모듈 전역으로 영구 복사**. 오염원 4곳(전역 8개) 처분 + 상시 가드. **BL-583 Resolved**)
- 그 앞 — [`metric-guard-residual`](dev-log/2026-08-03-metric-guard-residual.md)
  (「감쌀 필요 없다」의 근거를 고장 주입으로 재판정 — 명시 4곳 **전건 반증**, 12곳 수리 ·
  census 141→129. **BL-582 「7종 도달 불가」→5종**. 신규 **BL-583** = 스위트 순서 의존)
- 그 앞 — [`metric-guard-parity`](dev-log/2026-08-02-metric-guard-parity.md)
  (계측 실패가 성공한 발주를 실패로 기록하고 **주문을 하나 더 냈다**. 가드 18곳 · census 159→141)
- 그 앞 — [`context-budget-repair`](dev-log/2026-08-02-context-budget-repair.md)
  (문서·계측만. `INDEX.md` **−92.3%** · 자동 로드 고정비 **−42.2%** · 줄길이 게이트 신설.
  ★**착수 전제 3건 반증** — `CONTEXT.md`·`.ai/rules` 는 자동 로드가 아니다)
- 그 앞 — [`canonical-measurement-surface`](dev-log/2026-08-02-canonical-measurement-surface.md)
- 그 앞 — [`divergence-label-split`](dev-log/2026-08-02-divergence-label-split.md)
- 이번 주 완료 스프린트와 이전 회고 — [`dev-log/INDEX.md`](dev-log/INDEX.md)
- 2026-07-26 이전 status 원문 — [`archive/status-history.md`](archive/status-history.md)
- 열린 BL의 현재 상태 — [`backlog.md`](backlog.md) (`scripts/bl-audit.sh`가 정본)
