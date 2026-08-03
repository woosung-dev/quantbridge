# QuantBridge — Status

> **업데이트:** 2026-08-03
> **★★★소크 창이 죽었다 — 판정할 창이 없다.** 세션 `04097fdc` 는 T0 `2026-08-03T09:53:34Z` 에서
> **65분** 뒤인 `10:58:34Z` 에 `position_divergence`(`category=direction`)로 **fail-closed
> 자동 비활성화**됐다. `engine +0.0304` vs `exchange −0.03` — 방향 정반대. ⇒ **[BL-589] 신설(P1)**.
> **`2026-08-05T09:53Z` 판정은 성립하지 않는다.** 재가동 전에 [BL-589] 원인을 확정해라.
> **★정정:** 이 블록은 「PR #533 OPEN · 머지는 창이 닫힌 뒤」라고 적고 있었으나 **PR #533 은
> `2026-08-03T10:41:10Z` 에 이미 머지됐다**(merge commit `00c63018` = 현재 main HEAD).
> **최근 머지:** `stage/demo-soak-restart` → `main` (**PR #533** @ `00c63018`, 2026-08-03).
>
> **다음 세션의 첫 step = [BL-589] 원인 확정.** 아래 「진행 중」 블록의 소크 관측 절차는 창이
> 없으므로 지금은 적용 대상이 아니다 — 재가동한 뒤에 다시 유효해진다.

---

## 다음 스프린트 — **backtest-metric-oracle** (착수 완료 · 머지 대기)

> ★**소크와 병행한다.** 이 스프린트는 celery 를 안 타므로(엔진 직접 호출) 워크트리에서 완결된다.
> 작업 위치 = `.claude/worktrees/metricoracle` **슬롯 5** · 브랜치 `stage/backtest-metric-oracle`.

**왜.** 백테스트 회귀 안전망(Trust Layer P-3)이 위험조정지표에 대해 **감지력이 0** 이었다 —
코퍼스 5벌이 전부 자본을 음수로 몰고 끝나 `sharpe_ratio` 가 5벌 모두 `"0.00000000"`,
`sortino`·`calmar` 가 5벌 모두 `null` 이었다. 값이 상수라 그 지표들의 산술이 회귀해도
baseline diff 가 0 이다.

**한 것.** ① `sharpe_convention` 대조 신설(schema v2) ② 비축퇴 코퍼스 2벌 등재
(`s4_hma_curvature` 음수 3지표 · `s5_ema_trend` 양수 3지표) ③ **[BL-461] Resolved** —
daily fallback 날짜 리샘플 ④ **[BL-391] Resolved** — 3단 계약 오라클.

**게이트.** BE pytest **3893 → 3906**(+13) · ruff 0 · mypy 0 · FE 1242 · docs-audit 0 ·
bl-audit 3면 정합. 회고 = [dev-log](dev-log/2026-08-03-backtest-metric-oracle.md).

### ★머지 조건 — 소크 창이 닫힌 뒤

이 브랜치는 `backend/src/backtest/engine/` 을 건드린다. **머지가 main 의 `backend/src` 를 바꿔
`watchfiles` 재적재를 유발하므로 `2026-08-05T09:53Z` 전에는 머지하지 않는다.**
머지 후 첫 step = **celery 경유 dogfood**(실제 백테스트 제출 → 리포트 화면에서 daily 컨벤션
각주 확인). 워크트리에서는 구조적으로 불가능하다 — worker 가 메인의 `src` 를 mount 한다.

---

## 🎯 진행 중 — **demo-soak-restart** (데모 시계 재가동 · P0 [BL-003] 유일 진입로)

> ★**이것이 다음 세션의 유일한 진입점이다.** 별도 킥오프 파일을 만들지 않는다.
> ★**`AGENTS.md` 는 읽지 마라 — 자동 로드된다.** `CONTEXT.md`·`.ai/rules/*.md` 는 반대다(읽어야 들어온다).

**시계가 다시 돈다.** 재가동 전 일별 주문은 `07-30: 86 · 07-31: 53 · 08-01: 5 · 08-02: 3 ·
08-03: 0` 이었고 마지막 라이브 신호 이벤트는 **07-31** 이었다. **P0 [BL-003] 의 Trigger 는
「Bybit Demo 1주 안정 운영 후」** 라 이 시계 말고 P0 를 여는 길이 없다.

| 항목      | 값                                                                      |
| --------- | ----------------------------------------------------------------------- |
| 세션      | `04097fdc-0322-4a23-bfcc-d9f7c7a7e2b3`                                  |
| T0        | `2026-08-03T09:53:34.451807+00` (★창은 시계가 아니라 이 값이다)         |
| 조합      | 전략 `07a22564` PbR · 계정 `19a8166a` bybit/demo · `BTC/USDT` · `1m`    |
| 파라미터  | leverage 2 · isolated · size 1.0% · equity baseline 190422.997 USDT     |
| 창 종료   | **`2026-08-05T09:53Z` 이후** (≥48h)                                     |
| 관측      | `scripts/soak-observe.sh` (앵커는 `.soak/session`, gitignore)           |
| 유도 주입 | 이벤트 `ca3c645f` — `sequence_no=9999` + `trade_id='h8_probe'` **합성** |

### 다음 세션의 첫 step

1. **`scripts/soak-observe.sh` 를 인자 없이 한 번 돌려라.** 그게 일일 대조 전량이다
   (세션 생존 · 주문 일자×state · outbox 분포 · **counter 차분** · H8 불변식 · `/metrics` 파일 수).
   조회가 실패하면 `UNKNOWN` + exit 3 이다 — **`UNKNOWN` 을 「이상 없음」으로 읽지 마라.**
2. ★★**이상이 없으면 아무것도 고치지 마라.** 시계를 세우는 게 더 비싸다.
3. ★★★**소크 중 `backend/src` 편집 금지.** 워커가 `watchfiles` 로 물고 있어서 다단계 편집의
   **중간 상태**를 적재하면 `NameError` 로 평가가 죽고 세션이 fail-closed 비활성화된다
   (2026-07-27 실측). [BL-580] 잔여 96곳은 비목표일 뿐 아니라 **창이 닫힐 때까지 구조적 금지**다.
   문서·`scripts/`·테스트는 안전하다.
4. ★**`make up-isolated` / `down-isolated` 금지** — 선행 타깃 `metrics-wipe` 가 baseline 스냅샷을
   지운다. 워커를 되살려야 하면 `docker compose … restart <서비스>` 만.
5. **창이 닫히면**(≥48h) 판정 → dev-log → PR. 판정 축: [BL-578] 잔여 거절 · H8 **자연** 발화 ·
   미검증 5PR(#523·#525·#528·#530·#532). **1주 무사고면 [BL-003] Trigger 가 열린다.**

### 오늘(T0) 검증한 것 / 하지 않은 것 — 합쳐 말하지 마라

| 층                | 무엇을 증명했나                                    | 결과                                           |
| ----------------- | -------------------------------------------------- | ---------------------------------------------- |
| (a) 아티팩트 동일 | 러닝 워커가 HEAD 소스로 실행 중                    | ✅ sha256 `70996462…` 일치 + 09:15 리로드 로그 |
| (b) 파이프라인    | 평가·발주가 실제로 돈다                            | ✅ `due_count:1` · `evaluated_total` 1043→1045 |
| (c1) H8 분기 실행 | flat 청산이 프로덕션에서 거절로 종결, 주문 안 샌다 | ✅ 카운터 14→**15** · **그 키의 주문 0행**     |
| (c2) 가드 봉쇄    | 계측 실패가 그 거절을 뒤집지 못한다                | ✅ **오프라인** 15 passed (프로덕션 유도 아님) |

★**(c1)과 (c2)를 합쳐 「H8 검증 완료」라고 쓰지 마라.** 유도는 분기의 **도달·종결**만 증명한다.
계측 실패 봉쇄는 `tests/tasks/test_live_signal_metric_failure.py` 가 결정론적으로 증명하고,
프로덕션에서 그걸 유도하려면 multiproc 디렉터리를 망가뜨려야 해서 소크 중에는 금지다.

★**왜 유도했나 — 기다려서는 못 재기 때문이다.** 원장 실측으로 `close` 이벤트가 **≈0.7건/h**,
그중 `close_position_flat` 비율은 회차마다 고쳐져 **07-28 15건 → 07-29 3건 → 07-30 1건 →
07-31 0건**으로 감소 중이었다. 30분 기대값 ≈**0.02건**, 48h 에도 **0~2건**이다.
⇒ **판정 지표가 그 창에서 발화 가능한지를 먼저 계산해라.** 발화 안 하면 창을 늘리는 게 아니라
발화 조건을 만든다.

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

### baseline (T0 = 2026-08-03T09:53Z 실측)

**`qb_live_signal_dispatch_total{close,close_position_flat}` = 14 → 유도 후 15** ·
**`qb_metrics_mutation_failed_total` = 0**(BL-580 Trigger 여전히 미발화) ·
`qb_live_signal_evaluated_total{1m,success}` = **1043** ·
`/metrics` **12615 파일 · 781MB**(BL-581 Trigger 20000 미달) ·
마이그레이션 head **`20260801_0001`** · 가드 밖 mutation **96**.
카운터 원본 스냅샷은 `.soak/snap-*.txt` 에 있다 — **차분은 거기서 뜬다.**
★**BE/FE/ruff/mypy 는 PR #532 커밋 후 값(BE 3893 passed / 46 skipped · FE 1242 · mypy 214)
그대로다** — 본 브랜치는 `backend/src`·`frontend` 를 한 줄도 안 건드렸다(docs + `scripts/` 만).

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
