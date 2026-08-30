# QuantBridge — Refactoring Backlog · DEFERRED 본문

> ★★★**2026-08-23 원장 다이어트 — 183건 → 23건.** 삭제 160건의 원문 = `git show 21e40d5c:docs/backlog-deferred.md`.
> 판정 기준은 **트리거의 형태**였다 — 「그 코드 만질 때 / 그게 필요해질 때 / 사용자가 요청하면」
> 형태는 **원장 항목이 아니라 코드에 붙어야 할 메모**다. 원장에서 골라질 일이 없고, 그 코드를
> 만질 때 발견된다. 여기에 2026-08-23 사용자 결정 3건(실자금 안 감 · Beta 안 염 · 멀티 거래소 안 함)이
> 걸리는 축을 더해 닫았다. 상세 표 = `backlog.md` 헤더의 「원장 다이어트 tombstone」.
> **남은 23건의 공통점** — 트리거가 **관측 가능한 사건**이거나(재발·측정치) 우리가 **실제로 갈 길**의 게이트다.

> ★★★**2026-08-25 [BL-829] 기각 tombstone — 증상 절이 실측으로 반증됐다.**
> 「SLL 2단계 예측 — ANTLR 콜드 파스 자체를 줄이는 유일한 축」을 **본문 삭제**했다 —
> 원문 = `git show 3ee036bb:docs/backlog-deferred.md`. 그 항목은 「콜드 파스의 **지배 성분**은
> full-context(LL) 재시도」를 전제했는데, preflight 실측이 그것을 깼다: `execATNWithFullContext`
> 는 `s5_ema_trend` **0회** · `s3_rsid` **29회**(`adaptivePredict` 3,672 중) · `i3_drfx` **204회**
> (27,652 중 **0.7%**)뿐이고, SLL 로 **전부 0 으로 만들어도** 49.91→48.06초(**3.7%**)다.
> 진짜 지배 성분은 `closure_` = `s3_rsid` cProfile cumtime **35.77/36.96초(96.8%)** — SLL 이
> 안 건드리는 ATN 클로저 계산 본체다. 대체 축 = **[BL-832] 프로세스 밖 AST 캐시**.
> ★되살리지 마라 — 되살리려면 「full-context 가 지배 성분이 되는 코퍼스」를 먼저 실측해라.


> ★★★**2026-08-21 — 이 파일이 언급하는 검사기 4종은 존재하지 않는다.** [ADR-037] 제로베이스가
> `bl-audit.sh` · `docs-audit.sh` · `bl-trigger-sweep.sh` · `final-gates.sh` 를 **2026-08-19 에
> 철거했다**(원문 = `git show harness-v1:tools/scripts/`). 아래 산문에 남은 그 이름들은 **당시의
> 이력**이지 지금 돌릴 명령이 아니다 — **치지 마라, 없다.**
> 지금 기계로 집행되는 것은 `tools/scripts/ledger-vitals.sh` **3축뿐**이다(다음 행동 ≤1 ·
> ⓪ 표 행 ≥3 · RESOLVED 역류 0). 나머지 규칙(원장 3분할 · `**상태:**` 줄 · 3면 일치 · 줄 길이
> 상한)은 **규칙으로 남았고 사람이 지킨다.** 판정어별 목록이 필요하면 `grep '^### BL-'` 과
> `grep '^\*\*상태:\*\*'` 로 직접 세라. 복귀는 **재입힘 규칙**(문서화된 사고 1건 = 슬림 복귀 1건) 경유다.

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

## P3 — Nice-to-have / 컨벤션 정합

### BL-849

**Title:** ★서버 디스크 회수가 **FE 배포에 얹혀 있다** — FE 를 안 올리면 build cache 상한이 사라진다
**Category:** 운영 / 디스크
**Priority:** P3 (현재 45% · 경보선 80%)
**Trigger:** `disk-guard` 가 80% 를 발화하거나, FE 무배포 4주 경과
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-30 실측 45%, 여유 54G
**출처:** 2026-08-30 docker 디스크 감사

