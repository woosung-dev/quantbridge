# close-mismatch-soak — 실재한다. 2.60건/h, 그리고 6/6 이 같은 패턴이었다 (2026-07-30)

> **PR #513** 머지 `main@bc0046b6` · **마이그레이션 0** · herdr 함대 2벌(`bracket` · `docdrift`) 병렬 + CONTROL soak.
> 사전등록 판정 **V3 (실재 · 원인 착수)**.

---

## 한 줄

직전 회차가 **보이게** 만들었다. 이번 회차는 **쟀다** — 그리고 6/6 이 같은 패턴이라 **뿌리까지 좁혀졌다.**

---

## T1 — BL-560 soak (CONTROL, 메인 체크아웃)

창 **3h20m** (`15:54:56Z` → `19:15Z`). PbR · BTC/USDT · 1m · bybit demo `19a8166a`.

| 지표                            |                               값 |
| ------------------------------- | -------------------------------: |
| `reduce_only_same_side`         |                    **2.60 건/h** |
| 청산 시도 대비                  |               **46.2%** (6 / 13) |
| `reduce_only_violation` 차분    |                **0** (7.0 → 7.0) |
| `reduce_only_position_zero`     |           **0** (한 번도 미발화) |
| `deferred_market_inflight_noop` | **4** (defer 10건 중 40%가 사문) |

- **V1a**(러닝 워커 안 코드 sentinel) PASS · **V1b**(라벨 발화, 6.0) PASS · **V4** 충족(13 ≥ 10) · **V5** 미발동.
- ★**라벨 분리가 실제로 작동했다** — 구 라벨 차분이 **0**. 이 6건은 예전이면 전부 `reduce_only_violation` 에
  묻혀 "유령 포지션 문제" 로 읽혔을 것이다. **독립 계측기 2개가 일치한다**(Prometheus 6.0 = 원장 6).
- ★★**직전 회차의 헤드라인이 이 창에서 뒤집혔다.** "무해 갈래가 3배 많아 위험 갈래를 묻는다" 는
  성립하지 않았다 — `position_zero` **0건**이고 `same_side` 만 6건. **역사 비율은 창마다 다르다.**

### ★★★뿌리 — 6/6 전건이 같은 패턴이다

모든 거절이 **직전 체결과 같은 방향**이고, 체결 후 **50–104초**(평균 78초) 안에 일어난다:

```
16:03:27 buy  0.058 체결 → 16:04:43 buy  reduce-only 거절 (+76s)
16:21:27 sell 0.029 체결 → 16:22:42 sell reduce-only 거절 (+75s)
16:55:52 buy  0.029 체결 → 16:56:42 buy  reduce-only 거절 (+50s)
17:11:39 sell 0.029 체결 → 17:12:42 sell reduce-only 거절 (+63s)
17:42:01 buy  0.029 체결 → 17:43:43 buy  reduce-only 거절 (+102s)
18:07:59 sell 0.058 체결 → 18:09:43 sell reduce-only 거절 (+104s)
```

buy 로 체결하면 롱이 되고, 롱은 **sell** 로 닫는다. 그런데 엔진은 **buy** reduce-only 를 보낸다
= **숏을 닫으려 한다.** 즉 원장에 숏이 아직 열려 있는데, 그 숏은 반전 체결
(`buy 0.058` = 숏 0.029 청산 + 롱 0.029 진입)로 거래소에선 이미 닫혔다.

⇒ ★**엔진이 자기 반전 체결의 청산 leg 를 반영하지 못한다.** 발신은 정상 봉 평가
(`live_signal.dispatch_event`)이지 별도 정리 태스크가 아니다. **거절은 미정렬의 원인이 아니라 결과다.**
사전등록 후보 ①(재가격 경주)·③(재생 아티팩트)은 **"직전 체결과 같은 방향" 이라는 6/6 규칙성을 예측하지 않는다.**

★**원칙대로 고치지 않았다** — `status.md` §하지 않는 것이 "방향 반전을 크기 모르는 채 고치는 것" 을
금지한다. 크기와 뿌리를 확정한 것이 이번 산출물이고, 수정은 다음 회차(`reversal-ledger-sync`)다.

### ★수용 기준 하나가 구조적으로 충족 불가였다

