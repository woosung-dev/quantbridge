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

## 다음 스프린트 — **soak-divergence-root + trust-envelope**

> ★**이것이 다음 세션의 유일한 진입점이다.** 별도 킥오프 파일을 만들지 않는다.
> ★**`AGENTS.md` 는 읽지 마라 — 자동 로드된다.** `CONTEXT.md` 는 반대다(읽어야 들어온다).

**두 덩어리를 한 세션에 묶되 순서를 지킨다. A 가 먼저고, B 는 A 가 시계를 다시 켠 뒤 그 창이
도는 동안 한다.** B 를 먼저 하지 마라 — 계측 부채는 무한하고 오프라인 검증이 가능해서 항상
그쪽을 고르게 되고, 그래서 실주행 시계가 며칠씩 멈춰 있었다(2026-08-03 방향 재판정).

★**작업 위치 = 메인 체크아웃. 워크트리를 쓰지 마라.** A 의 검증은 celery 경유라 워크트리에서
구조적으로 불가능하고(워커가 메인 `src` 를 mount), 지금은 소크가 꺼져 있어 메인의 `backend/src`
편집이 안전한 창이다. **재가동 전에 A 수리를 끝내라.** 굳이 워크트리를 쓴다면 python 을 **3.12 로
핀해라** — bootstrap 의 `uv sync` 가 3.13 을 집어 직전 회차가 CI 가 재현 못 하는 baseline 을
만들었다(실측 사고, [BL-587]).

### A. [BL-589] — 소크를 65분에 끊은 발산 (P1)

`engine +0.030392388292696512` vs `exchange −0.03`. 방향이 정반대다. 체결분만 더하면 거래소는
정확히 −0.03 이 맞다 ⇒ **거래소 원장은 일관적이고 엔진만 틀렸다.** `10:38:46` 반전 주문
`buy 0.06` 이 `10:56:41` 에 **취소**된 53초 뒤 첫 divergence. [BL-560] 의 거울상이다 —
그쪽은 「반전이 **체결**됐는데 모른다」, 이쪽은 「**취소**됐는데 됐다고 믿는다」.

1. **preflight** — 위 숫자를 네가 다시 재라(주문 원장 + 워커 로그). 앞 세션의 측정도 대조 대상이다.
2. **A1 · 엔진 포지션의 출처 확정** — ★**이 한 가지가 수리 위치를 완전히 바꾼다. 확정 전 코드
   수정 금지.** (a) 값이 **체결 원장**에서 오나 **자체 시뮬레이션**에서 오나 (b) `+0.0304` 의
   출처(거래소는 `qty_step` 절삭으로 `0.03` — 엔진은 발주 수량이 아니라 **의도 수량**을 드는가)
   (c) `cancelled` 시 엔진 상태를 되돌리는 경로가 있는가, 있다면 왜 안 탔나 (d) 2회 연속
   divergence 비활성화 정책이 맞나.
3. **A2 · 취소 사유가 없다** — T0 이후 7건 중 **4건이 cancelled 인데 `error_message` 가 전부
   NULL**. 사유 없이는 「왜 취소됐나」를 영원히 못 센다([BL-578] 계열). A1 이 막히면 이게 먼저다.
4. **A3 · 수리 + 재가동** — 수리는 소크가 꺼진 상태에서 끝내고, 재가동 후
   `scripts/soak-observe.sh --baseline --session <새 uuid>` 로 앵커를 다시 잡아라.
   ★재가동 후 **최소 1시간은 관측만** 해라 — 65분에 끊긴 창이라 그 구간 통과가 1차 증거다.

### B. 정답지 envelope 마무리 ([BL-587] → [BL-585] → [BL-588])

★**A3 재가동 뒤에 착수한다.** 전부 `tests/`·`scripts/`·설정 파일만 건드려 `backend/src`
무접촉이라 소크와 병행 안전하다. 반나절 분량이다.

1. **B1 · `.python-version` 핀** — 핀이 없어 `uv sync` 가 최신을 집는다. **검사보다 원인 차단이
   먼저다.**
2. **B2 · envelope 검증 assert 3건** — `ohlcv_sha256`·`schema_version`·`tool_versions.python` 을
   **읽는 곳이 하나도 없다**. ★(c) 의 red 는 「회귀」가 아니라 「regen 하고 값이 같은지 확인해라」
   신호다 — assert 메시지에 그렇게 써라. 안 그러면 다음 사람이 값을 손으로 고친다.
3. **B3 · 스키마를 켜거나 지워라** — `baseline_metrics.schema.json` 은 어디서도 로드되지 않는다
   (`jsonschema` import 0건). **「있지만 안 도는」 상태가 가장 나쁘다.** 지우는 쪽도 정답일 수
   있다 — dataclass 가 이미 SSOT 다.