**원인 / 영향:** 이번 회차가 회수를 `frontend-deploy.md` §3.3 에 **한 줄로** 붙였다(태그 3세대 유지 +
`builder prune --filter until=168h`). 그 한 줄은 **FE 를 배포할 때만 돈다.** BE 배포(`backend-deploy.md`
§3.3)는 `soak-stack.sh` 경로라 회수를 타지 않고, BE 이미지는 `image:` 태그가 없어 재빌드가 드물다
(실측: 3주 전 빌드본이 그대로). 따라서 FE 무배포 기간이 길어지면 build cache 만 자란다.

★**현재 회수 가능분의 주인은 우리가 아니다** — 2026-08-30 실측 12.2GB 중 quantbridge 몫은
**330MB(2.7%)** 이고 나머지 11.9GB 는 **kairos·truewords 의 죽은 롤백 태그**다
(`truewords-backend` 죽은 4벌 × 1.79GB ≈ 7.2GB · `kairos-api` 죽은 4벌 ≈ 3.7GB).
이 호스트는 `/dev/sda1` 97G 한 벌을 3개 프로젝트가 공유한다. **남의 프로젝트 이미지는 지우지 마라** —
그쪽 롤백 경로가 사라진다. 트리거가 오면 **그 프로젝트 소유자에게 알리는 것**이 첫 행동이다.

**권장 접근:** 트리거 도래 시 ⑴ `docker system df` 로 주인을 먼저 가르고 ⑵ quantbridge 몫만 회수한 뒤
⑶ 그래도 부족하면 타 프로젝트 소유자와 협의. 회수를 `disk-guard.sh` 에 **얹지 마라** — 그 스크립트의
설계 근거가 「경보와 회수의 분리」이고(`disk-guard.sh` 헤더), 경보가 회수 실패로 죽으면 둘 다 잃는다.


## 변경 이력

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
★**주의** — [BL-562] 는 **이 세션 이전부터 원장에 섹션이 없다**(RESOLVED 아카이브분). 이 트리거는 사람이 판단해야 발화한다
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

### BL-616

**Priority:** P3
**카테고리:** DX / 워크트리 부트스트랩 (훅 결손 감지)
**Trigger:** 워크트리에서 훅 미작동이 또 관측되면
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)** — 관측된 결함(워크트리 1개의 훅 결손)은 2026-08-07 에 정상화했다. **감지 수단 부재**만 열려 있다.
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
★★**2026-08-30 — 원인은 재발했다. 실패 모드는 달랐다(그래서 아직 미도래).** 원장 트리아주 회차가
`worktree-fix+check` 에서 커밋하려다 막혔다: `ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL Command "lint-staged" not found`
(`husky - pre-commit script failed (code 254)`). **`.husky/_` 는 있었고 훅은 돌았다** — 없던 것은
`node_modules` 뿐이라 훅의 첫 줄이 **시끄럽게** 죽었다. 이 항목이 지목하는 조용한 실패
(`core.hooksPath` 를 git 이 **경고 없이 무시**)와는 다른 모드다. ⇒ **트리거는 여전히 미도래**지만
**원인(부트스트랩 우회 생성)이 3주 뒤 그대로 재발한다는 증거**라 이 항목은 닫지 않는다.
수리 = `pnpm install`(952ms). 정본 진입은 `worktree-bootstrap.sh --adopt-env` 다.

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

### BL-740

→ **2026-08-30 트리거 도래로 `docs/backlog.md` 로 승격**(DEFERRED → ACTIVE). 옵티마이저가 `objective_metric="sharpe_ratio"` 로 Sharpe 를 **판단 입력**으로 쓰고 있었고, 이 항목이 원인 후보로 적어 둔 「NaN 만 보는 degenerate 판정 자체가 좁다」가 **정확히 맞았다**. 원문은 git 에 있다.

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