"그 시점의 엔진/거래소 포지션 **쌍**" 은 못 남겼다. 발신부(`tasks/live_signal.py:585-594`)가
`engine_position`/`exchange_position` 을 `extra=` 로 넘기지만 **포매터가 `extra` 를 렌더하지 않는다** —
실제 로그 라인은 `live_signal_position_divergence` 한 단어가 전부다.
**방향** 쌍은 거래소 거절 코드로 정확히 복원되지만 **크기** 쌍은 못 얻는다. → **BL-561 신설**(BL-560 선행).

★**같은 계열 두 번째다** — BL-553 이 `trade_ids` 를 확인 신호에서 빼야 했던 이유가 동일하다.
개별 회피가 아니라 포매터를 고쳐야 한다.

### BL-553 — 사전조건이 불완전했음이 밝혀졌다

공백 **33분 03초**(`18:35:03Z`→`19:08:06Z`)를 **장전된 상태에서** 열었다(armed=1, `buy 0.087 @ 64795.6`).
직전 회차가 지정한 사전조건을 충족했는데도 `applied` 는 **또 미발화**했고 `already_open` 이 +1 됐다.
누적 **96분에서 0회**(62분57초 + 33분03초).

★★**「장전」만으로는 부족하다.** `already_open` = 엔진 원장에 이미 열린 트레이드가 있어 seed 가 불필요했다는 뜻.
`applied` 에 도달하려면 **장전 + 엔진 flat** 이어야 한다. 그리고 그것이 **PbR 로는 구조적으로 어렵다** —
`s1_pbr` 은 stop-and-reverse 라 flat 구간이 사실상 없다. **5회 연속 미발화의 이유가 이것으로 설명된다.**
→ 다음 회차는 `strategy.close` 로 flat 으로 돌아가는 전략을 써라. ★**PbR 재시도 금지.**

---

## T2 — 조건부 진입 계측 (`bracket` 워크트리)

### ★★BL-523 의 전제가 코드 대조로 반증됐다

1. `place_exit` 가 `targets = [from_entry] if from_entry in self.open_trades else []`
   (`strategy_state.py:963`) 로 **`open_trades` 만** 타깃하는데, stop 진입은
   `pending_orders[...] = PendingOrder(...); return None`(`:714-726`) 이라 체결 전까지 거기 없다
   ⇒ `exit_levels_for` 가 읽는 `pending_exits` 에 레그가 **애초에 생기지 않는다** = 항상 `(None,None,None)`.
2. 시드 전략 **`s1_pbr.pine` 은 `strategy.exit` 이 0건**이고, 코퍼스 8벌 중 stop 진입과 exit 을
   **둘 다 쓰는 전략이 없다**.

**부수 정정** — BL 본문의 패리티 근거도 틀렸다. _"백테스트는 체결 직후 `check_exit_fills` 로 활성화되므로
라이브만 무방비"_ 라 적혀 있었으나, bar 루프는 `check_exit_fills`(`event_loop.py:169`) →
`interp.execute`(`:197`) 순서라 레그는 그 bar **끝**에 등록되어 **다음 bar** 부터 검사된다.
**백테스트도 체결 bar 안에서는 보호하지 않는다.**

⇒ 목표를 **부착 → "붙일 것이 있었는가" 계측**으로 바꿨다. 3단 seam 배관(전부 default `None`) +
게이트 A(trailing-only 거부)/B(tpSize 정합) + `conditional_request_invalid` 라벨 분리 + guard outcome 4종.
**실주행 확인**(메인 체크아웃, celery 경유): `bracket_unavailable` **2.0 / `bracket_attached` 부재** = **100%/0%**.

가장 중요한 산출물은 회귀 테스트 `test_pending_order_snapshot_has_no_exit_levels_when_entry_not_open` —
**왜** None 인지를 `strategy_state.py:963`/`:714-726`/`:1088` 인용으로 적고 "다시 파지 마라" 를 못박았다.
같은 id 가 열린 경우를 대조군으로 붙여 **"배관이 죽은 것" 과 "타깃이 없는 것" 을 분리**했다.

### BL-516 — backlog 권장안 2종을 기각했다

- **leg 분리 기각** — `Order.reduce_only.is_(False)` 술어가 **4곳**
  (`order_repository.py:275` reconciler · `:315` sweep · `:347` janitor · `:513` 진입원장)이라
  청산 leg 가 **모든 lifecycle 쿼리에서 배제**된다 ⇒ 세션 종료 후에도 안 걷히는 고아 reduce-only 조건부 주문.
  게다가 같은 trigger 가의 조건부 2건은 **체결 순서가 보장되지 않아** `110017 same side` 를 **늘린다** —
  ★**T1 이 지금 재고 있는 바로 그 신호다.**
