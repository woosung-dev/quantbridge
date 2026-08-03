# QuantBridge — Status

> **업데이트:** 2026-08-03
> **활성 Sprint:** 없음. 다음 작업은 아래 「다음 스프린트」 블록만 읽는다.
> **준비 브랜치:** `stage/metric-guard-residual-close` — **PR 생성 대기**(사용자 승인 후 push).
> **최근 머지:** `stage/gate-trustworthiness` → `main` (**PR #528**, 2026-08-03).

---

## 🎯 다음 스프린트 — **metric-guard-residual-sweep** ([BL-580] 잔여 104곳, `live_signal.py` 54곳부터)

> ★**이것이 다음 세션의 유일한 진입점이다.** 별도 킥오프 파일을 만들지 않는다.
> 시작 방법: **"다음 스프린트 진행해줘"**. `CONTEXT.md` + 본 파일을 읽고 시작한다.
> ★**`AGENTS.md` 는 읽지 마라 — 자동 로드된다**(`CLAUDE.md` 가 `@AGENTS.md` 하나만 import 한다).
> ★**`CONTEXT.md` 는 반대다 — 자동 로드가 아니라서 읽어야 들어온다.** `.ai/rules/*.md` 도 마찬가지다.
> ★**`docs/dev-log/INDEX.md` 를 통째로 grep 하지 마라** — `## 최근 12회차` 상단만 읽는다.

**목표·왜 지금.** 계측 실패가 머니-패스를 오기록하는 자리가 **104곳** 남았다([BL-580]).
직전 회차가 25곳을 판정해 **수리함 23 · 판정 보류 2**로 끝났고, 누적 34곳에서 **「가드 없이
유지」가 0곳**이다. 산문 근거의 타율이 0 이므로 **잔여도 분류하지 말고 주입으로 시작한다.**
**비목표** — census 키 구조 변경 · [BL-581] (Trigger 미달) · soak.

**작업 단위.** `tasks/live_signal.py` **54곳**이 전체의 52%다. 함수별로는
`_evaluate_session_inner` 21 · `_reconcile_conditional_entries` 12 · `_async_dispatch_event` 11.
**한 회차에 한 함수**로 끊어라 — 25곳이 한 회차의 상한에 가까웠다.

### 첫 step

1. **baseline 재측정** (`global.md` §7.1). 대조값은 아래 블록. ★**`-p no:randomly` 를 쓰지 마라 —
   randomizer 가 없어 no-op 이다.** 「두 번 재라」는 **수집 집합을 바꿔 재라**는 뜻이다.
2. **주입 관용구를 그대로 복제해라** — `.inc` 가 아니라 **`.labels` 를 폭파**(`OSError("mmap allocation failed")`)
   - **stub 정확히 1회 호출 단언** + **사이트별 비-계측 postcondition**. 정본 5파일은 아래 참조.
3. **판정 라벨은 누적 7종이다** — H1~H4(직전 정의 그대로) + **H5**(4xx 거절이 500 으로) ·
   **H6**(정상 종결이 재시도로 오분류) · **H7**(내구 쓰기 **앞**이라 아직 안 일어난 적재가 중단).
   **H3 은 두 회차 연속 공허**다. 넓히지 말고 필요하면 늘려라.
4. **[BL-584]** 신규 — 수리 전에 **현재 코퍼스에서 도달 가능한지**부터 확인해라(demo 전용이라
   `mode == live` 분기 미도달 가능성). 급하지 않다.
5. **[BL-582]** 반증된 2종은 전략 등록이 선행돼야 한다. ★`degraded_input` 은 **영구 제외**.
6. **[BL-581]** `/metrics` **11449 파일 · 708MB**. Trigger 20000 미달이라 착수하지 않는다.

### ★착수 전 반드시 읽을 것 (직전 회차가 실제로 밟은 것)

1. ★★★**산문 근거의 타율이 0 이다.** 이번에 반증된 두 문장은 각각 **10곳**·**7곳**을 가드에서
   빼는 근거였다. 직전 회차 4곳까지 합쳐 **21곳 중 21곳**이 주입에서 유해했다.
2. ★★★**백로그가 이름을 댄 범위가 문제의 범위가 아니었다.** 「closed_pnl 7곳」은 같은 파일·같은
   metric **15곳 중 7곳**이었고, **이름 없던 8곳 중 6곳이 더 나빴다**(계정 루프 전체 중단 · 원장 유실).
   나머지 2곳은 도달 불가로 **판정 보류**다 — 아래 7번 참조.
   **census 정본을 먼저 읽고 백로그 문장은 대조 대상으로 삼아라.**
3. ★★★**반쪽 수리는 사이트 주입을 전부 통과한다** — `.labels()` 만 감싸고 `.inc()` 를 밖에 두면
   **주입 29건이 전부 green** 이다(변이 M5 실측). 가드 폭은 `tests/common/test_metrics_multiproc.py`
   의 `_count_safely` 전용 테스트 2건이 지킨다. **그 테스트를 지우지 마라.**
4. ★★**불변식을 지키는 테스트가 있다는 게 그 불변식이 지켜진다는 뜻이 아니다** —
   `test_sweep_isolates_one_account_failure` 는 계정 격리용인데 **provider 예외만 주입해서**
   격리를 실제로 깨는 경로(`except` 첫 줄의 raw 계측)를 못 잡았다.
5. ★★**세 회차 연속으로 사전등록 변이 하나에 판별력이 0 이었다**(세 번 다 실행 전에 잡았다).
   **변이를 적을 때 「무엇을 끄는가 / 어느 테스트가 살아남는가」를 함께 적어라.**
6. ★★**codex 가 「내 변이가 판별력 없다」를 두 건 맞혔다** — `_PROTECTED_SITES` 검사는
   `(파일, 함수, metric)` 삼중항이라 **과선택**하고, 기존 격리 테스트는 계측을 주입하지 않는다.
7. ★★★**「테스트가 red 다」와 「프로덕션이 그 분기에 도달한다」는 다른 명제다.** 직전 회차의
   sweep 6곳 중 2곳(`:1879`/`:1884`)은 **프로덕션에서 구조적으로 도달 불가**인데 내 하네스가
   fake repo·팩토리 교체로 분기를 만들어 「실측 유해」로 적을 뻔했다(codex G6 가 잡았다).
   [BL-582] 함정의 **거울상**이다. ⇒ **주입 대상 분기마다 「프로덕션이 여기 도달하는 경로가
   무엇인가」를 한 줄로 적어라. 못 적으면 「판정 보류」다.**
8. ★**「전건 red」는 좋은 신호가 아니라 확인 대상이다** — 실패 지점이 전부 주입 stub 의 `raise`
   줄인지 먼저 봐라(드라이버가 잘못돼 red 인 것과 구별되지 않는다).
9. ★★**표적 변이를 전체 pytest 와 동시에 돌리지 마라**(테스트 DB 1벌 + `drop_all`).
10. ★★**게이트를 파이프에 넣지 마라 · 부분 경로로 재지 마라**(`ruff check src/` 만 돌리면 놓친다).

### baseline (2026-08-03 실측 — **커밋 후 재측정값**)

**BE 3885 passed / 46 skipped**(282s) · **BE 좁은 집합 `tests/trading tests/tasks` 1570 / 12** ·
**FE 1242**(205 파일 — FE diff 0 이라 착수 시점 값 그대로) · ruff clean · mypy **214** clean ·
마이그레이션 head **`20260801_0001`** ·
가드 밖 mutation **104**(규칙 R1 — 정본은 `backend/tests/common/test_metric_guard_census.py`) ·
`/metrics` **11449 파일 · 708MB**(BL-581 Trigger 20000 미달).
★**이 숫자도 대조 대상이다. 첫 step 에서 지금 HEAD 로 다시 재라.**
★**BE 증가분 29 는 신규 테스트다** — 사이트 25 + 호출자 오라클 2 + 가드 폭 2. 주입 정본 5파일: `tests/trading/test_order_rejected_metric.py` ·
`tests/tasks/test_closed_pnl_refresh_metric_failure.py` ·
`tests/tasks/test_closed_pnl_sweep_metric_failure.py` · `tests/tasks/test_refresh_closed_pnl.py` ·
`tests/tasks/test_live_signal_metric_failure.py`.

> ★★**표적 변이는 CONTROL 이 직접 집행한다.** `git checkout` 금지, 문자열 치환 + sha256 복원 대조.
> ★**브랜치 접두사는 `stage/`** (pre-push 훅 화이트리스트). `QB_PRE_PUSH_BYPASS=1` 은 **쓰지 마라**.
> ★**`cd backend` 는 다음 명령까지 이어진다** — 레포 루트 스크립트는 절대경로로.
> ★**pre-commit 이 `ruff format`·`prettier --write` 를 돌린다** — **커밋 후 게이트를 다시 재라**.

## 완료 이력

- 직전 회차 — [`metric-guard-residual-close`](dev-log/2026-08-03-metric-guard-residual-close.md)
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