★★**2026-08-30 정정 — 이 항목의 census 를 「경계 밖 접근 0건」으로 읽으면 안 된다.**
`tests/common/test_repository_boundary_guard.py` 는 이름 그대로 **`select(` 호출만** 셌다.
그래서 `repo.session.get(...)` 리치스루(`trading/kill_switch.py`)와 `session.execute(text("INSERT …"))`
(`trading/funding.py`)는 **한 건도 안 세어졌고**, 그 0 이 「위반 없음」으로 읽혔다.
둘 다 2026-08-30 에 수리했고 **게이트를 3축으로 늘렸다**(경계 밖 `select(` · `repo.session` 리치스루 ·
경계 밖 raw SQL 실행). 잔여는 `tasks/` 의 `session.get(ExchangeAccount, …)` **8곳**이다 — 아래 표와 별개 축.

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

★★★**2026-08-30 재측정 — 9건이 아니라 2건이다.** 위 표는 낡았다. 전수 grep(`session.execute`·`db.execute`, repository 제외) 실측:

| 파일                                      | 2026-08-16 | **2026-08-30** |
| ----------------------------------------- | ---------- | -------------- |
| `src/trading/dependencies.py`             | 3          | **0**          |
| `src/trading/kill_switch.py`              | 2          | **0**          |
| `src/trading/websocket/reconciliation.py` | 1          | **0**          |
| `src/trading/websocket/state_handler.py`  | 1          | **0**          |
| `src/tasks/websocket_task.py`             | 1          | 1 (`:449`)     |
| `src/trading/funding.py`                  | 1          | 1 (`:32`)      |

★**누가 고쳤는지도 원장 밖이었다** — 2026-08-24 n8 회차가 「경계 밖 `select()` census **0건**(AST·`tasks/` 제외, 잔여는 `websocket_task.py` 1건)」을 산출로 적었는데(`status.md` 346행) **이 섹션은 따라오지 않았다.** 6파일 중 4파일이 그때 소멸했다.

⇒ **트리거의 전제가 바뀐다.** 「6파일을 손대는 회차에 동승」은 대상 파일이 4개 사라져 성립하지 않는다. 남은 2건은 **단독 착수가 M 이 아니라 S**(1h 내외)이고, 방향은 위 「repository 에 그 메소드를 만든다」 그대로다.

**Risk:** 🟢 (동작 정상 — 회귀 방어면이 좁을 뿐)

**상태:** ⏳ **대기 (트리거 미도래)** — ~~2026-08-16 에 코드 대조로 9건 확정~~ → **2026-08-30 재측정 = 2건 / 2파일.** 미착수
**트리거 판정:** 미도래 — ~~해당 6파일을 손대는 회차에 동승한다 (2026-08-16 deploy-activation)~~ → **2026-08-30** 잔여 2파일(`tasks/websocket_task.py` · `trading/funding.py`)을 손대는 회차에 동승. 단독 착수도 S 라 가능하다

---

### BL-765

**Title:** `src/tasks/live_signal.py` 가 4,606줄 — 레포 최대 단일 파일
**Category:** Backend / 구조 (tasks)
**Priority:** P3
**Trigger:** ★그 파일을 실질적으로 손대는 회차 (분할 자체를 목적으로 착수하지 마라)
**Est:** L
**출처:** 2026-08-15 surface-truth 아키텍처 감사 §B ([BL-759] 에서 분리) · 2026-08-16 실측 재확인

**원인 / 영향:** 2026-08-30 실측 **4,606줄 / 84 top-level def**(private 80 + `@shared_task` 4).
~~2026-08-16 실측 4,493줄~~ → **+113줄**. 같은 도메인의 repository 2종은 338·220줄이다.
★**「손대는 회차에 조금씩 뗀다」는 정책이 지금까지 순증을 냈다** — 트리거가 도래한 회차(n8·n9·n10)마다
줄이 늘었지 줄지 않았다. 다음 재측정 때 이 숫자가 또 올라가 있으면 정책 자체를 바꿔라.
이 파일은 소크의 심장이고([BL-003] 판정이 여기서 나온다) 회차마다 손이 간다 — 한 파일이
크다는 것 자체보다 **변경 충돌면이 넓다**는 것이 비용이다.