- **발주 직전 재확인 기각** — 갭은 「등재 → 트리거」 사이인데 거기에 우리 코드가 없다. 못 푼다.
  게다가 `fetch_open_positions`(`live_signal.py:929`) + 3중 fail-closed 로 **이미 구현돼 있다.**

⇒ **계측 + 좁은 가드.** 발주 형태 불변(1건, `reduce_only=False`, 수량 산식 그대로) +
`crosses_zero`/`overshoot_ratio` 파생값 + `qb_live_conditional_reversal_total{bucket}` +
`max_reversal_overshoot_ratio` 캡(**기본 `None` = 비활성**). **깨진 기존 테스트 0건** —
`test_reversal_uses_full_target_delta` 가 살아남아 "수량 불변" 계약의 수호자가 된다.

★**soak 이 이 선택을 사후 정당화했다.** 6/6 이 반전 체결 직후 방향 불일치를 보여줬다 —
leg 분리를 했다면 reduce-only 를 **더 만들어** 그 거절을 늘렸을 것이다.

### ★워커가 내 스펙의 실제 결함을 잡았다

스펙은 `resulting_position_qty = abs(target_position)` 였는데 **틀렸다.** 그대로 썼다면 게이트 B 가
**반전이 아니라 순수 진입에서 상시 오작동**한다 — `percent_of_equity` 사이징이 20자리 목표를 만드는데
(실측 `0.00029537036490054884`) 발주 수량은 `qty_step` 절삭(`0.029`)이라 flat 진입에서도 불일치가 난다.
**가설이 아니라 프로덕션의 일반 경로**였다. → `abs(current_position ± quantity)` 로 구현 + 변이 테스트로 잠금.

---

## T3 — BL 산식을 스크립트로 승격 (`docdrift` 워크트리)

`scripts/bl-audit.sh` 신설. 지금까지 "공식 산식" 은 `backlog.md` 헤더의 **인라인 awk 주석**이었고
사람이 복붙해 돌렸다. 그 판정은 "섹션 본문 어딘가에 `Resolved` 문자열이 있으면 RESOLVED" 였다
— 즉 **cross-ref 한 줄이 항목을 지운다.**

★**실제로 BL-003(P0, 열려 있음)이 자기 섹션 안의 `BL-004 ✅ Resolved` 두 줄 때문에 RESOLVED 로 집계됐다**
= 공식 산식이 **P0 active 를 0 으로 보고하고 있었다.** 같은 뿌리로 BL-499·BL-535 도 오분류.

★**판별력 증명(변이 실험)** — 낡은 산식이 틀리던 정확한 조건(BL-003 의 Status 줄 제거 +
cross-ref `✅ Resolved` 복원)을 주입:

| 산식        | 판정                               |
| ----------- | ---------------------------------- |
| 낡은 awk    | `RESOLVED` (P0 버킷이 조용히 0)    |
| 새 스크립트 | **`UNKNOWN`** (P0 에 노출, exit 1) |

원복 후 다시 `ACTIVE`. **대조군까지 확인했다.**

BL-543(roadmap 자기모순 — 같은 문서가 3곳에서 "착지" 라 하면서 체크박스는 `[ ]`) ·
BL-308(표 Open ↔ 본문 Resolved) · BL-361(표 행 부재 + 상태가 `Trigger` 필드 안) 3면 정합.

★**워커가 내 스펙 2건을 정정했다** — ① `status.md:890` 에 BL-308 은 **없다**(grep 0건, 오염은 3곳이지 4곳이 아니다)
② roadmap 의 "P별 내역 기계 집계 불가" 는 정규식 문제였다(`**Priority:**` 는 217 섹션 전부에 있다).

★**그리고 스크립트가 즉시 내 드리프트를 잡았다** — 내가 BL-516/523 에 판정 블록만 넣고 `**상태:**` 줄을
안 달자 **UNKNOWN 으로 떨어뜨렸다**. 설계대로 작동한 첫 실사용 사례다.

---

## ★★★codex 적대 리뷰가 실제 파손을 잡았다

**MAJOR — FE strict 스키마 파손.** BE 가 `max_reversal_overshoot_ratio` 를 `default=None` 으로 emit 하고
`strategy/service.py:331` 이 `settings.model_dump()` 를 그대로 저장한다 ⇒ FE `StrategySettingsSchema` 는
`.strict()` 라 **설정을 한 번이라도 저장하면 그 전략의 이후 파싱이 영구히 실패**한다.