4. **B4 · 코퍼스 목록 3중 정의**(30분) — parity 7벌 / regen 7벌 / `_MUTATION_CORPORA` **5벌**.
   판별력을 만든 비축퇴 2벌이 nightly 에 확산 안 됐다. 5→7 만 해도 감지율이 오른다 —
   **단 nightly 소요를 먼저 재라.**

### 사전등록 (착수 전에 문턱을 적어라)

- **A-V1** A1 의 「엔진 포지션 출처」를 **코드 인용으로** 확정. 「~일 것이다」는 미달.
- **A-V2** 수리 후 인위로 반전 주문을 취소시키면 엔진이 되돌아간다(또는 divergence 를 안 낸다).
  ★수리 **전에** 같은 주입으로 현재 동작을 먼저 재서 판별력을 증명해라.
- **A-V3** 재가동 창이 **65분을 넘긴다.** 안 넘기면 원인이 다른 데 있다.
- **B-V1** B2 의 assert 3건이 인위 변조(해시 1글자·schema_version·python minor)에 각각 red.
- **B-V2** B4 후 mutation 감지율이 증가하거나 최소 유지(줄면 새 코퍼스가 노이즈다).

★사전등록 변이가 **판별력 0 이었던 사례가 네 회차 연속** 있었다(직전 회차 V3 포함 — 백로그가
지목한 표적이 **이미 커버돼 있었다**). **「테스트가 green」은 증거가 아니다. 「이 변조에 red 다」가
증거다.**

### 비목표

[BL-586] 골든 51필드 중 13개만 고정 — 별도 스프린트 크기 · [BL-389] v2_adapter finance-math
이동 · [BL-466] 파산 모델 — **사용자 설계 결정 선행** · [BL-462] · mainnet.

### 직전 회차 인계 (2026-08-03 backtest-metric-oracle · PR #534 @ `7df44af9`)

- 거래소 포지션은 flat 으로 정리했다. ★단 **앱 원장을 거치지 않았다** — `ClosePositionService` 가
  HTTP 경로에만 조립돼 있어 provider 를 직접 호출했다. 그 청산에 대응하는 `trading.orders` 행이
  **없다.** 원장을 셀 때 이 구멍을 빼먹지 마라.
- `.soak/session` 앵커는 **죽은 세션**을 가리킨다.
- 게이트 baseline: BE **3906 passed / 46 skipped** · ruff 0 · mypy 0 · FE 1242 · bl-audit active **155**.

---

## ⛔ 종료 — **demo-soak-restart** (창 65분에 끊김 · 재가동 참고자료로만 유지)

> ★**진입점은 여기가 아니라 위 「다음 스프린트」 블록이다.** 이 절은 **재가동할 때 다시 읽을
> 참고자료**로 남긴다 — 함정 목록(§착수 전 반드시 읽을 것)과 T0 baseline 숫자가 그대로 유효하다.
> ★**`AGENTS.md` 는 읽지 마라 — 자동 로드된다.** `CONTEXT.md`·`.ai/rules/*.md` 는 반대다(읽어야 들어온다).

**★시계는 멈췄다.** 세션 `04097fdc` 는 T0 65분 뒤 `position_divergence`(`direction`)로
fail-closed 비활성화됐다 ⇒ **[BL-589]**. 아래 「창 종료 `2026-08-05T09:53Z`」 는 **성립하지 않는다.**
재가동 전 일별 주문은 `07-30: 86 · 07-31: 53 · 08-01: 5 · 08-02: 3 · 08-03: 0` 이었고 마지막
라이브 신호 이벤트는 **07-31** 이었다. **P0 [BL-003] 의 Trigger 는 「Bybit Demo 1주 안정 운영 후」**
라 이 시계 말고 P0 를 여는 길이 없다 — **그래서 [BL-589] 가 P0 를 막고 있는 유일한 장애물이다.**

| 항목      | 값                                                                      |
| --------- | ----------------------------------------------------------------------- |
| 세션      | `04097fdc-0322-4a23-bfcc-d9f7c7a7e2b3`                                  |
| T0        | `2026-08-03T09:53:34.451807+00` (★창은 시계가 아니라 이 값이다)         |
| 조합      | 전략 `07a22564` PbR · 계정 `19a8166a` bybit/demo · `BTC/USDT` · `1m`    |
| 파라미터  | leverage 2 · isolated · size 1.0% · equity baseline 190422.997 USDT     |
| 창 종료   | **`2026-08-05T09:53Z` 이후** (≥48h)                                     |
| 관측      | `scripts/soak-observe.sh` (앵커는 `.soak/session`, gitignore)           |
| 유도 주입 | 이벤트 `ca3c645f` — `sequence_no=9999` + `trade_id='h8_probe'` **합성** |

### 재가동 후의 일일 절차 (창이 다시 돌 때 유효)

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