★**분할을 단독 목적으로 착수하지 마라.** 이 파일은 라이브 신호 tick 경로라 리팩터가
곧 소크 리스크다. 실측 회귀 방어면(`test_live_signal_tick_oracle.py` 의 부작용 원장)이
이미 있으므로, **그것이 덮는 범위 안에서** 손대는 회차에 조금씩 떼는 것이 옳다.

**Risk:** 🟠 (이 파일의 리팩터는 소크 창을 끊을 수 있다)

**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-16 에 줄 수만 확정. 미착수
**트리거 판정:** 미도래 — 그 파일을 손대는 회차에 동승한다 (2026-08-16 deploy-activation)

---

### BL-774

**Title:** TradingView webhook 이 **body 기반 HMAC** 을 요구한다 — 동적 alert 본문에서 성립하는지 미확인
**Category:** Backend / Trading ingress
**Priority:** P2
**Trigger:** ★**TradingView 유료 플랜을 다시 결제하기로 결정하면.** webhook alert 는 TradingView 유료 기능이고
**지금은 결제하지 않는다**(2026-08-30 사용자 — 예전에는 결제했다). 결제 없이는 실측 자체가 불가능하다
**Est:** M (실측 선행 · 결과에 따라 ingress 설계 분기)
**출처:** 2026-08-16 외부 레포 비교 분석(finsight) 지적 → 코드 축만 확정, **TradingView 쪽은 [확인 필요]**

**원인 / 영향:** `trading/webhook.py:116` 은 `hmac.new(secret, payload, sha256)` 으로 **요청 body
전체**에 대한 HMAC 을 계산해 query `token` 과 비교한다. FE 도 그대로 안내한다 —
`tab-webhook.tsx` 의 URL 템플릿이 `.../webhooks/{strategyId}?token={HMAC}` 이고 힌트 문구가
「`{HMAC}` 자리에는 secret 과 body 로 만든 HMAC-SHA256 토큰을 채웁니다」다.

**[확인 필요] — 아직 실측하지 않은 것:** TradingView alert 는 URL 과 message 를 **정적으로** 지정한다.
⑴ body 가 완전히 고정이면 HMAC 도 고정이므로 이 방식은 **동작한다**(외부 분석의 「불가능」은 과장이다)
⑵ 그러나 body 에 `{{close}}`·`{{time}}`·`{{strategy.order.action}}` 같은 placeholder 를 넣는 순간
본문이 매 alert 마다 달라지고 **고정 token 은 전부 401 이 된다.** 실제로 어느 쪽인지는
**사용자의 alert 본문 설계에 달려 있고 아직 실측이 없다.**

**함께 볼 것 — idempotency:** `trading/router.py` 의 idempotency key 는 **optional query
parameter** 다. 고정 키를 쓰면 다음 정상 alert 가 충돌로 거부되고, 생략하면 TradingView 의
재전송이 **중복 주문**이 된다. 즉 HMAC 축과 idempotency 축이 **같은 결정에 묶여 있다.**

**권장 접근:** ⑴ ★**먼저 실측해라** — 실제 TradingView alert 하나를 정적 body 로 걸어 200 이 나는지
확인한다. 코드를 고치기 전에 이 한 건이 설계를 가른다 ⑵ 동적 body 가 필요하다고 판정되면 세 갈래 중
선택: (a) 고정 endpoint token + body fingerprint (b) 서명 relay (c) 서버가
`strategy_version + symbol + side + bar_timestamp` 로 idempotency key 를 **자동 생성**
⑶ (c) 는 [BL-773] 의 `strategy_version` 에 의존한다 — 순서를 보라

**Risk:** 🟡 (ingress 계약 변경은 기존 연결을 끊을 수 있다. 지금 실사용 연결이 있는지부터 확인)

**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-30 재기술(종전 마커 `⬜ Open` 은 [ADR-028] 판정어 5종 밖이었다).
코드 축(body-HMAC + optional idempotency)은 2026-08-16 에 확정됐고 **TradingView 쪽 실측은 미착수**다.
**트리거 판정:** ~~도래 — 다만 첫 step 은 코드 수리가 아니라 **실측 1건**이다 (2026-08-16 external-comparison)~~
→ ★**2026-08-30 미도래로 재판정.** 「첫 step 은 실측 1건」은 여전히 맞지만 **그 실측을 할 수단이 없다** —
webhook alert 는 유료 플랜에서만 만들어지고 현재 결제하지 않는다. **결제가 선행**이다.

