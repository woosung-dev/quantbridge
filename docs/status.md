# QuantBridge — Status

> **업데이트:** 2026-08-03
> **활성 Sprint:** 없음. 다음 작업은 아래 「다음 스프린트」 블록만 읽는다.
> **준비 브랜치:** 없음 — 누적분은 전부 착지했다.
> **최근 머지:** `stage/gate-trustworthiness` → `main` (**PR #528**, 2026-08-03).
> ★이 PR 하나가 **두 회차**(metric-guard-residual + gate-trustworthiness · 6커밋)를 담았다 —
> 스택이 선형이라 tip 하나로 덮였다. 다음 회차는 **`main` 에서 새로 딴다**(3단 스택 금지).

---

## 🎯 다음 스프린트 — **metric-guard-residual-close** ([BL-580] 잔여 129곳을 고장 주입으로 판정한다)

> ★**이것이 다음 세션의 유일한 진입점이다.** 별도 킥오프 파일을 만들지 않는다.
> 시작 방법: **"다음 스프린트 진행해줘"**. `CONTEXT.md` + 본 파일을 읽고 시작한다.
> ★**`AGENTS.md` 는 읽지 마라 — 자동 로드된다**(`CLAUDE.md` 가 `@AGENTS.md` 하나만 import 한다).
> ★**`CONTEXT.md` 는 반대다 — 자동 로드가 아니라서 읽어야 들어온다.** `.ai/rules/*.md` 도 자동 로드가 아니다.
> ★**`docs/dev-log/INDEX.md` 를 통째로 grep 하지 마라** — `## 최근 12회차` 상단만 읽는다.

**한 줄.** 계측 실패가 머니-패스를 오기록하는 자리 **129곳**이 가드 밖에 남아 있고, 그중 아직
**코드 독해로만** 판정된 구간이 있다([BL-580]). 직전 두 회차가 같은 종류의 산문 근거를 **전건
반증**했으므로(4곳 → 4곳 전부 H1), 남은 곳도 **고장 주입으로 재라.**

### 첫 step

1. **baseline 재측정** (`global.md` §7.1). 대조값은 아래 블록. ★**`-p no:randomly` 를 쓰지 마라 —
   이 레포에는 randomizer 가 없어 no-op 이다**(2026-08-03 실측). 「두 번 재라」의 의미는 순서가
   아니라 **수집 집합을 바꿔 재라**는 것이다.
2. **[BL-580] 잔여 129곳 중 아직 코드 독해인 것** — `order_service.py` 10곳(blast radius 0) ·
   `trading.py` closed_pnl 7곳(`already_synced` 수렴). **고장 주입 + 사이트별 postcondition**
   으로만 판정한다. 「~라서 안전하다」는 산문은 근거가 아니라 **조사 대상**이다.
3. **[BL-582] 반증된 2종** — 코퍼스에 발현 전략이 없어 프로덕션 유도는 전략 등록이 선행돼야 한다.
   급하지 않다. ★`degraded_input` 은 **영구 제외**(제3자 API 남용).
4. **[BL-581]** `/metrics` **11277 파일 · 698MB**. Trigger 20000 미달이라 아직 착수하지 않는다.

### ★착수 전 반드시 읽을 것 (직전 회차가 실제로 밟은 것)

1. ★★★**「전부 통과」가 수집 집합 운이었다** — [BL-583] 의 뿌리는 **클래스 정의 모듈을 패치한
   상태에서 소비 모듈이 「처음」 적재되면 가짜가 그 모듈 전역으로 영구 복사되는 것**이었다
   (`monkeypatch` 는 정의 모듈만 되돌린다). 무관한 파일 **6개**가 문제 모듈을 미리 적재해 줘서
   전체 스위트는 green 이었고, 그 6개를 빼면 **3 failed** 였다. **4개만 빼면 여전히 green** 이다 —
   실험의 ignore 집합을 손으로 고르면 **마스킹된 green** 을 얻는다.
2. ★★★**「고쳤다」와 「그 종류를 다 고쳤다」는 또 달랐다** — 픽스 1줄로 2파일 repro 가 green 이
   됐는데, 같은 병이 **다른 오염원·다른 모듈·다른 도메인으로 3건 더** 있었다. 찾은 방법은 손
   추론이 아니라 **가드를 먼저 넣고 좁은 수집 집합으로 census 를 돌린 것**이다.
3. ★★★**내 사전등록 변이가 두 회차 연속 판별력 0 이었다** — 이번엔 「스캔 범위를 없앤다」가
   순수 함수 단위 테스트를 통과했다(codex G1 이 코드 전에 잡았다). **변이를 적을 때 「무엇을
   끄는가 / 어느 테스트가 살아남는가」를 함께 적어라.**
4. ★★**codex 도 틀렸다** — 사전 적재원 6개 중 **5개만** 셌다. findings 전건 코드 대조가 이번엔
   codex 를 보정했다. 반대로 **내 근거도 틀렸다**(「지연 import 가 순환을 끊는다」 → 실측 순환 0).
5. ★★**비용을 추정하지 말고 재라** — 가드가 스위트를 8% 늦춘 것처럼 보였지만 실측 비용은
   **0.9초**였고, 차이는 실행 간 변동폭(259~281s)이었다. 추정했다면 15배 틀렸다.
6. ★**내가 추가한 에러 경로에 테스트가 없었다** — codex 지적으로 넣은 `except` 분기를 검증 없이
   넘길 뻔했다. 자식 pytest 세션에 **teardown 이 터지며 대역을 남기는 항목**을 넣어 고정했다.
7. ★**요약 줄을 통째로 문자열 비교하지 마라** — `"1 passed, 1 error"` 로 단언했더니 실측은
   `1 passed, 6 warnings, 1 error` 였다.
8. ★★**표적 변이를 전체 pytest 와 동시에 돌리지 마라** — 테스트 DB 1벌 + `drop_all`.
9. ★★**게이트를 파이프에 넣지 마라 · 부분 경로로 재지 마라**(`ruff check src/` 만 돌리면 놓친다).

### baseline (2026-08-03 실측 — `stage/gate-trustworthiness` 커밋 후)

**BE 3856 passed / 46 skipped**(296s) · **FE 1242**(205 파일) · ruff clean · mypy **214** clean ·
마이그레이션 head **`20260801_0001`** ·
가드 밖 mutation **129**(규칙 R1 — 정본은 `backend/tests/common/test_metric_guard_census.py`) ·
`/metrics` **11277 파일 · 698MB**(BL-581 Trigger 20000 미달).
★**이 숫자도 대조 대상이다. 첫 step 에서 지금 HEAD 로 다시 재라.**
★**BE 증가분은 신규 가드 테스트 8건이다.** 그리고 이제 **테스트를 실제로 실행하는 경로마다
자기 감시를 한다**(`--collect-only` 는 훅을 부르지 않는다) — 한 테스트가 프로덕션 모듈 전역에
테스트 대역을 남기면 `tests/conftest.py` 가 **그 테스트를 teardown ERROR** 로 만든다([BL-583]).
그 가드가 **못 잡는 5종**은 backlog BL-583 에 적혀 있다.

> ★★**표적 변이는 CONTROL 이 직접 집행한다.** `git checkout` 금지, 문자열 치환 + sha256 복원 대조.
> ★**브랜치 접두사는 `stage/`** (pre-push 훅 화이트리스트). `QB_PRE_PUSH_BYPASS=1` 은 **쓰지 마라**.
> ★**`cd backend` 는 다음 명령까지 이어진다** — 레포 루트 스크립트는 절대경로로.
> ★**pre-commit 이 `ruff format`·`prettier --write` 를 돌린다** — **커밋 후 게이트를 다시 재라**.

## 완료 이력

- 직전 회차 — [`gate-trustworthiness`](dev-log/2026-08-03-gate-trustworthiness.md)
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