★**GET 경로는 멀쩡하다**(BE 가 DB JSONB 를 그대로 돌려줘 응답에 그 키가 없다) — 그래서
**평가자가 playwright 로 화면 3개를 돌고도 통과시켰고**, T2 워커도 "동작 영향 없음" 으로 오판했다.
**저장 경로에서만 터진다.** → 수정 완료(`schemas.ts` + 폼 기본값 보존).

나머지는 사실 확인 후 등재 — **BL-562**(게이트 B/캡이 등재 시점 포지션만 본다) ·
**BL-563**(bracket outcome 을 게이트 뒤에서 세 오분류 가능) · **BL-564**(bl-audit 이 fence/`<details>` 에 속음).

codex 가 **"결함 없음" 으로 확인해준 것**도 기록해 둔다 — `_GuardOutcomeCounter` allowlist 전수 통과 ·
`target_position == 0` 가드 · trailing+trigger 가 Bybit 로 나가는 경로 부재(2중 방어) · 마이그레이션 불요.

---

## 게이트

**17건 전건 통과.** BE **3659 passed / 46 skipped**(main 3633 대비 **+26**) · FE **1232**(205 파일) ·
ruff clean · mypy **213** clean · FE typecheck/lint clean · `pnpm e2e` **4 passed**(수동) ·
e2e design-canon/authed @:3100 · CI 커버리지·fresh DB alembic·lockfile·hooks.
**마이그레이션 0**(head `20260730_0001` 불변).

★**baseline 정정 2건** — 문서의 「FE 1231」은 **stale**이었다(main 을 직접 재측정하니 **1232**,
이번 회차 FE 테스트 추가 0건). backlog/roadmap 표기 수치도 스크립트 실측(143/221)과 동기화.

---

## 함정 (정본 `reference/gates-and-traps.md` 에 승격)

- ★★★**JOIN 이 카운트를 뻥튀긴다** — soak 감시가 `same_side=14` 로 보고했으나 실제 **1건**(세션 14개만큼 곱해짐).
  **V3 을 오판할 뻔했다.**
- ★★**정규화 함수 프로브는 실제 입력 형태로** — 산문을 넣어 `unparsed` 3건, "배선이 죽었다" 로 읽힐 뻔했다.
- ★★**`prometheus_client` 는 발화 전 series 를 안 만든다** → "샘플과 함께 존재" 류 사전등록 문턱은 **달성 불가**.
- ★★**`final-gates.sh` 는 exit code 만 보증한다** — 숫자 대조는 사람 몫(그래서 stale baseline 을 잡았다).
- ★**`pnpm e2e` 는 정말로 게이트 밖**(게이트는 `chromium-design-canon`·`chromium-authed` 다른 프로젝트).
- ★**`EXIT=$?` 를 파이프 뒤에 쓰면 `tail` 의 코드를 읽는다** · **`git merge-tree` 는 커밋을 받는다** ·
  **`pnpm test --run` = Unknown option**.
- ★**`herdr agent prompt` 가 stall 할 수 있다**(`agent_prompt_stalled`, idle 유지) — 재발송하면 붙는다.
- ★**`make down-isolated`/`up-isolated` 금지** — 선행 `metrics-wipe` 가 before 기준선을 지운다. 워커만 `restart`.
- ★**soak 계정을 원장이 고르게 하라** — 탐색이 지목한 `0277c150` 은 `read_only=true` 라 주문 불가였고,
  `110017` 39건 **전량**이 `19a8166a` 에서 나왔다. 그대로 갔으면 **구조적으로 0인 soak**.
- ★**`gap_resync_position_mismatch` 사망 경로가 있다** → 공백 실험은 **관측 창을 은행에 넣은 뒤** 열어라.

---

## 신규 BL

**BL-561**(P2, 포매터 `extra` 미렌더 — BL-560 선행) · **BL-562**(P2, 등재 시점 포지션만 봄) ·
**BL-563**(P3, bracket outcome 귀속 지점) · **BL-564**(P3, bl-audit 이 fence/details 에 속음).

## 정직하게 남긴 것

- `qb_live_conditional_reversal_total` **실주행 미발화** — 검증 창(3분)에 반전이 없었다.
- `scripts/bl-audit.sh` **exit 1** — UNKNOWN 17건 미판정. 게이트 체인 편입은 그 정리 후(BL-564 와 함께).
- BL-553 `applied` **5회 연속 0** — PbR 로는 구조적으로 도달 불가.