★★**[사용자 방향 · 미확정] 이 항목의 값을 정하는 것은 결제가 아니라 타겟이다.** 2026-08-30 사용자 =
「**결제를 하지 않는 대상**도 쓸 수 있게 타겟팅을 생각하고 있다」. 그 방향이 확정되면 webhook 은
**주 경로가 아니게 된다**(무료 TradingView 계정은 webhook alert 를 못 만든다) — 이 항목은 그때
「결제 사용자용 선택적 고급 경로」로 내려가고, 대신 **무료 사용자의 진입 경로**가 제품 축이 된다.
⇒ **그 방향 결정이 이 항목보다 앞선다.** 확정되면 `docs/PRD.md` 범위 절이 먼저 바뀐다

---

### BL-005

**Title:** Beta 외부 공개 게이트 — 사용자 결정 축
**Category:** 제품 / 운영 판단
**Priority:** P0
**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-23 재기술. 트리거는 **사용자 결정 하나**로 좁혀졌다
**Trigger:** ★**사용자가 「Beta 를 연다」고 결정하면.** 그 외 선행조건 없음
**Est:** L (사용자 수동)

★★★**2026-08-23 재기술 — 이 항목의 전제가 통째로 바뀌었다.**
종전 본문은 `**Title:** 본인 **실자본** 1~2주 dogfood` 였고 트리거가 `BL-001~004 완료 +
self-assessment ≥7/10 + 본인 의지` 였다. 그 사슬은 **`[BL-641] 소크 MTBF → [BL-003] mainnet
runbook → [BL-005] 실자본 dogfood → [BL-070~072] Beta`** 였다.

**같은 날 사용자 결정 3건이 그 사슬의 앞 두 칸을 없앴다:**

| 결정 | 이 항목에 미치는 영향 |
| --- | --- |
| ⑴ **실자금(mainnet) 안 간다** | **「실자본 dogfood」가 성립하지 않는다.** [BL-003](mainnet runbook)도 같은 날 삭제됐다 |
| ⑵ **Beta 외부 공개 당분간 안 연다** | 이 항목이 **바로 그 결정**이다. 트리거 = 그 결정의 반전 |
| ⑶ 멀티 거래소 안 한다 | 무관 |

⇒ **트리거의 객관 선행절(BL-001~004 · self-assessment)은 전부 걷어냈다.** 남은 것은
**사용자 결정 하나**다. 종전 본문이 근거로 든 좌표는 전부 사라졌거나 뒤집혔다 —
`roadmap.md:319`·`:354`(파일 삭제) · [BL-003](섹션 삭제) · [BL-070~072](원장 섹션이 처음부터 없다).
원문 = `git show 4c65bc0e:docs/backlog-deferred.md`.

**열 때 실제로 필요한 것 (코드 기준, 2026-08-23 실측):**

1. 서버 `.env.local` 에 키 3종 — `RESEND_API_KEY` · `RESEND_FROM_ADDRESS` · `WAITLIST_ADMIN_EMAILS`.
   절차·판정·롤백 전문 = [`operations/waitlist-activation.md`](./operations/waitlist-activation.md)
2. Cloudflare Access 정책에 초대 대상 이메일 추가 — ★**env 로는 못 여는 관문**이다(런북 §4.0)
3. Access 를 **걷지는 마라** — 걷으면 가입이 개방된다(2026-08-19 결정으로 초대 게이트는 짓지 않는다)

★**코드·테스트·화면은 이미 완비다**(2026-08-16 [BL-072]). 막고 있는 것은 기술이 아니라 결정이다.

★**이 BL 은 세션이 열 수 없다** — Resend 키 발급과 Access 정책 편집이 둘 다 사용자 소유 콘솔이다.

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

### BL-800

