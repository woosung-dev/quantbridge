# QuantBridge — Status

> **업데이트:** 2026-08-03
> **활성 Sprint:** 없음. 다음 작업은 아래 「다음 스프린트」 블록만 읽는다.
> **준비 브랜치:** `stage/metric-guard-residual-sweep` — **PR #532 OPEN**(BL-580 발주 outbox 8곳 수리 · census 104→96).
> **최근 머지:** `stage/metric-guard-residual-close` → `main` (**PR #530** @ `6b7e1271`, 2026-08-03).

---

## 🎯 다음 스프린트 — **demo-soak-restart** (데모 시계 재가동 · P0 [BL-003] 유일 진입로)

> ★**이것이 다음 세션의 유일한 진입점이다.** 별도 킥오프 파일을 만들지 않는다.
> 시작 방법: **"다음 스프린트 진행해줘"**. `CONTEXT.md` + 본 파일을 읽고 시작한다.
> ★**`AGENTS.md` 는 읽지 마라 — 자동 로드된다.** `CONTEXT.md`·`.ai/rules/*.md` 는 반대다(읽어야 들어온다).

**목표·왜 지금.** ★**데모 운영 시계가 멈춰 있다.** 일별 주문이
`07-30: 86 · 07-31: 53 · 08-01: 5 · 08-02: 3 · 08-03: 0` 이고 마지막 라이브 신호 이벤트는
**07-31** 이다. **P0 [BL-003] — 실자금 cutover — 의 Trigger 는 「Bybit Demo 1주 안정 운영 후」** 이고,
그 시계를 다시 돌리는 것 말고 P0 를 여는 방법은 없다.

★**그동안 머지된 5개 PR(#523·#525·#528·#530·#532)은 실주행 검증이 0이다.** 오늘 고친 **H8**
(계측 실패가 fail-open `except` 에 삼켜져 flat 청산 거부를 발주로 뒤집는다)의 그 분기는
프로덕션에서 **14회 발화**한 자리인데, 수리 후 한 번도 안 돌려봤다.

★**소크는 백로그를 닫으러 가는 게 아니다.** 실측: 「실주행으로만 닫히는」 미해결 BL 은
**2건뿐**([BL-516]·[BL-573])이다. 소크의 값어치는 (a) **P0 시계**, (b) **미검증 5PR 의 검증**,
(c) 이 레포에서 소크가 데스크 결론을 뒤집은 전례 — 07-30 소크가 **단위테스트를** 반증했고
07-31 실주행이 **코드 대조 뿌리 가설을** 반증했다.

**비목표** — [BL-580] 잔여 96곳(P2, Trigger `qb_metrics_mutation_failed_total` **실측 0** — 한 번도
안 올랐다) · 새 기능 · 마이그레이션.

### 재가동 전제 — 이미 다 갖춰져 있다 (2026-08-03 실측)

인프라 전량 가동(`worker`·`beat`·`ws-stream`·`db`·`redis`) · Bybit **demo** 계정 **2개** ·
활성 세션 **0** · settings 유효 전략 **2건**. ⇒ **세션 등재 한 번**이면 시계가 다시 돈다.
마지막 조합 = 전략 `07a22564` + 계정 `19a8166a` + `BTC/USDT`.

### 첫 step

1. **세션을 먼저 올려라 — 코드를 읽기 전에.** 시계가 도는 동안 나머지를 한다. 이 회차의
   실패 모드는 「분석하다가 또 안 돌리는 것」이다.
2. **재가동 직후 30분 안에 H8 수리를 확인해라** — `qb_live_signal_dispatch_total{action="close",
outcome="close_position_flat"}`(현재 **14**)의 **창 차분**을 보고, 그 tick 에 실주문이
   나가지 않았는지 `trading.orders` 로 대조한다. ★절대값 말고 차분이다.
3. **소크 창을 최소 48시간 잡아라** — [BL-578] 잔여 거절이 **1건/2일**이라 그보다 짧으면
   구조적으로 못 잰다(직전 회차들이 「4일에 1회」를 창 길이로 못 이긴 전례가 있다).
4. **매일 한 번 원장 대조**(주문 수 · `live_signal_events` 상태 분포 · reconcile_errors stage별
   창 차분). 이상이 없으면 **아무것도 고치지 마라** — 시계를 세우는 게 더 비싸다.
5. **1주 무사고면 [BL-003] Trigger 가 열린다.** 그때 mainnet runbook 을 착수 후보로 올린다.

### ★착수 전 반드시 읽을 것

1. ★★★**데스크 회차가 반증하는 것은 「내가 적은 산문」이고, 소크가 반증하는 것은 「코드가
   실제로 하는 일」이다.** 최근 5회차는 전자만 했다. 계측 부채는 무한(96곳)하고 오프라인에서
   검증 가능하지만 소크는 느리고 위험하다 — 그래서 **이 루프는 자기 지속된다.** 의식적으로 끊어라.
2. ★★**`roadmap.md` 가 2026-07-26 에 스스로 세운 규칙** — 「이후 스프린트는 **전부 실주행
   dogfood 를 포함**한다」. 최근 5회차가 이 규칙을 지키지 않았다.
3. ★★**소크 전후로 거래소를 flat 으로 맞춰라**(직전 소크 회차 교훈).
4. ★**`idle` 은 완료가 아니다** · **Clerk JWT 는 60초** · **`:3000` 은 다른 앱(Kairos)** 이다.
5. ★★**게이트를 파이프에 넣지 마라** · **`cd backend && set -a; . ./.env.local` 금지**(아래 참조).

### baseline (2026-08-03 실측 — PR #532 커밋 후)

**BE 3893 passed / 46 skipped** · **FE 1242**(205 파일) · ruff clean · mypy **214** clean ·
마이그레이션 head **`20260801_0001`** · 가드 밖 mutation **96** ·
`/metrics` **12459 파일 · 771MB**(BL-581 Trigger 20000 미달) ·
**`qb_metrics_mutation_failed_total` = 0**(BL-580 Trigger 미발화) ·
`qb_live_signal_dispatch_total{close,close_position_flat}` = **14**(H8 분기 실발화 누계).
★**이 숫자도 대조 대상이다. 첫 step 에서 지금 HEAD 로 다시 재라.**

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

- 직전 회차 — [`metric-guard-residual-sweep`](dev-log/2026-08-03-metric-guard-residual-sweep.md)
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
