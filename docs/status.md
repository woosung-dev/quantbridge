# QuantBridge — TODO

> **Last Updated:** 2026-07-28 (**live-outcome-parity** — 라이브가 백테스트대로 **버는지** 물을 수 있는 자를 만들었다)
> **Active Sprint:** 없음 — `feat/live-outcome-parity` PR 대기. **다음 스프린트는 아래 §다음 스프린트 참조.**
> **Last Merged:** `feat/live-entry-parity` → `main@274dc645` (PR #493)

---

## 🎯 다음 스프린트 — live-close-completeness (BL-530 + BL-522)

> ★**이것이 다음 세션의 유일한 진입점이다.** 별도 킥오프 파일을 만들지 않는다.
> 시작 방법: **"다음 스프린트 진행해줘"**. 에이전트는 `CONTEXT.md` + `AGENTS.md` + 본 파일을 읽고 시작한다.

**한 줄.** 직전 회차가 만든 자가 **첫 숫자를 냈다** — 엔진이 청산했다고 본 것의 **71%가 거래소에서 확정되지 않는다**(51/72). 그 유실을 분해하고 닫는다.

**본체 = BL-530**(청산 유실 51건) + **BL-522**(진입 완결성). 둘은 같은 뿌리일 가능성이 높다 — 거절 상당수가 "reduce-only 대상 포지션 부재" 계열이고, 그건 진입이 애초에 안 걸린 것의 하류 효과다.

### 왜 지금인가 (2026-07-28 실측, outcome-parity 표면이 낸 값)

| 항목             | 값                           |
| ---------------- | ---------------------------- |
| close 이벤트     | **72**                       |
| 거래소 확정      | **21 (29%)**                 |
| dispatch failed  | **16**                       |
| order rejected   | **35**                       |
| 왕복 실효 비용률 | **0.1115%** (손계산과 일치)  |
| leg 당 net       | **-1.28** (표본 9 < 필요 30) |

★**엔진은 포지션이 닫혔다고 보고 다음 신호를 평가하는데 거래소에는 남아 있을 수 있다.** 시뮬과 실제의 포지션 상태가 갈린다. 실자금 cutover 전 필수다.

### ★설계 시 반드시 짚을 것

1. **첫 step 은 기계적 수리가 아니라 원인 분해다.** 거절 코드별로 쪼개 진입 유실 하류인지 독립 결함인지 판정하고, 그 다음에 고친다.
2. **BL-522 와 묶어서 본다.** 따로 고치면 같은 뿌리를 두 번 만난다.
3. 직전 회차가 만든 `GET /live-sessions/{id}/outcome-parity` 가 **before/after 계측기**다. 새 계측기를 만들지 마라.
4. ★**그 계측기 자체를 믿기 전에 BL-527 을 확인해라** — `trade_id` 재사용 + catch-up 다중 emit 이 기대치를 오염시킬 수 있다(잠재, 실데이터 미재현).

### 하지 않는 것

BL-527/528/529(전부 P2) · 거래소 확장 · `tasks/` deepen · 옵티마이저 · 표본을 늘리기 위한 장시간 soak(그건 이 스프린트의 목표가 아니다).

### baseline (2026-07-28 실측, 본 브랜치 기준)

BE **3385** / FE **1212**(203 파일) / e2e authed **65** · canon **32** · CI전용 **4** / cov **93.14%** / ruff·mypy(212)·tsc·eslint 0 / 마이그레이션 **0**.

---

## ⚡ live-entry-parity — 라이브가 백테스트의 진입 절반을 버리는 것을 멈춘다 (BL-511 · BL-512) (2026-07-28)

**스코프.** 조건부 진입 가드의 stale 기준가 수리(BL-511) + 거래소 응답 계측 신설(BL-512) + `fill_timing` 라이브 배선. **마이그레이션 0.** 방법론 = Generator/Evaluator 파이프라인 **3/3 검증 회차(승격 조건 충족)**.

### ★본체 결과 (62분 soak 실측)

| 축                      | before            | after                        |
| ----------------------- | ----------------- | ---------------------------- |
| 조건부 주문             | 67                | 19                           |
| **거절률**              | **43.3%** (29/67) | **0%** (0/19)                |
| **`110093`**            | **29건**          | **0건**                      |
| 시장가 전환             | 기능 없음         | **5건 전부 체결**            |
| 거래소 오라클(raw HMAC) | —                 | **26주문 전부 `EC_NoError`** |
| kill switch             | 0                 | 0                            |

**가설이 맞았다.** 가드 기준가가 마지막 종료 bar 종가라 최대 60초 스테일이었고, 실시간 perp last price 로 교체하니 `110093` 이 사라졌다. 돌파된 트리거는 **시장가로 전환**한다 — 우리 백테스트 엔진이 그 상황을 다음 bar 시가에 체결하므로(`strategy_state.py:67-84`) 그게 패리티다.

### ★핵심 발견

- ★★★**적대 검증이 스프린트를 구했다 — 가드 기준가가 perp 이 아니라 스팟이었다.** 실거래소 실측: `ccxt.market("BTC/USDT")` = **spot**, perp 은 `BTC/USDT:USDT`. 그 순간 **스팟-perp 차이 34.50 USDT(0.0543%)** 인데 우리가 잡으려던 돌파폭은 **중앙값 15.60(0.025%)** 이었다. **측정 오차가 신호보다 컸다** — 그대로 soak 을 돌렸으면 숫자는 나와도 무엇을 뜻하는지 알 수 없었다. 덤으로 `fetch_mark_price` 는 도입 이래 mark 를 읽은 적이 없다(ccxt ticker 에 `"mark"` 키 자체가 없고 `info.markPrice` 에 있다).
- ★★**G1 플랜 검증이 "계측이 성공을 못 세는 설계" 를 코드 쓰기 전에 잡았다.** Bybit demo 는 **시장가도 `submitted` 로 응답**하고 체결은 WS 가 확정한다. `filled` 만 accepted 로 셌다면 그 카운터는 **영구히 0** 이었다 — soak 실측(`accepted/submitted` 27 · `filled` 0)이 사후 증명했다.
- ★★**같은 렌즈가 예측한 `110017` 오분류가 soak 중 실제로 발생했다.** `110017` 은 "포지션 0" 이 아니라 **"reduce-only 규칙 위반"** 이고(ccxt 에러맵), 실제 메시지가 `"reduce-only order has same side with current position"` 이었다. 정정하지 않았다면 **포지션 반전 부작용이 "무해" 로 위장**됐을 것이다.
- ★★**cross-bar 이중 진입 억제기가 실제로 발화했다**(`convert_suppressed` 1). 시간·경합 렌즈가 요구한 방어인데 이론이 아니라 실재하는 경합이었다.
- ★★**롱 돌파 거절코드를 통째로 놓치고 있었다** — `110092`(롱, "expect Rising") vs `110093`(숏). 우리 데이터가 100% short 라 안 보였을 뿐이다.
- ★★**G6 가 평가자 수선 2줄 중 하나가 fail-closed 를 깬 것을 잡았다**(8세션 연속 P1). `[]` → `.get(..., 3600)` 이 창만 넓힌 게 아니라 **전환 허용 여부까지 바꿨다.**
- ★★**평가자(나)의 계측기가 3번 틀렸다** — 변이 오조준 2건(동치 지점에 주입 / 두 가드가 같은 mock 으로 서로를 가림) + mmap 4-튜플 오판독 1건(**1389개 파일 전부에 metric 0개**라는 오답). 셋 다 "시스템이 고장났다" 로 갈 뻔했다. **측정값이 0이면 대상보다 계측기를 먼저 의심해라.**
- ★**남은 유실 채널의 크기가 처음 측정됐다** — `deferred_market_inflight` **시간당 14회**. 조건부 모델에선 무해했지만 1-shot 전환에선 유실이다 → **BL-522(P1)** 로 등재. 이번엔 계측만 하고 고치지 않았다(크기를 모르는 채 새 상태 저장소를 만드는 것이 최대 위험).
- ★**배포 시 화면이 깨질 뻔했다** — FE zod 스키마가 `.strict()` 인데 백엔드가 신규 키를 싣기 시작해, **라이브 설정을 한 번 저장하면** 전략 응답 파싱이 throw 한다. W4 에서 회귀 테스트와 함께 수리.

### 게이트 (실측)

BE **3341**(baseline 3277, +64) / 커버리지 래칫 **93.14%**(기준 90) / FE **1191**(baseline 1182, +9) / ruff·mypy(209)·typecheck·lint **0** / `pnpm build` ✓ / e2e:authed **65** · canon **32** / rules-of-hooks grep 통과 / **마이그레이션 0**.
변이 **누적 21종 전건 판별** — W1 5 · W2 10 · W3 2 · W6 3 (+ 탈출 3건은 전부 계측기 결함으로 재조준 후 검출).

### Completed

- [x] **BL-511** 조건부 진입 가드 기준가 → 거래소 실시간 perp last price + 돌파 시 시장가 전환(resting 없을 때만) + 사용자 상한 `max_trigger_breach_pct`
- [x] **BL-512** 거래소 응답 축 계측(`retCode` 정규화 · `unknown` outcome 분리) + guard 판정 계측 7종 + `exchange_missing` 오계상 수정
- [x] `run_live` 에 `fill_timing` 배선(5번째 미배선 인자) + `StrategySettings` 미러 + FE 노출 + 백테스트 폼 불일치 배지
- [x] `gates-and-traps.md` §3.5 컨텍스트 예산 **실제 승격**(직전 핸드오프가 "있다" 고 적었으나 없었다) + 거래소 실상·계측기 함정 승격
- [x] 파이프라인 §6 **2/3 소급 등재 + 3/3 등재**

### Next Actions

- [ ] **BL-522 (P1)** 진입 완결성 — 유실 채널 5종. 실측 크기(시간당 14회) 위에서 설계
- [ ] **BL-523 (P2)** 조건부·전환 진입에 TP/SL 브래킷 부착
- [ ] **BL-516 (P2)** 조건부 진입 `reduce_only=False` 하드코딩
- [ ] **BL-508/509** metric gauge 스냅샷 전환 + 파일 회수 (**결합 의무** — 순서 뒤집으면 즉시 깨진다)
  > **요약:** **BL-506 Resolved** — `PROMETHEUS_MULTIPROC_DIR` + `MultiProcessCollector` 로 worker 계측을 스크레이프 가능하게 만들었다(마이그레이션 **0**, 기능 추가 **0**). 배선하자 **보이자마자 믿으면 안 된다는 것**이 드러났다 — `qb_active_orders` 가 0 인데 실제 in-flight 는 1(BL-508, 산술 전건 설명됨). **stand-down 을 유도해 발화·해제를 3층 증거로 관측**했고, **거절률 50%**(38건 중 19건, 100% `110093`)라는 백테스트↔라이브 발산을 실측했다(**BL-511 P1**). **판정표** = 관측됨 11 / 관측 안 됨 9 / 구조적 관측 불가 10. **BL-499 정정** — trigger 는 여전히 미발화지만 **관측 가능성 자체는 확보**됐다. **Generator/Evaluator 파이프라인 2/3 검증.** 신규 BL-508~521.

## ⚡ live-observability — 계기판을 연결하고 실제로 읽는다 (BL-506) (2026-07-28)

**스코프.** worker 프로세스 metric 스크레이프 배선(BL-506) + 라이브 데모 실주행 관측 + BL-499 정직한 종결 판정. **기능 추가 0 · 마이그레이션 0.**

### ★핵심 발견

- **G0.5 선행 스파이크가 설계를 살렸다.** `prometheus_client` 의 mmap 계층에 `msync` 호출이 **하나도 없어** 컨테이너→호스트 전파가 소스로 보증되지 않는다. 실측하니 전파는 되지만 **최대 18~20초 지연 + 버스트**였고, **PID 충돌은 파괴적**이었다(컨테이너 2개가 둘 다 PID 1 → 같은 파일 → 값이 실증분과 어긋남). 실제 배포에서 **네 컨테이너 master 가 전부 pid 51** 이라 role 접두어가 없었으면 그대로 재현될 뻔했다.
- ★★**보이게 만들자마자 그 metric 을 믿으면 안 된다는 게 드러났다.** `qb_active_orders` **0.0** 인데 DB 실제 in-flight **1**. 산술 전건 설명 — 재기동 후 생성 +7 / 종료 −6 / **재기동 이전 생성→이후 종료 1건의 고아 dec −1**. 배선 전엔 API `inc` 만 잡혀 **단조 증가**였으니 더 나빴다. BL-506 이 한 일은 **편향을 보이게 만든 것**이다(BL-508).
- ★★**거절률 50%** — soak 창 주문 38건 중 **거절 19건, 100% 가 `110093`**("트리거가 이미 지났다"). 시각이 연속 분 클러스터라 **매 tick 같은 값으로 재시도하는 루프**다. 원인은 가드의 기준가가 **마지막 종료 bar 종가**인데 거래소는 **현재가**로 판정하는 것(최대 60초 스테일). **백테스트가 의도한 진입의 절반이 라이브에서 조용히 사라진다**(BL-511 P1).
- ★**stand-down 유도 실험 성공** — 같은 계정·심볼에 2번째 세션을 2분 39초 올려 metric 2종 + 로그 3건 + **행동(창 안 신규 등재 0건)** 3층으로 발화를 잡고, 중단 후 재개(placed 16→18)로 해제까지 확인. **배선 없이는 불가능한 관측이었다.** 그 실험이 새 결함도 냈다 — **발화는 알아도 사유는 알 수 없다**(BL-514).
- ★★★**G6 최종 리뷰가 7세션 연속 P1** — `order_service.py` 의 **diff 는 0줄인데** `qb_active_orders.inc()` 가 in-memory 증가에서 **공유 mmap 쓰기**로 바뀌어, 예외 시 주문 행은 commit 됐는데 발주가 안 되고 멱등 캐시가 재시도를 삼켜 **영구 미발주**가 된다. **파일을 안 건드려도 머니-패스가 바뀐다.**
- ★**평가자(나)의 3줄 수선이 fail-open 을 만들었고 리뷰가 잡았다** — `metrics-wipe` 를 `exit 1`→skip 으로 바꾸면서 `docker compose ps` 자체가 실패하는 경로에서 **살아 있는 파일을 지우는** 분기를 열었다(fail-closed 로 재정정).
- ★**측정 오류를 스스로 3건 잡았다** — 카운터가 **감소**해 보인 건 샘플러 엔드포인트 교체가 기준선에 섞인 것 · `placed +2 vs DB +4` 는 창 경계 + 전파 지연 인공물(누적 재측정에서 정확 일치) · stand-down 3번째 증가가 해제 이후인 줄 알았으나 로그 실제 시각은 창 안. **성긴 샘플링으로 인과를 뒤집을 뻔했다.**
- ★**함정 재확인** — 변이 복원에 `git checkout <file>` 을 써서 신규 코드 6곳이 통째로 날아갔고, 의무화된 **"복원 확인 실행"이 그걸 잡았다**(2회 연속 이 단계가 사고를 잡음).

### 게이트 (실측)

BE **3277**(baseline 3249, +28) / FE **1182** / e2e authed **65** · canon **32** · CI전용 **4** / ruff·mypy(209)·tsc·eslint **0** / build ✓ / 마이그레이션 **0**.
변이 **25종 전건 판별(실패 0)** — M1~M11(배선) · X1~X8(회귀 수정) · Z1~Z6(P1) + 음성 3종 green 유지.

### soak 실측 (T0 02:48:16Z → 04:27:59Z, **1시간 40분**)

계획은 3~4시간이었으나 관측이 조기 포화돼(정상 경로 전 장치 주행 + stand-down 발화·해제 유도 완료) 앞당겨 종료했다.
조건부 진입 **67**건 · 체결 **4**(창 내) · 거절 **19** · 취소 **15** · 실현손익 **−2.96 USDT** · kill switch **0** · `multiproc_files` 50→54 · `scrape_seconds` **24샘플 0.01 고정**(파일 누적 열화 미관측).

## ⚡ live-ops-hygiene — 조건부 진입 운영 위생 (BL-503 · BL-501 · BL-502) (2026-07-28)

**스코프.** 4스프린트 연속으로 만든 라이브 조건부 진입이 남긴 **정리 주체 부재(BL-503)** + 계정 스코프 표의 **누르면 실패하는 버튼 두 축(BL-501/502)**. 새 기능 없음. **마이그레이션 1건.**

### ★핵심 발견

- **★★★게이트가 전부 green 인 상태에서 P1 이 세 번 나왔다.** 거래소 오라클(Bybit 이 `orderId` 를 우선해 **살아 있는 주문을 "미발주" 로 오판**), 변이 주입(**거짓 게이트 3건** — cutoff 를 0으로 무력화해도·과차단으로 바꿔도·`commit()` 을 지워도 통과), codex 최종 리뷰(**접기가 hedge 의 실포지션 leg 를 화면에서 지움**). 원인은 하나 — **생성자가 쓴 테스트는 생성자의 구현을 비춘다.** codex 의 테스트는 ccxt 를 mock 하므로 거래소 실동작을 구조적으로 볼 수 없다.
- **★★내 결론이 거래소에 반증됐다.** "`trigger=True` 없이는 조건부 주문을 못 본다"(codex 도 독립적으로 같은 결론)는 **틀렸다** — 진짜 `orderId` 로 조회하면 `orderFilter` 유무와 무관하게 나온다. 나와 codex 는 **같은 내부 증거(ccxt 소스+우리 코드)** 를 봐서 독립 표본이 아니었다. 게다가 그 필터는 **트리거된 주문을 숨겨** 체결을 `rejected` 로 찍을 수 있었다.
- **★★초안이 장부 잡음을 관리 불가 실주문으로 바꿀 뻔했다.** form 1 을 "물어볼 대상이 없으니 `rejected`" 로 처분하려 했는데, dispatch 는 `create_order`(거래소 등재) → `attach_exchange_order_id` 순서라 **그 사이에 죽으면 주문은 거래소에 살아 있다.** 물어볼 대상은 있었다 — `orderLinkId = str(Order.id)`.
- **★★화면 검증이 P1 을 통과시켰다.** 실포지션을 열어 접기 1행·실클릭 체결·거래소 flat 을 3중 대조로 확인했는데, dogfood 계정이 **one-way 단일 leg** 라 hedge 은폐가 재현되지 않았다. **화면에 없는 상태는 화면 검증이 못 본다.**
- **★uid 로 접되 청산은 계정 id 로.** 세션 귀속·자격증명이 `exchange_account_id` 에 묶여 있어 "uid 대표만 조회" 로 갔으면 read-only 형제가 세션을 가진 경우 **청산 버튼이 오히려 사라진다.** 그래서 접기는 표시 전용이고 `close_service` 는 무변경이다.

### Completed

- [x] **BL-503** 조건부 진입 janitor(beat 5분) + sweeper 를 예외추론→probe 확인으로 교체
- [x] **BL-501** `exchange_uid`·`read_only` 마이그레이션 + 등록 1회/beat 백필 + 표시 전용 접기 + readOnly 이중 차단 + uid 형제 캐시 무효화(3 사이트)
- [x] **BL-502** 포지션 단위 `mutationKey` 공유 lock
- [x] roadmap 4d 드리프트 3건 정정(폐기된 나이 게이트가 출시된 것처럼 · BL-503 누락 · PR 번호 부재)
- [x] `docs/guides/generator-evaluator-pipeline.md` 신설 + README 목차 등재

### 게이트 (실측)

BE **3249**(baseline 3212) / 커버리지 래칫 통과 / FE **1182**(baseline 1175) / ruff·mypy·typecheck·lint 0 / `pnpm build` ✅ / e2e:authed **65-0** · canon **32** · CI 전용 **4** / **alembic fresh chain ✅**(throwaway DB) / **변이 28건 전건 판별, 실패 0**.

### Blocked / 확인 필요

- **배포 순서가 강제되어야 한다** — 새 ORM 필드가 모든 `ExchangeAccount` select 에 즉시 포함되므로 **마이그레이션 → 코드** 순서여야 한다. 코드가 먼저 뜨면 `UndefinedColumn`. 롤백은 반대(코드 → 마이그레이션). nullable 추가라 구 코드와는 호환된다.
- **BL-506** — worker 프로세스의 metric 이 스크레이프되지 않는다. BL-503 이 닫았다고 적은 gauge 표류가 **배포 토폴로지에서는 보이지 않는다.** metric 기반 trigger(BL-499 포함)가 이 상태에선 성립하지 않는다.
- `AGENTS.md` / `docs/backlog.md` 의 `/claude-md-improver` 산출물(BL-504 포함)이 이 브랜치 작업 트리에 있다. **스코프 밖이라 내 커밋에서 제외**했다 — 이 PR 에 포함할지 사용자 결정 필요.

### 신규 BL

- **BL-505** [P3] 청산 lock 축이 포지션 정체성이 아니라 `sessionId + symbol`
- **BL-506** [P2] worker metric 미스크레이프 → gauge 규율 전체가 관측 불가
- **BL-507** [P3] 접기·청산 가능성 판정이 view 안에 (이번 P1 이 그 경계에서 나왔다)

### Next Actions

- [ ] 사용자 PR 리뷰 → squash 머지
- [ ] 머지 후 **마이그레이션 → 코드** 순서로 배포, worker/beat 재기동
- [ ] 파이프라인 2/3 회차 — 태스크 스펙에 "DB 의존 테스트는 평가자가 돌린다" 명시 + **표적 변이를 수용 기준에 포함**해 생성자가 처음부터 만족시키게 한다

---

## ⚡ live-conditional-hardening — 잔여 노출·견고성 (BL-498 · BL-499 · BL-500) (2026-07-27)

**스코프.** 라이브 조건부 진입 실전 투입 직후, 그 경로가 남긴 **관리 불가 노출 1건 + 무음 미진입 2건**. 기능을 늘리지 않는다. **마이그레이션 0.**

### ★핵심 발견

- **preflight 가 BL-498 을 줄였다.** `close_position` 이 세션 `is_active` 를 **요구하지 않는다** — 비활성 세션 id 로도 청산된다. 막힌 건 화면이 활성 세션만 순회하는 것뿐이었다. 신규 청산 경로 0, **읽기 엔드포인트 1개 + 화면**으로 닫혔다.
- **★★내 preflight 결론이 틀렸고 codex 가 반박했다.** "취소 16건이 전부 `exchange_order_id` 를 보유 ⇒ DB-only 취소 경로 미주행" 은 성립하지 않는다 — **패배한 호출은 행에 아무것도 안 쓴다.** 증명된 것은 "DB-only 취소 _성공_ 0건" 뿐이다.
- **★★dogfood 가 결함을 더 찾았다.** 등록된 두 계정이 **같은 Bybit uid `558689281`** 이라 같은 포지션이 두 행으로 나왔고, 그중 하나는 `readOnly=1` 이라 청산 버튼이 실패한다(BL-501 등재, 이번엔 각주 고지까지).
- **★★★e2e 가 dev 서버의 stale CSS 로 거짓 red 를 냈다.** 소스·프로덕션 빌드에는 `.pager-nums{flex-wrap:wrap}` 이 있고 **dev 서빙본에만 없었다.** 프로덕션 빌드를 별도 포트에 띄우니 그 캐논이 통과했다. 이 함정의 **4차 재발**이고 처음으로 게이트를 red 로 만들었다.

### Completed

- [x] **BL-498 ✅ Resolved.** `GET /exchange-accounts/{id}/positions` + 코크핏 §03 "계정 잔여 포지션" 표(세션별 대조 **위**). ccxt `fetch_positions()` 심볼 없는 1콜. 청산 가능 판정을 **서버에서** — `no_owning_session` / `hedge_unsupported`. 조회 범위(USDT linear 전용) 고지.
- [x] **BL-500 ✅ Resolved.** 거래소 목록에 없는 로컬 행을 **`fetch_order` 로 직접 물어** terminal 확인 뒤에만 `actual` 에서 제거(확인 못 하면 유지). 체결 확인 시 그 tick 등재 중단. ★중간에 넣었던 **나이 게이트 3분은 적대 검증이 반박해 폐기**했다 — reconcile 은 bar 마다 돌고 `submitted_at` 은 부재의 나이가 아니다.
- [x] **BL-499 🟡 부분 완화.** `cancel_raced` / `cancel_stalled` 분류 metric + **패배해도 `to_place` 는 건너뜀**(fail-closed). 근본 경합은 열려 있다.
- [x] **G0.5 codex 8건 + G3 적대 검증 3렌즈 9건 전건 재현 판정** — 수정 13 / 기각 2 / BL 등재 3.
- [x] **표적 변이 15종** 전부 의도한 테스트만 red, 음성 green 유지.
- [x] 게이트: BE **3212**(+33) · 커버리지 **93.21%** · FE **1175**(+14) · canon **32** · **e2e:authed 65-0** · ruff·mypy·tsc·lint 0 · **마이그레이션 0**

### ★★dogfood — 3중 대조 종단 증명

활성 세션 **0건** 상태에서 raw HMAC 으로 **우리 앱 밖에서** 포지션을 만들고, 화면으로 닫았다.

```
진입(앱 밖) d74c5206 Buy  0.002 @65331.1  → 코크핏 §03 렌더된 화면에 표시
청산(화면)  bedc278b Sell 0.002 @65315.1 reduceOnly=True  orderLinkId=a8765854…
우리 원장 a8765854 = 거래소 orderLinkId / exchange_order_id bedc278b = orderId / 65315.1 = avg
거래소 포지션 legs=0 (독립 raw HMAC).  콘솔 error 0.
```

### Blocked

- 없음. ★**e2e:authed 는 dev 서버 재기동 후 65 passed / 0 failed 로 실측 확정**됐다 — 재기동 전 실행의 1건 red 는 Turbopack 이 서빙하던 stale CSS 가 만든 **거짓 red** 였고, 코드는 손대지 않았는데 재기동만으로 사라졌다.

### ★★적대 검증이 "내가 이미 맞다고 쓴 문장" 을 또 반박했다

**계정 스코프 Redis 캐시(15초)를 지우는 코드가 0건**이었다. 쿼리 키를 `positionsPrefix` 아래 둔 것만 보고 "캐시 무효화는 이미 맞다" 를 세 문서에 썼는데 React Query 층에서만 참이었다 — 청산 직후 15초 동안 **닫은 포지션이 살아 있는 청산 버튼과 함께 다시 렌더**된다. ★**dogfood 는 이 창을 못 밟았다**(확인까지 30초 넘게 걸려 TTL 만료 후였다).

★★**그 수정도 처음엔 절반이었다** — 즉시 `filled` 경로만 덮었고 **watchdog 확정 경로**(접수 응답이 `submitted` 이고 position WS 를 놓친 조합)는 빠져 있었다. G6 최종 codex 리뷰가 잡았다. 지금은 즉시 체결·watchdog·WS position 세 경로를 덮는다. 잔여 = WS order 이벤트만 오는 조합(15초 TTL 이 닫는다).

### 신규 BL

- **BL-501 P3** — 같은 거래소 계정을 가리키는 API 키가 둘이면 포지션 중복 + read-only 키에 실패하는 청산 버튼.
- **BL-502 P3** — 세션 표와 계정 표의 청산 버튼에 공유 lock 부재.
- **BL-503 P2** — 제출 중단(`submitted` + `exchange_order_id` NULL)·유령 조건부 진입 행을 아무도 치우지 않는다. `orphan_scanner` 는 면제, WS `Reconciler` 는 `trigger=True` 미사용이라 구조적으로 못 본다.

### Next Actions

- [x] **e2e:authed 재측정 완료** — dev 서버 재기동 후 **65 passed / 0 failed**(3.6분).
- [ ] PR 생성 → **squash 는 사용자**

## ⚡ live-conditional-entry — 조건부 진입 등재 (BL-478 (a) · BL-488 · BL-365) (2026-07-27)

**스코프.** 라이브가 `strategy.entry(..., stop=)` 진입을 **거래소에 올린 적이 없었다.** 시드 `s1_pbr` 은 진입 2개가 100% 이 경로라 라이브를 아예 못 돌았다(세션 `0e15c3c0` 이 8시간 동안 close 29건 / entry 0건). 선언적 reconcile 로 등재·취소·동기화·청소를 배선하고 차단을 푼다. **마이그레이션 0.**

### ★핵심 발견

- **preflight 가 킥오프 전제 4건을 반박했다.** 24h 평가 갭 131바의 원인은 beat 가 아니라 **macOS 클램셸 수면 73바 + 우리 배포창 50바**였고(`pmset` 과 컨테이너 4종 동시 침묵 + RestartCount 0 으로 확정), 서버에서도 나는 진짜 기전은 **늦은 tick 4바(0.29%)** 뿐이었다. 정체는 인프라가 아니라 `run_live` 가 마지막 바 이벤트만 발행하는 계약이다.
- **G0 거래소 실측이 설계 전제 2건을 더 반박해 스코프를 줄였다** — 필터 없는 `fetch_open_orders` 에도 조건부가 보이고(Reconciler 수정 불필요), 현행 `cancel_order` 형태로 취소가 된다(신설 불필요). 문서만 믿었으면 두 파일을 헛되이 고쳤다.
- **★★E1 이 내 설계 지시 자체를 반박했다.** delta 를 방출하면 같은 id 재발행에서 포지션이 **2배**가 된다 — `check_pending_fills` 가 체결 시 같은 id 를 **먼저 닫고 다시 열기** 때문이고 시드 `s1_pbr` 이 정확히 그 형태다. **`target_position`**(체결 후 순 포지션)으로 교체했고, dogfood 가 그 값을 실증했다(시뮬 -0.0291 / 거래소 0 에서 delta 였다면 정확히 2배 발주).
- **E2** = 계획기의 미매칭 정리 루프에 소유 판정이 0이라 **사용자 손절이 지워질 경로**가 있었다. **E4** = 취소 후 재등재가 **거래소에 닿지 않는데 DB·metric 은 "등재됨" 으로 보고**하는 멱등성 재생(키에 `bar_time` 추가로 해결).

### Completed

- [x] **BL-478 (a) ✅ Resolved.** `PendingOrderSnapshot`(`target_position` SSOT) → 순수 계획기 → reconcile 태스크 → provider. 귀속 불변식 5조건(`orderLinkId` UUID · 전략/계정 일치 · `trigger_price` 존재 · `reduce_only=false` · 키 세션 일치)으로 남의 주문·TP/SL·다른 세션 주문을 건드리지 않는다. `trade_id` 는 `idempotency_key` 에 구조적으로 실어 **마이그레이션 0**.
- [x] **BL-488 ✅ Resolved.** `run_live(..., emit_from_bar_time=)` opt-in(기본값 byte-identical). 상한은 **벽시계**(바 개수 아님). 초과는 catch-up 대신 resync — 양쪽 flat 이면 조용히 정상화, 불일치면 비활성화 + 조건부 진입 청소. close dispatch 전 포지션 확인(조회 실패는 fail-OPEN).
- [x] **BL-365 ✅ Resolved.** `entry_trigger_direction` 신설. `trigger_direction_for` 는 청산 side 기준 역시맨틱이라 진입에 재사용하면 정반대가 나온다(프로덕션 호출자 0인 dead code 였다).
- [x] **BL-478 (c) 차단 해제** — 세션 생성 422 와 preflight 자동 종료 제거. 다른 preflight 카테고리는 그대로 차단(음성 대조로 고정).
- [x] **오탐·청소** — `orphan_scanner` 가 쉬는 조건부 진입을 stuck 으로 오판해 30분마다 CRITICAL 을 울리던 것 면제. 비활성화 4경로 + HTTP 정지에서 조건부 진입 청소 + beat 안전망.
- [x] **화면** — 세션 상세 "대기 중인 조건부 진입"(방향·트리거가·목표 포지션). 열린 record 원소를 세 필드 전부 타입 검증.
- [x] 게이트: BE **3179** · FE **1161** · **canon 32** · **e2e:authed 65-0** · ruff·mypy·tsc·lint 0 · **마이그레이션 0**
      ★**BL-495 ✅ Resolved** — `/orders` 캐논 하드 실패 1건은 `.pager-nums` 에 `flex-wrap: wrap` 1줄로 닫았다(453px → 301px, `scrollWidth` 490 → 375). **이번 스프린트 코드 회귀가 아니라** dogfood 가 주문을 62->99건으로 늘려 잠복 결함이 드러난 것이다. ★전 세션의 "`flex-wrap` 이 적용되지 않았다" 는 **재현되지 않았다** — CSSOM 덤프 결과 매치 규칙은 1개뿐이고 HMR 이 즉시 반영했다. 진짜 제약은 그 규칙이 **KITPORT 센티넬 안**이라 `design-canon-kit-port.test.ts` 가 `_kit.html` 정본에 잠근다는 것이었고, 기존 선례 3건과 같은 방식으로 allowlist 4번째 항목 + "실재한다" 테스트를 함께 넣었다.
      ★**내 테스트가 DB 를 오염시켜 랜덤 순서 flake 3건**을 만들었다 — sweeper 프로덕션 경로가 `commit()` 을 해 테스트 트랜잭션 격리가 깨지고 픽스처의 `Strategy` 행이 남아 전략 페이지네이션 카운트를 흔들었다. 픽스처 정리 추가 후 랜덤 순서 3175-0.

### ★★dogfood — 3중 대조 종단 증명

브라우저에서 PbR 세션 시작(어제는 이 동작이 422) → 104분 관측 → **조건부 진입 5건 실체결**.

```
PivRevLE buy  0.029 트리거 65425.90 dir=1(RISE) -> 체결 65429.60   ← 트리거 위
PivRevSE sell 0.029 트리거 65465.20 dir=2(FALL) -> 체결 65461.20   ← 트리거 아래
우리 DB / raw HMAC /v5/order/history 5/5 / /v5/execution/list 5/5 (stopOrderType=Stop, closedSize=0 = 진입)
```

`trading.orders` 의 `reduce_only=f` + `trigger_price` 행이 **62행 중 0 → 생성**됐다. 렌더된 화면(3100, 콘솔 error 0)에도 대기 조건부 진입이 보인다.

**★dogfood 가 P1 2건을 추가 적발했다.** (1) 시드 `position_size_pct` 0.01% 로 목표가 눈금 미만이라 **조용히 아무것도 안 나가는데 화면엔 대기 주문이 뜨는** 되는 척 — 발산 보고로 수정. (2) 이미 돌파된 트리거를 매 tick 재시도해 `110093` 거부 10건 — 참조가로 사전 차단.

**★예정에 없이 G5+G6 이 함께 작동하는 것을 관측했다.** 평가 갭 → 포지션 불일치 → `gap_resync_position_mismatch` fail-closed 비활성화 → sweeper 가 쉬는 주문 전량 취소 → 거래소 미체결 0. 조용히 계속했다면 BL-488 이 만들던 orphan close 가 났을 것이다.

### ★★최종 codex 리뷰가 P1 을 또 잡았다 (4세션 연속)

누적 diff `840b1259..HEAD` 읽기 전용 리뷰 → 지적 6건. **액면 수용하지 않고 각각 코드로 재현 판정**했고, 6건 전부 실재였으나 **등급은 셋으로 갈렸다**.

- **★수정 — 같은 계정·심볼의 다른 전략 세션이 서로의 포지션을 조건부 수량에 섞는다.** 활성 세션 unique 키가 `strategy_id` 를 포함하므로(`uq_live_sessions_active_unique`) 구조적으로 허용되는 배치인데, reconciler 는 **계정 전체** 순포지션을 세션별 target 에서 뺀다. 전략 A 가 +1 보유 중 전략 B 가 -1 을 목표하면 B 는 수량 2 를 내 **A 의 포지션까지 닫고 반전**시킨다. hedge mode 분기(기존엔 그냥 `return` 이라 **이미 올려둔 주문을 남긴 fail-open**)와 함께 **stand-down 단일 기전**으로 통합했다 — 포지션 산술을 신뢰할 수 없으면 발주를 멈추고 **우리 주문을 걷는다**(취소는 포지션을 늘리지 않으므로 항상 안전).
- **★수정 — 화면이 엔진 의도를 거래소 등재로 말하고 있었다.** "대기 중인 조건부 진입" 의 출처는 `last_strategy_state_report.pending_orders`, 즉 **reconcile 이전**에 저장된 엔진 desired set 이다. 눈금 미만·트리거 기돌파로 계획기가 발주를 걷어내도 화면은 그대로 "대기 중" 이라고 말한다. ★**이 스프린트가 "되는 척을 없앴다" 고 쓴 것은 과장이었다** — 발산을 시끄럽게 만든 곳은 로그·metric 이지 화면이 아니었다. 제목을 **"전략이 의도한 조건부 진입"** 으로 바꾸고 등재 확정은 주문 원장이 SSOT 임을 명시했다.
- **수정 — `qb_active_orders` 게이지 누수.** 조건부 취소 2경로(reconcile·sweeper)가 생성 시 inc 된 게이지를 dec 하지 않아 단조 증가했다.
- **BL-499 등재 (P2) — 취소↔dispatch 경합.** 실재하나 **재현 판정에서 자가 치유가 확인**됐다. sweeper 가 `submitted`+비활성 세션을 잡고, 활성이면 다음 tick 이 정상 취소한다. 노출은 최대 1 tick.
- **BL-500 등재 (P2) — 거래소에서 사라진 주문을 DB 행만으로 resting 오인.** WS 취소 이벤트가 완화하나, 이번 스프린트가 `orphan_scanner` 를 면제시켜 그 검출기는 더 이상 안 잡는다.

### 신규 BL

- **BL-492 P2.** 이미 돌파된 stop 의 시뮬↔거래소 시맨틱. 시뮬은 `low <= stop` 을 즉시 체결로 보고 거래소는 `110093` 으로 거부한다. 시장가 근사는 라이브 매매 의미를 바꾸므로 별도 설계.
- **BL-493 P3.** 조건부 진입 첫 바 커버리지 공백 — tick 이 바 종료 56초 뒤에 도는 구조상 그 바의 93% 를 놓친다.
- **BL-494 P3.** `min_qty != qty_step` 인 심볼에서 스텝 절삭이 최소수량을 보장하지 않는다.
- **BL-496 P3 · BL-497 P3.** 종결 시 작업 문서를 삭제하기 전 대조하다 **어디에도 흡수되지 않은 2건**을 발견해 등재했다 — 발주 순서(`trade_id` 순)와 엔진 체결 우선순위(open 가격 거리순) 불일치 · cancel→place 사이 stop 부재 창.
- **BL-498 P2.** ★**활성 세션이 없으면 거래소 포지션을 화면에서 보지도 닫지도 못한다.** 코크핏 §03 이 세션 스코프라 세션 0건이면 청산 버튼 자체가 없다. fail-closed 종료가 포지션을 남기는 것은 **설계**이므로 이 상황은 반복된다(이번에 실제로 겪었고 raw HMAC 으로 정리했다).
- **BL-499 P2 · BL-500 P2.** 위 최종 리뷰 참조.

### 문서 종결

`reference/gates-and-traps.md` 에 함정 8종 승격(조건부 주문의 stuck 오판 · 멱등성 재생 · 키 길이/콜론 · except 블록 크래시 · TICK_SIZE · 110093 · codex 파일 수 제약 · no-op 변이). 작업 문서는 커밋하지 않는다. **`docs/` 최상위 10 유지.**

## ⚡ live-engine-parity — `run_live` 인자 4종 패리티와 라이브 원장 신뢰 (2026-07-26)

**스코프.** `run_live` 가 `run_historical` 로 넘기지 않던 사이징 equity 기준·`leverage`·`sessions_allowed`·`pyramiding`을 끝내고, 새로 켜지는 게이트가 무음으로 진입을 삼키지 않게 표면화한다.

### ★핵심 발견

- **preflight 가 킥오프 전제 4건을 반박했다.** carry 후보 `live_signal_states.total_realized_pnl` 은 창 스코프·매 tick 덮어쓰기이고, `Σ orders.realized_pnl` 은 거래소 net과 rejected 추정 PnL이 섞여 둘 다 기각됐다. 라이브 OHLCV의 `RangeIndex` + `timestamp` 는 tz 조건을 no-op으로 만들었고, NaN 기준선 단순 비교는 `InvalidOperation` 을 raise한다.
- **★★D7.** 16:12Z의 3건·`5.16879987` 이 16:49Z의 2건·`4.07002377` 이 될 예측은 맞았지만, 이유는 창 밖 청산이 아니었다. 진입이 창 bar 0에서 EMA를 재현하지 못해 청산도 재현되지 않았고 carry에도 안 들어갔다. 화면은 원장 SSOT로 수리했지만 사이징 자본의 일시 함몰은 남는다.
- **leverage 배선은 게이트만 켜지지 않았다.** `check_liquidations` 도 살아나 실제 reduce-only 주문을 낼 수 있는 머니-패스가 됐다. 따라서 청산 표면화와 "격리 증거금 기준" 고지를 같이 넣었다.

### Completed

- [x] **BL-486 ✅ Resolved.** carry는 append-only `live_signal_events`를 `bar_time < window_start`로 자른 합으로 정했다. `sum_realized_pnl_before`는 **사이징 자본 경계**(`initial_capital`), `sum_realized_pnl_all`은 **상태 행 총계**의 원장 SSOT다. 새 close 이벤트만 `equity_curve`에 append한다.
      ★★**정정 — 상태 행은 화면이 아니다.** 최종 리뷰에서 확인했다. `router.py:474-483`(2026-07-01 dogfood)이 `GET /live-sessions/{id}/state` 응답의 `total_realized_pnl`·`total_closed_trades`·`equity_curve` 를 **체결(`state=filled`) 주문으로 재계산해 덮어쓴다**. 즉 화면은 원래부터 창 드리프트를 타지 않았고, 이번 상태 행 수정은 **내부 정합 + `equity_curve` 무한 증식 차단**(분당 1 포인트 → 청산당 1)이다. **사용자에게 보이는 실제 효과는 `initial_capital` carry = 주문 수량**이다. 아래 dogfood 표의 "화면" 은 전부 **상태 행**으로 읽어야 한다.
- [x] **BL-483 ✅ Resolved.** leverage를 라이브 엔진에 전달하고, 진입 skip을 reason별로 마지막 bar만 표면화했다. 라이브 리포트에서 `has_lastbar_skips=t`, `has_liq=t`, `liquidation_count=0` 을 확인했다.
- [x] **BL-481 ✅ Resolved.** `Strategy.trading_sessions`를 전달하고, 값이 있을 때만 `timestamp`로 tz-aware 인덱스를 복원해 세션 밖 진입을 fail-closed로 막는다.
- [x] **BL-482 ✅ Resolved.** 선언 `pyramiding` cap을 전달하고 cap 미만·초과 양방향 회귀를 뒀다.
- [x] **BL-487 ✅ Resolved.** pool 객체 참조를 붙잡아 `id()` 재사용 flake를 `is not` 단정으로 바꿨다.
- [x] **상태 행**과 원장은 17:10Z·17:23Z·19:02Z 에 연속 일치했다(약 1시간 52분). curve는 청산 0건·tick 24회에서 +0, 청산 1건에서 정확히 +1이었다. ★이 값들은 API 가 덮어쓰므로 화면 렌더값이 아니다(위 정정 참조).
- [x] 변이 10종이 전부 적발됐고 매 변이에서 음성 95/96이 GREEN을 유지했다. `MUTANT` 잔존은 0, 복원은 바이트 동일이다.
- [x] **독립 raw HMAC 오라클** — ccxt·`providers.py` 미경유로 `X-BAPI-SIGN` 을 손서명해 `/v5/position/closed-pnl` 직격. 청산 **5건 전부 DB 와 정확히 일치**(불일치 0). 시뮬 `+1.09877350` vs 거래소 `-1.09767393` 의 부호 반전이 외부 진실로 확정됐다.
- [x] 게이트: BE **3102**(+28) · FE **1156**(+5) · **canon 32** · **e2e:authed 65-0** · ruff·mypy·tsc·lint 0 · 마이그레이션 **0**
      ★ canon 은 처음 **27/32** 가 나왔는데 회귀가 아니라 `baseURL` 기본값 3000 을 다른 앱이 점유한 것이었다. `PLAYWRIGHT_BASE_URL=3100` 재실행으로 32. **통과 27건이 거짓 그린이었다는 게 실패 5건보다 무섭다.**

### 신규 BL 4건

- **BL-488 P1.** 평가 갭이 orphan close와 거래소 거부, 시뮬 손익 오염을 만든다.
- **BL-489 P2.** D2 구간에서 사이징 자본이 일시 함몰한다. 화면 총계는 해결됐지만 `initial_capital`은 별도 설계가 필요하다.
- **BL-490 P2.** `margin_mode` 미전달과 isolated 전용 청산 모델 때문에 cross 사용자가 조기 청산될 수 있다.
- **BL-491 P3.** 백테스트 폼이 Live 레버리지를 아직 미러하지 않는다.

### 문서 종결

게이트 운영 지식 6종은 [`reference/gates-and-traps.md`](reference/gates-and-traps.md)에 승격했다. 작업 문서(`checklist.md` · `context-notes.md` · `bl-drafts.md`)는 회고·백로그·정본으로 전부 흡수했고 커밋하지 않았다. **`docs/` 최상위는 10 을 유지한다.** 이력인 아래 `live-entry-wiring` 섹션은 유지한다.

## ⚡ live-entry-wiring — BL-478 (c) 세션 차단 + BL-479 라이브 사이징 (2026-07-26)

**스코프**: 라이브 자동매매는 **진입 주문을 낸 적이 없다.** `strategy.entry(..., stop=)` 는 `PendingOrder` 만 파킹하고 이벤트를 발행하지 않는데(`strategy_state.py:598-609`) 거래소에 그 조건부 주문을 올리는 코드가 없다. 청산만 나가 매번 `110017`. 진입이 열리면 곧바로 수량이 문제가 된다 — `compute_qty()` 가 항상 `1.0`(1 BTC 명목). **기능을 늘리지 않고 거짓말을 멈춘다.**

### ★★사용자 요청 실측이 후보 3 을 반증했다

equity 기준선 후보 3(kill-switch balance provider 재사용)의 **갱신 주기를 먼저 재라**는 지시였고, 답은 "갱신 주기라는 개념이 없다" 였다.

```
account_service.py:126-157  캐시 0줄. TTL·Redis·beat 갱신 태스크 전부 부재
                            매 호출 = DB 2회 + AES 복호화 + ephemeral ccxt -> REST -> close
                            실측 1600ms (BL-476). 독스트링의 "~200ms" 는 8배 낙관
kill_switch.py:106-107      total_pnl >= 0 이면 조기 반환 -> "이미 부르니 공짜" 가 아니다
live_signal.py:873-885      exchange_svc 는 Celery 경계 뒤 dispatch 소속 -> 코드 재사용일 뿐
```

★**지연보다 큰 문제는 시맨틱이었다.** `run_live` 는 warmup replay(300바)라 매 tick 히스토리를 재실행하고 `running_equity` 는 `initial_capital` 에서 시작해 청산 손익을 **다시** 누적한다. 거래소 실잔고는 이미 그 손익이 반영된 값 → **이중 계상**. 300바를 벗어나면 빠지므로 이중 계상량이 시간에 따라 변한다 = 같은 바가 tick 마다 다른 수량. → **세션 시작 1회 스냅샷 + 컬럼 저장**으로 확정(사용자 승인).

★**다만 절반만 닫혔다.** 실잔고 주입에서 오던 이중 계상은 없앴지만 `running_equity` 가 **창 안 청산 손익**을 누적하는 것은 그대로다 → 창이 밀리면 같은 바의 수량이 바뀐다. 최종 codex 리뷰가 잡았고 실측 재현했다(**BL-486**).

### ★탐색이 뒤집은 전제 4건

| 전제                                         | 실측                                                                                                                                                                    |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `s4_hma` 는 명시 `qty=` 라 사이징 **대조군** | ✗ **세 번째 양성.** `capital = strategy.equity` 인데 `running_equity is None` 이면 NaN → BL-376 chokepoint 가 주문을 **skip**. 라이브에서 hma 는 진입 신호가 0 건이었다 |
| 우선순위 사슬을 `compat.py` 에 두고 공유     | ✗ **순환 import** (`compat.py:23` 이 `event_loop` 를 module-level import) → 신규 `sizing.py` 필수                                                                       |
| 잔고 = `fetch_balance_usdt`                  | ✗ 그건 `data["free"]` 만 읽는다. 포지션이 있으면 왜곡 → **`total`** 이 맞다                                                                                             |
| preflight 차단 시 divergence 카운터 inc      | ✗ `common/metrics.py` 의 divergence 카운터 정의 = "0 초과 = 즉시 운영 page". 예상 가능한 사용자 상황은 page 대상 아님                                                   |

### Completed

- [x] **BL-478 (c) Resolved** — `ast_extractor.uses_stop_entry()` 신설(리터럴 `stop=na` 는 인터프리터와 동일하게 제외, 변수 표현식은 보수적 차단). `register()` 가 422 `live_stop_entry_unsupported` 로 거부 + evaluate preflight 가 이미 도는 세션을 자동 종료
- [x] **BL-479 Resolved** — `register()` 가 `AccountBalanceService.get_balance().total` 로 1회 스냅샷 → `live_signal_sessions.equity_baseline_usdt`(`Numeric(18,8)`, nullable) → evaluate 가 `run_live(initial_capital=..., live_position_size_pct=...)` 로 전달. Pine > form > Live 우선순위 사슬이 라이브에서도 성립
- [x] **`pine_v2/sizing.py` 신설** — 우선순위 사슬 SSOT. 백테스트(`compat`)와 라이브(`event_loop`)가 공유. `_extract_default_qty` 는 alias 없이 삭제(SSOT 2개 방지)
- [x] **fail-closed 4종** — `supported=False` / `total is None` / `total <= 0` / `ProviderError`(502를 422로 흡수해 안내 문구가 도달 가능해짐). 통과시키면 `initial_capital=None` → `compute_qty()=1.0` 이라 "고친 척" 이 된다
- [x] **페이징 계약 분리** — 신규 2종은 `qb_live_signal_skipped_total` 만 올리고 `qb_live_signal_divergence_total` 은 **안 올린다**. ★알림 **제목**도 함께 갈랐다 — 카운터가 page 를 안 해도 제목이 "divergence" 면 사람은 제목 보고 호출된다(계약을 반만 고치는 것)
- [x] **FE** — 코크핏 `selected` 를 목록에서 `useMemo` 파생(객체 스냅샷이라 자동 종료 후에도 "돌고 있는 것처럼" 렌더되던 결함) + 중단 안내 · 세션 상세 **기준 자본** 노출(부재는 `—`, 0 위장 금지) · 폼 폴백 문구. ★`FormErrorInline` 교체는 **기각** — 그 컴포넌트가 `detail.detail` 을 안 읽어 기존 422 4종이 조용히 `"API 422 …"` 로 퇴행한다
- [x] 게이트: BE **3074**(+45) · FE **1151**(+7) · canon **32** · **e2e:authed 65-0** · ruff·mypy·tsc·lint 0 · 마이그레이션 **1**

### ★★판별력 증명 — 전체 stash 대신 표적 변이 6종

전체 stash 는 import/TypeError 를 내서 **"심볼이 없다"** 만 증명한다. 행동적 RED 를 만들려고 변이를 넣었다 뺐다.

```
M1 uses_stop_entry -> False   양성 5 FAIL / 음성 17 PASS  <- 과잉차단 아님을 동시 증명
M2 uses_stop_entry -> True    25 FAIL                     <- 음성 케이스가 진짜 판별력을 가짐
M3 compute_qty 의 /100 제거    4 FAIL                      <- 손계산 오라클이 산술을 잡음
M4 total -> free              2 FAIL                      <- 필드 혼동을 잡음
M5 신규 2종도 page             1 FAIL                      <- 카운터 계약을 잡음
M6 initial_capital 미전달      6 FAIL                      <- 배선이 가정이 아니라 증명됨
변이 잔존 0 · 복원 5/5 바이트 동일
```

손계산 오라클은 2의 거듭제곱만 골라 부동소수 오차를 0 으로 만들었다 — `8192 x 50 / 100 / 65536 = 0.0625`. 오답(1.0 / 0.03125 / 6.25 / 0.000625)이 정답과 충돌하지 않는다.

### 실화면 dogfood

- [x] **자동 종료** — `0e15c3c0` 이 마이그레이션 후 첫 tick(30초 내)에 `{'deactivated': 'stop_entry_unsupported'}`. ★이 세션은 **stop-entry 와 NULL baseline 둘 다** 해당인데 근본 원인을 보고했다(설계한 우선순위대로). 화면 "활성 세션" 이 1 → 0
- [x] **차단 문구** — PbR 로 세션 시작 → `live-session-form-error` 에 BE 문구 원문. `"API 422"` 미포함
- [x] **음성 대조군** — EMA 로 바꾸면 **201**, 활성 세션 1. 설정 없을 땐 기존 `StrategySettingsRequired` 문구가 정상 렌더(= `FormErrorInline` 을 기각한 판단이 옳았음을 실화면이 확인)
- [x] **독립 raw HMAC 오라클**(ccxt·`providers.py` 미경유) — `USDT walletBalance 190549.99467459` = DB `equity_baseline_usdt` **바이트 동일**, `retCode 0`
- [x] **M-4 마이그레이션** — 활성 세션이 있는 개발 DB 에서 upgrade → `is_active` 불변, 신규 컬럼 NULL, hydrate 정상. 클린 DB 에서 `downgrade base → upgrade head → downgrade -1 → upgrade head` 왕복 통과

### ★★프로덕션 진입 — 실주문 체결까지 3중 대조

기다렸더니 EMA 크로스가 실제로 났다. **시드로 만들지 않았다.**

```
손계산   190549.99467459 x 1% / 64512.50  = 0.02953691
DB       live_signal_events.qty            = 0.02953691   (action=entry, dispatched)
         orders.quantity                   = 0.02953691   (state=filled)
거래소    qty 0.029 · cumExecQty 0.029 · avgPrice 64484.2 · Filled · retCode 0
         orderId d474e540-… (UUID = linear perp)
```

DB → 거래소 `0.02953691 → 0.029` 차이는 **`amount_to_precision` 절삭**(BTCUSDT linear 수량 스텝 0.001)으로 정확히 설명된다. 실집행 명목 **$1,870** — 미배선이었다면 `1.0` = **$64,484**, **34.5 배**다.

### ★프로덕션 원장의 before / after

같은 계정, 같은 심볼, 같은 날. 수정 전후가 `trading.orders` 에 그대로 남았다.

```
10:02  sell 1.00000000  reduce_only=t  rejected   <- BL-478 증상. 진입이 없으니 청산만 나가 110017
10:17  buy  1.00000000  reduce_only=t  rejected
10:36  buy  1.00000000  reduce_only=t  rejected
11:51  buy  0.02953691  reduce_only=f  filled     <- 수정 후. 진짜 진입 + 자본 기준 수량
```

`1.0`(미배선 fallback) 이 전부 `reduce_only=t` 이고 전부 `rejected` 라는 것이 BL-478 과 BL-479 가
**한 증상의 두 얼굴**이었다는 증거다. 진입이 안 나가니 청산만 남고, 그 청산 수량조차 `1.0` 이었다.

### ★정직하게 남기는 것

- **플랜의 대안 하나가 틀렸다** — "신호 없이도 `last_strategy_state_report.running_equity` 로 배선을 증명한다" 고 적었는데 `to_report()` 에 그 키가 없다(7개 키뿐). 결국 진짜 신호를 기다려서 증명했다.
- **지금 `total == free`** (`totalPositionIM: 0`). dogfood 만으로는 둘을 구별할 수 없고, 그걸 증명한 건 **M4 변이뿐**이다.
- **배포 순서는 마이그레이션이 먼저다.** 워커가 신규 코드인데 DB 에 컬럼이 없던 몇 분 동안 `UndefinedColumnError` 로 전 세션 평가가 실패했다(실측). fail-closed 지만 시끄럽다.

### 신규 BL 5건

- **[BL-481]** P2 `sessions_allowed` 라이브 미배선 — 거래 시간대를 제한해도 라이브는 24h 진입
- **[BL-482]** P3 `pyramiding` cap 라이브 미배선
- **[BL-483]** **P1** `leverage` 라이브 마진게이트 미배선 — 백테스트가 거부할 진입을 라이브가 통과시킨다. ★그냥 넘기면 안 된다: 증거금 부족 skip 이 `warnings` 로만 남아 **완전 무음**이라 표면화 경로를 같이 만들어야 한다
- **[BL-484]** P2 자동 중단 **사유**가 화면에 안 남는다(알림 채널 전용)
- **[BL-485]** P3 `FormErrorInline` 이 `detail.detail` 폴백을 안 해 공통 컴포넌트를 못 쓴다
- **[BL-487]** P3 `test_get_pool_safe_across_event_loops` 가 `id()` 재사용에 취약한 선재 flake — pool 객체를 붙잡지 않고 `id()` 만 비교해 CPython 이 주소를 재사용하면 random RED. 전체 스위트에서 1회 관측, 격리 실행과 재실행은 통과
- **[BL-486]** **P1** ★라이브 사이징 equity 가 **300바 롤링 창**에 따라 변한다 — 같은 마지막 바에서 창 안 청산 유무로 `qty 0.09375 vs 0.0625`(**50% 차이**) 실측. 미배선 `1.0` 보다는 낫지만 완결이 아니다. KNOWN_LIMITATION 테스트로 못 박아 조용한 드리프트를 차단했고, 고치려면 라이브 equity 시맨틱((a) 세션 고정 / (b) 세션 누적 / (c) 실잔고 추종)을 먼저 정해야 한다

### 문서 종결 (sprint-template §9)

강등 2(`dogfood-restore` · `live-entry-wiring` → `archive/sprints/`) + 승격 1(**`reference/gates-and-traps.md`** — 게이트 지식이 7개 스프린트 문서에 복붙되고 있었다) → **`docs/` 최상위 12 → 10**. `README.md` 에 `<테마>/` 지위 명문화.

---

## ⚡ 체크리스트 A — BL-474 webhook ingress 패리티 (2026-07-26)

**스코프**: [`docs/archive/sprints/dogfood-restore/checklist.md`](archive/sprints/dogfood-restore/checklist.md) §A. #481 출처 라벨·#477 SessionScope 를 화면에서 보려면 linear perp **진입 → 청산 → 스윕 확정**이 실제로 일어나야 하는데, 그 경로를 테스트 주문 도구가 막고 있었다.

### ★진단이 한 겹 더 깊었다 — 다이얼로그가 아니라 webhook ingress

`router.py:138-147` 이 `OrderRequest` 를 7개 필드로만 조립하고 `parse_tv_payload`(`webhook.py:118-125`)가 6개 키만 읽어 **한 자리에서 3건이 동시에 버려졌다**.

```
leverage / margin_mode   해결 자체를 안 함        → has_leverage=false → spot
reduce_only              프론트는 보냄, 파서가 안 읽음 → 청산 확정 경로 전체가 막힘
take_profit / stop_loss  프론트는 보냄, 파서가 안 읽음 → UI 입력이 거짓말
```

★**leverage 만 고쳤으면 A 는 안 열렸다** — `tasks/trading.py:1342` 가 `not order.reduce_only` 로 조기 반환하고 스윕 쿼리도 `reduce_only IS TRUE` 를 요구한다. 그 플래그 없이는 다이얼로그 청산이 영원히 `realized_pnl_synced_at` 을 못 받는다.

### ★★체크리스트 자신의 함정 문구가 틀렸다

`checklist.md:108` 은 "레버리지 1 → `has_leverage=False` → spot" 이라 적었는데 **같은 문서 §A 표는 정반대**(`leverage=1 … → linear perp`)였다. 코드가 심판 — `order_service.py:194` = `req.leverage is not None and req.leverage > 0`, `tasks/trading.py:135` = `return lev > 0` → **1이면 linear**. 진짜 원인은 값이 1이어서가 아니라 **아무 값도 안 보내서**다. 관측에서 원인을 성급히 일반화한 사례로 문서에 정정 기록.

### Completed

- [x] **BL-474 Resolved** — `WebhookService.resolve_trading_params()` 신설. `Strategy.settings` 가 SSOT(`live_signal.py:931-932` / `close_service.py:86-92` 와 동일), 미설정·무효는 **422 fail-closed**, HMAC 검증 **뒤에** 호출(응답코드로 settings 유무 탐지 차단). `reduce_only`(+`bool("false")` 함정 방어)·TP/SL·`risk_percent` 파서 통과.
- [x] **FE** — 라우팅 배지(`Linear Perp · 2x · isolated`) · settings 없을 때 422 경고(**차단은 안 함** — 공개 ingress 라 서버가 권위) · 미리보기 레버리지 기본값 = 전략 설정 · `reduce_only` 시 `realized_pnl` 입력(추정/확정 대조용) · secret 안내문에 §05 Webhook 카드 명시
- [x] **신규 [BL-475]** — risk% 사이징 모드는 한 번도 작동한 적 없었다(`quantity` 누락 401 + 백엔드는 상한만 검사). 문구 정정 + 수량·손절가 필수화 + `risk_percent` 배선
- [x] **Sprint 7a 부채 청산** — `test_e2e_webhook_to_futures_order.py` 독스트링이 "Sprint 7b 로 분리" 라 적어둔 HTTP→ccxt 전 구간 테스트
- [x] **RED 증명 22건**(parse 17 · router 4 · e2e 1) + FE 신규 7건은 `git stash` 로 프로덕션만 되돌려 RED 재현
- [x] 게이트: BE **3029**(+24) · FE **1136**(+6) · ruff·mypy·tsc·lint 0 · 마이그레이션 **0**
- [x] **실화면 dogfood — Bybit 데모 실주문 4건.** 결정적 증거는 **주문 ID 형식**이었다: 수정 전 `2267433208968908032`(숫자형=spot) → 수정 후 `0a245783-f809-…`(UUID=linear). 거래소가 시장 유형이 바뀌었다고 말해주는 외부 증거다
- [x] **출처 라벨 혼재 상태 포착** — 청산에 추정 `-9.99` 주입(확정값과 우연히 같아질 수 없게) → 04:30:00 화면에 **`거래소 확정 -0.05935440` / `추정 -9.99000000`** 동시 표시 → 8초 뒤 확정 `-0.12772399`(두 청산의 정확한 합). `confirmed + estimated == total` 화면에서 성립. 대시보드 §01 KPI foot(`splitComplete`)도 렌더
- [x] **독립 HMAC 오라클** — ccxt·`providers.py` 미경유로 `/v5/position/closed-pnl` 직격. `orders.realized_pnl` · `exchange_exits.closed_pnl` · 거래소 원문 **3중 일치**
- [x] 라우팅 배지 · settings 없는 전략 422 경고 · 미리보기 레버리지 기본값 실화면 확인. 콘솔 error 0

### ★신규 BL 2건 (dogfood 실측이 만든 것)

- **[BL-476] 지연 +4.8초 실측** — `fetch_mark_price 1663ms · fetch_min_notional 1549ms · fetch_balance_usdt 1600ms`. leverage 가 채워지며 notional 가드가 webhook 에서 처음 도달 가능해진 대가. ★**게이트는 provider 를 stub 으로 갈아끼우므로 영원히 0ms** — 프로덕션에서만 보이는 회귀라 예상만 하지 않고 쟀다
- **[BL-477] 청산 원장 유령 `unknown`** — API 키 2개가 같은 Bybit 서브계정을 가리켜 같은 청산이 2행 적재. 07-24 행도 같은 패턴이라 **선재**. 금액은 안전(`aggregate_closed_pnl` 계정 스코프 + 세션 손익은 `orders.realized_pnl` 을 셈 — 실측 확인). 영향은 귀속/알림 표면뿐

---

## ⚡ 체크리스트 B — pine_v2 ↔ 거래소 발산 (조사 완료, 2026-07-26)

### ★★가설이 틀렸다 — "상태가 롤백 안 된다" 가 아니라 **진입이 나간 적이 없다**

체크리스트 B 는 "발주 실패 후 pine_v2 상태가 롤백되는가" 를 물었다. 답은 "롤백 경로 0" 이지만 **그게 원인이 아니었다.**

```
strategy.entry(..., stop=)  →  PendingOrder 파킹 + return None   (이벤트 미발행)
                            →  체결 시 event_action="fill"
run_live                    →  fill 은 dispatch 대상에서 제외      ← event_loop.py:287-288
독스트링                     →  "broker 가 자체 fill 알림 처리"
실측                        →  live_signal.py 에 trigger_price 참조 0건
```

**broker 에 그 stop 주문을 올린 적이 없다.** 그래서 진입 이벤트가 0건이고, 반전 시 생기는 `close` 만 나가서 매번 110017. 라이브 세션 `0e15c3c0` 의 주문 전량이 `reduce_only=true`·`rejected` 이고 **진입 주문은 한 건도 없다** — 이게 그 증거였는데 "사이징 문제" 로 읽었다.

**영향 범위는 `stop=` 진입 전략 한정.** 시장가 진입은 `strategy_state.py:634-642` 가 `event_action="entry"` 를 정상 발행한다. 시드 `s1_pbr` 은 진입 2개가 전부 `stop=` 이라 100% 이 경로.

### 등재한 BL

- **[BL-478] P1** — stop-entry 전략은 라이브에서 진입이 구조적으로 안 나간다. 최소 정직안 = 그런 전략의 세션 시작을 **차단하고 이유를 표시**(지금은 조용히 안 되면서 되는 척)
- **[BL-479] P1** — 라이브 사이징 미배선. `run_live` 가 사이징 인자 없이 `run_historical` 호출 → `compute_qty()` 항상 `1.0`. `position_size_pct` 는 라이브에서 **아무 데서도 안 읽힌다**(유일한 소비처 `compat.parse_and_run_v2` 의 프로덕션 호출자는 백테스트 어댑터 하나). Pine `default_qty_type` 선언조차 무시됨
- **[BL-480] P2 → ✅ Resolved** — ★**화면이 발산을 은폐했다.** 백엔드는 정확히 알고(실측 `verdict="local_only"` + `PivRevLE long qty 1 @ 64557.51`) 프론트에 문구도 있었는데, 행 생성이 `positions` 순회라 **`local_only` = `positions` 빈 배열**인 그 순간에만 렌더 불가였다. `divergences` 를 세션 단위로 건져 올려 수정. **실화면 확인** — _"BTC/USDT · PbR Pivot Reversal · 전략에만 열린 거래가 있습니다. 전략 보고: PivRevLE 롱 1 거래소 보고 포지션은 0건입니다."_ RED 7건 선확인. ★근본 원인(BL-478 진입 미발주)은 그대로 — **화면이 숨기지 않게** 만든 것뿐

### 확인된 설계 사실 (결함 아님)

- 상태 쓰기가 dispatch 보다 **먼저**고 그 사이 Celery 경계가 2개 — 거래소 결과를 알 수 없는 게 정상이다(transactional outbox)
- Option B(warmup replay)라 매 tick `run_historical` 재실행 → **되먹일 자리 자체가 없다**. 되먹여도 다음 tick 이 덮어쓴다
- 재동기화 경로(`Reconciler`·`orphan_scanner`·`resync_exchange_realized_pnl`)는 전부 **orders 만** 본다. 포지션/시뮬 재동기화는 없다
- `router.py:504-544` 가 응답 시점에 체결 주문으로 PnL 을 재계산하는 건 **read-side mask** 다 — DB 의 `total_realized_pnl -175.82` 는 그대로 남아 있다

### Next Actions

**이 스프린트는 여기서 닫는다.** 잔여 전량은 [`docs/archive/sprints/live-entry-wiring/checklist.md`](archive/sprints/live-entry-wiring/checklist.md) 로 이관 — 조사는 끝났고 남은 건 **결정 + 구현**이다.

- [x] **PR [#484](https://github.com/woosung-dev/quantbridge/pull/484)** `feat/bl-474-webhook-ingress-parity` → main — **squash 는 사용자**
- [x] ~~다음 세션 = `docs/archive/sprints/live-entry-wiring/checklist.md`~~ **완료** — BL-478 은 (c) 차단 후 (a) 조건부 등재까지 끝났다(#486·#489). 첫 step = **BL-478 선택지 (a)/(b)/(c) 사용자 결정** — 라이브 매매 시맨틱을 바꾸므로 blocking 이다. 권고 = (c) 먼저(거짓말을 즉시 멈추고 (a) 설계 시간을 번다), (b) 는 백테스트↔라이브 일치를 조용히 깨므로 비권장

---

## ⚡ dogfood-restore 스프린트 (2026-07-26)

**스코프**: #477·#480·#481 이 전부 **실화면 dogfood 없이** 닫혔고(07-25 DB 전소로 `ts.ohlcv` 0행 → 백테스트 불가), 세 스프린트 분량 신뢰 작업이 우리가 쓴 테스트로만 검증돼 있었다 — §7.3 이 금지하는 circular oracle. (A) 복원 경로 + (B) 실화면 검증 + (C) e2e 소생. 마이그레이션 **0**.

### ★§0.5 실측이 킥오프 전제를 3건 정정했다

```
"authed 13 spec 실패" = 파일 수를 테스트 수로 오독. 실제 = 13파일/64테스트 중
  하드 실패 6, 나머지 57 은 page.route 목킹이라 빈 DB 에서도 통과.
  ★진짜 문제는 따로 — 캐논 감사 9건이 StateBox 만 감사하며 조용히 통과(BL-470).

복원은 거의 공짜 — TimescaleProvider 가 cache-first + live CCXT fill 이라
  백테스트 1회가 곧 시딩. 실측 9,337행 · 갭 0.

프로즌 픽스처는 현재 경로에서 도달 불가 — FixtureProvider 가 canonical
  `BTC/USDT` 의 슬래시를 경로로 해석(BL-468).
```

### ★★워커가 구 코드였다 — 그래서 legacy 행이 공짜였다

착수 시 `quantbridge-worker` 가 `b97ac57`(#480) **8시간 전** 이미지로 돌고 있었다(§7.2 위반). 덕분에 **조작 0의 진짜 pre-#480 행**을 얻었다 — 계획했던 "`metrics` 에서 마커만 SQL 로 제거" 는 오히려 **부정직**했다(신 컨벤션 숫자에 구 기준 각주가 붙는다). 순서가 비가역이라 legacy 를 먼저 돌리고 워커를 bind-mount 로 교체했다(재빌드 0).

### ★★dogfood 가 P1 을 잡았다 — 파산한 계좌에 양수 샤프

`_periodic_returns` 가 `prev == 0` 만 막고 **`prev < 0` 을 안 막아** 자본이 음수면 부호가 뒤집힌다 → **더 잃을수록 수익률이 양수**. 실측 = 10,000 → **-207,968**(총수익률 **-2179.68%**) 실행의 월간 수익률 13개 중 11개가 양수, **샤프 +0.029**. BL-398(#480)이 없애려던 거짓말의 다른 얼굴(그쪽은 수식, 이쪽은 분모 부호).

**★committed Trust Layer baseline 이 이걸 담고 있었다** — `s1_pbr` baseline 샤프 **+0.600** · 소르티노 **+2.349**(총수익률 -536%). 코퍼스 5종 중 4종이 음수 자본이고 **골든이 깨진 것도 정확히 그 4종**(거래 0인 `i2_luxalgo` 만 무관). baseline 재생성 diff = **12 메트릭 키 중 2개**(sharpe/sortino)·해당 4종 한정, `ohlcv_sha256` 불변.

### Completed

- [x] **S0 환경** — `docker builder prune -f`(8.9G→12.9G) · **`ts.ohlcv` hypertable 복구**(dev DB 만 평범한 테이블이었다, test DB 는 정상 = 07-25 사고 잔재. 0행이라 무료) · BE 8100 기동
- [x] **S1 `make seed`** — `backend/scripts/seed_dogfood.py`. **실 서비스 계층 + 실 Celery** 경유(HTTP/auth 만 우회 — clerk SDK 가 `azp` 클레임을 필수로 요구해 헤드리스 HTTP 시딩이 구조적으로 불가). 함정 3종을 상수로 박음(canonical `BTC/USDT` · 격자 정렬 UTC · `exchange` NOT NULL). **멱등**
- [x] **S2 커버리지** — 전략 3 / 백테스트 6 / 거래 3,194 / OHLCV 9,337 / optimizer 1. 샤프 4상태 전부 + 100x 청산 503
- [x] **S3 외부 오라클 대조**(엔진 미개입) — 샤프 **양 컨벤션 독립 재계산 일치**(구 수식 6.66e-16, 신 수식 1.5e-05) · legacy↔monthly **에쿼티 9,337 포인트 바이트 동일**(격차 42배가 전부 컨벤션) · 청산수 **엔진 503 = trades 테이블 503**, 1x 대조군 0 · 청산가 **롱 최대 0.995000 / 숏 최소 1.005000 = 손수식 정확 일치**(유리한 체결 0건)
- [x] **S5 결함 수정 4건** — **D1** 샤프 raw 렌더 **5곳**(계획은 4곳, CSV export 를 놓쳤다) → `describeSharpe` 경유 + 소스 스캔 가드 · **D2** 전체 원장 청산 사유 열(리포트 미리보기는 최신 25건 한정이라 503 청산이 안 보였다) · **BL-465** 음수 자본 가드 · **BL-467** optimizer-heavy OHLCV env
- [x] 게이트: BE **3005**(+5) · FE **1125**(+1) · ruff/mypy/tsc/lint 0 · **canon 32 불변** · build ok · **마이그레이션 0**
- [x] **e2e:authed 65 passed / 0 failed** — 빈 DB 하드 실패 6건 전부 초록
- [x] 실브라우저(MCP Playwright) — 전략목록 degenerate `—` · 목록 5행 각 컨벤션 각주 · **혼재 정렬 고지 발화** · 전체 원장 "청산 사유" 열 · 콘솔 error 0

### ★사용자가 알아야 할 것

**Bybit demo API 키가 죽었다.** ws-stream 실측 — `00:45:02Z ws_stream_auth_failed … Params Error` → `ws_circuit_opened`(1h). 시계 드리프트는 배제(호스트·컨테이너·Bybit 서버 시각 일치). **키 재등록 전까지 S4(실주문 머니-패스 dogfood)는 불가** — #481 출처 라벨과 #477 SessionScope 는 여전히 화면 미검증이다.

### ★S4 실주문 — 진단 정정 + 부분 완주

**"키 만료" 진단이 틀렸다.** 독립 HMAC 오라클로 REST 를 치니 **양쪽 키 모두 `retCode 0`**(자산 846,921.08). 진짜 원인은 **우리 WS 인증 `expires` 창이 +1s** 라 왕복 지연에 먹힌 것(**BL-473 Resolved**, 통제 실험 +1s 실패 / +10s·+60s 성공). 사용자에게 불필요한 키 재등록을 시켰다. 새 키는 `readOnly: 1` 로 생성돼 거래 불가였고 기존 키로 진행했다.

**검증됨** — Bybit 데모 **실주문 체결**(독립 오라클로 거래소 확인) · **BL-454 심볼 정규화 실경로 작동**(다이얼로그 `BTCUSDT` → `Order.symbol` canonical `BTC/USDT`) · 라이브 신호 경로 종단(`live_signal_events` dispatched + 주문 연결 + pine_v2 추정 손익) · **D3 수정 화면 확인**(`API 422 …` → `Cannot normalize symbol: BTCUSDT.P`).

**★신규 발견 BL-474** — 테스트 주문 다이얼로그는 `has_leverage=false` 라 **spot** 으로, 라이브 신호는 `true` 라 **linear perp** 로 나간다. 청산 원장·코크핏은 linear 만 보므로 **이 도구로 머니-패스를 dogfood 하면 조용히 아무것도 검증하지 못한다.**

### Blocked

- **출처 라벨(#481)·SessionScope(#477) 화면 검증** — linear perp 체결이 청산까지 가야 확정/추정이 섞인다. 라이브 세션은 1분마다 평가 중이나 PbR 피벗 신호 미발생(`events_inserted: 0`). 시드로 만들면 조작이라 하지 않음

### Next Actions

- [x] **PR [#482](https://github.com/woosung-dev/quantbridge/pull/482)** `stage/dogfood-restore` → main — **squash 는 사용자**
- [x] ~~다음 세션 = `docs/archive/sprints/dogfood-restore/checklist.md`~~ **완료** — (A) BL-474 는 #484 로 닫혔고 (B) 발산 조사는 #486~#489 로 이어졌다. 원문: 사용자 확정. (A) **BL-474** 테스트 주문 다이얼로그가 spot 으로 나가는 것 먼저 → 고치면 perp 진입→청산을 결정적으로 만들 수 있어 **출처 라벨·SessionScope 화면 검증이 열린다** (B) pine_v2 시뮬 상태 ↔ 거래소 포지션 발산 조사(`retCode 110017`, 수량 1.0 사이징 미반영 의혹 포함)
- [ ] (선택) 최종 codex 누적 diff 리뷰

---

---

## 완결 스프린트 이력

2026-07-26 이전 스프린트 섹션은 **[`archive/status-history.md`](./archive/status-history.md)** 로 분리했다.
회고가 있는 스프린트는 [`dev-log/INDEX.md`](./dev-log/INDEX.md) 도 함께 본다.

## 상시 활성 컨텍스트 (영구 기록 외 발견 패턴)

- `dogfood Day N` 노트는 sprint 묶음과 별개로 `dev-log/` 에 단독 파일로 보관
- BL-005 (본인 1-2 주 dogfood) trigger 도래 후 H1→H2 gate (self-assessment ≥7) 가 재평가 기준
- `make up-isolated` (3100 / 8100 / 5433 / 6380) 가 다른 웹앱 병렬 시 디폴트
- **Pine SSOT 4 invariant audit** (`tests/strategy/pine_v2/test_ssot_invariants.py`) — supported list 추가 시 4 collection 동시 갱신 의무 자동 검증
- **Surface Trust sub-pillar (Sprint 30 ADR-019)** — Backend Reliability + Risk Management + Security + Surface Trust (가정박스 / 차트 / 24 metric / 거래목록). 측정: PRD 24 metric BE+FE 100% / config 5 가정 FE 100% / lightweight-charts 정합 / dogfood self-assess Day 3 ≥7
- **자율 병렬 sprint Agent worktree 패턴** — 충돌 회피 신규 파일 only / 통합 작업은 메인 세션 후처리 / gh CLI auto-merge --squash / `--no-verify` 1 회 우회 사용자 명시 승인 패턴

---

## 활성 BL 요약 (상세는 [`backlog.md`](./backlog.md))

> 본 sprint kickoff 시 백로그 review 의무. 자연어 표현은 컨텍스트 복원성 위해 sprint 회고 안에 유지하되, 새 항목 추가 시 BL ID 부여 후 등록.

핵심 cross-link (Sprint 59 PR-D 트리아주 후):

- **P0 active**: [BL-003](./backlog.md#bl-003) Bybit mainnet runbook
- **P1 active**: [BL-014](./backlog.md#bl-014) partial fill / [BL-015](./backlog.md#bl-015) OKX WS / [BL-022](./backlog.md#bl-022) golden 재생성 / [BL-023](./backlog.md#bl-023) KIND-B/C / [BL-024](./backlog.md#bl-024) real_broker E2E / [BL-025](./backlog.md#bl-025) autonomous-parallel patch / [BL-026](./backlog.md#bl-026) mutation fixture
- **P2 active**: [BL-186](./backlog.md#bl-186) full leverage model / [BL-190](./backlog.md#bl-190) PDF export / [BL-195](./backlog.md#bl-195) form animation / [BL-235](./backlog.md#bl-235) N-dim viz / [BL-236](./backlog.md#bl-236) objective whitelist
- **Deferred milestone** ([`_deferred.md`](archive/refactoring-backlog/_deferred.md)): BL-005 본인 dogfood / BL-070~075 Beta 본격 진입 / BL-145 EffectiveLeverageEvaluator
- **Archived 138건** ([`_archived.md`](archive/refactoring-backlog/_archived.md)): 모든 ✅ Resolved + Sprint 16~30 stale follow-up + P3 전부
- **정합성 audit:** [`04_architecture/architecture-conformance.md`](reference/architecture-conformance.md) — 15 항목 영구 체크리스트

---

## Test Skip / xfail 추적표 (Sprint 15-C 신설, 2026-04-28)

> 18 skip + 0 fail (Sprint 14 기준). "이 skip 이 왜 존재 + 언제 해소" 명시. 신규 skip 추가 시 본 표 업데이트 의무.

| #    | 위치                                                                                   | 종류                     | 사유                                                                                 | 해소 트리거                                                                  |
| ---- | -------------------------------------------------------------------------------------- | ------------------------ | ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| 1    | `tests/backtest/engine/test_golden_backtest.py:19`                                     | `pytestmark.skip`        | legacy golden expectations — pine_v2 `strategy.exit` 지원 + expected 재생성 필요     | pine_v2 strategy.exit 도입 후 golden 재생성                                  |
| 2    | `tests/real_broker/test_webhook_to_filled_e2e.py:31`                                   | `pytestmark.real_broker` | nightly E2E (Bybit Demo 실 호출). `--run-real-broker` flag + `BYBIT_DEMO_*` env 필요 | 매일 nightly cron (`.github/workflows/nightly-real-broker.yml`)              |
| 3    | `tests/real_broker/conftest.py:43`                                                     | `skip_marker`            | 위 #2 의 conftest fallback (env 미주입 시 collection-time skip)                      | 동일                                                                         |
| 4-7  | `tests/strategy/pine_v2/test_trust_layer_parity.py:251/334/357/421`                    | `skipif`                 | Trust Layer fixture (`regen_trust_layer_baseline.py` / 8 mutation set) 미생성        | Path β Stage 2c 2 차 mutation 8/8 도달 (2026-04-23 완료, 회귀로 활성화 검토) |
| 8    | `tests/strategy/pine_v2/test_trust_layer_parity.py:405`                                | `pytest.mark.skip`       | Mutation oracle 은 nightly workflow 또는 `--run-mutations` 수동 (CI default 차단)    | nightly mutation workflow 또는 manual gate                                   |
| 9-15 | `tests/strategy/pine_v2/test_mutation_oracle.py:147/179/212/253/296/328/376/414` (8건) | `skipif`                 | mutation fixture 미생성 시 collection skip                                           | Stage 2c 2 차 fixture 활성화 후 사용 가능 (현재 안전 fallback)               |
| 16   | `tests/strategy/pine_v2/test_mutation_oracle.py:213`                                   | `xfail(strict=False)`    | KIND=B/C 가 NaN-tolerance 한계로 mutation 구분 못 함. strict=False 로 명시           | KIND-B/C 분류 정밀도 향상 (Trust Layer v2 검토)                              |
| 17   | `tests/conftest.py:93`                                                                 | `skip_mutation` autouse  | 모든 `@pytest.mark.mutation` 자동 skip (CI default), `--run-mutations` 시 활성화     | pytest collection-time guard (영구)                                          |
| 18   | (집계 차이)                                                                            | xfail/skip 누적          | pytest collection-time 자동 분기 (real_broker / mutation 기본 차단)                  | 표 업데이트 의무                                                             |

**카테고리:**

- 영구 (정상): #2, #3, #8, #17 — opt-in flag 가 정확한 안전장치
- fixture 활성화 후 자동 해소: #4-7, #9-15 — Path β Stage 2c 2 차 후 회귀 검토 → [BL-026](./backlog.md#bl-026)
- dette: #1 (golden 재생성) → [BL-022](./backlog.md#bl-022) / #16 (KIND-B/C 정밀도) → [BL-023](./backlog.md#bl-023)

**관리 규약:** 신규 skip 추가 시 본 표 동일 PR 업데이트 / 매 sprint 끝 fixture 카테고리 재검토.

---

## Blocked

(현재 없음 — Sprint 58 종료)

---

## Questions

(없음 — 활성 질문 시 추가)

---

## Next Actions

> ★이 절은 2026-05-16(Sprint 59)에서 멈춰 있었다. 활성 sprint 의 Next Actions 는 **문서 최상단 절**을 본다 — 여기가 아니다.

- 활성 sprint 의 다음 행동은 이 문서 **맨 위 sprint 절**의 `### Next Actions` 를 따른다
- 다음 후보 = [`docs/roadmap.md`](roadmap.md) · open BL = [`docs/backlog.md`](backlog.md)