**Title:** 화면 증거 게이트의 CI 게시 경로 — 리눅스 baseline 과 PR 코멘트 자동화
**Category:** 테스트 / 인프라 / CI
**Priority:** P3
**Trigger:** ⏳ **대기** — 화면 증거 측정 축(구 [BL-797])이 서고 나서. 라우트 집합이 확정돼야 baseline 을 굽는 값이 있다.
★**2026-08-23 — [BL-797] 섹션은 원장 다이어트에서 삭제됐다**(트리거가 「사용자 수요 등장 시」 형태였다).
그 축을 다시 세우려면 `git show 21e40d5c:docs/backlog-deferred.md` 에서 되살려라 — 이 항목 단독으로는 판단 불가다
**Est:** M
**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-17 night3 에 로컬 경로까지만 착지했다. baseline 스냅샷이 `-darwin` 접미뿐이고 리눅스 판이 없어 `e2e-project-wiring.test.ts` 의 `LOCAL_ONLY["chromium-screen-evidence"]` 로 CI 에서 제외돼 있다. 표는 사람이 `gh pr comment --body-file` 로 올린다.
**트리거 판정:** 미도래 — **선행 조건**([BL-797]). 라우트 집합이 바뀌면 구운 baseline 을 다시 구워야 한다 (2026-08-17 night3 CONTROL)
**출처:** 2026-08-17 night3 레인 α (레인 파일 갈래 ⑵ 미착수)

**원인 / 영향:** 지금은 게이트가 로컬에서만 돌고 리포트도 사람이 붙인다. CI 가 돌리면 「화면을 바꾼 PR 이 증거 없이 지나갈 수」 없게 되지만, 그러려면 리눅스에서 픽셀이 결정적이어야 한다.

**권장 접근:** 리눅스 baseline 을 굽고 워크플로에 프로덕션 서버 스텝을 넣은 뒤 `actions/github-script` 로 코멘트 게시. 선례 `nightly-real-broker.yml:207`. 그때 `LOCAL_ONLY` 항목을 걷는다.

**Risk:** 🟡 빌드가 `next/font/google` 로 네트워크에 매달려 있다 — 레인 α 실측에서 13회 중 1회가 폰트 CSS 를 못 받아 죽었다. **오프라인이면 이 게이트는 못 돈다.**


### BL-826

**Title:** BE 가 cancelled/rejected 주문의 **종결 시각**을 `filled_at` 에 쓴다 — 기록 의미론 오염 ([BL-824] 의 정본 수리 축)
**Category:** Backend / Trading order repository (+ DB 스키마)
**Priority:** P3
**출처:** [BL-824] 잔여 축 (2026-08-25 qa-sweep J7 — FE 라벨 최소 수리로 종결, 원문 = git)

**증상 (실측, 2026-08-25):** cancelled **431/431** · rejected **88/88** 이 `filled_at` 을 보유하나 부분 체결 0건 — 값의 실체는 체결이 아니라 **종결 전이 시각**이다. rejected 축은 `order_repository.py:941-945` 가 주석으로 문서화까지 해 뒀다.
**영향:** 컬럼 이름이 값의 의미와 어긋나 소비자마다 라벨 분기를 반복해야 한다 — FE 드로어가 두 번(2026-08-15 rejected · 2026-08-25 cancelled) 같은 병을 앓았고, CSV/API 를 직접 읽는 쪽은 여전히 「체결 시각」으로 오독한다.
**권장 접근:** cancelled/rejected 의 종결 시각을 `filled_at` 이 아닌 별도 컬럼(예: `closed_at`)에 쓰거나 `filled_at` 은 null 유지. migration + 기존 519건 backfill + FE 라벨 분기 단순화(`order-detail-drawer.tsx` BL-824 주석 참조)가 한 묶음이다.

**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-25 등재. FE 표기는 [BL-824] 수리로 이미 옳다
**트리거:** orders 스키마 또는 주문 serializer 를 손대는 회차에 동승 — 단독 착수 가치가 낮다

### BL-828

