# QuantBridge — Refactoring Backlog · DEFERRED 본문

> ★**이 파일은 원장의 일부다.** `docs/backlog.md` · `docs/backlog-resolved.md` 와 **한 벌로**
> `tools/scripts/bl-audit.sh` 가 읽는다 — 섹션 수·판정 수는 세 파일의 **합계**이고,
> 인덱스 표 행(`| [BL-nnn](#bl-nnn) | … |`)은 `docs/backlog.md` 에 남아 있다.
> 즉 3면 정합(섹션 · 인덱스 표 · roadmap)이 **세 파일에 걸친다.**
>
> ★**왜 갈랐나** ([BL-779] 마무리, 2026-08-18 backlog-triage). [BL-779] 는 RESOLVED 를 내려
> **21.5% 만** 줄였고 그것이 그 축의 천장이었다. 남은 감축분은 전부 **DEFERRED**(원장 열린
> 항목의 84%)에 있었고, 그것을 내릴지가 [BL-779] 가 적어 둔 **미결 사용자 결정**이었다.
> 2026-08-18 에 그 결정이 났다 — **내린다.**
>
> ★**분할의 축은 판정어다** — 이 셋이 전부이고 겹치지 않는다:
>
> | 파일                  | 사는 것                               | 왜                           |
> | --------------------- | ------------------------------------- | ---------------------------- |
> | `backlog.md`          | **ACTIVE ∪ PARTIAL** + 인덱스 표 전량 | 매 세션 읽는 것              |
> | `backlog-deferred.md` | **DEFERRED**                          | 트리거가 오기 전엔 안 읽는다 |
> | `backlog-resolved.md` | **RESOLVED**                          | 끝난 것                      |
>
> ★**규칙을 산문으로 두지 않았다** — `bl-audit.sh` 가 「판정어 ↔ 사는 파일」을 검사 축으로
> 집행한다. 어긋나면 rc=1 이다. 이 레포는 산문 처방이 3회 실패한 뒤에야 집행처를 만든 전례가
> 있다([BL-643]).
>
> ★**이동은 기계적이었다 — 본문은 한 글자도 고치지 않았다.** H2 묶음과 섹션 순서도 원본 그대로다.
> 직전 원문 = `git show HEAD:docs/backlog.md` (분할 커밋 기준).
>
> ★**여기에 새 항목을 손으로 적지 마라.** 항목이 DEFERRED 가 되면 `docs/backlog.md` 의 본문을
> 이 파일로 **옮기고** 표 행은 원본에 남긴다. 같은 id 를 양쪽에 두면 `bl-audit` 이
> 「중복 섹션 헤더」로 red 를 낸다.
>
> ★**표 행의 `#bl-nnn` 앵커는 이 파일을 가리키지 않는다** — 접두사를 붙이려 했으나 되돌렸다.
> 행마다 **+18자**가 붙어 P2 표의 패딩이 `docs-audit` 의 **줄 길이 상한 1,000자**를 넘겼다
> (실측 985 → 1,012자). 상한을 올려 통과시키지 않는다는 것이 그 게이트 자신의 규약이다.
> ⇒ **섹션이 어느 파일에 있는지는 앵커가 아니라 판정어가 답한다** —
> `bash tools/scripts/bl-audit.sh --list DEFERRED` 의 **4번째 칸**이 파일 이름이고,
> 「파일 배치」 축이 그 대응을 rc=1 로 집행한다. 앵커 잔여는 [BL-801] 로 등재했다.
> 트리거가 도래해 ACTIVE 가 되면 **되돌려 옮긴다** — 그것이 이 파일이 얼어붙지 않게 하는 유일한 길이다.

## P1 — Risk mitigation / 알려진 broken bug 패턴 재발 방어

### BL-015

**Title:** OKX Private WS
**Category:** WebSocket / Exchange
**Priority:** P3 — ★**2026-08-18 P1→P3 강등** — 제품 범위가 Bybit demo 단일이다(`CONTEXT.md:64` 「현재 Bybit + demo 계정만 허용」). 실자금 blocker 는 [BL-003] 하나이고 OKX WS 는 그 경로에 없다. P1 라벨이 긴급도를 반영하지 않으면 P1 표 자체를 못 믿게 된다
**Trigger:** Bybit Demo 안정화 후 (BL-001 watchdog 완료 + 1주 운영) ★**2026-08-18 — 「멀티 거래소 확장」 묶음**(`roadmap.md` §권장착수순서 7): [BL-015]·BL-186b·[BL-756]·[BL-426] 넷이 「2번째 거래소를 붙인다」는 **하나의 사용자 결정**에 걸려 있다. 그 결정 전에는 단독 착수 시 값이 0이다
**Est:** M (6-8h)
**상태:** ⏳ 대기 (트리거 미도래) — OKX 는 여전히 REST 전용 — private WS 스트림 파일이 없고 websocket_task.py:277 이 미구현을 주석으로 명시한다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 소크 창 미완(soak-gate rc=2 · C1 46.24h/168h). PASS 만 도래다([ADR-024]) (2026-08-10 bl-trigger-triage)
**출처:** TODO.md L710

**원인 / 영향:** Sprint 7d OKX 어댑터는 REST 만 보유. WS event 부재로 BL-001 의 fetch_order polling 부담 가중.

**권장 접근:** OKX private WS signing 방식 구현 (Bybit 와 다름). clOrdId 매핑은 Sprint 12 C-pre 에서 이미 완료.

---

### BL-023

**Title:** KIND-B/C mutation 분류 정밀도 (xfail strict 해소)
**Category:** Trust Layer / Mutation
**Priority:** P3 — ★**2026-08-18 P1→P3 강등** — 테스트 분류 정밀도이고 머니-패스·실자금 경로에 없다. 트리거(「Trust Layer v2 검토 시」)도 외생이다
**Trigger:** Trust Layer v2 검토 시
**Est:** M (5-6h)
**상태:** ⏳ 대기 (트리거 미도래) — M4 의 xfail(strict=False) 가 그대로 남아 있고 KIND-B/C·NaN-tolerance 재설계 흔적은 docs 외 코드에 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** TODO.md L23 / `tests/strategy/pine_v2/test_mutation_oracle.py:213`

**권장 접근:** KIND-B/C 가 NaN-tolerance 한계로 mutation 구분 못 함 (현재 `xfail(strict=False)`). NaN-tolerance 알고리즘 정밀화 또는 KIND 분류 재설계.

---

### BL-493

**Title:** 조건부 진입 첫 bar 커버리지 공백
**Category:** Backend / trading
**Priority:** P3
**Trigger:** 진입 누락이 실측될 때
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — 첫 bar 커버리지 공백을 다루는 코드·테스트가 없다 — 평가 tick 지연 보정도, 재발행 보장도 미구현. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-27 live-conditional-entry

**원인 / 영향:** 평가 tick 은 bar 종료 **56초 뒤**에 돈다(실측 16:17:56 tick 이 16:16 bar 를 읽음). 시뮬은 stop 을 다음 bar 전체에서 체결 가능하다고 보지만 거래소 주문은 그 bar 의 93% 가 지난 뒤 올라간다. PbR 처럼 매 bar 재발행하는 전략은 최초 1바만 해당하나, 한 번만 발행하는 전략은 그 bar 를 통째로 놓친다.

**Risk:** 🟢

---

### BL-494

**Title:** `min_qty != qty_step` 심볼에서 최소수량 미보장
**Category:** Backend / trading
**Priority:** P3
**Trigger:** BTCUSDT 외 심볼 지원 시
**Est:** XS
**상태:** ⏳ 대기 (트리거 미도래) — 계획기는 여전히 qty_step 절삭만 하고 limits.amount.min 조회는 레포 어디에도 없다(있는 건 limits.cost.min 가드뿐). (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-27 live-conditional-entry

**원인 / 영향:** 조건부 진입 계획기는 `qty_step` 절삭만 한다. BTCUSDT 는 `limits.amount.min == qtyStep == 0.001` 이라 절삭이 최소수량을 겸하지만 일반 보장은 아니다. 둘이 다른 심볼에서는 스텝은 통과하고 최소수량은 미달인 주문이 매 tick 거부될 수 있다.

**Risk:** 🟢

---

### BL-496

**Title:** 조건부 진입 발주 순서가 엔진 체결 우선순위와 다르다
**Category:** Backend / trading (조건부 진입)
**Priority:** P3
**Trigger:** 같은 바에 조건부 진입이 2건 이상 열리고 둘 다 트리거될 수 있을 때
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — 계획기는 여전히 trade_id 순 정렬(620-621)이고 엔진은 open 거리순(strategy_state.py:1057) — 정렬 통일도 독스트링 명시도 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-27 live-conditional-entry 작업 노트 (E1 적대 검증 §9(f), 종결 시 등재)

**원인 / 영향:** 계획기는 `to_cancel`/`to_place` 를 **`trade_id` 순**으로 정렬한다(`conditional_entry_planner.py:179,297-298`). 반면 엔진의 같은 바 pending fill 후보는 **open 가격과의 거리순**으로 정렬한다(`strategy_state.py:765` `candidates.sort(key=lambda c: abs(c[2] - open_))`). 즉 두 조건부 진입이 같은 바에 둘 다 트리거되면 시뮬이 먼저 체결로 보는 쪽과 거래소에 먼저 올라가는 쪽이 다를 수 있다.

실해는 낮다 — 등재는 트리거 **이전**에 끝나고 거래소가 트리거 순서를 가격으로 결정하므로, 발주 순서가 체결 순서를 바꾸지는 않는다. 다만 **부분 등재로 끊긴 경우**(게이트 거부·네트워크 실패로 일부만 올라간 tick)에는 남는 주문이 시뮬 우선순위와 어긋난다.

**권장 접근:** 계획기 정렬 키를 `abs(stop_price - 참조가)` 로 맞추거나, 최소한 두 정렬 규약이 다르다는 사실을 계획기 독스트링에 고정한다. **정렬을 바꾸면 결정론 테스트가 함께 바뀐다**(현재 `trade_id` 순 결정론이 테스트로 고정돼 있다).

**영향 파일:** `trading/services/conditional_entry_planner.py`, `strategy/pine_v2/strategy_state.py`.

**Risk:** 🟢

---

### BL-497

**Title:** cancel → place 사이에 stop 이 부재하는 창
**Category:** Backend / trading (조건부 진입)
**Priority:** P3
**Trigger:** 재등재 churn 이 잦아지거나(BL-486), 그 창에서 놓친 돌파가 실측될 때
**Est:** M
**상태:** ⏳ 대기 (트리거 미도래) — cancel 루프(2456) 전량 후 place 루프(2501) 구조가 그대로고, amend/edit_order 는 레포 전체에 백로그 문장 외 구현이 0건이다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-27 live-conditional-entry 작업 노트 (종결 시 등재)

**원인 / 영향:** reconcile 은 취소 루프를 **전부 끝낸 뒤** 등재 루프를 돈다(`tasks/live_signal.py:406-416` → `:462-492`). 의도한 순서지만(이중 등재 방지), 그 사이 수 초 동안 거래소에 그 stop 이 **없다**. 그 창에서 가격이 트리거를 지나가면 진입을 통째로 놓치고 시뮬만 진입했다고 믿는다 — BL-492 와 같은 발산의 다른 경로다. BL-486 창 드리프트로 재등재가 104분에 8건 나므로 창이 반복 열린다.

**권장 접근:** ccxt `edit_order`(amend) 로 취소·재등재를 한 번의 왕복으로 바꾼다. Bybit v5 는 `/v5/order/amend` 로 `triggerPrice`·`qty` 수정을 지원하므로 **계약 실측이 선행**한다(미트리거 조건부에 amend 가 되는지). 대안은 place-then-cancel 순서 뒤집기인데 그 사이 **이중 등재**가 열리므로 귀속 불변식만으로는 부족하다.

**영향 파일:** `tasks/live_signal.py`, `trading/providers.py`.

**Risk:** 🟢 (fail-closed 는 아니지만 무음 미진입이라 관측 가능성이 낮다).

---

### BL-499

**상태:** ⏳ **대기 (트리거 미도래) — 단 trigger 는 이제 발화 가능하다.** ★★2026-07-28 `feat/live-observability` 정정: 이 항목의 **Trigger("취소 실패 metric 이 관측되면")가 BL-506 이전에는 구조적으로 충족 불가**였다. 그 카운터는 worker 전용이라 어떤 스크레이프 경로에도 노출되지 않았기 때문이다(BL-506 이 그 모순을 지적했다). **BL-506 Resolved 로 관측 가능성 자체는 확보됐다** — 배선 후 `qb_live_conditional_reconcile_errors_total` 의 다른 라벨(`deferred_market_inflight` 8 · `positions` 3)이 실제로 관측된다.
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
★그럼에도 **1시간 40분 soak 에서 `cancel`/`cancel_raced`/`cancel_stalled` 는 시리즈조차 나타나지 않았다.** 여전히 **"관측 안 됨" 이지 "일어나지 않음이 증명됨" 이 아니다.** 근본 경합은 열려 있다.
★**부수 발견** — 라벨 있는 Counter 는 자식이 처음 생길 때 노출되므로, 이 항목들은 `/metrics` 에 **0 으로도 나오지 않는다. 시리즈가 아예 없다.** 대시보드에서 "아직 안 일어남" 과 "그런 metric 이 없음" 이 구분되지 않는다.

**이전 상태(2026-07-28 live-ops-hygiene):** ★**신설 metric 실관측을 확인만 했다 — 결과는 0건이다.** janitor·sweeper beat 은 5분 주기로 정상 발화하지만(30분에 각 6회) `cancel_stalled`/`cancel_raced` 는 한 번도 오르지 않았다. 고착 행이 DB 에 0건이라 그 경로가 **주행되지 않았기 때문**이고, "관측되지 않음" 이지 "일어나지 않음이 증명됨" 이 아니다. 근본 경합은 그대로 열려 있다. ★단 BL-503 janitor 가 생기면서 `cancel_stalled` 의 **근거 문장이 낡았다** — "아무도 안 치운다" 는 이제 거짓이고 30분 뒤 janitor 가 처리한다(그 문구는 BL-503 에서 정정).

**이전 상태:** 🟡 부분 완화 (2026-07-27, `feat/live-conditional-hardening`). 근본 경합(취소 의도 영속 또는 dispatch 시점 재검사)은 사용자 결정으로 **마이그레이션 0** 을 택해 그대로 남는다. 이번에 한 것은 **패배와 진짜 실패를 구분해 관측 가능하게 만든 것**이다 — `transition_pending_to_cancelled` 가 rowcount 0 이면 `get_state_and_exchange_id_fresh`(식별맵 우회 컬럼 select)로 재조회해, 비-`pending` 이면 `RuntimeError` 대신 metric + 로그를 남긴다. ★**경합과 제출 중단을 라벨로 가른다** — `submitted` 인데 `exchange_order_id` 가 없으면 경합이 아니라 dispatch 가 상태만 커밋하고 거래소 왕복에서 죽은 **영구 고착**이고(`orphan_scanner` 가 조건부 진입을 면제해 아무도 안 치운다) 그 행은 매 tick 이 분기를 타 세션 등재를 영구 정지시킨다. `stage="cancel_stalled"` + `logger.error` 로 분리한다(적대 검증 지적 — 안 가르면 영구 장애가 1회성 경합 카운터에 섞여 사라진다). ★**패배해도 그 tick 의 `to_place` 는 건너뛴다(fail-closed 유지)** — `current_position` 은 취소 루프보다 **먼저** 찍은 스냅샷이라, 패배한 주문이 그 사이 체결되면 낡은 포지션 위에서 사이징한 주문이 나간다(G0.5 codex 지적, 재현 판정 후 플랜 개정).

★★**preflight 결론을 정정한다.** "취소된 16건이 전부 `exchange_order_id` 를 보유하므로 이 경로는 미주행" 은 **성립하지 않는다.** 패배한 호출은 rowcount 0 이라 행에 아무것도 안 쓰고, 이후 dispatch 가 `exchange_order_id` 를 붙이면 최종 행은 정확히 그 16건과 같은 모습이 된다. 증명된 것은 **"DB-only 취소 _성공_ 0건"** 뿐이다. 신설 metric 이 앞으로 호출·패배 횟수를 따로 센다.

**Title:** 조건부 진입 취소와 비동기 dispatch 의 경합 — 취소하려던 주문이 거래소에 올라간다
**Category:** Backend / trading (조건부 진입)
**Priority:** P2
**Trigger:** 취소 실패 metric(`stage="cancel"`)이 관측되거나 실자금 cutover 전
**Est:** M
**출처:** 2026-07-27 live-conditional-entry 최종 codex 리뷰 (재현 판정 후 등재)

**원인 / 영향:** `exchange_order_id` 가 없는 `pending` 주문은 `transition_pending_to_cancelled` 로 **DB 에서만** 취소한다(`live_signal.py:406-421`). 그 조건부 UPDATE 는 `state == pending` 을 요구하므로, 실행 워커가 `pending → submitted` 를 먼저 커밋하면 rowcount 0 → `RuntimeError` → `cancel_failed` → reconcile 중단이다. reconcile 을 중단해도 **이미 클레임한 dispatch 는 막지 못한다** — 취소하려던 조건부 진입이 거래소에 등재된다.

★**액면 수용하지 않고 재현 판정한 결과 자가 치유는 확인됐다.** 세션이 비활성이면 beat sweeper(`list_orphan_conditional_entries`)가 `state=submitted` + `trigger_price` + `reduce_only=false` + 비활성 세션으로 그 주문을 찾아 거래소에서 취소한다. 세션이 활성이면 다음 tick 의 `actual` 에 `exchange_order_id` 와 함께 들어와 정상 취소된다. **따라서 노출은 최대 1 tick(약 60초)이고 영구화하지 않는다.** 그 창에서 트리거가 돌파되면 원치 않은 진입이 체결될 수 있다는 것이 잔여 위험이다.

**권장 접근:** 취소 의도를 주문 행에 먼저 남기고(예: `cancel_requested_at`) dispatch 직전에 재검사하거나, dispatch 태스크가 라이브 세션·desired 유효성을 실행 시점에 재확인한다. 어느 쪽이든 마이그레이션 또는 dispatch 계약 변경이 필요하다.

**영향 파일:** `tasks/live_signal.py`, `trading/repositories/order_repository.py`, `tasks/trading.py`.

**Risk:** 🟡 (최대 1 tick 노출, sweeper·다음 tick 이 닫는다).

---

## P2 — Hardening / 건강도 작업

### BL-190

**Title:** PDF export (jsPDF + html2canvas client-side 또는 Playwright server-side) — backtest 결과 인쇄/오프라인 공유
**Category:** Frontend UX
**Priority:** P2 (deferrable)
**Trigger:** 외부 사용자 요청 또는 인쇄 use case 발견 시
**Est:** M (3-5h)
**상태:** ⏳ 대기 (트리거 미도래) — 사용자 결정 대기: PDF 관련 코드·의존성 0건이고, Trigger 자체가 외부 사용자 요청 + client/server 방식 선택이라 사용자 결정이 선행이다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(사용자 결정·요청). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** Sprint 41 Worker H 결정 — share link 충분 P1 deferrable, demo 첫인상 단계 미구현

**권장 접근:** share link 가 충분히 우선이라 demo 단계 미구현. 사용자 요청 시 jsPDF + html2canvas (client) 또는 Playwright (server-side) 둘 중 선택.

---

### BL-235

**Title:** N-dim acquisition surface viz (3D+ surface 또는 parallel-coord, Bayesian 전용)
**Category:** Frontend UX / Optimizer
**Priority:** P2
**Trigger:** 동승 — 옵티마이저 화면(Bayesian/Genetic 결과 표면)을 다시 손댈 때. `roadmap.md` §권장착수순서 9 「옵티마이저 파워업」 묶음([BL-236]·[BL-364] 와 함께). ★**2026-08-18 좌표 수리** — 종전 「Sprint 57+」는 **발화할 수 없는 좌표**였다: 스프린트 번호 체계는 날짜-슬러그로 대체됐고(최근 60커밋·`status.md` 에 `Sprint NN` **0건**), 번호가 오지 않으므로 `bl-trigger-sweep.sh` 가 영원히 미도래를 낸다. 본문의 `**트리거 판정:**` 이 적은 「동승 조건」이 처음부터 진짜 게이트였다
**Est:** M (8-12h, estimate)
**상태:** ⏳ 대기 (트리거 미도래) — Bayesian 시각화는 여전히 1D best_so_far inline SVG 뿐 — N차원 surface/parallel-coord 컴포넌트가 optimizer 디렉터리에 없다(2D heatmap 은 grid_search 전용). (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** ADR-013 §6 #8 deferred (실체 = `git show 94da86b1^:docs/dev-log/2026-05-12-sprint54-bayesian-genetic-grammar-adr.md` `:202` — [BL-504]). Sprint 55 = inline SVG iteration-chart (1D best_so_far) 만 구현.

**권장 접근:** recharts 또는 plotly.js 의존성 추가 검토 + cross-page consistency 의무. Bayesian / Genetic 공용.

---

### BL-236

**Title:** `objective_metric` whitelist 자유화 (BacktestMetrics 24+ 지표 노출)
**Category:** Optimizer
**Priority:** P2
**Trigger:** 동승 — 옵티마이저 목적함수/결과 표면을 다시 손댈 때. `roadmap.md` §권장착수순서 9 「옵티마이저 파워업」 묶음([BL-235]·[BL-364] 와 함께). ★**2026-08-18 좌표 수리** — 종전 「Sprint 56+」는 **발화할 수 없는 좌표**였다([BL-235] 와 같은 뿌리). 본문의 `**트리거 판정:**` 이 적은 「동승 조건」이 처음부터 진짜 게이트였다
**Est:** S (3-5h, estimate)
**상태:** ⏳ 대기 (트리거 미도래) — 3엔진 화이트리스트와 \_common.metric_value_for_objective switch 모두 sharpe/total_return/max_drawdown 3종 그대로 — 확장 미착수 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** Sprint 55 = `_SUPPORTED_OBJECTIVE_METRICS = {sharpe_ratio, total_return, max_drawdown}` 3종만 노출

**권장 접근:** BacktestMetrics 24 metric (sortino_ratio / calmar_ratio / win_rate / profit_factor 등) 노출 검토. `_objective_from_metrics` switch + FE select option 확장.

---

### BL-364

**Title:** Optimizer 진짜 string-label CategoricalField sweep (Genetic + Bayesian)
**Category:** Optimizer / Feature
**Priority:** P2
**Trigger:** 사용자 string 카테고리 sweep 요청 시 (예: maType ∈ {ema,sma,wma})
**Est:** M (4-6h)
**상태:** ⏳ 대기 (트리거 미도래) — GA·Bayesian 둘 다 비숫자 라벨을 여전히 명시 거부하고(BL-364 주석 포함), 테스트가 그 거부를 고정하고 있다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(사용자 결정·요청). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** `2026-05-30-full-inspection.md` appendix P1-9 (S4 Option A 후속)

**원인 / 영향:** S4(Option A)는 비숫자 CategoricalField 를 명확히 거부(InvalidOperation 크래시 차단)했으나, 스키마 docstring 의 본래 의도(`pine input.string / 사용자 정의 선택지` = `['ema','sma']`)는 미지원 상태. GA/Bayesian 이 individual 을 Decimal(ordinal)로 표현하기 때문.

**권장 접근:** ordinal 인코딩 — GA/Bayesian 이 categorical 차원을 index(Decimal 0..N-1)로 sample/mutate, backtest 호출 시 `field.values[int(idx)]` 로 string 디코드하여 input override 전달, best-params 에서 라벨 복원. Genetic `_sample_individual`/`_gaussian_mutation`/run-loop + Bayesian `_coerce_skopt_to_decimal`/skopt `Categorical(transform="label")` 양쪽 일관 처리. (S4 에서 사용자 결정 = Option A 우선, 본 feature 는 후속.)

---

### BL-366

**Title:** live-signal dispatch 의 OrderService DI 인라인 조립 중복 (HTTP `get_order_service` 와 drift)
**Category:** Trading / Architecture (locality / DI-dup)
**Priority:** P2
**Trigger:** trading deepening sprint 또는 OrderService 의존성 추가 시
**Est:** S-M (3-5h)
**상태:** ⏳ 대기 (트리거 미도래) — 공유 factory(create_order_service_for_dispatch)는 레포에 없고, OrderService+킬스위치 인라인 조립이 dispatch 2곳·recovery 1곳·HTTP DI 로 4중 중복이다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** `2026-06-26-trading-deepen-2.md`

**원인 / 영향:** `tasks/live_signal.py:650-682` 가 OrderService + 9 deps(order/account/kse repo, crypto, `BybitFuturesProvider()`, exchange_svc, 2 evaluator, ks_svc) 를 **인라인 조립** — `dependencies.py get_order_service`(HTTP 경로) 와 별도. 신규 인스턴스 vs singleton provider, threshold 값 등 **config drift** + 한쪽만 테스트되는 blind spot. money-path 조립이라 drift 시 dispatch 와 HTTP 가 다른 동작.

**권장 접근:** 공유 factory `create_order_service_for_dispatch(session, crypto=None)` 추출 → HTTP `get_order_service` 와 Celery dispatch 양쪽이 호출. (트레일링 안정화 후 — money-path churn 회피.)

**영향 파일:** `tasks/live_signal.py` + `trading/dependencies.py` + (선택) 신규 factory module.

**Risk:** 🟡 (money-path 조립 — CCXT 호출 전 조립 경로라 신중).

---

### BL-368

**Title:** `_merge_exit_params` 가 ccxt 키명 문자열을 3 call site 로 누설 (shallow interface)
**Category:** Trading / Architecture (shallow interface / information hiding)
**Priority:** P2
**Trigger:** trading deepening sprint 또는 4번째 provider / exchange 추가 시
**Est:** S-M (3-5h)
**상태:** ⏳ 대기 (트리거 미도래) — `_merge_exit_params` 가 여전히 키명 인자를 받고 3 call site 가 "orderLinkId"/"triggerBy"/"clOrdId" 문자열을 그대로 넘긴다. `build_ccxt_params_for_order` 는 레포에 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** `2026-06-26-trading-deepen-2.md`

**원인 / 영향:** `providers.py:135-207` 의 `_merge_exit_params` 가 `client_order_id_key`/`trigger_by_key`/`trigger_direction_key`/`trailing_stop_key` 등 **ccxt 필드명을 caller 가 알아야 하는 param** 으로 받음 → 3 call site(`:299/:480/:752`)가 `"orderLinkId"`/`"triggerBy"` 등 문자열을 분산 보유. exchange-specific 지식이 함수 안에 은닉되지 못함 → 새 exchange 추가 시 call site 마다 키 지식 복제.

**권장 접근:** `build_ccxt_params_for_order(exchange_name: ExchangeName, order: OrderSubmit) -> dict` 로 exchange→키명 dispatch 를 함수 내부로 은닉 (call site 는 ExchangeName 만 전달). lateral move + money-path 라 ccxt 전수 검증 필요.

**영향 파일:** `providers.py` (`_merge_exit_params` + 3 call site).

**Risk:** 🟡 (money-path ccxt 전수 검증).

---

### BL-369

**Title:** 3 provider `create_order` 의 try/except/finally + receipt 정규화 ~40 LOC 복붙
**Category:** Trading / Architecture (DRY / locality)
**Priority:** P2
**Trigger:** trading deepening sprint 또는 provider 예외 처리 변경 시
**Est:** S (2-4h)
**상태:** ⏳ 대기 (트리거 미도래) — 권장 helper(\_execute_create_order_with_ccxt) 가 레포에 없고 3 provider 의 try/except/finally+receipt 블록이 그대로 중복돼 있다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** `2026-06-26-trading-deepen-2.md`

**원인 / 영향:** `providers.py:279-349`(BybitDemo) / `:431-529`(BybitFutures) / `:728-795`(OkxDemo) 의 `create_order` 가 동일한 `try / except ProviderError / except ccxt BaseError / except Exception / finally close` + receipt 정규화 ~40 LOC 를 character-identical 복붙. 예외 처리 1곳 변경 시 3곳 동기화 누락 위험.

**권장 접근:** `_execute_create_order_with_ccxt(exchange, symbol, type, side, amount, price, params, timer_label) -> OrderReceipt` helper 추출 → 각 provider 는 client 구성 + helper 호출. money-path 라 거래소별 미세 차이 보존 검증 필요.

**영향 파일:** `providers.py` (3 provider create_order).

**Risk:** 🟡 (money-path — 거래소별 분기 보존 검증).

---

### BL-372

**Title:** STEP B 트레일링 live-placement — 3-리뷰어 검증 follow-up 번들 (9 항목)
**Category:** Trading / money-path / Architecture / Security / Tests
**Priority:** P2 (bundle — 개별 항목 P2/P3 혼재)
**Trigger:** Wave 3 실자금 cutover 전 (데모 기간엔 고정 bracket SL floor 가 모든 손실 경로 보호)
**Est:** M (6-10h, 항목별 분리 가능)
**상태:** ⏳ 대기 (트리거 미도래) — 9항목 중 tick정규화·ccxt assert·docstring·hedge가드·alert정제·회귀테스트·dead param은 구현됨, 하드코딩 BybitFuturesProvider() registry 우회(trading.py:1369-1371)만 잔존 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-06-26 트레일링 PR 3-리뷰어 검증 (codex CLI + Opus 6-lens 워크플로 + adversarial verify). P1 blocker 0.

**원인 / 영향:** STEP B 머지 전 Tier-1(false-flat 재시도 + 3 P2 테스트)은 본 PR 에서 해소. 아래는 adversarial 검증 통과한 잔여 follow-up. 전부 degraded-protection / 방어심화 / 문서 수준 (현재 무버그 또는 narrow). 라이브 실자금 진입 전 처리 권장.

- **(P2, money-path) same-side stale 오부착** — 🟡 **Mitigated — common path (2026-06-29, `fix/trailing-372-same-side-stale`).** `_do_place_trailing_stop` 가드가 flat/flip 만 차단하던 것에 **createdTime ↔ filled_at 불변식** 추가: `PositionInfo.created_at`(Bybit raw `info.createdTime`/`createdAt`, ADD 시 불변 — ccxt normalized `timestamp` 가 아닌 raw 사용으로 ADD 오탐 회피[G1]) > `order.filled_at` + 2s tol → reopened 판정 → benign skip(`skipped_position_reopened` metric). 타임스탬프 결측 시 side-only degrade. placement 창의 **common(>2s) 구간을 닫음**(원 버그의 ~30s 창 대부분). 검증 = G1 codex(GO_WITH_FIXES) → TDD(매핑 4 + 가드 7 + session 전달 1 + helper 단위 1) → G2 codex(NO_GO=완전성 기준, 잔여 지적) + G3 fresh(SOUND, **mutation 4/4 catch**). **잔여(narrow, 전부 [BL-375](#bl-375)): (a) sub-2s reopen (b) fetch↔set TOCTOU (c) reconcile-lag late filled_at (d) worker clock-skew>2s false-skip.** 데모 기간 = 고정 bracket SL floor 가 손실 경로 보호. (이력) codex Evaluator(2026-06-28) [P1] = 실자금 cutover 전 필수 → common path 해소, 완전 닫기는 BL-375(거래소 fill-time).
- **(P2) tick-normalization** — `set_trading_stop` 가 `trailingStop` distance 를 price precision 정규화 없이 raw `str(Decimal)` 전송 → coarse-tick 심볼 Bybit 거부 가능(fail-safe: 거부→retry→critical alert). `providers.py:586-591`.
- **(P3, architect) 하드코딩 provider** — `_place_trailing_stop_with_session` 가 `BybitFuturesProvider()` 직접 생성, dispatch registry 우회(LESSON-063). Protocol 미노출 강제 + live=BL-003 stub 라 현재 무버그. 2nd native-trailing 거래소 추가 시 SSOT 라우팅. `tasks/trading.py:954-958`.
- **(P3, architect) hedge-mode 가정** — `fetch_position` first-size>0 = one-way mode 암묵 가정. hedge-mode 면 wrong-leg 가능(expected_side 가드가 benign skip 으로 중화). 문서화 또는 side/positionIdx 필터. `providers.py:637-644`.
- **(P3, money-path) docstring 모순** — `set_trading_stop` docstring 이 "독립 fetch_position 사후검증" 주장하나 미구현(ccxt retCode raise 로 실거부는 잡힘). 주석 정정 또는 재조회 구현. `providers.py:598`.
- **(P3, security) kill-switch bypass 2nd-line 부재** — trailing placement 가 kill-switch 우회(엔드포인트가 포지션 증가 불가 전제). `reduceOnly`/`positionIdx`/ccxt-version-assert 등 belt-and-suspenders 없음. one-way 모드선 exit-side market 이 포지션 close 라 framing 다소 과장. `providers.py:600` / `tasks/trading.py`.
- **(P3, security) alert 정보 노출** — catch-all `str(exc)` 가 미정제로 Slack 전송(사설 채널, api_secret 부재이나 sign-error 시 public apiKey/params 가능). classified reason 만 전송 + raw 는 `logger.exception`(team 기존 stance `providers.py:357` 정합). `tasks/trading.py:980-990,1007-1015`.
- **(P3, qa) 회귀 가드 2건** — `leverage is None` spot-skip 분기 + `expire_on_commit=False` 불변식 (4 enqueue 사이트 post-commit attr read load-bearing) 전용 테스트 신설.
- **(P3, ponytail) dead param cut** — `set_trading_stop` 의 `trigger_price`/`trailingTriggerPrice`(activePrice) 라이브 caller 0 + 그 테스트(~17L) 제거 (activation-price 스토리 실현 시 재추가).

**Risk:** 🟢 (전부 degraded-protection / 방어심화 / 문서 — 데모 기간 bracket SL floor 보호).

---

### BL-373

**Title:** OCO 형제취소 (sibling-cancel) — standalone exit order 시점에 구현
**Category:** Trading / money-path
**Priority:** P2 (defer)
**Trigger:** BL-365 standalone-trigger 발주 도입 시 (= app-side OCO 가 실제 필요해지는 시점)
**Est:** S-M (3-5h)
**상태:** ⏳ 대기 (트리거 미도래) — oco_group_id 컬럼·전달만 존재하고 코드 주석이 여전히 'Wave 2 deferred' — sibling-cancel 오케스트레이션 코드는 레포에 없고 Trigger(BL-365 standalone 발주)도 미도래 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-06-28 grilling (트레일링 후속 scope 결정)

**원인 / 영향:** `oco_group_id` DB 컬럼 + OrderSubmit 전달은 이미 존재하나 sibling-cancel 오케스트레이션은 미구현. 현재는 entry-attached bracket 이라 거래소가 네이티브 OCO(한 다리 체결 시 형제 자동취소)를 처리 → app-side sibling-cancel 은 YAGNI. standalone exit order(BL-365) 발주 시점에 두 다리가 독립 주문이 되면 그때 app-side 형제취소가 필요.

**Risk:** 🟢 (현재 네이티브 OCO 로 커버 — defer 안전).

---

### BL-379

**Title:** pine_v2 user-function 지역변수 `x[1]` history = na (subscript in `=>` 깨짐)
**Category:** Strategy / pine_v2 (interpreter)
**Priority:** P2 (latent harm-class — 코퍼스 8종 미트리거, 흔한 패턴)
**Trigger:** pine_v2 robustness 후속
**Est:** M (4-6h)
**상태:** ⏳ 대기 (트리거 미도래) — \_eval_subscript 가 여전히 \_var_series 만 보고 \_scope_stack 을 안 봄 — 추적도 unsupported reject 도 미구현. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-06-30 QA codex G2 challenge + 직접 재현

**원인 / 영향:** `_eval_subscript`(interpreter.py:653)가 `x[1]`을 `_var_series`에서만 조회하는데, user function(`f(s) => ...`) 지역변수는 `_var_series`에 append 되지 않음. 재현: `f(s) => prev = s[1]` → `[nan]*N`(항상 na) vs top-level `close[1]` 정상. 코퍼스 8종은 미트리거(전부 인라인/builtin) 이나 `f(x)=>...x[1]...` (지표 함수 내 history 참조) 는 흔한 패턴 → 해당 전략 silent divergence. **권장:** user-function 스코프 변수 history 추적 또는 명시적 unsupported reject.

---

### BL-380

**Title:** Track A INFORMATION/UNKNOWN alert 무경고 drop (docstring 계약 위반)
**Category:** Strategy / pine_v2 (Trust Layer / Track A)
**Priority:** P2 (신뢰 표면)
**Trigger:** Track A 신뢰 표면 sprint
**Est:** S-M (3-5h)
**상태:** ⏳ 대기 (트리거 미도래) — INFORMATION/UNKNOWN 이 여전히 무경고 continue 이고, v2_adapter 는 state.warnings 만 전파해 VirtualRunResult.warnings 유실 그대로. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-06-30 QA LuxAlgo 0-trade 추적 + codex G2

**원인 / 영향:** `virtual_strategy.py:128-130` 가 INFORMATION/UNKNOWN alert 를 경고 없이 `continue` (docstring `:12` 은 "무시 + warning" 약속 — 계약 위반). LuxAlgo `alertcondition(.., 'Price broke the down-trendline upward')` → strict 기본 INFORMATION 키워드 `\btrendline\b` → 무경고 무시 → **0 trades, status=ok** (지표 수치는 정확). loose 모드(opt-in)면 directional. **추가:** 경고를 추가해도 `run_backtest_v2`(v2_adapter.py:181)가 `state.warnings`만 내보내 `VirtualRunResult.warnings` 유실. **권장:** (a) ignored actionable alert 시 wrapper.warnings 기록 + (b) VirtualRunResult.warnings → backtest parse warnings 전파. (strict 기본 정책 자체는 유지.)

---

### BL-381

**Title:** Track A `VirtualRunResult` var_series/warnings 미반환 → trust-parity digest 공허
**Category:** Strategy / pine_v2 (Trust Layer CI)
**Priority:** P2 (meta / 검증 인프라)
**Trigger:** Trust Layer CI 강화
**Est:** S (2-4h)
**상태:** ⏳ 대기 (트리거 미도래) — VirtualRunResult 에 warnings 만 있고 var_series 필드·반환이 여전히 없어 추출기 getattr 이 빈 dict 를 digest 한다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-06-30 QA codex G2 + diff-challenge

**원인 / 영향:** `VirtualRunResult`(virtual_strategy.py:61) 에 var_series 필드 부재 + 미반환. `test_trust_layer_parity.py:239` 의 golden 추출기가 `getattr(.., 'var_series', {})` → 빈 dict digest. 결과: Track A 전략(i2_luxalgo 등)의 지표 변화(예: ta.atr→slope)가 var_series_digest 에 반영 안 됨 → documented P-3 parity 검증이 부분 공허(BL-378 fix 시 i2_luxalgo baseline 불변이 이를 노출). **권장:** VirtualRunResult 에 var_series/warnings 노출 + 추출기 배선.

---

### BL-382

**Title:** qty=1.0 fallback sizing-source FE 미표면화 (자본초과 백테스트 투명성)
**Category:** Backtest / 투명성
**Priority:** P2 (투명성)
**Trigger:** sizing 투명성 sprint
**Est:** S (2-4h)
**상태:** ⏳ 대기 (트리거 미도래) — BE 는 sizing_source 를 config JSONB 에 저장하지만 BacktestConfigOut 에 없고, FE schemas.ts·AssumptionsCard 어디에도 sizing 표면화가 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-06-30 QA F1 (codex G2 = harm-class 아닌 transparency)

**원인 / 영향:** `default_qty_type` 미지정 전략(PbR/UtBot)은 qty=1.0 (1 BTC/trade ≈ $42k notional vs $10k capital) → mdd=-16.95/-41.47, fees $156k. 엔진은 `mdd_exceeds_capital=True` 정직 flag + FE KPI 가 자본초과 손실 표시. **그러나** sizing_source 가 FE 결과 schema 부재(schemas.ts:254), AssumptionsCard 가 "1 BTC 고정수량 fallback" 미표면화(assumptions-card.tsx:88). **권장:** config 응답에 sizing_source/default_qty 포함 + fallback 시 경고 표시.

---

### BL-384

**Title:** ta.valuewhen 이 na-source occurrence skip (TV 는 na 기록)
**Category:** Strategy / pine_v2 (indicator parity)
**Priority:** P3 (좁은 edge)
**Trigger:** pine_v2 parity 후속
**Est:** S (2-3h)
**상태:** ⏳ 대기 (트리거 미도래) — stdlib.py:308 이 여전히 `source is not None and not _is_na(source)` 로 na occurrence 를 skip 하고, na 기록을 강제하는 테스트도 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-06-30 QA codex G2 + 직접 재현

**원인 / 영향:** `stdlib.py:305-307` 가 `cond_bool and source not na` 일 때만 occurrence 기록. cond=true + source=na 인 occurrence 를 TV 는 기록(na 반환), QB 는 skip → 이전 non-na 반환. 재현: src=[10,na] → `valuewhen(cond,src,0)` QB=10, TV=na. RsiD `valuewhen(plFound, osc[lbR], 1)` (osc warmup 시 na) 후보. 좁은 edge. **권장:** cond=true occurrence 는 source 가 na 여도 기록.

---

### BL-385

**Title:** PineVersion enum v6 부재 → `//@version=6` 가 v5 로 collapse
**Category:** Strategy / pine_v2 (coverage / 메타데이터)
**Priority:** P3 (경미)
**Trigger:** pine_v2 coverage 후속
**Est:** XS (1-2h)
**상태:** ⏳ 대기 (트리거 미도래) — PineVersion enum은 여전히 v4/v5뿐이고 \_detect_version이 v6를 v5로 반환하며, DB enum에도 v6 값이 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-06-30 QA F3

**원인 / 영향:** `PineVersion` enum(strategy/models.py)이 v4/v5 뿐 → `_detect_version`(strategy/service.py)이 `//@version=6`(PbR, bs)를 v5 로 보고. 메타데이터 부정확(실행엔 무영향). **권장:** v6 enum 값 추가(alembic enum-add 패턴, LESSON-066).

---

### BL-386

**Title:** v4 bare math builtin `floor`/`ceil`/`round`/`sqrt` 미별칭 (preflight reject)
**Category:** Strategy / pine_v2 (coverage)
**Priority:** P3 (경미, 안전 측 — silent 아님)
**Trigger:** pine_v2 coverage 후속
**Est:** XS (1-2h)
**상태:** ⏳ 대기 (트리거 미도래) — interpreter/coverage 양쪽 \_V4_ALIASES 에 abs/max/min 만 있고 floor·ceil·round·sqrt bare 별칭이 여전히 없다 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-06-30 QA F4

**원인 / 영향:** `SUPPORTED_FUNCTIONS` 의 `_V4_ALIASES` 가 abs/max/min 만 포함, `floor`/`ceil`/`round`/`sqrt`(유효 Pine builtin) 부재 → v4 스크립트의 `floor()` 가 unsupported flag(preflight 차단). over-strict 이나 silent 아님(안전). **권장:** v4 bare math builtin 을 `math.*` 로 재라우팅하는 alias 추가.

---

### BL-387

**Title:** backtest sizing-canonical → config_payload 가 untyped `dict[str,Any]` seam 으로 영속 경계 횡단 (key drift 시 silent 잘못된 sizing)
**Category:** Backtest / Architecture (shallow seam / money-path)
**Priority:** P2
**Trigger:** backtest deepening sprint 또는 sizing 로직 변경 시
**Est:** S-M (3-5h)
**상태:** ⏳ 대기 (트리거 미도래) — SizingCanonical 타입 VO 미도입 — dict[str,Any] seam 그대로. 단 config 조립은 .get 이 아니라 직접 인덱싱이라 drift 는 KeyError(무음 아님). (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** `2026-06-30-backtest-deepen.md` (codex challenge 최강 후보)

**원인 / 영향:** `service.py:754-876` `_resolve_sizing_canonical` 이 6-key `dict[str, Any]` 를 반환하고 `service.py:188-212` 가 `.get('leverage', default)` 식으로 config_payload 를 손-조립한다. 두 dict 의 key 일치가 타입으로 보장되지 않아, resolve 쪽 key 가 rename 되면 조용히 default 로 떨어져 `sizing_source`/`leverage_basis` 가 잘못 영속될 수 있다(money-affecting). `dict[str, Any]` = Interface 가 거의 없는 shallow seam 이 백테스트 입력의 진실을 DB 경계로 흘려보낸다.

**권장 접근:** sizing 결정을 typed value object(`SizingCanonical`)로 만들어 `_resolve` 출력과 config 영속 사이 Seam 에 타입 부여 → key 불일치가 검증/타입 시점에 잡히게. `test_resolve_sizing_canonical` 8-case 존재하나 resolve 출력↔config_payload key-match 단언 부재 = 부분 gap.

**영향 파일:** `backtest/service.py` (`_resolve_sizing_canonical` + config_payload 조립), `config_mapper.py`.

**Risk:** 🟡 (money-path sizing — 영속 값 parity 검증 필요).

---

### BL-377

**Title:** pine_v2 non-finite 주문/청산 가격 + 초대형 유한 length OverflowError (BL-376 후속 잔여)
**Category:** Strategy / pine_v2 (interpreter robustness)
**Priority:** P3
**Trigger:** pine_v2 robustness 후속 또는 실자금 cutover 전 (BL-376 후속)
**Est:** S (2-4h)
**상태:** ⏳ 대기 (트리거 미도래) — entry stop/\_num 은 여전히 \_is_na 만 보고 isfinite 가드가 없고, \_coerce_length 에도 maxsize 상한이 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-06-30 BL-376 G2 codex challenge [P1#3/#4] + G3 fresh review [LOW]

**원인 / 영향:** BL-376 이 na/inf 의 raw-예외-escape harm class 를 닫았으나, 다음 2종 잔여는 escape 가 아니거나(deterministic 오값) 별도 trigger 라 BL-376 scope 밖으로 이연:

- **non-finite 주문/청산 가격:** `strategy.entry(stop=inf)` / `strategy.exit(stop|limit|profit|loss|trail=inf)` 는 실측상 raw 예외 escape 가 **아니라** status='ok' + 무-NaN 의 deterministic false-fill(예: inf short-stop 이 다음 bar 체결). 라이브는 이미 `_to_decimal`(isfinite) 로 drop. 백테스트 path 에 동일 isfinite drop 미러 필요(entry `stop` = `interpreter.py:1265`, exit `_num` = `interpreter.py:1325-1340`).
- **초대형 유한 length OverflowError:** `_coerce_length` 는 na/inf/<1 만 차단 → `ta.sma(close, close*1e17)`(유한 ~1e19 > `sys.maxsize`) 는 통과 후 `deque(maxlen=int(huge))` 가 `OverflowError` escape(G3 실측). harm class 이나 trigger 가 비현실적이고 완전 수정은 sane max-length cap(제품 결정) 필요.
- (참고, 별도 boundary) `input.int` override `int()`(`interpreter.py:982`)에 `Decimal('NaN')` override 시 ValueError — optimizer 가 NaN override 미발행이라 도달 불가. config boundary(`BacktestConfig`) finite 검증이 더 적절.

**권장 접근:** (a) 백테스트 entry stop + `_num` exit level 에 `math.isfinite` drop 가드(라이브 `_to_decimal` 미러). (b) `_coerce_length` 에 sane upper-cap 추가(또는 `value > sys.maxsize` → None). 골든 테스트 동반.

**Risk:** 🟢 (전부 현재 deterministic 또는 비현실적 trigger — escape 아니거나 라이브 이미 안전. 실자금 cutover 전 처리 권장).

---

### BL-375

**Title:** trailing same-side stale — 완전 닫기 (거래소 fill-time 소싱 + TOCTOU/sub-tol 잔여)
**Category:** Trading / money-path
**Priority:** P2
**Trigger:** Wave 3 실자금 cutover 전 (데모 기간엔 고정 bracket SL floor 가 손실 경로 보호)
**Est:** M (4-8h)
**상태:** ⏳ 대기 (트리거 미도래) — 거래소 fill-time 소싱 컬럼·경로가 없고 코드 주석 자체가 잔여 4건을 미해결로 기록 중이다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-06-29 BL-372 same-side stale fix 의 G1/G2 codex Evaluator (BL-372 가 common path 만 닫음)

**원인 / 영향:** BL-372 가드(`position.createdTime > order.filled_at + 2s`)는 placement 창의 common(>2s) 구간만 닫는다. 4 narrow 잔여:

- **(a) sub-tolerance reopen** — fill 후 2s 내 close+reopen 은 미탐(2s 는 clock-skew 흡수용 tolerance). codex G2 [P1].
- **(b) fetch↔set TOCTOU** — `_do_place_trailing_stop` 가 createdTime 을 read 한 뒤 `set_trading_stop` 보내는 ms 윈도에 reopen 되면 거래소가 현재 포지션에 부착(check-then-act inherent race). codex G2 [P1].
- **(c) reconcile-lag late filled_at** — `filled_at` 은 fill _처리_ 시각(`datetime.now(UTC)`)이지 거래소 체결 시각이 아님. reconcile 경로(watchdog/reconciler)에선 실제 체결보다 늦게 기록 → reopened `createdTime < filled_at` 이면 가드 통과. codex G1 [P1-3].
- **(d) worker clock-skew** — worker clock 이 거래소보다 >2s 느리면 정상 open 도 `createdTime > filled_at + 2s` 로 false-skip(저위험: trailing 미부착, bracket SL floor 유효). codex G2 [P2].

**권장 접근:** 근본 = **거래소 보고 체결 시각 소싱**. 4 fill-recording 경로(sync receipt / WS event / watchdog / reconciler)에서 exchange order/exec timestamp 추출 → 비교 기준으로 사용(전용 컬럼 또는 전달) → (c)(d) 해소. (a)(b) inherent race 는 거래소-side conditional(예 createdTime 조건부 trading-stop) 또는 placement 전 재확인(refetch-after-set verify)으로 좁힘. clock-skew 는 NTP 전제 문서화.

**Risk:** 🟡 (전부 narrow residual — common WS/sync path 는 BL-372 로 차단, 데모 bracket SL floor 보호. 실자금 cutover 전 처리 권장).

---

### BL-393

**Title:** pine_v2 `strategy.exit` trail_points/trail_offset 틱 단위 시맨틱스 (TV=틱\*mintick, QB=price-distance) + `syminfo.mintick` 0.01 하드코딩
**Category:** Strategy / pine_v2 (TV parity)
**Priority:** P2
**Trigger:** pine_v2 parity 후속 또는 틱 기반 exit 전략 사용자 등장 시
**Est:** M (4-6h — 실 심볼 mintick 소싱 결정 포함)
**상태:** ⏳ 대기 (트리거 미도래) — 처방 (a) 문서화만 완료; mintick 은 여전히 0.01 하드코딩이고 CCXT precision 소싱·틱 해석 opt-in config 는 코드에 전무. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(사용자 결정·요청). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-05 TV-parity sprint — 사용자 전략(HMA+ATR+Curvature) 커버리지 판정

**원인 / 영향:** TV 의 `trail_points`/`profit`/`loss` 는 **틱 단위**(값 × syminfo.mintick = 가격 오프셋). QB 인터프리터는 price-distance 로 해석(`interpreter.py` `_num` 근사, mintick=0.01 고정 — `interpreter.py:1131`). ATR 값을 trail_points 에 넣는 전략(사용자 전략 포함)은 TV 에선 초미세 트레일링(예: ATR 500 → $5)이 되어 승률 98%+ 의 **가짜 성적**이 나오고, QB 는 저자 의도(가격 거리)에 가깝게 동작 — 즉 발산의 원인이 TV 쪽 함정. 그러나 틱 단위를 의도한 전략은 QB 에서 발산.

**권장 접근:** (a) 발산 방향/원인을 supported-indicators 문서에 명시(완료: 2026-07-05 노트) (b) 실 심볼 mintick 소싱(CCXT market precision) + 틱 해석 opt-in config. TV 정합 모드(fill_timing 과 묶음) 시 함께 검토.

**Risk:** 🟢 (현 동작이 보수적/의도-근접. 문서화 우선).

---

### BL-490

**Title:** `margin_mode` 가 엔진에 전달되지 않고 청산 모델이 isolated 전용이다
**Category:** Backend / trading (레버리지 모델 정확도)
**Priority:** P2
**Trigger:** cross 계정 라이브 사용 시 / BL-186 풀 모델 진행 시
**Est:** M-L (구조 변경)
**상태:** ⏳ 대기 (트리거 미도래) — 엔진 kwargs 에 margin_mode 가 여전히 없고(주석으로 명시) leverage_model 은 MMR 0.5% isolated 단일 모델 그대로다 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 선행 BL-186=PARTIAL (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-26 live-engine-parity 적대적 검증 (BL-483 구현 중).

**원인 / 영향:** `StrategySettings.margin_mode`(`cross`/`isolated`)가 엔진에 전달되지 않고 `strategy/pine_v2/leverage_model.py` 는 **isolated 전용**이다(MMR 0.5% 고정, `liquidation_price = entry x (1 - 1/lev + mmr)`). BL-483 이 `leverage` 를 배선하면서 `check_liquidations` 가 라이브에서 처음 활성화됐는데, **cross 계정은 실제보다 훨씬 이르게 강제 청산으로 판정**된다. 강제 청산은 실제 reduce-only 주문을 낸다.

레버리지별 롱 청산 임계 실측:

```
lev   2x -> 진입가 x 0.50500  (하락 49.50%)
lev  10x -> 진입가 x 0.90500  (하락  9.50%)
lev  25x -> 진입가 x 0.96500  (하락  3.50%)
lev 125x -> 진입가 x 0.99700  (하락  0.30%)
```

현재 등록된 라이브 전략은 전부 `isolated` / 레버리지 2 라 즉각 영향은 없다. 이번 스프린트는 **화면 고지**로 정직 처리했다(강제 청산 행 + "격리 증거금 기준이며 거래소의 실제 청산과 다를 수 있습니다" 문구).

**권장 접근:** cross 계정 통합 증거금 모델 신설. 계정 전체 자산 대비 유지증거금 합으로 판정해야 하는데 현재 엔진은 포지션 단위라 구조 변경이 크다. BL-186 과 묶어 설계.

**영향 파일:** `strategy/pine_v2/leverage_model.py`, `strategy/pine_v2/strategy_state.py`, `tasks/live_signal.py`.

**Risk:** 🟡 (cross 사용자 조기 강제 청산 — 화면 고지로 완화 중).

---

### BL-508

**Title:** `qb_active_orders` 의 inc/dec 계약이 multiprocess 에서 절대값을 보장하지 못한다 — 재기동마다 영구 편향
**Category:** Backend / observability (trading)
**Priority:** P2
**Trigger:** gauge 를 근거로 운영 판단·경보를 붙이려 할 때, 또는 실자금 cutover 전
**Est:** M
**상태:** ⏳ 대기 (트리거 미도래) — gauge 는 여전히 multiprocess_mode="sum" + inc 1곳/dec 13곳 구조이고, DB 개수를 .set() 하는 스냅샷 경로가 코드·테스트 어디에도 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-observability — G1 codex 적대 검증이 예측하고 **soak 이 산술까지 맞춰 확증**

**원인 / 영향:** `inc` 는 1곳(`order_service.py:431`, API+worker), `dec` 는 13곳(worker 11 · ws_stream 2 · API 1)에 흩어져 있다. multiprocess 모드에서 `sum` 은 **프로세스별 델타 파일의 합**이므로, 콜드 스타트로 파일이 비면 그 순간 in-flight 였던 주문의 `inc` 가 유실되고 `dec` 만 나중에 찍혀 **영구 −N 편향**이 남는다.

★**실측으로 확증했다.** soak 중 metric `qb_active_orders = 0.0` 인데 DB 실제 in-flight = **1**. 산술이 전부 설명된다 — 재기동 이후 생성 **+7** / 종료 **−6** / **재기동 이전 생성 → 이후 종료 1건의 고아 dec −1** = **0**. 그 1건은 `03:13:52` 생성 → `03:34:10` 취소로 원장에서 특정된다.

★**BL-506 이 만든 결함이 아니다.** 배선 전에는 API 프로세스의 `inc` 만 수집돼 **단조 증가**였으니 더 나빴다. BL-506 이 한 일은 **편향을 보이게 만든 것**이다.

**권장 접근:** inc/dec 계약을 버리고, 한 프로세스가 DB 의 `pending + submitted` 개수를 주기적으로 `.set()` 하는 **스냅샷 gauge** 로 교체한다. ★**주의** — `mark_process_dead` 는 `live*` 파일만 지우므로 지금은 **죽은 자식의 델타 파일이 남아 있어야 산술이 맞는다**(BL-509 와 결합). 파일 회수를 먼저 하면 이 gauge 가 즉시 깨진다.

**영향 파일:** `common/metrics.py`, `trading/services/order_service.py`, `tasks/trading.py`, `tasks/live_signal.py`, `tasks/conditional_entry_janitor.py`, `trading/websocket/*`.
**Risk:** 🟡 (동작 무영향 · 그러나 이 gauge 를 근거로 한 판단이 공허하다)

---

### BL-510

**Title:** 라이브 세션 생성이 `read_only` 계정을 막지 않는다 — 화면은 그 계정을 기본 선택으로 놓는다
**Category:** Backend / trading (세션 등록) + Frontend
**Priority:** P2
**Trigger:** 사용자가 계정을 여러 개 등록한 상태에서 세션을 시작할 때
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — register() 계정 게이트는 여전히 exchange/mode 만 검사하고 read_only 는 청산·표시 경로에만 있다; 세션 폼도 읽기 전용 배지/비활성화 없음. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-observability — soak 세션 생성 중 화면 관측 + 코드 대조

**원인 / 영향:** `LiveSignalSessionService.register()` 의 계정 게이트는 `account.exchange != bybit or account.mode != demo` **뿐**(`live_session_service.py:108-112`). `read_only` 는 검사하지 않는다. `read_only` 강제는 **청산**(`close_service.py:59-60` → 422)과 **표시**(`position_service.py:301-302`)에만 있다.

즉 **읽기 전용 키로 라이브 자동매매 세션을 시작할 수 있다.** 세션은 평가·신호 생성까지 정상 진행하고 **주문 단계에서야** 실패한다(과거 원장에 `retCode 10005 Permission denied` 2건 실재).

★**화면이 악화시킨다** — 계정 선택 콤보박스가 `bybit demo- aaa`(`read_only=true`)를 **기본 활성 옵션**으로 놓고, 라벨만으로 두 계정을 구분할 수 없다. 쓰기 계정은 `bybit demo` 다.

**권장 접근:** `register()` 에서 `read_only` fail-closed(422) + 콤보박스에 읽기 전용 배지·비활성화.
**Risk:** 🟡

---

### BL-516

> ### 🟡 **권장안 2종 기각 · 「계측 우선」으로 착수 (2026-07-30 close-mismatch-soak)**
>
> 본문의 **권장 접근(leg 분리 / 발주 직전 재확인)은 둘 다 채택하지 않았다.** 근거:
>
> - ★**leg 분리 = 기각.** `Order.reduce_only.is_(False)` 술어가 **4곳**
>   (`order_repository.py:275` reconciler · `:315` sweep · `:347` janitor · `:513` 진입원장)이라
>   청산 leg 가 **모든 lifecycle 쿼리에서 배제**된다 → 세션 종료 후에도 안 걷히는 **고아 reduce-only
>   조건부 주문**. 계획기 주석이 스스로 _"사용자 손절을 지우는 것이 최악의 결함"_ 이라 적은 것의 거울상이다.
>   게다가 같은 trigger 가의 조건부 2건은 **체결 순서가 보장되지 않아** 진입 leg 가 먼저 체결되면
>   뒤이은 청산 leg 가 `110017 same side` 가 된다 — **BL-560 이 지금 재고 있는 바로 그 신호를 늘린다.**
> - ★**발주 직전 재확인 = 무효.** 갭은 **「등재 → 트리거」 사이**인데 거기에 우리 코드가 없다.
>   게다가 `fetch_open_positions`(`live_signal.py:929`) + 3중 fail-closed 로 **이미 구현돼 있다.**
>
> **채택 = 계측 + 좁은 가드.** 발주 형태 불변(1건, `reduce_only=False`, 수량 산식 그대로).
> `crosses_zero` / `overshoot_ratio` 파생값 + `qb_live_conditional_reversal_total{bucket}` +
> `max_reversal_overshoot_ratio` 캡(**기본 `None` = 비활성**). 깨진 기존 테스트 **0건** —
> `test_reversal_uses_full_target_delta` 가 살아남아 "수량 불변" 계약의 수호자가 된다.
>
> ★**soak 이 이 선택을 사후 정당화했다.** BL-560 실측 6/6 이 **반전 체결 직후 방향 불일치**를
> 보여줬다 — 반전 주문이 그 기계다. leg 분리를 했다면 reduce-only 를 **더 만들어** 거절을 늘렸을 것이다.
>
> **미검증:** `qb_live_conditional_reversal_total` 은 검증 창(3분)에 반전이 없어 **실주행 미발화**다.
> 다음 회차에서 확인할 것.

**Title:** 조건부 진입이 `reduce_only=False` 로 하드코딩돼 반전 주문이 기존 포지션을 보호 없이 가로지른다
**Category:** Backend / trading (조건부 진입)
**Priority:** P2
**Trigger:** 실자금 cutover 전
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래) — 「계측 우선」으로 착수**(2026-07-30 close-mismatch-soak). 권장안 2종(leg 분리 / 발주 직전 재확인) 기각. 발주 형태 불변 + overshoot 계측 + 기본 비활성 캡.
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-observability soak 실관측 + 코드 대조

**원인 / 영향:** `live_signal.py:628` 이 조건부 진입 `OrderRequest` 를 **무조건 `reduce_only=False`** 로 만든다. `_action_is_reduce_only`(`:182-188`)는 **시장가 close 에만** 적용된다.

★**soak 실관측** — 03:13:52 에 `qty 0.06` 매도 조건부 주문이 나갔다. 이는 기존 롱 0.03 청산 + 신규 숏 0.03 진입(stop-and-reverse)인데, **청산 부분에 reduce-only 보호가 없다.** 포지션이 그 사이에 이미 줄어 있으면 초과분이 반대 포지션을 연다.

**권장 접근:** 반전 주문을 청산 leg(`reduce_only=True`)와 진입 leg 로 분리하거나, 거래소의 reduce-only 시맨틱을 쓸 수 없다면 발주 직전 포지션 재확인을 강제한다.
**Risk:** 🟡

---

### BL-519

**Title:** 컨테이너로 API 를 띄우는 배포에는 multiprocess 배선이 없다 — 조용히 폴백해 worker 지표를 영영 못 본다
**Category:** Infra / observability
**Priority:** P2
**Trigger:** 프로덕션 배포 시
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — API 컨테이너 서비스도, production 미설정 경고 로그도 아직 없다 — 폴백은 여전히 무증상이다 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(Beta·프로덕션 배포). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-observability 적대 검증

**원인 / 영향:** `docker-compose.yml` 에 API 서비스가 **없다**(호스트 uvicorn). `PROMETHEUS_MULTIPROC_DIR` 을 주입하는 곳은 compose 의 worker 4곳 + Makefile 2곳뿐이다. `Dockerfile` 이 `/metrics` 디렉토리를 만들어 두지만 **그 값을 주입하는 곳이 레포 전체에 없다.**

컨테이너 API 배포에서는 env 미설정 → 단일 프로세스 폴백 → **worker 지표가 안 보인다.** 그리고 그 상태가 200 을 반환하므로 **무증상**이다.

★이번 세션에서는 `.env.example` 과 `docker-entrypoint.sh` 주석으로 **경고만** 남겼다. 배포 매니페스트가 이 레포에 없어 코드로 강제할 수 없다.

**권장 접근:** 배포 매니페스트에 env + 공유 볼륨을 넣고, API 기동 시 `PROMETHEUS_MULTIPROC_DIR` 미설정을 **production 에서 경고 로그**로 남긴다.
**Risk:** 🟡

---

## P3 — Nice-to-have / 컨벤션 정합

### BL-491

**Title:** 백테스트 폼이 Live 레버리지를 미러하지 않는다 (차단 사유가 이미 사실이 아니다)
**Category:** Frontend / 정합
**Priority:** P3
**Trigger:** 백테스트↔라이브 폼 패리티 작업 시
**Est:** S (2-3h)
**상태:** ⏳ 대기 (트리거 미도래) — live_blocked_leverage 분기와 liveLeverage===1 게이트가 그대로 있고 leverage 는 상수 1 로 초기화 — 미러 배선 미착수. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-26 live-engine-parity 적대적 검증.

**원인 / 영향:** `useBacktestForm.ts` 의 `liveLeverage != null && liveLeverage !== 1` 이 `live_blocked_leverage` 를 내고 `BacktestSizingFieldSet.tsx` 가 "Live 미러" 옵션을 `liveLeverage === 1` 로 막는다. 원래 문구는 "백테스트의 1배 자기자본 기준과 비대칭" 이라 설명했는데 **거짓**이다. 같은 폼에 백테스트 레버리지 입력이 있고 `v2_adapter` 가 `leverage=cfg.leverage` 를 같은 엔진 게이트로 넣는다. BL-483 배선 후엔 라이브도 레버리지를 반영하므로 차단 사유가 더 이상 없다.

이번 스프린트는 **문구만** 사실대로 고쳤다(술어 불변). 실제 미러링 배선은 미착수.

**권장 접근:** Live 설정(leverage / margin_mode / position_size_pct)을 백테스트 config 로 미러하는 경로를 열고 `live_blocked_leverage` 분기를 제거한다. 미러 시 백테스트↔라이브 패리티가 폼 수준에서도 성립한다.

**영향 파일:** `apps/web/src/app/(dashboard)/backtests/_components/forms/useBacktestForm.ts`, `.../BacktestSizingFieldSet.tsx`, `.../live-settings-badge.tsx`.

**Risk:** 🟢 (UX / 정합. 금전 영향 없음).

---

### BL-389

**Title:** backtest finance math 10 함수 (~250 LOC) 가 v2*adapter god-file 에 혼재 — `engine/metrics.py` Deep Module 추출 (locality)
**Category:** Backtest / Architecture (shallow-by-size / locality)
**Priority:** P3
**Trigger:** backtest deepening sprint
**Est:** M (4-6h)
**상태:** ⏳ 대기 (트리거 미도래) — metrics.py 는 실재하나 \_v2*\* finance 헬퍼 12개가 여전히 v2_adapter.py(1239줄) L935-1167 에 남아 있어 이동 미완. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** `2026-06-30-backtest-deepen.md` (codex DOWNGRADE → `metrics.py` 부재 직접 검증 후 KEEP 정정)

**원인 / 영향:** `v2_adapter.py` 의 본 책임은 V2RunResult → BacktestOutcome 변환(orchestration)인데, Sharpe/MaxDD/CAGR/win-rate/streak/monthly 등 도메인-비종속 finance math 함수가 같은 모듈에 혼재 = shallow-by-size, Locality 깨짐. stress_test 재사용은 speculative(현재 `result.metrics` 만 소비)라 추출 정당화는 locality 중심.

**★전제 정정 (2026-08-03 실측, backtest-metric-oracle):** 본 항목이 전제한 「`engine/metrics.py` 부재」는 **낡았다** — 그 파일은 2026-07-26 backtest-trust 스프린트 이후 실재하며 현재 343줄(`sharpe_ratio`/`sortino_ratio`/`calmar_ratio`/`compute_excursion_stats`/`compute_side_metrics` 등 12 함수)이다. 남은 이동 대상은 `v2_adapter.py` 의 `_v2_*` 헬퍼 블록이고 위치도 바뀌었다 — 등재 당시 인용 `L707-912 / 964L` 은 stale, 현재는 **1211줄 중 L907-1162**. 레포 전체 grep 결과 그 헬퍼 12개를 `src/` 안에서 import 하는 곳은 **0건**이라 순수 move 가 안전하다(테스트 2파일만 직접 import).

**권장 접근:** 남은 finance 계산을 기존 `engine/metrics.py` 로 이동 — '(equity_curve, trades, config) → 지표 묶음' 작은 Interface 뒤에 큰 behavior 은닉. v2_adapter 는 호출만 남김. 이동(move)이라 golden oracle parity 로 회귀 0 보장.

**영향 파일:** `engine/v2_adapter.py`(L907-1162 추출), 기존 `engine/metrics.py`.

**Risk:** 🟢 (move refactor — `test_golden_oracle_minimal` + `test_metrics_real_extract` parity 가드, 이동 전후 동일 oracle 재실행).

---

### BL-390

**Title:** backtest exit-leg maker/taker `fill_type` 라우팅이 v2_adapter 2곳 char-identical 복제 (주석은 SSOT 주장)
**Category:** Backtest / Architecture (DRY / locality, money-path)
**Priority:** P3
**Trigger:** backtest deepening 또는 `exit_kind` 의미 변경 시
**Est:** XS-S (1-3h)
**상태:** ⏳ 대기 (트리거 미도래) — 라우팅 삼항식이 v2_adapter :354/:838 에 여전히 char-identical 복제 — 헬퍼 위임 없음(줄번호만 265/568→354/838로 이동). (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** `2026-06-30-backtest-deepen.md`

**원인 / 영향:** exit leg maker/taker 분기 `fill_type_for(t.exit_kind) if t.exit_kind is not None else "taker"` 가 `v2_adapter.py:265`(\_build_raw_trades)와 `:568`(\_compute_metrics)에 character-identical 복제. L549 주석은 'SSOT 위임으로 중복 제거' 라 주장하나 실제 SSOT 는 `_leg_cost` 뿐이고 routing 분기는 미위임 → `exit_kind` 의미 변경 시 2곳 동시 수정(money-path 수수료/슬리피지). 작지만 확정된 Locality 결함.

**권장 접근:** `fill_type` 라우팅을 단일 헬퍼(또는 RawTrade 메서드)로 위임 → 두 소비 사이트가 같은 한 곳을 호출. 주석의 SSOT 주장과 코드 일치.

**영향 파일:** `engine/v2_adapter.py` (:265, :568).

**Risk:** 🟢 (refactor-safe — `test_exit_leg_cost_split` C14 불변식이 발산 가드).

---

### BL-367

**Title:** `_async_dispatch_event` 205 LOC + 8× `mark_failed+commit+metric` 반복 블록 추출
**Category:** Trading / Architecture (shallow-by-size)
**Priority:** P3
**Trigger:** trading deepening sprint (clean win, 단독 가치 낮음)
**Est:** XS-S (1-2h)
**상태:** ⏳ 대기 (트리거 미도래) — \_async_dispatch_event(:4217~4472, 약 255 LOC)이 그대로 있고 mark_failed+commit+metric 반복이 9회, 추출 헬퍼는 부재. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** `2026-06-26-trading-deepen-2.md`

**현 상태:** `tasks/live_signal.py` `_async_dispatch_event`(:572-776, 205 LOC, nesting 4-5) 안에 `await event_repo.mark_failed(...) + commit() + qb_live_signal_dispatch_total.labels(...).inc() + return/raise` 패턴이 8회 반복(session_inactive / strategy_missing / invalid_settings / settings_unset / rejected / kill_switched / NotionalExceeded계열 / idempotency_conflict).

**권장 접근:** `_mark_failed_and_return(event_id, error, action, outcome, repo) -> dict` + `_mark_failed_and_raise(...)` 추출 → 함수 길이/중첩 감소. 단일 파일, 저위험 clean win.

**영향 파일:** `tasks/live_signal.py`.

**Risk:** 🟢 (단일 파일, 동작 불변).

---

### BL-370

**Title:** exit-field multi-SSOT — 8 필드 × OrderSubmit/Order/OrderRequest 평행 재정의
**Category:** Trading / Architecture (locality / distributed schema)
**Priority:** P3
**Trigger:** exit-field 추가 시 3곳 동시 수정이 부담될 때 (현재는 견딜 만함)
**Est:** S-M (3-5h)
**상태:** ⏳ 대기 (트리거 미도래) — OrderSubmit/Order/OrderRequest 3곳 exit-field 평행 정의가 그대로 살아 있고 ExitFields mixin 은 레포 전역 0건 — Trigger 도 미도래. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** `2026-06-26-trading-deepen-2.md`

**현 상태:** `reduce_only`/`trigger_price`/`trigger_by`/`take_profit`/`stop_loss`/`trigger_direction`/`oco_group_id`/`trailing_stop` 8 필드가 `OrderSubmit`(dataclass, providers.py:67-83) / `Order`(SQLModel, models.py:193-218) / `OrderRequest`(pydantic, schemas.py:60-71) 3 boundary type 에 동일 타입·주석으로 재정의 (+ LiveSignalEvent subset). 필드 추가 시 3곳 동시 수정.

**권장 접근:** `ExitFields` mixin/base 추출 검토 — **단 3 base(dataclass/SQLModel/pydantic)를 가로지르는 mixin 은 awkward → over-abstraction 함정 주의.** ROI 낮으면 보류. 등재 = 가시성 확보용.

**영향 파일:** `providers.py` / `models.py` / `schemas.py`.

**Risk:** 🟡 (3 base 가로지르는 추상화 — 잘못하면 복잡도 증가).

---

### BL-394

**Title:** BE 거래 분포/수익구조 집계 엔드포인트 — `useAllBacktestTrades` 2000-cap 페이지 루프 대체
**Category:** Backtest / API + Frontend
**Priority:** P3
**Trigger:** 2000+ trades 백테스트가 흔해질 때
**Est:** M (4-6h)
**상태:** ⏳ 대기 (트리거 미도래) — BE 집계 엔드포인트가 없어 FE 가 2000건 cap 으로 전량을 끌어온다 — 단 페이지 fetch 는 이미 병렬이라 남은 것은 cap 과 전송량뿐 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-05 TV-parity sprint F1/F3 (FE 파생 분포·waterfall 은 표본 근사 캡션으로 정직 고지 중)

**원인 / 영향:** 수익 분포 histogram/거래 분포 donut/수익 구조 waterfall 이 FE 에서 전체 trades(최대 2000, 페이지 루프 10회)로 파생. 초과 시 "표본 기준" 근사. BE 집계 1 endpoint 면 정확+경량. **참고:** BE `gross_profit_abs`/`gross_loss_abs`/`per_side.*` 는 net(비용 차감 후) 기준 승/패 분해 — waterfall 용 비용 전(gross) 분해와 다름(FE `computeProfitStructure` 항등식 참조). 집계 endpoint 설계 시 두 정의 모두 제공 권장.

---

### BL-395

**Title:** lightweight-charts v5 업그레이드 spike — 네이티브 멀티-pane + 시간축 동기화
**Category:** Frontend / 차트 인프라
**Priority:** P3
**Trigger:** 차트 pane 4개+ 필요 또는 줌/팬 동기화 요구 시
**Est:** M (6-8h, spike)
**상태:** ⏳ 대기 (트리거 미도래) — 여전히 lightweight-charts ^4.2.0 이고, 차트는 createChart 2회 호출로 독립 인스턴스를 쌓는다 — v5 네이티브 pane 미도입. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(사용자 결정·요청). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-05 TV-parity sprint F2 (v4.2 는 멀티-pane API 부재 → 독립 인스턴스 3개 스택, 시간축 미동기화)

---

### BL-396

**Title:** `/backtests/[id]/trades` 상세 서브페이지에 TV 신규 컬럼(런업/드로다운/누적/fee split/exit_kind) 정렬
**Category:** Frontend UX
**Priority:** P3
**Trigger:** 원장(trade-ledger-table)과 서브페이지 컬럼 비정합 불편 접수 시
**Est:** S (2-3h)
**상태:** ⏳ 대기 (트리거 미도래) — 원장 CSV 는 cumulative_pnl·runup_abs·drawdown_abs·fee_paid·slippage_paid 를 내는데 서브페이지 상세는 손익·수익률·수수료 3종뿐 — 비정합 존속 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(사용자 결정·요청). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-05 TV-parity sprint F4 (원장만 신규 컬럼 반영, 서브페이지는 무변경)

---

### BL-399

**Title:** `ta.sar` TV hand-oracle 부재 — parity 스팟 검증 미완
**Category:** Strategy / pine_v2 (indicator parity)
**Priority:** P3
**Trigger:** SAR 사용 전략 등장 시
**Est:** S-M (3-5h — AF/EP/flip 규칙 손유도)
**상태:** ⏳ 대기 (트리거 미도래) — SAR 구현·단위테스트는 있으나 전부 성질 검사뿐 — TV 손유도 오라클 값 대조는 코드·문서 어디에도 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-05 TV-parity sprint P1-4 (wma/bb/mom/obv/cross 는 스팟 판정 완료 — bb=population stdev=TV biased 기본 ✓, mom/obv/cross ✓. sar 만 오라클 미작성)

---

### BL-400

**Title:** optimizer 쿼리만 `enabled: userId != null` 가드 — 도메인 간 React Query enabled 정책 비일관 (통일 여부 결정 필요)
**Category:** Frontend / React Query 컨벤션
**Priority:** P3
**Trigger:** FE 훅 팩토리 후속 정비 시 (`use-auth-ctx` 소비 도메인 전수)
**Est:** S (2-3h — 정책 결정 + 일괄 적용)
**상태:** ⏳ 대기 (트리거 미도래) — 사용자 결정 대기: optimizer만 enabled: userId != null 유지, 타 도메인은 여전히 무가드 발사 — (a)통일 vs (b)제거는 사용자 정책 결정이 선행 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-05 PR #394 FE 리팩토링 번들 (훅 팩토리 SSOT 작업 중 발견, 2026-07-05 코드 재검증)

**원인 / 영향:** `features/optimizer/hooks.ts:59,70` 만 `enabled: userId != null` 로 로그아웃 시 쿼리를 미발사한다. 나머지 도메인(backtest/strategy/trading/live-sessions/waitlist) list 훅은 가드 없이 `useAuthCtx` 의 `uid="anon"` sentinel + null token 으로 발사(401 → retry 1). PR #394 훅 팩토리(`use-auth-ctx`/`use-invalidating-mutation`/`query-poll`)는 폴링 가드만 SSOT 화했고 enabled 가드는 미흡수. 실버그는 아니나 로그아웃 시 도메인별 동작이 달라 디버깅·테스트 기대가 갈린다.

**권장 접근:** 결정 사안 — (a) 전 도메인 `enabled: userId != null` 통일(무의미 401 제거, `use-auth-ctx` 에 헬퍼 추가) vs (b) optimizer 가드 제거로 "anon 발사" 일원화. Grilling 1문항으로 결정 후 일괄 적용.

**Risk:** 🟢 (정책 결정 사안 — 어느 쪽도 회귀 표면 작음).

---

### BL-403

**Title:** recharts↔lightweight-charts(+optimizer inline-SVG) 차트 3원화 해소 — 라이브러리 수렴 결정
**Category:** Frontend / 차트 인프라
**Priority:** P3
**Trigger:** **BL-395(lwc v5 spike) 완료 후** — 멀티-pane/커스텀 시리즈 확보가 수렴 가능성 판정의 전제
**Est:** L (8-16h — 대상 플롯별 이식 난도 상이, spike 선행)
**상태:** ⏳ 대기 (트리거 미도래) — 3원화 대상 3계열(파일·의존성)이 전부 그대로 있고 선행 BL-395(lwc v5) 도 미완이라 Trigger 자체가 미도래. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 선행 BL-395=ACTIVE (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-05 PR #394 FE 리팩토링 번들 (차트 지연로딩 정리 중 3원화 실측)

**원인 / 영향:** 시계열=lightweight-charts(`trading-chart.tsx` 싱글턴 dynamic import + backtest equity/drawdown pane + live-sessions), 통계 플롯=recharts 5종(`charts/recharts-plots.ts` 단일 seam, 414KB), optimizer 2종(`genetic-generation-chart.tsx`/`bayesian-iteration-chart.tsx`)=recharts 의존 회피 목적의 손수 inline SVG — 사실상 3원화. 번들 이중 부담 + 스타일 토큰(`lib/chart-tokens.ts` 로 완충 중) 3중 유지보수 + 신규 차트마다 라이브러리 선택 부채. Sprint 30-β 결정("recharts 보존, 신규만 lwc")이 3원화로 표류했다.

**권장 접근:** BL-395 spike 결과로 lwc v5 가 histogram/donut/waterfall 급 통계 플롯을 감당하는지 판정 → (a) lwc 수렴 + recharts 제거 (b) recharts 유지 + inline-SVG 2종만 recharts 편입 (c) 현상 유지 재확인 중 택1. BL-235(N-dim viz — cross-page consistency 의무)와 라이브러리 결정 공유.

**영향 파일:** `charts/recharts-plots.ts` 계열 5플롯, `components/charts/trading-chart.tsx`, optimizer inline-SVG 2종, `lib/chart-tokens.ts`.

**Risk:** 🟡 (표면 넓음 — spike 선행 + 페이지별 스냅샷 회귀 필요).

---

### BL-406

**Title:** DrFXGOD 잔여 미지원 builtin 5종 — ta.alma / ta.dmi / time() 호출형 / ticker.new / request.security_lower_tf
**Category:** Backend / pine_v2 coverage
**Priority:** P3
**Trigger:** 사용자 DrFXGOD 류 대형 indicator 수요 재확인 시
**Est:** M (ta.alma/ta.dmi 각 2-3h + time() stub 1h) / ticker.new·security_lower_tf 는 별도 설계 필요
**상태:** ⏳ 대기 (트리거 미도래) — ta.alma/ta.dmi 는 TA_FUNCTIONS 에 없고 coverage 가 여전히 미지원 안내만 한다 — time 은 식별자만, 호출형 stub 없음 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(사용자 결정·요청). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-12 pine-batch QA (`docs/archive/qa/2026-07-12-pine-batch-1h4h/report.md` §2)

**원인 / 영향:** G2(array 15종) 이후 DrFXGOD_indicator_hard(=i3_drfx) 의 잔여 차단 표면. (a) `ta.alma`(Arnaud Legoux MA)·`ta.dmi`(DMI/ADX) 는 순수 지표 — stdlib 추가로 feasible. (b) `time("")` 호출형은 timestamp stub 확장으로 feasible. (c) `ticker.new` + `request.security_lower_tf` 는 멀티심볼·하위 TF 데이터 패러다임 — 단일 TF 백테스트 전제 밖(거부 유지가 정직). (a)+(b) 만 구현해도 DrFXGOD 는 (c) 로 여전히 차단 — **전체 지원 목표가 아니라 (a)(b) 의 범용 가치로 판단할 것**.

**권장 접근:** ta.alma/ta.dmi 를 `_names.TA_FUNCTIONS` + stdlib `_call` 에 추가 (BL-378 ta.atr Wilder 검증 프로토콜 재사용 — TV 문서 대조 + 수계산 오라클). time() 은 bar timestamp 반환 stub. (c) 는 workaround 텍스트 유지.

**Risk:** 🟢 (신규 함수 추가 — 기존 경로 무변경).

---

### BL-408

**Title:** 리포트/위저드 Precision Instrument 폴리시 잔여물 팩 (stale aria-label 색명 + radius/글래스/레이블 어휘 6건)
**Category:** Frontend / 디자인 시스템 정합
**Priority:** P3
**Trigger:** 다음 FE polish 사이클 (BL-402 처리와 묶음 권장 — 파일 겹침)
**Est:** S (2-3h — 전부 표시 전용)
**상태:** ⏳ 대기 (트리거 미도래) — 6건 중 1~5 (색명·radius·글래스·레이블·mono)는 v3 재작성으로 소멸했으나 6번 --destructive-light 중복 alias(=subtle 동일값, 사용처 6곳)와 영문 aria-label 다수가 남았다 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-12 pine-batch QA 디자인 감사 (`docs/archive/qa/2026-07-12-pine-batch-1h4h/report.md` §6.1)

**원인 / 영향:** W6 잔여물 + 리디자인 이후 미세 드리프트 묶음. (1) `charts/chart-legend.tsx:51`·`charts/equity-pane.tsx:78` aria-label "실선 녹색" — 실제 equity 색은 코퍼, 스크린리더에 틀린 색 전달 (P2급, 팩 내 최우선. E2E getByLabelText 2건 동반 수정). (2) `report/key-stats-strip.tsx:83`·`report/performance-chart.tsx:42` 히어로 카드 `rounded-xl`(14px) — DESIGN.md §5 카드 규격은 10px. (3) `charts/chart-legend.tsx:44` `bg-card/80 backdrop-blur` 글래스 잔존 — v3 플랫+1px 보더 원칙 위반 (스코프 내 유일). (4) `components/metric-tile.tsx:60` 레이블 sans 10px — §0.1 mono 11px tracking 0.14em 규격과 분열. (5) `report/trade-ledger-table.tsx` 금액 셀 mono/tabular 혼용. (6) `--destructive-light` alias 잔존 + 영문 aria-label("strategy select" 등). DESIGN.md §11 표의 "백테스트 결과 = Light" 는 v2 스냅샷 잔재 — 문서 정리 동반.

**권장 접근:** 항목별 1-line 수정 (전부 표시/문서 전용, 로직 무변경). BL-402 SelectWithDisplayName 교체 PR 에 동승 가능.

**Risk:** 🟢 (표시 전용 — 시각 스냅샷 확인만).

---

### BL-409

**Title:** pine_v2 워밍업 TV-parity 잔여 2건 — (a) ta.ema 시딩 정합 (bs bar12↔bar15 실측 편차 진짜 후보) (b) bool[n] 범위밖 과거참조 nan vs TV false
**Category:** Backend / pine_v2 warmup parity
**Priority:** P3
**Trigger:** 다음 pine_v2 TV-parity 사이클 (BL-405 재분류 후속) — 특히 (a)는 실제 TradingView 그라운드트루스 확보 시
**Est:** M ((a) ta.ema 시딩 조사 2-4h — 단 확정엔 실제 TV 실행 대조 필요 / (b) XS, 관측 무영향이라 저순위)
**상태:** ⏳ 대기 (트리거 미도래) — 사용자 결정 대기: (a) ta.ema 시딩은 여전히 SMA seed 그대로라 실제 TV 관측 없이는 대조 불가(순환검증), (b)는 nan 반환 그대로지만 관측 무영향. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-12 A+B+C Trust 번들 — BL-405 재분류 과정에서 TV 문서 검증 + 회귀 테스트(`test_na_bool_tv_parity.py`)로 표면화

**원인 / 영향:**

- **(a) ta.ema 워밍업 시딩** — 엔진 `ta_ema`(stdlib.py:81-97)는 첫 `length-1` bar 를 nan 으로 두고 bar `length-1` 에서 SMA 로 시드. 실제 TradingView 의 ta.ema 워밍업 시작 bar/값이 다르면 emaSlow 가 다른 bar 에서 살아나 `bull != bull[1]` 첫 전환이 다른 bar 로 이동한다. **bs 4h 2024 의 엔진 bar 12 vs 오라클 주장 bar 15 편차의 진짜 후보** (bool-na 와 무관). 확정하려면 실제 TradingView 에서 bs 4h 2024 의 첫 시그널 bar + ta.ema(5)/ta.ema(13) 초기 시리즈를 관측해 엔진과 대조해야 함 (순수 pandas 오라클이 엔진과 같은 시딩을 가정하면 순환검증 — §7.3).
- **(b) bool[n] 범위밖 과거참조** — `_eval_subscript`(interpreter.py:882-884)가 범위밖 history 를 타입 무관 nan 반환. bool 변수의 `b[1]` 이 bar 0 에서 nan (TV 는 false). 소비(비교/제어흐름)에서 `_truthy`/비교가 nan→false 로 소거 → **거래·시그널 영향 0** (test_na_bool_tv_parity.py 가 관측 등가 잠금). raw 저장 값만 편차.

**권장 접근:** (a) 실제 TV ta.ema 초기 시리즈 캡처 → 엔진 시딩 규칙 대조/조정 (BL-378 ta.atr Wilder 검증 프로토콜 재사용 — TV 문서/실행 대조 + 수계산 오라클). (b) 관측 등가라 저순위 — 정적 bool 타입 추론 도입 시 함께 (pine_v2 동적 타입이라 난이도 있음).

**Risk:** 🟢 ((a) 조사 우선; (b) 관측 무영향).

---

### BL-463

**Title:** optimizer / stress_test 저장 sharpe 에 컨벤션 마커 없음
**Category:** Optimizer / Stress test (metrics 정합)
**Priority:** P3
**Trigger:** 구 optimizer·stress 결과 재해석 필요 시
**Est:** M (2 도메인 JSONB 스키마 확장)
**상태:** ⏳ 대기 (트리거 미도래) — sharpe_convention 마커는 backtest 계열에만 존재하고 optimizer/stress_test JSONB 는 여전히 순수 sharpe 값만 저장한다 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-26 backtest-trust 스프린트 (codex G0 P2 지적 → 스코프 밖 수용)

**원인 / 영향:** `optimizer/serializers.py:104` 와 `stress_test/serializers.py:80,159` 가 각자 독립 JSONB 에 sharpe 를 저장한다. 본 스프린트는 **backtest metrics 만** 마킹했으므로 두 도메인의 과거 결과는 구·신 구분 없이 남는다. 신규 실행은 새 수식이지만 저장값에 그 사실이 기록되지 않는다.

**권장 접근:** 두 도메인 result JSONB 에도 컨벤션 마커 추가 + FE 표기. 3 도메인 동시 마킹은 스코프 폭발이라 분리했다.

**Risk:** 🟢 (신규 실행은 일관 · 구 결과 비교 시에만 오해 가능).

---

### BL-505

**Title:** 청산 공유 lock 의 축이 포지션 정체성이 아니라 `sessionId + symbol` 이다
**Category:** Frontend / trading (코크핏 §03)
**Priority:** P3
**Trigger:** 같은 계정·심볼에 세션이 여러 개 생긴 뒤 두 표에서 연달아 청산을 누를 때
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — mutationKey 가 여전히 ["close-position", sessionId, symbol] 이고 두 표 테스트도 같은 sessionId 를 주입한다 — 포지션 정체성 축 전환 흔적 없음 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-ops-hygiene codex 최종 적대 리뷰 (재현 판정 후 등재)

**원인 / 영향:** BL-502 의 `mutationKey` 는 `["close-position", sessionId, symbol]` 이다. 그런데 두 표가 같은 포지션에 대해 **서로 다른 `sessionId` 를 잡을 수 있다** — 계정 표는 그 계정·심볼의 **최신** 귀속 세션(비활성 포함, `position_service.py:283`)을 쓰고, 세션 표는 **활성** 세션별로 렌더한다. 최신 세션이 비활성이고 더 오래된 세션이 활성이면 두 키가 갈리고 lock 이 분리된다 → 같은 순 포지션에 감소전용 주문 2개가 나갈 수 있다(BL-502 가 없애려던 바로 그 상태).

★**추가된 테스트도 이 경로를 판별하지 못한다** — `close-position-lock.test.tsx` 가 두 표에 **같은** `SESSION_ID` 를 주입한다. 정렬된 경우만 덮는다.

**권장 접근:** lock 축을 세션이 아니라 **포지션 정체성**(계정 또는 uid + 심볼 + 방향)으로 바꾼다. 다만 `close_position` API 가 세션 id 를 받으므로 키와 요청 인자가 갈라진다 — 그 분리를 감당할지 결정이 필요하다. 손실이 아니라 **원장 잡음**(두 번째 주문은 평탄해진 포지션에서 거부)이라 우선순위는 낮다.

**영향 파일:** `apps/web/src/features/live-sessions/hooks.ts`, `.../account-positions-table.tsx`, `.../open-positions-table.tsx`.

**Risk:** 🟢

---

### BL-507

**Title:** 계정 표의 접기·청산 가능성 판정이 view 컴포넌트 안에 있다
**Category:** Frontend / trading (레이어)
**Priority:** P3
**Trigger:** 접기 규칙이 한 번 더 바뀔 때
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — features 분리 미실시. 단 :56 은 이미 모듈 레벨이라 분리는 성능을 안 바꾼다 — 실비용은 :248-301 조립·호출이 useMemo 밖인 것 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-ops-hygiene codex 최종 적대 리뷰

**원인 / 영향:** `collapseRows`(`account-positions-table.tsx`)가 권한(`readOnly`)·귀속 세션·차단 사유를 해석해 대표 행과 청산 가능성을 결정한다. `apps/web/AGENTS.md` 의 view ↔ 비즈니스 로직 분리 원칙 위반이다.

★**이번 스프린트의 P1 이 정확히 이 경계에서 나왔다** — hedge 의 두 leg 를 한 행으로 지운 것이 이 함수였다. 규칙 위반이 실제 결함으로 이어진 사례이므로 nit 로만 두지 않는다.

**권장 접근:** 접기·대표 선택을 순수 함수로 분리해 단독 테스트 가능하게 하거나, 서버가 접힌 형태를 계산해 내려준다. 후자는 uid 가 계정 목록 계약에 이미 있으므로 가능하지만 **응답 계약 변경**이라 결정이 필요하다.

**Risk:** 🟢

---

### BL-509

**Title:** multiprocess mmap 파일이 무한히 쌓이고, 그 누수가 `qb_active_orders` 의 정확성을 떠받치고 있다
**Category:** Infra / observability
**Priority:** P3
**Trigger:** 스크레이프 지연이 눈에 띌 때, 또는 장기 무중단 가동 시
**Est:** M
**상태:** ⏳ 대기 (트리거 미도래) — role별 dead-pid 접기 janitor(merge accumulate=False)가 코드·테스트 어디에도 없고, 있는 것은 콜드 스타트 wipe 뿐이다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-observability 적대 검증(프로세스 경계 렌즈)

**원인 / 영향:** `mark_process_dead` 는 `gauge_live*` 파일만 지운다. `counter_`/`histogram_`/`gauge_sum_`/`gauge_mostrecent_` 는 **아무도 지우지 않는다**. `worker_max_tasks_per_child=250` 자식 교체마다 +4 파일, `uvicorn --reload`/watchfiles 재기동도 각각 새 식별자다. 수집기는 매 스크레이프마다 전 파일을 re-mmap + 키마다 `json.loads` 하므로 비용이 **O(F×K)** 다.

★**soak 실측 — 아직 문제로 관측되지는 않았다.** 약 1시간 창에서 파일 50 → 54(자식 1회 재활용), `scrape_seconds` 는 **24샘플 전부 0.01 고정**. 즉 이 태스크 부하에서는 열화가 나타나지 않았다. 원리상 실재하되 **긴급하지 않다.**

★★**함정: 순진하게 고치면 BL-508 이 즉시 깨진다.** 죽은 자식의 **음수 delta 파일이 남아 있어야** `sum` gauge 산술이 맞는다. 회수 janitor 를 만들 때 `multiprocess.merge(files, accumulate=False)` 로 role 별 집계 파일에 **접고** 삭제하는 형태여야 한다.

**권장 접근:** 콜드 스타트 wipe(현행) 유지 + role 별 dead-pid 접기 janitor. 런타임 중 counter 파일 pruning 은 **가짜 counter reset** 이므로 금지.
**Risk:** 🟢

---

### BL-513

**Title:** 성공은 안 보이고 실패만 보인다 — 완전체결 카운터 부재 · janitor 실적 미노출 · planner divergence 5종 무계측
**Category:** Backend / observability (trading)
**Priority:** P3
**Trigger:** 운영 대시보드를 만들 때
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — 3종 처방 중 divergence 계측만 구현(BL-536), janitor 실적·완전체결 카운터는 여전히 부재. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-observability 적대 검증(거래소 실상 렌즈)

**원인 / 영향:**

- **완전체결을 세는 카운터가 코드베이스에 없다.** `qb_partial_fill_total{source}` 는 **부분체결 전용**이다. 체결 시 일어나는 건 `qb_active_orders.dec()` 뿐이라 "몇 건 체결됐나" 를 물을 수 없다.
- **janitor 실적이 Prometheus 에 없다.** `conditional_entry_janitor.py:168` 이 `{repaired, rejected, terminal}` 를 **return 만** 한다. 오류 stage(`janitor_race`/`janitor_probe`)만 계측된다. soak 실측에서 janitor 는 5분마다 정상 발화하며 전부 0 을 반환했는데, **그 사실이 Celery 결과 로그에만 있다.**
- **planner divergence 5종 전량 무계측** — `conditional_entry_planner.py:172/195/216/240/255` → 소비처는 `live_signal.py:499-503` `logger.warning` 뿐. 특히 `below_exchange_minimum` 은 "전략이 영원히 한 주도 못 낸다" 는 뜻인데 무계측이다.

**권장 접근:** `qb_order_filled_total{source}`, `qb_conditional_janitor_actions_total{action}`, `qb_conditional_plan_divergence_total{reason}` 신설.
**Risk:** 🟢

---

### BL-515

**Title:** 정상 교체 사이클이 이상 판별을 삼킨다 + 경보 규칙이 2개뿐이라 카운터가 올라도 아무도 안 본다
**Category:** Infra / observability
**Priority:** P3
**Trigger:** metric 기반 운영 경보 도입 시
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — alerts.yml 은 여전히 alert 2개뿐이고 placed−cancelled recording rule 은 레포 어디에도 없다(record: 0건). (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-observability 적대 검증

**원인 / 영향:** PbR 같은 전략은 매 bar 피벗이 움직여 `conditional_entry_planner.py:285-289` 가 항상 불일치 → **매 tick** `cancelled_total{reason="replaced"}` +1 · `placed_total` +1 이 정상이다. 병리(거절 루프)도 **같은 패턴**이라 두 카운터로는 구분할 수 없다. 유일한 신호는 `placed − cancelled` 의 발산인데 recording rule 이 없다.

그리고 `apps/api/prometheus/alerts.yml` 에 rule 이 **2개뿐**(`QbPendingAlertsHigh`, `QbRedisLockPoolUnhealthy`). 이번 세션이 관측 가능하게 만든 어떤 카운터도 경보에 연결돼 있지 않다.

★**단, BL-506 이전에는 이 논의 자체가 불가능했다** — 그 카운터들이 스크레이프되지 않았기 때문이다.

**권장 접근:** `placed − cancelled` recording rule + 이번 세션 판정표의 "관측됨" 계열에 대한 경보 규칙.
**Risk:** 🟢

---

### BL-518

**Title:** multiprocess 모드의 관측 계약 변화 — `_created` 전면 소실 · 프로덕션 경로 미테스트 · 값 범위 변화
**Category:** Infra / observability
**Priority:** P3
**Trigger:** `/metrics` 소비자(대시보드·경보)를 만들 때
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — 4건 중 1건만 BL-448 로 소멸했고, 관측 계약 문서화도 multiproc /metrics HTTP 테스트도 레포에 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-observability 적대 검증(관측 계약 렌즈) + 실측

**원인 / 영향:**

- ★**`_created` 시리즈 전면 소실.** 실측 — 미배선 API **30줄** → 배선 API **0줄**. `prometheus_client` 의 `_created` 는 `ValueClass` 를 거치지 않는 순수 float 이라 mmap 에 실리지 않는다. `rate()` 는 무영향이나 `_created` 기반 쿼리는 깨진다. **multiprocess 모드의 내재적 성질**이지 우리 버그가 아니다.
- **프로덕션 경로가 테스트되지 않는다.** 테스트 env 에 `PROMETHEUS_MULTIPROC_DIR` 이 없어 전 스위트가 폴백을 탄다. **`/metrics` HTTP 를 multiproc 모드로 때리는 테스트가 0건**이다(신규 테스트도 `render_metrics()` 단위까지).
- ~~**`qb_ws_orphan_buffer_size` 값 범위 변화.** docstring 은 "capped at 1000" 인데 `concurrency=3` + `livesum` 이라 0~3000. 기존 임계 재조정 필요.~~ → **2026-08-09 무효 — 그 gauge 는 [BL-448](#bl-448) 에서 삭제됐다**(버퍼째 제거). 이 항목이 재던 「livesum × concurrency 로 범위가 배수가 된다」는 성질 자체는 남은 `livesum` gauge(`qb_pending_alerts`)에 그대로 유효하다.
- **`qb_redis_lock_pool_healthy` 가 fail-open.** `mostrecent` 는 죽은 프로세스가 남긴 `1` 을 계속 서빙한다 — 건강한 프로세스가 없어도 healthy=1. `livemostrecent`/`min` 이 후보이나 각각 다른 실패 모드가 있다.

**권장 접근:** 위 4건을 `docs/reference/` 관측 계약 문서에 명시 + multiproc 모드 endpoint 테스트 추가.
**Risk:** 🟢

---

### BL-521

**Title:** `qb_live_signal_outbox_pending_gauge` 를 두 곳이 서로 다른 상한으로 덮어써 경보 신호가 잘린다
**Category:** Backend / observability
**Priority:** P3
**Trigger:** outbox 적체 경보를 붙일 때
**Est:** XS
**상태:** ⏳ 대기 (트리거 미도래) — limit=10_000 과 limit=50 두 .set() 이 그대로 공존하고 gauge 에 라벨도 없다 — 처방 미적용. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-observability G1 codex 적대 검증, 코드 재현 완료

**원인 / 영향:** `live_signal.py:813` 은 `list_pending(limit=10_000)` 결과를 `.set()` 하고, `:1475` 는 `list_pending(limit=50)` 결과를 같은 gauge 에 `.set()` 한다. **마지막 writer 가 이긴다.** 실제 pending 이 50 을 넘으면 recovery task 가 **50 으로 덮어써** 적체 신호가 조용히 잘린다.

★**단일 프로세스에서도 이미 그런 선재 결함**이다 — BL-506 이 만든 것이 아니다.

**권장 접근:** recovery task 의 `.set()` 을 제거하거나(문서상 계약은 "last eval cycle"), 두 소스를 라벨로 가른다.
**Risk:** 🟢

## Cross-reference

### BL-410

**Title:** FE vercel-react-best-practices 감사 low 잔여 팩 (확정 8건 — 배럴 2 + localStorage 스키마 2 + js 최적화 3 + fitContent 설계 1)
**Category:** Frontend / 성능·컨벤션
**Priority:** P3
**Trigger:** 다음 FE polish 사이클 (BL-408 과 묶음 가능)
**Est:** S (2-4h — 전부 국소)
**상태:** ⏳ 대기 (트리거 미도래) — 8건 중 draft.ts version 스키마 1건만 구현, 배럴 2·webhook version·js 최적화 3·fitContent 설계 모두 코드에 그대로 남아 있다 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 선행 BL-408=ACTIVE (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-13 vercel 70룰 멀티에이전트 감사 (파인더 6 + 반박형 검증, 원시 24 → 확정 18 중 high/medium 10건은 stage/fe-react-audit PR #433 에서 해소 — 본 팩은 low 8건)

**원인 / 영향:** (1) `components/ui/form.tsx:6` + `features/trading/index.ts:3` 배럴 import. (2) `features/strategy/webhook-secret-storage.ts:53` + `draft.ts:89` localStorage 버전 스키마 부재. (3) `features/backtest/utils.ts:218` 함수 결과 캐시 부재 + `equity-chart-v2.tsx:184` / `trade-stats-strip.tsx:113` filter/map 다중 순회. (4) `components/charts/trading-chart.tsx:300` data effect 의 `fitContent()` 가 매 sync 마다 실행되는 설계 — 근본 수정(최초 1회 제한)은 전 호출처 동작 변경이라 별도 검토 (PR #433 은 호출측 identity 안정화로 해소).

**권장 접근:** 항목별 1-line~소형 수정. (4)는 lightweight-charts v5 업그레이드 (BL-395) 와 함께 재검토.

**Risk:** 🟢.

---

### BL-412

**Title:** optimizer result read-side 판별 유니온 (C-full) — `OptimizationRunResponse.result: dict[str,Any]` 를 FE 동형 `OptimizationResultOut` 으로
**Category:** Optimizer / Arch (read-side 타입화)
**Priority:** P3
**Trigger:** optimizer 폼/리포트 다음 기능 사이클 (BL-235/236/364 중 아무거나 착수 시 동승 검토)
**Est:** M (+80~120 LOC, FE 동형 유지 의무)
**상태:** ⏳ 대기 (트리거 미도래) — read 응답은 여전히 result: dict[str,Any] 이고 \_to_response 가 raw jsonb 를 그대로 흘린다 — OptimizationResultOut 유니온 자체가 레포에 없다 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 선행 BL-235=ACTIVE (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-13 optimizer deepen 감사 후보 C-full (C-min 은 동일 세션 해소 — get/list 손상 row 방어 대칭화, PR feat/optimizer-cmin-n2)

**원인 / 영향:** BE 는 typed 역직렬화 역량(`*_from_jsonb`)을 갖고도 read 응답을 untyped dict 로 흘려 FE zod 가 유일한 검증층. writer 변경 시 drift 를 BE 테스트가 못 잡음 (BL-388/392 harm-class).

**권장 접근:** ADR-013 §7.2/§8.2 result grammar (실체 = `git show 94da86b1^:docs/dev-log/2026-05-12-sprint54-bayesian-genetic-grammar-adr.md` — [BL-504]) 를 정확히 mirror 하는 `OptimizationResultOut` 판별 유니온 추가 — 반드시 C-min 의 저하 경로(retro-incorrect row 404) 위에서 soft-validate. FE `schemas.ts` 와 필드 1:1 대조 테스트 동반.

**Risk:** 🟡 (구 row 실패율 상승 가능 — C-min 선행 완료로 완화됨).

---

### BL-415

**Title:** `.field-error` FieldError 컴포넌트 3사본 → 공용 컴포넌트 승격 + zod-v4-resolver 평탄 키의 per-field 재검증 stale 가능성
**Category:** Frontend / 폼 프리미티브
**Priority:** P3
**Trigger:** 다음 폼 터치 사이클 또는 4번째 사본 등장 시
**Est:** S (2-3h)
**상태:** ⏳ 대기 (트리거 미도래) — 공용 FieldError 승격 미실시(optimizer 로컬 정의 + raw .field-error 사본 다수), resolver 는 여전히 path.join(".") 평탄 키이고 재검증 테스트도 없다 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-23 BL-401 적대 평가 사소 지적 (waitlist/optimizer 2곳+@ 사본)

**원인 / 영향:** waitlist·optimizer 가 동일 FieldError 를 로컬 복제. 또 커스텀 resolver 가 평탄 키(`parameters.0.max`)로 에러를 만들면 RHF per-field 재검증(dotted-path unset)이 못 지워 제출 재시도까지 stale 에러가 남을 수 있음 (중첩 경로 폼 첫 소비 사례).

**권장 접근:** `components/` 공용 FieldError 승격 + resolver 평탄/중첩 키 정책 1개로 통일 + stale 재검증 재현 테스트.

---

### BL-420

**Title:** WS 인바운드 서버 하드닝 팩 — 비인증 소켓 글로벌 상한/rate-limit + auth→realtime 역참조 정리
**Category:** Backend / realtime 보안·아키텍처
**Priority:** P3
**Trigger:** Beta 공개 배포 전 또는 realtime 다음 터치 시
**Est:** S (2-4h)
**상태:** ⏳ 대기 (트리거 미도래) — pre-auth 글로벌 상한·rate-limit 코드가 전무하고 auth→realtime 역참조도 dependencies.py:13 에 그대로 남아 있다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(Beta·프로덕션 배포). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-24 tc-realtime-be 적대 평가 잔여 리스크 2건

**원인 / 영향:** accept 후 5s auth 창을 쥔 미인증 소켓의 동시 수 상한이 없음(per-user 상한은 인증 후에만 작동, Origin 은 비브라우저가 위조 가능 — 인증 자체는 별도라 보안 붕괴는 아님). 또 `src/auth/dependencies.py` 가 feature 도메인 `src.realtime.auth` 를 import 하는 방향 역전.

**권장 접근:** pre-auth 소켓 글로벌 상한/접속 rate-limit + helper 를 `src/auth/` 로 이동하고 realtime 이 역참조. (부수: position 서비스의 spot 방어 분기 dead code — `market_type` 키는 실경로 저장 불가 — 함께 정리.)

---

### BL-426

**Title:** ws_stream 워커 용량 정책 — 멀티계정 시 public ticker starvation 가능 + 스트림 태스크 루프 직접 유닛 부재
**Category:** Backend / trading websocket 인프라
**Priority:** P3
**Trigger:** 거래소 계정 2개 이상 등록 시 (현 로컬 1계정 무해) ★**2026-08-18 — 「멀티 거래소 확장」 묶음**(`roadmap.md` §권장착수순서 7): [BL-015]·BL-186b·[BL-756]·[BL-426] 넷이 「2번째 거래소를 붙인다」는 **하나의 사용자 결정**에 걸려 있다. 그 결정 전에는 단독 착수 시 값이 0이다
**Est:** S-M (2-6h)
**상태:** ⏳ 대기 (트리거 미도래) — public ticker 가 여전히 private 과 같은 ws_stream 큐(concurrency=3 고정) — 분리·계정수 산정·starvation 회귀 테스트 전무. lease 갱신 유닛만 존재. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-24 opspack-ws2 codex G0 + WA 적대평가 P3 관찰

**원인 / 영향:** reconcile 이 활성 계정마다 장기 private stream 을 enqueue 하는데 계정 수 상한이 없어, 계정 N+1 > concurrency(3) 이면 public ticker 태스크가 큐에서 기아. 또한 60s refresh/lease-lost 루프는 코드 정독+프로브로만 검증(직접 단위 테스트 없음).

**권장 접근:** singleton public ticker 를 별도 큐·concurrency 1 워커로 분리하거나 계정 수 기반 concurrency 산정 + starvation 회귀 테스트. refresh 루프 유닛 동반.

---

### BL-428

**Title:** 트레이드 구간 미니차트 share 페이지 미지원
**Category:** Frontend
**Priority:** P3
**Trigger:** 공개 share 리포트에 구간 차트 요구 시
**Est:** M (owner-authed OHLCV 엔드포인트를 token 기반 공개 경로로 확장)
**상태:** ⏳ 대기 (트리거 미도래) — owner-authed /trades/{i}/ohlcv 그대로이고 token 공개 OHLCV 경로도, share 페이지 trade 표도 없다 — 처방 미구현. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(사용자 결정·요청). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-24 perf-surface A4 (TradeDetailTable 은 owner-authed `/trades/{i}/ohlcv` 사용 → share 페이지는 미렌더가 정직. 현재 share 는 trade 표 자체가 없음)

**원인 / 영향:** 미니차트 fetch 는 owner-authed 엔드포인트라 share(token) 컨텍스트에서 401. 현재 share 페이지는 Stat 카드+EquitySparkline 만 있고 trade 표가 없어 무해하나, 향후 share 에 trade 상세 도입 시 차트 공백.

**권장 접근:** token 기반 공개 OHLCV 조회 경로(민감도 낮음 — 과거 시세) 또는 share 렌더 시 차트 명시적 비활성 + 안내.

---

### BL-437

**Title:** 청산 스윕 — 청산 후 잔여 reduce-only 조건부 주문 자동취소 (post-fill + 세션 귀속)
**Category:** Backend / trading
**Priority:** P3
**Trigger:** 수동 청산 후 잔여 조건부 주문(standalone SL/Trail 등 flat 시 자동취소되지 않는 것)이 dangling 으로 남아 재진입 시 오발화하는 실사례가 확인될 때
**Est:** M (post-fill flat 확인 mechanism + orderLinkId→세션 매핑)
**상태:** ⏳ 대기 (트리거 미도래) — 청산 후 잔여 조건부 주문 스윕 코드가 close_service 어디에도 없다; 계정 배타성만 갖춰졌고 post-fill flat 확인·세션 귀속 취소는 미구현. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-25 close-completeness (BL-434 분리 — codex G0 이 스윕에서 2 BLOCKING 발견해 이연)

**원인 / 영향:** BL-434 의 완전 보고(display)는 완료. 청산 스윕(잔여 reduce-only 조건부 주문 취소)은 codex G0 이 2 BLOCKING 을 드러내 이연: (1) **타이밍** — `execute()` 성공 = 주문 accept(async)이지 fill 이 아님. 발주 직후 스윕하면 시장가 청산 미체결 중 보호 주문부터 취소 = 머니-패스 위험. (2) **교차 세션** — 조회는 account+symbol 단위. 같은 계정·심볼 공유 타 세션의 보호 주문까지 방향만 맞으면 취소(스냅샷에 세션 귀속 식별자 없음). dogfood 실측 = 포지션-부착 Partial 조건부 TP/SL 은 Bybit 이 flat 시 자동취소하므로(close 후 orders count=0) 이연은 안전. 스윕은 truly-standalone dangling 주문에만 필요.

**권장 접근:** (a) post-fill flat 확인 후에만 스윕(재조회 후 flat 일 때만, 또는 fill 이벤트 훅) + (b) orderLinkId→Order→세션 매핑으로 이 세션이 건 조건부만 취소(account+symbol 단일-활성-세션 DB 제약이 없는 한). 그 매핑이 없으면 스윕 자체를 빼는 게 안전.

---

### BL-439

**Title:** 부분체결 후 `cancelled` 로 종료된 청산의 실체결 손익 누락
**Category:** Backend / trading (money path)
**Priority:** P3
**Trigger:** limit 청산 경로가 생기거나, 부분체결 상태에서 사용자 취소가 가능해질 때
**Est:** S (2-3h)
**상태:** ⏳ 대기 (트리거 미도래) — cancelled 승자 backfill 예약도, SUM 의 realized_pnl_synced_at 기준 확대도 미구현. limit 청산 매핑은 있으나 미배선이라 Trigger 미도래. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-25 money-path-accuracy (codex G0 BLOCKING 을 실측 반박한 뒤 남은 진짜 잔여)

**원인 / 영향:** closedPnl backfill 은 `state==filled` 인 reduce-only 주문만 대상으로 한다. 부분체결 뒤 `cancelled` 로 끝난 청산은 실제로 자금이 움직였는데도 `state==filled` 필터에 걸려 손익이 계상되지 않는다. **현재는 도달 불가** — 이 레포의 청산은 전부 `OrderType.market` 이고 Bybit 시장가 부분체결은 `PartiallyFilledCanceled` → ccxt `closed` → 우리 `filled` 로 매핑되기 때문이다. limit 청산이 도입되는 순간 활성화된다.

**권장 접근:** `transition_to_cancelled` 승자에서도 reduce-only 면 backfill 을 enqueue 하고, Kill Switch SUM 의 state 필터를 `realized_pnl_synced_at IS NOT NULL` 기준으로 넓힌다(단 생성 시점 엔진 추정값이 cancelled 행에 남아 있으면 오계상되므로 취소 시 null-out 이 선행돼야 한다).

---

### BL-440

**상태:** ⏳ **대기 (트리거 미도래)** — 본 섹션의 "Resolved" 문자열은 **BL-014 를 가리키는 cross-ref**(출처 줄)이고, 이 BL 자신(`order_executions` per-execution ledger)은 **YAGNI 로 미착수**다. 근거: 본 섹션 `**권장 접근:**` 줄("실제 분석 수요가 생기기 전에는 만들지 않는다") · `docs/roadmap.md:262` `- [ ] **BL-440**`.
**트리거 판정:** 미도래 — 외생 조건(사용자 결정·요청). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)

**Title:** per-execution ledger (`order_executions`) — BL-014 원안의 잔여
**Category:** Backend / trading
**Priority:** P3
**Trigger:** 주문 1건의 체결 내역(체결가·수량·수수료 분포) 분석 요구가 생길 때
**Est:** M (4-5h, 마이그레이션 1)
**출처:** 2026-07-25 money-path-accuracy (BL-014 부분 Resolved 후 잔여)

**원인 / 영향:** BL-014 원안은 append-only `order_executions` 테이블(order_id / executed_at / qty / price / fee)을 권고했다. money-path-accuracy 는 거래소 확정 `closedPnl` 로 **주문 단위** 정확도를 확보했으므로 리스크 집계에는 충분하지만, 한 주문 안의 체결 분포는 여전히 표현되지 않는다. `Order.filled_quantity` 는 누적 체결 수량 1개 값만 보유한다.

**권장 접근:** 실제 분석 수요가 생기기 전에는 만들지 않는다(YAGNI). 필요해지면 `/v5/execution/list` 를 원천으로 append-only 적재.

---

### BL-441

**Title:** entry 부분체결 시 pine_v2 warmup-replay 의 사이즈 발산
**Category:** Backend / pine_v2 · trading (money path)
**Priority:** P2
**Trigger:** entry 부분체결이 1건이라도 실관측될 때
**Est:** M (4-6h)
**상태:** ⏳ 대기 (트리거 미도래) — 부분체결 계측(qb_partial_fill_total)만 있고 warmup-replay 수량 보정도 세션 fail-closed 비활성화도 없다 — 조건부 진입 tick 판정 불가 처리가 전부. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-25 money-path-accuracy

**원인 / 영향:** entry 주문이 부분체결되면 거래소 실포지션은 시뮬레이션이 가정한 수량보다 작다. `run_live` 는 매 평가마다 전체 히스토리를 재실행하며 **자기 시뮬 포지션**을 기준으로 청산 수량을 산출하므로, 이후 close 신호가 실제 보유량보다 큰 수량을 요청한다. reduce-only 라 over-fill 은 막히지만 시뮬과 실계좌의 사이즈가 계속 어긋난다.

**권장 접근:** `Order.filled_quantity`(이번 스프린트로 4 경로 전부 write 됨)를 warmup-replay 진입 수량 보정 입력으로 사용하거나, 부분체결 감지 시 세션을 fail-closed 비활성화한다. `qb_partial_fill_total` 이 실관측 빈도를 제공한다.

---

### BL-446

**Title:** `cumulative_loss` 가 전 기간 누적 손익을 현재 잔고로 나눈다 (시간축 불일치 + 외부 거래 분모 오염)
**Category:** Backend / trading (risk gate)
**Priority:** P2
**Trigger:** 실자금 전환 전 필수
**Est:** M (4h — 리스크 게이트 변경이라 회귀 범위 넓음)
**상태:** ⏳ 대기 (트리거 미도래) — 분자는 여전히 strategy_id+filled 전 기간 합(시간창 없음), 분모는 trigger 시점 실잔고 — 스냅샷/기간창 처방 흔적 없음 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-25 exit-attribution Plan 압박검증 + 실측

**원인 / 영향:** `CumulativeLossEvaluator`(`kill_switch.py:97-136`)의 분자는 `strategy_id` + `state=filled` 전 기간 누적이고(시간창·`reduce_only`·`realized_pnl_synced_at` 필터 전무), 분모는 `balance_provider.fetch_balance_usdt` 로 조회한 **현재** 잔고다. ① 과거 데이터를 소급 삽입/보정하면 **오늘의 발주 게이트**가 즉시 반응한다 ② 앱 밖 외부 거래가 잔고를 줄이면 **분모가 이미 오염**되므로 그 손익을 분자에 넣으면 이중 반영, 안 넣어도 과대평가다. **실측 — 임계 10%, 분모 실잔고 190,679 USDT 기준 백필 후 loss% 는 0.00018%(여유 54,117배)라 현재 계정에선 발화하지 않는다.** 구조 결함이므로 실자금 전환 전에 닫아야 한다.

**권장 접근:** `capital_base` 를 전략 시작 시점 스냅샷으로 고정하거나, 분자에 세션/기간 창을 도입해 분자·분모의 시간축을 맞춘다.

---

### BL-447

**Title:** `exchange_order_id` write 2경로가 `""` / `"None"` 을 저장할 수 있어 unique index 도입을 막는다
**Category:** Backend / trading
**Priority:** P3
**Trigger:** `exchange_order_id` 에 unique index 를 걸어야 할 때 (합성 행 도입 등)
**Est:** S (2h)
**상태:** ⏳ 대기 (트리거 미도래) — sanitize 미적용 — WS 는 여전히 str(...,""), reconciler 는 str(exch.get("id",...)), transition_to_filled 는 str 무조건 write, 계정 스코프도 없다 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-25 exit-attribution 적대 평가

**원인 / 영향:** `state_handler.py:235` 는 `str(payload.get("orderId", ""))` 이라 WS 페이로드에 키가 없으면 **빈 문자열**을 저장한다. `reconciliation.py:233` 은 `str(exch.get("id", ...))` 인데 ccxt `safe_order` 가 `id` 키를 **항상 포함**하므로 값이 `None` 이어도 default 가 발동하지 않아 문자열 `"None"` 이 된다. 두 경로 모두 `transition_to_filled` 의 무조건 write 로 들어간다. partial unique index 가 걸린 상태라면 이 UPDATE 가 `IntegrityError` 로 실패해 **체결이 DB 에 기록되지 않는다.** 또한 `state_handler.py:251-263` 의 `_get_by_exchange_order_id` 는 계정 스코프가 없어 계정 간 id 충돌 시 `MultipleResultsFound` 로 터진다(Binance `orderId` 는 심볼별 int64).

**권장 접근:** 두 write 경로를 sanitize(빈 문자열/`"None"`/공백 → `NULL`)하고 `transition_to_filled` 의 인자를 `str | None` 으로 바꿔 None 이면 기존값 보존. `_get_by_exchange_order_id` 에 `exchange_account_id` 조건 추가. 그 다음에야 `(exchange_account_id, exchange_order_id)` 복합 partial unique 가 안전하다.

---

### BL-449

**Title:** `Order.webhook_payload` 가 SQL NULL 이 아니라 JSONB `'null'` 로 저장됨
**Category:** Backend / trading
**Priority:** P3
**Trigger:** `webhook_payload IS NULL` 술어나 partial index 를 쓰려 할 때
**Est:** S (1h, 마이그레이션 1)
**상태:** ⏳ 대기 (트리거 미도래) — webhook_payload 는 아직 plain JSONB 이고 'null' 정규화 마이그레이션도 없다 — none_as_null 은 ExchangeExit.raw 에만 적용됐다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-25 exit-attribution 적대 평가 실측

**원인 / 영향:** `models.py:181-184` 가 `Column(JSONB, nullable=True)` 만 지정해 `none_as_null` 이 기본값 False 다. Python `None` 이 `'null'::jsonb` 로 직렬화되어 **DB 실측 17행 중 15행이 JSONB `'null'`** 이고 SQL NULL 은 레거시 시드 2행뿐이다. `webhook_payload IS NULL` 을 술어로 쓰면 레거시 2행만 잡는다.

**권장 접근:** `postgresql.JSONB(none_as_null=True)` 로 바꾸고 기존 `'null'` 행을 SQL NULL 로 정규화하는 데이터 마이그레이션을 함께 넣는다. exit-attribution 의 `ExchangeExit.raw` 는 처음부터 이 지정을 적용했다.

---

### BL-450

**Title:** 일일 dogfood 보고 `get_daily_summary` 에 테넌트 스코프가 없음
**Category:** Backend / trading
**Priority:** P3
**Trigger:** 사용자가 둘 이상 되는 시점 (Beta)
**Est:** S (1h)
**상태:** ⏳ 대기 (트리거 미도래) — get_daily_summary(date) 는 여전히 date 인자 하나뿐이고 user/account 조인이 없어 전 테넌트 글로벌 합계다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(Beta·프로덕션 배포). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-25 exit-attribution grounding 실측

**원인 / 영향:** `order_repository.py:286-319` 의 `get_daily_summary` 는 `state='filled' AND filled_at ∈ [UTC 자정, +1d)` 만 걸고 user/strategy/account 스코프가 전혀 없다 — **전 테넌트 글로벌 합계**다. `dogfood_report.py:84` 가 이 값을 HTML 리포트에 싣는다. 단일 사용자 환경에선 무해하나 Beta 진입 시 남의 손익이 섞인다.

**권장 접근:** `user_id` 파라미터를 받아 `exchange_accounts` 조인으로 스코프를 건다.

---

### BL-452

**Title:** 거래소 청산 원장이 최근 7일만 담는다 — 과거 이력 적재·백필 불가
**Category:** Backend / trading (money path)
**Priority:** P3
**Trigger:** 아래 중 하나가 실제로 관측될 때 — ① 워커가 7일 넘게 정지한 실사례 ② 7일보다 오래된 미동기화 reduce-only 주문 관측 ③ 한 계정의 7일 청산이 500행 초과(`closed_pnl_window_truncated` 경고 발화) ④ `list_unsynced_reduce_only` 목록이 영구 좀비로 포화
**Est:** M (4-6h — 일회성 catch-up 재도입)
**상태:** ⏳ 대기 (트리거 미도래) — 일회성 catch-up 경로가 레포에 없고, ASC 좀비 정렬(order_repository.py:769)과 meta 커서 tie(-1)도 그대로다 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-25 exit-attribution **범위 축소** 결정 (`context-notes.md` §9)

**원인 / 영향:** 스윕은 매 주기 `[now−7d, now]` **한 창만** 조회한다([BL-438](#bl-438) 축소). 여기서 파생되는 한계 4종을 **의도된 트레이드오프**로 수용했다.

1. 7일보다 오래된 거래소 청산은 원장에 들어오지 않는다.
2. 따라서 백필·재동기화도 **7일 안에서만** 동작한다(#475 의 24시간 한계를 7일로 넓힌 것). 7일 넘게 미동기화로 남은 주문은 자동으로 안 고쳐진다.
3. 워커가 7일 넘게 죽어 있으면 그 구간은 영영 조회되지 않는다.
4. 7일 500행(`_CLOSED_PNL_MAX_PAGES=5` × `limit=100`) 상한을 넘는 계정은 가장 오래된 행을 잃는다. **관측은 로그뿐** — `providers.py` 의 `closed_pnl_window_truncated` 경고(계정 식별자 포함). `qb_closed_pnl_backfill_total` 의 8-outcome 계약이 불변이라 메트릭 라벨은 추가하지 않았다.

**★부수 위험 — `list_unsynced_reduce_only` head-of-line.** `order_repository.py:162` 는 시간창 없이 `ORDER BY filled_at ASC LIMIT 500` 이다. 7일 밖 청산은 원장에 못 들어오므로 그 주문은 영구 미동기화(좀비)로 남고, **ASC 라서 좀비가 앞줄을 차지**한다. 한 계정에 좀비가 500건 쌓이면 쿼리가 좀비만 돌려주어 신규 주문이 영영 백필되지 않으며, 그 상태와 "할 일 없음"을 구분하는 메트릭이 없다. `list_synced_reduce_only` 는 이미 `.desc()` 라 비대칭이다. **사용자 확정 = 등재만, 코드 미변경** (축소 전에도 90일 catch-up 이 ~65분 후 latch-off 되어 동일 위험이었고, 1인 로컬 앱에서 좀비 500건은 멀다).

**★부수 항목 — `fetch_closed_order_meta` 의 커서 tie.** `providers.py:1410` 은 아직 `until = oldest_ms - 1` 이라 같은 `createdTime` 행이 페이지 상한을 넘으면 tie 행을 건너뛴다. `fetch_closed_pnl_window` 쪽은 머니-패스라 이번에 경계 포함으로 고쳤으나, 이쪽은 **분류 라벨 전용 + `setdefault` 멱등**이라 그대로 뒀다 — 누락의 결과는 일부 행이 `unknown` 으로 분류되는 것뿐이다. 분류를 게이트 입력으로 승격하려면 함께 고쳐야 한다.

**권장 접근:** 워터마크 테이블을 되살리는 대신 **일회성 catch-up** 으로 설계한다(축소 전 구현이 실질적으로 그랬다 — §9 실측). 예: 관리 커맨드/1회성 task 가 지정 구간을 창 단위로 훑어 원장을 채우고 끝난다. 상시 beat 경로는 최근 7일 그대로 둔다. ★되살릴 때 **진행 상태를 원장의 `min(exchange_created_at)` 에서 파생하지 말 것** — 청산이 없던 구간에서 삽입이 0 이라 min 이 안 움직여 같은 빈 창을 영원히 재조회한다(실측 반증: 07-24 행 4건 적재 후 정지, 07-05 행 7건 영구 미도달). 함께 `list_unsynced_reduce_only` 를 `.desc()` 로 뒤집거나 `filled_at >= cutoff` 로 조회 창을 적재 창에 맞춘다.

**Risk:** 🟡 (관측 범위 축소. 머니-패스 정확도 자체는 7일 안에서 온전하고, 정상 상태 동작은 축소 전과 동일)

---

### BL-455

**Title:** 수동 청산이 `LiveSignalEvent` 를 남기지 않아 FE 타임라인과 watchdog 팬아웃에서 빠진다
**Category:** Backend / trading
**Priority:** P3
**Trigger:** 수동 청산을 이벤트 타임라인에서 보고 싶을 때 · watchdog 규칙을 수동 청산에도 걸고 싶을 때
**Est:** M (4-6h — 쓰기 경로 + 원자성 설계)
**상태:** ⏳ 대기 (트리거 미도래) — close_service 는 여전히 Order 만 만들고 이벤트를 안 남기며, 테스트가 'manual_close 는 세션 역인덱스에 안 잡힌다'를 그대로 고정하고 있다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(사용자 결정·요청). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-25 exit-money-path — [BL-444](#bl-444) 안 (b) 기각분 분리 등재

**원인 / 영향:** `ClosePositionService.close_position`(`close_service.py:78-95`)은 Order 만 만들고 `LiveSignalEvent` 를 만들지 않는다. [BL-444](#bl-444) 의 손익 집계 결함은 읽기 스코프 교체로 닫혔으나, **이벤트 FK 에 의존하는 나머지 두 기능은 여전히 수동 청산을 못 본다** — ① FE §07 이벤트 타임라인 ② `LiveSignalSessionRepository.find_active_by_order_id` 기반 watchdog 규칙 팬아웃(`tasks/trading.py:549-585`). TradingView 웹훅 주문도 같다.

**★착수 전 반드시 읽을 것 — 순진한 구현은 중복 청산을 발주한다.** `dispatch_pending_live_signal_events_task`(`tasks/live_signal.py:756`)가 beat 5분 주기로 `list_pending(limit=50)` 을 **세션 필터 없이 무조건 재발행**한다. `status=pending` 이벤트를 넣으면 beat 이 집어 두 번째 reduce-only 시장가 청산을 낸다. 수동 청산은 `idempotency_key=None`(`close_service.py:93`)이라 idempotency 방어도 없다. 또 `OrderService.execute` 가 내부에서 commit 하므로 "주문 커밋 → 이벤트 커밋" 사이 프로세스가 죽으면 이벤트 없는 주문이 남는다 — OrderService 의 커밋 경계를 재설계하지 않는 한 이 구멍은 못 막는다.

**★UNIQUE 주의.** `uq_live_signal_events_idempotency(session_id, bar_time, sequence_no, action, trade_id)` 에 `on_conflict_do_nothing` 이 걸려 있다(`live_signal_event_repository.py:100`). `bar_time` 을 바 경계로 정렬하면 **진짜 Pine 시그널 INSERT 가 조용히 삼켜진다.** `trade_id = f"manual:{order_id}"` 처럼 그 필드 하나로 전역 유일성이 보장되는 형태여야 한다.

**권장 접근:** 이벤트 테이블의 계약("엔진이 낸 실행 지시")을 오염시키지 않는 별도 표현(예: 이벤트에 출처 컬럼 추가, 또는 타임라인을 Order 기준으로 합성)을 먼저 검토한다. 이벤트를 직접 넣기로 한다면 `status` 를 pending 이 아닌 terminal 로 넣어 beat 재발행 경로를 원천 차단할 것.

**Risk:** 🟡 (관측 결손. 잘못 구현하면 🔴 — 중복 청산 발주)

---

### BL-456

**Title:** 세션 창이 `filled_at` 반열림이라 늦은 체결이 다음 세션으로 오귀속되거나 영구 미귀속된다
**Category:** Backend / trading (money path)
**Priority:** P3
**Trigger:** 세션 종료 직후 체결이 실제로 관측될 때 — `filled_at − created_at` 간극이 세션 종료 지연보다 클 때
**Est:** M (3-4h — 대안마다 다른 결함이 있어 설계가 핵심)
**상태:** ⏳ 대기 (트리거 미도래) — 창은 여전히 filled_at 반열림 그대로이고(:225/:233/:238) 권장 선행조건인 filled_at−created_at 간극 실측 기록이 레포에 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-25 exit-money-path [BL-445](#bl-445) 가 **수용한** 트레이드오프

**원인 / 영향:** `_session_scope_where`(`order_repository.py`)가 창을 `Order.filled_at` 에 `[created_at, deactivated_at)` 로 건다. 청산을 누르고(202, `state=pending`) 곧바로 세션을 끈 뒤 체결이 도착하면 그 주문은 자기를 만든 세션에서 빠진다. 인접 세션이 있으면 **그쪽으로 귀속**되고, 없으면 **어느 세션에도 안 잡힌다.** 후자의 경우 Site 3(loss-limit)·Site 4(커브·대시보드 KPI) 양쪽에서 사라진다.

덧붙여 `Order.filled_at` 은 거래소 체결시각이 아니라 **우리 관측시각**("terminal_at")이라, 창의 정밀도가 관측 지연만큼 흐리다(codex G0 지적).

**검토한 대안과 각각의 결함** — ① `created_at` 상한: 늦은 체결을 살리고 인접 세션 중복도 없지만, 인과("이 세션이 이 주문을 일으켰나")와 커브 x축(`filled_at`)의 기준이 갈린다 ② `filled_at + grace`: 임의 상수가 생기고 인접 세션과 창이 겹쳐 **같은 주문이 두 커브에 동시 등장**한다 ③ 현행 `filled_at` 반열림: 배타성은 완벽하나 늦은 체결을 흘린다.

**권장 접근:** 실측이 선행돼야 한다 — dogfood 에서 `filled_at − created_at` 실제 간극을 재고, 그 간극이 세션 종료 지연보다 유의하게 큰지 확인한 뒤에야 대안을 고른다. 간극이 수백 ms 수준이면 현행 유지가 옳다.

**Risk:** 🟡 (경계 케이스 손익 누락. 현행 계약은 테스트로 고정돼 있어 조용한 변경은 불가)

---

### BL-459

**Title:** 세션 읽기와 주문 조회 사이에 비활성화가 커밋되면 그 한 번의 응답이 종료 후 체결을 포함한다 (TOCTOU)
**Category:** Backend / trading (money path — 관측 정확도)
**Priority:** P3
**Trigger:** 세션 종료와 체결이 같은 순간에 겹치는 것이 실제로 관측될 때
**Est:** M (3-4h — 세션↔주문 단일 조인으로 재구성)
**상태:** ⏳ 대기 (트리거 미도래) — 세션 행을 파이썬에서 읽어 SessionScope 를 만든 뒤 별도 SELECT 로 주문을 조회하는 구조가 두 소비처에 그대로다 — 단일 조인 없음. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-25 exit-money-path **최종 codex 누적 diff 리뷰** [P2]

**원인 / 영향:** 두 소비처 모두 **세션 행을 먼저 읽고 → 별도 SELECT 로 주문을 조회**한다.

- `alert_rules.py:60` — `list_active_loss_rules_with_sessions()` 가 `is_active=true` 세션만 돌려주므로 `SessionScope.ended_at` 은 항상 `None`(무상한)이다.
- `router.py:465` — `get_by_id(session_id)` 로 읽은 `sess` 의 `deactivated_at` 을 그대로 쓴다.

그 사이에 `LiveSignalSessionRepository.deactivate`(`:155`)가 커밋되면 — 호출 지점은 4곳(`tasks/live_signal.py:433/503/539` beat + `router.py:442` 사용자 DELETE) — 스코프는 여전히 무상한이라 **종료 후 체결이 그 한 번의 계산에 섞인다.** READ COMMITTED 라 두 번째 SELECT 는 새 스냅샷을 보지만 `ended_at` 값은 이미 파이썬 쪽에 잡혀 있다.

**★등급 판단 — 회귀가 아니다.** 이 변경 **전에는** Site 4 에 창이 아예 없었고(전 기간 무조건 포함) Site 3 도 창이 없었다. 즉 이 레이스는 새 코드가 **한 번의 계산 동안만** 옛 동작을 하게 만드는 것이고, 다음 평가/요청에서 자가 교정된다. 두 경로 모두 발주를 막지 않는 **읽기 전용 관측**이다. 그래서 exit-money-path 는 이걸 고치지 않고 등재만 했다 — 스프린트 막바지에 쿼리 구조를 바꾸면 회귀 표면이 넓어지고, codex 자신도 "새 테스트는 순차 실행뿐이라 이 경쟁 조건을 잡지 못한다" 고 적었다.

**권장 접근:** 세션 경계와 주문을 **한 쿼리**로 묶는다(`live_signal_sessions` 를 조인해 `s.created_at`/`s.deactivated_at` 을 SQL 안에서 읽게 한다 — `docs/archive/sprints/exit-money-path/operating-contract.md` §5 의 진단 SQL 이 이미 그 형태다). 그러면 단일 스냅샷 안에서 경계와 행이 함께 결정된다. 잠금은 불필요하다.

**Risk:** 🟢 (한 번의 응답/평가에 한정 · 자가 교정 · 변경 전보다 엄격)

### BL-468

**Title:** `OHLCV_FIXTURE_ROOT` 기본값이 CWD 상대라 host 실행에서 깨지고, `FixtureProvider` 는 canonical 심볼을 서빙할 수 없다
**Category:** Backend / market_data
**Priority:** P3
**Trigger:** fixture provider 를 실제로 쓸 때
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — config 기본값은 여전히 CWD 상대이고 fixture.py:30 이 심볼 슬래시를 그대로 경로에 넣는다 — 두 결함 모두 미수정. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**원인 / 영향:** ① 코드 기본값 `"apps/api/data/fixtures/ohlcv"` 가 프로세스 CWD 상대인데 `mise run be`/`mise run be-isolated` 는 `cd apps/api` 후 실행하므로 `apps/api/apps/api/…` 로 풀린다(존재하지 않음). 오늘 무해한 이유는 host uvicorn 이 `FixtureProvider.get_ohlcv()` 를 실제로 호출하지 않기 때문뿐이다. ② `FixtureProvider` 는 `root / f"{symbol}_{tf}.csv"` 를 만드는데(`fixture.py:30`) canonical `BTC/USDT` 의 슬래시가 **경로 구분자**가 되어 `<root>/BTC/USDT_1h.csv` 를 찾는다. 커밋된 픽스처는 평면 `BTCUSDT_1h.csv` 뿐 — 레포의 빈 `apps/api/data/fixtures/ohlcv/BTC/` 디렉터리가 과거에 누가 여기 부딪힌 흔적이다.

**권장 접근:** 기본값을 레포 루트 기준 절대경로로 해석하거나, `FixtureProvider` 가 심볼의 `/` 를 파일명 안에서 치환.

**Risk:** 🟡 (오늘은 timescale provider 만 쓰여서 잠복)

---

### BL-471

**Title:** `exchange_exits` 는 `row_hash` 멱등이라 분류 로직이 바뀌어도 기존 행이 재분류되지 않는다
**Category:** Backend / trading (원장)
**Priority:** P3
**Trigger:** 분류·귀속 로직 변경 시
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — on_conflict_do_nothing 멱등 적재가 그대로고, classification_version 컬럼도 재분류 마이그레이션도 레포에 전혀 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**원인 / 영향:** 원장 적재는 `row_hash` 로 멱등이라 이미 있는 행은 건너뛴다. 그래서 BL-457(#481)이 `classify_exit` 의미를 바꿨는데도 기존 행은 pre-fix 라벨로 고착돼 있다. 실측 — 현 개발 DB 4행 중 3행이 `ours` 인데 `matched_order_id` 는 전부 NULL 이고 `orders` 는 0행이다. 포스트-#481 로직이면 `unknown` 이 나와야 한다.

**권장 접근:** 재분류 마이그레이션 또는 `classification_version` 컬럼 + 버전 불일치 시 재계산.

**Risk:** 🟢 (라벨 전용 축이고 소비처가 0)

---

### BL-475

**Title:** 서버 권위 risk% 사이징이 구현된 적 없다 (UI 는 있다고 말하고 있었다)
**Category:** Backend / trading (사이징)
**Priority:** P3
**Trigger:** 사이징 자동화가 실제로 필요해질 때
**Est:** M
**상태:** ⏳ 대기 (트리거 미도래) — compute_position_size 는 레포 전체에서 backlog 문서에만 존재하고 quantity 도 여전히 Field(gt=0) 필수 — 수량 산출 미구현. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-26 BL-474 작업 중 발견

**원인 / 영향:** 테스트 주문 다이얼로그의 "리스크 %" 모드 문구는 _"수량은 서버가 잔고·리스크 기준으로 계산합니다 (서버 권위 사이징)"_ 였다. 그런 코드는 없다. `OrderService._validate_position_size`(`order_service.py:92-134`)는 `max_qty` 를 구해 **client 수량이 초과하면 거부**할 뿐 수량을 만들어내지 않는다. 게다가 그 모드는 payload 에서 `quantity` 를 빼고 보냈고 `parse_tv_payload:122` 는 `payload["quantity"]` 를 필수로 읽으므로 **전송하면 401** 이었다 — 한 번도 작동한 적 없는 경로다.

**BL-474 에서 한 것(전체 아님):** 모드를 실제 동작에 맞춰 재정의했다 — 수량 필수 + risk% 는 **상한**, 손절가 필수(없으면 `risk_sizing_skip_no_stop` 으로 가드가 조용히 skip 되어 "통과처럼 보이는 미검증" 이 된다). `risk_percent` 를 webhook 파서·라우터에 배선해 상한 검증이 실제로 돌게 했다.

**남은 것:** 진짜 서버 사이징(잔고 × 리스크% ÷ 스탑거리로 **수량 산출**)은 미구현. 필요해지면 `_validate_position_size` 옆에 `compute_position_size` 를 두고 `OrderRequest.quantity` 를 optional 로 여는 설계 결정부터 해야 한다(현재 `Field(gt=0)` 필수).

**Risk:** 🟢 (거짓 문구는 제거됨)

---

### BL-476

**Title:** 공개 webhook 핸들러가 동기 CCXT 왕복 3회를 태운다 (실측 **+4.8초**)
**Category:** Backend / trading (지연)
**Priority:** P2
**Trigger:** TradingView 실연동 전 / webhook 타임아웃 관측 시
**Est:** M
**상태:** ⏳ 대기 (트리거 미도래) — webhook 라우터가 여전히 동기로 OrderService.execute 를 호출하고 가드의 CCXT 3회(mark/min_notional/balance)가 그대로 인라인이다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-26 BL-474 dogfood 실측

**원인 / 영향:** BL-474 로 `leverage` 가 채워지면서 `order_service.py:218-266` 의 notional 가드가 webhook 경로에서 **처음으로 도달 가능**해졌다. 그 대가로 동기 HTTP 핸들러 안에 CCXT 왕복 3회가 들어왔다.

```
fetch_mark_price     1663 ms   -> 64532.7
fetch_min_notional   1549 ms   -> 5.0
fetch_balance_usdt   1600 ms   -> 190549.99
TOTAL                4812 ms
```

각 호출이 계정 재조회 + 자격증명 복호화 + ephemeral ccxt 클라이언트 생성(`timeout: 30000`)을 한다. 위는 정상 응답 기준이고, 거래소가 느리거나 죽으면 **최악 90초**까지 늘어난다 — TradingView 는 webhook 을 재시도하므로 중복 신호가 될 수 있다(멱등키가 있으나 client-generated 라 재시도마다 새 값이면 무력).

**★게이트가 못 잡는 종류다.** 테스트는 provider 를 stub 으로 갈아끼우므로 항상 0ms 다. 회귀는 프로덕션에서만 보인다.

**권장 접근:** 가드를 Celery 경계 뒤로 옮긴다 — `OrderService.execute` 는 행을 만들고 즉시 201 을 주고, `tasks/trading.py:_execute_with_session` 이 발주 직전에 가드를 평가해 실패 시 `rejected` 로 전이. 이미 그 경로에 `except ProviderError` graceful 전이가 있다. 다만 **거부 시점이 응답 뒤로 밀리는** 계약 변경이라 별도 결정이 필요하다.

**Risk:** 🟡 (지연 절벽, 데이터 오류는 아님)

---

## 변경 이력

### BL-522

**Title:** ★**엔진이 체결로 간주한 진입을 라이브가 완결하지 못하면 복구 경로가 없다** — 유실 채널 ~~5종~~ **실측 1종**
**Category:** Backend / trading (라이브 진입 완결성)
**상태:** ⏳ **대기 (트리거 미도래) — 「축소」 (2026-08-01 entry-completeness-rejudgement).** 유실 채널 5종 중 **(2)(3) 은 유실 채널이 아님이 확정**, **(4)(5) 는 판별력을 증명한 계측기로 0**, 남은 것은 **(1) 잔여 거절 하나뿐 1건/2일**이다. 층위1 확정 거절률 **16.67% → 2.44%** · 에피소드 유실률 **2.08%**. **P1 → P2 강등** — 잔여 설계는 [BL-578](#bl-578), 재측정 근거는 [BL-536](#bl-536) §2026-08-01(Resolved). 아래 §채널 5종 크기 확정 참조.
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**Priority:** **P2** (~~P1~~ — 2026-08-01 축소 판정으로 강등. ★Trigger 는 유지한다)
**Trigger:** 실자금 cutover 전 필수
**Est:** M-L
**출처:** 2026-07-28 live-entry-parity — codex G1 검증 #1/#2/#3/#4/#5 가 하나의 근본원인으로 수렴, soak 실측으로 크기 확정

**원인 / 영향:** sim 이 pending stop 을 체결하면(`strategy_state.py:82-83`) 그 주문은 `desired` 에서 사라지고 포지션이 된다. 그런데 `action="fill"` 은 **dispatch 대상이 아니다** — `event_loop.py:422` 가 "broker 가 자체 fill 알림 처리" 를 전제하기 때문이다(BL-478 이 지적한 그 전제). 따라서 그 진입이 라이브에서 **어떤 이유로든** 완결되지 못하면 다시 시도할 주체가 없다.

**유실 채널 5종** — (1) 조회~발주 사이 가격이 다시 움직여 생기는 잔여 거절 (2) `market_orders_in_flight` 로 reconcile 전체가 deferred (3) 전환 주문의 부분체결 (4) 돌파+resting 조합에서 취소가 트리거를 이긴 경우 (5) notional/balance 사전 게이트 거부.

~~★**크기가 처음 측정됐다** — 62분 soak 에서 `qb_live_conditional_reconcile_errors_total{stage="deferred_market_inflight"}` = **14**. 채널 (2) 하나가 **시간당 14회**다.~~ 조건부 모델에서는 다음 bar 에 재등재되므로 무해했지만 **1-shot 시장가 전환에서는 유실**이다.

> ### ❌ **「시간당 14회」는 반증됐다 (2026-08-01 silent-surface-honesty, 소급 정정)**
>
> 근거였던 `deferred_market_inflight` 는 **유실 채널이 아니라 「청산 tick 수」**임이
> 2026-07-30 close-mismatch-visibility 에서 확정됐다 — `live_signal_events` 9건이 **전량
> `action='close'`** 이고 counter 9 와 **1:1 동치**이며, 게다가 이 counter 는 `desired` 를
> **읽기 전에** 오른다(`live_signal.py:706` vs `:742`) ⇒ **미룰 진입이 0건이어도 발화한다.**
> 그 판정은 [BL-536](#bl-536) 섹션에 기록됐는데 **본 섹션에는 전파되지 않아** 3개월 가까이
> 반증된 숫자가 P1 크기 근거로 남아 있었다.
>
> **처분:** 채널 (2) 의 크기는 **미측정**이다. 이 숫자를 인용하지 마라.
> 채널 5종 중 (2) 를 제외한 나머지의 크기도 재측정 대상이다.
> ★결함 실재 자체는 반증되지 않았다 — **크기만 근거를 잃었다.**

> ### 🟢 **채널 5종 크기 확정 (2026-08-01 entry-completeness-rejudgement)** — 위 「재측정 대상」의 답
>
> **[BL-536](#bl-536) 재판정이 5종 전건의 크기를 냈다. 판정 = 「축소」(사전등록 A3).**
>
> | 채널                                 | 크기 (창 P = 2026-07-30~31, 조건부 파이프라인 109건)                                                                            |
> | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- |
> | **(1) 잔여 거절**                    | **1건 / 2일** — 유일한 잔존 채널. 격차 0.0005~0.071%. → [BL-578](#bl-578)                                                       |
> | **(2) `market_orders_in_flight`**    | ★**유실 채널이 아니다.** 「청산 tick 수」로 확정(PR #511). **크기 질문 자체가 성립 안 함**                                      |
> | **(3) 전환 주문의 부분체결**         | ★**유실 채널이 아니다.** 조건부 진입 부분체결은 **원장 전 기간 0건**. 원표 `7` 은 **청산측 `qty_step` 절삭 아티팩트**(5축 확정) |
> | **(4) 취소가 트리거를 이김**         | **0 / 68** — 공개 Bybit kline 2호스트 교차(불일치 0) + 체결분 35/37 양성 대조로 판별력 증명                                     |
> | **(5) notional/balance 사전 게이트** | **0** — counter 3종 series 전부 부재 + `live_signal_events` 전 기간 failed 는 `close_position_flat` 뿐 (2축)                    |
>
> ★**따라서 본문의 「유실 채널 5종」은 실제로는 1종이다.** 「전환 의도를 영속화하는 새 상태
> 저장소」는 **짓지 마라** — 본문 자신이 경고한 「사라질 문제에 저장소를 만드는」 경우다.
> 상세 = [BL-536](#bl-536) §2026-08-01 재판정.

**권장 접근:** 전환 의도를 영속화해 다음 tick 에 재시도하거나, `action="fill"` 을 라이브에서 소비하는 경로를 만든다. ★**새 상태 저장소는 위험하므로 크기를 본 뒤 설계한다** — 이번 스프린트가 계측만 넣고 멈춘 이유다.
**Risk:** 🟡 (백테스트↔라이브 진입 발산. 실주문을 잘못 내지는 않는다)

---

### BL-523

> ### 🟡 **판정 「축소」 (2026-07-30 close-mismatch-soak) — ★붙일 값이 없다**
>
> **본문의 전제 2건이 코드 대조로 반증됐다.**
>
> 1. ★**`exit_levels_for` 는 조건부 진입에 대해 항상 `(None, None, None)` 이다.**
>    `place_exit` 가 `targets = [from_entry] if from_entry in self.open_trades else []`
>    (`strategy_state.py:963`) 로 **`open_trades` 만** 타깃하는데, stop 진입은
>    `pending_orders[...] = PendingOrder(...); return None`(`:714-726`) 이라 체결 전까지 거기 없다.
>    ⇒ `pending_exits` 에 레그가 **애초에 생기지 않는다.**
> 2. ★**시드 전략 `s1_pbr.pine` 은 `strategy.exit` 이 0건**이고, 코퍼스 8벌 중 stop 진입과 exit 을
>    **둘 다 쓰는 전략이 없다**(`s4_hma_curvature` 는 exit 만, 나머지는 stop 진입만).
>
> **부수 정정 — 본문의 패리티 근거도 틀렸다.** _"백테스트는 체결 직후 `check_exit_fills` 로
> 브래킷이 활성화되므로 라이브만 무방비"_ 라고 적었으나, bar 루프는
> `check_exit_fills`(`event_loop.py:169`) → `interp.execute`(`:197`) 순서라 레그는 그 bar **끝**에
> 등록되어 **다음 bar** 부터 검사된다. **백테스트도 체결 bar 안에서는 보호하지 않는다.**
>
> #### 실주행 확인 (2026-07-30, celery 경유 · 메인 체크아웃)
>
> ```
> qb_live_conditional_guard_total{outcome="bracket_unavailable"} 2.0
>                                (bracket_attached — 부재)
> ```
>
> 조건부 진입 2건 전량이 `bracket_unavailable`. **100% / 0%** 로 전제가 재현됐다.
>
> **이번 회차에 한 것:** 3단 seam 배관 + 게이트 A(trailing-only 거부)/B(tpSize 정합) +
> `conditional_request_invalid` 라벨 분리 + guard outcome 4종. **부착이 목적이 아니라
> "붙일 것이 있었는가" 를 재는 계측이 산출물이다.** 회귀 테스트
> `test_pending_order_snapshot_has_no_exit_levels_when_entry_not_open` 이 이 사실을 못박는다.
>
> **남은 것(이번 범위 밖):** `bracket_unavailable` 이 계속 100% 면 선택은 둘 —
> (a) `place_exit` 이 pending 진입도 타깃하도록 **엔진 계약 변경**(백테스트 결과가 바뀌므로 TV 패리티 게이트 필요),
> (b) 체결 후 부착(`set_trading_stop` 이 현재 trailing 전용 시그니처라 TP/SL 확장 필요).
> ★**지금 고르지 마라 — 아직 크기를 모른다.**

**Title:** 조건부·전환 진입에 TP/SL 브래킷이 붙지 않는다 — ~~전환은 즉시 체결이라 무방비 창이 실재한다~~ → **엔진이 pending 진입에 exit 레그를 만들지 않아 실을 값이 없다**
**Category:** Backend / trading (조건부 진입)
**Priority:** P2
**Trigger:** 실자금 cutover 전
**Est:** M
**상태:** ⏳ **대기 (트리거 미도래) — 범위 「축소」**(2026-07-30 close-mismatch-soak). 전제 반증: 엔진이 pending 진입에 exit 레그를 만들지 않아 실을 값이 없다. 배관+계측은 착지, 엔진 계약 변경은 크기 미확정으로 보류.
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-entry-parity 적대 검증(백테스트 패리티 렌즈)

**원인 / 영향:** reconcile 의 `OrderRequest`(`tasks/live_signal.py` 발주 루프)에 `take_profit`/`stop_loss`/`trailing_stop` 이 없다. 일반 LiveSignal 경로는 지정한다. 백테스트는 체결 직후 `check_exit_fills`(`event_loop.py`)로 브래킷이 활성화되므로 **라이브만 무방비**다. 조건부일 때는 트리거 전까지 잠재적이었지만 **시장가 전환은 즉시 포지션을 연다.**

**권장 접근:** `PendingOrderSnapshot` 에 exit 레벨을 실어 진입 주문에 부착한다. 체결 후 부착 경로(`_enqueue_trailing_if_intended`)와 중복되지 않게 정리 필요.
**Risk:** 🟡

---

### BL-524

**Title:** `strategy.entry(limit=...)` 이 조용히 버려지고 시장가 진입으로 대체된다 — TV 충실도 결함
**Category:** Backend / pine_v2
**Priority:** P2
**Trigger:** limit 진입을 쓰는 전략을 지원할 때
**Est:** M
**상태:** ⏳ 대기 (트리거 미도래) — entry 의 limit/trail/qty_percent 는 여전히 unsupported 로 버려지고, PendingOrder 에 limit_price 필드가 없다(있는 건 exit leg 뿐). (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-entry-parity 스코프 조사

**원인 / 영향:** `interpreter.py:1521-1523` 이 `limit`·`trail_points`·`trail_offset`·`qty_percent` 를 **미지원 인자로 걸러 경고만 남기고** 버린다. `stop` 이 없으면 그 진입은 `MarketIntent` 로 큐돼 **시장가로 체결**된다. `PendingOrder`/`PendingOrderSnapshot` 에 `limit_price` 필드 자체가 없어 라이브 reconciler 까지 도달하지 못한다.

★백테스트와 라이브가 **똑같이** 그러므로 패리티 결함은 아니다. 그러나 TV 는 지정가 도달을 기다리므로 **TV 충실도**가 깨지고, 사용자는 경고를 라이브에서 보지 못한다(`live_signal.py` 에 `warnings` 참조 0건).
**Risk:** 🟡

---

### BL-525

**Title:** 라이브가 Track A(indicator + alertcondition) 전략을 어떻게 다루는지 정의되지 않았다
**Category:** Backend / trading (라이브 신호)
**Priority:** P3
**Trigger:** Track A 전략으로 라이브 세션을 열 때
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — run_live 는 아직 run_historical 만 호출하고, trading 라우터/서비스 어디에도 Track 판정·422 가드가 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-entry-parity codex G1 검증 #7 (재현 확인)

**원인 / 영향:** `run_live`(`event_loop.py`)는 `run_historical` **만** 호출한다. Track A 를 처리하는 `run_virtual_strategy` 는 `TrackRunner._dispatch_table["A"]` 로만 도달한다. 즉 라이브 경로에 Track 분기가 없다. `fill_timing=next_bar_open` 이 Track A 에서 무시된다는 경고도 라이브에서는 발생하지 않는다(그 코드에 도달하지 않으므로).

★이번 스프린트가 "없는 경로에 계측을 붙이지 않기 위해" W3-3 을 폐기하면서 발견했다. **영원히 0인 카운터를 만들지 않은 대신, 그 경로가 무엇을 하는지는 여전히 미정의다.**

**권장 접근:** 라이브 세션 등록 시 Track 을 판정해 미지원이면 422 로 막거나(BL-478 (c) 선례), `run_live` 에 Track 분기를 넣는다.
**Risk:** 🟢

---

### BL-527

**Title:** ★`trade_id` 재사용 + catch-up 다중 emit 이 `pnl_by_trade` 를 덮어써 기대치를 오염시킬 수 있다
**Category:** pine_v2 / 라이브 신호
**Priority:** P2 (잠재 — 실데이터 미재현)
**Trigger:** 기대치 정확도가 판정 입력으로 쓰이기 전
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — pnl_by_trade 는 여전히 t.id 단일 키 dict 이고 거짓 전제 주석도 그대로이며, catch-up 정상 경로도 유지된다 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-outcome-parity 적대 검증

**원인 / 영향:** `event_loop.py` 의 `pnl_by_trade` 는 `strategy_state.closed_trades` 를 `t.id` 로 인덱싱하는데, 그 id 는 Pine 진입 이름(`"PivRevSE"` 등)이라 **거래마다 재사용**된다. 같은 dict 키에 여러 청산이 들어오면 **마지막 값만 남는다.**

그 코드의 주석은 스스로 "마지막 bar event 만 signal 로 나가므로 실무상 1:1" 을 근거로 든다. 그런데 `tasks/live_signal.py` 는 `last_evaluated_bar_time` 이 있으면 **거의 항상** `emit_from_bar_time` 을 세운다 — **catch-up 은 예외가 아니라 정상 경로**다. 즉 그 주석의 전제는 이미 거짓이다.

★**결함은 잠재, 근거는 확정.** 실데이터에서 같은 배치 안 다중 close 오염은 재현되지 않았다(중복 PnL 1쌍은 25분 떨어진 별개 bar). 오염되면 `live_signal_events.realized_pnl` 이 틀리고, 그것이 BL-526 표면의 **기대치 입력**이다.

**권장 접근:** `pnl_by_trade` 키를 `(trade_id, exit_bar_index)` 같은 유일 키로 바꾸거나, 청산을 dict 가 아닌 리스트로 들고 이벤트 생성 시점에 짝을 맞춘다. ★**주석의 거짓 전제를 먼저 지워라** — 그 문장이 남아 있으면 다음 사람이 같은 판단을 반복한다.
**Risk:** 🟡 (기대치 정확도)

---

### BL-528

**Title:** 세션 창 밖 늦은 체결이 어느 표면에도 안 잡힌다
**Category:** Trading / 세션 스코프
**Priority:** P2
**Trigger:** 세션 손익 완결성이 필요할 때
**Est:** M
**상태:** ⏳ 대기 (트리거 미도래) — created 창은 BL-536 진입 원장에만 열렸고, /state·손실한도·parity 3소비처는 여전히 terminal 창 기본값 + grace 없음 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-outcome-parity 실측

**원인 / 영향:** `SessionScope` 의 창은 `filled_at` 기준 반열림 `[started_at, ended_at)` 이고, 그 docstring 이 **"세션 종료 뒤 체결된 주문은 인접 세션이 있으면 그쪽으로, 없으면 어디에도 안 잡힌다"** 를 수용된 트레이드오프로 명시한다.

★**이번에 그 크기를 처음 쟀다** — 확정 청산 **27건 중 4건**(net **−0.5463**)이 어느 세션 창에도 안 들어간다. 그 4건은 `/state` 커브에도, outcome-parity 표면에도 나타나지 않는다.

부수 효과 — 기대 축(이벤트, `session_id` FK)과 실제 축(주문, `filled_at` 창)의 스코프 정의가 다르므로, 늦은 청산은 세션 A 에서 `expected_only`, 인접 세션 B 에서 `actual_only` 가 된다. **두 세션 패널이 서로 다른 답을 내되 둘 다 정상 응답**이다.

**권장 접근:** 창 상한을 `deactivated_at + grace` 로 두거나, 세션 귀속을 `filled_at` 이 아니라 **주문 생성 시점**(세션이 발주했다는 사실)으로 바꾼다. 후자가 의미상 맞지만 기존 소비처 3곳(`/state` 커브 · 손실 한도 알림 · 이번 표면)에 동시 영향이라 별도 스프린트가 필요하다.
**Risk:** 🟡

---

### BL-531

**Title:** parity 표면의 `ParitySummary` -> `OutcomeParityScope` 평탄화가 shotgun surgery
**Category:** Refactor / Trading
**Priority:** P2
**Trigger:** parity 지표를 더 붙일 때
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — \_to_scope 36필드 수동 평탄화·private \_session_scope_where import·linked/confirmed 술어 중복이 모두 그대로 남아 있다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-29 PR #496 코드리뷰 (Standards 축)

**원인 / 영향:** 순수 파생 `ParitySummary`(중첩 dataclass)를 응답 `OutcomeParityScope`(36 필드 평탄화)로 `_to_scope` 가 손으로 옮긴다. 지표 1개를 추가하면 **5파일**(순수 모듈 · 서비스 매핑 · 스키마 · zod · 패널)을 편집해야 한다.

부수로 같은 리뷰가 지적한 것 — `linked_order_scope` / `confirmed_close_scope` 가 5개 술어 완전 동일한데 이름만 둘(`parity_repository.py:337-355`), `_derive_ledger_values` 가 `len != 1` 을 걸러낸 뒤 1원소 합산 루프를 돈다, `load_account_ledger_diagnostics` CTE 가 안 쓰는 3열을 select 한다, `parity_repository.py:31` 이 `order_repository` 의 private `_session_scope_where` 를 import 한다.

**권장 접근:** 평탄화를 유지할지(직렬화 단순) 중첩을 노출할지 먼저 정한다. 유지한다면 매핑을 필드 목록 하나에서 파생시켜 손 편집 지점을 1곳으로 줄인다. `_session_scope_where` 는 공개 이름으로 승격하거나 `SessionScope` 에 메서드로 얹는다.
**Risk:** 🟢 (읽기 전용 파생)

---

### BL-532

**Title:** `_sum_decimals` 사본이 `PARITY_DECIMAL_CONTEXT` 밖에서 돈다
**Category:** Refactor / 금융 정확도
**Priority:** P2
**Trigger:** 다음 parity 손질 시
**Est:** XS
**상태:** ⏳ 대기 (트리거 미도래) — \_sum_decimals 사본이 여전히 2벌이고 리포지토리 호출부 4곳(92·159·169·174)은 localcontext(PARITY_DECIMAL_CONTEXT) 밖 그대로다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-29 PR #496 코드리뷰 (Standards 축, 평가자 재현 확인)

**원인 / 영향:** `_sum_decimals` 가 `outcome_parity.py:130` 과 `parity_repository.py:59` 에 **2벌** 있고, 후자의 호출부(`:92, 159, 169, 174`)는 `localcontext(PARITY_DECIMAL_CONTEXT)` **밖**이다. 전자는 모든 산술을 `prec=50` 으로 감싼다.

★**PR #496 이 `gates-and-traps.md` 에 직접 추가한 규칙**("금융 파생 모듈은 `localcontext(Context(prec=50))` 로 감싸라")과 그 PR 자신이 어긋난다. `Numeric(18,8)` 값의 단순 합산이라 실무 위험은 낮지만, 규칙을 세운 PR 이 그 규칙을 안 지키면 다음 사람이 규칙을 안 믿는다.

**권장 접근:** 사본을 지우고 `outcome_parity._sum_decimals` 를 import 하거나, 리포지토리 호출부를 같은 컨텍스트로 감싼다.
**Risk:** 🟢

---

### BL-534

**Title:** 외부 오라클 테스트가 27 leg Decimal 합산을 실제로 실행하지 않는다
**Category:** Test infra / Trading
**Priority:** P2
**Trigger:** parity 산술을 손댈 때
**Est:** XS
**상태:** ⏳ 대기 (트리거 미도래) — 오라클 총계를 관측 1건에 몰고 26건을 0으로 채우는 구조·테스트 이름 모두 그대로다(:47, :54-66). (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-29 PR #496 코드리뷰 (Spec 축)

**원인 / 영향:** `test_outcome_parity.py:55-78` 이 SQL 오라클 **총계를 관측 1건에 통째로 넣고** 나머지 26건을 0 으로 채운다. 총계와 실효 비용률(0.05526%)은 맞지만 **27건 Decimal 합산 자체는 이 오라클이 검증하지 않는다.**

★조인·스코프 정확성은 `test_parity_repository.py` 와 실 DB 대조가 담당하므로 커버는 있다. 다만 이 테스트의 이름(`test_reproduces_sql_oracle_totals...`)이 실제보다 넓은 것을 주장한다.

부수 — 리뷰가 함께 지적한 스코프 이탈 2건은 **의도된 것으로 판단해 기각**한다: (a) 종료 세션 도달 경로(W5)는 화면 검증이 "기능에 도달 불가" 를 잡아 추가한 것으로 dev-log 에 근거가 있다, (b) `/state` 폴링 계약 변경은 신규 표면이 폴링하지 않도록 한 결과이고 핸들러는 무변경이다. 다만 **둘 다 G1 동결 스펙 밖이었다** — 스코프 확장 시 동결 문서를 갱신하는 절차가 없었던 것이 진짜 문제다.

**권장 접근:** 27개 관측에 실제 leg 값을 넣어 합산을 재현하거나, 테스트 이름을 실제 검증 범위에 맞게 좁힌다.
**Risk:** 🟢

---

### BL-541

**Title:** 세션 행이 아예 없는 포지션은 여전히 앱에서 못 닫는다 (웹훅 경로 · 거래소 수동 거래)
**Category:** Backend / trading
**Priority:** P2
**Trigger:** 웹훅으로 포지션을 열기 시작할 때, 또는 `no_owning_session` 이 실제로 관측될 때
**Est:** M
**상태:** ⏳ 대기 (트리거 미도래) — 차단 사유만 있고 원장 귀속 폴백은 미구현(position_service 는 세션 없으면 즉시 no_owning_session), Trigger 관측도 아직 없다 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-29 live-orphan-close (BL-537 재현이 남긴 잔여)

**원인 / 영향:** `Order.strategy_id` 가 `nullable=False` + FK RESTRICT(`models.py:172-178`)라 청산 원장 행에 전략이 반드시 필요하다. 세션에서 그걸 얻으므로 세션 행이 없으면 `no_owning_session` 으로 막힌다(`position_service.py:303`). 해당 클래스는 **웹훅 경로**(`router.py:99-183` 은 `LiveSignalSession` 없이 주문을 낸다)와 거래소에서 직접 연 포지션이다.

★**아직 실측된 적이 없다.** 2026-07-29 재현에서 `no_owning_session` 은 **한 번도 안 났다** — 세션 행은 비활성이어도 영구히 남기 때문이다. 그래서 이번 스프린트에서 **의도적으로 짓지 않았다**(BL-536 이 경고하는 "측정되지 않은 필요 위에 설계" 회피).

**권장 접근:** 실제로 관측되면 착수한다. 그때도 `Order.strategy_id` nullable 화는 금지 — `CumulativeLossEvaluator`(`kill_switch.py:96-105`)가 전략별로 합산하므로 NULL 행은 kill-switch 에 **영구 불가시**가 되고, `order_service.py:161-175` 소유 게이트에 `None` 분기를 뚫어야 한다. 대신 **원장 귀속**(해당 계정·심볼의 `filled` 진입 주문의 distinct `strategy_id` 가 정확히 1개일 때만 채택 — `exit_attribution.py:129-130` 의 보수 규칙)이 마이그레이션 0 이다.
**Risk:** 🟡

---

### BL-538

**Title:** 발산 알림 본문이 **모든 카테고리에 "전략 수정 후 재활성화 필요"** 라고 처방한다 (포지션 불일치엔 틀린 처방)
**Category:** Backend / trading (운영 알림)
**Priority:** P2
**Trigger:** 운영 알림을 사람이 신뢰해야 할 때
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — 메시지가 여전히 stage 분기 없는 단일 f-string 이고 '전략 수정 후 재활성화 필요' 하드코딩, remedy 원소 부재. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-29 PR #497 사후 리뷰 (Spec 축)

**원인 / 영향:** `_alert_live_divergence`(`tasks/live_signal.py`)의 메시지가 단일 f-string 이고 **stage 분기가 없다**:

```
f"{reason}({stage}/{category}) 감지 — 세션을 비활성화했습니다(...). 전략 수정 후 재활성화 필요."
```

`reason` 은 카테고리별로 갈리지만 **처방 문장은 하드코딩**이라, 포지션 계열(`gap_resync_position_mismatch`, `position_direction_mismatch`)에도 "전략을 고쳐라" 가 나간다. 실제 필요한 조치는 **거래소 포지션과 엔진 상태 대조 후 재활성화**다.

★**선재 결함이다** — `gap_resync_position_mismatch` 가 이미 같은 문장을 받고 있었고, PR #497 이 카테고리를 하나 더 추가하면서 노출면이 넓어졌다. #497 은 사유·제목만 정정했다(메타데이터 등재).

**권장 접근:** `_PREFLIGHT_CATEGORY_METADATA` 에 처방(remedy) 원소를 추가하거나 `_alert_live_divergence` 에 kwarg 로 주입한다.
**Risk:** 🟡 (사람이 잘못된 조치를 하게 만든다. 자동 경로 무영향)

---

### BL-540

**Title:** `live_signal.py` 의 반복 3종 — deactivate 의식 6회 · provider+creds 조립 4회 · divergence category 가 맨 `str`
**Category:** Refactor / trading
**Priority:** P3
**Trigger:** 이 파일을 다시 크게 손댈 때
**Est:** M
**상태:** ⏳ 대기 (트리거 미도래) — get_state 는 1회로 줄었으나 deactivate 의식 중복(헬퍼로 쪼갰지만 본문 동일·테스트가 7건 동결)·provider+creds 5곳·category 맨 str 이 그대로다 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-29 PR #497 사후 리뷰 (Standards 축)

**원인 / 영향:**

- **deactivate 의식**(`deactivate` → `commit` → `rows == 1` → sweep → `publish_realtime` → counter → alert)이 한 함수 안에서 **6회** 반복된다. 한 갈래만 고치면 나머지가 조용히 갈린다.
- **provider + credentials 조립**(`BybitFuturesProvider` + `EncryptionService` + `ExchangeAccountService` + `get_credentials_for_order`)이 **4곳**(`:316` `:449` `:1437` `:2155`)에 거의 동일하게 반복된다.
- **divergence category 가 맨 `str | None`** — 합법 집합이 `common/metrics.py` 주석에만 있고 `== "direction"` 리터럴과 metric label 로 재인코딩된다. 이 저장소는 StrEnum-vs-plain-str 로 이미 물렸다(BL-453).
- 같은 tick 에 `sess_repo.get_state(sess.id)` **2회**(발산 판정 · equity curve).

★전부 **선재 패턴**이고 PR #497 이 각각 하나씩 보탰다. 지금 리팩터링하면 diff 가 커져 리뷰가 어려워지므로 분리한다.

**권장 접근:** deactivate 의식을 헬퍼로 접고, category 를 StrEnum 으로 승격하고, `get_state` 를 한 번만 읽어 두 소비처가 공유한다.
**Risk:** 🟢

---

### BL-545

**Title:** ★gap-resync 안전 게이트가 5% 수량 허용치를 물려받아, 구 게이트가 막던 불일치를 통과시킨다
**Category:** Backend / trading (가용성 ↔ 안전 트레이드오프)
**Priority:** P2
**Trigger:** 조건부 진입 세션이 실자금으로 가기 전 / 부분체결이 흔해질 때
**Est:** S
**출처:** 2026-07-30 conditional-entry-alignment codex 적대 리뷰 (P1 제기 → 오케스트레이터가 코드 대조 후 P2 로 강등)
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-10 guards-blind-spots 가 `tol = max(qty_step, larger*0.001)` 로 **구현했다가 되돌렸다**(변이 4/4 red 를 통과했는데도). codex 최종 리뷰가 **P1 2건을 냈고 둘 다 숫자로 재현됐다** — 아래 ★2026-08-10 절이 정본이다. **권장 접근 자체가 불완전하다**: 양자화 오차는 **leg 수**에 비례해 쌓이는데 판정은 순포지션 하나만 받는다. ★단 **「leg 수를 못 구한다」는 거짓이다** — 2026-08-10 review-and-merge 가 `_carried_position_size` 에서 반증했다(아래 절)
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)

**원인 / 영향:** BL-544 가 gap-resync 판정을 `exchange_positions == [] and carried_flat`(무관용)에서
`_classify_position_divergence(carried, exchange) is None`(엔진↔거래소 일치)로 일반화했다. 그런데 그 함수는
같은 방향 크기차가 `_POSITION_SIZE_REL_TOL = 0.05` 이하면 `None` 을 준다(`live_signal.py:227`, `:303`).
따라서 엔진 `0.028` / 거래소 `0.029` 처럼 **실제로 0.001 어긋난 상태가 "일치" 로 통과**한다.
구 게이트는 거래소가 non-empty 이기만 하면 죽였으므로, 이 부류는 **새로 통과하게 된 것**이다.
그리고 이후 정상 tick 의 발산 감지도 `size` 를 **counter 만 올리고 차단하지 않는다**(`:1765-1772`).

★**그 5% 를 그냥 좁히면 안 된다.** 값에 실측 근거가 있다 — 엔진 `position_size` 는 float 누적
(실측 `-0.029910810628287526`)이고 거래소는 step 양자화(실측 `0.029`, BTC linear step 0.001)라
**의도가 같아도 두 값은 절대 같아지지 않는다.** 측정된 양자화 폭 = 3.45%. 좁히면 seed 가 정렬되지
않아 BL-544 자체가 무효가 된다.

★★**2026-08-10 정정 두 건 — 위 문단의 숫자와 근거가 정확하지 않다.**

⑴ **「3.45%」는 관측값이 아니라 상한이다.** `live_signal.py:237` 주석도 같은 수를 적는데,
`:799` 의 식은 `larger = max(|engine|,|exchange|)` 로 나눈다. 실측 쌍
(`-0.029910810628287526` vs `-0.029`)의 **실제 비율은 3.045%** 다
(`0.000910810628287526 / 0.029910810628287526`, python 확인). 3.45% 는 `step / 거래소수량`
(`0.001/0.029`)으로 **코드가 계산하지 않는 양**이다. 둘 다 맞지만 답하는 질문이 다르고,
**좁히기를 제약하는 수는 상한인 0.0345** 다.

⑵ **「좁히면 BL-544 가 무효」는 테스트 근거로는 훨씬 약하다.** 하한을 구속하는 테스트는
**정확히 하나**(`test_live_signal_instrument_parity.py` 의 `test_quantization_is_not_a_divergence`)
이고, BL-544 의 gap-resync 테스트는 전부 engine/exchange 가 **정확히 같다**(`0.029`/`0.029`).
tick-oracle 픽스처 11종도 0~5% 밴드에 하나도 없다 ⇒ `[0.0345, 0.05)` 로 좁히면 **red 0건**이다.
주장은 프로덕션 거동에 대해서는 참이고 「테스트의 벽」으로는 거짓이다.

★★★**⑶ 「size 비례 → step 파생」이라는 권장 접근 자체가 불완전하다. 구현했다가 되돌렸다.**

`tol = max(qty_step, larger * 0.001)` 로 구현했고 표적 변이 **4/4 가 red**(배선 변이 포함)였다.
그런데 codex 최종 적대 리뷰가 **P1 2건**을 냈고 **둘 다 python 으로 재현**됐다:

| 입력                                                      | 종전 축 (5%)             | step 축                   | 무엇이 문제인가          |
| --------------------------------------------------------- | ------------------------ | ------------------------- | ------------------------ |
| pyramiding 10 leg · 엔진 net `5.999108…` / 거래소 `5.990` | tol 0.29996 → **None**   | tol 0.005999 → **`size`** | **정상 세션을 죽인다**   |
| 최소 수량 · 엔진 `0.001` / 거래소 `0.002`(1 lot 차이)     | tol 0.00005 → **`size`** | tol 0.001 → **None**      | **진짜 불일치를 삼킨다** |

⇒ 내 변경은 **아파야 할 곳에서 더 관대해지고, 관대해야 할 곳에서 더 엄격해졌다.**
뿌리는 하나다 — **절삭 오차는 `leg 수 × step` 으로 쌓이는데 `_classify_position_divergence` 가
받는 것은 순포지션 하나뿐이다.** 엔진은 leg 를 절삭하지 않고 거래소는 leg 마다 절삭하므로
(`providers.py:404` `amount_to_precision`), 누적 드리프트는 포지션 크기가 아니라
**체결 횟수**를 따라간다. 순포지션 하나만 보는 어떤 문턱도 두 실패 모드를 동시에 못 막는다.

★★★**2026-08-10 review-and-merge 정정 — 「순포지션이 leg 수를 안 들고 있다」는 판정부에서 거짓이다.**
2축 리뷰 Spec 축이 제기했고 코드로 재현했다. 판정이 쓰는 순포지션을 만드는 것은
`_carried_position_size`(`apps/api/src/tasks/live_signal.py:712-746`)인데, 그 함수는
`open_trades` **리스트를 leg 단위로 순회**하며 leg 마다 `qty` 를 읽어 net 을 누적한다.
⇒ **leg 수도 leg 별 수량도 이미 그 자리에 있다.** 필요한 것은 새 데이터 원천이 아니라
**반환값을 `net` 하나에서 `(net, legs)` 로 넓히는 것**이다 — 「입력 자료의 문제」라는 진단은
맞지만 정확히는 **「자료가 없다」가 아니라 「있는 자료를 버리고 있다」**이다. 비용이 다르다.
★단 **tick 관측부에는 진짜로 없다** — `live_signal.py:925-938` 이 다루는 `position_size` 는
스칼라다. **두 자리를 섞지 마라.**
★**되돌림 커밋(`e17a082c`)의 인용 2건이 모두 빗나갔다** — `strategy_state.py:861` 은 [BL-104]
pyramiding cap 주석이고, `providers.py:403` 은 `load_markets()` 다(절삭은 `:404`).
엔진 무절삭의 근거는 특정 줄이 아니라 **파일 1,321행 전체에 `amount_to_precision`·`quantize`
호출이 0건**이라는 사실이다(2026-08-10 실측). **근거를 줄 번호로 적을 때 그 줄을 열어 봐라.**

★**되돌린 이유** — 첫 행은 `gap_resync_position_mismatch` 사망 경로이고, 그것은 역대 실격
11건 중 **2건**의 라벨이다. 소크가 도는 중에 사망률을 올릴 수 있는 변경을 넣지 않는다.

**다음 착수자에게** — 후보는 「leg 별 거래소 정밀도로 정규화한 기대 순포지션과 비교」다
(codex 처방). 그러려면 판정이 순포지션이 아니라 **leg 목록**을 받아야 하므로
`_classify_position_divergence` 의 시그니처 문제가 아니라 **입력 자료의 문제**다.
★**그리고 그 자료는 이미 있다**(위 2026-08-10 정정) — 착수 지점은
`_carried_position_size` 의 반환을 `(net, legs)` 로 넓히는 것이고, 그 함수는 이미 leg 를 돈다.
**「원리상 불가능」으로 읽고 포기하지 마라.**
되돌린 구현·테스트·변이 하네스는 git history 에 있다(`3cc33b75`·`dca6b11a` 와 그 revert).

**권장 접근:** 상대 허용치를 **거래소 수량 step 에서 파생**시켜라 —
`tol = max(qty_step, size * rel_tol_small)` 같은 형태. step 은 `_reconcile_conditional_entries` 가
이미 `market["precision"]["amount"]` 로 가져온다(`live_signal.py:638`). 그러면 "양자화 1틱" 은
통과하고 "부분체결 잔량" 은 통과하지 못한다. 대안: gap-resync 에만 더 좁은 별도 문턱을 두고
정상 tick 의 관측용 문턱과 분리한다.

**2026-08-08 실측.** `size` 발산은 `14:17:49.558` ~ `15:08:49.945` 동안 **51분 연속 52건**
발화했지만 게이트 C3 실격 목록에는 **0건**이었다 — `size` 는 실격 라벨이 아니다.

그 52건의 `exchange_position` 은 엔진 값의 정수배였다 — `0.087 = 0.029 × 3` ·
`-0.145 = -0.029 × 5`. 이 계열은 「양자화 1틱」도 「부분체결 잔량」도 아니고, 다른 호스트의
포지션이 같은 계정에 얹힌 것이다. 근인은 BL-634 로 등재했다.

따라서 이 BL 의 문턱 설계는 그대로 유효하다. 다만 `size` 를 관측 전용으로 두는 정책 자체가
별도 질문이며, 이번 회차는 그 수리를 하지 않았다.

**Risk:** 🟡 (통과한 불일치는 다음 주문이 그 위에 얹히지만, 5% 이내라 규모는 제한적)

---

### BL-546

**Title:** 원장→엔진 seed 경계에서 `Decimal` 수량·가격이 `float` 로 강등된다 (Decimal-first 하드 규칙 위반)
**Category:** Backend / pine_v2 · trading 경계
**Priority:** P2
**Trigger:** 엔진 내부 수치 표현을 손댈 때 / 큰 notional 을 다룰 때
**Est:** M (엔진 전반이 float 기반이라 국소 수정으로 안 끝난다)
**상태:** ⏳ 대기 (트리거 미도래) — seed 경로가 여전히 float(fill.filled_quantity/price) 로 강등하고, Trade.qty 도 float이며 dust 상한을 고정하는 테스트가 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-30 conditional-entry-alignment codex 적대 리뷰 (확정)

**원인 / 영향:** DB `Numeric(18,8)` 인 `filled_quantity`/`filled_price` 가 seed 경로에서 `float` 로
변환된다(`live_signal.py` seed leg 조립 · `strategy_state.py` `Trade.qty: float`). 예:
`9999999999.99999999` 는 float 왕복 뒤 `10000000000.0`. seed 포지션의 수량·진입가·증거금 계산에
반올림값이 들어간다. `AGENTS.md` 와 `apps/api/AGENTS.md` §2 의 "금융 숫자는 Decimal,
float 금지" 를 형식상 위반한다.

★**이 변경이 새로 만든 문제는 아니다** — `StrategyState` 는 원래 float 기반이고(`Trade.qty: float`),
`run_live` 의 모든 수치 입력이 이미 float 다. seed 는 **새 변환 지점을 하나 더 만들었을 뿐**이다.
그래서 국소 수정이 아니라 엔진 수치 표현 결정 사안이다.

**권장 접근:** (a) 엔진 경계에 변환 지점을 한 곳으로 모으고 그 자리에 정밀도 손실 상한을 단언한다,
또는 (b) `StrategyState` 의 금액·수량을 `Decimal` 로 올린다(대공사 — 별도 스파이크로 크기부터 재라).
현실적 1차: **BTC 급 수량·가격 범위에서 float 왕복 오차가 `_POSITION_DUST`(1e-8) 아래임을 테스트로
고정**하고, 그 가정이 깨지는 심볼(고가·고정밀)에서 경고하게 한다.
**Risk:** 🟢 (현재 취급 범위에서는 오차가 dust 아래일 가능성이 높다 — 단 측정된 적 없다)

---

### BL-550

**Title:** (P3) 비활성 세션의 **세션별** 포지션 대조가 화면에 없다 (계정 스코프 표로만 보인다)
**Category:** Frontend / live-sessions
**Priority:** P3
**Trigger:** 죽은 세션의 포지션을 세션 단위로 대조해야 할 때
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — OpenPositionsTable 은 여전히 is_active 필터된 activeSessions 만 받는다 — 비활성 세션 per-session 대조 UI 미구현. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-30 conditional-entry-alignment (BL-423 잔여 중 의도적 defer)

**원인 / 영향:** `OpenPositionsTable`(`trading-cockpit.tsx:342`)은 `activeSessions` 만 받는다.
BE `GET /live-sessions/{id}/positions` 는 비활성 세션에도 200 을 주지만 FE 가 부르지 않는다.

★**의도적으로 미루었다** — 계정 스코프 표(`AccountPositionsTable`)가 이미 고아 포지션을 보여주고
청산까지 되며(2026-07-29 BL-537 실측), 비활성 세션마다 per-row 쿼리를 붙이면 폴링 비용이 붙는다.
**Risk:** 🟢

---

### BL-553

> ### ⏳ **유지 (2026-07-30 close-mismatch-soak) — ★사전조건이 불완전했음이 밝혀졌다**
>
> **공백 33분 03초**(`18:35:03Z` → `19:08:06Z`)를 **장전된 상태에서** 열었다
> (armed=1, `buy 0.087 @ 64795.6`). 즉 직전 회차가 지정한 사전조건을 **충족했다.**
> 그런데 `applied` 는 **또 미발화**했고 `already_open` 이 +1(1.0 → 2.0) 됐다.
> 누적 **62분57초 + 33분03초 = 96분에서 0회.**
>
> ★★**"장전" 만으로는 부족하다.** `already_open` 은 **엔진 원장에 이미 열린 트레이드가 있어
> seed 가 불필요했다**는 뜻이다. `applied` 에 도달하려면 **장전 + 엔진 flat** 이어야 한다 —
> 공백 중 트리거가 체결돼 **엔진이 모르는 포지션이 생겨야** seed 가 의미를 갖는다.
>
> ★**그리고 그것이 PbR 로는 구조적으로 어렵다.** `s1_pbr` 은 stop-and-reverse 라 거의 항상
> 포지션을 들고 있다(flat 구간이 사실상 없다). **5회 연속 미발화의 이유가 이것으로 설명된다.**
>
> **다음 회차 설계:** 전략을 바꿔라. `strategy.close` 로 **flat 으로 돌아가는 구간이 있는 전략**
> (예: `s4_hma_curvature`)에서, flat + 장전 상태를 확인한 뒤 공백을 연다.
> ★**PbR 로 재시도하지 마라 — 같은 0 을 6번째로 얻는다.**

<details><summary>이전 판정 (2026-07-30 live-entry-completeness)</summary>

> ### ⏳ **유지 — 단 이유가 정확해졌다**
>
> 이번 soak 공백 2회(16분35초 + 18분22초, 누적 34분57초)에서도 `applied` **미발화**.
> 직전 28분 + 이번 34분57초 = **누적 62분57초에서 0회**.
>
> ★★**그런데 "시장이 안 움직였다" 가 아니다.** 대기 stop 이 **실제로 트리거됐고, 하필 공백 밖
> (leg 3)에서** 일어났다 — 화면의 진입가 **64609.1** = 공백 2 의 `trig=64610`.
> 공백 중 거래소를 외부 raw HMAC 오라클로 **5회** 찍어 내내 `Untriggered` 임을 실측했다.
>
> → **다음 회차 설계:** 공백을 **30분+** 로 가져가면 트리거가 공백 안에 들어올 확률이 오른다.
> 확인 신호에서 **구조화 로그의 `trade_ids` 는 빼라** — 포매터가 `extra` 를 렌더하지 않아
> 관측 불가다(정본이 이미 경고). metric `{outcome="applied"}` + 엔진 `open_trades` 변화로 본다.

</details>

**Title:** ★`outcome="applied"`(원장 seed **주입**)가 실주행에서 한 번도 밟히지 않았다 — 단위테스트로만 증명됨
**Category:** Backend / trading 검증 공백
**Priority:** P2
**Trigger:** 다음 soak / 조건부 진입 전략을 오래 굴릴 때 (기회주의적 확인)
**Est:** XS (검증만 — 코드 변경 없음)
**상태:** ⏳ 대기 (트리거 미도래) — 코드 변경 없는 실주행 관측 항목 — 계측은 그대로 있고 관측된 outcome 은 no_basis 뿐, applied>0 근거 0건. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 소크 창 미완(soak-gate rc=2 · C1 46.24h/168h). PASS 만 도래다([ADR-024]) (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-30 conditional-entry-alignment soak 3 leg

**원인 / 영향:** BL-544 의 핵심 기전은 둘이다 — (1) **판정 완화**(엔진↔거래소 순포지션 일치) (2) **원장 seed 주입**. soak 3 leg 이 3/3 생존했지만 **세 번 다 (1) 로 살았다** — 재생이 포지션을 스스로 재현해 seed 가 생략됐다(`already_open` / `no_basis` / `inadmissible`). `applied` 를 밟으려면 **대기 조건부 주문이 공백 중에 트리거**돼야 하는데 누적 공백 ~28분 동안 일어나지 않았다(시장 변동 의존이라 강제할 수 없다).

★따라서 현재 증거 수준은 **비대칭**이다 — 판정 완화 = 실주행 실증 / seed 주입 = 단위테스트 + 표적 변이(멱등·마지막 bar Pine 가시성·기본값 report dict 불변)까지. 원래 BL-544 실패(2026-07-29)가 정확히 seed 주입이 필요한 케이스였으므로 이 공백은 실질적이다.

**권장 접근:** 코드 변경 없음. 다음 soak 에서 (a) 공백을 **더 길게**(15분+) 가져가 대기 stop 이 트리거될 확률을 올리거나, (b) 변동성이 큰 구간을 골라 재현한다. 확인 신호는 `qb_live_gap_ledger_seed_total{outcome="applied"} > 0` + 구조화 로그 `live_signal_gap_ledger_seed` 의 `trade_ids` 비어 있지 않음. **관측되면 이 BL 을 닫고 BL-544 의 검증을 완성으로 표기한다.**
**Risk:** 🟡 (기전이 틀렸다는 증거는 없다 — 다만 실주행 증거가 없다)

---

### BL-557

**Title:** (P3) `qb_active_orders` 게이지가 **음수(-2.0)** 로 표류 — inc 1곳 / dec 약 18곳
**Category:** Backend / 계측
**Priority:** P3
**Trigger:** 그 게이지로 무언가를 판단하기 전
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — Gauge 그대로이고 inc 1곳(order_service:457) vs dec 17곳 비대칭 유지 — created/terminal Counter도 terminal 단일 훅도 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-30 live-entry-completeness (기존 BL 의 새 증거)

**원인 / 영향:** 이미 등재된 "inc/dec 계약이 multiprocess 에서 절대값을 보장하지 못한다" 의
**새 증거 2건**이다. (a) 직전 회차는 "0 인데 실제 1"(양의 편향)이었는데 이번엔 **음수 -2.0** —
편향이 양방향이다. (b) ★**구조적 비대칭** — `inc` 지점은 **1 곳**(`order_service.py:432`),
`dec` 지점은 **약 18 곳**(`tasks/trading.py` 8 · `tasks/live_signal.py` 3 ·
`conditional_entry_janitor.py` 3 · `websocket/{reconciliation,state_handler}.py` 2 · `router.py` 1 …).
1:18 이면 어느 dec 하나가 중복 발화해도 음수로 샌다.

**권장 접근:** dec 를 단일 지점(terminal 전이 훅)으로 모으거나, Gauge 를 버리고
`created - terminal` 두 Counter 의 차분으로 렌더한다. **음수는 그 자체로 계약 위반 신호다.**
**Risk:** 🟢 (관측 왜곡. 머니-패스 영향은 없다)

---

### BL-558

**Title:** retCode 를 `error_message` 에 싣는 경로가 **동기 1곳뿐** — 비동기 확정 거절이 코드 미상이 된다
**Category:** Backend / trading (계측 타당성)
**Priority:** P2
**Trigger:** 거절 코드로 채널을 가를 때
**Est:** M
**상태:** ⏳ 대기 (트리거 미도래) — 구조화 코드 컬럼이 없고(models.py 에 error_message 문자열뿐), WS·submission 경로는 여전히 평문이라 retCode 정규식 파싱에 의존한다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-30 live-entry-completeness (적대 검증 렌즈1)

**원인 / 영향:** retCode JSON 을 원문에 싣는 것은 동기 `provider_failure: {ccxt}`
(`tasks/trading.py:432`) **하나뿐**이다. WS(`state_handler.py:241` `ws_rejected: <rejectReason>`) ·
reconciler(`reconciliation.py:240`) · janitor(`conditional_entry_janitor.py`) ·
sweep(`live_signal.py:2480`) · `exchange_rejected_at_submission`(`trading.py:549`) 는 전부 **평문**이라
`110092`/`110093` 같은 코드가 **복원 불가**다. 즉 비동기로 확정된 거절은 진입 완결성 도구에서
**"코드 미상"** 으로 떨어진다.

★**이번 측정의 알려진 한계**이고 도구 출력에 그렇게 명시돼 있다
(_"`unparsed` 는 '거절 아님' 이 아니다"_).

**권장 접근:** 거절 확정 경로 전부가 **구조화된 코드 필드**를 남기게 한다.
`error_message` 문자열 파싱에 의존하는 설계 자체가 취약하다 — 별 컬럼이면 마이그레이션 1이다.
**Risk:** 🟡 (채널 분해의 분자를 과소·오분류한다)

---

### BL-565

**우선순위:** P2
**카테고리:** Backend / trading (라이브 청산 정합성)
**Trigger:** `strategy.exit` 을 쓰는 전략을 라이브로 돌리기 **전**
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)** — 2026-07-31 reversal-ledger-sync 에서 BL-560 을 고치며 **읽기만** 하고
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
범위 밖으로 남긴 항목. 코드 수정 0.
**출처:** 2026-07-31 reversal-ledger-sync (BL-560 4단계 판단)

★**거래소 bracket 이 이미 체결한 청산을 엔진이 또 보낸다 — BL-560 과 같은 모양이다.**

**원인/영향.** BL-560 은 `check_pending_fills` 의 close leg 가 broker 소유임을 확정하고 고쳤다.
`check_exit_fills` 는 **같은 성질인데 손대지 않았다**:

- `strategy_state.py:1068` — TP/SL/트레일링 leg 가 체결되면 `self.close(entry_id, ...)` 를
  **표시 없이** 부른다 → `action="close"` 이벤트 → `event_loop.py:513` 필터를 그대로 통과 →
  `live_signal.dispatch_event` 가 `reduce_only=True` 시장가 청산을 발주한다.
- 그런데 그 TP/SL 은 **거래소에 이미 걸려 있다.** 진입 주문이 `take_profit`/`stop_loss` 를
  실어 보내 Bybit 포지션 bracket(거래소-네이티브 OCO)이 되고(`tasks/live_signal.py:2865-2866`,
  부착 여부는 `:1389` `bracket_attached` 로 계측), 트레일링은 체결 후
  `set_trading_stop` 으로 따로 등재된다(`:2867-2871`).
- ⇒ 거래소가 먼저 청산해 **flat** 이 된 뒤 엔진이 다음 봉에서 그 체결을 재도출하고 청산 주문을
  또 낸다. 결과는 `110017 current position is zero` — BL-560 이 셌던 표의 **"무해" 30건 갈래**다.

**★단 무해가 보장되지는 않는다.** 같은 봉에서 전략이 재진입하면 그 사이 포지션이 반대편으로
차 있어 `same side` 가 된다 — BL-560 과 같은 위험 갈래로 넘어간다.

**★아직 실측되지 않았다 — 크기를 모른다.** 2026-07-30 soak 창의 전략(PbR)은 `strategy.exit` 을
쓰지 않아 `pending_exits` 가 비어 있고, `check_exit_fills` 는 그때 **즉시 return** 했다
(`strategy_state.py:1042`). 즉 그 창의 `position_zero` 0건은 **이 경로의 반증이 아니다.**
BL-563 이 같은 조건을 다른 각도에서 이미 경고하고 있다("`strategy.exit` 을 쓰는 전략이
등장하는 순간 이 숫자는 못 믿는다").

**권장 접근:** BL-560 과 같은 자리·같은 수단이다 — `check_exit_fills` 의 `close` 를
`broker_filled=True` 로 표시하면 dispatch 에서 빠진다(필드와 필터는 이미 있다).
★**단 먼저 재라.** BL-560 에서 배운 대로 bracket 부착이 **실제로** 되고 있는지가 전제인데
(`bracket_attached` 비율), 지금 그 counter 는 BL-563 의 귀속 오류를 안고 있다.
**BL-563 → 실측 → 이 항목** 순서를 지켜라. `strategy.exit` 전략 없이 고치면 검증 불가능한
수정이 된다.

★**`check_liquidations`(`strategy_state.py:901-`)는 다르다.** 그쪽 close 는 계속 dispatch 돼야
한다 — 엔진의 격리 청산가 모델은 **근사**이고 거래소가 실제로 청산했다는 보장이 없다.
`test_run_live.py:610` 이 그 계약을 이미 고정하고 있다. 같이 묶지 마라.

**Risk:** 🟡 (현재 관측 갈래는 무해하나 재진입이 겹치면 BL-560 과 동급)

---

### BL-567

**우선순위:** P2
**카테고리:** Backend / trading (체결 후속 훅 회수)
**Trigger:** 트레일링을 쓰는 전략을 라이브로 상시 운용하기 **전**, 또는
`terminal_hook_trailing_failed` counter 가 1건이라도 발화할 때
**상태:** ⏳ **대기 (트리거 미도래)** — 2026-07-31 reversal-ledger-sync 에서 **한계로 명시하고 남긴 것**.
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-31 reversal-ledger-sync (codex 3차 리뷰 [3] 후속)

★**`place_trailing_stop` enqueue 가 실패하면 그 주문의 트레일링은 영구 유실이다.**

**원인/영향.** BL-560 write-back 은 후속 훅 실패를 전이 성공과 분리해 삼킨다
(`tasks/live_signal.py:790-816`). **세 훅의 회수 범위가 갈린다**:

| 훅                                      | enqueue 실패 시 회수                                                                             |
| --------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `_enqueue_closed_pnl_refresh`           | ✅ `trading.sweep_closed_pnl` 비트(`celery_app.py:141`)가 backfill                               |
| `_enqueue_conditional_reversal_measure` | 🟡 불필요 — 크기 분포 프로브라 1건 유실이 판정을 안 뒤집는다 (BL-562 가 이미 at-least-once 수용) |
| `_enqueue_trailing_if_intended`         | ❌ **없다**                                                                                      |

`place_trailing_stop_task` 는 `_enqueue_trailing_if_intended`(`tasks/trading.py:1141-1152`)
**한 곳에서만** 예약되고, 그 시점엔 행이 이미 `filled` 이라 다른 terminal 경로도 다시
오지 않는다. 결과 = **의도한 트레일링이 없는 채로 포지션이 열려 있다**(무방비).

★**삼키는 선택 자체는 옳다.** 삼키지 않아도 트레일링은 똑같이 유실되고, 거기에 더해
호출자의 전역 catch 가 그 tick 의 취소 루프까지 날린다. 삼키는 쪽이 순수하게 낫다.
문제는 **회수 경로가 없다**는 것이지 삼킨 것이 아니다.

★**이 한계는 write-back 이 만든 것이 아니다** — 같은 훅을 쓰는 기존 3 사이트
(`tasks/trading.py:526,867` · `conditional_entry_janitor.py:154`)도 동일하다. write-back 이
그 사실을 counter 로 **보이게** 만들었을 뿐이다.

**권장 접근:** `sweep_closed_pnl` 과 같은 모양의 비트 스윕 — `filled` + `trailing_stop IS NOT NULL`

- 포지션이 아직 열려 있는데 거래소에 트레일링이 없는 주문을 찾아 재예약한다.
  ★**먼저 재라.** `terminal_hook_trailing_failed` 가 실제로 발화하는지 모른다(구조적 가능성만
  확인했다). 발화 0 이면 이 항목은 비용 대비 가치가 없다 — BL-560 이 두 번 밟은 함정이다.

**Risk:** 🟡 (트레일링 미부착 = 무방비 포지션. 단 발생률 미측정)

---

### BL-568

**우선순위:** P2
**카테고리:** Backend / trading (조건부 진입 반전 계측)
**Trigger:** BL-562 의 **체결시점** 반전 분포를 근거로 무언가를 판단하기 전
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-01 ledgerhygiene 에서 실측. 아직 원인 미측정.
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-01 ledgerhygiene (BL-562 착지 후 첫 실측)

★**BL-562 의 체결시점 반전 계측이 11건 중 10건을 못 쟀다 — 분류된 건이 0 이다.**

**원인/영향.** 메인 스택 worker 의 prometheus multiproc 레지스트리를 그대로 읽었다:

```
qb_live_conditional_reversal_filled_total{bucket="unmeasured_position_predates_order"}  10
qb_live_conditional_reversal_filled_total{bucket="not_reversal"}                         1
(그 외 버킷 = 없음)                                                                       0
```

같은 창의 **등재 시점** 축은 `qb_live_conditional_reversal_total{bucket="1x"} = 27` 로 살아 있다.
즉 축 자체는 돌지만 **체결시점 축만 91%(10/11)가 `unmeasured` 로 떨어진다.**
BL-562 는 "증명하지 못하면 버킷에 넣지 않는다" 를 원칙으로 삼았고 그 원칙은 옳다 —
문제는 **그 결과 남는 신호가 사실상 없다**는 것이다. 지금 이 counter 로는 반전이
일어나는지 아닌지를 말할 수 없다.

`unmeasured_position_predates_order` 는 `_reversal_bucket_at_fill`
(`apps/api/src/tasks/trading.py:1595`) 의 마지막 분기다 — 같은 방향 + `size < filled_quantity`
까지 온 뒤 `created_at < submitted_at - 2s` 면 여기로 떨어진다.

**[가정] anchor 가 구조적으로 뒤진다는 후보 1.** `position.created_at` 은
`_parse_position_created_at`(`apps/api/src/trading/providers.py:271-278`)이 Bybit raw
`info.createdTime` 에서 채우고, 그 주석이 **「최초 포지션 생성 시각 (ADD 시 불변)」** 이라고
못박는다. 포지션이 flat 을 거치지 않고 살아 있는 한 `created_at` 은 계속 최초 개시 시각이므로,
**나중에 등재된 조건부 주문의 `submitted_at` 보다 항상 앞선다.** 조건부 주문은 등재 후
트리거까지 대기하므로 이 시차는 분 단위로 벌어진다. ★단 이건 코드 대조로 세운 가설이고
**실측되지 않았다.**

★**먼저 재라 — 왜 anchor 가 항상 뒤지는가.** 10건 각각에 대해 `submitted_at` ·
`position.created_at` · `filled_quantity` · `position.size` 를 함께 남기고 차이를 봐라.
가설이 맞다면 `created_at` 이 **모든 건에서 동일한 한 시각**(그 포지션의 최초 개시)으로
수렴한다 — 그게 판별식이다. ★★**코드 대조로 뿌리를 정하지 마라** — BL-560 이 정확히 그렇게
두 번 틀렸다(2026-07-31 실주행이 코드 대조 가설을 반증).

**권장 접근:** 원인이 측정된 뒤에 고른다. anchor 후보는 최소 3개이고 셋 다 대가가 다르다 —
(a) 거래소 체결 시각 소싱(BL-375 와 같은 뿌리, 가장 비싸고 가장 정확),
(b) 주문 등재 시점의 포지션 스냅샷을 함께 저장해 delta 로 판정(계측 전용 경로에 쓰기가 생긴다),
(c) `created_at` 대신 포지션 `updatedTime` 을 보조 축으로(★BL-372 가 정확히 그 이유로
`timestamp` 를 버렸다 — same-side ADD 를 reopen 으로 오탐한다. **같은 함정을 반대편에서
다시 밟는 선택지다**).

★**계측 전용이라는 성질은 지켜라.** 이 경로는 주문을 내지 않고 행을 쓰지 않는다
(`trading.py:1610-1613`). 원인을 고치려고 여기에 쓰기를 넣으면 계측기가 머니-패스가 된다.

**Risk:** 🟢 (계측 전용 — 잘못된 값이 주문으로 이어지지 않는다. 단 BL-562 의 판정 근거가 비어 있다)

---

### BL-573

**우선순위:** P3
**카테고리:** Backend / trading (라이브 tick 중복 조회)
**Trigger:** `live_signal` tick 비용을 손댈 때, 또는 발산 감지와 reconcile 을 한 자리로 합칠 때
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-01 codex 적대 리뷰 #1 (CONTROL 코드 대조로 확인).
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-01 soak 후속 codex 리뷰

★**`engine_only` tick 마다 `list_resting_conditional_entries` 가 두 번 돈다 — 결과 공유가 구조적으로 불가능하다.**

**원인/영향.** 두 호출부가 `apps/api/src/tasks/live_signal.py:639`(발산 감지)와 `:946`(reconcile)에 있다.
**발산 감지가 reconcile 보다 앞서 돈다.** 그래서 뒤쪽이 앞쪽 결과를 물려받을 수 없고,
앞쪽이 뒤쪽을 위해 캐시하려면 tick 수명 동안 값을 들고 다녀야 한다 — 지금 구조로는 그 자리가 없다.

비용은 **인덱스 SELECT 1회/틱**이다(같은 `strategy_id` + `exchange_account_id` 조건,
`order_repository.py:267-281`). 작다. **P3 인 이유가 그것이다** — 정합성 문제가 아니라 중복이다.

★**좌표 주의.** 위 줄번호는 **메인/스테이지 기준**이다. `wt/ledgerhygiene` 워크트리에는
이 두 호출부가 아직 없다(`list_resting_conditional_entries` 가 `live_signal.py:880` 한 곳뿐).
발산 감지 경로는 W1 `divsplit` 작업이 들여온 것이다 — 브랜치를 확인하고 grep 해라.

**권장 접근:** 합치려면 **호출 순서를 먼저 정하라.** 발산 감지를 reconcile 뒤로 옮기면 공유가
가능해지지만, 그러면 감지가 reconcile 이 만든 상태를 보게 되어 **무엇을 재는지가 바뀐다.**
★**비용이 SELECT 1회이므로, 순서를 바꿔서까지 합칠 값어치가 있는지부터 판단해라.**
[BL-576](#bl-576) 과 같은 자리를 건드리므로 함께 보는 편이 싸다.

**Risk:** 🟢 (중복 읽기. 정합성 영향 없음)

---

### BL-574

**우선순위:** P2
**카테고리:** Backend / trading (조회 절단이 분류를 뒤집는다)
**Trigger:** 한 (strategy, account) 의 **동시 resting 이 20건을 넘긴 날**이 관측될 때 (아래 쿼리). 또는 `awaiting_trigger` / `unexplained` 분해를 근거로 쓰기 **전**
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래) — 크기 측정 완료, 수리는 의도적으로 보류.** 2026-08-02 divergence-label-split.
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-01 soak 후속 codex 리뷰

★**`LIMIT 100` 이 세션 필터보다 앞서 걸려, 현 세션의 resting 주문을 놓치고 `awaiting_trigger` 를 `unexplained` 로 오분류한다.**

**원인/영향.** `order_repository.py:267-281` 의 조회는 **세션으로 필터하지 않는다** —
`state IN (pending, submitted)` + `trigger_price IS NOT NULL` + `reduce_only = false` +
`strategy_id` + `exchange_account_id` 로만 좁히고, `submitted_at ASC` 정렬에
**`.limit(100)`(`:279`)** 을 건다. 세션 스코프는 **호출부에서 사후에** 적용된다.

⇒ 같은 전략·계정에 **다른 세션의 미종결 조건부 주문 100건이 더 오래된 `submitted_at` 으로
앞서 있으면**, 현 세션의 resting 주문이 SQL 단계에서 잘려 나간다. 호출부는 "이 세션에 대기 중인
조건부 진입이 없다" 고 읽고, 그 tick 의 `engine_only` 를 **`awaiting_trigger` 가 아니라
`unexplained` 로 분류**한다.

★**이것이 [BL-566](#bl-566) 재판정의 20/9 분해를 직접 건드린다.** 편향 방향은 다행히
**보수적**이다 — 놓치면 `unexplained` 쪽으로 떨어지므로 "설명된 비율" 을 **과소** 평가한다.
즉 재판정의 69%는 하한이다. 그래도 **분류 근거가 조회 절단에 의존한다는 사실 자체가 결함**이고,
세션이 쌓이면 임계를 넘는 날이 온다.

### ★크기 측정 완료 (2026-08-02, divergence-label-split) — **수리는 값어치 근거로 보류**

~~★**아직 실측되지 않았다**~~ → **쟀다. 그리고 재는 축이 틀려 있었다.**

★★**`LIMIT 100` 은 달력일이 아니라 「동시각 resting」에 걸린다.** 그전에 인용되던
「(strategy, day) 당 최대 75건」은 **일별 생성 수**라 이 술어의 축이 아니다.

| 축                             | 값                                                                       |
| ------------------------------ | ------------------------------------------------------------------------ |
| 조건부 파이프라인 총량         | **264** = `cond` **255** + `condmkt` **9** — 전건 terminal               |
| 일별 생성                      | 07-28 **81** · 07-30 **59** · 07-31 **50** · 07-29 **43** · 07-27 **31** |
| ★**동시 미종결(resting) 최대** | **2** (per strategy+account) — 독립 4방법 일치                           |
| 날짜를 넘긴 미종결             | UTC **0** / **KST 2** ★타임존 의존                                       |

★**총량 술어 주의** — `trigger_price IS NOT NULL` 로 세면 **`condmkt` 9건이 통째로 빠진다**
(시장가 전환 주문은 정의상 `trigger_price` 가 NULL). 정본은 `idempotency_key` 의 kind 세그먼트다
(`entry_completeness.py` 의 `label="조건부 진입 (우리 cond/condmkt key 만)"`).
**이 함정은 2회차 연속 밟혔다.**

⇒ **`LIMIT 100` 이 절단한 적은 없다.** 단 여유는 「75 대 100」이 아니라 **「2 대 100」**이고,
★**그 2 는 부하 여유가 아니라 이 전략의 진입 신호 수(2종)가 만든 상한**이라 다른 전략으로 외삽할 근거가 없다.

**판단: 선제 경화를 지금 하지 않는다.** 실측 상한이 한계의 **2%** 라 `limit + 1` 절단 감지의
기대 이득이 없다. **되살릴 조건 = 아래 Trigger** — 한 (strategy, account) 의 동시 resting 이
**20건(한계의 20%)을 넘기면**(= 21 이상) 그때 경화한다.

```bash
docker exec quantbridge-db psql -U quantbridge -d quantbridge -At -F'|' -c "
WITH scoped AS (
  SELECT strategy_id, exchange_account_id, created_at,
         COALESCE(filled_at, now()) AS closed_at
    FROM trading.orders
   WHERE trigger_price IS NOT NULL AND reduce_only = false
     AND COALESCE(filled_at, now()) >= now() - interval '7 days'
), ev AS (
  SELECT strategy_id, exchange_account_id, created_at AS ts,  1 AS d FROM scoped
  UNION ALL
  SELECT strategy_id, exchange_account_id, closed_at  AS ts, -1 AS d FROM scoped
), r AS (
  SELECT strategy_id, exchange_account_id,
         sum(d) OVER (PARTITION BY strategy_id, exchange_account_id ORDER BY ts, d DESC
                      ROWS UNBOUNDED PRECEDING) AS run
    FROM ev)
SELECT strategy_id, exchange_account_id, max(run) FROM r GROUP BY 1,2 HAVING max(run) > 20"
```

★★**창 필터를 `created_at` 이 아니라 `closed_at` 에 건다** (2026-08-02 codex MAJOR#2 정정).
`created_at >= now()-7d` 로 거르면 **창 시작 전에 열려 창 안에도 살아 있던 주문(carry-in)이 통째로
빠져** 재고가 0 에서 시작한다. 술어의 실제 대상은 `pending`/`submitted` 상태의 지속이지 생성 시각이 아니다.
★**`>= 20` 이 아니라 `> 20`** — 문장이 「넘긴」이므로 20 은 발화하지 않는다(codex MINOR#3).

**2026-08-02 실행 결과 = 0행 (보류 유지).** ★판별력 확인 = 같은 쿼리의 `HAVING max(run) > 1` 이
`(전략 07a22564, 계정 19a8166a, max 2)` 를 돌려준다 — **창이 비어서 0행인 게 아니다.**

★**여기서는 `trigger_price IS NOT NULL` 이 옳다** — 이 술어가 재는 것은 `list_resting_conditional_entries`
가 실제로 거는 조건이고, 그 조회 자체가 같은 필터를 쓴다(`order_repository.py:275`). **총량을 셀 때와
절단 위험을 잴 때의 정본 술어가 다르다** — 이 구분이 위 함정의 반대편이다.

**권장 접근(되살릴 때):** 세션 술어를 **SQL 안으로** 내린다(`SessionScope` 관용구가 이미 있다).
그게 어려우면 최소한 **절단을 감지**해라 — `limit + 1` 로 가져와 `len(rows) > limit` 이면
분류를 `unexplained` 가 아니라 **`unmeasured_truncated`** 로 떨어뜨린다. ★후자가 이 레포의 기존
관용구다(`list_fills_since` 가 정확히 그렇게 한다, `order_repository.py:400-418`).
**모르는 것을 아는 것처럼 분류하지 마라** — BL-562 가 세운 규칙과 같다.

**Risk:** 🟢 (실측 상한이 한계의 2%. 단 그 분류가 [BL-566](#bl-566) 판정의 근거였으므로 Trigger 는 유지)

---

### BL-575

**우선순위:** P2
**카테고리:** Backend / trading (실패 후 세션 재사용 — fail-open 계약)
**Trigger:** 「발산 감지는 세션을 죽이지 않는다」를 근거로 쓰기 전, 또는 그 tick 의 DB 실패를 조사할 때
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-01 codex 적대 리뷰 #5. ★**선재 패턴이고 회귀가 아니다.**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-01 soak 후속 codex 리뷰

★**SELECT 가 실패하면 같은 `AsyncSession` 을 rollback/savepoint 없이 계속 쓴다 — aborted transaction 이면 「fail-open · 세션을 죽이지 않는다」 계약이 깨진다.**

**원인/영향.** 발산 감지의 `except Exception` 은 예외를 삼키고 경고만 남긴다
(`live_signal.py:637-645` 근방). 하지만 `session` 을 rollback 하지 않는다. 실패가 asyncpg
트랜잭션을 **abort 시키는 종류**라면 그 tick 의 이후 DB 작업이 **줄줄이 실패**한다.
즉 이 `except` 가 막는 것은 **이 함수가 예외를 위로 던지는 것**뿐이고, 계약이 약속한
"세션이 안 죽는다" 는 여기서 보장되지 않는다.

★**코드가 이미 이 한계를 스스로 적어 놓았다** — `live_signal.py:630-634` 의 docstring 이
_"`session` 을 rollback 하지 않으므로 … 같은 tick 의 이후 DB 작업이 이어서 실패한다.
즉 '세션이 안 죽는다' 를 여기서 보장하지는 못한다"_ 라고 명시한다. **결함을 숨긴 코드가 아니라
정직하게 적어 두고 남긴 것**이다. 이 항목은 그 한계를 원장으로 끌어올린 것이다.

★★**선재 패턴 — 회귀가 아니다.** 같은 관용구가 `live_signal.py:2168` 의 `list_fills_since`
호출부에도 있다(docstring 이 그 자리를 직접 지목한다). **한 자리만 고치면 다른 자리가 남으므로
두 자리를 함께 봐야 한다.** 새 코드가 만든 문제로 오해하고 W1 변경을 되돌리지 마라 —
되돌려도 `:2168` 은 그대로다.

★**아직 실측되지 않았다** — aborted transaction 으로 tick 이 연쇄 실패한 관측은 없다.
이 SELECT 가 실패한 적 자체가 없다.

**권장 접근:** 두 자리에 같은 처리를 준다 — `begin_nested()` savepoint 로 감싸거나,
`except` 안에서 `await session.rollback()` 한다. ★**어느 쪽이든 「그 tick 을 계속 진행해도
되는가」를 먼저 정해라.** rollback 은 같은 tick 의 **앞선 미커밋 작업까지** 되돌리므로,
savepoint 없이 넣으면 조용히 다른 것을 잃는다.

**Risk:** 🟡 (fail-open 계약이 문서와 어긋난다. 단 발생 실측 0)

---

### BL-578

**우선순위:** P3
**카테고리:** Backend / trading (조건부 진입 발주 레이스 — 잔여)
**Trigger:** C1 잔여 거절이 **UTC 달력일 기준 3건 이상**인 날이 나오거나, 실자금 cutover 로 1건의 비용이 달라질 때.

★**집행 방법 — 문장이 아니라 쿼리다** (2026-08-01 codex MINOR: 「누가 무엇을 보고 판단하나」).
스프린트 kickoff 의 baseline 재측정 step 에서 **아래 한 줄을 함께 돌린다.** 별도 alert 는 만들지 않는다
(현재 크기 1건/2일에 상시 감시를 붙이는 것이 과하다 — 그 판단 자체가 이 BL 의 내용이다).

```bash
docker exec quantbridge-db psql -U quantbridge -d quantbridge -At -F'|' -c "
SELECT date_trunc('day', created_at AT TIME ZONE 'UTC')::date, count(*)
FROM trading.orders
WHERE reduce_only = false AND state = 'rejected'
  AND (error_message LIKE '%110092%' OR error_message LIKE '%110093%')
  AND created_at >= now() - interval '14 days'
  AND created_at >= timestamptz '2026-07-29 00:00+00'
GROUP BY 1 HAVING count(*) >= 3 ORDER BY 1"
```

**행이 하나라도 나오면 이 BL 을 되살린다.** 나오지 않으면 보류 유지.
기준선(2026-08-01 실측) = 07-27 **10** · 07-28 **20** · 07-29 **2** · 07-30 **0** · 07-31 **1**
— PR #493 이후 문턱을 넘은 날이 없다.

> ★★**2026-08-02 정정 — 이 Trigger 는 자기 기준선에 발화하고 있었다.** 마지막 줄
> (`created_at >= '2026-07-29'`)이 그 수정이다. 그전 형태는 14일 롤링 창이 기준선 07-27(**10**)·
> 07-28(**20**) 을 그대로 담아 **2행을 돌려줬고**, 위 결정 규칙이 「행이 하나라도 나오면 되살린다」라
> **2026-08-11 04:26 UTC 까지 매번 되살림을 지시하는 항상-참 판정식**이었다(verbatim 실행 확인).
> 원장에 **2026-07-31 18:39 UTC 이후 주문이 0건**이므로 새 증거 없이 발화한다.
> 정본 규율 = [`reference/operations/workflows/generator-evaluator-pipeline.md`](reference/operations/workflows/generator-evaluator-pipeline.md) §G1.1 규율 6.
> 수정 후 실행 = **0행**(= 보류 유지). 판별력 확인 = 같은 쿼리의 `HAVING count(*) >= 1` 이 07-29(**2**)·07-31(**1**)을 돌려준다(창이 빈 게 아니다).

**Est:** S
**상태:** ⏳ **대기 (트리거 미도래) — 크기 측정 완료, 수리는 의도적으로 보류.** 2026-08-01 entry-completeness-rejudgement.
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-01 [BL-536](#bl-536) 재판정에서 유일하게 살아남은 채널(C1)의 잔여

★**조건부 진입이 `110092`/`110093` 으로 거절될 때 거래소는 정답(`current[...]`)을 함께 주는데 우리는 그 값을 버린다.**

**원인/영향.** `conditional_entry_planner.plan_reconcile` 은 plan 시점의 `reference_price` 로
돌파 여부를 판정한다(`conditional_entry_planner.py:404-416`). 판정과 발주 사이의 REST 왕복 동안
가격이 트리거를 넘어서면 거래소가 거절한다 — long stop 은 `110092`("expect Rising"),
short stop 은 `110093`("expect Falling"). 거절 메시지는
`trigger_price[627343000] <= current[627366000]` 처럼 **거래소 기준 현재가를 그대로 담고 있다.**

**측정된 크기 (2026-08-01, 원장 전 기간 5일치).**

| 축                        | 값                                                                    |
| ------------------------- | --------------------------------------------------------------------- |
| 거절 총량 (일자별)        | 07-27 **10** · 07-28 **20** · 07-29 **2** · 07-30 **0** · 07-31 **1** |
| `trigger↔current` 격차    | 최소 **0.0005%** · 중앙 **0.0236%** · 최대 **0.0710%** (33건 전건)    |
| 고유 의도 수              | **6** (= 33 거절은 재시도 폭주. 07-28 한 의도가 **18건**)             |
| 같은 의도가 나중에 체결됨 | **22 / 33 (66.7%)**, 지연 **3~54분**                                  |
| 현행 코드 구간(07-30~31)  | **1건 / 2일** · 조건부 파이프라인 109건 대비                          |

★**PR #493(2026-07-28 live-entry-parity)이 이미 20배 줄였다** — 실시간 perp last 기준가 +
돌파 시 시장가 전환. 재시도 폭주도 그 이후 사라졌다. **이 항목은 그 수리의 잔여다.**

**왜 이번에 고치지 않았나 (그 자리에서 판단했다).** 남은 수리 수단이 **시장가 전환**뿐인데
그건 머니-패스 변경이다. 측정된 이득은 **1건/2일**이고 그마저 **66.7%가 다음 bar 에 자연 회복**한다.
게다가 창 P 의 그 1건은 거절 **44초 뒤 세션이 `user_stopped`** 로 꺼져 회복 tick 자체가 없었다 —
「회복 안 됨」이 아니라 「회복할 기회가 없었다」다. 레포 규칙(「새 상태 저장소는 위험하므로
**크기를 본 뒤** 설계한다」, [BL-522](#bl-522))을 따라 **크기를 근거로 보류**한다.

**권장 접근(되살릴 때).** 새 상태 저장소를 만들지 마라. 거절 응답의 `current[...]` 를 파싱해
**그 tick 의 돌파 판정에 되먹인다** — 기존 `max_trigger_breach_pct` cap 을 그대로 통과시켜
시장가 전환 여부를 재평가한다. ★**전환 폭주 방지 가드를 함께 설계해라** — 07-28 에 한 의도가
18번 재시도한 이력이 있다.

**Risk:** 🟢 (현행 크기 1건/2일 · 자연 회복 66.7%. 단 되살릴 때의 수리는 머니-패스라 🟡)

---

### BL-580

**우선순위:** P2
**카테고리:** Backend / 관측 (계측 가드 잔여)
**Trigger:** ★`qb_metrics_mutation_failed_total` 의 **창 차분이 0 을 벗어나는 순간** 즉시 승격. 절대값 아님 — `CounterBasis.delta` 로만 읽는다. 또는 잔여 96곳 중 어느 자리가 머니-패스·알림·내구 쓰기 경계에 새로 닿게 될 때
**Est:** M
**상태:** ⏳ **대기 (트리거 미도래) — 84곳.** 2026-08-04 direction-channel-decomposition 연장이 `_reconcile_conditional_entries` **12곳을 전건 수리**(96→84). 그 앞 회차가 발주 outbox 12곳 판정(수리 8 · 보류 4, 104→96). 그 앞이 25곳(129→104), 그 앞이 12곳(141→129). 2026-08-02 metric-guard-parity 에서 [BL-579](#bl-579) 분리.
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-02 metric-guard-parity (18곳 수리 후 잔여)

가드 밖 mutation **84곳**(규칙 R1, `test_metric_guard_census.py` 가 정본이고 천장으로 고정).

★★★**2026-08-04 교훈 — 함수 하나를 통째로 한 형태로 취급하지 마라.** `_reconcile_conditional_entries`
12곳을 「전부 바깥 fail-open `except` 안」으로 판정했는데 **기존 회귀 테스트가 반증했다**:
`unrepresentable_key`(`:1817`)는 **안쪽 발주 `try`** 안이라 예외가 `stage="conditional_place"`
(= 발주 실패)로 **오기록**되고 있었다 — 발주를 시도한 적도 없는데. 해악은 두 갈래로 갈라 적어라:
**(a) 안쪽 `except` → 오기록** / **(b) 바깥 fail-open → 조용한 중단 + 호출자는 `outcome="success"`**.
★직전 회차도 「전부 commit 뒤라 같은 형태」가 8곳 중 1곳에서 틀렸다. **두 회차 연속 같은 병이다.**
★**H8 은 아니다** — 어느 갈래든 예외는 `continue` 와 `execute` 를 함께 건너뛴다.

★**주입 판정이 안 되면 「판정 보류」로 적고 하네스를 짓지 마라.** 이 회차에 시도한 주입 2건은
**판별력 0**(하나는 기존 A3 와 같은 갈래로 샘 · 하나는 `precision_error` 가 자체 `except` 에
잡혀 바깥까지 안 감)이라 **커밋하지 않고 지웠다.** 구조적 방어는 주입이 아니라 **census AST 동결**이다.

### ★2026-08-03 — 「뺀 이유」 4곳이 **전건 반증**됐다

아래 표의 첫 줄(명시 4곳)은 **코드 독해**였다. 고장 주입으로 재니 **4곳 전부 H1**(성공한 외부
작용이 실패로 보고)이었다. 같은 회차 스윕이 5곳을 더 찾았고 수리 중에 2곳이 더 나왔다 ⇒ **12곳**.
근거는 이제 산문이 아니라 테스트다 — `tests/trading/test_router_cancel_metric_failure.py` ·
`tests/trading/test_trading_task_metric_failure.py` · `tests/tasks/test_live_signal_metric_failure.py`.

★**S1(「가드 옆 raw」) 스윕은 앞만 본다** — `_count_safely` **뒤**에 오는 raw 는 구조적으로 못 잡는다.
실제로 2곳을 놓쳤고 수리 중 테스트 red 로 발견했다. **이 규칙은 완전성을 주장하지 않는다.**

★**`metrics_multiproc.py:35` 는 영구 제외** — `record_metric_safely` 자신의 실패 fallback 이라
감싸면 **재귀**한다. 이미 자체 `try/except` 안이고 DB write·후속 훅·HTTP 표면이 없다.

★**Trigger 의 한계** — `qb_metrics_mutation_failed_total` 은 `record_metric_safely` **안에서만**
오른다(`metrics_multiproc.py` 유일 증가 지점). 가드 **밖** 96곳이 던지면 이 counter 는 오르지
않고 호출자가 죽는다. 즉 이 Trigger 는 **직접 관측이 아니라 프록시**다 — 「같은 환경이면 가드된
자리도 함께 실패한다」를 전제로만 성립한다.

### ★2026-08-03 — 위 표의 **산문 2줄이 25곳을 잘못 뺐다** (metric-guard-residual-close)

종전 이 자리에는 「`order_service.py` 10곳 = 발주 전 검증 거절 직후 `raise`, blast radius 0」과
「`trading.py` closed_pnl 7곳 = `already_synced` 로 수렴, 귀결은 거짓 알림 1건」이 적혀 있었다.
**둘 다 고장 주입으로 반증됐다. 판정 25곳 전건 「수리함」, 「가드 없이 유지」 0곳.**

- **`order_service.py` 10/10** — 계측이 던지면 도메인 예외가 **아예 발생하지 않고** `OSError` 가
  탈출한다. 9종 전부 `AppException`(4xx) 이라 HTTP **500** 이 되고, 그중 6종은 호출자가 예외
  **타입으로 분기**하므로(`tasks/live_signal.py:3232`/`:3239`/`:3249`/`:2793`) `mark_failed` +
  `commit` 이 통째로 빠지고 결정론적 거절이 **3회 재시도**된다. ★`idempotency_conflict` 자리는
  「발주 전」이 아니라 `begin_nested()` + advisory lock **안**이었다.
- **closed_pnl** — 수렴을 만드는 `realized_pnl_synced_at IS NULL` 조건은
  `backfill_exchange_realized_pnl` 을 **호출하는 자리에만** 적용된다. 7곳 중 **5곳은 그 함수를
  한 번도 안 부르는 종결 skip** 이고, `already_synced` 자신은 수렴이 아니라 **고정점 실패**다.
  논거가 성립하는 것은 `applied` 1곳뿐이고 그 자리도 commit **뒤**다.
- **★「거짓 알림 1건」은 반대였다** — `:1744`/`:1756` 은 포기 알림 **바로 앞**이라 지속 실패 시
  알림이 **0건**이 되고 task 가 죽는다.
- **★백로그가 이름을 대지 않았던 8곳 중 6곳이 더 나빴다** — `(tasks/trading.py, qb_closed_pnl_backfill_total)`
  census 는 **15곳**이고 「7곳」은 한 함수의 부분집합이었다. 나머지 중 `:2144` 는 **계정 격리를
  지키는 `except` 의 첫 줄**이라 계측 지속 실패 시 **계정 루프 전체가 중단**된다.
- ★★**단 `:1879`/`:1884` 2곳은 「판정 보류」다 — 프로덕션에서 구조적으로 도달 불가**
  (`list_by_exchange(bybit)` 가 SQL 로 걸러 오고, `BybitFuturesProvider` 에는 `__init__` 이 없다).
  **내 하네스가 계약을 깨서 만든 분기였고 codex G6 가 잡았다.** [BL-582] 함정의 거울상이다 —
  손조립한 상태는 「도달 불가」로도 「유해」로도 거짓말한다. 래핑은 유지, 인용은 금지.
  ⇒ 판정 25곳 = **수리함 23 + 판정 보류 2**, 「가드 없이 유지」 0.

정본은 산문이 아니라 테스트다 — `tests/trading/test_order_rejected_metric.py` ·
`tests/tasks/test_closed_pnl_refresh_metric_failure.py` ·
`tests/tasks/test_closed_pnl_sweep_metric_failure.py` · `tests/tasks/test_refresh_closed_pnl.py` ·
`tests/tasks/test_live_signal_metric_failure.py`(호출자 오라클) ·
`tests/common/test_metrics_multiproc.py`(가드 폭).

★**가드 폭도 별도로 지킨다** — `.labels` 만 감싸고 `.inc()` 를 밖에 두는 **반쪽 수리는 사이트
주입 29건을 전부 통과한다**(변이 M5 실측). `_count_safely` 전용 단위 테스트 2건이 그것을 막는다.

**남은 84곳 — 파일별 분포 (개별 사유는 아직 없다. 「미판정」이지 「안전」이 아니다)**

| 건수 | 파일                                                                                                                                                                                                                                                                                                      |
| ---: | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
|   34 | `apps/api/src/tasks/live_signal.py` (`_evaluate_session_inner` 21 · `_async_sweep_conditional_entries` 4 · `_async_evaluate_all` 2 · `_async_evaluate_session` 2 · `_async_dispatch_pending` 1 · **`_async_dispatch_event` 4 = 판정 보류**) — `_reconcile_conditional_entries` 12 는 2026-08-04 전건 수리 |
|   14 | `apps/api/src/tasks/trading.py`                                                                                                                                                                                                                                                                           |
|    5 | `apps/api/src/tasks/conditional_entry_janitor.py`                                                                                                                                                                                                                                                         |
|    4 | `apps/api/src/tasks/_ws_circuit_breaker.py`                                                                                                                                                                                                                                                               |
|    3 | `apps/api/src/common/redlock.py` · `apps/api/src/tasks/websocket_task.py` · `apps/api/src/trading/websocket/state_handler.py` (각 3)                                                                                                                                                                      |
|    2 | `common/alert.py` · `common/metrics.py` · `trading/realtime_publisher.py` · `trading/webhook.py` · `trading/websocket/bybit_private_stream.py` (각 2)                                                                                                                                                     |
|    1 | 나머지 8개 파일 (각 1)                                                                                                                                                                                                                                                                                    |

★**누적 판정 42곳 중 「가드 없이 유지」 0곳이다**(9 + 25 + 이번 8). 잔여 84곳도
산문으로 분류하지 말고 **주입으로 시작해라.**

**착수 순서 — `live_signal.py` 34곳부터, 한 회차에 한 헬퍼 계열로 끊어라.**
★**선행 조건은 이미 서 있다**(2026-08-04 handler-visibility): 그 34곳은 **이름 붙은 헬퍼 안**에
있고, 운반자 함수(`_reconcile_conditional_entries_inner`·`_evaluate_session_with_engine`)에는
**`try` 가 하나도 없으며** 감싸는 핸들러는 각 헬퍼가 소유하고 **docstring 에 적혀 있다**.
⇒ 4차·3차가 두 번 연속 밟은 **「함수 하나 = 한 형태」 오판의 물리적 조건이 사라졌다.**
★**그래도 산문으로 분류하지 마라** — 누적 42곳에서 「가드 없이 유지」가 0곳이다. 주입으로 시작해라.

**방법 4단계 (이전 4회차가 확립한 것 — 바꾸지 마라):**

1. 자리마다 **감싸는 핸들러를 코드로 확인**하고, 해악을 (a) 오기록 / (b) 조용한 중단 으로 갈라 적는다
2. **고장 주입으로 판정**한다 — 산문으로 「~라서 안전하다」 쓰지 마라(누적 42곳에서 그 산문 **전건 반증**)
3. 주입 판정이 안 되면 **「판정 보류」로 적고 하네스를 짓지 마라**(4회 연속 판별력 0 을 밟았다)
4. 구조적 방어는 `tests/common/test_metric_guard_census.py` 의 AST 동결(**현재 40키 / 84곳**)

★**census 숫자가 줄면 그만큼 `_FROZEN_CENSUS` 를 낮춰라** — 안 낮추면 다음 회차가 그 자리를 다시 판정한다.

### ★2026-08-03 — 「commit 뒤」는 형태가 아니다 (신규 라벨 **H8**)

발주 outbox 12곳은 **전부 `mark_failed`/`mark_dispatched` + `commit()` 뒤**였고 나는 그것을
하나의 형태로 요약했다. **8곳 중 1곳에서 그 요약이 틀렸다.** `:3133`(`close_position_flat`)만
**fail-open `try` 안**이라, 계측 예외를 `except Exception` 이 「포지션 조회 실패」로 오인해
삼키고 `return` 을 건너뛴 채 **그대로 발주한다**(주입 실측: 반환값이 `{"dispatched": …}`).
⇒ 귀결이 오기록이 아니라 **원장 분기**다 — `failed` 로 커밋된 이벤트에 실주문이 나간다.
**H8 = 거절이 집행으로 뒤집힌다.** 다음 스윕은 사이트마다 **바깥 `except` 가 무엇을 하는지**부터 적어라.

★**보류 4곳은 「안전」이 아니라 「도달 경로를 못 적었다」다** — 하네스를 만들면 프로덕션이
못 만드는 상태를 손조립하게 된다([BL-582] 함정의 거울상). 사유는 census 정본의 키 위 주석에 있다.
그중 `:3253`(`idempotency_conflict`)은 **사문**이다 — 유일 raise 지점이 `body_hash is not None`
안인데 이 호출자는 `body_hash=None` 을 넘긴다.

★**census 규칙이 못 잡는 것** — 별칭(`c = qb_x; c.inc()`) · `getattr` 동적 접근 · 모듈 alias ·
**eager `.labels()`**(`record_metric_safely(qb_x.labels(a="b").inc)` 는 `.labels()` 가 헬퍼 호출
**전에** 실행돼 예외가 탈출하는데 census 는 guarded 로 센다. 현 트리에 **0곳**, 2026-08-02 codex G6 MINOR).
★**디스크 full 의 mmap write 는 `SIGBUS`** 라 `record_metric_safely` 도 못 잡는다. 가드는 만능이 아니다.

**Risk:** 🟡

---

### BL-581

**우선순위:** P3
**카테고리:** Backend / 운영 위생 (`/metrics` 영구 누적)
**Trigger:** 파일 수가 20000 을 넘거나, `/metrics` 스크레이프 지연이 관측되거나, 디스크 여유가 20G 아래로 떨어질 때
**Est:** M
**상태:** ⏳ **대기 (트리거 미도래) — 측정 완료, 수리 보류.** 2026-08-02 metric-guard-parity (사용자 확정: 측정만).
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-02 [BL-579](#bl-579) 측정 중 별개 축으로 분리

| 축           | 실측 (2026-08-02)                        | 실측 (2026-08-04 03:1x Z)              |
| ------------ | ---------------------------------------- | -------------------------------------- |
| 파일 수      | **10277** (전날 9423 → 회차 중에도 증가) | **14905** — Trigger 20000 의 **74.5%** |
| 용량         | **635MB** (여유 125G)                    | **924MB** (여유 124G — 아직 여유)      |
| distinct PID | **1968**                                 | 미측정                                 |
| 최초 파일    | **2026-07-28**                           | 2026-07-28 12:19 (= counter 출생일)    |
| 스크레이프   | 미측정                                   | **2.67초**                             |

~~★**증가율 실측 = +175 파일/h**(08-03 15:11 의 12836 → 08-04 03:1x 의 14905). 이 속도면
**약 29시간 뒤 Trigger(20000) 에 닿는다.** 즉 이제 이 항목은 소크 창의 **상한**이다.~~

★★**2026-08-04 후속 회차 정정 — 이 항목은 소크 창의 상한이 아니다.** 위 「+175/h ⇒ 29시간」은
**개발 세션 중** 창을 재서 나온 값이고, 그 시간대에는 `apps/api/src` 편집마다 워커가 재기동한다.

증가 드라이버는 **PID churn** 이 맞는데, 그 PID churn 을 만드는 것이 무엇인지가 빠져 있었다 —
워커 커맨드가 **`uv run watchfiles --filter python celery … /app/src`**(`docker inspect` 실측)라
**`apps/api/src` 를 편집할 때마다** 전체 재기동하고, 재기동마다 새 PID 가 role 당 5파일
(`counter`/`gauge_livesum`/`gauge_mostrecent`/`gauge_sum`/`histogram`)을 만든다.

| 시간대                        | 실측 증가율     | 근거                                                                           |
| ----------------------------- | --------------- | ------------------------------------------------------------------------------ |
| **편집 세션**                 | **~600 파일/h** | 08-03 08시 584 · 08-03 17시 829 · 08-04 01시 595 (birth 시각 히스토그램)       |
| **조용한 소크**(`src` 편집 0) | **~4–5 파일/h** | 08-04 00시 **4개** · 08-04 02:55~04:27 의 90분에 **5개**(워커 자식 1회 재활용) |

⇒ 잔여 5,091 파일을 조용한 소크 속도로 나누면 **약 42일**이다. **소크를 며칠 돌리는 데 구조적
상한이 없다.** 이 항목이 제약하는 것은 소크 시간이 아니라 **개발 재기동 예산**(약 8시간치 편집
세션)이다. ⇒ 우선순위 **P3 유지**, [BL-591]/[ADR-023] 보다 앞설 이유 없음.

★**「최근 57분간 신규 0개」로 먼저 적었던 것은 과장이었다** — 같은 회차 안에서 90분 창으로 다시
재니 5개였다. **n=1 창으로 「0」을 주장하지 마라**(이 레포의 「작은 창의 0 은 0 이 아니다」).

★★**counter/histogram 파일을 지우지 마라** — `entry_completeness.py` 가 **재기동 생존을 전제로**
창 차분을 잰다. 지우면 이 레포의 측정 체계가 깨진다. `mark_process_dead` 는 gauge 만 지운다.
★**writer id 를 PID → worker index 로 바꾸는 것도 금지** — `MmapedDict` 는 단일 writer 전제이고
prefork 부모+자식 동시 생존 · reload drain 겹침 구간이 실재한다. **손상 확률을 올린다.**
★**착수 시 내가 「로컬 API 는 단일 프로세스 모드」라고 적었는데 거짓이다** — `Makefile:163-166` 이
`PROMETHEUS_MULTIPROC_DIR` 와 `QB_METRICS_ROLE=api` 를 직접 주입한다.

**Risk:** 🟢

---

### BL-582

**우선순위:** P3
**카테고리:** Backend / 관측 (도달 불가 series)
**Trigger:** `PendingOrderSnapshot` 이 exit level 을 갖게 되거나(엔진 계약 변경), `degraded_input` 이 자연 발화로 관측될 때
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래) — 2026-08-03 metric-guard-residual 이 「7종」을 「5종」으로 축소 재판정.**
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
2종은 **엔진 실행으로 반증**됐고 남은 5종은 실행 가능한 구조 전제 게이트로 고정했다.
**출처:** 2026-08-02 [BL-576](#bl-576) 잔여 검증 중 확정

`qb_live_conditional_divergence_total` 의 13 series 중 **5종**이 구조적으로 도달 불가다(종전 7종).

### ★2026-08-03 반증 — 근거 문장이 거짓이었다

종전 근거는 「`PendingOrderSnapshot.take_profit/stop_loss/trailing_stop` 이 **항상 `None`**」이었다.
`run_live` 를 직접 돌려 반증했다 — **반대 방향 same-id 재발행 + `strategy.exit`** 이면 엔진이
`take_profit=192`·`stop_loss=64`(또는 `trailing_stop=100`)를 **실제로 싣는다.**

★**올바른 서술은 [BL-523](#bl-523) 쪽이었다** — 「현재 코퍼스 미발현」. 발현 조건 3개:
(a) 같은 `trade_id` 가 이미 열려 있고 (b) 그 id 에 `strategy.exit` 브래킷이 붙고
(c) 재발행이 **반대 방향**(같은 방향이면 계획기가 `quantity==0` 에서 `continue` 해 게이트 미도달).

★**왜 종전 판정이 그렇게 나왔나** — 기존 게이트 테스트는 스냅샷을 **손조립**해 게이트 라인만
구동했다. 「게이트는 동작한다」는 증명하지만 「엔진이 그 입력을 만들 수 있는가」는 검증하지
않았다. 그 미검증 구간이 「도달 불가」로 기록됐다. 정본 =
`tests/tasks/test_conditional_divergence_reachability.py`(엔진 산출물을 reconcile 루프에 직접 흘린다).

| series                                                            | 판정                                                                                                            |
| ----------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `guard_drop`/`bracket_trailing_only` · `bracket_tp_size_mismatch` | ★**도달 가능** (2026-08-03 엔진 구동 확인). 프로덕션 발화는 여전히 미관측                                       |
| `other` 5종                                                       | 도달 불가 — 전 호출부 reason 가능값이 allowlist 부분집합임을 **bounded def-use 오라클**로 고정(해소 실패 = red) |

★**도달 가능 8종**(2026-08-03 재판정, 종전 6종) **중 프로덕션 확인 = 3**
(`stand_down/shared_account_symbol` · `market_converted` ·
**`exchange_divergence`**(2026-08-02 유도로 신규 확인)). 남은 **5종**:
`stand_down/hedge_mode`(계정 position mode 전환 필요) · `guard_drop/breach_exceeds_cap`(확률적) ·
★`degraded_input/reference_price_unavailable` — **유도하려면 제3자 공개 API 에 레이트리밋 유발
트래픽을 쏘거나 MITM 프록시가 필요하다. 전자는 하지 않는다(영구 제외)** ·
`guard_drop/bracket_trailing_only` · `guard_drop/bracket_tp_size_mismatch`(2026-08-03 신규 —
결정론 fixture 로만 검증, 코퍼스에 발현 전략이 없어 프로덕션 유도는 전략 등록이 선행돼야 한다).

★**2026-08-03 회차는 soak 를 하지 않았다**(사용자 결정) — 위 5종은 **「프로덕션 미확인」으로
명시 유지**한다. 미확인을 적어 두는 것 자체가 산출물이다.

★**「13 series 존재」를 기능 증거로 인용하지 마라 — 증거는 오직 차분이다.**

**Risk:** 🟢

---

### BL-584

**우선순위:** P3
**카테고리:** Backend / 관측 (라이브 발주 실패 사유 유실)
**Trigger:** ★**`mode=live` 인 `ExchangeAccount` 가 처음 생성될 때**(Wave 3 cutover — 그 순간 도달 가능해진다). 또는 `qb_live_signal_dispatch_total{outcome="max_retries_exhausted"}` 의 창 차분이 0 을 벗어날 때
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래) — 2026-08-03 metric-guard-residual-sweep 가 「현재 코퍼스 도달 불가」로 확정.**
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
수리하지 않는다. 등재는 유지하되 Trigger 를 cutover 로 바꿨다.
**출처:** 2026-08-03 metric-guard-residual-close (BL-580 A6/A7 판정 중)

`BalanceUnverified`(fail-closed 잔고 미검증 거절, 422)가 `tasks/live_signal.py` 의 **결정론적-거절
튜플 양쪽에 없다** — `_async_dispatch_event` 의 `except (NotionalExceeded, LeverageCapExceeded,
MinNotionalNotMet, TradingSessionClosed)` 에도, `dispatch_live_signal_event_task` 의 무재시도
튜플에도 없다. 같은 계열의 다른 거절 5종은 둘 다에 있다.

**귀결.** 이 거절은 `except Exception` 으로 떨어져 **재시도 대상**이 되고, 소진하면
`mark_failed(error="max_retries_exhausted")` + `outcome="max_retries_exhausted"` 로 기록된다.
**실제 사유(잔고 미검증)가 기록에서 사라진다.**

★**재시도 자체는 타당할 수 있다** — 잔고·mark price 조회 실패는 일시적일 수 있다. 그래서 P3 이고,
수리 방향은 「튜플에 넣기」가 아니라 **소진 시 원래 예외 사유를 error 에 보존하기**일 가능성이 높다.
결정 전에 `BalanceUnverified` 가 라이브에서 실제로 발생하는지부터 봐야 한다 — 현재 플랫폼은
Bybit **demo** 만 허용하고 이 거절은 `mode == live` 분기에서만 난다(`order_service.py`), 즉
**현재 코퍼스에서 도달 불가일 수 있다**. 그것부터 확인하는 것이 첫 step 이다.

### ★2026-08-03 도달성 확인 — **현재 코퍼스 도달 불가 확정** (수리 없음)

- `raise BalanceUnverified` 2곳(`order_service.py:295`·`:309`)은 모두
  `dispatch_snapshot["mode"] == ExchangeMode.live` 게이트 안이다.
- `dispatch_snapshot["mode"]` 는 발주 시점 계정 **fresh read**(`order_service.py:199`) —
  세션 등재 시점 스냅샷이 아니다.
- 라이브 세션 등재는 `account.exchange == bybit and account.mode == demo` 를 강제하고
  아니면 `AccountModeNotAllowed`(`live_session_service.py:109`).
- ★**계정 mode 는 생성 후 불변이다** — `ExchangeAccountRepository` 에 갱신 메서드가 없고
  (`save`/`get_by_id`/`list_*`/`delete` 뿐), 라우터도 POST(등재)·GET·DELETE 뿐이다.
- 코퍼스 실측(2026-08-03): `mode=live` 계정 **0건**.

⇒ 라이브 신호 dispatch 경로에서 이 거절은 **날 수 없다.** 그래서 고치지 않고, Trigger 를
「그 전제가 깨지는 순간」(= `mode=live` 계정 생성)으로 바꿔 등재만 유지한다.

**Risk:** 🟢

---

### BL-592

**우선순위:** P2
**카테고리:** Trading / 거래소 계정 (계측 정합성)
**Trigger:** `exchange_exits` 로 원장 구멍·귀속을 판정하기 전에
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-04 engine-position-ssot ([BL-591] Q2 실측 중 발견)

**같은 Bybit 데모 계정이 두 번 등록돼 있어 청산 원장이 이중 적재된다.**

`trading.exchange_accounts` 에 `bybit demo`(`19a8166a`, 2026-07-25 생성) 와
`bybit demo- aaa`(`0277c150`, 2026-07-26 생성) 두 행이 있고 **같은 거래소 계정을 가리킨다.**
`exchange_exits` 의 유니크 키가 `(exchange_account_id, row_hash)` 라 **같은 청산이 계정마다 한 행씩**
들어간다.

**오라벨이 따라온다.** `classify_exit` 의 `known_order_ids` 는 **계정 스코프**다. 주문을 실제로
가진 계정(`19a8166a`)에서는 `ours` 로 맞게 분류되는 **바로 그 청산**이, 주문이 없는 계정
(`0277c150`)에서는 `unknown` 이 된다.

실측(2026-08-04):

| 계정                   | ours   | unknown | external_manual |
| ---------------------- | ------ | ------- | --------------- |
| `19a8166a` (주문 보유) | **91** | 0       | 12              |
| `0277c150` (주문 없음) | 0      | **91**  | 12              |

★**대칭이 단서였다** — `CreateByUser` 65/65 · `CreateByStopOrder` 26/26 으로 정확히 갈렸다.

**영향 — 계측을 3.7배 부풀린다.** 중복 제거 전 전체 206행 중 미매칭이 119건으로 보이지만 실제
청산은 **103건**이고 원장 밖은 **12건(11.7%)** 이다. [BL-591] 슬라이스 1 이 이 테이블을 관측축으로
쓰므로 **인지하지 않으면 판정이 오염된다.**

**처리 방향 (택일 — 미확정):** ① 미사용 계정 행 정리(참조 무결성 확인 선행 — `orders` ·
`live_signal_sessions` 가 `RESTRICT` 다) ② 거래소 UID 기준 중복 등록 차단
(`backfill_exchange_account_identities` 가 이미 UID 를 채운다) ③ 계측 질의에서만 중복 제거.
★**최소한 ②는 필요하다** — 지금은 같은 계정을 몇 번이든 등록할 수 있다.

**Risk:** 🟡 계측 정합성. 머니-패스는 아니다(각 계정의 주문 스코프는 정확히 분리돼 있다).

**연결:** [BL-591] (이 테이블을 관측축으로 쓴다)

---

### BL-593

**우선순위:** P2
**카테고리:** Trading / 운영자 도구 (원장 완결성)
**Trigger:** 소크를 끄거나 거래소를 손으로 flat 으로 만들기 전에
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 소크 창 미완(soak-gate rc=2 · C1 46.24h/168h). PASS 만 도래다([ADR-024]) (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-04 engine-position-ssot ([BL-591] Q2 실측 중 확정)

**운영자 도구가 청산할 때 원장에 아무것도 안 남는다.**

★**앱 코드에는 원장을 건너뛰는 청산 경로가 없다.** `ClosePositionService.close_position` 은
`OrderService.execute(...)` 를 타므로 **`Order` 행을 남긴다**. `src/` 전체에서 주문을 내는 provider
호출은 `tasks/trading.py:431`(= 원장 경로) 하나뿐이다.

문제는 **그 서비스가 `dependencies.py` 를 통해 HTTP 에만 조립돼 있다**는 것이다. 그래서
`apps/api/scripts/verify_*.py` · `bybit_demo_smoke.py` 및 임시 정리 스크립트는 그걸 못 쓰고
**provider 를 직접 호출**한다 → 대응 `trading.orders` 행이 없다.

**실측 (2026-08-04, `trading.exchange_exits` 계정 `19a8166a`):** 청산 **103건** 중
`external_manual`(원장 밖) **12건 = 11.7%**. 날짜별 07-24(1) · 07-27(1) · 07-28(2) · 07-31(3) ·
08-01(2) · 08-03(3) — **6일에 걸쳐 상시**다. 단 **12건 중 10건이 「활성 세션 없음」 구간**이고
세션 안은 2건(`dc1e08f1`, 07-31)뿐이다.

**왜 지금 중요한가.** [BL-591] 이 채택한 C 안은 **원장을 진실로 써서 엔진에 주입**한다. 원장에
없는 청산이 있으면 **틀린 포지션을 주입**하게 된다. veto 게이트가 그 순간을 막도록 설계됐지만,
애초에 구멍을 안 만드는 쪽이 근본이다.

**처리 방향:** `ClosePositionService` 를 **HTTP 밖에서 조립하는 진입점**을 만들어 스크립트가
그것을 쓰게 한다. 선례 = `apps/api/scripts/seed_dogfood.py:11-19`(서비스 계층 직접 호출).
★**검증은 실사용으로 한다** — 정리 후 `exchange_exits` 에 `external_manual` 이 **안 늘고**
`ours` 가 느는지로 판정한다.

**Risk:** 🟡 도구 결함. 다만 [BL-591] C 안의 전제를 직접 갉는다.

**연결:** [BL-591] (원장을 SSOT 로 쓰는 전제)

---

### BL-598

**Priority:** P2
**카테고리:** Backend / 테스트 인프라 (코퍼스 첫-접촉 파싱 비용)
**Trigger:** CI backend 를 **14분 아래**로 내리려 할 때 · pine_v2 코퍼스 테스트를 늘리기 전에
**Est:** M
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**코퍼스 스크립트를 「처음」 파싱하는 테스트가 비용을 전부 물고, 이후는 거의 공짜다.**

**실측 (2026-08-06 ci-diet):**

| 대상                              | 단독 실행  | 전체 스위트 안 |
| --------------------------------- | ---------- | -------------- |
| `test_ast_classifier[i3_drfx]`    | **42.66s** | **4.58s**      |
| `test_ast_classifier[i1_utbot]`   | 12.06s     | 0.02s          |
| `test_ast_classifier[i2_luxalgo]` | 6.45s      | 0.04s          |

★샤딩 전에는 알파벳상 앞선 `test_alert_hook` 이 그 값을 치르고 나머지가 무임승차했다. 그래서
이 테스트는 단일 실행 `--durations=10` 에 **아예 안 나타났고**, 샤드 경계를 그 목록으로 잡은
착수 추정이 **2.2배 빗나갔다**(샤드 a 추정 385s → 실측 847s).

**왜 중요한가.** 이 비용은 **프로세스 전역**이라 스위트를 쪼개는 순간 샤드마다 중복된다.
CI 3 샤드 합 **1796s** vs 단일 **1278s** 의 **+519s 전부**가 이 중복이다(고정 오버헤드가 아니다 —
샤드 b 는 70 테스트에 615.42s 인데 top-10 만 596s 를 차지한다). ⇒ **스위트가 샤딩에 저항한다.**
현행 3-way 는 wall 14.8분이 한계고, 재분배로는 못 내려간다(샤드 a 에 `i3_drfx` 소비 파일이 9개 더
있어 `ast_classifier` 를 빼도 다음 테스트가 그 240s 를 문다).

**① 정체 규명 — 확정 (2026-08-08).** 재현 도구 = `apps/api/scripts/profile_corpus_parse.py`
(인자 없이 돌리면 요약표. `--ramp` / `--solo` / `--cprofile` / `--all`). 정체는 **`pynescript` 가
쓰는 ANTLR4 ALL(\*) 어댑티브 예측의 DFA 캐시가 「파싱에 의해」 지연 구축되는 것**이다 —
import 워밍업도 아니고 입력 크기 법칙도 아니다.

| 축               | 실측                                                                                           | 판정                                             |
| ---------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| import 비용      | `classify_script` import **0.26s**(warm), import 직후 DFA 상태 **0**                           | **(a) 기각** — cold 합계의 0.4% (**warm 한정**)  |
| 코퍼스 cold/warm | 9벌 cold 합계 **71.25s** vs 같은 프로세스 warm **5.77s**                                       | 첫-접촉 프리미엄 **91.9%**                       |
| `i3_drfx` 단독   | cold **42.19s** / warm **3.80s**                                                               | warm 이 전체 스위트 안 4.58s 와 일치             |
| **인과 대조**    | 같은 프로세스·같은 입력에서 캐시**만** 비우니 3.68s → **51.37s**, 다시 3.69s                   | 원인이 캐시 상태임을 **인과로 확정** (14.0배)    |
| **성분 분리**    | `parser_dfa` 만 비움 **55.16s(15.0배)** · `shared_ctx` 3.82s(1.0배) · `lexer_dfa` 3.93s(1.1배) | 비용을 지는 것은 **파서 DFA 하나**뿐             |
| cold 램프        | **조각마다 새 프로세스**. 크기 8.6배 → cold 8.39s→**50.80s**(6.1배), log-log 기울기 **0.78**   | **(b) 기각** — 초선형이 아니라 **sublinear**     |
| warm 램프        | log-log 기울기 1.25 이나 꼬리 절반은 크기 1.6배 → 시간 1.1배(sublinear)                        | **(b) 기각** — warm 5.77s 로 42.66s 를 못 만든다 |
| 샤딩 중복        | 프로세스 9개로 쪼개면 합계 **122.82s** vs 단일 프로세스 **69.93s**                             | 중복분 **+52.89s** 를 실측으로 확인              |

★**램프는 두 축을 분리하지 못한다** — 한 파일의 prefix 는 「글자 수」와 「처음 보는 문법
결정 수」가 **함께** 자란다(기울기 0.78 vs 0.84 로 사실상 구분 불가). 램프가 답하는 것은
「초선형인가」뿐이고 답은 **아니다**. 축을 가르는 것은 아래 성분 대조다.

기전: `PinescriptParser.decisionsToDFA` 가 generated 파서의 **클래스 속성**(`PinescriptParser.py:346`)
이라 프로세스 전역이고, 파서 인스턴스는 생성 시점에 그것을 읽는다
(`ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)`).
cProfile 누적시간 99% 가 `adaptivePredict` → `execATN` → `closure_`(2,396만 호출)다.
⇒ 「프로세스 전역이라 샤딩하면 중복된다」는 위 진단은 **맞았다**. 틀린 것은 원인 후보
2개(import·크기)뿐이다.

★**성분 분리가 없으면 「ANTLR 캐시가 원인」까지밖에 못 간다.** 초판은 파서 DFA·
`sharedContextCache`·렉서 DFA 를 한꺼번에 비워 놓고 결론을 「DFA 가 원인」이라고 적었다 —
셋을 묶어 비운 실험은 그 문장을 지지하지 못한다. 하나씩 비우자 **파서 DFA 만 15.0배이고
나머지 둘은 1.0/1.1배**로, 결론이 좁혀지는 동시에 강해졌다.

★★**2026-08-08 결론 문구 정정 — 「parser DFA **단독**이 원인」은 과대 진술이었다.**
성분 루프가 회차마다 `→ warm` 으로 **다시 데우므로**, `shared_ctx` 를 비울 때 parser DFA 는
**이미 워밍돼 있었다.** 그 배치에서 나온 1.0배가 지지하는 문장은

> **parser DFA 가 워밍된 상태에서는 나머지 둘이 추가 비용을 지지 않는다**

까지다. 「shared_ctx 는 무관하다」가 아니다. **처방(파싱 결과 디스크 캐시)은 그대로 지지된다** —
파싱을 아예 안 하면 셋 다 안 쌓이므로 성분 배분과 무관하다. 근거 진술만 좁힌다.

★**independent control 을 실제로 재서 순서 의존을 배제했다**(`--components`, 2026-08-08).
성분마다 **새 프로세스**를 띄워 리셋 직전 상태를 「cold 1회 + warm 1회」로 셋 다 동일하게 맞췄다:

| scope        | cold_s | warm_s | after_reset_s | 배수       |
| ------------ | ------ | ------ | ------------- | ---------- |
| `parser_dfa` | 51.28  | 3.80   | **52.70**     | **13.9배** |
| `shared_ctx` | 51.15  | 3.74   | 3.85          | 1.0배      |
| `lexer_dfa`  | 51.30  | 3.82   | 3.93          | 1.0배      |

순서 의존이 사라져도 결과가 같다 ⇒ [8] 의 15.0/1.0/1.1 은 **측정 순서의 산물이 아니다.**
다만 이것도 **조건부 문장을 확증할 뿐 단독 기여를 재지 않는다** — 리셋 시점에 parser DFA 는
여전히 데워져 있다.

★**[확인 필요] clean first-touch 성분 분해는 미측정이다.** 「셋 다 비어 있는 상태에서 각
성분이 첫 파싱의 몇 초씩을 가져가는가」는 이 도구가 답하지 않는다 — 캐시를 **끈 채로** 파싱할
수단이 없어서(비우면 즉시 다시 쌓인다) 실험 설계 자체가 없다. ② 가 디스크 캐시로 닫히면
이 분해는 필요 없어지므로 **하지 않기로 했고, 여기 적어 둔다.**

**② 처리 방향 — 테스트 쪽에서 닫힌다 (`apps/api/src` 0줄).** 파싱 시간이 크기에 초선형이
아니므로 **파서에는 고칠 표적이 없다**. 표적은 「테스트가 파싱을 한다」는 사실 자체다.

★**단, `classify_script()` 만 캐시하면 안 닫힌다.** 코퍼스를 읽는 테스트가 **30 파일**이고
그중 `i3_drfx` 를 건드리는 것이 **10 파일**이다. 진입점도 `classify_script`·`extract_content`·
`analyze_coverage`·`classify_message`(alert hook)·`parse_and_run_v2` 로 갈린다.
`test_ast_classifier` 만 캐시하면 **그 샤드의 다음 테스트가 같은 워밍업을 그대로 문다.**

닫는 자리는 **하나**다 — `src/strategy/pine_v2/` 의 7 모듈이 전부 `from pynescript import ast
as pyne_ast` 뒤 `pyne_ast.parse(...)` 를 부르므로 **호출 시점에 같은 모듈 객체의 속성**을 본다.
⇒ `conftest.py` 에서 `pynescript.ast.parse` 를 **소스 해시 키 디스크 캐시로 감싸면** 7 진입점이
한꺼번에 덮인다. `tests/` 안에서 끝나므로 `apps/api/src` 0줄이다(baseline 재생성 경로는 캐시
우회 플래그로 남긴다).

캐시 매체는 **pickle 로 확인됐다** — AST 노드가 module-level `@dataclass` 라 그대로 직렬화된다.
`s1_pbr` 실측: cold 파싱 **5.316s** vs unpickle **0.0002s**(6,542 B, 타입·`body` 길이 보존).
파싱을 **약 3만 배** 싼 역직렬화로 바꾸는 것이라 ② 의 이득은 구조적으로 확보된다.
[확인 필요] 캐시가 켜진 상태에서 **코퍼스 소비 테스트 전량이 여전히 green 인지**는 ② 착수 시
확인한다(위 실측은 타입·`body` 길이까지만 대조했다).

③ ②가 되면 샤드마다 중복되던 비용이 사라져 샤드 재분배로 추가 이득이 열린다.

★★**사거리 — 위 결론은 전부 `warm` 프로세스 한정이다. cold 축은 미측정이다**(2026-08-08 정정).
프로파일러 `section_import` 는 **첫 서브프로세스를 버린다** — 그 첫 회가 **17초**였고 그 안에
bytecode(`.pyc`) 컴파일 + OS 파일 캐시 워밍이 섞여 있다. 버린 뒤 3회를 재서 나온 것이
0.26s 다. 그런데 **CI 러너는 cold 다** — `.pyc` 도 파일 캐시도 없이 시작한다.
⇒ 「import 는 cold 합계의 0.4% 라 무시 가능」은 **[BL-598] 이 정의하는 현상**(같은 머신,
warm 프로세스에서 단독 42.66s vs 스위트 안 4.58s)에 대해서만 참이고, **cold CI 를 배제하지
않는다.** 그 축은 신규 **[BL-652](#bl-652)**.

★★**규모 대조는 하지 않았다 — 「+519s 전부가 이 중복」은 여전히 미검증 가정이다**
(2026-08-08 zero-touch-bundle `/code-review` 지적). 착수 spec 이 든 숫자와 ①의 실측은 **잰 양이 다르다**:

| 출처                | 단위                                         | 값                              |
| ------------------- | -------------------------------------------- | ------------------------------- |
| 착수 spec (CI 실측) | pytest **3샤드** wall 합 vs 단일             | 1796s vs 1278s ⇒ **+519s**      |
| ① 실측 (로컬)       | 코퍼스 파싱만, **9프로세스** 합 vs 1프로세스 | 122.82s vs 69.93s ⇒ **+52.89s** |

두 값은 **약 10배** 차이인데, 그 차이가 규모 때문인지 다른 성분 때문인지 **아무도 대조하지 않았다.**
셈만 해 보면 대조가 필요한 이유가 보인다 — 「샤드마다 코퍼스 첫-접촉을 한 번씩 다시 문다」 모형에서
샤드 3개의 중복은 `(3-1) × 프리미엄` 이고, 이 맥의 프리미엄은 **65.48s**(cold 합 71.25 − warm 합 5.77)라
**약 131s** 다. 519s 의 **25%** 다. 나머지를 이 모형으로 덮으려면 CI 러너의 cold 파싱이 이 맥보다
**약 4배** 느려야 하는데, 그건 방향으로는 그럴듯해도(러너 2 vCPU) **잰 적이 없다.**
★그리고 ①의 `+52.89s` 를 샤드 프리미엄으로 읽으면 안 된다 — 그 실험은 코퍼스 9벌을 **9프로세스로
쪼갠** 것이라 프로세스마다 **자기 조각 하나만** 파싱한다. 샤드가 코퍼스 전체를 다시 무는 CI 상황과
**모집단이 다르다.** ⇒ 이 축을 닫으려면 **CI 에서** 샤드 수를 바꿔 가며 재야 한다. 여기서는
**미대조**로 적어 둔다(추정치를 지어내지 않는다). [BL-652] 의 cold import 축도 같은 자리에서 열린다.

★**「캐시가 있을 것이다」로 시작하지 마라** — 찾아봤고 없었다. 관측부터 해라.

★**절대초를 인용하지 마라 — 배수를 인용해라.** 같은 cold 파싱이 머신 부하에 따라 41~68s 로
흔들렸다. 재현 가능한 것은 순위와 배수(cold/warm ≈ 14배)이지 절대시간이 아니다.

**[확인 필요]** ANTLR `PredictionMode.SLL` 로 낮추면 예측 비용이 급감하지만 모호 문법에서
오파싱 위험이 있고, 그 설정 지점이 `pynescript` 의 `parse()` 경로 **안**이라 이번 축에서는
건드리지 않았다. ② 가 디스크 캐시로 닫히면 이 선택지는 열 필요가 없다.

**Risk:** 🟢 CI 시간·비용 문제이고 프로덕션 정확성과 무관. 단 **테스트 시간 추정을 반복해서
빗나가게 만드는** 원인이라 계측 신뢰도에 영향.

**연결:** [BL-583] (수집 집합이 결과를 바꾼 선례 — 같은 「무엇이 함께 도는가」 축)

**출처:** 2026-08-06 ci-diet (CI run 31071389290 잡별 실측 부검)

### BL-599

**Priority:** P3
**카테고리:** Backend / 죽은 코드 (Pine v1 shim)
**Trigger:** `BacktestOutcome` 를 손볼 일이 생겼을 때 (단독으로 열지 마라 — 이득 대비 파급이 크다)
**Est:** M
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**Pine v1 shim(`src/strategy/pine/`, 135L)은 타입 4종만 재export 하는 껍데기다.**
lexer/parser/interpreter/stdlib/v4_to_v5/ast_nodes 6 모듈(2146L)은 이미 제거됐고, 남은 것은
`ParseOutcome / SignalResult / SourceSpan / PineError` 뿐이다.

**왜 아직 못 지우나.** `BacktestOutcome.parse: ParseOutcome` 이 코어 DTO 필드라서다. 소비처는
**「2곳」보다 넓다**(2026-08-06 실측): 프로덕션 import 2곳(`backtest/engine/types.py:13` ·
`v2_adapter.py:39`) + `BacktestOutcome(...)` 생성 site **10곳 이상**(v2_adapter) + 테스트 3파일
(`tests/backtest/engine/test_types.py` · `tests/strategy/pine/test_types.py` · `test_errors.py`).
`walk_forward.py` 도 `BacktestOutcome` 을 타입으로 받는다.

**처리 방향:** shim 제거는 `BacktestOutcome.parse` 철거와 **동시에만** 의미가 있다.
① 그 필드가 실제로 소비되는지(API 응답까지 나가는지) 먼저 추적 ② 안 나가면 필드 제거 +
생성 site 정리 ③ 그 뒤 `src/strategy/pine/` 삭제. ★①을 건너뛰고 shim 만 옮기면 순환만 늘어난다.

**Risk:** 🟢 순수 정리. 다만 코어 DTO 를 건드리므로 백테스트·최적화·스트레스 3 소비자에 동시 파급.

**출처:** 2026-08-06 dead-code-sweep

---

### BL-600

**Priority:** P3
**카테고리:** Backend / 명명 (CONTEXT 헌법 충돌)
**Trigger:** `trading_sessions` JSONB 키를 마이그레이션할 일이 생겼을 때 · 신규 도메인 용어 정리 시
**Est:** M
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**`strategy/trading_sessions.py:26` 의 `TradingSession` 이 CONTEXT.md 의 _Avoid_ 이름과 충돌한다.**
헌법은 **TradingSession** 을 「미구현 phantom — 실제 lifecycle 은 LiveSignalSession + Order +
LiveSignalEvent」로 못박아 두었는데, 이 파일은 같은 이름을 **장중 시간대 필터**(asia/london/ny)로
쓴다. 의미가 다른 동음이의어라 헌법을 읽고 온 사람이 정확히 반대로 이해한다.

★**단순 rename 이 아니다.** 이 값은 `Strategy.trading_sessions` **JSONB 에 문자열로 영속**되고
(`SESSION_VALUES` frozenset), 백테스트 엔진과 라이브 executor 양쪽이 읽는다. 게다가 trading 도메인에
`TradingSessionClosed` 예외와 `TradingSessionTzNaiveReject` 가 따로 있어 grep 만으로는 안 갈린다.

**처리 방향:** ① JSONB 에 실제로 들어 있는 키/값 분포를 먼저 조사 ② 코드 심볼만 개명
(`MarketSession` 등) 하고 **영속 값은 건드리지 않는** 안이 최소 ③ 예외 이름 2종도 같이 볼지 판단.

**Risk:** 🟡 영속 데이터가 걸려 있어 rename 을 코드에만 적용해야 한다.

**출처:** 2026-08-06 dead-code-sweep

---

### BL-613

**Priority:** P3
**카테고리:** Backend / 구조 (핸들러 가시화 잔여)
**Trigger:** `live_signal.py` 를 다음에 크게 손댈 때 ([BL-580](#bl-580) 착수 회차와 겹친다)
**Est:** M
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 선행 BL-580=ACTIVE (2026-08-10 bl-trigger-triage)

**2026-08-04 handler-visibility 회차가 「안 한 것」 — 줄 수 부채는 남았다.**
그 회차의 목표는 줄 수가 아니라 **핸들러 가시성**이었고 그건 달성됐다(최대 `try` 본문 **845 → 8**).
남은 것:

- `_evaluate_session_with_engine` **506줄** — Kind B 추출(E8~E14) 미완. 프롬프트의 「200줄 이하」를
  운반자 기준으로는 못 채웠다.
- `_place_planned_entry` **236줄** · `_reconcile_conditional_entries_inner` **203줄** — 경계선.
- `_async_dispatch_event` **256줄** · 최대 `try` 본문 **225줄** — 그 회차 **범위 밖**이었다.
  ★**이제 이게 트리 최대다.**

★[BL-580](#bl-580) 과 같은 파일을 건드리므로 **한 회차에 묶어라** — 따로 하면 같은 코드를 두 번 읽는다.
★`_async_dispatch_event` 는 [BL-580] 쪽에서 **4곳이 판정 보류**로 잠겨 있다. 줄 수를 줄이겠다고
그 4곳의 감싸는 핸들러를 바꾸면 보류 판정의 전제가 깨진다 — 손대려면 census 부터 다시 판정해라.

**Risk:** 🟢 가시성은 이미 확보됐으므로 급하지 않다. 단 `_async_dispatch_event` 225줄 `try` 는
다음 사고 때 「어느 핸들러가 삼켰나」를 다시 어렵게 만든다.

---

### BL-615

**Priority:** P3
**카테고리:** Docs / 스택 규칙 크기 (ADR-027 후속)
**Trigger:** 스택 규칙을 다음에 손댈 때 ([ADR-027](decisions/027-nested-agents-md.md) 정착 후)
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**스택 규칙이 공식 권장 크기의 2배다** — `apps/api/AGENTS.md` **416줄** · `apps/web/AGENTS.md` **316줄**.
Claude Code 메모리 문서는 파일당 **200줄 이하**를 권장하며 이유를 명시한다 — 「Longer files consume more
context and reduce adherence」. [ADR-027] 배치에서는 그 디렉터리 파일을 여는 순간 **전량** 로드되므로,
백엔드 작업 세션의 실질 고정비다(416줄 ≈ 11k tok).

**덜어낼 1순위 = §1 Tech Stack 표** — 두 파일 모두 첫 절이 스택 나열인데, 이건 `pyproject.toml` ·
`package.json` 에서 **추론 가능한 정보**다(구 `.ai/common/global.md` §5 가 「추론 가능한 정보 제외」를
규정했던 바로 그 축이고, 그 규정은 ADR-026 으로 소멸했다). 2순위 = 코드 예시 블록 — 규칙 진술과
예시가 1:1 로 붙어 있어 길이의 상당분을 차지한다.

★**줄이면서 규칙을 지우지 마라.** 이 두 파일에는 `LESSON-004/005/006/019/020/066` 이 승격돼 있고
`docs/lessons.md` 가 **§ 번호로** 그것을 가리킨다. 절을 재배치하면 그 표의 § 참조도 함께 갱신해야 한다
(ADR-027 이 `nextjs-shared.md §3` → `apps/web/AGENTS.md §9` 로 갱신한 것과 같은 작업).

**Risk:** 🟢 동작에 영향 없다. 다만 「reduce adherence」가 사실이라면 **규칙이 안 지켜지는 쪽**으로
조용히 샌다 — 게이트로는 안 잡힌다.

---

### BL-616

**Priority:** P3
**카테고리:** DX / 워크트리 부트스트랩 (훅 결손 감지)
**Trigger:** 워크트리에서 훅 미작동이 또 관측되면
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)** — 관측된 결함(워크트리 1개의 훅 결손)은 2026-08-07 에 정상화했다. **감지 수단 부재**만 열려 있다.
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)

**부트스트랩을 우회해 만든 워크트리는 husky 훅이 없다.**

**사슬** — ~~`herdr-fleet.sh:234` 가 워크트리 생성 후 `worktree-bootstrap.sh --adopt-env` 를 부르고~~
(★2026-08-13 [ADR-030] 이 `herdr-fleet.sh` 를 제거 — 앞 고리는 이제 없다. 현행 진입은
`tools/scripts/worktree-bootstrap.sh --adopt-env` **직접 호출**이고 뒤 고리는 그대로다),
그 부트스트랩이 `pnpm install --frozen-lockfile`(:356)을 돌리면 `package.json` 의 `"prepare": "husky"` 가
실행돼 `.husky/_` 가 생긴다. 이 경로를 건너뛰면 `.husky/_` 가 없고, git 은 존재하지 않는
`core.hooksPath` 를 **경고도 exit code 도 없이 무시**한다.

**실태 (2026-08-07 전수 확인)** — 워크트리 5개 중 **4개는 정상**이었다(`node_modules` 가 실디렉터리 =
`pnpm install` 을 거쳤다는 지문). 결손은 `node_modules` 를 **심볼릭으로 때운** 1개뿐이었고,
`pnpm exec husky` 로 정상화해 메인과 파일 목록이 일치함을 확인했다.

★★**이 항목은 처음에 「워크트리 전반의 구조적 결함, `core.hooksPath` 가 상대 경로라서」로 등재됐다가
같은 회차에 반증됐다.** 표본 1개(결손 워크트리)만 보고 원인을 귀속했고 **정상 사례 4개를 확인하지
않았다.** 이 레포가 반복해서 적어 온 「기저율 먼저」를 그대로 어겼다. 상대 경로는 문제가 아니다 —
`.husky/pre-commit`·`pre-push` 는 트래킹되고, 없던 것은 husky 가 만드는 `_` wrapper 뿐이다.

**증상(그 워크트리에서 실제로 일어난 일)** — `pre-push` 의 main 직접 push 차단·브랜치 화이트리스트·
FE 회귀 방어와 `pre-commit` 의 lint-staged 가 전부 무력이었고, 그 결과 prettier 위반 14파일이
푸시됐다(같은 회차에 발견·수리). eslint·ruff 는 CI 가 받치지만 **prettier 검사 스텝은 CI 에 없다.**

**남은 축 = 감지 수단이 없다.** 훅이 안 도는 실패 모드는 **출력이 0줄**이라 「통과했다」와 구별되지
않는다. `worktree-bootstrap.sh` 는 env 파일 실재는 검증하지만 훅 작동은 검증하지 않으며, 애초에
그 스크립트를 안 돌린 워크트리에는 그 검증도 닿지 않는다.
★**판별법(수리 없이도 쓸 수 있다)** — 워크트리에서 `git push --dry-run <remote> <branch>` 를 돌려
`→ pre-push:` 로 시작하는 줄이 하나도 없으면 훅이 없는 것이다.
수리를 넣는다면 후보는 ⑴ 부트스트랩 검증에 `core.hooksPath` 실재 확인 한 줄 · ⑵ CI 에 prettier
검사 추가(로컬 훅과 독립한 이중 안전망). **2026-08-07 사용자 판정: 둘 다 하지 않는다** — 도구 체인은
이미 옳고 이번 사고는 「도구가 없어서」가 아니라 「도구를 안 거쳐서」 났다.

**Risk:** 🟡 재발 시 조용하다. 단 정상 경로(herdr / `worktree-bootstrap.sh`)로 만든 워크트리는 영향 없다.

---

### BL-617

**Priority:** P3
**카테고리:** Docs / 운영 절차 회수 (ADR-026 후속)
**Trigger:** [BL-071](#deferred--trigger-미도래--의도적-부활-가능-구-_deferredmd-승격-2026-08-06) 발동 시 (프로덕션 배포) · Bybit mainnet 전환 시
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-16 production-readiness 가 대상 목록을 정정(4종 → **3종**)하고 삭제 SHA·실측 크기를 확정했다. 회수는 여전히 안 한다
**트리거 판정:** 미도래 — [BL-071] 이 **아직 착수되지 않았다**. ★2026-08-16 [ADR-033] 이 G1 DB 호스팅을 확정해 [BL-071] 의 **선행은 풀렸다** — 종전 판정문 「외생 조건(실자금 cutover). 우리 의지로 만들 수 없다」는 이제 정확하지 않다. 트리거는 외생이 아니라 **우리가 [BL-071] 을 착수하는 시점**이다 (2026-08-16 production-readiness)

**「과거 기록」이 아닌 운영 절차가 문서 대개편에서 working tree 밖으로 나갔다.**
ADR-026 은 `docs/archive/` 를 통째로 삭제했는데, 그 분류 기준은 **위치**(폴더 이름)였지
**미래 유용성**이 아니었다. 그 결과 아직 **실행하지 않은 절차**가 「과거 원문」으로 함께 나갔다.

★★**2026-08-16 정정 — 4종이 아니라 3종이다.** mainnet 축은 이미 대체됐다:
`docs/reference/operations/bybit-mainnet-runbook.md`(26,325 B)가 **워킹트리에 존재**한다. 그것은
회수본이 아니라 [BL-003] 으로 **새로 쓴 문서**(`3915bd7b`, 2026-08-09 — 삭제 커밋 3일 후)다.
⇒ 남은 회수 대상은 Cloud Run · Grafana · 법무 **3종**.

★**삭제 커밋은 `0f0f0b06` 이 아니라 `94da86b1`** 이다(2026-08-06, 512 files / 123,707 deletions).
`0f0f0b06` 은 그 **직전 상태 참조용**이라 `git show 0f0f0b06:<경로>` 로 꺼내는 것은 맞다.

| 문서 (`git show 0f0f0b06:<경로>`)                                           | 크기 (실측)  | 언제 필요한가           |
| --------------------------------------------------------------------------- | ------------ | ----------------------- |
| `docs/archive/operations/deployment/2026-05-05-cloud-run-runbook.md`        | 39,493 B     | [BL-071] 프로덕션 배포  |
| `docs/archive/operations/observability/grafana-cloud-setup.md`              | 11,294 B     | 운영 관측성 켤 때       |
| `docs/archive/operations/legal/2026-04-25-legal-temporary-runbook.md`       | 5,087 B      | 외부 사용자 받기 전     |
| ~~`docs/archive/operations/trading/2026-04-21-bybit-mainnet-checklist.md`~~ | ~~11,425 B~~ | **해소** — 위 정정 참조 |

**측정 (2026-08-07)** — 머지 후 `docs/` 전체에서 **Cloud Run · Grafana · Prometheus · mainnet ·
법무 언급이 0건**이 된다. 그런데 `apps/api/prometheus/alerts.yml` · `apps/api/Dockerfile` ·
워크플로 4종은 **레포에 살아 있다** — 설정은 있고 「왜/어떻게」만 이력으로 빠지는 비대칭이다.

★**지금 되살리지 않는 것이 맞다** — 넷 다 3개월 이상 낡았고, 실제 배포·전환 시점에 어차피 다시 쓴다.
지금 `reference/` 로 옮기면 안 쓰는 채로 다시 썩는다. 필요한 것은 **꺼낼 수 있다는 사실의 보존**이고,
그 경로는 [`docs/README.md`](./README.md) §문서의 수명과 위치에 명시했다.

**수리** = 트리거 발동 시 위 경로에서 꺼내 **갱신한 뒤** `docs/reference/operations/` 로 재등재.
그대로 복사하지 않는다 (낡은 절차를 정본으로 만드는 것이 더 나쁘다).

**Risk:** 🟢 지금은 영향 없다. 단 트리거가 왔을 때 **이 항목이 없으면 그 문서들의 존재 자체를
아무도 모른다** — `docs/archive/` 375파일에는 파일 목록 색인이 남아 있지 않기 때문이다.

★★**2026-08-16 — 그 위험이 이미 현실이 됐다.** 이 항목이 근거로 든 tombstone 색인이
**워킹트리에 없다**: `git ls-files docs/archive` 결과가 `docs/archive/lessons-archive-2026H1.md`
**단 1개**이고, 삭제 커밋이 남겼다던 `docs/archive/dev-log/index-full-2026-08-02.md` 도 없다.
⇒ 지금 이 3종의 존재를 아는 유일한 기록은 **이 BL 본문 그 자체**다. 이 항목을 지우면
그 문서들은 사실상 사라진다.

---

### BL-625

**Priority:** P2
**카테고리:** 운영 / 배포 검증
**Trigger:** 새 호스트에 API 를 세울 때 · [BL-071] 프로덕션 배포 발동 시
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 외생 조건(Beta·프로덕션 배포). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)

**플레이스홀더 시크릿이 development 에서는 아무 게이트에도 안 걸린다.**

2026-08-07 FE 배포 실측: 서버 `apps/api/.env.local` 이 `CLERK_SECRET_KEY=sk_test_...`(문자 그대로
플레이스홀더)였는데 **API 는 정상 기동하고 `/health` 는 200 을 냈다.** 진짜 키는 루트 `.env` 에만
있었고(compose 워커만 그걸 읽는다) 호스트 uvicorn 은 인증 경로를 **한 번도 밟은 적이 없어서**
드러나지 않았다. 브라우저에서 로그인한 첫 요청이 **전건 401** 로 터지고 나서야 보였다.

`_enforce_production_safety`(`config.py`)는 이 계열을 이미 안다 — `SECRET_KEY`·`CLERK_SECRET_KEY`·
`WAITLIST_TOKEN_SECRET` 의 placeholder 를 기동 시점에 raise 한다. **단 `app_env == production`
일 때만이다.** development/staging 은 통과시킨다.

★같은 회차에 **2차 결함**도 물렸다 — 루트 `.env` 는 이 레포 관례상 `KEY=value  # [필수 …]` 로
인라인 주석을 단다. 값을 `cut -d= -f2` 로 옮기면 주석의 한글이 값에 섞이고, 그러면 401 이 아니라
**500** 이 난다(`clerk_backend_api` 가 헤더를 ascii 인코딩 → `UnicodeEncodeError`).
두 실패의 **증상이 다르다**는 것이 오히려 진단을 도왔다.

**수리 후보(택1, 미결정):** ⑴ placeholder 검사를 env 무관하게 **warning 으로** 항상 돌린다
⑵ `/healthz` 에 「Clerk 키가 placeholder 아님」 서브체크를 넣는다 ⑶ 배포 런북의 검증을
「로그인 후 데이터 화면」까지로 못박는다(이미 반영 — `frontend-deploy.md` §5).

**Risk:** 🟡 조용하다. 새 호스트마다 재발하고, 발견 시점이 **사용자가 처음 화면을 열 때**다.

---

### BL-623

**Priority:** P3
**카테고리:** 운영 / 클라우드 서버 체크아웃
**Trigger:** 서버에서 feature 브랜치를 다시 받아야 할 때
**Est:** XS
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**서버 클론이 `--single-branch` 라 feature 브랜치가 기본 fetch 로 오지 않는다.**

`remote.origin.fetch` 가 `+refs/heads/main:refs/remotes/origin/main` **한 줄뿐**이라
`git fetch origin && git checkout <branch>` 가 `pathspec did not match` 로 죽는다(2026-08-07 실측).
우회는 refspec 명시 — `git fetch origin <branch>:refs/remotes/origin/<branch>`.

**Risk:** 🟢 무해하지만 배포 때마다 한 번씩 걸린다. 근본 수리는
`git remote set-branches origin '*'` 한 줄인데, **소크가 도는 서버의 git 설정을 바꾸는 것**이라
창을 내릴 필요가 없다는 확인을 먼저 하고 싶어 이연했다.

---

### BL-624

**Priority:** P2
**카테고리:** 운영 / BL-003 게이트
**Trigger:** `QB_METRICS_URL`(원격 데몬 + ssh 터널 운영안)을 실제로 쓰려 할 때
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**게이트의 HTTP 갈래는 `PROMETHEUS_BEARER_TOKEN` 과 양립하지 않는다.**

`soak-gate.sh` 의 `curl -sf --max-time 20 "${METRICS_URL}"` 는 **인증 헤더를 안 보낸다.**
`PROMETHEUS_BEARER_TOKEN` 이 설정돼 있으면 `/metrics` 가 401 을 내므로 `METRICS_RC != 0` →
`DARKNESS=null` → **C5⑷ 가 영구 ✗** 다. `APP_ENV=production` 과 무관하다 — 토큰이 있으면
development 에서도 강제된다(`main.py` 의 `_verify_prometheus_bearer`).

**2026-08-07 실측으로 물렸다.** 서버 체크아웃이 [BL-620] **이전** 커밋이라 기본값이 HTTP 였고,
FE 배포 회차가 공개 `/metrics` 를 막으려고 베어러 토큰을 켜자 그 즉시 C5 가 죽었다. 체크아웃을
올려 직독으로 바꾸자 복구됐다(판별자 = API 로그의 `GET /metrics` 유무 — 게이트 출력의
`darkness_computed=✓` 는 **어느 경로로 성공했는지 말해주지 않는다**).

**지금은 발동하지 않는다** — 기본 경로가 직독이라 `QB_METRICS_URL` 을 명시할 때만 문제다.
수리하면 `QB_METRICS_BEARER` 를 읽어 `-H "Authorization: Bearer …"` 를 붙이는 한 줄이다.

**Risk:** 🟡 그 override 를 쓰는 순간 **C1/C2 를 다 채워도 PASS 불가**가 된다 —
[BL-620] 이 닫은 실패 계열이 override 갈래에 그대로 남아 있다.

---

### BL-632

**Priority:** P2
**카테고리:** Backtest / Trust Layer (외부 오라클 부재)
**Trigger:** 골든 값이 또 어긋났을 때 · 백테스트 정확성을 대외적으로 주장해야 할 때
**Est:** M
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**골든을 오라클로 승격했지만 그 골든은 여전히 엔진 자신의 출력이다 — 그리고 반순환 근거가 ATR 축을 안 덮는다.**

2026-08-07 backtest-fidelity 가 [BL-621]/[BL-022] 를 닫으면서 `test_golden_backtest.py` 를 smoke 에서
**71 스칼라 + 3 digest + 봉 위치를 전건 비교**하는 오라클로 승격했다. 그런데 그 기대값은
`regen_golden.py` 가 `run_backtest` 를 돌려 받아 적은 **엔진 자신의 출력**이다 ⇒ **회귀 감지기이지
정확성 오라클이 아니다.**

★**반순환 근거가 이 축을 안 덮는다** — 레포의 손계산 오라클 `test_golden_oracle_ema_sltp.py` 는
**4봉 · 고정 stop 95 / limit 110** 시나리오라 **`ta.atr` 를 한 번도 안 탄다**.
`test_golden_oracle_tv_pack.py` 는 합성 계열로 metric **함수**를 검증할 뿐 이 케이스의 진입/청산
집합을 검증하지 않는다. ⇒ **이번에 낡음을 만든 바로 그 축(ATR)이 구조적으로 오라클 밖이다.**

★★[BL-621] 본문이 이미 경고해 뒀다 — _"나중에 이 파일을 오라클로 승격하면 **틀린 값을 정본으로
고정**하게 된다."_ 그 승격을 했고, 답한 것은 「부검으로 값의 출처를 설명할 수 있게 됐다」이지
**「외부 오라클을 얻었다」가 아니다.** 이 구분을 문서 밖으로 흘리지 않기 위해 등재한다.

**수리 방향(택1):**
① ATR 기반 SL/TP 케이스에 **손계산 오라클**을 하나 더 만든다(작은 봉 수 + 손으로 계산 가능한 ATR).
② TradingView 에서 같은 전략·같은 봉을 돌린 결과를 **동결 픽스처**로 들여온다([ADR-020] 이 이연한 P-4).
③ 승격을 되돌리지 않고 **문서로만** 한계를 명시한다(현재 상태 — `git show 8abd0d67:docs/dev-log/2026-08-07-backtest-fidelity.md` §2.4 · 2026-08-13 docs-diet 로 본문은 git 에만 있다).

**Risk:** 🟡 지금은 무해하다(값의 출처가 설명 가능하므로). 단 다음 사람이 이 골든을
「정확성이 검증된 값」으로 읽으면 **틀린 값을 근거로 쓴다.**

---

### BL-636

**Priority:** P2
**카테고리:** Docs / 백로그 인덱스 검사
**Trigger:** 다음 백로그 인덱스를 편집할 때
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**backlog 인덱스 표가 파손돼도 `bl-audit.sh` 는 이를 감지하지 못 한다.**

실측에서 P1 표는 `BL-522` 다음의 빈 줄 하나 때문에 `BL-619` **1행**이 헤더 없는 조각이 됐고,
P2 표는 `BL-617` 다음의 빈 줄 하나 때문에 BL-625/621/627/628/629/630/633/632/631/624/626/623/620
**13행**이 헤더와 구분선 없는 조각이 됐다. GFM 에서 구분선 없는 파이프 줄은 표로 렌더되지 않아
그 14행은 문서상 보이지 않았다.

`tools/scripts/bl-audit.sh` 는 줄 형태 정규식 `^\|[ ]*\[BL-[0-9]+\]\(#bl-[0-9]+\)` 만 보고 H2 섹션이나
표 경계를 추적하지 않는다. 따라서 조각 속 행도 정상 행처럼 읽혀 3면 대조가 통과했다.

이번 회차는 빈 줄을 제거하고 조각을 재결합해 행 손실 없이 총 **104행**을 보존했다. 검사 축 추가는
하지 않았으므로 재발 방지는 없다.

**Risk:** 🟡 다음 편집자가 같은 자리에 빈 줄을 넣으면 인덱스 행이 다시 문서에서 보이지 않을 수 있다.

---

### BL-640

**Priority:** P3
**카테고리:** 운영 / 지표 세대 경계
**Trigger:** 게이트가 `.metrics` 값을 창 기준으로 해석할 때
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**`.metrics` 합산은 죽은 컨테이너 세대의 값을 함께 센다.**

`apps/api/.metrics` 는 역할과 컨테이너 id 로 파일이 갈린다. 파일을 전부 합산하면 죽은 이전 세대의
값까지 들어온다. 2026-08-08 실측에서 `engine_only_suppressed` 합산 **89** 중 **15가 이전 컨테이너**
세대의 값이었다. 창 안의 차분을 보려 해도 창 밖 값이 섞인다.

BL-620 이 게이트 취득 경로를 HTTP 에서 `.metrics` 직독으로 바꿨으므로 이 함정은 게이트 경로 위에
있다. 당장은 현 컨테이너 id 만 거르는 세대 필터 또는 창 시작 스냅샷과의 차분으로 읽어야 한다.

**Risk:** 🟡 이전 세대 누적을 이번 창의 관측값으로 오독할 수 있다.

---

### BL-710

**Title:** 전략 목록 성과 정렬·파생 필드의 규모 비용 3종 (현 규모에서는 무해)
**Category:** Backend / 성능
**Priority:** P3
**Trigger:** 전략 목록이 느려질 때 / 전략·백테스트가 수천 건이 될 때
**Est:** S-M
**상태:** ⏳ **대기 (트리거 미도래)** — 처방 미착수. 2026-08-12 codex G6 #1·#5·#6 을 평가자가 코드 대조로 채택했으나 발화 조건이 **규모**다.
**트리거 판정:** 미도래 — **규모 조건**이다. 현 실측(전략 3 · 완료 백테스트 7 · 활성 세션 0)에서는 발화하지 않는다 (2026-08-12 surface-demo-pack)
**출처:** 2026-08-12 surface-demo-pack G6

**원인 / 영향:** 셋 다 [BL-430]/[BL-427] 구현이 만든 것이고 **현 규모에서는 측정 가능한 피해가 없다.**

★**2026-08-17 — 이 문장이 원장의 다른 두 줄을 반증했다.** 본 항목(2026-08-12)은 두 BL 이 **구현됐음을 전제**로 그 성능 비용을 적는데, 같은 원장의 [BL-430]·[BL-427] 상태줄은 2026-08-09 판정 그대로 「미구현」이라 적고 있었다. 시간순으로 더 최신인 이쪽이 옳았고 두 상태줄을 Resolved 로 정정했다. **원장 안의 자기모순이 3일치 역행으로 남아 있었고 문서끼리 대조해선 아무도 안 봤다 — 코드가 잡았다.**

⑴ `apps/api/src/strategy/repository.py` 의 `latest_completed` 서브쿼리는 `status == COMPLETED` 만
걸고 **owner 나 현재 페이지의 `strategy_id` 로 좁히지 않는다.** `DISTINCT ON` 이 1:1 을 보장하므로
`total` 은 틀어지지 않지만, 비용이 **페이지 크기와 무관하게 전역 백테스트 수**에 비례한다.
★처방은 1줄이다 — 서브쿼리에 `Backtest.user_id == owner_id` 를 더한다(조인이 이미 그 사용자의
전략에만 붙으므로 **의미 보존**이다).

⑵ `apps/api/src/strategy/service.py` 의 `param_count` 는 행마다 `_strip_comments` +
`_strip_string_literals` + 정규식을 돈다. 그리고 `list_by_owner` 는 `defer` 가 없어 `pine_source` 를
**전량 로드**한다. 10MB 소스 100건이면 요청당 약 1GB 문자열이다(`pine_source` 크기 상한도 없다).
처방 = `param_count` 를 컬럼으로 영속(**alembic 필요**) 또는 목록 조회에서 `load_only`.

⑶ `apps/api/src/trading/models.py:471-484` 의 인덱스 3개는 `(user_id, is_active)` ·
`(is_active, last_evaluated_bar_time)` partial · `(user_id, strategy_id, exchange_account_id, symbol)`
partial-unique 다 — **`strategy_id` 선행이 없다.** `list_active_strategy_ids` 의
`strategy_id IN (...) AND is_active` 는 활성 세션 전량을 훑을 수 있다. 처방 = alembic 인덱스.

**Risk:** 🟢 정확성 문제는 없다. 규모가 커지면 지연으로 나타난다.

---

### BL-711

**Title:** `metrics` JSONB 손상값이 정렬 캐스팅에서 목록 전체를 500 으로 만든다 (선재 · 백테스트·전략 양쪽)
**Category:** Backend / 견고성
**Priority:** P3
**Trigger:** 손상 `metrics` 가 관측될 때 / 정렬 축을 늘릴 때
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)** — 처방 미착수. 2026-08-12 codex G6 #2 채택 + **선재임을 함께 확인**했다(손상 행 관측 0).
**트리거 판정:** 미도래 — 손상 `metrics` 행이 관측된 적이 없다. 발화 조건이 외생이다 (2026-08-12 surface-demo-pack)
**출처:** 2026-08-12 surface-demo-pack G6

**원인 / 영향:** 정렬 축은 `metrics["<key>"].astext.cast(Numeric)` 이다. 값이 숫자가 아니면
PostgreSQL 이 `invalid input syntax for type numeric` 을 던져 **목록 요청 전체가 500** 이 된다.
같은 응답 경로의 `metrics_summary_from_jsonb` 는 손상값을 `None` 으로 격리하는데 **정렬 경로만**
그 방어를 우회한다.

★**이 회차가 만든 것이 아니다** — `apps/api/src/backtest/repository.py:165-168` 이 동일한 패턴을
4축(`total_return`·`max_drawdown`·`sharpe_ratio`·`num_trades`)에 **먼저** 갖고 있다. 전략 목록
(`apps/api/src/strategy/repository.py`)이 그 노출을 물려받았을 뿐이다. **그래서 처방도 한 곳이 아니라
두 도메인에 같이 가야 한다.**

**권장 접근:** 캐스팅 앞에 숫자 판별을 두거나(정규식 `~ '^-?[0-9.]+$'` 후 캐스팅) 안전 캐스팅
함수를 쓴다. ★**한 도메인만 고치면 다른 쪽이 남는다** — 두 파일을 같은 PR 에서 다뤄라.

**Risk:** 🟡 발화하면 목록 화면이 통째로 죽는다. 다만 손상 행이 실제로 관측된 적은 없다.

---

### BL-712

**Title:** 전략 목록 표시 정합 2건 — lifecycle 이 archived 를 안 보고, 정렬 라벨이 방향을 안 말한다
**Category:** Frontend / backend (표시 계약)
**Priority:** P3
**Trigger:** 전략 목록 표시를 다시 손댈 때 / 아카이브 화면을 낼 때
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)** — 처방 미착수. 2026-08-12 codex G6 #4·#12 채택. ⑴은 **사용자 결정 선행**이다.
**트리거 판정:** 미도래 — ⑴은 **사용자 결정 선행**(칩 4번째 값을 만들 것인가)이고 ⑵는 UI 가 만들지 않는 URL 에서만 보인다 (2026-08-12 surface-demo-pack)
**출처:** 2026-08-12 surface-demo-pack G6

**원인 / 영향:**

⑴ `lifecycle` 파생은 `deployed → validated → draft` 3분기이고 **`is_archived` 를 보지 않는다.**
아카이브된 전략을 `?is_archived=true` 로 조회하면 `validated`/`deployed` 칩이 그대로 나온다.
`StrategyLifecycle` 에 `archived` 값이 없다. ★**캐논에도 칩이 3종뿐**이라(screen-06) 4번째를 만드는
것은 디자인 결정이다 — 그래서 미도래로 둔다.

⑵ 정렬 select 는 `order_by` 만 반영하고 라벨은 고정 문구(「수익률 높은 순」)다. UI 의 `pushSort` 는
축마다 방향을 고정해 넣으므로 정상 경로에서는 어긋나지 않지만, `?order_by=total_return&order=asc`
같은 URL(공유·수동 편집·뒤로가기)에서는 **오름차순 결과에 「높은 순」 라벨**이 붙는다.

**권장 접근:** ⑴ 사용자와 칩 4번째 값을 정한 뒤 파생에 `is_archived` 를 더한다. ⑵ 라벨을
`order` 에서 파생하거나, 화이트리스트 밖 조합을 기본값으로 정규화한다(후자가 [BL-709] 처방과 같은
자리에서 처리된다).

**Risk:** 🟢 데이터는 정확하고 라벨만 어긋난다.

---

### BL-713

**Title:** e2e 정체성 프로브가 `<title>` 부분일치라 고유 식별자가 아니다
**Category:** 테스트 / 게이트 판별력
**Priority:** P3
**Trigger:** 정체성 프로브가 거짓 통과하는 것이 관측될 때 / 같은 호스트에 앱이 늘 때
**Est:** XS
**상태:** ⏳ **대기 (트리거 미도래)** — 처방 미착수. 2026-08-12 codex G6 #10 채택. 현행 판별은 **실측으로 성공**하지만 우연에 의존한다.
**트리거 판정:** 미도래 — 실측으로 지금은 판별한다(`"Nexus Admin"` red). 거짓 통과가 관측되면 도래다 (2026-08-12 surface-demo-pack)
**출처:** 2026-08-12 surface-demo-pack G6

**원인 / 영향:** `apps/web/e2e/identity.setup.ts` 와 `global.setup.ts` 의 프로브는
`title.includes("QuantBridge")` 다. 다른 앱의 title 이 그 문자열을 **포함하기만** 하면 통과한다
(예: `QuantBridge migration docs`). 2026-08-12 실측에서는 `:3003` 의 title 이 `"Nexus Admin"` 이라
정확히 red 가 났지만, 그것은 **이름이 겹치지 않았기 때문**이다.

★같은 회차에 이 프로브가 **status 200 을 통과한 남의 앱**을 잡았다는 것을 기억해라 — status 만으로는
못 잡았고 title 이 잡았다. 그 마지막 판별자가 부분일치라는 것이 이 BL 이다.

**권장 접근:** 앱이 고유 마커를 내보내고 프로브가 그것을 본다 — 예: `<meta name="qb-app"
content="quantbridge">` 또는 루트 요소의 `data-app` 속성. title 검사는 보조로 남겨도 된다.

**Risk:** 🟢 지금은 판별한다. 우연이 깨지는 날 거짓 그린이 된다.

---

## Deferred — trigger 미도래 · 의도적 부활 가능 (구 `_deferred.md` 승격, 2026-08-06)

### BL-647

**Priority:** P3
**카테고리:** Frontend / CSS 규약 집행
**Trigger:** CSS 규약을 집행 가능하게 만들 때
**Est:** M
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**mobile-first 규약과 코드가 정반대다.**

`apps/web/AGENTS.md` §10 은 「데스크탑 기준으로 먼저 작성하는 방식 **금지**」라고 적어 왔는데,
`globals.css` 의 `@media` **30곳이 전부 `max-width`** 이고 `min-width` 는 **0건**이다.
C 이식 CSS 가 `_kit.html`(desktop-first)의 바이트 정본이라 구조적으로 그렇다.

2026-08-08 에 **규칙의 사거리를 좁혀** 봉합했다 — 신규 Tailwind 컴포넌트는 mobile-first 필수,
KITPORT·화면 전용 CSS 는 그 파일의 desktop-first 관례를 따른다. **전면 전환은 미결이다.**

★전환하려면 `_kit.html` 17벌 재검증이 따라온다(`design-canon-kit-port.test.ts` 가 바이트
대조). 비용이 크므로 「하지 않는다」도 정당한 결론이다 — 다만 **결론을 적어야** 다음 사람이
같은 모순을 다시 발견하지 않는다.
**Risk:** 🟢 동작 무관. 규약 신뢰도 문제.

---

### BL-652

**Priority:** P3
**카테고리:** Backend / 테스트 인프라 (cold CI import·bytecode 비용)
**Trigger:** [BL-598] ② (파싱 디스크 캐시)를 착수할 때 · CI 샤드 수를 늘리려 할 때
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 선행 BL-598=ACTIVE (2026-08-10 bl-trigger-triage)

**[BL-598] 이 재고 결론 낸 것은 전부 `warm` 프로세스다. cold 축은 아직 아무도 안 쟀다.**

`apps/api/scripts/profile_corpus_parse.py` 의 `section_import` 은 **첫 서브프로세스를 의도적으로
버린다** — 그 첫 회가 **17초**이고 안에 bytecode(`.pyc`) 컴파일 + OS 파일 캐시 워밍이 섞여
있어서다. 버린 뒤 3회를 재서 나온 값이 **0.26s** 이고, [BL-598] 은 그것으로 가설 (a)(import
워밍업)를 기각했다. 그 기각은 **[BL-598] 이 정의한 현상**(같은 머신·warm 프로세스에서
`test_ast_classifier[i3_drfx]` 단독 42.66s vs 스위트 안 4.58s)에 대해서는 옳다.

**옳지 않은 것은 일반화다.** CI 러너는 매 잡이 **cold** 다 — `.pyc` 도, OS 파일 캐시도, 그리고
샤드를 나누면 **샤드마다** 없다. 버려진 17초가 CI 에서 샤드 수만큼 반복되는지는
**측정된 적이 없다.** 3샤드면 그것만으로 최악 51초이고, 샤드를 더 쪼갤수록 커진다.
[BL-598] 의 처방(파싱 결과 디스크 캐시)은 **파싱 비용만** 지우고 이 축은 그대로 남긴다 —
import 와 bytecode 컴파일은 캐시 히트여도 일어난다.

**재는 법:** ⑴ `__pycache__` 를 지우고 `_IMPORT_CHILD` 를 **첫 회부터** 기록하는 모드를
프로파일러에 추가(현재는 버린다) ⑵ CI 에서 잡별 `python -X importtime` 상위 항목 수집
⑶ `uv` 캐시·`__pycache__` 를 actions/cache 로 나르는 것이 이 17초를 지우는지 대조.

★**착수 전 확인할 것** — GitHub Actions 러너가 `.pyc` 를 잡 사이에 나르는지는 캐시 설정에
달렸다. 「cold 다」를 가정하지 말고 **런 로그로 확인부터** 해라([BL-598] 이 정확히 반대 방향의
가정으로 물린 자리다).

**Risk:** 🟢 CI 시간 문제이고 프로덕션과 무관. 단 [BL-598] ② 를 끝내고도 CI 가 기대만큼 안
줄면 **원인 후보가 여기밖에 안 남는다** — 그때 이 항목이 없으면 처음부터 다시 잰다.

**연결:** [BL-598](#bl-598) (모집단은 같고 온도가 다르다)

**출처:** 2026-08-08 zero-touch-bundle (codex challenge F3 — cold 표본을 버린 것이 결론의 사거리를 좁힌다)

---

### BL-654

**Priority:** P2
**카테고리:** Backend / backtest engine (모델 충실도)
**Trigger:** 고레버리지 백테스트를 신뢰해야 할 때 / [BL-466] 후속
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**증거금 게이트가 진입 비용을 판정에 넣지 않는다.** `apps/api/src/strategy/pine_v2/strategy_state.py`
의 `_open_trade` 최종 검증(`available = gate_equity - Σ margin_used`)과 `_can_afford_entry` 가
**둘 다 초기 증거금만** 비교하고, **바로 아래에서 차감하는 진입 leg 비용**을 가용 자본에서 빼지 않는다.

**갈리는 수치 (codex challenge 제시 · 코드 대조 완료):** 자본 $1,000 · 125x · 비용률 0.069% ·
명목 $118,750 ⇒ 증거금 $950 으로 **통과**한다(버퍼 95% 한도에 정확히 닿는다). 그런데 진입 수수료
$81.94 를 차감하면 `gate_equity` 가 **$918.06** 이 되어 **유지 중인 증거금 $950 보다 작다** —
실제 잔고로는 낼 수 없는 주문이 백테스트에서 허용된다.

★**[BL-460] 이 고친 것과 다른 축이다.** BL-460 은 **gross(`running_equity`) → net(`gate_equity`)**
축이었고 이 회차에 닫혔다. 여기는 **「증거금」 대 「증거금 + 진입 비용」** 축이고 **선재**다 —
이 회차가 만든 회귀가 아니다.

★**착수 시 확인할 것:** 이 수리는 **진입 거절을 늘린다** ⇒ golden baseline 이 움직일 수 있다.
[BL-466] (c)안이 산 「baseline 무변경」과 충돌하는지 먼저 재고, 움직인다면 그것이 **의도된 정정**임을
golden 갱신 커밋에 적어라.

**Risk:** 🟡 저레버리지에서는 버퍼가 흡수한다 — 갈리는 것은 버퍼 한도에 닿는 고레버리지뿐이다.

**연결:** [BL-460](#bl-460) (같은 함수, 다른 축) · [BL-466](#bl-466) (golden 무변경 계약)

**출처:** 2026-08-08 soak-mortality-repair (codex challenge P1 — 코드 대조로 수치 재현 확인)

---

### BL-655

**Priority:** P2
**카테고리:** Backend / trading (계정 축)
**Trigger:** 같은 `exchange_uid` 에 **쓰기 가능한** 행이 2개 생기면 / 실자금 전환 전
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)

**계정 dedup 이 쓰기 가능한 형제 행 둘을 만나면 주문을 누락한다.**
[BL-605] 수리는 `dedupe_accounts_by_exchange_uid`(`apps/api/src/trading/account_identity.py`)로
`exchange_uid` 당 **대표 1행**만 스윕한다. 그런데 스윕은 그 뒤로 대표 `account.id` **하나로만**
매칭·backfill 한다(`apps/api/src/tasks/trading.py:1949` · `:1987` · `:2027`). 버려진 형제 행에 달린
주문의 청산은 대표 계정에서 `unknown` 으로 기록되고 그 `Order.realized_pnl` 은 동기화되지 않는다.

★**현재 데이터에서는 발화하지 않는다 — 그래서 P2 다.** 실측(2026-08-08) `exchange_uid`
**558689281** 형제 2행 중 `0277c150` 이 **`read_only=t`** 이고, 대표 선택 규칙 ⑵ 가 `read_only` 행을
대표로 뽑지 않으므로 쓰기 가능한 `19a8166a` 가 대표가 된다. 주문은 쓰기 가능한 행에만 달리므로
누락이 없다. ★**위험의 실체는 「그 배치를 막는 DB 제약이 없다」** 는 것이다.

**처방 후보:** ⑴ 거래소 **조회**만 uid 당 1회로 접고 **매칭·backfill 은 형제 계정 ID 전량**에
적용한다(가장 곧다 — [BL-634] 소유권 집합이 이미 「형제 행 전량」을 쓰므로 **두 축이 일관돼진다**)
⑵ 주문을 canonical 계정으로 통일한다(이관 필요) ⑶ 쓰기 가능한 형제 2행을 **DB 제약으로 금지**한다.

**Risk:** 🟡 잠복. 발화하면 손익이 조용히 미동기화된다(원장 구멍 계측을 다시 흔든다).

**연결:** [BL-605](#bl-605) (이 dedup 을 도입한 수리) · [BL-634](#bl-634) (계정 축을 형제 전량으로
정한 결정 — 스윕이 그것과 어긋나 있다) · [BL-592](#bl-592) (형제 행 오라벨의 원 관측)

**출처:** 2026-08-08 soak-mortality-repair (codex challenge P2 — 전제는 현재 미성립, 코드 경로는 실재)

---

### BL-658

**Priority:** P3
**카테고리:** Docs / decisions (소급 ADR)
**Trigger:** Optimizer 설계를 실제로 바꿀 때 (알고리즘 교체 · scikit-optimize 이탈 · GA 파라미터 변경)
**Est:** M
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-09 등재. **착수 금지**(이 회차 비목표 = M/L 급).
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**`decisions/013-optimizer-strategy.md` 를 소급 작성해 ADR-013 결번을 닫는다.**

[BL-504](#bl-504) 가 2026-08-09 에 인용 축을 닫았다 — 살아 있는 인용 4곳에 git tombstone 경로를 병기했다.
남은 것은 **실체를 `decisions/` 로 승격**하는 일이고, 그것은 별개 작업이다.

**실체(확인됨):** `docs/dev-log/2026-05-12-sprint54-bayesian-genetic-grammar-adr.md` — **24,703바이트**,
도입 `9c93fa70`(PR #258), 삭제 `94da86b1`(2026-08-06 문서 대개편).
읽는 법 = `git show 94da86b1^:docs/dev-log/2026-05-12-sprint54-bayesian-genetic-grammar-adr.md`.
인용되는 절이 전부 그 안에 있다 — `## 6.`(§6 #8 = BL-235 deferred, `:202`) · `### 7.2` · `### 8.2` ·
`## 5. References` · `## 7~9` Sprint 55/56/57 amendment 3종.

★**소급 작성은 결정을 새로 만드는 게 아니라 이미 실행된 결정을 기록하는 것이다.**
없는 근거를 지어내지 말고 실제 코드(`apps/api/src/optimizer/executors/`)와 **대조**해라 —
dev-log 가 적은 결정과 코드가 어긋나면 **코드가 맞다**([ADR-026] 「지금 무엇을 하는가」 축).

★**같이 볼 것 — ADR-019 는 결번이 아니다.** `decisions/019-worker-auto-rebuild.md` 가 실재한다(Sprint 38).
`docs/dev-log/INDEX.md:141` 의 `2026-05-05 · ADR-019 Surface Trust Pillar` 는 **ID 중복 호칭**이므로
그 줄을 고칠지도 이 작업에서 함께 정한다(고칠 거면 `020-trust-layer-ci-design.md:3` 의 renumber 서술과 정합시켜라).

**Risk:** 🟢 동작 무영향. 비용은 24,703바이트를 읽고 코드와 대조하는 시간이다.

**연결:** [BL-504](#bl-504) (인용 축 — 닫힘) · [ADR-026](decisions/026-documentation-ssot.md) (tombstone 규약)

**출처:** 2026-08-09 backlog-sweep ([BL-504] G0 에서 실체가 git 에 살아 있음을 확인하고 분리)

---

### BL-659

**Priority:** P3
**카테고리:** Test infra / 디자인 캐논 게이트
**Trigger:** 디자인 캐논 게이트가 빨개졌을 때 / 캐논 스윕 착수 시
**Est:** XS
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**`design-canon-calibration.spec.ts` 의 `screen-06-strategies-list.html` 케이스가 간헐 실패한다.**

2026-08-09 backlog-sweep-4lane W3 관측 — `pnpm e2e:design-canon` **7회 중 2회** 이 케이스
하나만 빨개졌다(나머지 실행은 42/42). 같은 커밋에서 **연속 3회 42/42** 이고, `git stash` 로
내 diff 를 걷어낸 뒤에도 같은 케이스가 통과/실패를 오갔다 — 즉 **코드 회귀가 아니다.**

★**위험은 실패 자체가 아니라 오독이다.** 이 게이트는 W3 회차에서 [BL-548](#bl-548) ·
[BL-645](#bl-645) 의 음성 대조로 쓰였다. 간헐 실패를 자기 변경의 회귀로 읽으면 멀쩡한
수리를 되돌리게 된다. 이번 회차도 처음 빨개졌을 때 stash 대조를 하고서야 무관함을 확정했다.

★**원인은 조사하지 않았다.** 대상이 정적 HTML 이라 서버 상태와 무관해 보이는데도 흔들린다는
점이 단서다 — 폰트 로딩 타이밍 또는 대비 계산 경계값을 의심한다. **[가정]** 이며 미확인이다.

**권장 접근:** 실패 실행의 하드 실패 목록을 성공 실행과 diff 해 흔들리는 항목을 특정한다.
그 항목이 대비 경계값이면 임계 근처 표본을 고정하거나 폰트 로딩 완료를 기다린다.

**Risk:** 🟢 게이트 신뢰성만 해당. 프로덕션 코드 영향 없음.

**출처:** 2026-08-09 backlog-sweep-4lane W3 (BL-548·BL-645 음성 대조 중 관측)

---

### BL-660

**Priority:** P3
**카테고리:** Test infra / 골든 재생성 (도구 산출 ↔ 포매터 충돌)
**Trigger:** 골든을 의도적으로 갱신할 때 / `regen_golden.py` 를 CI 에 넣을 때
**Est:** XS
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**`--confirm` 이 쓰는 포맷과 커밋본의 포맷이 구조적으로 다르다.**

pre-commit 의 `prettier --write` 가 `*.json` 을 대상으로 하므로 커밋된
`golden/<case>/expected.json` 은 배열이 **한 줄로 접혀** 있다. 반면 `regen_golden.py` 는
`json.dumps(generated, indent=2)` 로 쓰므로 **원소당 한 줄**이다. 그래서 `--confirm` 을 한 번만
돌려도 트리가 dirty 해진다 — 2026-08-09 실측 `+29/-2` (값은 하나도 안 바뀌고 전부 재포맷).

★**`--check` 는 이 어긋남을 구조적으로 못 본다.** `_differences()` 가 비교하는 것은
`json.loads` 한 **값**이라 포맷에 무관하기 때문이다. 즉 `--check` 는 green 인데 `--confirm` 은
트리를 더럽히는 상태가 정상으로 유지된다.

**왜 지금 아픈가 (실사례):** [BL-627](#bl-627) 을 고치면서 「`--check` 가 통과하니 산출이 커밋본과
바이트 동일하겠지」라고 넘겨짚었다가 **자기 반증**했다. 이 어긋남이 바로 그때 `test_regen_roundtrip_is_stable`
이 정본을 **시험 시간의 31.8%** 동안 dirty 로 만들던 실체다(표본 906 중 288).

**처방 후보:** ⑴ 스크립트가 `prettier` 와 같은 서식으로 쓴다 ⑵ `.prettierignore` 에 golden 을 넣어
`json.dumps` 서식을 정본으로 삼는다 ⑶ 쓰기 직후 `prettier --write` 를 부른다. ★어느 쪽이든 **한쪽을
정본으로 정하는 것**이 요점이고, 정한 뒤에는 `--check` 가 서식까지 보게 할지 따로 정해야 한다.

**Risk:** 🟢 값 정확성에는 영향이 없다. 다만 골든 갱신 diff 의 신호 대 잡음비를 망가뜨린다.

**출처:** 2026-08-09 backlog-sweep-4lane (W2 — BL-627 수리 중 부수 발견)

---

### BL-669

**Title:** `flatten` 이 미체결 조건부 진입을 **보고만** 하고 취소하지 않는다
**Category:** Backend / trading (청산) · 운영 CLI
**Priority:** P2
**Trigger:** [BL-517] 종결 + 거래소 접촉 검증이 가능한 회차
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — [BL-661] 이 거짓 성공만 없앴다(보고 + exit 3). 취소는 미착수
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 guards-blind-spots (사용자 결정으로 범위 분리)

**원인 / 영향:** [BL-661] 의 권장 접근은 「포지션이 없어도 미체결 조건부가 있으면 그것을
취소하도록」이었는데, 2026-08-10 회차는 **보고까지만** 했다. 고아 조건부는 여전히
운영자가 손으로 취소해야 한다.

**왜 이번에 안 했나 (사용자 판정 5)** — ⑴ [BL-661] 의 P1 은 **거짓 성공**이지 취소 부재가 아니다
⑵ 취소는 비가역이고 미룸은 가역이다(같은 선택을 `live_signal.py:1467-1512`
`_cancel_planned_entry` 가 이미 한다 — 취소 대신 `"deferred"` 를 돌려 janitor 로 넘긴다)
⑶ `soak-restart.sh:347-363` 의 `EXCLUSIVE` 가드가 하류에서 fail-closed 다
⑷ 「ours 만 취소」는 `_ownership_scope` 위에 서는데 [BL-517] 이 그 축을 다루는 중이다
⑸ 그 회차는 거래소 접촉 금지라 취소 경로를 **검증할 수 없었다**.

**권장 접근:** `order_link_id` 소유권으로 ours 만 취소하고 foreign 은 보고한다
(`live_session_admin.py:246-255` 의 status 표기와 같은 판별자). `close_service` 에는
소유권 스코프가 없으므로 `OrderRepository` 주입이 선행이다.
**Risk:** 🔴 비가역 · 실자금

---

### BL-670

**Title:** `docs/status.md` 가 **존재하지 않는 절**을 근거로 인용한다 (`[ADR-025] §⑧`)
**Category:** Docs / SSOT
**Priority:** P3
**Trigger:** 문서 감사 시 / 그 문장을 근거로 쓸 때
**Est:** XS
**상태:** ⏳ 대기 (트리거 미도래)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 guards-blind-spots (사용자가 제기 → grep 으로 확정)

**원인 / 영향:** `docs/status.md:396` 이 「원장 못 읽은 tick 은 리컨사일을 1 tick 미룬다
(취소는 비가역, 미룸은 가역)」를 **[ADR-025] §⑧** 으로 돌린다. 그런데
`025-conditional-fill-ownership.md` 에는 **번호 절이 없고**(전부 이름 헤딩),
`비가역` 은 `docs/decisions/` **전체에 0건**이다(grep 실측). **죽은 앵커다.**

★원칙 자체는 유효하다 — 정본은 **구현**이다: `live_signal.py:1467-1512` 가 취소 대신
`"deferred"` 를 돌려 janitor 로 넘기고(`:1499`), gap-resync 는 `_GAP_RESYNC_DEFER_KEY`(`:273`)로
같은 선택을 한다.

**권장 접근:** `status.md` 의 인용을 ADR 앵커에서 **구현 경로**로 교체한다.
★2026-08-10 회차는 `status.md` 를 안 건드렸다(레인 충돌 회피) — 등재만 했다.
**Risk:** 🟢

---

### BL-666

**Title:** `reactCompiler: true` 검토 — FE 전체 `memo()` 0건인 채로 수동 처방을 반복하고 있다
**Category:** Frontend / 빌드
**Priority:** P3
**Trigger:** `rerender-*` 계열 결함이 또 등재될 때 · Next 16 업그레이드 회차
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — [BL-663] 에서 분리했다. 켜지 않았고 측정도 안 했다 (2026-08-09 fe-perf-quartet)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-09 fe-perf-quartet ([BL-663] 범위 분리)

**원인 / 영향:** `next.config.ts` 에 `reactCompiler` 가 없다. `eslint-plugin-react-compiler`(19.1.0-rc.2)는 devDependency 로 있지만 **린트만 한다.** 그래서 FE 전체에 `memo()`/`React.memo` 가 **0건**인 채로 재렌더 범위를 컴포넌트 분리로 하나씩 손봐 왔다([BL-663] 이 그 4번째다).

**권장 접근:** ⑴ `reactCompiler: true` 를 켜고 빌드·번들·테스트 델타를 잰다 ⑵ H-3(render body 에서 `ref.current` 대입 금지, `apps/web/AGENTS.md`)이 이미 컴파일러 호환을 전제하므로 위반 잔여를 먼저 센다 ⑶ 켠 뒤에도 [BL-663] 같은 **구독 위치** 문제는 안 사라진다는 것을 명시해라 — 컴파일러는 메모이제이션을 자동화하지 나쁜 구독 경계를 옮겨 주지 않는다.
**Risk:** 🟡 빌드 전역 스위치라 회귀 표면이 넓다. 단독 회차로 잡아라.

---

### BL-668

**Title:** `e2e:authed` backtest form 2건이 로컬에서만 빨갛다 (CI 는 초록)
**Category:** DX / 테스트 환경
**Priority:** P3
**Trigger:** 로컬에서 `pnpm e2e:authed` 를 돌릴 때 · 격리 스택을 새로 만들 때
**상태:** ⏳ 대기 (트리거 미도래) — 원인 미규명. 코드가 아니라 환경이라는 것까지만 좁혔다 (2026-08-09 fe-perf-quartet)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-09 fe-perf-quartet (final-gates 에서 발견 · 음성 대조 2회)

**원인 / 영향:** `e2e/sprint46-tier1-critical.spec.ts:69`(#1 backtest form 422 unsupported_builtins)와 `e2e/sprint46-tier3-nth.spec.ts:489`(#20 friendly_message 카드)이 로컬 격리 스택(`:3100`/`:8100`)에서 일관 실패한다. 증상은 **하나**다 — `POST /api/v1/backtests` 가 아예 안 나가서 `waitForRequest` 가 15초 타임아웃한다. 폼 제출 **이전** 단계에서 막힌다는 뜻이다.

★★**음성 대조 2회로 코드 축을 배제했다:**

1. `git checkout 85970b83 -- apps/web/src` 로 **main 코드**를 씌우고 같은 두 건을 태웠다 → **동일하게 2 failed / 1 passed.** 브랜치 회귀가 아니다.
2. ~~**CI 는 초록이다** — PR **#574 에서 `e2e` SUCCESS**, 그 뒤 #575·#576·#577 은 전부 문서 전용이라 `e2e` 가 SKIPPED. ⇒ CI 가 통과시킨 FE 코드가 지금 main 과 같다.~~
   → ★★**2026-08-17 [BL-789] 로 무효.** 이 근거는 **성립한 적이 없다.** `ci.yml` 의 `e2e` 잡은 `--project=chromium` / `chromium-live-smoke` / `chromium-design-canon` **3종만** 부르는데, 이 항목의 대상인 `e2e:authed` backtest form 2건은 `chromium-authed` 소속이라 **CI 에서 한 번도 실행된 적이 없다**(spec 29개 중 20개가 같은 처지). ⇒ 「PR #574 의 `e2e` SUCCESS」는 **이 두 건에 대해 아무 말도 하지 않는다.** 음성 대조로 쓸 수 없다.
   ★그러므로 아래 「⇒ 남은 축은 로컬 격리 스택의 데이터/시드 상태다」라는 **좁히기 자체가 근거를 잃었다** — 코드 축이 배제된 적이 없다. 재착수하면 **거기서부터** 다시 봐라.

⇒ 남은 축은 **로컬 격리 스택의 데이터/시드 상태**다. 폼이 제출까지 못 가는 것이므로 전략 목록·`parse_status`·coverage 전제가 CI 시드와 다를 가능성이 높다.

★**이것이 게이트를 오염시킨다** — `final-gates.sh` 의 `e2e authed` 가 항상 FAIL 이면 그 게이트는 **신호를 잃는다**(진짜 회귀도 같은 빨강으로 보인다).

★★**같은 회차에 별개의 flake 1건도 드러났다 — `e2e/trading-ui.spec.ts:108`(kill switch API 오류 → 황색 배너).** 전체 스위트 2회 중 **1회만** 실패했고(`ks-error-banner` 미발견 + 30초 테스트 타임아웃), **격리 실행 3/3 통과**했다. ★이 파일은 이 회차가 실제로 만진 `kill-switch-banner.tsx` 의 시험이라 회귀를 의심해 일부러 3회 태웠다 — **회귀가 아니라 flake 다.** 위 2건(항상 실패)과 **다른 현상**이므로 같이 묶어 고치지 마라.

**권장 접근:** ⑴ `test-results/.../error-context.md` 와 trace 를 열어 어느 검증에서 멈추는지 본다 ⑵ CI 의 e2e 시드 절차와 로컬 격리 스택 시드를 대조한다 ⑶ 차이가 시드면 로컬 시드 타깃에 반영하고, 아니면 이 BL 의 전제를 다시 세운다.
**Risk:** 🟢 프로덕션 코드 무관. 단 게이트 신뢰도를 깎는다.

---

### BL-680

**Title:** 공개 공유 URL `/share/backtests/[token]` 에는 리포트 섹션 앵커가 아예 없다
**Category:** Frontend / backtest (공유)
**Priority:** P3
**Trigger:** 공유 링크로 특정 섹션을 가리키고 싶다는 요구가 나올 때
**Est:** M (같은 데이터를 토큰 경로에서 다시 조립해야 한다)
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-10 fe-shareable-urls 에서 코드 대조로 확인. 사거리 밖이라 열어 둔다.
**트리거 판정:** 미도래 — 외생 조건(사용자 결정·요청). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 fe-shareable-urls, codex G1 설계 검증 발견 2

**원인 / 영향:** [BL-397] 이 준 앵커 10개는 `/backtests/[id]` 의 `BacktestReportShell` 에만 있다.
그런데 화면의 「공유」 버튼은 API 가 준 `share_url_path` 를 그대로 복사하고
(`share-button.tsx:29-39`), 그 공개 URL 은 `/share/backtests/[token]` 이다.
그 페이지는 `BacktestReportShell` 을 **참조조차 하지 않는다**(`page.tsx` 에 해당 import 0건,
고정 `id=` 0건). 즉 **사용자가 실제로 공유하는 링크에는 `#trades` 가 붙을 대상이 없다.**

★따라서 [BL-397] 이 닫은 것은 「로그인한 사용자끼리 주소창을 복사해 나누는 경로」다.
공개 공유 경로는 별개이고, 두 화면이 같은 리포트를 서로 다른 컴포넌트로 그린다는 사실 자체가
이 항목의 비용을 정한다.

**Risk:** 🟢 (지금 깨진 것은 없다. 없는 기능이다)

---

### BL-681

**Title:** 백테스트 상세 라우트가 Suspense 없이 클라이언트 `isLoading` 분기를 쓴다 — 앵커 재조정이 필요해진 뿌리
**Category:** Frontend / backtest (렌더 경로)
**Priority:** P3
**Trigger:** 상세 라우트를 스트리밍으로 바꿀 때 / [BL-397] 의 해시 효과를 걷어내고 싶을 때
**Est:** M
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-10 fe-shareable-urls 에서 실측. 이 회차 사거리 밖.
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 fe-shareable-urls, G5 `/vercel-react-best-practices` (`async-suspense-boundaries`)

**원인 / 영향:** `backtests/[id]/page.tsx` 는 서버 prefetch 도 `HydrationBoundary` 도 없이
클라이언트 `BacktestDetailView` 만 렌더하고, 그 컴포넌트는 `isLoading`/`isError` 를 손으로
분기한다. `apps/web/AGENTS.md` §3 이 명시적으로 금지하는 패턴이다
(「`if (isLoading)` / `if (error)` 남발 금지 → `Suspense` + `ErrorBoundary` 로 위임」).

★**이것이 [BL-397] 에서 마운트 1회 해시 재조정 `useEffect` 를 넣어야 했던 이유다.** 리포트가
문서 로드 시점에 DOM 에 없으니 네이티브 fragment 위치결정이 빈손으로 끝난다.
비교 대상 — 목록 라우트(`backtests/page.tsx`)는 이미 `auth()` + `prefetchQuery` +
`HydrationBoundary` 를 쓴다. **같은 도메인 안에서 두 라우트가 다른 규약을 따르고 있다.**

★★**단, 「Suspense 로 바꾸면 해결된다」는 틀렸다** — 이 항목의 첫 판이 그렇게 적었고
codex G6 적대 리뷰가 반증했다. **클라이언트** Suspense fallback 뒤에 리포트를 꽂는 구조는
여전히 fragment 위치결정 **이후**다. 효과를 없앨 수 있는 조건은 하나뿐이다 —
**대상 엘리먼트가 최초 HTML 에 들어 있을 것**(서버 렌더 또는 prefetch + 하이드레이션).

**권장 접근:** 상세 라우트를 목록 라우트와 같은 형태(서버 prefetch + `HydrationBoundary`)로
맞춘 뒤, `backtest-report-shell.tsx` 의 해시 효과가 **없어도** e2e
`report-section-anchors.spec.ts` 가 green 인지로 판정한다. 그 시험이 이미 판별자다.

**Risk:** 🟡 (상세 화면 전체의 로딩 계약을 바꾼다 — 회귀 표면이 넓다)

---

### BL-682

**Title:** 세션 생성 직후 잠깐 「목록에서 밀려났습니다」로 오진한다 (background refetch 창)
**Category:** Frontend / live-sessions UX
**Priority:** P3
**Trigger:** 세션 생성 흐름을 손볼 때 / 사용자가 이 깜빡임을 보고할 때
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-10 fe-shareable-urls 의 codex G6 적대 리뷰가 제기. ★**이 diff 가 만든 것이 아니라 종전 `useState` 판에도 있던 동작**임을 코드 대조로 확인했다.
**트리거 판정:** 미도래 — 외생 조건(사용자 결정·요청). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 fe-shareable-urls, codex G6 발견 1

**원인 / 영향:** `LiveSessionForm` 은 생성 성공 즉시 `onSuccess(session)` 을 부르고, 무효화 래퍼는
목록 refetch 를 `await` 하지 않는다(`use-invalidating-mutation.ts`). **기존 목록 캐시가 있으면
background refetch 중에도 `isPending` 은 false** 이므로, 코크핏은 「선택 id 는 있는데 목록에 없다」
= `live-session-stopped-notice` 로 떨어진다. 새 응답이 오면 상세로 바뀐다.

★**종전 판도 같았다** — `onSuccess` 가 `setSelectedId(session.id)` 를 했고 같은 3분기를 탔다.
[BL-551] 이 그 id 를 URL 로 옮겼을 뿐 이 창은 그대로다. 즉 **회귀가 아니라 기존 결함의 재발견**이다.

★현행 시험이 이것을 못 잡는 이유도 기록해 둔다 — vitest 는 `replace` 인자만 보고 다음 렌더를
하지 않으며, e2e 는 폼 제출을 하지 않는다. **닫을 때 이 두 구멍을 함께 메워야 한다.**

**권장 접근:** ⑴ 생성 응답으로 목록 캐시를 낙관적으로 채우거나 ⑵ `isFetching` 중에는 중단 안내
대신 로딩 안내를 쓴다. ⑵ 는 [BL-551] 이 이미 만든 `isPending` 분기 옆이라 값싸다.
**Risk:** 🟢 (자기 해소되는 깜빡임 · 데이터 오류 아님)

---

### BL-683

**Title:** `useSearchParams` 가 Suspense 경계 없이 들어와 `/trading` 을 prerender 밖으로 밀어냈다
**Category:** Frontend / trading (성능)
**Priority:** P2
**Trigger:** FE 성능 회차 · 또는 `/trading` 초기 페인트가 느리다는 보고
**Est:** S (page.tsx 에 Suspense 한 겹 = 5분. 복원폭 측정이 그보다 오래 걸린다)
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-10 review-and-merge 2축 리뷰 Standards 축이 제기, **실측으로 확정**. 사용자 판정으로 머지를 막지 않고 등재했다
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 review-and-merge (PR #580 Standards 축)

**원인 / 영향:** `trading-cockpit.tsx:54` 가 `useSearchParams()` 를 부르는데
`(dashboard)/trading/page.tsx` 는 `<TradingCockpit />` 하나만 렌더하고 `<Suspense>` 경계가 없다.
Next 16 은 static 세그먼트에서 이 훅을 만나면 **라우트 전체를 CSR 로 bail out** 한다.
기존 `useSearchParams` 선례 둘(`backtests/`·`strategies/`)은 서버 `auth()` 로 이미 dynamic 이라
이 문제가 없었다 — `/trading` 이 **첫 static 사례**다.

**실측** (빌드 산출물 대조 — main `d277a54a` 빌드 vs 브랜치 `e9f01576` 빌드):

| 축                              | main        | 브랜치      | 델타                     |
| ------------------------------- | ----------- | ----------- | ------------------------ |
| `.next/server/app/trading.html` | 65,097 B    | 41,439 B    | **−23,658 B**            |
| `aria-label="트레이딩 개요"`    | 1건         | **0건**     | 코크핏이 통째로 사라졌다 |
| `static/chunks` 총량            | 2,941,841 B | 2,955,844 B | +14,003 B (**+0.48%**)   |
| 청크 파일 수                    | 57          | 57          | 0                        |

★**음성 대조** — prerender 된 **16개 라우트 중 15개가 바이트 동일(+0)** 이고 `trading.html` 만
줄었다. 빌드 조건 차이가 아니라 **이 변경이 원인**이다.
★**잃은 것은 prerender HTML 뿐이고 클라이언트 JS 는 +0.48% 다.** 두 축을 섞어 말하지 마라 —
[BL-662]~[BL-665] 가 판 것은 JS 축이고 이것은 HTML 축이다.

**되찾을 수 있는 것의 크기 — fallback 수준이다.** `useSearchParams` 가 코크핏 **최상단**(`:54`)
이라 `page.tsx` 를 `<Suspense>` 로 감싸면 경계가 **페이지 전체**를 삼킨다 ⇒ prerender 되는 것은
fallback 껍데기뿐이고, **그 껍데기는 `trading/loading.tsx` 가 이미 준다.**
65kB 를 통째로 되찾으려면 URL 을 읽는 부분만 작은 자식으로 격리해야 한다 — 그건 S 가 아니다.
★`/trading` 은 `(dashboard)` **인증 라우트**라 공개 라우트보다 prerender 의 값이 낮다.

**권장 접근:** `page.tsx` 에 `<Suspense>` 한 겹. 선례는 `backtests/[id]/trades/page.tsx:32`.
그 뒤 **같은 방법으로 복원폭을 재라** — `.next/server/app/*.html` 전 라우트 크기 대조 +
`aria-label` 존재 여부. 음성 대조(다른 15개 라우트 불변)를 반드시 함께 재라.

**Risk:** 🟡 초기 페인트가 CSR 로 늦다. 기능 결함은 아니다.

---

### BL-685

**Title:** 마운트 1회 해시 재조정이 데이터 도착 뒤 성장에 밀리는지 **측정되지 않았다**
**Category:** Frontend / backtest (리포트 앵커)
**Priority:** P2
**Trigger:** [BL-397] 앵커 불만 보고 · 또는 FE e2e 를 손보는 회차
**Est:** S (픽스처 하나 + 시험 하나)
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-10 review-and-merge Spec 축이 제기. ★**「결함」이 아니라 「미측정」이다** — 제기한 리뷰어 본인이 「브라우저 scroll-anchoring 이 막을 수 있다, 측정하지 않았다」고 자인했다
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 review-and-merge (PR #580 Spec 축)

**원인 / 영향 (제기된 기전 — 미확정):** `backtest-report-shell.tsx:89-93` 의 해시 재조정은
`useEffect(…, [])` 라 마운트 1회만 돈다. 그 시점에 `:74` 의 `trades.data?.items` 는 `undefined`
이고, §02(`#benchmark` — `#trades` **위**)의 `performance-chart.tsx:88-92` 는 trades 가 있을 때만
caption + 120px pane 을 그린다 ⇒ §02 가 **스크롤이 끝난 뒤** 자라 `#trades` 를 아래로 민다.

★**현 시험이 못 잡는 이유:** `report-section-anchors.spec.ts:37` 이 쓰는
`fixtures/backtest-report.ts:82` 의 `trades` 기본값이 **`[]`** 라 `hasTrades` 가 false 다 ⇒
**성장 경로를 아예 안 탄다.** 게다가 두 단언이 한쪽 방향이다(`toBeInViewport()` 에 ratio 없음 ·
`box.y >= TOPBAR_H`) — 아래로 밀리는 드리프트는 red 를 못 만든다.

**재는 법 (다음 회차가 0에서 시작하지 않도록):**

1. `trades` 가 **있는** 픽스처를 만든다 — 현 기본값 `[]` 를 덮어야 한다.
2. `/backtests/<id>#trades` 로 진입한다.
3. §02 성장 **후** `#trades` 의 `box.y` 가 유지되는지 관측한다 — ratio 를 준
   `toBeInViewport({ ratio })` 로. 한쪽 방향 단언으로는 이 현상을 못 잡는다.
4. ★**로컬 e2e 는 [BL-668] 로 2건이 상시 red 다**(`sprint46-tier1-critical.spec.ts:69` ·
   `sprint46-tier3-nth.spec.ts:489`). **새 red 를 그 둘과 분리해서 읽어라.**
5. green 이면 원인은 브라우저 scroll-anchoring 이다 — **그 사실을 여기 적고 닫아라.**
   「측정했더니 문제가 없었다」도 산출이다.

**Risk:** 🟢 (미측정. 참으로 밝혀지면 🟡)

---

### BL-686

**Title:** `scroll-mt-[76px]` 이 `--topbar-h` 토큰을 우회하고 같은 수를 네 곳에 다시 쓴다
**Category:** Frontend / backtest (리포트 앵커) · 디자인 토큰
**Priority:** P3
**Trigger:** 탑바 높이를 바꿀 때 — 그때 네 곳이 따로 논다
**Est:** XS
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-10 review-and-merge Standards 축이 제기, 코드 대조로 확인
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 review-and-merge (PR #580 Standards 축)

**원인 / 영향:** `backtest-report-shell.tsx:56` 이 `className="section scroll-mt-[76px]"` 다.
`globals.css:170` 이 `--topbar-h: 60px` 를 선언하고 7곳 이상이 `var(--topbar-h)` 로 소비하는데,
이 60(+16 여백)은 **컴포넌트 클래스 · 그 주석 · 단위 시험의 정확-문자열 단언 · e2e `TOPBAR_H = 60`**
**네 곳**에 다시 쓰여 있다.

★**부수 — [BL-397] 이 스스로 정한 회귀 판별자를 움직였다.** 그 명세는 「**Risk:** 🟢 렌더 트리
무변경(속성 하나 추가) · 기존 `stress-test` 앵커 불변이 회귀 판별자」라고 썼는데, `:56` 의 클래스가
`id={STRESS_ANCHOR}`(`:262`) 를 포함한 **모든** 섹션에 붙어 그 앵커도 76px 이동했다.
**판별자로 쓰려면 움직였다는 사실을 알고 써야 한다.**

**권장 접근:** `scroll-mt-[calc(var(--topbar-h)+16px)]` 한 줄로 접는다.

**Risk:** 🟢

---

### BL-689

**Title:** stand-down 이 uid 형제 행마다 세션 조회를 따로 돈다 (N+1)
**Category:** Backend / trading (조건부 진입)
**Priority:** P3
**Trigger:** 같은 `exchange_uid` 행이 3개 이상으로 늘 때 — 지금은 실측 2행이라 무증상
**Est:** XS
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-10 close-ownership-axis 가 [BL-517] 을 닫으며 **의도적으로 남겼다**(스코프)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 close-ownership-axis (Standards 축 · Spec 축 **양쪽이 독립 검출**)

**원인 / 영향:** `live_signal.py` 의 `_resolve_current_position` 이 이렇게 돈다.

```python
for account_id in scope_ids:
    others.extend(await session_repo.list_active_by_account(account_id))
```

`list_active_by_account` 는 단일 id 만 받으므로 **형제 행 수만큼 쿼리가 는다.**
`apps/api/AGENTS.md` §2 의 「N+1 방지」와 결이 다르다.

★**이 회차가 안 고친 이유** — `list_active_by_account` 는 소비자가 3곳이고
([BL-517] 이 넓힌 stand-down · `tasks/trading.py:501` · `websocket/position_fanout.py:69`)
그중 stand-down 만 넓은 축이 필요하다. 시그니처를 바꾸면 나머지 둘의 의미도 함께 바뀐다.
⇒ 복수형 메서드를 **새로** 추가하는 것이 옳고, 그건 이 회차 스코프 밖이었다.

★**지금 무증상인 이유는 형제가 2행이라서다 — 가드가 아니라 데이터다.** [BL-605] 가
신규 이중 적재를 막았지만 기존 574행은 그대로 두므로, 행 수는 줄지 않는다.

**권장 접근:** `list_active_by_accounts(account_ids, *, symbol=None)` 를 리포지토리에 추가해
한 쿼리로 접는다. 판정이 `any()` 라 심볼 필터를 repo 로 내리면 조기 종료도 산다.

**Risk:** 🟢 (성능 축. 결과는 지금도 옳다)

---

### BL-690

**Title:** `soak-stack.sh` 의 「연속 창은 끊긴다」가 「벌어 둔 C2 를 잃는다」로 읽힌다
**Category:** Infra / 소크 운영 도구 (문구)
**Priority:** P3
**Trigger:** 다음에 `pin` 을 집행할 때 — 또는 사망 축 수정을 미룰지 판단할 때
**Est:** XS
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-10 soak-pin-cost-correction 이 오해를 코드로 반증하고 문서 2곳을 고쳤다. **도구 문구는 아직 그대로**다
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 close-ownership-axis (세션 프롬프트의 절대 규칙이 코드에 반증되며 발각)

**원인 / 영향:** `tools/scripts/soak-stack.sh:185` 가 `down` 을 요구하며 이렇게 말한다.

```
→ 'tools/scripts/soak-stack.sh down' 으로 내린 뒤 pin 해라 (연속 창은 끊긴다).
```

문장 자체는 참이다 — **진행 중인 창**은 거기서 끊긴다. 그런데 **「이미 벌어 둔 최장 창(C2)을
잃는다」**로 읽혔고, 그 오독이 `docs/status.md` 의 「재기동 시 … C2 는 0 부터」를 낳았으며,
거기서 다시 세션 프롬프트의 **절대 규칙**(「`pin` 금지 — C2 를 0 으로 리셋한다」)으로 승격됐다.

**무엇이 사실인가** — `soak_gate_predicate.py` 에서 `window_start = disq[-1].at`(`:614`)이라
창을 리셋하는 것은 **실격뿐**이고, `C1 = sum(merged)`(`:690`) · `C2 = max(merged)`(`:691`) 다.
게이트 자체 출력이 고정 sha **두 종류**의 귀속 창을 나란히 보여주며 합이 맞는다
(`15.3007 + 0.0133 + 26.6558 = 41.97h`). ⇒ pin 은 attribution 을 쪼갤 뿐 과거를 배제하지 않는다.

★**피해는 문구가 아니라 그것이 만든 미룸이다** — 「사망 축 수정은 C1 완주 후」라는 계획이
**검증되지 않은 전제 위에** 서 있었다. 코드 결함 7건이 실격 원장의 다수인데도 그렇다.

**권장 접근:** 두 문장으로 가른다 — ⑴ 「진행 중 창은 끊긴다(C1 은 거기까지 계상된다)」
⑵ 「이미 24h 를 넘긴 창은 C2 가 `max` 라 그대로 남는다」 ⑶ 「진짜 위험은 `down` 동안의 tick
공백이 실격을 만드는 것이다 — 그것만이 창을 리셋한다」.

**Risk:** 🟢 (문구. 단 이 문구가 만든 판단 오류는 🟡였다)

---

### BL-691

**Title:** `RestingEntryOrder` docstring 이 409 직렬화를 `str()` 이라고 말하는데 코드는 `model_dump(mode="json")` 이다
**Category:** Backend / trading (청산) · 문서(주석)
**Priority:** P3
**Trigger:** 409 경로의 필드 타입을 바꿀 때 — 또는 그 docstring 을 근거로 삼을 때
**Est:** XS
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-10 fe-close-surface 가 FE 쪽 계약을 읽다 발견. 스코프 밖이라 등재만
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 fe-close-surface (계약 조사 중 코드 대조)

**원인 / 영향:** `apps/api/src/trading/schemas.py:132-139` 의 docstring 이 「문자열이 필요한
것은 `HTTPException(detail=<raw dict>)` 로 나가는 409 경로뿐이고, **거기서만 `str()` 로
담는다**(`close_service.py`)」고 적었다. 그런데 실제 코드는
`close_service.py:143` 에서 `RestingEntryOrder.from_snapshot(order).model_dump(mode="json")`
을 쓴다. `str()` 을 직접 부르는 자리는 없다.

**재현:** `grep -n 'str(' apps/api/src/trading/services/close_service.py` → 해당 호출 0건.
`grep -n 'model_dump' 같은 파일` → `:143` 1건.

★**결과는 같지만 기술이 낡았다.** 이 문장은 2026-08-10 close-ownership-axis 가 `str()` 방식을
`model_dump(mode="json")` 로 바꾸면서 남은 잔재다(그 커밋이 「두 경로가 갈라지지 않게 하는
유일한 장치」라고 쓴 것이 바로 이 교체다). 다음 사람이 docstring 을 믿고 `str()` 을 찾으면
없는 것을 찾게 된다.

**권장 접근:** 그 문단을 `model_dump(mode="json")` 으로 고친다. 한 문장이다.
**Risk:** 🟢 (주석. 동작 무관)

---

### BL-692

**Title:** `RestingEntryOrder.from_snapshot(order: object)` 이 정적 검증을 통째로 포기한다
**Category:** Backend / trading (청산) · 타입
**Priority:** P3
**Trigger:** `ConditionalOrderSnapshot` 의 필드명을 바꿀 때
**Est:** XS
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-10 fe-close-surface 가 FE 쪽 계약을 읽다 발견. 스코프 밖이라 등재만
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 fe-close-surface (계약 조사 중 코드 대조)

**원인 / 영향:** `apps/api/src/trading/schemas.py:146-156` 의 시그니처가 `order: object` 라
다섯 필드 접근이 전부 `# type: ignore[attr-defined]` 다. `ConditionalOrderSnapshot`
(`providers.py:221-232`)에서 `trigger_price` 나 `order_link_id` 를 개명하면 **mypy 가 아무 말도
안 하고** 런타임에 `AttributeError` 로 터진다. 그 자리는 청산 경로 한복판이다.

★**409 경로는 더 나쁘다** — 거기서 터지면 「포지션 0 + 진입 잔량」이라는 이미 나쁜 상황에서
500 이 된다.

**재현:** `providers.py` 의 `ConditionalOrderSnapshot.trigger_price` 를 개명하고
`uv run mypy apps/api/src/trading/schemas.py` → 0 errors. 그 뒤 `test_close_service.py` 만 빨개진다.

**권장 접근:** `order: ConditionalOrderSnapshot` 으로 좁히고 `type: ignore` 5개를 지운다.
순환 import 가 걸리면 `TYPE_CHECKING` 블록 + 문자열 어노테이션으로 충분하다.
**Risk:** 🟢 (지금 동작은 옳다. 개명 안전망이 없을 뿐)

---

### BL-693

**Title:** `alert-rule-form` 의 수동 2단계 `code` 폴백이 `api-client` 수리로 잉여가 됐다
**Category:** Frontend / alert-rules · 정리
**Priority:** P3
**Trigger:** 그 파일을 다음에 열 때
**Est:** XS
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-10 fe-close-surface 가 만든 잉여. 남의 코드라 지우지 않고 등재만 (`CLAUDE.md` §3)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 fe-close-surface

**원인 / 영향:** `apps/web/src/features/alert-rules/components/alert-rule-form.tsx:31-44` 의
`isDuplicateActiveRule` 은 `error.code` 를 먼저 보고 실패하면 `detail.detail.code` 로 한 겹 더
판다. 그 두 번째 갈래는 `api-client.ts` 가 최상위 `code` 만 보던 시절의 우회다.

2026-08-10 fe-close-surface 가 `resolveErrorCode` 로 그 한 겹을 클라이언트에서 파도록 고쳤으므로
이제 **첫 줄에서 이미 참**이고 아래 9줄은 판정을 가르지 않는다.

★**죽은 코드가 아니다** — 여전히 옳고, 지금도 같은 답을 낸다. 그래서 이 회차가 지우지 않았다.
지울지 남길지는 그 파일을 소유한 회차가 정하는 것이 맞다.

**재현:** `alert-rule-form.tsx:34-43` 을 지우고 alert-rules 테스트를 돌린다 → 전건 통과.

**권장 접근:** 그 파일을 다음에 만질 때 `error.code === "alert_rule_already_active"` 한 줄로 접는다.
**Risk:** 🟢 (동작 무관. 읽는 비용만)

---

### BL-694

**Title:** `## Deferred` H2 표와 판정어 `DEFERRED` 가 같은 것을 두 방식으로 말한다
**Category:** Docs / 원장 정합
**Priority:** P3
**Trigger:** Deferred 표를 편집할 때 · 또는 6-8주 부활 재평가를 돌릴 때
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-10 bl-trigger-triage 가 등재만 하고 통합하지 않았다.
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 bl-trigger-triage ([ADR-028](decisions/028-backlog-deferred-verdict.md) Consequences)

**원인 / 영향:** `## Deferred — trigger 미도래 · 의도적 부활 가능` 표(BL-070~075 · BL-005 · BL-145,
8건)는 **섹션이 없어서** `bl-audit` 집계 밖이다(의도). 그런데 [ADR-028] 이 같은 의미의 판정어
`DEFERRED` 를 신설했으므로, 지금 원장은 「트리거 미도래」를 **두 방식으로** 말한다 — 섹션 있는
151건은 판정어로, 표의 8건은 표 소속으로. 읽는 사람이 어느 쪽이 전부인지 못 고른다.

**권장 접근:** 셋 중 하나. ⑴ 표의 8건에 섹션 + `⏳` 상태줄을 달아 판정어로 흡수(집계가 244→252,
DEFERRED 159) ⑵ 표를 남기되 머리글에 「이 8건은 판정어 축 밖이다」를 명시 ⑶ 표를 `_deferred`
tombstone 으로 되돌린다. **⑵ 가 가장 싸고 ⑴ 이 가장 정합적이다.**
**Risk:** 🟢 문서 전용. 단 ⑴ 은 `bl-audit` 총계를 움직이므로 같은 커밋에서 수치 인용을 함께 고쳐라.

---

### BL-696

**Title:** `apps/web/**` eslint 훅이 스테이징 파일을 안 받아 **매 커밋 전량 린트**한다
**Category:** DX / 게이트 (pre-commit)
**Priority:** P3
**Trigger:** FE 커밋 대기가 거슬릴 때 · 또는 pre-commit 설정을 다음에 손댈 때
**Est:** XS
**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-10 실측 등재. 결과는 맞고 **비용만** 틀리다.
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 precommit-scope)
**출처:** 2026-08-10 precommit-scope ([BL-687] 수리 중 인접 관측)

**원인 / 영향:** 루트 `package.json` 의
`"bash -c 'cd apps/web && pnpm exec eslint --fix --no-warn-ignored --'"` 는 lint-staged 가 뒤에
붙이는 파일 목록을 **한 번도 참조하지 않는다**(`$0`·`$@` 어느 쪽도 안 쓴다). ⇒ eslint 가 인자 없이
돌아 flat config 기본 패턴으로 **레포 전량**을 린트한다. 실측 **14.7s / 203% CPU**.

★**[BL-687] 과 같은 뿌리(`bash -c` 위치인자)지만 실패 모드가 반대다** — backend 는 **과소**(첫
하나만), frontend 는 **과대**(전량). 그래서 [BL-687] 로 묶지 않았다. **결과가 맞아서 아무도 못
알아챘다** — 전량 린트는 스테이징분을 포함하므로 검사 자체는 통과한다.

**권장 접근:** [BL-687] 과 같은 꼴로 `"$0" "$@"` 를 넘긴다. 단 eslint 는 `cd apps/web` 뒤
**상대경로**를 받으므로 `"${0#apps/web/}" "${@#apps/web/}"` 여야 한다.
★**고치면 반드시 음성 대조를 해라** — 인용을 빠뜨리면 빈 인자가 들어가 지금과 같은 전량 린트로
조용히 되돌아간다([BL-687] 수리에서 실제로 잰 축이다).
**Risk:** 🟢 훅 설정 1줄. 단 FE 커밋 경로 전체가 걸리므로 종단(`pnpm exec lint-staged`)까지 재라.

---

### BL-697

**Title:** 테스트 DSN 판정 사본이 `test_prefork_smoke_integration.py` 에 1곳 남았다
**Category:** Testing / 안전 (판정 SSOT)
**Priority:** P3
**Trigger:** prefork integration 테스트를 다음에 손댈 때 · 또는 테스트 DSN 판정 규칙을 또 바꿀 때
**Est:** XS
**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-10 [BL-451] 수리 중 인접 관측. 위험은 낮고 **일관성**만 문제다.
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 migration-guard)
**출처:** 2026-08-10 migration-guard ([BL-451] ① 수리 중 전수 grep)

**원인 / 영향:** [BL-451] 이 테스트 DSN 판정을 `tests/_db_guard.py` 한 곳으로 모으면서
`tests/test_migrations.py` · `tests/real_broker/conftest.py` · `tests/real_broker/_harness.py`
세 사본을 위임으로 바꿨다. **`tests/tasks/test_prefork_smoke_integration.py:42` 만 남았다** —
`TEST_DATABASE_URL or DATABASE_URL` 폴백과 `make_url().database` + `_test` 검사를 자기 안에 갖고 있다.

★**지금 위험하지 않은 이유 셋.** ⑴ 이 파일은 `@pytest.mark.integration` 이라 `--run-integration`
없이는 수집돼도 **skip** 된다 ⑵ 파괴적 경로가 아니다(`drop_all`·`downgrade` 를 호출하지 않는다)
⑶ 무엇보다 루트 `tests/conftest.py::pytest_configure` 가 **세션 최상단에서 먼저 판정**하므로
그 폴백이 개발 DB 를 돌려주는 상태에는 애초에 도달할 수 없다.

★**그럼에도 등재하는 이유.** 판정이 두 벌이면 한 벌만 고쳐지는 날이 온다 — 그것이 [BL-451] 의
실사고 구조 그 자체였다. 그리고 이 사본은 폴백을 **허용**하므로, 루트 가드가 미래에 약해지면
둘의 판정이 **어긋난 채로** 조용히 통과한다.

**권장 접근:** `_verify_test_db_dsn()` 을 `_db_guard.refusal_reason()` 위임으로 바꾼다. 단
이 파일의 계약은 「미명시면 **명시적 fail**」(silent skip 금지, codex G.0 P1 #2)이고 `_db_guard`
의 기본값은 `DEFAULT_TEST_DSN` 폴백이라 **의미가 다르다** — 위임 시 그 차이를 어느 쪽으로
맞출지 먼저 정해라. 그냥 갈아끼우면 codex P2 권고가 조용히 뒤집힌다.
**Risk:** 🟢 (테스트 파일 1개. 단 위 의미 차이를 안 보면 계약이 뒤집힌다)

---

### BL-699

**Title:** RHF 폼 6개에 `noValidate` 가 없다 — [BL-698] 과 같은 클래스의 **잠복** 결함
**Category:** Frontend / 폼 검증
**Priority:** P3
**Trigger:** 그 6개 폼 중 하나의 **기본값이 native 제약(step/min/max)을 어기는 순간** — 그때 제출이 조용히 죽는다
**Est:** S (1-2h · 폼당 `noValidate` 1줄 + 클릭 경로 테스트)
**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-10 backtest-submit-fix 에서 전수 스캔. **현재 활성 결함 0건.**
**트리거 판정:** 미도래 — 6개 전건의 현재 기본값이 자기 제약 격자 안에 있음을 실측 확인 (2026-08-10 backtest-submit-fix)
**출처:** 2026-08-10 backtest-submit-fix ([BL-698] 수리 중 부수 발견)

**원인 / 영향:** [BL-698] 은 「기본값이 `step` 격자를 벗어나면 브라우저가 submit 이벤트를 발화조차
하지 않는다」는 결함이었다. 그 조건의 **전건**은 `<form>` 에 `noValidate` 가 없는 것이다.
실측 — 이 레포 RHF 폼 **9개 중 `noValidate` 는 3개뿐**이다:

| `noValidate`                                     | 폼                                                                                                                                                                     |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 있음 (3, + BL-698 로 추가된 `backtest-form` = 4) | `waitlist-form-card` · `test-order-dialog` · `alert-rule-form`                                                                                                         |
| **없음 (6)**                                     | `optimizer/{genetic,grid,bayesian}-search-form` · `strategies/[id]/edit/tab-metadata` · `live-sessions/live-session-form` · `trading/register-exchange-account-dialog` |

★**지금 붉지 않다.** 6개의 native 제약을 전수 확인한 결과 전부 `step="any"` 이거나 정수 step +
정수 경계라 기본값이 격자 안이다. 즉 **잠복**이지 발현이 아니다 — 그래서 ACTIVE 가 아니라 DEFERRED
([ADR-028](decisions/028-backlog-deferred-verdict.md)).

★**위험은 「지금 틀렸다」가 아니라 「조용히 틀려진다」다.** [BL-698] 은 폼 코드를 한 줄도 안 건드린
커밋(`753f4bf6` — 기본값 상수만 좁혔다)이 만들었고, **212 커밋 동안 아무 게이트도 못 잡았다.**
같은 일이 이 6개에서 일어나면 증상은 또 「버튼을 눌러도 아무 일이 없다」이고, 로그도 에러도 없다.

**권장 접근:** 폼당 `noValidate` 1줄. 단 **넣기 전에** 그 폼의 native `min`/`max`/`required` 가
RHF rule 로 이중화돼 있는지 확인해라 — 이중화가 없으면 `noValidate` 는 검증을 **없애는** 것이 된다
([BL-698] 은 전건 이중화돼 있어 잃는 것이 0 이었다). 함께 각 폼에 **클릭 경로**(`fireEvent.submit`
아님) 테스트 1건씩.

**영향 파일:** 위 표의 6개 + 각 테스트.

**Risk:** 🟢 (선제 조치. 단 RHF 이중화 확인을 건너뛰면 검증을 지우는 변경이 된다)

---

### BL-700

**Title:** FE 헤더 주석과 `"use client"` 의 순서 관례가 두 갈래로 갈려 있다
**Category:** Frontend / 컨벤션
**Priority:** P3
**Trigger:** `apps/web/AGENTS.md` 를 손댈 회차 — 관례를 문서로 고정할 때 함께 처리한다
**Est:** XS (문서 1줄 + 필요 시 정렬)
**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-10 bl-307-header-lint 에서 발견. **둘 다 합법이고 게이트는 양쪽 다 통과한다** — 지금 고장난 것은 없다.
**트리거 판정:** 미도래 — 동승 트리거(`apps/web/AGENTS.md` 를 여는 회차). 단독 착수 시 값이 0이다 (2026-08-10 bl-307-header-lint)
**출처:** 2026-08-10 bl-307-header-lint (`/code-review` Spec 축 (b)2)

**원인 / 영향:** [BL-307] 이 헤더를 첫 3줄에 넣으면서 `"use client"` 와의 상대 순서를 정해야 했다.
실측 — 레포에 **두 관례가 이미 공존**한다:

| 관례                          | 표본                                                  |
| ----------------------------- | ----------------------------------------------------- |
| 주석 → `"use client"`         | `waitlist-filter-bar` · `waitlist-stats-strip` (다수) |
| `"use client"` → 빈 줄 → 주석 | `waitlist-admin-view` · `components/ui/*` 6건         |

[BL-307] 은 **다수 쪽(주석 먼저)**으로 통일했다. Next.js 는 지시문 앞에 주석만 있으면 합법이라
둘 다 동작하고, `header-audit` 은 3줄 창 안이기만 하면 양쪽을 통과시킨다.

**권장 접근:** `apps/web/AGENTS.md` 에 한 줄로 고정하고(권장 = 주석 먼저), 어긋난 파일은
**그 파일을 다음에 열 때** 맞춘다. 일괄 정렬은 값에 비해 diff 가 크다.

**영향 파일:** `apps/web/AGENTS.md` 1 + (동승) 해당 컴포넌트.

**Risk:** 🟢 (순수 컨벤션. 동작 영향 0)

---

### BL-725

**Title:** `exchange_exits` 중복 290행 — 같은 `exchange_uid` 에 계정 행이 둘
**Category:** Backend / trading (원장 위생)
**Priority:** P2
**Trigger:** ★**신규 적재는 2026-08-08 에 멈췄다.** 잔재 정리는 `exchange_accounts` 행 축 결정([BL-477](#bl-477)·[BL-529](#bl-529)·[BL-592](#bl-592))이 풀릴 때 동승
**Est:** S (30분 — 결정이 선행이면 삭제는 단순)
**출처:** 2026-08-14 money-path-attribution

**원인 / 영향:** 원장 **882행 = 고유 청산 592건 + 중복 290행**이다. 290건이 정확히 2행씩이고
잉여분 합계는 **−517.84 USDT** 다. 같은 Bybit uid(558689281)에 앱 계정 행이 둘(`0277c150` ·
`19a8166a`)이라 스윕이 각자 같은 창을 적재했고, UNIQUE 축이 `(exchange_account_id, row_hash)`
라 계정 행이 다르면 충돌로 안 걸린다.

★**[BL-605] 수리(`dedupe_accounts_by_exchange_uid`)는 작동 중이다.** 적재일 축 실측 —
`0277c150` 마지막 적재가 **2026-08-08**(23행)이고 08-09 부터는 `19a8166a` 단독이다.
**지금 새로 늘지 않는다.**

★**부수 효과가 하나 있다** — 중복쌍의 두 사본이 **서로 다른 라벨**을 받았다(한쪽 `ours/exact`,
다른 쪽 `unknown/none`). 계정 스코프(`list_existing_ids(account_id, …)`)가 다른 계정 행의 주문을
못 찾기 때문이다. 원장을 통계로 읽을 때 이 편향을 빼고 봐야 한다.

**권장 접근:** DB 행 삭제는 **불목표**로 잠겨 있다(`docs/status.md` ⓹). 계정 행 축 결정이 나기
전까지는 **집계 시 `DISTINCT ON (row_hash)` 로 접는 것**이 정답이고, 그 축은 이 회차가 이미 썼다.

**Risk:** 🟡 (원장을 통계로 읽는 모든 판단이 최대 1.5배 부풀어 보인다)

**상태:** ⏳ **대기 (트리거 미도래)** — 미착수. 신규 적재는 멈춤 (2026-08-14 money-path-attribution). ★**2026-08-15 재확인 — 「코드 0줄 판정 종결」 후보로 열었으나 종결할 것이 없다.** 처방은 이미 「집계 시 `DISTINCT ON (row_hash)`」로 적혀 있고, `exchange_exit_repository.py:48` 이 「여기서는 no-op 이라 넣지 않는다」까지 명시한다. 트리거도 미도래(동승)다 ⇒ **지금 상태가 정답이라 그대로 둔다** (2026-08-15 soak-survival). ★★**2026-08-15 clock-fill-sweep — 리드인을 `⬜ Open` 에서 교정했다.** 본문이 「트리거도 미도래」를 적어 놓고 리드인만 `Open` 이라 `bl-audit.sh` 가 이 항목을 **ACTIVE 로 셌다**([ADR-028] 위반). 전수 대조 결과 「트리거 판정 = 미도래」인 **185개 섹션 중 리드인이 `⬜ Open` 인 것은 이 하나뿐**이었다 — 패턴이 아니라 단발 드리프트다. 재발 방지로 `bl-audit.sh` 에 정합 축을 넣었다
**트리거 판정:** 미도래 — 동승 조건. `exchange_accounts` 행 축이 사용자 결정 대기다 (2026-08-14 money-path-attribution · 2026-08-15 재확인)

---

## ★2026-08-15 실측 — 「해석적 재계산」을 측정으로 바꿨다

### BL-732

**Title:** `gap_resync_position_mismatch` 재발 — ★**표본이 반증됐다**(로컬 사망은 맥 sleep 이 원인)
**Category:** Backend / trading (라이브 세션 생존)
**Priority:** P2 — ★**2026-08-18 P1→P2 강등** — 등재 근거였던 표본이 **반증됐다**(로컬 소크 6h33m 사망 = 맥 sleep). 증거가 없는 항목이 P1 슬롯을 차지하면 P1 표가 신호가 아니게 된다. 재발 시 승격은 트리거가 이미 적고 있다
**Trigger:** ★**인프라가 깨끗한 창**(서버 · `EXCLUSIVE=YES` · beat tick 정상)에서 같은 사인이 다시 나면
**Est:** M (3-4h — 그때는 표본이 코드 축을 가리킨다)
**출처:** 2026-08-14 money-path-close 등재 → **2026-08-15 soak-survival 이 표본을 반증하고 재기술**

**★★2026-08-15 재기술 — 등재 당시의 표본은 코드 축 판별에 쓸 수 없다.**

`e9c504f1`(로컬 맥, 6h33m)의 사망은 **맥이 잠든 것**이 원인이다. `pmset -g log` 와 컨테이너
로그가 초 단위로 겹친다 — 09:11:59 Clamshell Sleep ↔ `last_evaluated_bar_time=09:11:00` ·
09:28:18 Wake ↔ 09:28:46 `gap_resync_deferred #1` · 09:49:09 Sleep ↔ beat 마지막 tick 09:48:43.
**beat 가 09:38~12:26 에 168회 중 15회만 tick 을 보냈고 그 15회가 DarkWake 횟수와 같다.**
DarkWake 직후엔 `socket.gaierror: Name or service not known` 이 따라붙는다. 별건으로 06:04:11
**Redis AOF 가 디스크 풀로 쓰기 실패**해 celery 가 `Unrecoverable error` 로 죽었다(→ [BL-736]).

⇒ `gap_resync_position_mismatch` 는 **인프라가 만든 2h48m 공백의 하류 증상**이다. 이 표본으로
H1/H2/H3 를 가르면 「맥이 잠든 창을 로직이 어떻게 다뤘나」를 재게 된다. **정상 운영에서는 그런
크기의 공백이 생기지 않으므로 트리거를 「깨끗한 창에서의 재발」로 옮긴다.**

★**C1 을 실제로 끊은 사건은 이것이 아니다** — 서버 세션 `de3db35a` 의 `position_divergence`
이고, 그 뿌리는 **하네스 배타성**([BL-734](#bl-734))으로 **확정·수리됐다.**

★아래는 등재 당시 기록이다(축 자체는 재발 시 여전히 유효한 출발점이다):

**원인 / 영향(등재 시점):** 로컬 맥 소크 세션 `e9c504f1`(pin `4b11da26`, 05:53:52Z 기동)이
**6h33m 만에** `gap_resync_position_mismatch` 로 자동 사망했다. 워커 로그 실측:

```
live_signal_gap_ledger_seed session=e9c504f1 symbol=BTC/USDT
  outcome=already_open  ledger_net=0.06000000  carried_position=0
```

★**[BL-622](#bl-622) 가 같은 `reason` 을 2026-08-07 에 `✅ Resolved` 로 닫았고, 이 pin(08-14)에는
그 수리가 들어 있다.** ⇒ **수리 후 재발**이다. BL-622 의 진단(H3 관측 지연 — 거래소 체결과 원장
기록 사이 872초)이 이 사건을 설명하는지는 **아직 확인되지 않았다.**

★★**초판 리드는 반증됐다 (2026-08-14 codex 적대 리뷰).** 등재 시 「`ledger_net = 0.06` 이
반전 수량(2×0.03)과 같으니 seed 가 반전을 **절대 수량**으로 접는 것 아닌가」라고 적었다.
**코드가 그것을 부정한다** — 이 값의 생산자는 `_ledger_gap_seed`(`tasks/live_signal.py:399`)이고
`:434` 가 `net += quantity if fill.side == OrderSide.buy else -quantity` 로 **부호 있는 합산**을
한다(로그 배선 = `:3707` 의 `ledger_net: str(ledger_seed.net)`). 내가 지목했던
`ledger_position.py:derive_open_position` 은 **이 로그의 생산자가 아니다.**

★**대신 같은 함수의 독스트링이 진짜 한계를 이미 적어 두고 있다**(`:406-411`):

> 창 안 체결이 **전부 같은 side** 이고 **reduce-only 가 하나도 없다** … ★근거 — 공백 중
> "열고 (부분)닫은" 창을 엔진 상태로 되돌리려면 **공백 이전 포지션**을 알아야 하는데
> 이 창에는 그 정보가 없다.

★★**2차 적대 리뷰가 여기서 한 겹 더 벗겼다 — `ledger_net` 은 사망 판정 입력이 아니다.**
실제 판정은 `live_signal.py:3716` 의
`_positions_are_aligned(exchange_positions, carried_position)` 이고, 어긋나면
`_block_on_gap_mismatch` 로 간다. 즉 대조되는 두 값은 **거래소 포지션**과 **엔진 이월
포지션**이지 `ledger_net` 이 아니다. 로그의 `ledger_net=0.06` 은 **진단 텔레메트리**다.
(부수 확정: `_ledger_gap_seed` 가 `net` **과 `legs` 를 둘 다** 만든다(`:434-459`) —
`derive_open_position` 은 별도 shadow telemetry 전용이다.)

⇒ **「창 축이다」도 아직 단정할 수 없다.** 공백 이전 포지션을 실제로 대조하기 전에는 가설이다.
남은 축은 셋 — ⑴ 시간축([BL-622] 재발) ⑵ 창 축([BL-547] 계열) ⑶ `carried_position` 산출
자체(`_carried_position_size` + `_closed_seed_position`, `:3682-3692`).

**권장 접근:** ★**먼저 판정해라 — BL-622 재발인가 별건인가.** 살아 있는 가설 둘:
⑴ **시간축**(BL-622 H3 재발) = 거래소 체결과 원장 기록의 관측 지연으로 유예 창이 모자랐다 —
판별 = 사망 직전 체결의 거래소 시각 vs `orders.filled_at` 격차를 재라.
⑵ **창 축**([BL-547] 계열) = gap 창이 공백 이전 포지션을 모른 채 legs 를 채택했다 —
판별 = 그 창에 들어간 체결 목록(`ledger_seed.order_ids`)과 공백 **이전** 포지션을 나란히 재라.
⑶ **`carried_position` 산출 축** = 엔진 이월값 자체가 틀렸다 —
판별 = `_carried_position_size`/`_closed_seed_position` 이 그 시점에 낸 값 vs 거래소 실제 포지션.
★**수량축 가설은 죽었다. 되살리지 마라** — 위 코드 인용이 그것을 닫는다.
★**`ledger_net` 을 판정 입력으로 취급하지 마라** — 로그일 뿐이다.
★**재기동 전에 거래소 포지션을 확인해라** — 마지막 체결이 `buy 0.06` 이고 세션이 그 뒤 죽었다.
고아 포지션 위에 새 세션을 얹으면 [BL-024] 회차가 밟은 함정을 반복한다.

**Risk:** 🟡 (표본이 인프라 사고로 밝혀져 낮췄다. 소크 생존 자체의 병목은 [BL-734] 로 이관됐다)

**상태:** ⏳ **대기 (트리거 미도래)** — 등재 표본이 맥 sleep 으로 설명돼 코드 축 판별에 못 쓴다. 서버·배타성 확보 창에서 같은 사인이 재발하면 그때 착수한다 (2026-08-15 soak-survival)
**트리거 판정:** ~~도래~~ → **미도래** (2026-08-15) — 종전 근거였던 실격 원장 17행은 `cause_class: operational`(맥 sleep)로 정정됐다. 코드 축을 가리키는 표본이 아직 없다

---

### BL-738

**Title:** 계정 배타성 가드의 한계 3종 — resting 없는 남의 포지션 · probe/청산 경쟁 · Repository 밖 DB 접근
**Category:** Backend / trading (테스트 인프라 · 계정 배타성)
**Priority:** P2
**Trigger:** ★[BL-734] 가드가 **실제로 한 번 열린 것이 관측되면** 즉시 / 또는 거래소 계정 분리를 착수할 때
**Est:** M (2-3h — ⑴⑵ 는 설계 결정이 선행)
**출처:** 2026-08-15 soak-survival ([BL-734] 수리에 대한 codex 적대 리뷰 P1·P2)

**원인 / 영향:** [BL-734] 가 넣은 가드는 **resting 조건부 주문의 소유권**만 본다. 그것이
2026-08-14 사고를 막는 것은 맞지만(그때 서버는 조건부를 걸어 둔 채 돌고 있었다), 계약을
「빈 목록 = 계정 배타적」으로 읽으면 틀린다. codex 가 짚은 세 구멍:

- **⑴ resting 없는 남의 포지션** — 다른 호스트가 **시장가로 진입**했거나 조건부가 **이미
  체결**됐으면 resting 이 0 이다. 가드는 통과하고 `close_position` 은 여전히 그 포지션을 닫는다.
  ★현재 코드는 이 한계를 주석으로 고지하고 있다(`_harness.py` 2.5단계) — **숨기지 않았을 뿐
  해결한 것은 아니다.**
- **⑵ probe ↔ 청산 경쟁** — 판정과 실제 청산 사이에 교차 호스트 락이 없다. probe 직후 남이
  진입하면 그대로 닫는다. **예외에는 fail-closed 지만 경쟁에는 아니다.**
- **⑶ Repository 밖 DB 접근** — `scan_resting_conditionals` 가 `session.execute(text("SELECT id
FROM trading.orders"))` 로 원장을 직접 읽는다. `apps/api/AGENTS.md` §3 위반이다. 종전
  `_cmd_status` 인라인에서 옮겨온 **기존 부채**지만, 공유 API 가 되면서 표면이 넓어졌다.

**권장 접근:** ⑴⑵ 를 코드로 막으려면 결국 **거래소 계정을 분리**하는 것이 정답이다(소크 전용
Bybit demo 서브계정). 그 전까지의 차선은 **진입 전 baseline** — `register()` 시점에 계정이
`QUIET` 임을 확인해 두고, 청산 시점 포지션이 그 baseline + 우리 체결로 설명되지 않으면 거부.
★단 그것도 ⑵ 를 완전히는 못 막는다. **막을 수 없는 잔여를 문서에 남기는 편이 거짓 안전망보다 낫다.**
⑶ 은 `OrderRepository` 에 id 집합 조회를 하나 추가하면 끝난다 — ⑴⑵ 와 독립이라 먼저 해도 된다.

**Risk:** 🟡 (가드가 이미 주 경로를 막는다. 이것은 **가드의 계약을 정확히 하는** 축이다)

**상태:** ⏳ **대기 (트리거 미도래)** — 한계는 코드 주석과 이 항목에 고지됐다. 가드가 실제로 열린 관측이 나오거나 계정 분리를 착수할 때 연다 (2026-08-15 soak-survival)
**트리거 판정:** 미도래 — 가드가 열린 관측이 아직 없고, 계정 분리도 착수 전이다 (2026-08-15 soak-survival)

---

### BL-740

**Title:** Cost-Assumption 9-cell 이 전부 `sharpe=0` 인데 `is_degenerate=False` 다
**Category:** Backend / stress_test (지표 계산)
**Priority:** P3
**Trigger:** Sharpe 를 **판단 입력으로 쓰기 전에** / 또는 다른 grid sweep 에서 같은 값이 보이면
**Est:** S (1h — 계산 경로 추적)
**출처:** 2026-08-15 soak-survival ([BL-729] 판독 중 부수 관측)

**원인 / 영향:** `run_cost_assumption_sensitivity` 를 `a22faccb`(1029 trades)로 9-cell 돌렸더니
**모든 cell 의 `sharpe` 가 `0`** 이었다. `GridSweepMetricsCell.is_degenerate` 는
「`num_trades=0` 또는 NaN sharpe」일 때 참인데 **`False`** 다 — 즉 계산이 정상 종료하고
0 을 냈다는 뜻이다. 같은 실행에서 `total_return`·`max_drawdown` 은 cell 마다 정상적으로 갈렸다
(−7.74% ~ −22.59% / −4.53% ~ −16.69%).

★[BL-729] 의 결론에는 **영향이 없다** — 그 판정은 총수익·MDD 로 했고 Sharpe 를 안 썼다.
그래서 이번 회차에서 파지 않았다. 다만 **화면은 이 값을 보여준다**.

★두 갈래 중 어느 쪽인지가 먼저다: ⑴ 계산이 실제로 0 을 내는 것(수익률 표준편차 산출 경로) 인지
⑵ `metrics_cell` 매핑에서 필드가 안 실리는 것인지. 후자면 `is_degenerate` 도 못 잡는 것이
당연하고, 그렇다면 **NaN 만 보는 degenerate 판정 자체가 좁다**.

**Risk:** 🟢 (표시 축. 지금 무엇을 깨지는 않지만 **0 은 「나쁜 Sharpe」로 읽힌다** — 부재와 구별 불가)

**상태:** ⏳ **대기 (트리거 미도래)** — 관측만 확보됐다. Sharpe 를 판단 입력으로 쓰는 회차가 오거나 다른 grid sweep 에서 같은 값이 보이면 연다 (2026-08-15 soak-survival)
**트리거 판정:** 미도래 — Sharpe 를 판단에 쓰는 회차가 아직 없다 (2026-08-15 soak-survival)

---

### BL-742

**Title:** 반전·순포지션 가정 **163곳 / 12파일** 전수 감사 ([ADR-032] §대가)
**Category:** Backend / trading · strategy (반전 의미론)
**Priority:** P2
**Trigger:** 반전이 원인으로 지목되는 사건이 **한 번 더** 나면 즉시 / 또는 헤지 모드를 재검토할 때
**Est:** M (2-3h — 모집단이 이미 세어져 있다)
**출처:** 2026-08-15 soak-survival (A3 로 계획됐다가 사용자 결정으로 이월)

**원인 / 영향:** [ADR-032] §대가가 모집단을 이미 실측해 뒀다 — **반전·순포지션 가정이 163곳 /
12파일**에 박혀 있고 그중 4개가 `strategy/pine_v2/` 다(`event_loop.py` · `strategy_state.py` ·
`stdlib.py` · `alert_hook.py`). 반전에는 `reduce_only` 를 걸 수 없으므로(one-way 유지 결정)
그 가정 하나가 틀리면 머니-패스가 조용히 어긋난다.

★**긴급도가 낮아졌다** — 2026-08-15 A1 이 「반전 의미론은 소크 사망의 원인이 **아니다**」를
보였다. 서버 세션을 죽인 것은 계정 배타성 위반이었고([BL-734]), 로컬은 맥 sleep 이었다
([BL-735]). 이 감사는 **예방**이지 진행 중인 사고의 수리가 아니다.

**권장 접근:** 「반전 체결이 오면 이 코드가 틀리는가」 **하나의 질문**으로 훑는다.

| 위치      | 무엇을 가정하나               | 반전이 오면        | 판정                         |
| --------- | ----------------------------- | ------------------ | ---------------------------- |
| (파일:줄) | (예: 체결 수량 = 포지션 증분) | 틀린다 / 안 틀린다 | 수리 필요 / 무해 / 이미 처리 |

★**「무해」에도 근거를 적어라** — 「반전이 그 경로에 도달하지 않는다」면 **왜** 도달하지 않는지.
★이미 아는 것부터 표에 넣고 시작해라: 백필 축(#631 종결) · `_net_position_size`(2026-08-15 에
옳다고 확인) · `_ledger_gap_seed` · `derive_open_position` · 체결 직후 refresh([BL-733] 종결) ·
seed watermark([BL-547]).
★pine_v2 4파일은 **Pine 도메인 모델 자체가 순포지션**이라([ADR-032] §대가) 「틀린다」가 아니라
**「거래소와 의미가 다르다」**쪽일 가능성이 높다 — 그 구분을 표에 명시해라.

★★**소크 창을 고려해라** — 이 감사가 `apps/api/src` 수리로 이어지면 **재-pin 이 필요하고 C2 가
리셋**된다. 감사(읽기)와 수리(쓰기)를 나눠서, 수리는 C1 창을 채운 뒤나 다음 재-pin 창에 묶어라.

**Risk:** 🟡 (예방 축. 지금 알려진 사고는 다른 원인으로 닫혔다)

**상태:** ⏳ **대기 (트리거 미도래)** — 모집단은 [ADR-032] 에 있고 착수 준비는 끝났다. 반전이 다시 지목되거나 헤지 재검토 시 연다 (2026-08-15 soak-survival)
**트리거 판정:** 미도래 — A1 이 반전을 사망 원인에서 배제했고 헤지 재검토 계획도 없다 (2026-08-15 soak-survival)

---

### BL-745

**Title:** 텔레그램 봇 토큰이 `curl` 의 **argv** 에 실린다 — 같은 사용자의 다른 프로세스가 읽을 수 있다
**Category:** 보안 / 소크 감시
**Priority:** P3
**Trigger:** 소크 서버에 다른 사용자·서비스가 들어올 때 / 토큰 회전 절차를 세울 때
**Est:** XS (30분)
**출처:** 2026-08-15 soak-watch-restore (codex 적대 리뷰 P2 — 등급만 조정해 이월)

**원인 / 영향:** 텔레그램 API 는 토큰을 **URL 경로**에 둔다(`/bot<TOKEN>/sendMessage`). 그래서
`curl … "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage"` 는 실행되는 동안
토큰을 argv 에 노출하고, 같은 UID 의 다른 프로세스가 `ps` 나 `/proc/<pid>/cmdline` 으로 읽을 수 있다.

★**이 회차가 만든 결함이 아니다** — `soak-watch.sh:128` 의 기존 `_notify` 가 **처음부터 같은 형태**다.
2026-08-15 에 추가한 `OnFailure` 알람 유닛이 그 패턴을 따랐을 뿐이라, 알람만 고치면 두 경로가
서로 다른 모양이 되어 오히려 읽기 어려워진다. **두 곳을 함께** 바꿔야 하는 항목이다.

★현재 위험도가 낮은 이유: 서버는 1인 사용자이고 두 경로 다 `--silent`(+ 알람은 `--show-error`
제거)라 **로그·stderr 로는 새지 않는다**. 파일 영속도 없다(유닛엔 변수 참조만 들어간다).

**권장 접근:** `curl --config -` 로 URL 을 **stdin** 에서 받는다(argv 미노출). 두 호출부를 같은
헬퍼로 모으면 형태가 하나로 유지된다. ★단 알람 유닛은 **스크립트 파일에 의존하지 않는다**는
설계가 [BL-737] 의 핵심이므로, 헬퍼로 모으더라도 알람 쪽은 인라인을 유지해야 한다.

**Risk:** 🟢 (단일 사용자 서버에서는 실현 경로가 사실상 없다. 다중 사용자·CI 로 넓히면 오른다)

**상태:** ⏳ **대기 (트리거 미도래)** — 위험 실현 조건(다중 사용자)이 아직 없다 (2026-08-15 soak-watch-restore)
**트리거 판정:** 미도래 — 서버는 1인 사용자이고 로그 유출 경로는 이미 닫혀 있다 (2026-08-15 soak-watch-restore)

---

### BL-751

**Title:** 실격 귀속 원장에 **호스트 축이 없다** — 게이트가 남의 호스트 사건을 「원장이 낡았다」로 오보한다
**Category:** Ops / soak
**Priority:** P3
**Trigger:** 원장 호스트 대조가 필요해질 때 — 소크를 두 호스트에서 동시에 굴리거나, `stale_ledger_rows` 가 2건 이상으로 늘 때
**Est:** S (스키마에 `host` 1필드 + 소급 기재 + 매칭 조건)
**출처:** 2026-08-15 ledger-thaw (판독 preflight 에서 발견)

**원인 / 영향:** `soak_gate_predicate.py:attribute_disqualifications` 는 원장 행을 `(at, kind)` 로
매칭하고 **남은 행을 `stale_ledger_rows`** 로 낸다. 그런데 원장
(`docs/reference/operations/soak-disqualifications.jsonl`)은 **서버 소크와 로컬 맥 소크의 사건을
함께** 담고, 판독은 **한 호스트의 DB** 만 본다. ⇒ 다른 호스트 행은 구조적으로 매칭될 수 없고
매 판독마다 남는다.

★실측 — 2026-08-15 서버 판독이 찍던 1건은 `2026-08-14T12:26:37 auto_death`(세션 `e9c504f1`)이고,
그 행의 evidence 자신이 「**로컬 맥 소크**(pin 4b11da26, 05:53:52Z 기동 → 6h33m 생존)」라고 적고
있다. 서버 DB 에 있을 수 없는 세션이다. 원장은 낡지 않았다 — **여기서 볼 수 없을 뿐**이다.

★이 오보는 조용히 해롭다: 매 판독이 「원장이 낡았다」고 말하면 다음 사람이 그 줄을 넘기게 되고,
**진짜 stale 이 생겼을 때도 넘긴다**(늑대 소년). 2026-08-13 tick_stall 행의 evidence 가 이미 같은
혼란을 기록해 뒀다 — 「맥 게이트 판독으로는 이 행 반영을 검증할 수 없다」.

**권장 접근:** ⑴ 원장 행에 `host`(`server` | `local-mac`) 필드를 넣는다 — 기존 17행은 evidence
본문에서 판정 가능하다 ⑵ 게이트는 **자기 호스트 행만** 매칭 대상으로 삼고, 다른 호스트 행은 셈에서
제외한다 ⑶ `host` 미기재 행은 「알 수 없음」으로 두고 지금 문구(양자택일)를 유지한다.

**Risk:** 🟢 (보고 전용 축 — C1~C5 판정에 참여하지 않는다)

**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-15 ledger-thaw 에서 **문구만** 정정했다(「원장이 낡았다」 단정 → 「다른 호스트이거나 원장이 낡은 것이다」). 스키마 축은 미착수
**트리거 판정:** 미도래 — 지금 `stale_ledger_rows` 는 1건이고 그 정체가 문서로 확정돼 있다. 호스트가 늘거나 건수가 늘 때 열어라 (2026-08-15 ledger-thaw)

---

### BL-752

**Title:** 소크 술어의 **귀속 구간 경계 3종** — 실격과 같은 시각에 열린 창이 계상될 수 있다
**Category:** Ops / soak 판정 술어
**Priority:** P2
**Trigger:** ★실격 시각과 `up` 시각이 **같은 구간**이 관측될 때 · 또는 C1 이 운영 이력으로 설명되지 않게 오를 때 · 또는 `--since` 회고 판독을 자격 판정에 쓰려 할 때
**Est:** S (경계 3곳 + 각각 테스트)
**출처:** 2026-08-15 ledger-thaw (codex 적대 리뷰 P1·P2·P2)

**원인 / 영향:** 셋 다 **이번 회차가 만든 것이 아니라** 자격 판정을 붙이면서 드러난 기존 경계다.

⑴ **P1 — `soak_gate_predicate.py:667` `countable = [a for a in attribution if a.start >= window_start]`.**
`window_start` 는 마지막 실격 시각이다. `>=` 라서 **실격과 정확히 같은 시각에 열린 귀속 구간이 포함**된다.
codex 재현: `up@T0` 과 같은 시각의 phantom 실격 뒤 `up@24h·48h·72h` 를 주면 첫 창까지 세어 **C1=3 · PASS**
가 난다. 주석이 적은 계약(「실격 **이후에 열린** 구간만」)과 코드가 한 글자 어긋난다.
★단 `>` 로 바꾸면 **실격과 같은 시각의 정상 재기동**이 배제된다 — 어느 쪽이 옳은지는 실측 표본이 없다.

⑵ **P2 — `:655` `open_window = attribution[-1] if attribution and attribution[-1].end == now`.**
`down` 으로 닫힌 구간도 `end == now` 인 순간(판독이 `down` 과 같은 시각)에는 **열린 창으로 읽힌다.**
그때 자격 블록은 「지금 누르면 N시간을 잃는다」를 찍지만 이미 닫혔으므로 잃을 것이 없다(보수적 오답).

⑶ **P2 — `--since` 회고 실행.** 창을 강제하면 열린 구간이 `countable` 에서 빠져 `open=True` 인데
`longest_hours=0 · qualified=False` 가 된다. 자격 판정은 **「지금」의 질문**이라 회고 실행에서는 의미가
없다 — 그 사실을 출력이 말하지 않는다.

**권장 접근:** ⑴ 은 실측 표본이 생길 때 결정한다(같은 시각 실격+up 이 실제로 나오는가). ⑵ 는
`attribution_intervals()` 가 열린 구간을 **명시 표시**하도록 바꾸면 `end == now` 추론이 사라진다.
⑶ 은 `--since` 실행에서 자격 블록을 **찍지 않는** 것이 정직하다.

**Risk:** 🟡 (⑴ 은 판정을 위조할 수 있다 — 단 재현 조건이 마이크로초 일치라 실측된 적 없다)

**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-15 ledger-thaw 에서 등재만 했다. 셋 다 재현 조건이 좁고, 고치는 방향(⑴ `>` 로 좁힘)이 **정상 재기동을 배제할 수 있어** 실측 표본 없이 결정하면 안 된다
**트리거 판정:** 미도래 — 실격 시각과 `up` 시각이 같은 구간은 전 이력 15건에서 관측된 적이 없다(실측 2026-08-15). 관측되거나 C1 이 설명 없이 오르면 그때가 도래다 (2026-08-15 ledger-thaw)

---

### BL-753

**Title:** 배포 호스트에 `APP_ENV` 가 없어 **placeholder 시크릿 fail-fast 가 꺼져 있다** — 코드 수리로 닫히지 않는 마지막 게이트
**Category:** Security / 배포 설정
**Priority:** P2
**Trigger:** ★**사용자 결정 대기** — `PROMETHEUS_BEARER_TOKEN` 을 배포 호스트에 넣을지 정해질 때. 또는 공개 전환([BL-071]) 착수 시 자동 도래
**Est:** XS (env 2줄 + read-back) — 단 선행 결정이 있다
**출처:** 2026-08-15 surface-truth S1

**원인 / 영향:** 배포 호스트(`~/quantbridge/apps/api/.env.local`, 서버 실측 2026-08-15)에
**`APP_ENV` 줄이 없다**. `Settings._enforce_production_safety` 는 `app_env != production` 이면
**조기 반환**하므로 그 호스트는 production validator 보호를 하나도 받지 않는다.

★**게이트 4개 중 3개는 이 회차에 코드로 닫았다** — `_hide_docs`·HSTS 술어를
`is_production or not debug` 로 넓혔고(그 호스트는 `DEBUG=false` 다), traceback 축은
**애초에 발화한 적이 없다**(`DEBUG=false` 실측 — 착수 시 `[확인 필요]`였던 것이 반증됐다).
**남은 하나가 placeholder 시크릿 fail-fast** 이고 그것만은 `app_env == production` 게이트다.

★**그런데 `APP_ENV=production` 전환은 공짜가 아니다.** 그 validator 는
`PROMETHEUS_BEARER_TOKEN` 을 **의무**로 만들고(`config.py:409-416`), ~~서버 `.env.local` 의
`CLERK_SECRET_KEY`/`WAITLIST_TOKEN_SECRET`/`PROMETHEUS_BEARER_TOKEN` 3종 중 **하나가 비어
있다**(실측 — 값을 읽지 않고 개수만 셌다)~~. 지금 켜면 API 가 **부팅을 거부**한다.
2026-08-07 회차가 같은 함정을 밟았다 — 「`APP_ENV=production` 이 게이트를 죽인다」.

★★**2026-08-16 실측 정정 — 위 「하나가 비어 있다」는 종류부터 틀렸다.**
서버 `.env.local` 에 **빈 값은 0건**이다. 실제 상태는 이렇다:

| 변수                        | 서버 실측                                                         |
| --------------------------- | ----------------------------------------------------------------- |
| `SECRET_KEY`                | len=36 ✓                                                          |
| `CLERK_SECRET_KEY`          | len=50 ✓                                                          |
| `PROMETHEUS_BEARER_TOKEN`   | len=64 ✓ (이미 있다 — 「넣을지 정해질 때」라는 Trigger 도 낡았다) |
| **`WAITLIST_TOKEN_SECRET`** | ★**줄 자체가 없다 (ABSENT)**                                      |

기본값이 `SecretStr("")`(`core/config.py:324`)라 `config.py:405` 가 raise 한다 ⇒
**부팅 거부라는 결론은 옳고, 원인은 「빈 값」이 아니라 「부재」다.** 채워야 할 것은
`WAITLIST_TOKEN_SECRET` 하나로 특정됐다.

★★★**그리고 이 항목은 보안 목적으로는 더 이상 필요하지 않다 (2026-08-16).**
`main.py:308` `_hide_docs = settings.is_production or not settings.debug` · `:345`
`enable_hsts = 같은 술어` 이고 서버는 `DEBUG=false` 다. 2026-08-16 에 #641 을 배포하고
API 를 재기동하자 **`/docs`·`/openapi.json`·`/redoc` 이 전부 404** 가 됐다 —
`APP_ENV` 는 여전히 없는 채로다. `#641` 이후 `is_production` 이 추가로 사는 곳은
`main.py:249` 의 **deprecation 경고 로그 1줄**과 `/health` 의 `env` 라벨뿐이다.
⇒ 남는 값은 「placeholder 시크릿 fail-fast」와 **「선언된 환경이 실제와 일치한다」** 뿐이고,
그 대가가 부팅 거부 리스크다. **2026-08-16 사용자 결정 = 보류.**

★**유닛 파일에 구워진 반대 근거는 낡았다.** 배포 호스트
`~/.config/systemd/user/quantbridge-api.service` 주석이 「production 으로 올리면
게이트의 무인증 스크레이프가 401 이 되어 C5⑷ 가 영구 false」라 적었는데,
[BL-620] 이후 게이트의 **기본 취득 경로는 HTTP 가 아니라 `apps/api/.metrics` 디렉터리
직독**이고(`soak-gate.sh:49,61`) 서버에 `QB_METRICS_URL` 은 **미설정**이다 ⇒
그 경로는 인증을 타지 않는다. 2026-08-07 의 교훈은 **여전히 참이되 그 메커니즘은 아니다.**

**권장 접근:** ⑴ `WAITLIST_TOKEN_SECRET` 을 생성해 넣는다(`openssl rand -hex 32`)
⑵ `APP_ENV=production` 추가 ⑶ 재기동 후 `/health` 가 `{"env":"production"}` 을 내는지
**read-back** ⑷ 소크 게이트 판독 1회로 C5⑷ 가 살아 있는지 확인.
★⑷ 를 빼면 2026-08-07 사고가 그대로 재현된다.

**Risk:** 🔴 (잘못 켜면 배포 API 가 부팅 거부 — 롤백은 env 1줄 삭제 + 재기동)

★**갱신 이력** — 종전 상태줄은 「코드 축은 2026-08-15 에 닫혔다(게이트 4 중 3)」였고,
종전 트리거 판정은 「사용자 결정(시크릿 채우기 + 전환 승인) 대기」였다. 둘 다 아래로 대체됐다.
★★**그 두 줄에 `~~취소선~~` 을 쓰지 마라** — `bl-audit.sh:174` 가 `~~` 를 담은 `**상태:**` 줄을
**통째로 건너뛰고**, 근거가 사라진 섹션은 `:107` 에서 **ACTIVE 로 떨어진다**(2026-08-16 실측:
이 항목이 DEFERRED → ACTIVE 로 조용히 뒤집혔다). 레포의 `~~옛 문장~~ → 새 사실` 관용구는
**상태줄·트리거줄에서만 예외**다 — 정정은 본문에 적고 그 두 줄은 새 문장으로 갈아끼워라.

★★**2026-08-17 [ADR-034] 로 이 항목의 셈이 바뀌었다.** ⑴ `CLERK_SECRET_KEY` 축은 **사라졌다**
(백엔드에 인증 시크릿이 0개다). ⑵ 대신 validator 에 **URL 3종 localhost 잔존 검사**가 붙어서
`APP_ENV=production` 이 새로 사는 값이 생겼다 — 종전에는 「placeholder fail-fast 하나뿐」이라
켤 이유가 약했는데, 이제 `FRONTEND_URL`/`WAITLIST_INVITE_BASE_URL`/`BETTER_AUTH_URL` 이
기본값으로 남은 채 뜨는 것을 막는다. ⑶ 그리고 **`WAITLIST_TOKEN_SECRET` 부재는 [BL-072] 를
여는 순간 보안 결함이 된다** — 비면 `waitlist/dependencies.py:29` 가 레포에 공개된 상수를
HMAC 키로 주입해 초대 토큰이 위조 가능해진다. 즉 「보류」는 Beta 공개 전까지만 유효하다.

**상태:** ⏳ **대기 (트리거 미도래 → 2026-08-16 도래)** — 2026-08-16 에 코드 축 3개가 배포로 발효했다(`/docs` 404 실측). 2026-08-17 에 validator 가 URL 3종 검사를 얻었다. ★**2026-08-16 beta-cutover 에서 [BL-072] 가 열렸다** — 초대 페이지가 실재하므로 「보류」의 유효기간이 끝났다(비면 `waitlist/dependencies.py:29` 가 레포에 공개된 상수로 초대 토큰을 서명한다). 서버 주입은 사용자 승인으로 진행 중
**트리거 판정:** 미도래 — 사용자가 「이번 창에서 보류」로 결정했다. 다음 도래 = 공개 전환([BL-071]) 착수 시 (2026-08-17 auth-selfhost 재확인)

---

### BL-755

**Title:** 잔고 조회가 실패하면 kill-switch 자본 기준이 **10,000 USDT 로 고정 fallback** 된다 — 소액 계정의 차단기가 안 터진다
**Category:** Trading / kill switch
**Priority:** P2
**Trigger:** ★거래소 잔고 조회 실패가 관측될 때(`balance_provider_failed` 로그) · 또는 실계좌 자본이 10,000 USDT 와 크게 다른 상태로 라이브를 돌릴 때
**Est:** S (fallback 정책 결정 + 가드 + 회귀)
**출처:** 2026-08-15 surface-truth 아키텍처 감사 §C-4

**원인 / 영향:** `CumulativeLossEvaluator` 는 `fetch_balance_usdt` 예외를 **삼키고 로그만 남긴
뒤**(`kill_switch.py:145-153`) `config` 기본값 `kill_switch_capital_base_usd = 10000` 으로
계산을 계속한다. 실자본이 200 USDT 인 사람의 **-10% 손실(20 USDT)** 은 10,000 기준으로
**0.2%** 가 되어 문턱(10%)에 한참 못 미친다 ⇒ **차단기가 안 터진다.**

★fail-open 인데 **로그 말고는 아무 신호가 없다**. 감사 §8 이 「fail-open 위생이 좋다 —
로그/메트릭 없이 삼키는 것은 2건뿐」이라 셌는데 이것이 그중 하나의 이웃이다.

★부수 축: `kill_switch_capital_base_usd` 에 `gt=0` 제약이 없다. 0 을 넣으면
`abs(total_pnl) / capital` 이 `DivisionByZero` 로 터진다.

**권장 접근:** ⑴ fallback 을 **정책으로 정한다** — 「모르면 보수적으로 막는다」(gated=True)와
「마지막으로 성공한 잔고를 쓴다」 중 선택. 지금의 「고정 상수로 계산을 계속한다」는 셋 중 가장
나쁘다 ⑵ 그 분기에 metric/alert 을 붙인다 — 조용한 fail-open 은 관측 불가다
⑶ `kill_switch_capital_base_usd` 에 `gt=0`.

**Risk:** 🟡 (⑴ 을 「막는다」로 정하면 잔고 API 흔들림이 정상 거래를 멈춘다 — 표본이 필요하다)

**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-15 감사에서 코드 대조로 확인(`kill_switch.py:143-157` · `config.py:162-169`). 미착수
**트리거 판정:** 미도래 — 소크 계정 자본이 문턱 계산에서 유의미하게 어긋난 적이 아직 없다. `balance_provider_failed` 가 관측되면 그때가 도래다 (2026-08-15 surface-truth)

---

### BL-756

**Title:** `ts.ohlcv` PK 에 `exchange` 가 없다 — 2번째 거래소를 붙이면 캔들이 **조용히 폐기**된다
**Category:** Market data / 스키마
**Priority:** P2
**Trigger:** ★2번째 거래소 데이터 적재를 시작할 때 (**그 전에** 해야 한다 — 뒤에 하면 이미 유실된 데이터를 복구할 수 없다) ★**2026-08-18 — 「멀티 거래소 확장」 묶음**(`roadmap.md` §권장착수순서 7): [BL-015]·BL-186b·[BL-756]·[BL-426] 넷이 「2번째 거래소를 붙인다」는 **하나의 사용자 결정**에 걸려 있다. 그 결정 전에는 단독 착수 시 값이 0이다. ★**단 이 항목이 묶음의 첫 순서다** — 순서 제약이 있다
**Est:** M (hypertable PK 변경 + 백필 + 조회 필터 전수)
**출처:** 2026-08-15 surface-truth 아키텍처 감사 §A-7

**원인 / 영향:** `market_data/models.py` 의 `ts.ohlcv` PK 에 `exchange` 컬럼이 없고
`repository.py` 의 조회 필터에도 없다. 지금은 `DEFAULT_EXCHANGE=bybit` 단일이라 증상이 없다.
2번째 거래소를 붙이면 **같은 (symbol, timeframe, timestamp)** 행이 충돌하고, upsert 경로에서
나중 것이 앞 것을 덮거나 무시된다 — 어느 쪽이든 **조용하다**.

★백테스트가 그 데이터를 읽으므로, 증상은 「데이터가 없다」가 아니라 **「다른 거래소의 캔들로
백테스트가 돌았다」**로 나타난다. 이 스프린트가 고치고 있는 병(화면이 사실이 아닌 것을 말한다)과
같은 계열이고, 여기서는 원장이 그렇게 한다.

**권장 접근:** PK 에 `exchange` 를 넣기 전에 **조회 경로 전수**(`repository.py` · 캐시 키 ·
`funding_rates` 대칭)를 먼저 훑어라. 한 곳이라도 필터를 빠뜨리면 「행은 나뉘었는데 조회는
안 나뉜」 더 나쁜 상태가 된다.

**Risk:** 🟡 (hypertable PK 변경은 재적재를 부를 수 있다)

**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-15 감사에서 코드 대조로 확인. 미착수
**트리거 판정:** 미도래 — 지금 적재는 `DEFAULT_EXCHANGE=bybit` 단일이다 (2026-08-15 surface-truth)

---

### BL-758

**Title:** `entry(limit=)` 의 **라이브 발주 축** — 지금은 fail-closed 로 막고 있다
**Category:** Trading / 라이브 발주
**Priority:** P3
**Trigger:** ★사용자가 지정가 진입 전략을 **라이브로 돌리려 할 때**. 그 전에는 값이 0이다 — 지금은 막는 것이 옳다
**Est:** M (`OrderRequest` 에 limit 축 + 거래소 주문 종류 매핑 + reconciler 대칭 + maker 비용 가정)
**출처:** 2026-08-15 surface-truth U8

**원인 / 영향:** 2026-08-15 에 `strategy.entry(limit=)` 을 백테스트 엔진이 지정가로 체결하도록
고쳤다. 라이브는 **의도적으로 막았다** — 발주 경로(`OrderRequest`)가 `trigger_price`(stop)
하나만 표현하므로, 내보내면 지정가 의도가 왜곡돼 거래소에 도달한다.
사유 라벨 `limit_entry_unsupported_live` 로 관측 가능하고, 리포트 ⑨ 가 그 사실을 선언한다.

**권장 접근:** 열려면 ⑴ `OrderRequest` 에 limit 축(주문 종류 + 가격) ⑵ reconciler 의 desired
비교가 limit 주문을 인식 ⑶ **비용 가정 재검토** — 지정가는 maker 이고 지금 백테스트 비용
가정(taker 0.055%/leg)은 taker 기준이다. 그대로 두면 리포트가 **비관 편향**이 된다
⑷ 미체결 지정가의 sweep 정책([U4] 와 같은 자리).

★같은 뿌리의 잔여: `trail_points` / `trail_offset` / `qty_percent` 는 여전히 미지원이고
「무시했다」 경고를 낸다. 그 경고는 이제 리포트 ⑨ 에 **보인다**(2026-08-15 배선).

**Risk:** 🟡 (거래소 주문 종류를 늘리는 것은 돈 경로 확대다)

**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-15 에 백테스트 축만 열고 라이브는 fail-closed 로 못박았다
**트리거 판정:** 미도래 — 지정가 진입을 라이브로 돌리려는 사용자가 아직 없다 (2026-08-15 surface-truth)

---

### BL-759

**Title:** 2026-08-15 아키텍처 감사 **잔여 발견 원장** — §A 인프라 / §B 계층 / §C 엣지의 미수리분
**Category:** Meta / 감사 원장
**Priority:** P3
**Trigger:** ★해당 영역을 손대는 회차가 올 때 (항목별로 다르다 — 이 원장은 **찾기 위한 색인**이지 단독 착수 대상이 아니다)
**Est:** 항목별 상이
**출처:** 2026-08-15 surface-truth 아키텍처 감사

**원인 / 영향:** 그 감사에서 P1 5건(S1~S5)을 수리했고, 그 아래 등급의 발견은 별도 BL 로
쪼갠 5건([BL-753]~[BL-757])을 빼면 **이 원장에만 남는다**. 목록을 잃으면 다음 사람이 같은
감사를 다시 돌려야 하므로 여기 적는다. **각 줄은 코드 대조로 확인된 것이고 추측이 아니다.**

**§A 인프라·설정**

- `backtest.run`·stress_test 에 **타임아웃 없음** + `visibility_timeout` 미설정(기본 3600) +
  `acks_late` ⇒ **도는 중에 재배달**. `optimizer_tasks.py:27-28` 만 예외
- 그 인프라 부재가 **사용자 대면 제약**이 됐다 — `grid_search.py:52` 의 `_MAX_GRID_CELLS=9`
  주석이 「soft_time_limit 부재 시 보호」라 적고, 그 9가 리포트 CTA 「그리드 최대 9조합」으로 노출
- Redis 락 URL 이 로그에 **평문**(`SecretStr` 아님) — 하필 Redis 가 죽었을 때 찍힌다
- 워커 엔진에 `pool_pre_ping` 없음(API 는 있다) + 일회용 엔진에 `QueuePool`
- hypertable **compression/retention 정책 0건**(`add_*_policy` 레포 0건)
- **CI 만 `uv sync --frozen` 누락**(Docker·FE 는 고정) ⇒ 조용히 re-lock
- `ci.yml` 7개 job 전부 `timeout-minutes` **없음**(다른 워크플로엔 있다)
- ~~`.env.example` 골든룰 위반 — `HEALTHZ_CELERY_TIMEOUT_S`(os.environ 직독) 외 4~~
  → ★**2026-08-16 실측 정정 — 「외 4」가 과대였다. 실질 1건이다.** `src/` 의 `os.environ`·
  `os.getenv` 직독 중 `.env.example` 에 없는 것은 **4종**이지만, 그중 3종은 **인프라 주입**
  이라 위반이 아니다 — `HOSTNAME`(`apps/web/Dockerfile:23`) ·
  `PROMETHEUS_MULTIPROC_DIR`·`QB_METRICS_ROLE`(`infra/compose/docker-compose.yml:102,103`,
  그리고 배포 호스트의 `quantbridge-api.service` 유닛). 어디에도 선언이 없는 것은
  **`HEALTHZ_CELERY_TIMEOUT_S` 하나뿐**이다
- `cloudflare/cloudflared:latest` — **유일한 부동 태그**이고 프로덕션 FE 터널
- `python-jose` **import 0건**인데 `ecdsa`(CVE-2024-23342)를 끌고 온다

**§B 계층·인터페이스**

- **라우터가 Repository 를 직접 생성 11건 + service private `_repo` 를 5건 뚫는다**
  ⇒ LESSON-019 commit-spy 회귀 테스트가 **그 경로엔 적용 불가**
  → ★**[BL-762] 로 분리 (2026-08-16).** `_repo` 5건 + `_crypto` 2건은 그 회차에 수리됐고
  commit-spy 가 처음으로 성립했다. `Repository()` 직접 생성 11건은 미착수
- ~~**Repository 밖 `session.execute` 8건**~~ → ★**9건이다 (2026-08-16 재실측)**.
  그중 2건은 코드가 자백(「OrderRepository 가 이 메소드를 직접 제공하지 않으면 raw SQL 로」)
  → **[BL-763] 로 분리**
- ★**에러 응답 봉투가 7모양** — 문서(`system-architecture.md:200-206`)가 정본이라 그린
  `{code,message,details}` 를 만드는 코드는 **한 줄도 없다**. 2026-08-15 의
  `RequestValidationError` 핸들러가 그중 하나를 줄였다
- `raise HTTPException` 38건(문자열 detail 33건) — **그중 13건이 `services/` 안**(계층 위반)
- **페이지네이션 6모양** — 정본 `Page[T]` 채택률 4/10. `/orders`·`/kill-switch/events` 는
  **response_model 자체가 없다**(OpenAPI 에 타입 0)
  → ★위 **에러 봉투 · `raise HTTPException` · 페이지네이션 3축은 [BL-764] 로 분리**
  (2026-08-16). 셋 다 「화면이 무엇을 받을지 모른다」로 수렴하므로 한 항목에 묶었다
- status code 계약 위반 2건 — `cancel` 이 `response_model` 과 다른 body 를 202 로, 웹훅이
  201 선언 후 replay 시 200. ★**FE 가 산문 문자열에 파싱을 못 박았다**
  (`z.literal("exchange cancel requested")`)
- `OrderService` 가 `AsyncSession` 보유 — `apps/api/AGENTS.md` §3 이 「절대 금지」라 쓴 것
- ★**순환 import 1건 추가 확인 (2026-08-16)** — `orders-blotter.tsx:52` → `order-detail-drawer.tsx`
  → `orders-blotter.tsx:41`. 드로어가 가져가는 것은 **순수 도메인 술어 2개**
  (`displayRealizedPnl`·`realizedPnlSource`)뿐이라, 그 둘을 `features/trading/` 로 내리면
  고리가 끊긴다(3파일 기계적 이동). ★`app/` 에 비즈니스 로직을 두지 말라는 FSD Lite 규칙
  (`apps/web/AGENTS.md` §4)의 실례이기도 하다. 현재 빌드·e2e 는 통과하므로 급하지 않다
- 런타임 import 순환 **5건** · **FSD Lite 역전**(`app/` 23,313줄 : `features/` 12,456줄) +
  eslint 에 import boundary 규칙 **0개**
- **codegen 이 존재하는데 앱이 한 줄도 안 쓴다** — `generated/` import 0건, drift `--check` 는
  만들어졌는데 CI 에 미배선
- `leverage` 한 개념이 **BE 5타입 / FE 4타입**
- ~~`tasks/live_signal.py` **4,485줄**~~ → **4,493줄 (2026-08-16 재실측 — #641 이 8줄 늘렸다)**
  — 최대 파일이자 돈 경로인데 도메인 디렉터리 밖이라 3-Layer 감시 대상이 아니다
  → **[BL-765] 로 분리**

**§C 에러·엣지**

- **웹훅이 rate limit 전면 면제 + 인증 실패 전에 DB 조회 + Fernet 복호** ⇒ 무인증 증폭 표면
- **명목가/최소주문 가드가 로그도 메트릭도 없이 fail-open** — 거래소 API 가 흔들리면
  서버 권위 사이징이 조용히 사라진다
- 웹훅 시크릿 rotate 에 **1시간 grace** — 유출 인지 후 즉시 폐기 경로가 없다(`mark_revoked`
  호출처 0). FE 주석은 「5분」이라 **12배 어긋남**. ★2026-08-15 에 **탈퇴 경로만** grace 0 이 됐다
- admin 권한이 **매 요청 JWT claim 으로 덮이는 `users.email`** 에 걸려 있다. `email` 컬럼에 unique 없음
- `/healthz` 가 **무인증·rate-limit 면제**로 내부 인프라 에러 문자열(`str(exc)`)을 반환
- `pine_source` 에 **길이 상한 없음** + `/strategies/parse` per-route 한도 없음
- 포지션 청산에 **멱등키·락 없음**(`idempotency_key=None`) ⇒ 더블클릭에 reduce-only 중복 발주
- 비ASCII 토큰 → `hmac.compare_digest` **TypeError → 500**(무인증 도달 가능)
- LLM 변환 라우터가 SDK 예외 원문을 클라이언트에 반사
- N+1 3건 — `alert_rules.py:70-84`(룰 N개당 집계 + **거래소 API** N회) · janitor · `live_signal.py:1645`

**권장 접근:** 항목별로 별도 BL 을 열 때 **이 줄을 근거로 인용하고 코드 대조를 다시 해라** —
이 원장의 줄번호에는 유효기한이 있다(이 레포가 반복해서 겪은 사고다).

**Risk:** 🟢 (원장 전용 — 코드 변경 0)

**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-15 에 색인으로만 등재. 항목별 착수는 그 영역을 손댈 때
**트리거 판정:** 미도래 — 단독 착수 대상이 아니다. 해당 영역 회차가 열릴 때 여기서 꺼내 쓴다 (2026-08-15 surface-truth)

---

### BL-760

**Title:** `/healthz` 와 주기 관측이 Redis **쓰기 가능성을 안 잰다** — `noeviction` OOM 이 「정상」으로 보인다
**Category:** Ops / 관측
**Priority:** P2
**Trigger:** ★Redis used-memory 가 `maxmemory` 의 70% 를 넘는 것이 관측될 때 · 또는 `noeviction` 쓰기 거부가 실제로 한 번 발생했을 때
**Est:** S (`/healthz` 에 쓰기 프로브 + 게이지 주기 갱신)
**출처:** 2026-08-15 surface-truth 적대 리뷰 (codex P2)

**원인 / 영향:** 2026-08-15 에 Redis 정책을 `allkeys-lru` → `noeviction` 으로 바꿨다([S4]).
그 대가는 **OOM 에서 쓰기가 거부되는 것**이고, 그 상태는 반드시 관측돼야 한다.

★**그런데 관측 축이 셋 다 PING 이었다:**

- `common/redis_client.py:healthcheck_redis_lock` 의 SET+GET+DEL 왕복은 **lifespan startup 1회**뿐이다
- compose healthcheck 는 `redis-cli ping` 이었다 → **2026-08-15 에 쓰기 프로브로 교체**
- `health/router.py` 의 `/healthz` 는 여전히 `pool.ping()` 이다 ← **잔여**

PING 은 OOM 에서도 PONG 을 낸다. ⇒ 기동 후 OOM 은 `/healthz` 초록 + `qb_redis_lock_pool_healthy=1`
(기동 시 1로 세팅된 뒤 갱신되지 않는다)로 보이고 `QbRedisLockPoolUnhealthy` 도 발화하지 않는다.

★**이 항목은 이 회차 자신의 커밋 주석이 거짓이었다는 기록이기도 하다** — compose 주석에
「healthcheck 가 SET+GET+DEL 왕복이라 그 상태를 잡는다」고 적었고 적대 리뷰가 반증했다.
주석은 정정했고 compose 는 고쳤다.

**권장 접근:** ⑴ `/healthz` 의 redis 축을 쓰기 프로브로 올린다 — **다만 호출 빈도를 먼저 재라**
(`/healthz` 는 자주 불린다. 짧은 TTL 키 + 샘플링이 필요할 수 있다) ⑵ `qb_redis_lock_pool_healthy`
게이지를 주기적으로 갱신한다(지금은 startup 에서만 쓴다) ⑶ used-memory 를 함께 노출해
**거부되기 전에** 보이게 한다.

**Risk:** 🟡 (⑴ 을 무겁게 만들면 healthz 자신이 부하가 된다)

**상태:** ⏳ **대기 (트리거 미도래)** — compose 축은 2026-08-15 에 닫았다. `/healthz`·게이지 축은 미착수
**트리거 판정:** 미도래 — 현 Redis 사용량은 `maxmemory 512mb` 대비 낮고 쓰기 거부가 관측된 적이 없다 (2026-08-15 surface-truth)

---

### BL-761

**Title:** 지정가 진입의 백테스트 비용이 **taker 로 과대 계산**된다 — 리포트가 비관 편향이 된다
**Category:** Backtest / 비용 모델
**Priority:** P2
**Trigger:** ★`entry(limit=)` 전략의 백테스트 결과를 **의사결정에 쓰려 할 때** (지금은 그 기능이 막 열렸다) · 또는 [BL-758] 라이브 축을 열 때 동승
**Est:** M (entry 비용 분기 + 골든 재계산 + 리포트 문구)
**출처:** 2026-08-15 surface-truth 적대 리뷰 (codex P2)

**원인 / 영향:** `v2_adapter.py` 의 entry 비용은 `fill_type="taker"` **고정**이다. 그런데
2026-08-15 에 연 `entry(limit=)` 은 **다음 bar 까지 대기하는 resting limit** 이라 실제로는
maker 다. 같은 레포의 exit 축은 이미 그 계약을 갖고 있다 — `exit_orders.py` 가
「TP = resting limit → maker」라고 적는다.

⇒ 지정가 진입 전략의 백테스트는 **수수료와 슬리피지를 둘 다 과대 계상**한다(진입 leg 에
taker 요율 + 진입가 잔차). 리포트는 실제보다 나쁜 곡선을 보여주고, 이 스프린트가 고치려는
「화면이 사실이 아닌 것을 말한다」의 **반대 방향 판**이다.

★**부호가 안전한 쪽이라 급하지 않다** — 과대 계상은 사용자를 낙관시키지 않는다.
그래서 P1 이 아니다. 다만 **의사결정 입력으로 쓰이기 전에** 고쳐야 한다([BL-729] 가
「낡은 비용 가정으로 전략을 골랐다」로 같은 병을 이미 한 번 겪었다).

**권장 접근:** ⑴ 진입 leg 의 `fill_type` 을 **주문 종류에서 파생**시킨다(resting limit → maker,
시장가·stop 돌파 → taker) ⑵ 골든 12종은 `entry(limit=)` 을 안 쓰므로 **불변이어야 한다** —
그것이 음성 대조다 ⑶ 리포트 ⑨ 가 「이 실행의 진입은 maker 로 계산됐다」를 말하게 한다.

**Risk:** 🟡 (비용 모델 변경은 과거 백테스트와 비교 불가를 만든다 — 문구로 선언해야 한다)

**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-15 에 지정가 진입 기능만 열었다. 비용 축은 미착수
**트리거 판정:** 미도래 — 지정가 전략의 백테스트를 의사결정에 쓴 적이 아직 없다 (2026-08-15 surface-truth)

---

### BL-763

**Title:** Repository 밖에서 `session.execute` 를 치는 곳이 9건 — AsyncSession 단독 보유 규칙 위반
**Category:** Backend / 계층 (trading · tasks)
**Priority:** P2
**Trigger:** ★해당 파일을 손대는 회차 (전량 수리는 단독 착수 대상이 아니다)
**Est:** M
**출처:** 2026-08-15 surface-truth 아키텍처 감사 §B ([BL-759] 에서 분리) · 2026-08-16 실측 재확인

**원인 / 영향:** `AGENTS.md` §3 = 「Repository — AsyncSession 유일 보유. DB 접근만」.
`session.execute` / `db.execute` 가 repository 밖에서 돌면 그 쿼리는 **repository 테스트가
보는 표면 밖**이고, 스키마가 바뀔 때 같이 안 움직인다.

**2026-08-16 실측 — 9건 / 6파일** (원장의 종전 「8건」을 정정한다):

| 파일                                      | 건수 |
| ----------------------------------------- | ---- |
| `src/trading/dependencies.py`             | 3    |
| `src/trading/kill_switch.py`              | 2    |
| `src/tasks/websocket_task.py`             | 1    |
| `src/trading/funding.py`                  | 1    |
| `src/trading/websocket/reconciliation.py` | 1    |
| `src/trading/websocket/state_handler.py`  | 1    |

★그중 2건은 **코드가 자백한다** — 「OrderRepository 가 이 메소드를 직접 제공하지 않으면
raw SQL 로」. 즉 이것은 실수가 아니라 **repository 표면이 부족해서 우회한 흔적**이다.
⇒ 수리 방향은 「옮긴다」가 아니라 **repository 에 그 메소드를 만든다**.

**Risk:** 🟢 (동작 정상 — 회귀 방어면이 좁을 뿐)

**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-16 에 코드 대조로 9건 확정. 미착수
**트리거 판정:** 미도래 — 해당 6파일을 손대는 회차에 동승한다 (2026-08-16 deploy-activation)

---

### BL-764

**Title:** 응답 계약이 세 축에서 갈라져 있다 — 에러 봉투 7모양 · 서비스가 HTTP 예외를 던진다 · 페이지네이션 미통일
**Category:** Backend / API 계약
**Priority:** P2
**Trigger:** ★해당 endpoint 를 손대는 회차 · 또는 FE 가 에러 표면을 통일하려 할 때
**Est:** L (세 축이 각각 M — 쪼개서 착수한다)
**출처:** 2026-08-15 surface-truth 아키텍처 감사 §B ([BL-759] 에서 분리) · 2026-08-16 실측 재확인

**원인 / 영향:** 세 축 다 「화면이 무엇을 받을지 모른다」로 수렴한다.

- **⑴ 에러 봉투 7모양** — `system-architecture.md:200-206` 이 정본이라 그린
  `{code, message, details}` 를 만드는 코드가 **한 줄도 없다**. 2026-08-15 의
  `RequestValidationError` 핸들러가 그중 하나를 줄였다
- **⑵ `raise HTTPException` 13건이 `src/trading/services/` 안** (2026-08-16 실측 · 전체 38건 중).
  서비스가 HTTP 를 아는 순간 그 서비스는 Celery·다른 서비스에서 재사용 불가다 —
  도메인 예외(`src/trading/exceptions.py`)로 던지고 라우터/핸들러가 번역해야 한다
- **⑶ 페이지네이션 미통일** — 정본 `Page[T]`(`src/common/pagination.py:10`)를
  `response_model` 로 쓰는 endpoint 는 **4곳**(backtest 2 · optimizer 1 · stress_test 1 계열)
  이고, `PaginatedExchangeAccounts`(`trading/schemas.py:202`)는 **별개 모양 1곳**,
  `/orders`·`/kill-switch/events` 는 **`response_model` 자체가 없다**(OpenAPI 에 타입 0)

★**⑶ 을 먼저 건드리지 마라** — 2026-08-15 에 9필드를 non-nullable 로 바꾼 변경이 route mock
4곳의 파싱을 죽여 **목록을 통째로 빈 화면**으로 만들었다. **vitest 는 못 잡고 e2e 만 잡았다.**
응답 스키마를 조일 때는 `.default(null)` + 「구 fixture 회귀 방지」 관용구를 먼저 세워라.

**Risk:** 🟡 (⑶ 은 FE 파싱을 깨뜨릴 수 있다 — 위 전례 참조)

**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-16 에 세 축을 코드 대조로 확정. 미착수
**트리거 판정:** 미도래 — 축별로 해당 표면을 손대는 회차에 동승한다 (2026-08-16 deploy-activation)

---

### BL-765

**Title:** `src/tasks/live_signal.py` 가 4,493줄 — 레포 최대 단일 파일
**Category:** Backend / 구조 (tasks)
**Priority:** P3
**Trigger:** ★그 파일을 실질적으로 손대는 회차 (분할 자체를 목적으로 착수하지 마라)
**Est:** L
**출처:** 2026-08-15 surface-truth 아키텍처 감사 §B ([BL-759] 에서 분리) · 2026-08-16 실측 재확인

**원인 / 영향:** 2026-08-16 실측 **4,493줄**. 같은 도메인의 repository 2종은 338·220줄이다.
이 파일은 소크의 심장이고([BL-003] 판정이 여기서 나온다) 회차마다 손이 간다 — 한 파일이
크다는 것 자체보다 **변경 충돌면이 넓다**는 것이 비용이다.

★**분할을 단독 목적으로 착수하지 마라.** 이 파일은 라이브 신호 tick 경로라 리팩터가
곧 소크 리스크다. 실측 회귀 방어면(`test_live_signal_tick_oracle.py` 의 부작용 원장)이
이미 있으므로, **그것이 덮는 범위 안에서** 손대는 회차에 조금씩 떼는 것이 옳다.

**Risk:** 🟠 (이 파일의 리팩터는 소크 창을 끊을 수 있다)

**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-16 에 줄 수만 확정. 미착수
**트리거 판정:** 미도래 — 그 파일을 손대는 회차에 동승한다 (2026-08-16 deploy-activation)

---

### BL-776

**Title:** 대기자 명단이 있는데 **가입이 초대로 게이트되지 않는다** — Cloudflare Access 가 그 공백을 가려 왔다
**Category:** Backend / FE · 접근 제어
**Priority:** P1
**Trigger:** ★공개 전환([BL-070] Access 제거) **직전**. Access 가 걸려 있는 동안은 발현하지 않는다
**Est:** M (가입 훅에 초대 검증 + 토큰 소비 + 상태 전이 `invited → joined`)
**출처:** 2026-08-16 beta-cutover — 사용자가 「Access 를 왜 제거하나」라고 물어 재측정하다 확정

**원인 / 영향:** `/sign-up(.*)` 은 `apps/web/src/proxy.ts` 의 **공개 라우트**이고, Better Auth 의
`databaseHooks.user.create.before`(`apps/web/src/lib/auth.ts`)가 검사하는 것은 **국가 하나뿐**이다 —
초대 토큰도, 대기자 명단 상태도, 이메일 검증도 없다(`requireEmailVerification: false`).
`auth-form.tsx` 도 `signUp.email({email,password})` 만 부른다.

⇒ **Cloudflare Access 를 제거하는 순간 인터넷의 누구나 계정을 만든다.** 대기자 명단
([BL-072])은 존재하지만 **가입을 막지 않는다** — 승인 흐름과 실제 관문이 이어져 있지 않다.

★**이것은 새로 생긴 결함이 아니라 가려져 있던 것이다.** Access(이메일 OTP)가 앞단에 있어서
그 공백이 한 번도 발현하지 않았고, `/invite/[token]` 페이지가 이 회차에 생기면서 「초대 →
가입」 경로가 처음으로 화면에 존재하게 되자 드러났다.

**함께 볼 것:** 서버 `WAITLIST_ADMIN_EMAILS` 미설정(승인 엔드포인트 fail-closed 403) ·
`RESEND_API_KEY` 미설정(초대 메일 발송 불가) — 즉 지금은 **초대 파이프라인 자체가 안 돈다.**
그래서 Access 제거는 오늘 얻는 것이 0 이고 잃는 것만 있다.

**권장 접근:** ⑴ `create.before` 훅에서 초대 토큰을 검증한다 — FE 가 가입 요청에 토큰을 실어
보내고(초대 페이지에서 이어받는다) 훅이 BE `verify_invite_token` 으로 확인한다
⑵ 가입 성공 시 대기자 행을 `invited → joined` 로 전이하고 **토큰을 소비**한다(재사용 차단)
⑶ ★**음성 대조가 이 항목의 핵심이다** — 토큰 없이 `POST /api/auth/sign-up/email` 을 직접 쳐서
**거부되는지** 확인해라. 화면에 입력칸이 없는 것은 게이트가 아니다
⑷ 대안(코드 0): Beta 사용자 이메일을 Access 정책에 추가한다. 수십 명까지는 이쪽이 더 안전하다
(문이 둘로 유지된다) — 그 규모를 넘을 때가 ⑴~⑶ 의 진짜 트리거다

**Risk:** 🟠 (공개 전환과 묶여 있다. 이 항목 없이 Access 를 걷으면 **개방 가입**이 된다)

**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-16 에 코드 대조로 확정(`proxy.ts` 공개 라우트 · `auth.ts` 훅 · `auth-form.tsx`). Cloudflare Access 가 앞단에 있는 동안은 발현하지 않는다. 미착수
**트리거 판정:** 미도래 — Access 가 앞단에 있는 동안은 발현하지 않는다. 도래 = [BL-070] 의 Access 제거를 실제로 누르기 직전 (2026-08-16 beta-cutover)

### BL-778

**Title:** API **버저닝 정책 문서가 없다** — `/api/v1` 이 `main.py` 에 문자열로 9회 반복될 뿐이다
**Category:** Backend / 계약
**Priority:** P3
**Trigger:** ★**미도래** — 첫 breaking change 를 내거나, 우리가 통제하지 않는 외부 소비자가 생길 때
**Est:** S (정책 문서 1벌 + 상수화)
**출처:** 2026-08-16 표준 레이아웃 정렬 — 권장 구조(`docs/api/versioning.md`) 대비 실측

**원인 / 영향:** `apps/api/src/main.py` 의 `include_router` 9곳이 `prefix="/api/v1"` 를 각각
문자열로 적는다. 상수도 변수도 없다. 그리고 **v2 를 언제 왜 내는지, v1 을 언제까지 유지하는지**
를 정한 문서가 없다 — `interfaces/endpoints.md` 의 「공통 계약」은 4줄이고 버저닝을 다루지 않는다.

★**지금은 실해가 없다.** 소비자가 `apps/web` 하나뿐이고 같은 레포에서 같은 커밋으로 배포된다.
계약 drift 는 2026-08-16 에 배선한 `mise run openapi-check` 가 막는다. 버저닝이 필요해지는 것은
**우리가 배포 시점을 통제하지 못하는 소비자**(모바일 앱·외부 파트너)가 생기는 순간이다.

**권장 접근:** ⑴ 트리거가 오면 `docs/reference/interfaces/versioning.md` 신설 — 무엇이 breaking
인가(필드 제거·타입 변경·enum 값 제거) / 병행 유지 기간 / deprecation 헤더
⑵ `/api/v1` 을 상수로 뽑는다 — 지금 뽑아도 값은 없다(9곳이 전부 같고 바뀔 이유가 없다)
⑶ ★**빈 문서를 미리 만들지 마라** — 권장 구조에 칸이 있다는 것이 트리거가 아니다

**Risk:** 🟢 (소비자 1벌인 동안은 영향 0)

**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-16 에 코드 대조로 확정(`main.py` 9회 반복 · 정책 문서 0건). 소비자가 `apps/web` 하나인 동안은 발현하지 않는다
**트리거 판정:** 미도래 — 도래 = 첫 breaking change 발행 또는 배포 시점을 통제하지 못하는 소비자 등장 (2026-08-16 layout-alignment)

### BL-791

**Title:** `mise-shim-path.sh` 가 shim **디렉터리 존재만** 본다 — 빈/부분 설치면 조용히 구버전으로 폴백한다
**Category:** Infra / 게이트
**Priority:** P3
**Trigger:** ⏳ **대기** — CI 로그의 `⚠ mise shim 디렉터리가 없다` 유무가 판단 근거다
**Est:** S (내용물 검증 + fail 정책 결정)
**출처:** 2026-08-17 야간 CONTROL 적대 리뷰 (레인 β)

**원인 / 영향:** 함수는 디렉터리가 없으면 실패를 반환하지만 **모든 호출부가 `|| true` 로 무시**한다. 더 좁게는, 디렉터리 **존재만** 확인하므로 빈/부분 설치된 `shims/` 는 성공으로 처리되고 그 안에 `pnpm` shim 이 없으면 셸이 다음 PATH 항목의 구버전으로 조용히 폴백한다. 버전이 호환되면 게이트는 초록을 낸다 — **[BL-785] 가 닫으려던 바로 그 모양이 좁은 경우로 남아 있다.**

**처방:** fail-closed 로 바꾸면 mise 없는 러너에서 게이트가 **전부** 죽으므로 그것이 옳은지는 CI 실행 결과가 정한다. **PR #658 의 CI 로그에 그 경고가 있었는지 먼저 확인하고**, 있으면 「CI 에는 mise 가 없다」가 확정되므로 fail-open 을 유지하되 경고를 게이트 요약에 올린다. 없으면 내용물 검증(`command -v pnpm` 이 shim 경로를 가리키는지)을 추가할 수 있다.

**Risk:** 🟡 (fail 정책 변경. 잘못 조이면 CI 가 통째로 red)

**상태:** ⏳ **대기 (트리거 미도래)** — CI 로그 확인이 선행이다
**트리거 판정:** 미도래 — 판단 근거(CI 로그)를 아직 안 읽었다

---

### BL-792

**Title:** `tool-pin-audit.sh` 의 알려진 사각 둘 — **핀 위치를 안 보고**, 간접 실행을 못 본다
**Category:** Infra / 게이트
**Priority:** P3
**Trigger:** ⏳ **대기** — 레포에 그 두 형태가 현재 0건이다
**Est:** M (셸 파서 수준의 판정이 필요하다)
**출처:** 2026-08-17 야간 CONTROL 적대 리뷰 (레인 β)

**원인 / 영향:** ⑴ 호출은 **명령 위치**로 판정하지만 핀은 「파일 어딘가에 source + `qb_pin_tool_path` 문자열이 있으면 참」이다 — 도달 불가한 `if false; then … fi` 안에 넣어도 통과한다. ⑵ `tool=pnpm; "$tool" install` 이나 `eval 'uv run pytest'` 는 호출 정규식에 안 걸려 위반 0건이 된다.

⇒ **「감사기가 초록이다」는 「위반이 없다」가 아니라 「내가 아는 형태의 위반이 없다」가 참인 문장이다.** 이 감사기는 실수 재유입을 막는 장치이지 적대적 우회를 막는 장치가 아니다.

**처방:** 임의의 간접 실행을 정적으로 잡으려면 셸 파서가 필요하다 — 결함 크기에 비해 큰 장치다. 실용적 대안은 핀 **위치**만 보는 것(핀 소싱이 첫 도구 호출보다 앞 줄에 있는가). 레포에 그 두 형태가 실제로 나타나면 그때 착수해라.

**Risk:** 🟢

**상태:** ⏳ **대기 (트리거 미도래)** — 그 두 형태가 레포에 0건이다
**트리거 판정:** 미도래 — 전수 grep 0건

---

### BL-793

**Title:** dashboard static 라우트 8개가 dynamic 이 됐다 — [BL-786] 수리의 측정된 대가
**Category:** 프런트 / 성능
**Priority:** P3
**Trigger:** ⏳ **대기** — TTFB/TTI 측정이 선행이다
**Est:** M (대안 구현 + 양쪽 측정)
**출처:** 2026-08-17 야간 CONTROL `/vercel-react-best-practices` 검토 (레인 γ)

**원인 / 영향:** [BL-786] 이 `(dashboard)/layout.tsx` 에서 `getServerAuth()` 를 부르면서 그 세그먼트 아래가 dynamic rendering 으로 내려갔다. 이 레포에는 미들웨어가 없고 dashboard 페이지 14개 중 **12개는 서버에서 인증을 건드리지 않았으므로** `React.cache` 가 합쳐 줄 상대가 없다 — 순수 추가다.

**대조 빌드 2회(같은 트리, layout 만 교체)로 확정: static 라우트 16 → 8.** 뒤집힌 8개 = `/admin/waitlist` · `/backtests/new` · `/dashboard` · `/onboarding` · `/optimizer` · `/orders` · `/strategies/new` · `/trading`.

★**그럼에도 유지가 옳다고 판단했다** — 이 8개는 로그인해야 보이는 화면이고 static 이라는 것은 「빈 껍데기를 주고 데이터는 전부 브라우저가 가져온다」는 뜻이었다(정확히 [BL-786] 이 고친 구조). 교환비도 유리하다: 서버 왕복 1회 추가 vs 브라우저 요청 `/dashboard` 15→8.

**처방:** 대안이 있다 — 쿼리를 `enabled: !isPending` 으로 막으면 anon 키 요청이 아예 안 나가므로 중복도 없고 static 도 유지된다. 대가는 첫 데이터가 세션 왕복 뒤에 시작된다는 것(TTI 지연). **어느 쪽이 나은지는 TTFB/TTI 를 재기 전에는 정할 수 없다** — 이 회차는 그것을 재지 않았다.

**Risk:** 🟡 (렌더링 모드 변경. 잘못 고르면 체감이 나빠진다)

**상태:** ⏳ **대기 (트리거 미도래)** — 측정 없이 판단하지 마라
**트리거 판정:** 미도래 — TTFB/TTI 실측이 선행 조건이다

---

### BL-794

**Title:** e2e rate limit 면제가 **신원 소유를 증명하지 않는다** — JWT `email` 문자열 일치일 뿐이다
**Category:** 보안 / 테스트
**Priority:** P3
**Trigger:** ⏳ **대기** — 표면이 `app_env == development` 로 좁혀져 있다
**Est:** M (신원 증명 방식 재설계)
**출처:** 2026-08-17 야간 CONTROL 적대 리뷰 (레인 α)

**원인 / 영향:** 면제 판정은 JWT 의 `email` 만 비교하고 그 이메일이 우리가 만든 계정의 것인지, 검증됐는지는 안 본다. 한편 가입은 공개이고 `apps/web/src/lib/auth.ts:66` 이 `requireEmailVerification: false` 다. e2e setup 자신도 `/api/auth/sign-up/email` 공개 엔드포인트로 계정을 만든다(`global.setup.ts:49`). ⇒ 그 변수가 설정된 인스턴스에서 **해당 계정이 아직 없으면** 아무나 그 이메일로 가입해 면제를 얻는다.

★**동작 유지 근거 셋** — ⑴ 표면이 `development` 로 좁혀졌다(staging·production 은 런타임 판정과 부팅 검사 두 층이 막는다). 거기 접근할 수 있는 공격자는 이미 더 큰 것을 갖는다 ⑵ 대안이 더 나쁘다: `sub` 는 DB 를 다시 만들 때마다 바뀌어 설정에 못 적고, 이메일 검증을 요구하면 e2e 부트스트랩이 메일함을 필요로 한다 ⑶ 선점은 탐지된다 — 우리 계정이 있으면 가입이 거부되고, 선점이 성공했다는 것은 우리 계정이 없었다는 뜻이라 스위트가 로그인에 실패한다.

**Risk:** 🟢 (development 한정)

**상태:** ⏳ **대기 (트리거 미도래)** — 표면이 좁고 대안이 더 비싸다
**트리거 판정:** 미도래 — development 밖으로 나가는 계기가 없다

---

### BL-796

**Title:** [BL-788] census 파서가 못 보는 표 선언 3형태 — 그 모듈을 아무도 import 하지 않으면 **네 다리 전부 초록**이다
**Category:** 테스트 / 인프라
**Priority:** P3
**Trigger:** ⏳ **대기** — `src/**` 실사용례 **0건**(2026-08-17 전수 grep). 셋 중 하나라도 쓰이기 시작하면 도래
**Est:** S (파서 확장 — 다만 아래 「왜 지금 안 하나」를 먼저 읽어라)
**출처:** 2026-08-17 metadata-scope — `/codex` 적대 리뷰 수리 뒤 독립 검증자가 찾음

**원인 / 영향:** `apps/api/tests/test_metadata_table_coverage.py` 의 census 는 `src/**` 를 AST 로 훑어
표 선언을 모으고, 그것이 이 검사면의 **유일한 기대치 원천**이다. 파서가 못 보는 형태가 셋 남았다:

- ⓐ **대입 별칭** — `T = Table` 뒤의 `T("x", SQLModel.metadata, ...)`. `_local_aliases` 는 import 문만 본다
- ⓑ **서브클래스** — `class MyTable(Table): ...` 뒤의 `MyTable("x", SQLModel.metadata, ...)`
- ⓒ **동적 속성** — `getattr(sa, "Table")("x", SQLModel.metadata, ...)`

★**위험한 것은 「못 본다」가 아니라 「못 보는 것이 조용하다」이다.** census 가 그 모듈을 못 보면
선언 축은 「import 할 것이 없다」로 통과하고, 그 모듈을 아무도 import 하지 않으면 실행 축도
「등록된 것이 census 와 같다」로 통과한다 — **네 다리가 전부 초록**이다. 이것이 [BL-788] 본체와
정확히 같은 구조다(실행 축이 보는 것은 **누군가 import 한** 모듈뿐이라 선언 축의 사각을 못 덮는다).

**처방:** 실제로 쓰이기 시작하면 파서를 넓혀라. 그때까지는 검사면 머리의 「★★초록이 말하지 않는 것」
절이 정본이다 — **「이 파일의 초록은 『그런 표가 없다』가 아니라 『내가 본 형태 중에는 없었다』만
말한다」**(`apps/api/AGENTS.md` §10).

**왜 지금 안 하나:** 쫓으려면 파서가 대입·상속·동적 속성을 추적해야 하는데 그 추적이 **순서 의존**이라
막는 결함보다 새로 만드는 결함이 크다. 그리고 셋 다 사고가 아니라 **적대적 저자**의 형태다 —
검사면이 잡아야 하는 것은 사고다. 같은 판정을 [BL-789] 의 셸 제어흐름 모델링에서도 내렸다.

**Risk:** 🟢 (테스트 검사면의 사각. 프로덕션 무관)

**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-17 등재. 실사용례 0건
**트리거 판정:** 미도래 — `src/**` 에 ⓐⓑⓒ 어느 형태도 없다(전수 grep 실측)

---

---

### BL-798

**Title:** 스트레스 테스트 목록 질의가 `result` JSONB 를 통째로 읽는다
**Category:** Backend / 성능
**Priority:** P3
**Trigger:** ⏳ **대기** — 한 백테스트의 스트레스 실행이 늘거나 목록 응답 지연이 관측될 때
**Est:** S-M
**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-17 [BL-414] 회차에 확인. `list_by_user` 가 `select(StressTest)` 로 전 컬럼을 읽고 `Page[StressTestSummary]` 는 `result` 본문을 안 내보낸다. MC 의 `result.equity_percentiles` 는 5계열 시계열이라 `limit=20` 이면 전송량이 응답 크기와 무관하게 커진다.
**트리거 판정:** 미도래 — **규모 조건**이다. 현 실측(개발 DB `stress_tests` 0건)에서는 발화하지 않는다 (2026-08-17 night3 레인 γ)
**출처:** 2026-08-17 night3 레인 γ ([BL-414] 이력 화면)

**원인 / 영향:** [BL-414] 가 추가한 `headline_metric` 은 **이미 읽고 있던** 컬럼에서 파생하므로 비용을 늘리지 않는다. 다만 그 파생 때문에 「목록이 `result` 를 읽는다」가 이제 **의도적 의존**이 됐다 — 최적화 시 그 의존을 함께 처리해야 한다.

**권장 접근:** `load_only` 로 목록 질의 컬럼을 좁히되 `result` 는 남기거나(파생에 필요), 대표 지표를 실행 완료 시점에 별도 컬럼으로 비정규화한다. 후자는 [BL-429] 가 optimizer 에서 쓴 패턴과 같다.

**Risk:** 🟢 정확성 문제 없음.

---

### BL-799

**Title:** 최적화 목록 응답이 `result` 를 통째로 싣는다 — iteration 전량이 행마다 따라온다
**Category:** Backend / 성능
**Priority:** P3
**Trigger:** ⏳ **대기** — `max_evaluations` 가 큰 run 이 쌓이거나 대시보드 §03 지연이 관측될 때
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-17 [BL-429] 회차에 관측. `GET /api/v1/optimizer/runs` 의 `OptimizationRunResponse.result` 는 `dict[str, Any]` 전량이다.
**트리거 판정:** 미도래 — **규모 조건**이다. [BL-710] 과 같은 성격이되 대상이 다르다(그쪽은 `/strategies`) (2026-08-17 night3 레인 β)
**출처:** 2026-08-17 night3 레인 β ([BL-429] 작업 중 관측)

**원인 / 영향:** grid 는 cell 전부, bayesian·genetic 은 iteration 전부가 행마다 실린다. 대시보드 §03 은 그중 best 두 값만 쓰는데 `max_evaluations=100` 짜리 run 8건이면 목록 한 번에 iteration 800개가 따라온다.

**권장 접근:** ★**[BL-429] 가 그 두 값을 별도 필드로 뽑았으므로 이제 목록에서 `result` 를 뺄 수 있다** — 다만 `/optimizer` 목록 화면이 `result` 를 쓰는지 먼저 확인해야 한다(objective 열·best 열이 raw value 를 그린다).

**Risk:** 🟡 FE 소비자 확인이 선행이다. 안 보고 빼면 `/optimizer` 목록이 빈다.

---

### BL-800

**Title:** 화면 증거 게이트의 CI 게시 경로 — 리눅스 baseline 과 PR 코멘트 자동화
**Category:** 테스트 / 인프라 / CI
**Priority:** P3
**Trigger:** ⏳ **대기** — [BL-797] 의 측정 축이 서고 나서. 라우트 집합이 확정돼야 baseline 을 굽는 값이 있다
**Est:** M
**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-17 night3 에 로컬 경로까지만 착지했다. baseline 스냅샷이 `-darwin` 접미뿐이고 리눅스 판이 없어 `e2e-project-wiring.test.ts` 의 `LOCAL_ONLY["chromium-screen-evidence"]` 로 CI 에서 제외돼 있다. 표는 사람이 `gh pr comment --body-file` 로 올린다.
**트리거 판정:** 미도래 — **선행 조건**([BL-797]). 라우트 집합이 바뀌면 구운 baseline 을 다시 구워야 한다 (2026-08-17 night3 CONTROL)
**출처:** 2026-08-17 night3 레인 α (레인 파일 갈래 ⑵ 미착수)

**원인 / 영향:** 지금은 게이트가 로컬에서만 돌고 리포트도 사람이 붙인다. CI 가 돌리면 「화면을 바꾼 PR 이 증거 없이 지나갈 수」 없게 되지만, 그러려면 리눅스에서 픽셀이 결정적이어야 한다.

**권장 접근:** 리눅스 baseline 을 굽고 워크플로에 프로덕션 서버 스텝을 넣은 뒤 `actions/github-script` 로 코멘트 게시. 선례 `nightly-real-broker.yml:207`. 그때 `LOCAL_ONLY` 항목을 걷는다.

**Risk:** 🟡 빌드가 `next/font/google` 로 네트워크에 매달려 있다 — 레인 α 실측에서 13회 중 1회가 폰트 CSS 를 못 받아 죽었다. **오프라인이면 이 게이트는 못 돈다.**

### BL-801

**Title:** 인덱스 표 행의 `#bl-nnn` 앵커가 **본문이 사는 파일을 안 가리킨다** — 원장 3분할의 잔여
**Category:** 문서 / 원장 위생
**Priority:** P3
**Trigger:** 동승 — 인덱스 표의 **제목 셀을 줄이는 회차**. 단독으로 열지 마라(앵커만 고치면 상한을 다시 넘는다)
**Est:** M (앵커 치환은 1줄 · 본체는 제목 셀 감축)
**출처:** 2026-08-18 backlog-triage — 원장 3분할([BL-779]) 실행 중 실측

**상태:** ⏳ **대기 (트리거 미도래)** — 접두사를 실제로 붙여 봤고 **되돌렸다**. 회귀가 아니라 측정된 대가다
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 제목 셀 감축이 선행이라 값이 0이다 (2026-08-18 backlog-triage)

**원인 / 영향:** 인덱스 표 행 **172건 전량**이 `| [BL-nnn](#bl-nnn) |` 로 같은 파일을 가리키는데,
본문 **313건**은 `backlog-deferred.md`·`backlog-resolved.md` 에 산다. 즉 `AGENTS.md`·`status.md` 가
「`#bl-NNN` 앵커로 열어라」라고 지시하는 그 앵커가 **대부분 아무 데도 안 간다**.
★**이건 3분할이 만든 결함이 아니다** — 2026-08-16 1차 분할 시점에 이미 120건이 그랬고, 아무도 안 봤다.

**★수리를 시도했고 반증됐다 (2026-08-18 실측).** 접두사(`backlog-deferred.md#bl-nnn`)를 156행에 붙였더니
행마다 **+18자**가 붙고, prettier 가 표 전체를 최장 셀에 맞춰 패딩하므로 **P2 표의 모든 줄이 함께** 자랐다 —
`docs-audit` 의 줄 길이 상한 **1,000자**에 대해 실측 **985 → 1,012자**, 위반 11행. 그 게이트 자신의 규약이
「상한을 올려 통과시키지 마라」이므로 되돌렸다.
★**부수로 드러난 구조적 취약성** — `docs-audit` 은 **문자 수**로 재고 prettier 는 **표시 폭**(CJK=2)으로
패딩한다. 한국어 표는 두 눈금이 어긋난 채 상한 1.5% 아래에 붙어 있어, **긴 행 하나가 표 전체를 넘긴다.**

**권장 접근:** 순서가 있다. ⑴ 인덱스 표의 **제목 셀을 요약으로 줄인다**(본문이 이미 다른 파일에 있으므로
행은 포인터면 된다 — 최장 4건이 표시폭 742~778). ⑵ 여유가 생기면 앵커 접두사를 붙인다. ⑶ `docs-audit` 의
줄 길이 축을 **표시 폭**으로도 재는 것을 검토한다(지금은 prettier 와 눈금이 다르다).
★**그 전까지 위치를 묻는 정본은 앵커가 아니다** — `bash tools/scripts/bl-audit.sh --list <판정어>` 의 4번째 칸이고,
「파일 배치」 축이 그 대응을 rc=1 로 집행한다.

---

### BL-804

**Title:** BE 이미지에 **태그도 레지스트리도 없다** — 의존성이 바뀐 커밋으로는 롤백할 수 없다
**Category:** Ops / 배포
**Priority:** P3
**Trigger:** ⏳ **대기 (트리거 미도래)** — `pyproject.toml`/`uv.lock` 경계를 넘는 롤백이 실제로 필요해지거나, BE 를 다중 호스트로 늘릴 때 도래한다
**Est:** M (빌드·태그·전송 경로 신설. FE 쪽 `QB_FRONTEND_TAG` 가 선례다)
**출처:** 2026-08-18 n5-ci-truth-close 레인 β — 롤백 절차를 적다 한계로 확정

**원인 / 영향:** BE 4서비스(`docker-compose.yml:93`·`:127`·`:157`·`:192`)는 `build:` 만 있고
`image:` 키가 **없다.** 이미지 이름이 compose 파생 `<프로젝트명>-<서비스>:latest` 뿐이라
git sha 태그도, 되돌아갈 이전 이미지도, 레지스트리도 없다.
`soak-stack.sh` 에 `docker pull/push/save/load` **0건**.

★**코드 롤백은 된다** — 소크 층이 `./.soak/src:/app/src:ro` 를 bind mount 하므로
(`docker-compose.soak.yml:35`) `down → pin <옛 sha> → up` 으로 앱 코드는 되돌아간다.
막히는 것은 **의존성**이다. 이미지에는 uv 의존성이 구워져 있고 그것을 되돌릴 경로가 없다.

⇒ 대비: FE 는 `image: quantbridge-frontend:${QB_FRONTEND_TAG}`(`docker-compose.frontend.yml:26`) +
`TAG=$(git rev-parse --short HEAD)`(`frontend-deploy.md:91`) 로 태그 전략이 **이미 있다.** BE 만 없다.

**권장 접근:** ⑴ FE 선례를 그대로 따라라 — `image:` + `QB_BACKEND_TAG` ⑵ 오라클 A1 은 aarch64 라
맥에서 빌드해 전송하는 FE 경로(`frontend-deploy.md:84-101`)가 그대로 쓰인다 ⑶ ★**하기 전에 세라** —
의존성이 바뀐 커밋으로 롤백해야 했던 적이 실제로 몇 번인가. 0 이면 이 항목은 계속 대기여도 된다.

**Risk:** 🟢 (지금 깨진 것은 없다. 필요해지는 순간 비용을 낸다)

**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-18 등재. 의존성 롤백이 실제로 필요해진 적이 아직 없다
**트리거 판정:** 미도래 — 외생 조건(의존성 경계를 넘는 롤백 요구)이 아직 발생하지 않았다 ([ADR-028], 2026-08-18 n5-ci-truth-close)
