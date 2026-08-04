# QuantBridge — Status

> **업데이트:** 2026-08-04
> **★[BL-591] 슬라이스 1(계측) 머지 — 그리고 사전등록 V1 이 발동해 슬라이스 2 를 착수하지 않는다.**
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
> 적중 4가 **전부 `legs=2`** — 거래소는 단일 포지션이다. **`trade_id` 는 trade 가 아니라 Pine
> 진입 규칙 이름**(`PivRevSE` 56체결/19세션)이고 **반전은 `:close:` 키를 만들지 않는다**(배수량
> 진입 하나로 나간다). **슬라이스 1 은 net 으로 `agree` 를 판정하고 슬라이스 2 는 legs 를
> 주입한다 — 계측이 초록이어도 주입될 값은 틀렸다.**
>
> **소크가 돌고 있다 — 세션 `bbea6da4` · T0 `2026-08-04T02:54:15Z` · equity baseline
> `190359.77569871`.** 앵커는 `.soak/session`. **`backend/src` 편집·변이 테스트·BE pytest 금지.**
>
> **최근 머지:** `stage/engine-position-ssot` → `main` (**PR #539**, 2026-08-04).
> 게이트: BE **3993 passed / 46 skipped** · ruff 0 · mypy 0 (**216**) · bl-audit active **154** ·
> docs-audit clean · 사전등록 변이 **M1~M5 전건 판별**.

---

## 다음 스프린트 — **결정 대기** (engine-position-ssot 슬라이스 1 로 축이 흔들렸다)

> ★**이것이 다음 세션의 유일한 진입점이다.** 별도 킥오프 파일을 만들지 않는다.
> ★**`AGENTS.md` 는 읽지 마라 — 자동 로드된다.** `CONTEXT.md` 는 반대다(읽어야 들어온다).

### 무조건 하는 첫 step — 관측 2건 확인 (판정 없이 기록만)

2026-08-04 `soak-observe.sh` 차분에 **처음 보는 것 2개**가 떴고, 소크 생존 중이라 손대지 못했다.

- `qb_live_conditional_guard_total{breach_with_resting}` **11 → 12** — [BL-589] 수리 관측축의
  **첫 프로덕션 발화**다. ★단 같은 창에서 `market_converted` 는 **증가하지 않았다.**
  status.md 가 정한 확인식(「`breach_with_resting` 이 증가할 때 `market_converted` 동시 증가」)이
  **충족되지 않았다** — 대기 주문이 진짜로 발화 가능했다면 정상이다. 그 주문의 트리거·기준가를
  원장에서 확인해라. **결론을 미리 적지 마라.**
- `qb_live_conditional_reconcile_errors_total{stage="terminal_write_back_filled"}` **= 1** (신규
  series) — write-back 경로에서 처음 나온 에러다. 로그에서 그 tick 을 찾아 무엇이 던졌는지 봐라.

★새 증상 BL 을 열지 마라 — [BL-591] 또는 해당 원본 BL 에 링크한다.

### 그다음 — 사용자 결정 (셋 중 하나. 추천은 A)

**A. [BL-591] 축 재판정** — ④ = 0 이 확인됐으므로 「C(원장 주입)를 계속 갈 것인가」 자체가 열린
질문이다. C 를 살리려면 주입 범위를 「엔진 flat」 밖으로 넓혀야 하는데 ADR-022 는 그것을
**멱등성 붕괴**로 이미 기각했다(§대안 「원장으로 전면 덮어쓰기」). 즉 **설계 축을 다시 골라야
한다** — 이것이 P0([BL-003])의 실질 게이트다. 사용자 결정 사항이라 코드보다 질문이 먼저다.

**B. [BL-581] 처분** — `.metrics` **14,905/20,000 파일**, **+175 파일/h** ⇒ 약 **29시간** 뒤 Trigger.
스크레이프 이미 **2.67초**. ★**counter 파일을 지우는 것은 금지**(창 차분 계측이 재기동 생존을
전제한다)라 처분에는 설계가 필요하다. **소크 창의 상한**이므로 A 보다 먼저 와야 할 수도 있다.

**C. 유도 함수 재설계**([BL-591] 슬라이스 1.5) — `trade_id` 재사용과 배수량 반전을 견디는 legs
분해. ★**A 의 답이 「C 안을 접는다」면 이 작업은 통째로 불필요하다.** A 를 먼저 답해라.

### 착수 전 반드시 읽을 것

- ★**소크가 살아 있으면 `backend/src` 편집 · 변이 테스트 · BE pytest 전면 금지**다
  (`drop_all` 이 소크 원장을 든 개발 DB 를 겨냥한다). 먼저 `scripts/soak-observe.sh` 로 생존을 재라.
- ★**「기다린다」를 고르기 전에 그 지표가 그 창에서 발화 가능한지 계산해라.** 이번 회차도 계산이
  선택지를 바꿨다(19 tick 짜리 창으로는 ①②③⑤ 를 못 잰다 → 과거 원장 재생으로 경로 교체).
- ★**작은 창의 0 은 0 이 아니다** — ⑤가 소크 19 tick 에서 **0/19**, 과거 29세션에서 **27.6%** 였다.

### 비목표

슬라이스 2(실제 주입·관망) — ★**재개 조건 3개를 다 채우기 전에는 착수 금지**
([ADR-022 §슬라이스 2 재개 조건](decisions/022-engine-position-ssot.md)).
[BL-580] 잔여 96곳 · [BL-578] 취소 사유 영속화 · [BL-389]/[BL-466] 파산 모델 · [BL-462] · mainnet.

---

## ⛔ 종료 — **engine-position-ssot 슬라이스 1** (완료 · 참고자료)

> ★**진입점은 여기가 아니라 위 블록이다.** 상세는
> [dev-log](dev-log/2026-08-04-engine-position-ssot.md) · [ADR-022](decisions/022-engine-position-ssot.md).

### 무엇을 했나

- **슬라이스 1(계측) 머지** — `trading/ledger_position.py` 신설(원장 → 열린 포지션 유도, 순수 함수) +
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
`/metrics` 파일 수([BL-581] Trigger 20000) ·
`qb_live_conditional_guard_total{breach_with_resting}` vs `{market_converted}`([BL-589] 수리 관측축) ·
`qb_live_conditional_guard_total{recovery_placed}`([BL-590] 수리 관측축 — 증가하면 그 시점
원장에 `condmkt` 주문이 짝으로 있는지 확인해라. `recovery_expired` 가 증가하면 **브로커 적체**다) ·
`qb_live_ledger_derive_total` / `qb_live_ledger_veto_total` / `qb_live_ledger_hold_resolved_total`
([BL-591] 슬라이스 1 계측 — ★`derive_total` 이 **증가 중**인지가 「계측이 돌고 있다」의 유일한 증거다.
「코드가 mount 됐다」와 다르다. 교차 확인은
`live_signal_states.last_strategy_state_report._qb_ledger_shadow` 의 `updated_at`) ·
마이그레이션 head `20260801_0001`.

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

- 직전 회차 — [`engine-position-ssot`](dev-log/2026-08-04-engine-position-ssot.md)
  (슬라이스 1(계측) 머지 **PR #539** · **슬라이스 2 미착수 확정**. ★★★**계측이 초록인데 주입될
  값이 틀렸다** — 유도 함수의 **net 은 맞고 legs 는 틀리다**(외부 오라클 11건: 오답 0, 적중 4가
  전부 `legs=2` 인데 거래소는 단일 포지션). 슬라이스 1 은 net 으로 `agree` 를 판정하고 슬라이스 2 는
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