**Title:** `worker_max_tasks_per_child=250` 완화 — 콜드 파스 창의 **빈도**를 낮추는 1줄 축
**Category:** Backend / Celery worker 운영
**출처:** 2026-08-25 n13 preflight (파스 콜드 비용 실측)
**Priority:** P2

**증상 (실측·[가정] 혼재, 2026-08-25):** prefork child 는 250 task 마다 교체되고(`apps/api/src/tasks/celery_app.py:98`, CLI 오버라이드 0건) 교체된 child 는 **빈 ANTLR DFA** 로 시작한다 — `worker_process_init`(`:208-238`)이 파싱을 하지 않으므로 fork 시점 상속도 없다. beat_schedule 16건이 전부 라우팅 없이 기본 큐로 가서(`:109-205`) **≈195회/시**, concurrency=2 이므로 **[가정]** child 당 ≈97.5회/시 ⇒ **≈1.3시간마다 콜드 child 1개 · 하루 ≈19회**. 콜드 창 1회의 크기는 실측 `s5_ema_trend` 2.61s · `s3_rsid` 11.55s · `i3_drfx` **52.37s**(격리·median-of-3).
**영향:** 사용자가 아무것도 안 해도 하루 ≈19번, 누군가의 첫 백테스트가 최대 52초를 문다.
**권장 접근:** 250 → 1000. 코드 주석이 이미 이 완화를 예고했다 — `celery_app.py:90-91`「1h soak gate(RSS slope + asyncpg/Redis fd count) 미수행 상태이므로 conservative. Sprint 19 의 soak 결과로 1000 으로 완화 검토」. 위험 = 메모리 누수 시 컨테이너 OOM(`infra/compose/docker-compose.soak.yml:33` `mem_limit: 2g`, idle 692MiB) → 콜드 창 2개 동시.
★**하네스 lane 이 될 수 없다** — 판정 수단이 소크(RSS slope)뿐이라 AC 로 세울 수 없다.

**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-25 **사용자 결정으로 이번 회차 제외**
**트리거:** 소크 창이 열리는 회차에 동승. 착수 첫 작업 = child 교체 **실빈도** 측정(`docker logs` 의 child exit 간격 — CPU 0). 위 하루 ≈19회는 산술이지 실측이 아니다

### BL-830

**Title:** `execution_speed_baseline.json` 이 **코드 속도가 아니라 실행 순서**를 재고 있다
**Category:** Backend / 테스트 픽스처 · 측정 구조
**출처:** 2026-08-25 n13 preflight (n12 산출물 재검증)
**Priority:** P2

**증상 (확인된 사실, 2026-08-25):** `tests/strategy/pine_v2/test_execution_speed.py:56` 이 **단일 프로세스**에서 `RUNNABLE_CORPUS` 를 순서대로 돌고 `bars_per_second` 를 **콜드 호출**로만 계산한다(`:70`). ANTLR DFA 는 파서 **클래스 속성**이라 프로세스 전역이므로(`PinescriptParser.py:346,348,606`) 첫 corpus 만 온전한 콜드 비용을 물고 나머지는 앞 corpus 가 데운 DFA 를 물려받는다. 그 결과 **20줄 `s1_pbr` 의 `ratio_to_fastest` 8.43 이 42줄 `s4_hma_curvature` 의 2.19 보다 4배 나쁘다.** 같은 `s3_rsid` 가 breakdown(자기 프로세스 1번째) 21.752s vs speed(3번째) 14.471s — **50% 차이가 순서 하나에서 난다.**
**영향:** `ratio_to_fastest` 로 코드 회귀를 판정하는 가드(`:154`)의 입력이 오염돼 있다. 그리고 n12 가 「s1_pbr 이 2.6배 흔들린다 ⇒ median-of-3 필요」로 귀속한 원인이 틀렸다 — **프로세스를 격리하면 9벌 전부 스프레드 1.013~1.065×** 다(격리 실측). 흔들림은 콜드 파스의 본질적 분산이 아니라 **측정 방식**에서 왔다.
**권장 접근:** corpus 당 **새 프로세스**로 재고(`subprocess` 또는 `pytest-forked`), median-of-3 를 채택한다. 격리 실측의 진짜 콜드 = `s1_pbr` 5.35 · `s2_utbot` 11.45 · `s3_rsid` 11.55 · `s4_hma` 4.06 · `s5_ema` 2.61 · `i1_utbot` 10.86 · `i2_luxalgo` 9.21 · `i3_drfx` 52.37 · `i4_bs` 16.95 (초).
★함께 볼 것 — `execution_stage_breakdown.json` 의 `parse` 는 **그 실행의 총 파싱 시간이 아니다**(계측 래퍼가 `classify_script` 하나만 감싼다 — `test_execution_stage_breakdown.py:49-53`). 그리고 이 파일에는 **재생성 경로가 레포에 없다**(REGEN env·writer 함수 0건).

