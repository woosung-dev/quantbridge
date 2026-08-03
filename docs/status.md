# QuantBridge — Status

> **업데이트:** 2026-08-03
> **활성 Sprint:** 없음. 다음 작업은 아래 「다음 스프린트」 블록만 읽는다.
> **준비 브랜치:** `stage/metric-guard-residual-sweep` — **PR 대기**(BL-580 발주 outbox 8곳 수리).
> **최근 머지:** `stage/metric-guard-residual-close` → `main` (**PR #530** @ `6b7e1271`, 2026-08-03).

---

## 🎯 다음 스프린트 — **metric-guard-reconcile-sweep** ([BL-580] 잔여 96곳, `_reconcile_conditional_entries` 12곳)

> ★**이것이 다음 세션의 유일한 진입점이다.** 별도 킥오프 파일을 만들지 않는다.
> 시작 방법: **"다음 스프린트 진행해줘"**. `CONTEXT.md` + 본 파일을 읽고 시작한다.
> ★**`AGENTS.md` 는 읽지 마라 — 자동 로드된다**(`CLAUDE.md` 가 `@AGENTS.md` 하나만 import 한다).
> ★**`CONTEXT.md` 는 반대다 — 자동 로드가 아니라서 읽어야 들어온다.** `.ai/rules/*.md` 도 마찬가지다.
> ★**`docs/dev-log/INDEX.md` 를 통째로 grep 하지 마라** — `## 최근 12회차` 상단만 읽는다.

**목표·왜 지금.** 계측 실패가 머니-패스를 오기록하는 자리가 **96곳** 남았다([BL-580]).
누적 42곳을 주입으로 판정해 **「가드 없이 유지」가 0곳**이다. 산문 근거의 타율은 여전히 0이므로
**잔여도 분류하지 말고 주입으로 시작한다.**
**비목표** — census 키 구조 변경 · [BL-581] Trigger 20000 미달 · [BL-584] 도달 불가 확정 · soak.

**작업 단위.** `tasks/live_signal.py` 46곳(전체의 48%). 함수별로는
`_evaluate_session_inner` 21 · **`_reconcile_conditional_entries` 12** ·
`_async_sweep_conditional_entries` 4 · `_async_dispatch_event` **4(판정 보류 — 손대지 마라)** ·
`_async_evaluate_all` 2 · `_async_evaluate_session` 2 · `_async_dispatch_pending` 1.

★**다음은 `_reconcile_conditional_entries` 12곳을 권한다.** 이번 회차가 찾은 **H8**(fail-open
`except` 가 계측 예외를 삼켜 거절을 집행으로 뒤집는다)의 조건이 이 함수에 **함수 전체 규모로**
있다 — 바깥 `except` 가 예외를 `stage="reconcile"` 로 계상하고 로그만 남긴 뒤 **정상과 똑같이
`None` 을 반환**한다(주입 정본 파일 상단이 이미 적어 뒀다). 12곳은 이번 회차와 같은 크기다.

### 첫 step

1. **baseline 재측정** (`global.md` §7.1). 대조값은 아래 블록. ★**`-p no:randomly` 를 쓰지 마라 —
   randomizer 가 없어 no-op 이다.** 「두 번 재라」는 **수집 집합을 바꿔 재라**는 뜻이다.
2. ★★★**「commit 뒤인가」가 아니라 「어느 `try` 안인가」를 봐라.** 이번 회차가 12곳을
   「전부 commit 뒤라 같은 형태」로 요약했고 **8곳 중 1곳에서 그 요약이 틀렸다.** 사이트마다
   **바깥 `except` 가 무엇을 하는지**를 도달 경로와 함께 한 줄로 적어라.
3. **주입 관용구를 그대로 복제해라** — `.inc` 가 아니라 **`.labels` 를 폭파**(`OSError("mmap allocation failed")`), **라벨 단위**로. **stub 정확히 1회 호출 단언**(`assert calls == [{...}]`) 과 **사이트별 비-계측 postcondition** 둘 다. 정본 5파일은 아래 baseline 블록 참조.
4. **판정 라벨은 누적 8종이다** — H1~H7(직전 정의 그대로) + **H8**(fail-open `except` 가 계측
   예외를 삼켜 **거절이 집행으로 뒤집힌다**). **H3 은 세 회차 연속 공허**다.
5. **도달 경로를 못 적으면 「판정 보류」다 — 하네스를 만들지 마라.** 만들면 프로덕션이 못
   만드는 상태를 손조립해 「실측 유해」로 적게 된다([BL-582] 함정의 거울상).
6. **[BL-582]** 반증된 2종은 전략 등록이 선행돼야 한다. ★`degraded_input` 은 **영구 제외**.
7. **[BL-581]** `/metrics` **12459 파일 · 771MB**. Trigger 20000 미달이라 착수하지 않는다.

### ★착수 전 반드시 읽을 것 (직전 회차가 실제로 밟은 것)

1. ★★★**같은 함수 · 같은 metric · 같은 「commit 뒤」인데 귀결의 *종류*가 달랐다.** `:3133` 만
   fail-open `try` 안이라, 계측 예외를 `except Exception` 이 「포지션 조회 실패」로 오인해
   삼키고 `return` 을 건너뛴 채 **그대로 발주한다**. `failed` 로 커밋된 이벤트에 **실주문이
   나간다** — 오기록이 아니라 **원장 분기**다. 내 구조 요약이 바로 그 산문이었다.
2. ★★★**변이의 판별력이 0 이면 「테스트를 넓힌다」도 후보다.** M4(무재시도 튜플에서
   `KillSwitchActive` 제거)가 `tests/tasks`+`tests/trading` **1578건 전부 green** 이었다.
   원인은 변이 설계가 아니라 **오라클이 결정론적 거절 5종 중 1종만 구동**한 것이었다.
   ⇒ 수리(D8·D9)가 기대는 대상이라 오라클을 5종 전체로 넓혔다.
3. ★★**사이트 주입은 증분 소실을 못 본다.** 변이 M2(`.inc()` 제거)에서 주입 8건이 **전부
   green** 이다. 유일한 방벽은 `tests/common/test_metrics_multiproc.py` 의
   `test_count_safely_swallows_child_inc_failure` **1건**이다. **그 테스트를 지우지 마라.**
4. ★★**도달 불가는 두 방향으로 틀린다.** [BL-582] 는 「불가」가 가능이었고, 이번 D10 은 반대로
   **`except` 자체가 사문**이었다(유일 raise 지점이 `body_hash is not None` 안인데 호출자는
   `None` 을 넘긴다). 둘 다 **「그 입력을 누가 만드는가」**를 따라가야만 갈린다.
5. ★★**「전건 red」는 좋은 신호가 아니라 확인 대상이다** — 이번에도 8건 중 1건(D5)이 주입
   stub 이 아니라 **결과 단언**에서 red 였고, 그것이 헤드라인 발견이었다.
6. ★**코퍼스 조회가 도달성 판정을 굳혔다** — 세션 24 / 활성 0 / `mode=live` 계정 0 /
   settings 가 JSONB `null` 인 전략 1건(그 위 세션 0건). 구조 분석과 코퍼스를 **양쪽** 봐라.
7. ★★**표적 변이를 전체 pytest 와 동시에 돌리지 마라**(테스트 DB 1벌 + `drop_all`).
8. ★★**게이트를 파이프에 넣지 마라 · 부분 경로로 재지 마라**(`ruff check src/` 만 돌리면 놓친다).

### baseline (2026-08-03 실측 — **커밋 후 재측정값**)

**BE 3893 passed / 46 skipped**(410.6s) · **BE 좁은 집합**(주입·발주·census·가드폭 4파일) **62** ·
**FE 1242**(205 파일 — FE diff 0) · ruff clean · mypy **214** clean ·
마이그레이션 head **`20260801_0001`** ·
가드 밖 mutation **96**(규칙 R1 — 정본은 `backend/tests/common/test_metric_guard_census.py`) ·
`/metrics` **12459 파일 · 771MB**(BL-581 Trigger 20000 미달).
★**이 숫자도 대조 대상이다. 첫 step 에서 지금 HEAD 로 다시 재라.**
★**BE 증가분 8 은 신규 주입 테스트다**(사이트 8). 주입 정본 5파일:
`tests/tasks/test_live_signal_metric_failure.py` · `tests/trading/test_order_rejected_metric.py` ·
`tests/tasks/test_closed_pnl_refresh_metric_failure.py` ·
`tests/tasks/test_closed_pnl_sweep_metric_failure.py` · `tests/tasks/test_refresh_closed_pnl.py`.

> ★★**표적 변이는 CONTROL 이 직접 집행한다.** `git checkout` 금지, 문자열 치환 + sha256 복원 대조.
> ★**치환 문자열이 다른 함수와 겹치는지 먼저 세라** — 이번에 `_count_safely` 와 `_touch_safely` 가
> 겹쳐 복원이 중단됐다(실행기 가드가 잡았다. 가드가 없었으면 조용히 두 곳을 바꿨을 것이다).
> ★**브랜치 접두사는 `stage/`** (pre-push 훅 화이트리스트). `QB_PRE_PUSH_BYPASS=1` 은 **쓰지 마라**.
> ★**`cd backend` 는 다음 명령까지 이어진다** — 레포 루트 스크립트는 절대경로로.
> ★★**`cd backend && set -a; . ./.env.local; set +a` 를 쓰지 마라.** 이미 `backend` 에 있으면
> `cd` 가 실패해 **`set -a` 만 건너뛰고** 나머지는 `;` 로 계속 실행된다 — env 가 **export 되지
> 않은 채** pytest 가 기본값(5432)으로 붙어 `InvalidPasswordError` 로 **대량 거짓 red** 가 난다
> (이번 회차에 실제로 밟았다). **`QB=…; set -a; . $QB/backend/.env.local; set +a; cd $QB/backend`**
> 처럼 절대경로로 소싱하고 `cd` 를 뒤에 둬라.
> ★**pre-commit 이 `ruff format`·`prettier --write` 를 돌린다** — **커밋 후 게이트를 다시 재라**.

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