**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-25 등재. n13 은 이 구조를 **의도적으로 안 바꾼다**(측정 구조를 같이 바꾸면 회차의 전/후 비교가 무엇 때문에 움직였는지 갈리지 않는다)
**트리거:** 속도를 **목표선으로 삼는** 회차가 열릴 때. 그전까지 이 픽스처는 회귀 신호로만 쓰고 절대값으로 인용하지 마라

### BL-831

**Title:** `POST /api/v1/strategies/parse` 에 rate limit 도 소스 길이 상한도 없다
**Category:** Backend / Strategy router
**출처:** 2026-08-25 n13 preflight
**Priority:** P3

**증상 (확인된 사실, 2026-08-25):** `apps/api/src/strategy/router.py:38-44` 의 파스 엔드포인트는 인증은 요구하지만(`get_current_user`) **rate limit 이 없다** — 바로 아래 `:48` 의 `create_strategy` 가 `@limiter.limit("30/minute")` 를 건 것이 대조군이다. `pine_source` 에 **길이 상한도 없다**(`schemas.py` `Field(min_length=1)`).
**영향:** 파스는 CPU 를 실제로 잡는 연산이다 — 격리 실측상 39KB 소스(`i3_drfx`)의 콜드 파스가 **52.37초**다. 인증된 사용자 하나가 큰 소스를 반복 던지면 CPU 를 점유한다. ★n13 Lane 2 가 스레드풀 이관으로 **이벤트 루프 블로킹**은 없앴지만 **CPU 점유 자체**는 남는다. 또한 n13 Lane 1 이 `parse_to_ast` 에 `lru_cache(maxsize=N)` 를 걸었으므로 **임의 입력으로 채워지는 캐시 표면**이 생겼다(그래서 `maxsize=None` 을 금지했다).
**권장 접근:** `create_strategy` 와 같은 `@limiter.limit(...)` + `pine_source` 에 `max_length`. 상한 값은 실사용 전략 크기 분포를 보고 정한다(레포 corpus 최대 = `i3_drfx` 38,954B).

**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-25 등재. n13 은 범위 밖으로 명시 제외(회차 범위 = 블로킹 하나)
**트리거:** strategy router 의 인증·제한 축을 손대는 회차, 또는 외부 공개(Beta) 판단이 열릴 때

★★**2026-08-30 — 이 엔드포인트의 표면이 넓어졌다(트리거는 아직 미도래).** [BL-833] 수리(PR #848)로
**옵티마이저 화면이 이 엔드포인트를 자동으로 친다** — `useStrategyInputs` 가
`GET /strategies/{id}` → `POST /strategies/parse` 를 호출해 `var_name` 드롭다운을 채운다.
종전에는 사용자가 위저드에서 **명시적으로** 파스를 눌러야 닿는 경로였다.
★**완화 요인 둘** — ⑴ `usePreviewParse` 가 `staleTime: Infinity` + 소스 문자열 키라 같은 전략 재방문은 요청 0회 ·
⑵ L2 디스크 캐시([BL-832] · PR #837)로 콜드는 **소스당 1회**(재방문 4.8ms)다. 위 「52.37초」는 캐시 이전 수치다.
⇒ **판정 불변(미도래)이지만 트리거 앞절이 가까워졌다** — strategy router 를 다음에 열 때 같이 닫아라.
