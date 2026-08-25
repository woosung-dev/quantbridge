# QuantBridge — Refactoring Backlog

> **Active 백로그.** 명백한 Resolved + stale 항목은 `_archived.md`, trigger 미도래 의도적 부활 가능 항목은 `_deferred.md`. 문서 경로 정합성은 `tools/scripts/docs-audit.sh`로 검증한다.
> ★**tombstone (ADR-026 §5).** 본문이 가리키는 `_archived.md`(Resolved + stale 137건)·`_deferred.md`(부활 가능 8건)는
> 2026-08-06 문서 대개편에서 삭제됐다 — 원문 = `git show 0f0f0b06:docs/archive/refactoring-backlog/_archived.md`
> (`_deferred.md` 동일 경로). `_deferred.md` 내용은 본 문서 말미 「Deferred」 섹션으로 승격돼 있다.
> 그 뒤 강등분(2026-08-06 entry-set-divergence)의 본문 = `git show 23a9fcd4:docs/backlog.md`.
> ★**2026-08-13 docs-diet.** RESOLVED **78건**의 본문을 접었다 — 각 섹션에 `### BL-nnn` 헤더 +
> `**Priority:**`(또는 `**우선순위:**`) + `**상태:**` + **원래 있던 경우에 한해** `**Title:**` 을 남기고
> 나머지는 `📦 본문 접힘` 1줄로 대체했다. 접힌 78건의 원문 전량 = `git show 8abd0d67:docs/backlog.md`.
> ★**수치는 여기 박지 않는다** — 이 헤더 자신이 파일 크기를 바꾸므로 박는 순간 stale 이다. `wc -m` 으로 재라.
>
> ---
>
> ★★★**2026-08-23 원장 다이어트 tombstone — 삭제된 것과 그 좌표.**
> **복원 좌표 = `git show 21e40d5c:docs/backlog.md`** (`backlog-deferred.md`·`backlog-resolved.md` 동일 SHA).
>
> | 무엇 | 몇 건 | 왜 |
> | --- | --- | --- |
> | `backlog-resolved.md` **파일 전체** | 159 | 끝난 것의 기록. git 이 이미 원문을 갖는다 |
> | DEFERRED 섹션 | 160 | **트리거가 「그 코드 만질 때 / 그게 필요해질 때」인 조건부 메모**. 원장에서 골라질 일이 없다 |
> | ACTIVE 섹션 | 10 | 사용자 결정 3건(아래)이 닫았다 — **BL-003 · BL-014 · BL-186 · BL-458 · BL-492 · BL-591 · BL-638 · BL-648 · BL-667 · BL-736** |
> | `status.md` ⓪ 표 취소선 행 | 43 | 끝난 일의 취소선이 매 세션 22k 토큰을 먹고 있었다 |
>
> **판정 근거 = 2026-08-23 사용자 결정 3건:**
> ⑴ **실자금(mainnet) 안 간다** — Bybit demo 만. money-path 「실자금 정밀도」 축을 닫는다
> ⑵ **Beta 외부 공개 당분간 안 연다** — 「사용자 수요 등장 시」 전제 항목을 닫는다
> ⑶ **멀티 거래소 안 한다** — Bybit 하나. OKX·Binance 전제 항목을 닫는다
> 셋 중 하나라도 뒤집히면 위 SHA 에서 해당 축을 되살려라 — **다시 쓰지 말고 되살려라.**
>
> ⚠️★**BL-nnn 인용이 섹션을 못 찾는 것은 정상이다.** 이 다이어트로 **269종**이 새로 끊겼고,
> 그 전에도 **156종**이 이미 끊겨 있었다(2026-08-23 실측 — RESOLVED 아카이브·roadmap 전용 항목).
> 인용 1,507회를 고치는 대신 이 tombstone 하나로 닫는다. 끊긴 인용을 보면 위 SHA 를 열어라.
>
> ★★**어느 줄이 게이트에 집행되는지 실측했다 (변이 5종).** 「넉 줄 다 필수」는 **거짓**이다:
>
> | 지운 것            | `bl-audit` | 비고                                                  |
> | ------------------ | ---------- | ----------------------------------------------------- |
> | `### BL-nnn` 헤더  | **red**    | 「표 행만 있고 섹션이 없다」                          |
> | `**상태:**` 줄     | **red**    | 「표 행에 ✅ 인데 섹션은 ACTIVE」                     |
> | `**Priority:**` 줄 | **red**    | 「Pn 표에 실렸는데 섹션에서 우선순위를 못 읽었다」    |
> | `**Title:**` 줄    | green      | ★**집행되지 않는다** — 78건 중 **33건은 애초에 없다** |
> | `📦 본문 접힘` 줄  | green      | ★**집행되지 않는다** — 사람을 위한 표기다             |
>
> ⇒ 접기를 다시 할 때 **앞 셋은 반드시 남겨라.** 뒤 둘은 사라져도 게이트가 안 운다 — 사람이 지켜야 한다.
>
> ★★★**2026-08-21 — 이 파일이 언급하는 검사기 4종은 존재하지 않는다.** [ADR-037] 제로베이스가
> `bl-audit.sh` · `docs-audit.sh` · `bl-trigger-sweep.sh` · `final-gates.sh` 를 **2026-08-19 에
> 철거했다**(원문 = `git show harness-v1:tools/scripts/`). 아래 산문에 남은 그 이름들은 **당시의
> 이력**이지 지금 돌릴 명령이 아니다 — **치지 마라, 없다.**
> 지금 기계로 집행되는 것은 `tools/scripts/ledger-vitals.sh` **3축뿐**이다(다음 행동 ≤1 ·
> ⓪ 표 행 ≥3 · RESOLVED 역류 0). 나머지 규칙(원장 3분할 · `**상태:**` 줄 · 3면 일치 · 줄 길이
> 상한)은 **규칙으로 남았고 사람이 지킨다.** 판정어별 목록이 필요하면 `grep '^### BL-'` 과
> `grep '^\*\*상태:\*\*'` 로 직접 세라. 복귀는 **재입힘 규칙**(문서화된 사고 1건 = 슬림 복귀 1건) 경유다.

> ★★★**2026-08-18 수명 분리 완료 ([BL-779]).** 원장은 이제 **파일 둘**이고 **축은 판정어**다 —
> 본 파일 = **ACTIVE ∪ PARTIAL** + **인덱스 표 전량** ·
> [`backlog-deferred.md`](./backlog-deferred.md) = **DEFERRED**.
> ~~`backlog-resolved.md` = **RESOLVED**~~ → **2026-08-23 파일째 삭제** — RESOLVED 는 파일이 아니라
> **지운다**(`AGENTS.md` §6). 복원 좌표는 이 헤더 위 「원장 다이어트 tombstone」이 갖는다.
> ★**규칙을 산문으로 두지 않았다** — `bl-audit.sh` 의 「파일 배치」 축이 rc=1 로 집행한다.
> 2026-08-16 의 1차 분할이 산문이라 그 뒤 닫힌 **13건이 전부 이 파일에 다시 쌓여 있었다**.
> ★**표 행의 `#bl-nnn` 앵커는 다른 파일을 안 가리킨다**(접두사 시도 → +18자/행이 줄 길이
> 상한을 넘겨 되돌렸다, [BL-801]). 섹션이 어디 있는지는 `bl-audit.sh --list <판정어>` 의 **4번째 칸**이 답한다.
> ~~원장은 이제 **파일 둘**이다 — 본 파일(열린 것) + `backlog-resolved.md`(RESOLVED 118건 본문).~~
> `bl-audit.sh`·`docs-audit.sh`·`bl-trigger-sweep.sh`·`context-budget.sh` 가 **셋을 한 벌로** 읽고,
> 섹션 수·판정 수는 **합계**다(`bl-audit` 머리줄이 파일별 수를 함께 찍는다).
> ★**인덱스 표 행은 여기 남아 있다** — 아래 `## Pn` 표에서 ✅ 가 붙은 행의 **본문은 저 파일에 있고**
> 행의 `#bl-nnn` 앵커는 같은 파일 안을 가리키지 않는다. 본문은 `backlog-resolved.md` 에서 찾아라.
> ★**항목이 RESOLVED 가 되면 본문을 옮기고 표 행은 남긴다.** 양쪽에 두면(=복사) `bl-audit` 이
> 「중복 섹션 헤더」로 red 를 낸다. 한쪽 파일이 비면 초록이 아니라 **rc=3 ABORT** 다.
>
> **신규 sprint 진입 시 본 문서 review 의무** — 각 BL 의 trigger 가 도래했는지 확인 후 active TODO 로 승격할지 결정. `_deferred.md` 도 6-8주마다 재평가.

**작성일:** 2026-04-30
**최종 갱신:** 2026-07-26 (**dogfood-restore 스프린트** — 로컬 실사용 복원 + 3스프린트 누적 신뢰 작업 실화면 검증. **BL-465/467 Resolved** +
신규 **BL-466/468~472/474** + **BL-473 Resolved**(WS auth `expires` 창 — 라이브 체결 스트리밍이 통째로 죽어 있었다). ★**dogfood 가
P1 을 잡았다** — `_periodic_returns` 가 음수 자본을 안 걸러 파산한 실행에 **양수 샤프**가 붙었고(실측 -2179.68% 에 +0.029), **committed
Trust Layer baseline 이 그걸 담고 있었다**(s1_pbr 샤프 +0.600 · 소르티노 +2.349 on -536%). 코퍼스 5종 중 4종이 음수 자본이고 골든이 깨진 것도
정확히 그 4종. baseline 재생성 diff = 12 메트릭 키 중 2개 한정. ★**옵티마이저는 이 스택에서 구조적으로 죽어 있었다** — `optimizer_heavy` 유일 소비자에
OHLCV env 3종 부재. ★**`mise run seed` 신설** — 백테스트 1회가 곧 OHLCV 시딩(TimescaleProvider cache-first). 마이그레이션 0.) // 이전:
2026-07-26 (**money-path-finish 스프린트** — BL-457/454 Resolved + BL-458 부분 Resolved + **신규 BL-464**. 머니-패스 정확도
마감 팩. ★**실측이 BL-457 의 '권장 접근' 을 반박** — `attribution_facts` 재사용은 진짜 우리 청산을 external 로 뒤집는다(백로그 본문에서 제자리 정정).
★**백로그에 없던 결함 발견(BL-464)** — `attribute_exit` 이 거래소 원문↔canonical 심볼을 비교해 `inferred` 귀속이 구조적으로 죽어 있었고, **픽스처
기본값이 그걸 한 스프린트 동안 가렸다**. ★`format:check` 는 이 레포의 통과 가능 게이트가 아님을 실측 확인(선재 356 red). 마이그레이션 0.) // 이전:
2026-07-25 (**exit-money-path 스프린트** — BL-444/445 Resolved + BL-453 부분 Resolved + 신규 BL-454~458. 세션 스코프 머니-패스
정정(Site 3·4). ★§0.5 실측이 BL-438 ② 를 "미룸" 이 아니라 **"현재 데이터로는 정직하게 구현 불가"** 로 재분류 — bracket/trailing 0행 ·
matched/attributed 0행. ★대조군 판별력을 프로덕션 stash 로 실제 증명. ★active BL 카운트 산식을 헤더에 박아 stale 재발 차단.) // 이전: 2026-07-25
(**exit-attribution 스프린트 + 범위 축소 + dogfood 완주** — BL-438 부분 Resolved(관측 원장, **최근 7일**) + BL-442 Resolved + 신규
BL-443~453. 거래소 청산 원장 신설 + 스윕 계정 독립 열거. ★과거 90일 catch-up 기계장치는 머지 전 축소로 걷어냄 → BL-452. ★로컬 개발 DB 전소 사고 → BL-451
가드. ★dogfood 실측이 알림 크래시 진짜 P1 을 적발·수정 → BL-453 예방 등재.) // 이전: 2026-07-25 (**close-completeness 스프린트** —
BL-435/436 Resolved + BL-434 부분 Resolved(display) + 신규 BL-437(스윕 이연). 청산 즉시 flat + margin 503 회피 + 완전 TP/SL
보고.) // 이전: trading-surface-pack — BL-431/416/425/432/433 Resolved + BL-434~436.
**직전 갱신:** 2026-07-24 (**trading-surface-pack 스프린트** — BL-431/416/425/432/433 Resolved + 신규 BL-434~436. 코크핏 §03 TP/SL 열 + reduce-only 시장가 청산 완성.)
**현재 상태:** **집계 수치를 여기 박지 않는다** — 정본은 `bash tools/scripts/bl-audit.sh` 이고, 그 스크립트는 `tools/scripts/final-gates.sh` 게이트 체인 안에 있다(라벨 `BL 감사`, BL-564). 숫자가 필요하면 **그 자리에서 재라.** 문서에 박은 수치는 BL 하나만 추가돼도 즉시 stale 이고, 이 줄은 실제로 여러 스프린트 동안 stale 이었다. **BL-070~075 milestone active 승격** (deferred → P0 prep).

> ★이 수치는 손으로 세지 말고 기계적으로 재라 — 직전까지 "49 active" 로 여러 스프린트 동안 stale 했고, 그 다음 표기 "86 active / 전체 135" 도 실측(217 섹션)과 어긋나 있었다. **산식은 이제 문서 주석이 아니라 스크립트다:**
>
> ★**아래 명령은 2026-08-19 [ADR-037] 로 철거됐다 — 치지 마라.** 대체를 함께 적는다.
>
> ★★**판정어는 낱말이 아니라 마커다** — 상태줄은 `⏳ 대기 (트리거 미도래)` · `✅ Resolved` ·
> `🔵 ACTIVE` · `🟡 부분 Resolved` 로 쓴다. **`grep -oE 'ACTIVE|DEFERRED|…'` 로 세면 9건만
> 잡히고 나머지 351건을 놓친다**(2026-08-21 실측 — 내가 먼저 밟았다). 마커로 세라.
>
> ```bash
> # ✗ 없다: bl-audit.sh · bl-trigger-sweep.sh · docs-audit.sh · final-gates.sh
> #        (원문 = git show harness-v1:tools/scripts/)
> # ✓ 섹션 수 — 원장 3종을 한 벌로
> grep -ch '^### BL-' docs/backlog.md docs/backlog-deferred.md docs/backlog-resolved.md | paste -sd+ - | bc
> # ✓ 판정어 집계 — 마커 기준 (셸 로케일이 이모지를 흘리므로 python 으로 센다)
> python3 -c "
> import re,pathlib,collections
> M={'⏳':'DEFERRED','✅':'RESOLVED','🔵':'ACTIVE','🟡':'PARTIAL','❓':'UNKNOWN'}
> c=collections.Counter()
> for f in ['docs/backlog.md','docs/backlog-deferred.md','docs/backlog-resolved.md']:
>     for s in re.split(r'^### (?=BL-)', pathlib.Path(f).read_text(), flags=re.M)[1:]:
>         m=re.search(r'^\*\*상태:\*\*(.*)\$', s.split(chr(10)+'### ')[0], re.M)
>         c[next((v for k,v in M.items() if m and k in m.group(1)), 'NONE')]+=1
> print(c)"
> ```
>
> **2026-08-21 실측** — 섹션 **361** · `🔵 ACTIVE` **1** · `🟡 PARTIAL` **21** ·
> `⏳ DEFERRED` **182** · `✅ RESOLVED` **151** · **판정어 결손 6건**
> (상태줄 자체가 없는 것 = `BL-003`·`BL-724` · 마커가 비표준인 것 = `BL-547`·`BL-591`·`BL-774`·`BL-811`
> 이 넷은 `⬜ Open`·`🟢 Open` 을 쓴다 — **[ADR-028] 판정어 5종에 없는 어휘다**).
> ★이 수치는 커밋마다 낡는다 — **손으로 세지 말고 위 명령을 다시 돌려라.**
>
> ★**2026-08-10 부터 판정어가 다섯이다** — `ACTIVE / DEFERRED / PARTIAL / RESOLVED / UNKNOWN`([ADR-028](./adr/028-backlog-deferred-verdict.md)). `DEFERRED`(상태줄 `⏳ **대기 (트리거 미도래)**`)는 🟡 와 마찬가지로 **active 로 세지 않는다.** 종전에는 「조건이 아직 안 왔다」를 적을 낱말이 없어 열린 항목이 **전부 ACTIVE** 로 떨어졌고, 그래서 ACTIVE 159 는 작업량이 아니라 **셈하는 규칙이 만든 수**였다(전량 판정 후 **9**). 미도래의 경계는 **외생 조건**(사용자 승인·cutover·Beta·소크·외부 관측·미해결 선행 BL)**과 동승 조건**(「그 파일을 다음에 열 때」류 — 단독 착수 시 값이 0이라고 트리거 자신이 선언한 것) **둘 다**를 포함한다. 3면에서 DEFERRED 는 **ACTIVE 와 같은 「미완」 쪽**이다. 각 섹션의 `**트리거 판정:**` 줄이 **무엇이 막는지**를 적는다.
>
> ★**낡은 산식(인라인 awk)은 폐기했다.** 그것은 "섹션 본문 어딘가에 `Resolved` 문자열이 있으면 RESOLVED" 였고, 그래서 **cross-ref 한 줄이 항목을 지웠다** — `BL-003`(P0, 열려 있음)이 자기 섹션의 `BL-004 ✅ Resolved` 두 줄 때문에 RESOLVED 로 집계돼 **공식 산식이 P0 active 를 0 으로 보고하고 있었다**(BL-499·BL-535 도 같은 뿌리). 새 산식의 SSOT 는 각 섹션의 `**상태:**` / `**Status:**` **줄 하나**이고, 근거가 없으면 추측하지 않고 **UNKNOWN 으로 남긴다**. 🟡 부분 Resolved 는 종전대로 active 로 세지 않는다.

**최근 sprint BL 변경 (Sprint 55~Sprint 62 Beta 진입):**

- **2026-07-25 close-completeness 스프린트 (codex G0 REJECT→개정 + 2-generator ∥ + Claude 적대평가 per-worker + codex 최종
  diff + Opus dogfood 3계통)**: trading-surface-pack(#473) 후속. 청산/TP-SL 완성도 3건. **BL-435 Resolved**(즉시 flat =
  post-fill Celery 캐시 DEL, accept-time DEL 은 async close 라 무효) + **BL-436 Resolved**(청산 create_order 가
  reduce_only 시 set_margin_mode/set_leverage skip = margin 503 회피, ccxt marginMode 신뢰불가 우회) + **BL-434 부분
  Resolved**(완전 TP/SL 보고 display = fetch_open_conditional_orders 2콜 union+orderId dedupe+stopOrderType 엄격분류 →
  §03 병합 리스트 + has_trailing_stop 각주; **스윕은 BL-437 이연**) + hedge positionIdx 409 가드. 마이그레이션 0. 게이트: BE
  **2611**(+10) / FE **1084**(+1) / canon **32 불변** / ruff·mypy·tsc·lint 0 / alembic 무변경. **검증 체인**: codex G0
  = **REJECT**(전건 코드 대조 §7.3 후 개정 — B2 skip 전환·B1 post-fill DEL·B3 union dedupe·trail=position 필드·hedge 가드) →
  사용자 재인터뷰(스윕 이연·트레일링 각주) → codex 2워커 생성 ↔ Claude 적대평가(W1 ruff B023×3+mypy → codex resume hoist) → codex 최종
  diff([P1] has_trailing_stop 조건부 trail 해소+테스트) → **dogfood 3계통**(독립 오라클 raw ↔ 앱 provider
  fetch_open_conditional_orders(66000/62000 정확 분류·count=2 dedupe) ↔ get_reconciliation 병합 + **authed
  브라우저**(§03 병합·청산 flat·콘솔 0) + B1 redis 키 부재 + B2 no-503 + Bybit Partial 자동취소 실증). **★docker 포트 오버레이
  함정**(plain `docker compose up <svc>` 이 db/redis 를 base 5432/6379 로 되돌림 → `--no-deps` 필수). 신규 **BL-437**.
- **2026-07-24 trading-surface-pack 스프린트 (codex 2-generator ∥ + Claude 적대평가 per-worker + Opus dogfood)**:
  position-cockpit(#472) 후속. 코크핏 §03 포지션 표에 TP/SL 열 + reduce-only 시장가 청산 완성 + 부채 4종. **BL-431 Resolved**(BE:
  포지션-보고 TP/SL read-time 0→null 정규화 + `POST /live-sessions/{id}/positions/close` reduce-only 청산 = 신규
  `close_service.py` + `OrderService.execute(flatten=True)` 진입-위험 가드 ②~⑧ bypass·ownership 유지·reduce_only
  불변식·**청산 leverage=포지션값**으로 set_leverage no-op·cap-bypass 방지 / FE: 익절·손절 2열 + 청산 액션·확인 모달(정직 고지)·colSpan 14) +
  **BL-416 Resolved**(주문취소 행별 disabled `cancelOrder.variables` + 비-409 broad toast + 실 ACTIVE_ORDER_STATES
  import) + **BL-425 Resolved**(alert-rule 중복 유형 사전검사 = 마운트 목록 재사용, 409 요청·콘솔 노이즈 회피) + **BL-432
  Resolved**(positions select→combine 인덱스 zip + 고아 삭제) + **BL-433
  Resolved**(`qb_ws_subscribe_rejected_total{account_id}` counter). 마이그레이션 0. 게이트: BE **2601**(+18) / FE
  **1083**(+8) / canon **32** / authed **66**(+2 코크핏 §03 구조) / build ✓ / alembic 무변경. **검증 체인**: codex G0
  14건(코드 대조 후 반영, BLOCKING 3=leverage 라우팅·flatten 불변식·hedge 거부) → codex 2워커 병렬(apps/api/frontend 교집합 0) ↔
  Claude 적대평가 per-worker(게이트 직접 실행, W1 RUF059 1건 codex resume) → 최종 codex 누적 diff(MAJOR 1=청산 leverage
  cap-bypass → 포지션값 사용 fix) → **Opus dogfood 2계통**(독립 Bybit HMAC 오라클 ↔ 코크핏 §03: TP/SL 값 66000/62000 정확 일치·빈값→—
  정직 / 청산 종단 flat+Order row / **kill-switch 활성 청산 성공 = 가드 bypass 실증, KS 미소비** / 콘솔 error 0). 신규
  **BL-434~436**.
- **2026-07-23 functional-parity 스프린트 (codex 4-generator ∥ + Claude 적대평가 + Opus dogfood)**: C 디자인 이식 후 기능 격차
  마감. **BL-401 Resolved**(3폼 `formState.errors` → `.field-error` 프리미티브, superRefine 평탄 경로 row 매핑, 메시지 한국어화 —
  grid min>max 만 거부로 BE 계약 정합) + **BL-411 Resolved**(지원 kind 목록 `OptimizationKind` enum 파생 + Sprint 넘버 문구 중립화) +
  **BL-402 Resolved (구조 소멸)** — C 이식이 4사이트 전부 네이티브 `<select>` 로 재작성해 uncontrolled/raw-UUID 결함 자체가 소멸(실측 재확인,
  코드 변경 0). 신규 A2(주문취소 액션 열 — "API 없음" 미렌더 전제가 거짓이었음, CF4 완비)·B2(orders state 반복 Query + 미체결 nav-count 캐논 §4.6
  복원)·B1(strategy.backtest_count read-time GROUP BY, COMPLETED 기준)·A7-lite(스트레스 최신 결과 리로드 복원)·A1(대시보드 전략 링크
  404→edit). 게이트: vitest 965→980 / BE 2416+18 / canon 32 불변 / authed 56→62. 신규 **BL-413~416**. **Opus MCP
  dogfood(10항목)가 잠복 P1 2건 추가 발굴·동일 스프린트 해소**: (a) stress_test enum 혼합 케이싱 — 최초 migration 소문자 라벨 vs SAEnum 대문자
  저장으로 실 DB 에서 MC/WF 생성 전부 500 → RENAME VALUE migration `20260723_0001` + alembic-경로 enum 라벨 sentinel 테스트(즉시
  status enum 드리프트도 추가 검출). (b) provider cancel_order 전 구현이 ccxt 에 symbol 미전달 — 실거래소 취소가 전부
  ArgumentsRequired(CF4 fail-closed 로 submitted 영구 잔존, BL-404 동형) → Protocol+5 provider symbol 관통 + futures
  linear 정규화. dogfood 최종 V1~V10 전 항목 PASS (취소 200/202 실클릭 + DB 오라클 3점 + A7-lite 리로드 복원 실측).

- **2026-06-30 stress_test-deepen (deepen-modules)**: stress_test 도메인 1차 deepen (`/deepen-modules`, 코드 변경 0). C1 = **BL-363 sharpen**(money-path framing + git 실증 `6c7adfba`→`ffb2299b` + `_load_run_context`/`_execute_grid_sweep` 구체 인터페이스) / C2 = 신규 **BL-392**(CA/PS "2D grid sweep" DTO 8-site 평행 정의 통합, untyped JSONB seam). 거부 = C3(`StressTestKind` dispatch registry — blast radius 최대 + 4타입 over-eng, 5번째 타입 등장 시 재평가) / C4(invariant SSOT — C2 graft 권장). engine 은 이미 `run_grid_sweep` 공유 = Deep 유지(건드리지 않음). dev-log `2026-06-30-stress_test-deepen.md`.
- **2026-06-30 backtest-deepen (verification loop)**: backtest 도메인 1차 deepen (improve-codebase-architecture + codex challenge, 코드 변경 0). 신규 **BL-387~391** (5건) — BL-387 sizing-canonical typed seam(P2 money-path) / BL-388 BacktestMetrics 4-site multi-SSOT(P2) / BL-389 finance-math `engine/metrics.py` 추출(P3) / BL-390 exit `fill_type` 중복 위임(P3) / BL-391 equity↔PnL reconciliation oracle(P3 test-first). codex KILL C3(idempotency dual-lock 통합 = 의도적 layered + 잘 테스트됨) → [ADR-021](./adr/021-backtest-idempotency-dual-lock.md). **codex C1 DOWNGRADE 는 phantom `metrics.py` 오인 → 직접 검증 후 KEEP 정정**(§7.3 circular-trust 차단). dev-log `2026-06-30-backtest-deepen.md`.
- **2026-06-30 BL-378 Resolved (`fix/pine-378-atr-wilder`)**: pine_v2 `ta.atr` 가 Wilder RMA (TV `ta.atr = ta.rma(ta.tr, len)`) 아닌 rolling SMA 사용 → 비-상수 TR(=모든 실데이터)에서 TradingView 와 silent divergence (헤드라인 harm-class). 실세계 8 전략 티어드 백테스트 QA (`docs/archive/qa/2026-06-30-pine-tiered-backtest/report.md`) 의 大-tier anti-circular hand-oracle 에서 발견 (5중 교차검증: codex G1 + 직접 oracle 9/9 bar + generator panel discriminator + panel 실행 15.0 vs 14.818 + codex G2). 수정 = `ta_atr` 가 기존 Wilder `ta_rma` 재사용 (~2줄, seed 동일·이후 TV 정합). G1-G4 (codex G1 plan eval + Workflow 12-agent generator panel + codex G2 challenge[B1 CONFIRMED] + codex diff-challenge[no P1] + G3 fresh review + mutation 2/2 CAUGHT) + full **2301 pass** (+6 pre-existing env, stash 대조 확인) + ruff/mypy clean + trust-layer golden 재생성(s2_utbot/i1_utbot num_trades 461→433, ATR→trailing 신호 변화). migration 0. 신규 **BL-379~386** (QA 부수 발견 9건: fn-local subscript / Track A alert warning / valuewhen na 등).
- **2026-06-30 BL-376 Resolved (`fix/pine-376-na-inf`)**: pine*v2 na/inf *소비\_ 사이트 robustness (BL-374 후속). 3 사이트 — (1) na/inf/<1 → ta.\* length: `_coerce_length` 헬퍼를 14 ta 함수 + dispatcher(change/stdev/variance int() 제거) + pivothigh/pivotlow 양 window + valuewhen occurrence(별도 non-finite 가드, occ=0 보존) 에 적용 → na 반환. (2) na/inf qty → `StrategyState.entry` skip + warning (라이브 reject 미러, 유한 0.0 보존). (3) inf → `math.floor/ceil/round`(per-branch, 공유 가드 미변경 — abs/sign/max 통과 유지) / subscript offset isfinite / timestamp +OverflowError. G1-G4(codex plan eval GO_WITH_FIXES + 4-candidate generator panel byte-수렴 + codex challenge[P1 valuewhen Decimal NaN 갭 → `(float, Decimal)` 가드] + fresh review SHIP + mutation 6/6 CAUGHT) + full suite 2305 pass(cov ≥90) + Playwright E2E(na/inf 백테스트 FAILED→COMPLETED, console.error 0). migration 0. 신규 [BL-377] (deferred: non-finite 주문/청산 가격 + 초대형 유한 length OverflowError).
- **2026-06-29 BL-374 Resolved (`fix/pine-374-na-semantics`)**: pine_v2 인터프리터 산술/math 도메인 오류 → Pine `na` 정규화 (`_na_safe`, 숫자 산술 한정, `math.pow` `**`→`math.pow()`). G1-G4 게이트(codex plan eval + 3-candidate generator panel + codex challenge[F1 dead stdlib-clamp 제거 + F2 문자열 `%` fail-closed] + fresh review GO + mutation 5/5) + full suite 2226 pass(cov 95.6%) + Playwright E2E(div-by-zero 백테스트 FAILED→COMPLETED, console.error 0). 신규 [BL-376] (deferred: na→length/qty, inf→floor·ceil·round).
- **2026-05-17 Sprint 62 PR #290 merge (Beta 본격 진입 결정 ★★★★★)**: 6 BL fix-first (BL-350+354 ★★★ Optimizer Zod resilience + BL-353 step 01 라벨 + BL-356/357/358/359 모바일 터치 ≥44pt 묶음). 실측 ~2-3h vs plan 6-8h (LESSON-067 6차 검증). main `36bb4e0`. **BL-070~072 milestone active 승격**. **재측정 skip + 본인 의지 (d) 통과**.
- **2026-05-17 Multi-Agent QA 재측정 (post-Sprint 61)**: Composite 6.08 → **7.5/10** (+1.42 목표 도달). 신규 BL-347~360 (14건, Critical 0 / P0 2 ★★★ 공통 BL-350+354 / P1 4 / P2 5 / P3 3). Sprint 61 11 BL Resolved 마킹 (PASS 8 + PARTIAL 2 + manual 1). 상세 = `integrated-report.html`.
- **2026-05-17 Sprint 61 PR #288 merge**: 11 BL fix (BL-310/311/312/319/322/323/327/328/339/340) source 적용 + hotfix PR #289 (BL-348/349). docs/archive/qa/2026-05-17/ baseline 별도.
- **2026-05-17 Multi-Agent QA 1차**: 신규 BL-310~346 (37건). 상세 = `integrated-report.html` + `sprint-61-plan.md`. 17 → 54 net.
- **Sprint 58** (2026-05-11~12): ✅ BL-241/242/243 Resolved (Pine TA 확장). 92 → 89 net.
- **Sprint 57** (2026-05-11): ✅ BL-234/237 Resolved (Optimizer Polish + heavy queue). 신규 BL-241~243. 91 → 92 net.
- **Sprint 56** (2026-05-11): ✅ BL-233 Resolved (Genetic). 신규 BL-238/239/240 chore. 91 net.
- **Sprint 55** (2026-05-11): ✅ BL-232 Resolved (Bayesian). 신규 BL-233~237. 88 → 92 net.

**Sprint 59 트리아주 결과 (PR-D, 2026-05-13):** 158 BL → **13 Active** (본 문서 본문) + **8 Deferred** (`_deferred.md` — Beta 6 + BL-005 + BL-145) + **137 Archived** (`_archived.md` — Resolved + Sprint 16~30 stale).

**P0 / P1 active short list (Beta 본격 진입 prep):**

- **🚀 Beta 진입 milestone (BL-070~072) — active P0** (`_deferred.md` 에서 승격):
  - ~~**BL-070** 도메인 + DNS + Cloudflare~~ → **2026-08-23 정정: 도메인·DNS 는 이미 있다**
    (2026-08-16 실측 — `qb.woosung.dev` 302 · `qb-api.woosung.dev/health` 200). 남은 것은
    **Cloudflare Access 제거 여부**이고 그것은 **「유지」가 사용자 결정**이다(`status.md` §320).
    걷으면 [BL-776](개방 가입)이 즉시 발현한다.
  - ~~**BL-071** Backend 프로덕션 배포 (Cloud Run/Railway/Render + … + Clerk production + 보안 헤더 gunicorn)~~
    → **2026-08-23 정정: 서술 3절 중 2절이 죽었다.** ⑴ **Clerk 은 없다** — [ADR-034](./adr/034-auth-self-host-better-auth.md)
    가 2026-08-17 에 self-host Better Auth 로 교체했고 코드의 `clerk` 언급 8건은 전부 **묘비 주석**이다.
    ⑵ **gunicorn 은 대상이 없다** — 레포에 0건이고 `apps/api/tests/test_uvicorn_server_header.py:84`
    `test_repo_has_no_gunicorn()` 이 그것을 단언한다([BL-347] 처방의 대상 부재). ⑶ 호스팅은
    [ADR-033](./adr/033-db-hosting-self-host-timescaledb.md) 이 **self-host CE** 로 확정했고 **서버는 이미 돌고 있다**(소크 상시 가동).
  - **BL-072** Resend 이메일 + Waitlist 활성화 — **코드·테스트는 완비**(`apps/api/src/waitlist/` 11파일 ·
    BE 테스트 8파일 · FE `/invite/[token]` 페이지+테스트). 남은 것은 **환경 변수 4종과 그 절차**다:
    `RESEND_API_KEY` · `RESEND_FROM_ADDRESS`(도메인 verify 24h) · `WAITLIST_TOKEN_SECRET` ·
    `WAITLIST_ADMIN_EMAILS`. ★**2026-08-23 실측 — 그 절차를 적은 문서가 레포에 0건이다**
    (`docs/operations/` 에 waitlist 항목 없음 · `RESEND_API_KEY` 언급은 `.env.example` 한 줄뿐).
    ⇒ 다음 회차의 실질 = **활성화 런북 신설**.
  - BL-073/074/075 = 위 완료 후 자연 trigger (Twitter/X 캠페인 + Beta 인터뷰 + H2 진입 gate)
- **Sprint 62 Resolved (6 BL)** ✅:
  - BL-350+354 ★★★ Optimizer Zod resilience / BL-353 step 01 라벨 / BL-356/357/358/359 모바일 터치 ≥44pt 묶음
- **Sprint 61 Resolved (11 BL)** ✅ (요약): BL-310/311/312/319/322/323/327/328/339/340/348/349 (PASS 9 + PARTIAL 2 + manual 1)
- **Production deploy 시점 자동 해소 묶음** (BL-070/071 시점):
  - BL-320 Development mode 배지 / BL-321/352 Clerk application name / BL-347 server header / BL-261 Clerk custom domain
- ~~**기존 P0**: BL-003 (Bybit mainnet runbook)~~ → **2026-08-23 삭제** (사용자 결정 ⑴ 실자금 안 간다). 산출물 `docs/operations/bybit-mainnet-runbook.md` 는 **실재하고 남긴다**
- **잔존 P1/P2/P3** (Beta 본격 진입 후 polish 또는 dogfood 발견 시 trigger):
  - P1: BL-014/015/022/023/024/025/026 (**BL-308 은 2026-06-29 W3 Resolved — 이 목록에서 제거**)
  - P2: BL-186/190/195/235/236/309/313/314/315/316/329/330/332/344/345/351
  - P3: BL-306/307/317/318/324/325/326/331/333/334/335/336/337/338/346/355/360

> **신규 BL-347~360 상세**: `docs/archive/qa/2026-05-17-post-sprint61/integrated-report.html` §3 + 페르소나별 원본 보고서 4종.
> **Beta 진입 milestone 상세**: `_deferred.md` BL-070~075 섹션.

---

## 분류 차원

### Priority

| 라벨   | 의미                                               | 예시                                                      |
| ------ | -------------------------------------------------- | --------------------------------------------------------- |
| **P0** | dogfood-blocker / H1 종료 gate                     | submitted watchdog, mainnet runbook, 본인 1~2주 dogfood   |
| **P1** | risk-mitigation / 알려진 broken bug 패턴 재발 위험 | commit-spy 도메인 확장, Redis lease, Auth circuit breaker |
| **P2** | hardening / nice-to-have 가 아닌 "건강도" 작업     | cardinality allowlist, dogfood 통합 dashboard             |
| **P3** | nice-to-have / 컨벤션 정합 / 미래 path             | zod import 정정, Path γ/δ                                 |

### Trigger 유형

- **time-based** — Sprint N+ / Q2 / H2 말 등 시점 명시
- **event-based** — "after dogfood week 1", "Beta 5명 onboarding 후" 등 외부 사건
- **dependency-based** — 다른 BL 또는 외부 자원 (예: Bybit mainnet API key) 후
- **on-demand** — 특정 PR / sprint 안에서 발견 시 즉시

---

## P0 — Dogfood / H1 종료 blocker

| ID                | 제목                                                                                                                                                                                                                                                                                                     | Trigger              | Est      | 출처                 |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- | -------- | -------------------- |

> 추가 P0 — BL-005 본인 dogfood + BL-145 EffectiveLeverageEvaluator (deferred). Resolved P0 = BL-001/002/004 (`_archived.md`).

### BL-489

**Title:** 사이징 자본이 D2 구간(진입 창 밖 / 청산 창 안)에서 일시 함몰한다
**Category:** Backend / trading (라이브 사이징)
**Priority:** P2
**Trigger:** BL-488 해소 후 (진입 이벤트 신뢰가 선행 조건)
★**주의** — [BL-488] 은 **이 세션 이전부터 원장에 섹션이 없다**. 발화 판정은 사람이 한다
**Est:** M (설계 선행 필요)
**상태:** 🟡 **부분 해결 — 결함은 살아 있고 원장의 처방이 반증됐다** (2026-08-21 재기술). carry 는 여전히 `bar_time < window_start` 단일 절단이고 2-pass 재실행 흔적이 없다(2026-08-09 status-triage-mass 확인, 2026-08-17 레인 γ 재판정). ★**2026-08-20 하네스 3회차 실사가 권장안 (a) 2-pass 를 반증했다** — `percent_of_equity` 사이징에서 손익이 자본에 비례(P=k·C)하므로 불변식 `C+P=B+L` 은 고정점 `C*=(B+L)/(1+k)` 에서만 성립하고 2패스는 거기 도달하지 못한다(원장의 「레버리지 게이트 활성 시 진동 가능성」은 과소 표현이다). 근거로 든 `KNOWN_LIMITATION` 오라클도 **실재하지 않는다**(`grep -rn KNOWN_LIMITATION apps/api` = 0건). ⇒ **처방이 없는 상태다. 착수하려면 수렴하는 사이징 재계산 설계가 먼저다**
**트리거 판정:** **미도래 (2026-08-21 재판정)** — 종전 판정은 「[BL-488] 해소 후」의 선행이 풀렸다는 것이었고 그것은 지금도 참이다. 그러나 **막는 것이 선행 BL 에서 처방으로 바뀌었다** — 원장이 든 2-pass 가 반증돼 지금 착수하면 반증된 처방을 구현하게 된다. 도래 = 수렴하는 사이징 재계산 설계가 서면으로 정해질 때. ★그래서 `docs/status.md` ⓪ 표에서 내렸다(ACTIVE ∪ (PARTIAL ∧ 도래) 정의를 지킨다)
**출처:** 2026-07-26 live-engine-parity. 적대적 검증 지적 → 프로덕션 실증.

**원인 / 영향:** `run_live` 는 warmup 창을 flat 에서 재실행하므로 창 시작 이전에 진입한 포지션은 열려 있지 않다. `close()` 가 `None` 을 반환해 그 거래의 청산이 재현되지 않는데, 그 청산의 `bar_time` 은 아직 `>= window_start` 라 carry(`bar_time < window_start`)에도 잡히지 않는다. 진입이 창을 벗어난 순간부터 청산이 창을 벗어날 때까지(보유 기간 + 지표 warmup) 그 손익이 **0 회 계상**된다.

프로덕션 실증 (창은 정확히 300 바 = 11:50~16:49):

```
16:12Z  화면 3 건 · 5.16879987
16:49Z  화면 2 건 · 4.07002377     <- 12:34 청산(+1.09877350)이 사라졌다
        원장은 불변 3 건 · 5.16882074
```

★ 창을 벗어나서가 아니다. 그 거래의 **진입(11:50)이 창의 bar 0** 이 되어 EMA 가 재현 불가해진 것이다.

**화면 총계는 이번 스프린트에서 해결됐다** (`sum_realized_pnl_all` 원장 SSOT — 17:10Z 실측으로 화면 == 원장 확인, 이후 1.5시간 유지). **남은 것은 `initial_capital` 뿐**이며, 미수정 시절의 영구 누락이 "일시 함몰 후 복귀" 로 완화된 상태다. `test_run_live_sizing.py` 의 KNOWN_LIMITATION 테스트가 이 한계를 못 박고 있다.

**권장 접근:** (a) 2-pass — 잠정 자본으로 1회 실행해 엔진이 재현한 청산 집합을 얻고 `전체 원장 − 재현분` 을 정확한 carry 로 삼아 재실행한다. 레버리지 게이트 활성 시 진동 가능성 검증 필요. (b) entry↔close 페어링으로 진입 `bar_time` 기준 절단 — 단 **BL-488 이 진입 이벤트를 떨어뜨리므로 신뢰 불가**. (a) 우선.

**영향 파일:** `tasks/live_signal.py`, `strategy/pine_v2/event_loop.py`.

**Risk:** 🟡 (수량이 일시적으로 작아진다. 과대가 아니라 과소 방향).

---

## P3 — Nice-to-have / 컨벤션 정합

> 12 archived (BL-050/051/052/053/054/055/056/057/138/139/151/153). ~~**활성 P3 = 8**~~ ★**stale** — 2026-08-08 `bl-audit.sh` 실측 P3 ACTIVE **101**. 이 파일 헤더 규약대로 집계 수치는 여기 박지 말고 스크립트를 돌려라 (BL-306/307 2026-05-15 CLAUDE.md align audit + BL-367/370/371 2026-06-26 trading-deepen-2 + BL-389/390/391 2026-06-30 backtest-deepen). ★2026-08-06 entry-set-divergence 강등 = BL-606/607/608/609.

| ID                | 제목                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | Trigger                                                                                                           | Est       | 출처                                                   |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | --------- | ------------------------------------------------------ |
| [BL-557](#bl-557) | (P3) `qb_active_orders` 게이지가 **음수(-2.0)** 로 표류 — inc 1곳 / dec 약 18곳                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | 그 게이지로 무언가를 판단하기 전                                                                                  | S         | 2026-07-30 live-entry-completeness                     |
| [BL-616](#bl-616) | 부트스트랩을 **우회해 만든** 워크트리는 husky 훅이 없다 — `pnpm install` 을 건너뛰면 `prepare: husky` 가 안 돌아 `.husky/_`(미트래킹)가 안 생기고, git 은 없는 `core.hooksPath` 를 **경고 없이 무시**한다. 실태: 워크트리 5개 중 **4개 정상**, 우회 생성된 1개만 결손(2026-08-07 정상화 완료). ★남은 축 = **감지 수단이 없다** — 훅이 안 도는 실패 모드는 출력이 0줄이라 「통과」와 구별되지 않는다                                                                                                                                                                                                                                                                                            | 워크트리에서 훅 미작동이 또 관측되면                                                                              | S         | 2026-08-07 ADR-027 회차 (자기 커밋에서 발견)           |

### BL-371

**Title:** ws-stream 고빈도 fill 스트레스 — orphan buffer cap 1000 + concurrent 순서 미검증
**Category:** Trading / Hardening (observability)
**Priority:** P3
**Trigger:** post-Beta 실거래 빈도 상승 시 (monitor)
**Est:** S (2-4h)
**상태:** 🟡 부분 해결 — 버퍼·cap·gauge 축은 BL-448 로 소멸하고 discarded 카운터·테스트가 대체됐다; 남은 건 out-of-order/고빈도 stress 테스트뿐(Trigger 미도래). (2026-08-09 status-triage-mass 코드 대조)
**트리거 판정:** 미도래 — 외생 조건(post-Beta 실거래 빈도 상승). Beta 미도달. 본문도 「현재 데모 빈도엔 충분 · 현재는 등재만」으로 스스로 적었다 (2026-08-11 bl-703-partial-verdicts)
**출처:** `2026-06-26-trading-deepen-2.md`

**현 상태:** ~~`state_handler.py` orphan buffer FIFO cap 1000(`_ORPHAN_MAX`)~~ → **2026-08-09 [BL-448](#bl-448) 로 버퍼·cap·gauge 가 통째로 사라졌다** (읽는 프로덕션 경로가 없었다). 남은 관심사는 out-of-order WS fill message / supervisor crash-restart cycle 의 고빈도(>100 fills/s) 스트레스 테스트 미검증뿐이다. 현재 데모 빈도엔 충분.

**권장 접근:** post-Beta 모니터링 — ~~`qb_ws_orphan_buffer_size` gauge alert >800~~ → **`qb_ws_orphan_discarded_total{reason="terminal_event_lost"}` 증가율**(버퍼 크기라는 축 자체가 없어졌다) + 필요 시 concurrent ordering 테스트 추가. 현재는 등재만.

**영향 파일:** `trading/websocket/state_handler.py` + 테스트.

**Risk:** 🟢 (현재 미발현, monitor).

---

## Beta 오픈 번들 — 단일 milestone

> **deferred** — Beta 본격 진입 trigger (BL-005 self-assessment ≥ 7/10 + 본인 의지 second gate) 도래 시 main 으로 row 이동.
>
> 상세 sub-task (BL-070~075) + TODO.md L748~801 보존.

---

## Cross-reference

### ADR ↔ Backlog

| ADR                                                                                    | 미해소 BL                                           |
| -------------------------------------------------------------------------------------- | --------------------------------------------------- |
| [ADR-005](./adr/005-datetime-tz-aware.md) DateTime tz-aware                            | (Sprint 5 backfill 완료, 잔여 없음)                 |
| [ADR-011](./adr/011-pine-execution-strategy-v4.md) Pine Execution v4                   | (Path γ/δ archived — BL-040/041)                    |
| [ADR-020](./adr/020-trust-layer-ci-design.md) Trust Layer CI (구 ADR-013)              | BL-026 (skip 활성화 회귀), BL-023 (KIND-B/C 정밀도) |
| [ADR-016](./adr/016-sprint-y1-coverage-analyzer.md) Coverage Analyzer                  | (BL-037 archived)                                   |
| [ADR-018](./adr/018-sprint12-ws-supervisor-and-exchange-stub-removal.md) WS Supervisor | BL-014 (partial fill), BL-015 (OKX WS)              |

### Lessons ↔ Backlog

| LESSON                                                     | 미해소 BL                                 |
| ---------------------------------------------------------- | ----------------------------------------- |
| LESSON-019 (commit-spy 회귀 의무화)                        | (BL-010 archived, 4 도메인 backfill 완료) |
| LESSON-007/008/009 (autonomous-parallel-sprints BUG-1/2/3) | BL-025 (스킬 patch)                       |

### Test Skip 추적표 ↔ Backlog

[2026-04-30 당시 `docs/TODO.md`의 Test Skip / xfail 추적표](https://github.com/woosung-dev/quantbridge/blob/b2c1541054326b06acf5e64f25094b6d5a37ea10/docs/TODO.md#L11-L31)의 dette 2 건이 백로그로 이관:

| Skip #                | 위치                                                 | BL ID                |
| --------------------- | ---------------------------------------------------- | -------------------- |
| #1                    | `tests/backtest/engine/test_golden_backtest.py:19`   | BL-022               |
| #16                   | `tests/strategy/pine_v2/test_mutation_oracle.py:213` | BL-023               |
| #4-7, #9-15 (12 skip) | `tests/strategy/pine_v2/test_*.py`                   | BL-026 (활성화 회귀) |

---

### BL-434

**상태:** 🟡 **부분 Resolved (2026-07-25 close-completeness)** — 완전 TP/SL **보고(display)** 는 착지, **청산 스윕은 [BL-437] 이연**(codex G0 2 BLOCKING). 근거: 본 섹션 `**⚠️ Partially Resolved …**` 리드인 줄 · 헤더 스프린트 변경 기록(`docs/backlog.md:23`, "BL-434 부분 Resolved(display) + 신규 BL-437(스윕 이연)").
**트리거 판정:** 미도래 — 선행 [BL-437] 이 **DEFERRED**(2026-08-11 실측)이고, 남은 청산 스윕이 그쪽 몫이다. Trigger 의 앞절(코크핏 §03 표시)은 display 축이 이미 착지해 소멸했다 (2026-08-11 bl-703-partial-verdicts)

**⚠️ Partially Resolved (2026-07-25 close-completeness)** — **완전 TP/SL 보고(display) 완료**: `fetch_open_conditional_orders`(2콜 union + orderId dedupe + stopOrderType 엄격분류) → position_service 조인(source-dedup·마크근접순) → §03 병합 표시(익절/손절 리스트) + has_trailing_stop 각주. dogfood 3계통(오라클 raw ↔ 앱 provider ↔ get_reconciliation 익절 66000/손절 62000). **청산 스윕은 BL-437 이연**(codex G0 2 BLOCKING: 타이밍 accept≠fill + account+symbol 공유 세션 오취소). dogfood 실측 = Partial 조건부 TP/SL 은 Bybit flat 시 자동취소(스윕 이연 안전).

**Title:** 완전 TP/SL 보고 — 포지션-부착 외 조건부(Partial-mode limit-TP) 주문 미표시 + 청산 시 미스윕
**Category:** Backend / Frontend / trading
**Priority:** P3
**Trigger:** 코크핏 §03 이 걸어둔 모든 TP/SL 을 보여줘야 하거나, 청산 후 잔여 조건부 주문 정리가 필요할 때
**Est:** M (fetch_open_orders 조인 + 스키마 확장 + 청산 스윕)
**출처:** 2026-07-24 trading-surface-pack (BL-431 은 포지션 필드만 read — Partial-mode limit-TP 는 별도 conditional order 라 미표시, 각주로 정직)

**원인 / 영향:** ccxt `fetch_positions` 의 position 필드는 Full-mode SL + set-trading-stop 트레일링만 담는다. QB 가 tpslMode=Partial 로 부착한 limit-TP 는 별도 조건부 주문이라 §03 에 안 나온다(각주로 고지). 또 reduce-only 청산은 포지션만 flatten 하고 잔여 조건부 주문은 스윕하지 않는다(포지션-부착 TP/SL 은 Bybit 이 flat 시 자동취소).

**권장 접근:** `fetch_open_orders`(conditional) 조인으로 완전 TP/SL 표시 + 청산 시 열린 reduce-only 조건부 주문 취소.

---

### BL-453

**Title:** StrEnum + 평문 String 컬럼 필드 — 새 세션 재조회 시 `.value`/`.name` 접근이 크래시할 수 있음
**Category:** Backend / trading (defensive — 패턴 재발 방지)
**Priority:** P3
**Trigger:** 이 5개 필드 중 하나에 `.value`/`.name`/`isinstance(..., <EnumClass>)` 를 새 세션 재조회 결과에 쓰는 코드가 추가될 때
**Est:** S (1-2h — 감사 + lint 가드 또는 테스트 1건씩)
**출처:** 2026-07-25 exit-attribution dogfood 실측 (`context-notes.md` §9.9) — **실제로 프로덕션 코드에서 한 건 발생해 수정함**

**원인 / 영향:** `ExchangeExit.classification`(`ExitClassification` StrEnum)이 `sa_column=Column("classification", String(24), ...)` 로 선언돼 있다(Sprint 26 의 `UndefinedObjectError` 회피 워크어라운드, `models.py:438-440`). 메모리에서 갓 만든 객체는 `.classification` 이 진짜 enum 이라 `.value` 가 되지만, **다른 세션에서 새로 `SELECT` 한 행은 SQLAlchemy 가 plain `str` 을 그대로 준다**(재캐스팅 없음) — `.value` 접근이 `AttributeError` 를 던진다. dogfood 에서 `_alert_new_exchange_exits` 가 정확히 이 경로로 죽어 신규 미귀속 행 알림이 매 사이클 조용히 실패하고 있었다(§7.3 대로 실측으로만 드러남 — 유닛테스트는 fake repo 라 잡지 못했다). `str(row.classification)` 로 수정 완료(`StrEnum.__str__` 이 값 자체를 돌려주므로 reload/메모리 양쪽 안전) + 실 DB 회귀 테스트 부착.

**감사 결과** — 같은 패턴(StrEnum 타입 + 평문 String 컬럼)인 필드가 4개 더 있다: `LiveSignalSession.interval` · `LiveSignalEvent.status` · `AlertRule.rule_type` · `AlertRule.channel`. 전수 조사 결과 **현재는 이 4개 모두 `==`/`!=`/`str()` 만 쓰거나 호출부가 없어 안전**하다(`StrEnum` 이 `str` 서브클래스라 비교 연산은 reload 여부와 무관). 즉 지금 당장 고칠 버그는 없고, **미래에 이 필드들에 `.value`/`.name` 을 쓰는 코드가 추가되면 같은 함정을 반복**할 잠재 위험만 남아 있다.

**권장 접근:** (a) 최소 — 5개 필드 선언부에 "`.value`/`.name` 금지, `==`/`!=`/`str()` 만 사용" 주석을 통일해서 남긴다(현재 `interval` 필드에만 있음, 나머지 4개엔 없음) (b) 중간 — ruff 커스텀 규칙 또는 AST 기반 테스트(이 레포의 `test_no_module_level_loop_bound_state.py` 패턴 참고)로 이 5개 필드명에 대한 `.value`/`.name` 접근을 정적으로 금지 (c) 근본 — Sprint 26 워크어라운드가 아직 필요한지 재검토하고, 필요 없으면 `sa.Enum` 으로 되돌려 SQLAlchemy 가 재캐스팅을 대신하게 한다.

**Risk:** 🟢 (현재 실제 발생한 크래시는 이미 수정됨. 이 항목은 재발 방지용 예방적 등재)

**상태:** 🟡 **부분 Resolved — 권장안 (a) 까지 (2026-07-25, `stage/exit-money-path`).** `tasks/trading.py:1698` 의 마지막 `.value` 잔존(`qb_exchange_exit_rows_total` 라벨)을 `str(row.classification)` 로 바꿨다. 지금은 메모리 객체라 안전하지만, 소스가 재조회 경로로 바뀌는 리팩터 한 번이면 dogfood 때와 같은 크래시가 재현되는 자리였다(grep 결과 코드베이스에 남은 유일한 `.value`). 그리고 **감사 목록에서 빠져 있던 `ExchangeExit.attribution_confidence` 를 포함해 6개 필드 전부**에 "`.value`/`.name` 금지, `==`/`!=`/`str()` 만" 주석을 통일했다(`models.py:441 · 583 · 634 · 640 · 718 · 742`). ~~권장안 (b) 정적 가드와 (c) `sa.Enum` 복귀는 미착수.~~
→ ★**2026-08-24 n9-trading-contract — (b) 의 「선언 축」만 닫혔다. 「사용 축」은 구조적으로 못 닫는다.**
신설 `apps/api/tests/trading/test_strenum_column_contract.py` 가 `sa_column=Column(..., String(...))` 위에 StrEnum 주석이 얹힌 필드를 AST 로 수집해(6건) **전건이 BL-453 계약 주석을 달고 있는지**를 잰다. 7번째 필드를 계약 없이 추가하면 red 다.
★★**사용처 가드(「이 6개 필드에 `.value`/`.name` 금지」)는 기각됐다 — 다시 만들지 마라.** `apps/api/src` 전량 AST 실측에서 12건이 걸렸고 **12건 전부 위양성**이었다: `bt.status.value`·`run.status.value`(backtest·optimizer·stress_test)의 `status` 는 **진짜 Enum 컬럼**이라 `.value` 가 정당하고, `tally.channel.value`(`trading/entry_completeness.py`)의 `tally` 는 `ChannelTally` 라는 **로컬 dataclass** 다. ⇒ **필드 이름만으로는 소유 클래스를 못 가른다.**
⇒ **잔여 = 사용 축 · (c) `sa.Enum` 복귀.** 사용 축을 닫으려면 이름이 아니라 **타입**을 봐야 하므로 mypy 게이트가 선행 조건이다(현재 CI 는 `ruff` 만 잰다).
**트리거 판정:** 미도래 — 동승 조건. 「이 5개 필드에 `.value` 를 새로 쓰는 코드가 추가될 때」라 그 코드를 쓰는 회차에 붙는다. 단독 착수 시 값이 0이다 (2026-08-11 bl-703-partial-verdicts)

---

### BL-477

**Title:** 같은 Bybit 서브계정을 가리키는 API 키 2개가 청산 원장에 같은 행을 2번 적재한다 (phantom `unknown`)
**Category:** Backend / trading (청산 원장 귀속)
**Priority:** P3
**Trigger:** 읽기 전용 계정 정리 시 또는 external-exit 알림이 시끄러워질 때
**Est:** S
**상태:** 🟡 부분 해결 — BL-605 dedupe 로 신규 이중 적재는 막혔으나 기존 574행이 남아 있다 — 잔여는 [BL-529] 와 같은 「이미 쌓인 거울 행 정리(사용자 승인)」 (2026-08-09 status-triage-mass 코드 대조)
**트리거 판정:** 미도래 — 외생 조건이 **사용자 결정으로 닫혔다.** 2026-08-11 결정 = `exchange_accounts` `0277c150` **행을 삭제하지 않는다**(FK `ondelete="RESTRICT"` ×3 + `exchange_exits` 103행 ⇒ 지금 DELETE 는 500). 잔여 574행 정리는 그 결정이 뒤집혀야 열린다 (2026-08-11 bl-703-partial-verdicts)
**출처:** 2026-07-26 BL-474 dogfood 실측

**원인 / 영향:** `exchange_accounts` 두 행(`19a8166a` "bybit demo" · `0277c150` "bybit demo- aaa")이 **같은 Bybit 데모 서브계정의 서로 다른 API 키**다. 스윕은 계정별로 `/v5/position/closed-pnl` 을 치므로 같은 청산이 두 번 적재되고, upsert 키에 `exchange_account_id` 가 들어가 중복으로 접히지 않는다.

```
exchange_order_id                     closed_pnl    classification  exchange_account_id
b0a1c42a-aeb9-404e-89ec-b22ac939e126  -0.05935440   ours            19a8166a  (우리 주문과 매칭)
b0a1c42a-aeb9-404e-89ec-b22ac939e126  -0.05935440   unknown         0277c150  (매칭 실패 → 외부로 분류)
```

07-24 행들도 같은 패턴이라 **선재 문제**이며 BL-474 와 무관하다.

**손익 이중 계상은 없다** — `aggregate_closed_pnl`(`exchange_exit_repository.py:43-59`)이 `WHERE exchange_account_id == account_id` 로 계정 스코프이고, 세션 손익은 `orders.realized_pnl` 을 세지 원장을 세지 않는다. 실측으로 확인: 세션 확정 손익 `-0.12772399` = 두 청산의 정확한 합.

**진짜 영향은 귀속/알림 표면**이다. 우리가 낸 청산이 두 번째 키 관점에서는 "앱 밖에서 일어난 청산" 으로 보여 `unknown` 이 되고, external-exit 알림이 유령 이벤트로 시끄러워진다.

**권장 접근:** ~~(a) 사용자가 읽기 전용 계정을 삭제하면 자연 소멸(가장 싸다)~~ · (b) 등록 시 동일 거래소 서브계정 중복을 감지해 경고 · (c) 귀속을 계정이 아니라 `(exchange, exchange_order_id)` 기준으로 재조회. 셋 중 무엇을 할지는 계정 2개 등록을 계속 지원할지에 달렸다.

★★★**2026-08-11 ledger-truth — (a) 는 「가장 싸다」가 아니라 「지금 누르면 500 이다」.**
DB·코드 대조 실측:

| 무엇                     | 실측                                                                                                                                             |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| 두 계정의 `exchange_uid` | **둘 다 `558689281`** (`0277c150` · `19a8166a`) — 중복 확인                                                                                      |
| `0277c150` 의 의존 행    | `exchange_exits` **290** · `orders` **2** · `live_signal_sessions` **1**                                                                         |
| FK 제약                  | `ondelete="RESTRICT"` **×3** — `trading/models.py:244` · `:509` · `:785`                                                                         |
| DELETE 핸들러            | `trading/router.py:274-291` `delete_exchange_account` → `svc._repo.delete()` 직행. `IntegrityError` 핸들러가 **router·service 양쪽에 0건**(grep) |

⇒ DELETE 는 FK RESTRICT 에서 `IntegrityError` 를 내고, 잡는 곳이 없어 **500** 이 된다.
★**「읽기 전용 계정」이라는 전제도 틀렸다** — `0277c150` 에는 `live_signal_sessions` **1행**이
붙어 있다. 읽기 전용이 아니다.
★**상속받은 「`exchange_exits` 103행」도 틀렸다 — 실측 290 이다**(LESSON-099: 「N건」을 상속하지 마라).

**2026-08-11 사용자 결정: 삭제하지 않는다.** ⇒ 진짜 처방은 (b)+(c) 이고, 그 앞에
`router.py:288` 에 **409** 를 세우는 것이 선행이다(현재 500 은 「왜 안 되는지」를 안 알려 준다).
이 셋은 이 회차 범위 밖이고 다음 회차 항목이다.

**Risk:** 🟢 (알림 노이즈. 금액 정확도 영향 없음)

---

## 운영 규약

### 신규 항목 추가

1. 적절한 priority 결정 (P0~P3 정의 표 참조)
2. 다음 BL ID 부여 (현재 사용 범위: BL-001~005, BL-010~487)
3. live ledger에는 다음 7필드를 쓴다: ID / 제목 / priority / **Status:** / 1줄 영향 / trigger 또는 재검토 시점 / 다음 검증 / 근거 링크. `Category`·`Est`는 실제 계획에 필요할 때만 추가한다.
4. 장문의 재현·반증·대안은 처음부터 해당 sprint `dev-log` 또는 `archive/backlog/`에 둔다. live ledger에 중복하지 않는다.
5. 출처 cross-link (파일:라인 또는 dev-log 파일명) 필수
6. 의존성 있으면 명시 (다른 BL ID 또는 외부 자원)
7. 출처 문서의 자연어 표현 옆에 `→ BL-XXX` cross-link를 추가한다.

### 항목 해소

1. 해당 BL 절에 `**Status:** ✅ Resolved (2026-XX-YY, PR #NN)` 추가
2. 원인·대안·실측이 1화면을 넘으면 먼저 해당 sprint `dev-log`를 상세 근거로 쓴다. 그 기록만으로 재검토할 수 없을 때만 묶음 단위 `archive/backlog/YYYY-MM-DD-<bundle>.md`를 만든다. 기존 `archive/refactoring-backlog/`은 이전 이력으로 유지한다.
3. 본 문서에는 ID / 제목 / priority / status / 1줄 결과 / archive·dev-log 근거 링크만 남긴다. 이 6줄 ledger를 삭제하지 않는다 — `scripts/bl-audit.sh`가 상태를 계속 대조한다.
4. 출처 문서의 cross-link 옆에 `(✅ Resolved BL-XXX)`를 표기한다.
5. "변경 이력"에는 묶음당 한 줄만 기록하고, 상세 서사는 dev-log 또는 archive 링크로 끝낸다.

### Trigger 도래 확인

신규 sprint 진입 시:

1. 본 문서 P0 섹션 전체 review — trigger 도래 항목이 있는가?
2. P1~P2 섹션의 trigger 도 함께 review (예: "Bybit Demo 안정화 후" → 현재 안정화 됐는가?)
3. `_deferred.md` 의 6-8주 재평가 (BL-005 본인 의지 second gate, BL-070~075 Beta milestone)
4. 도래 항목이 있으면 active TODO.md 의 "Next Actions" 로 승격 + 본 문서에서 `**Status:** 🟡 In progress (Sprint NN)` 마킹

---

## 변경 이력

> ★**2026-08-23 강등 tombstone.** 변경 이력 312줄(2026-04~08)을 **삭제**했다 — 원장의 변경 이력은
> **git log 가 정본**이고 여기 다시 적는 것은 순수 중복이었다.
> 원문 = `git show 21e40d5c:docs/backlog.md` (`## 변경 이력` 절).
> 앞으로 이 절에는 **원장의 구조가 바뀔 때만** 한 줄 적는다 — 항목 추가·상태 변경은 적지 마라.

- **2026-08-23** — 원장 다이어트. RESOLVED 파일 삭제 · DEFERRED 183→23 · ACTIVE 26→16 · 인덱스 표 70행 정리. 판정 근거 = 사용자 결정 3건(실자금 안 감 · Beta 안 염 · 멀티 거래소 안 함). 헤더의 tombstone 참조
- **2026-08-18** — 원장 3분할([BL-779]) — ACTIVE∪PARTIAL / DEFERRED / RESOLVED 세 파일
## Deferred — trigger 미도래 · 의도적 부활 가능 (구 `_deferred.md` 승격, 2026-08-06)

> archive 삭제(docs 대개편)와 함께 Sprint 59 트리아주의 deferred 원장을 본 문서로 승격했다.
> 부활 = 행을 위 P 섹션으로 옮기고 `### BL-NNN` 섹션 + `**상태:**` 줄을 단다. 6-8주마다 재평가.
> ★이 표의 BL 은 섹션이 없으므로 `bl-audit.sh` 집계 대상이 아니다(의도). BL-070~075 는 2026-05-17 헤더 shortlist 에 「milestone active 승격」 표기가 함께 있다 — 실행은 여전히 trigger 대기.

| ID     | 제목                                                                                                     | Trigger                                                                                          | Est                       |
| ------ | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | ------------------------- |
| BL-005 | 본인 실자본 1~2주 dogfood 운영                                                                           | BL-001~004 완료 + self-assessment ≥7/10 + 본인 의지 second gate                                  | L (≥14 days, 사용자 수동) |

★★★**2026-08-08 정정 — 이 BL 이 인용한 「MTBF 8.70h · P(168h)=4.115e-09」은 혼합 추정치다.**
원인별로 층화하면 이미 고친 원인들이 섞여 있다는 것이 드러난다:

**아래는 2026-08-12 재측정본**이고 괄호가 2026-08-08 값이다(층 경계는 날짜가 아니라 **수리**라서 불변):

| 창                  | n                                                                                                                                                                                                                                                                                                                                                                                                                                                  | 노출                                | 자동사망 | MTBF                     | 95% CI          | 그 사망의 정체                           |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- | -------- | ------------------------ | --------------- | ---------------------------------------- |
| 전 이력             | 40 (구 38)                                                                                                                                                                                                                                                                                                                                                                                                                                         | 193.37h (구 107.12)                 | 8        | 24.17h (구 13.39)        | [12.27, 55.99]  | 혼합                                     |
| 2026-08-03 이후     | 16 (구 14)                                                                                                                                                                                                                                                                                                                                                                                                                                         | 147.16h (구 60.91)                  | 7        | 21.02h (구 **8.70**)     | [10.20, 52.29]  | **혼합 — 이 BL 이 인용해 온 값**         |
| [ADR-025] 수리 이후 | 7 (구 5)                                                                                                                                                                                                                                                                                                                                                                                                                                           | 124.72h (구 38.47)                  | 2        | 62.36h (구 19.24)        | [17.26, 514.93] | gap-resync 1 — [BL-622] 가 수리 · 오염 1 |

★**각 수리 이후의 사망은 전부 「그 다음 원인」이었다.** 알려진 원인이 모두 닫힌 뒤의 **미설명 사망은
0건**이다. ★2026-08-12 정정 — 종전의 「노출이 5.59h 뿐이라 **아래에서 못 잰다**」는 낡았다:
[BL-622] 이후 노출이 **91.84h(16.4배)** 로 자랐고 그 안의 사망은 1건이다. 그래도 **CI 상한이
3627h** 라 여전히 아래에서 못 가른다 — 자란 것은 표본이지 **판별력이 아니다**.

★★**그러므로 이 BL 의 결론을 「MTBF 가 병목이다」로 단정하지 마라.** 정확한 문장은
**「현행 사망률을 아래에서 잴 표본이 아직 없다 — 층화 전 값(21.02h)은 고친 원인을 섞은 상한이다」**이다.
판정에 필요한 것은 **[BL-634] 착지 이후의 노출**이고, 그때까지 이 BL 은 **측정 대기**다.
★★★**네 층의 CI 가 2026-08-12 에도 6쌍 전부 겹친다**(운영 사고 제외 층을 넣으면 10쌍 전부).
MTBF 점추정이 13.39h → 24.17h 로 **1.8배** 올랐는데도 「올랐다」고 말할 수 없다 — 이것이 이 BL 이
CI 를 표와 같은 실행에서 내게 만든 이유다.

★부수 — **오염은 자동사망 8건 중 1건뿐**이었다(나머지 7건은 맥→오라클 이관 전이라 호스트가 하나였다).
「배타성을 고치면 MTBF 가 오른다」는 성립하지 않는다. [BL-634] 가 사는 것은 **재발 방지**다.

---

### BL-641

**Priority:** P1
**카테고리:** 운영 / 소크 C1 게이트 해석
**Trigger:** 소크 재기동 회차마다 재측정 (앞절 「BL-003 재계획 시」는 **발화 불가가 됐다** —
2026-08-23 사용자 결정 ⑴「실자금 안 간다」로 [BL-003] mainnet runbook 섹션을 삭제했다.
실자금 결정이 뒤집히면 `git show 4c65bc0e:docs/backlog.md` 에서 되살리고 이 절도 함께 복원해라)
**Est:** M

★★**2026-08-15 층 경계가 하나 생겼다 — 창 1과 창 2를 같은 모집단으로 묶지 마라.**
첫 24h 창이 `✓ 자격 획득`(연속 **24.0007h** · 실격 0)으로 확정되고(**C1 = 1/3회**) 사용자 승인
아래 R0b(`down → pin b5e24fbf → up`)를 돌렸다. 그 pin 이 워커를 `fb7bb772`(#633) →
`b5e24fbf`(#642)로 **4개 PR · 217 파일** 점프시켰다.
⇒ **창 1 = `fb7bb772` · 창 2 = `b5e24fbf`** 로 층을 나눠 세라. MTBF·사망률을 한 줄로 합치면
서로 다른 코드의 수명을 섞는 것이다(이 항목이 2026-08-08 에 세운 층화 규칙 그대로다).
★부수 실증 — **`pin` 은 C2 를 죽이지 않는다.** 재기동 직후 판독에서 C2 가 **24.0007h 그대로**
남았다([ADR-024] §255 가 코드로 확인됐다). 창 2는 0.0000h 부터 따로 센다.
★창 2 시작(celery ready) = `2026-08-15T16:35:32Z`.
**상태:** 🟡 **부분 해결 — 2026-08-12 재측정 완료. 셈은 움직였지만 CI 는 아직 못 가른다**
(2026-08-08 soak-exclusivity-and-observability 착지 · 2026-08-12 surface-demo-pack 재측정).
⑴ 층화 + **95% 신뢰구간**을 [ADR-024] 에 등재했고
⑵ 재측정 도구 `apps/api/scripts/mtbf_stratified.py` 를 만들어 「회차마다 재측정」 Trigger 를
집행 가능하게 했다(self-check 가 앞 38행으로 이 회차 값을 재현한다, 2/2).
⑶ **2026-08-12 에 그 Trigger 뒷절을 실제로 집행했다** — 아래 표가 새 값이다. 4일 만에 노출이
107.12h → 193.37h(**+86.25h**)로 늘었는데 자동 사망은 **8건 그대로**다. **닫는 조건은 불변** —
사망률이 실제로 내려가야 하고, 그 판정은 며칠 단위 관측이라 이 회차 밖이다.
★★★**그 과정에서 이 BL 자신의 인용값이 반증됐다** — 아래 층화 표는 **점추정끼리 비교할 수
없다**. 네 층의 CI 가 **6쌍 전부 겹친다**(상세 = [ADR-024] §층화). ⇒ 「수리로 MTBF 가 올랐다」도
「내렸다」도 이 데이터로는 말할 수 없다. **닫는 조건은 불변** — 사망률이 실제로 내려가야 한다.

★★★**2026-08-15 clock-fill-sweep — 아래 「관측 밀도」 처방이 코드로 반증됐다. 축을 정정한다.**
`darkness` 가 `evaluate()` 안에서 읽히는 곳은 **정확히 2곳**이고 둘 다 시간 계산과 무관하다:
`soak_gate_predicate.py:752`(존재 여부만 C5 로) · `:797`(출력 전용). **`ratio` 를 비교하는 부등식은
레포 전체에 없다** — 어둠 99.9% 여도 C1/C2/C3/C4 는 비트 단위로 동일하다. 관측으로도 같은 결론이
나왔다: 02:05Z→04:51Z 사이 C2 는 **+2.86h(경과분 100% 귀속)** 인데 어둠 분자는 **+202(경과분 100%
어둠)** 로, 두 셈이 동시에 성립한다. ⇒ **「C1 을 채우려면 관측 밀도가 올라야 한다」는 거짓이다.
타이머 주기 단축안은 철회한다** (30분 주기는 C4 한계 60분에 대한 안전 여유 1회분이라 오히려
건드리면 안 된다 — `soak-watch.sh:196`).
**참인 명제**: C1/C2 크레딧 = `세션 lifetime ∩ 귀속 구간 ∩ [창시작, now] ∩ phantom 커버리지`
(`soak_gate_predicate.py:667-706`, 자르는 것은 `restrict():415`). 그리고 C1 은 시간의 합이 아니라
**「24h 이상 연속 구간을 가진 귀속 구간의 개수」**(`:719-723`)다 — `C1_cumulative_hours` 는 어떤
조건식에도 안 들어간다. 귀속 구간은 `attribution_intervals():210` 이 만들고 **`up` 이 열고
`pin`/`up`/`down` 이 닫는다.** ⇒ **de3db35a 의 「125.6h 살았는데 0.0000h」의 사인은 어둠이 아니라
「귀속 구간 밖」이다** — 실측(`.soak/pin-history.jsonl`)으로 귀속 구간이 2026-08-07 09:33 에 닫히고
다음이 2026-08-14 05:53 에야 열렸다. **처방은 이미 들어가 있다**(BL-737/744/745 = 감시자 부활 +
`OnFailure` 텔레그램). 이 축에서 새로 등재한 것 = **[BL-748]**(C4 공허 통과).

★★**2026-08-15 실측 추가 — 「세션이 살아 있었다」와 「시간이 계상됐다」는 다른 값이다.**
서버 세션 `de3db35a` 의 행은 08-08 23:16 ~ 08-14 04:51 동안 `is_active` 였는데(125.6h),
그 시점 게이트는 **`C1 0/3 · 누적 0.0000h`** 였다. 같은 출력이 **귀속 불가 107.02h · 어둠 비율
98.6%(8684/8808)** 를 함께 찍는다. 표본 435건 · 간격 중앙 **31.0분**(30분 타이머 주기)이므로
표본과 표본 사이는 전부 어둠으로 셈된다. ⇒ **C1 을 채우려면 세션 생존만으로 부족하고 관측
밀도가 함께 올라야 한다.** 이 회차는 그것을 재기만 했다 — 밀도를 올리는 처방은 미착수다.
★이 값을 「소크가 안 돌았다」로 읽지 마라. 2026-08-14 에 실제로 그렇게 읽어 status.md 표에
「7일째 정지」를 적었는데, 그때 서버 소크는 돌고 있었다(2026-08-15 반증).
**트리거 판정:** ★**2026-08-24 재분류 — 이 항목은 「닫을 수 있는 일」이 아니라 「소크 창마다 반복하는 측정」이다.**
Trigger 뒷절이 「소크 **재기동 회차마다** 재측정」이라 일회성 종결점이 없고, 입력이 **살아 있는 소크 창**이라 코드 작업만으로는 진행이 안 된다. ⇒ ⓪ 표의 ★★★(= 지금 착수하면 닫힌다)는 **과대평가**였다. 소크 창을 다루는 회차에 **동승**시켜라 — 단독 회차의 주제로 고르지 마라.
~~도래 — Trigger 앞절이 발화했다.~~ 「[BL-003] 재계획 시 즉시」인데 **2026-08-11 사용자 결정으로 C1 문턱이 「168h」에서 「누적 24h × 3회」로 교체**됐고(그 미반영이 [BL-701] 로 등재됐다), 뒷절 「소크 재기동 회차마다 재측정」도 2026-08-08 재기동으로 충족된다. ★기계는 트리거에 「소크」가 들어 있어 소크 축으로 버킷하고 미도래를 냈다 — **절의 접속을 반쪽만 읽은 것**이다 (2026-08-11 bl-703-partial-verdicts)

**BL-003 의 실질 선행조건은 문턱이 아니라 MTBF 다.**

ADR-024 리셋 표에 의해 실격은 C1 을 0 으로 되돌린다. 그러므로 「누적 clean 168h」는 사실상
「168시간 연속 무실격」이고, 그 확률이 P(168h 생존)이다.

**2026-08-12 재측정** (surface-demo-pack · 서버 원장 40행 · self-check 2/2 ✓). 괄호는 2026-08-08 값:

| 표본            |   n | 누적                    | 최장                  | 자동 사망 | MTBF                  | 95% CI         | P(168h)                    |
| --------------- | --: | ----------------------- | --------------------- | --------: | --------------------- | -------------- | -------------------------- |
| 전 이력         |  40 | **193.37h** (구 107.12) | **65.28h** (구 19.42) |         8 | **24.17h** (구 13.39) | [12.27, 55.99] | **9.584e-04** (구 3.6e-06) |
| 2026-08-03 이후 |  16 | **147.16h** (구 60.91)  | **65.28h**            |         7 | **21.02h** (구 8.70)  | [10.20, 52.29] | **3.383e-04** (구 4.1e-09) |

**24h 도달 1건 / 40세션** — 전 이력 최초다(구 0/38). 사인 전량(서버 DB GROUP BY):
`user_stopped` **19** · 사인 없음 **13**(1건은 진행 중) · `position_divergence` **6** ·
`gap_resync_position_mismatch` **2**. ★**자동 사망은 뒤의 둘, 합 8건뿐이다.**

★★★**2026-08-12 반증 — 「이 표가 `user_stopped` 를 자동 사망과 함께 센다」는 거짓이었다.**
`user_stopped` 는 `AUTOMATIC_DEATH_REASONS`(8종)에 **없고**, `auto_death` 는 그 집합 소속 여부
단독으로 정해진다(`apps/api/scripts/mtbf_stratified.py` `parse_rows`). 정본이 코드 옆에 이미 적혀
있었다 — `soak_gate_predicate.py:39` 「`SessionDeactivationReason` 에서 `user_stopped` 를 뺀 것 =
**자동 사망**」. ⇒ 운영자 재기동은 **처음부터 우측 절단**이었고 P(24h)·MTBF 는 오염되지 않았다.
독립 대조: `soak-gate.sh` 실격 목록의 `auto_death` 도 **8건**이고 그 목록에 `user_stopped` 는 0건이다.
★그 대신 **표시 결함이 실재했다** — `절단` 열이 `alive + operational_dropped` 만 세서 40행이
`사망 8 + 절단 1` 로 인쇄됐다(비-자동사망 종료 31건이 어느 열에도 없었다). 산술은 처음부터
맞았고 표시만 틀렸다. 같은 회차에서 `n - deaths` 로 고쳤다.

★**168h 문턱은 이미 폐기됐다** — 2026-08-11 사용자 결정으로 C1 은 「누적 24h × 3회」다([BL-701] 반영).
그러므로 위 P(168h) 열은 **역사적 대조용**이고 판정에 쓰이지 않는다. 지금 진척은 `soak-gate.sh` 의
`C1 24h 창 N / 3회` 줄로만 읽는다(2026-08-12 실측 **1/3**). 사망률을 낮추는 것이 유일한 경로라는
결론은 불변이고, 표적도 그대로다 — BL-634 계정 배타성 이후 `position_divergence` 계열 전체.
이 BL 은 BL-003 의 하위 작업이 아니라 게이트 해석이므로, BL-003 의 Est 를 다시 잡기 전에 읽어야 한다.

**Risk:** 🔴 MTBF 를 개선하지 않으면 168h 연속 무실격 조건은 사실상 도달 불가다.

### BL-619

**Priority:** P1
**카테고리:** Backend / 라이브 신호 (가용성)
**Trigger:** 다음 소크 창에서 같은 정지가 관측되면 (로그가 남아 있는 동안 즉시 부검)
**Est:** M
**상태:** 🟡 **부분 해결 — 관측 장치는 배치됐다. 뿌리는 여전히 모른다** (2026-08-08
soak-exclusivity-and-observability 회차). 서버에 `dev.quantbridge.soak-logs-follow.service` 를
설치했다(`--install` · linger 는 이미 `yes` 라 sudo 불필요). 실측: 서비스 `active` ·
`~/quantbridge/.soak/logs/worker-follow.log` **871KB** · 활성 세션 `a4f1cbfb` 의
`live_signal.evaluate_all` 이 실제로 찍힌다. ★**「설치 완료」 출력은 검증이 아니다** — 75초
재측정으로 **+10,422 바이트**, 커서 `06:05:04Z → 06:15:03Z` 전진을 확인했다(멈춘 follow 와
살아 있는 follow 는 파일 존재만으로는 구분되지 않는다). 회전 상한 32MB × 4벌.
★**이것은 이 BL 을 닫지 않는다** — Trigger 가
비로소 **충족 가능해진 것**이지 정지의 뿌리를 안 것이 아니다. 닫는 조건은 불변이다:
같은 정지를 로그가 남아 있는 동안 재관측하고 부검한다.
**트리거 판정:** 미도래 — 외생 조건(재관측). 2026-08-11 게이트 실측 = **실격 0건 · C4 표본 공백 0건**이고, 본문의 첫 재관측(15.30h 창 · `evaluate_all` 919건 · 간격 최소=중앙=최대 60.0초)도 「재발 없음」이었다. **이벤트 부재는 정지의 증거가 아니지만, 관측되지 않은 것을 부검할 수도 없다** (2026-08-11 bl-703-partial-verdicts)

★★**2026-08-08 — 재관측이 처음 성립했고 결과는 「재발 없음」이다**(soak-mortality-repair).
로그가 남은 첫 창(세션 `a4f1cbfb` · `2026-08-08T02:32:42Z`~`17:50:42Z` · **15.30h**)에서
`live_signal.evaluate_all` 디스패치 **919건**을 재니 간격이 **최소=중앙=최대 60.0초** ·
**2분 이상 공백 0건**이다. ⇒ **태스크 디스패치 축의 정지는 0건**이다.
★**판별력은 있다** — 원 사건은 ~17분이고 이 도구는 60초 해상도로 2분 공백을 잡는다.
17분 정지가 있었다면 확실히 잡혔다. **유효한 음성 대조다.**
★**그래도 닫지 않는다** — 재발 0건은 뿌리를 밝히지 않는다. 원 사건은 1회성이고 창은 15.30h 다.

★★★**다른 축은 조용하지 않았다 — 그리고 그 축을 잴 도구가 없다.** 같은 창에서
`last_evaluated_bar_time` 은 **10분 이상 정체가 35구간**(최대 31.0분) 관측됐다. 디스패치는
60초마다 살아 있는데 **상태가 전진하지 않은** 것이고, 이는 원 사건이 보인 축
(`live_signal_states` 마지막 쓰기 `20:14:33` → 다음 claim `20:30:00` bar)과 **같은 축**이다.
★**그 35건의 크기는 못 믿는다** — 게이트 표본 간격이 **중앙 13.9분 · 최대 31.0분**이라
관측된 「정체 31.0분」이 표본 최대 간격과 **정확히 같다**. 정지의 크기인지 관측 공백의 크기인지
이 표본으로는 구분되지 않는다 ⇒ 신규 [BL-653](#bl-653). DB 축(`live_signal_states` 쓰기 시각)이
이를 가를 유일한 수단인데 이 회차는 스택을 내린 채 작업해 **조회하지 않았다**. 다음 창에서 물어라.

**라이브 파이프라인이 한 세션에 대해 ~17분 멈췄고 뿌리를 모른다.**

[BL-622] 부검의 **상류**다. 2026-08-06 20:14:33 ~ 20:31:48 사이에 세션 `c160a1a9` 는
**평가도 멈췄고**(`live_signal_states` 마지막 쓰기 20:14:33.924, 다음 claim 이 20:30:00 bar)
**체결 관측도 멈췄다**(같은 창에서 872초 지연). 둘이 같은 창이고 **같이 풀렸다** — 한 번의 정지가
두 증상을 냈다는 뜻이다. 그 정지가 `requires_gap_resync` 를 열었고, 그것이 사망의 전제였다.

★**판정 불가 — 「이상 없음」이 아니다.** 워커 컨테이너가 2026-08-07 03:35Z 경 재생성돼 사망
시점 로그가 없다(`docker logs quantbridge-worker` 최초 줄이 재생성 시점). 라이브 OHLCV 는
`ts.ohlcv` 가 아니라 CCXT REST(`live_signal.py:2885`, `fetch_ohlcv` 300봉)라 DB 로도 역추적이
안 된다. ⇒ **다음 창에서 로그를 남긴 채 재관측한다.**

★**정정(2026-08-08 실측).** 서버에는 `.soak/logs` 자체가 존재하지 않는다.
`.soak/logs/follow.sh` 는 로컬 전용 비추적 스크립트였고 서버로 배포된 적이 없다. 따라서 이 BL 의
「다음 소크 창에서 로그를 남긴 채 재관측」 조건은 서버 소크에 대해 한 번도 성립하지 않았다.

이번 회차는 추적되는 `tools/scripts/soak-logs-follow.sh` 를 만들었다 — **466줄 신규**, 이번 브랜치 커밋
`32ea2a5d` 이며 systemd unit 승격 경로를 가진다. 서버 활성 세션은 현재 **0**이다. 이 장치를
서버 소크에 올린 뒤에야 같은 정지를 로그가 남아 있는 동안 재관측할 수 있다.

**Risk:** 🟡 [BL-622] 수리가 이 정지의 **사망 전이**는 막지만 **정지 자체**는 안 막는다.
17분 무평가 = 그 창의 신호를 안 낸다.

---

### BL-529

**Title:** 같은 Bybit uid 를 두 계정 행이 스윕해 청산 원장이 2배로 적재된다
**Category:** Trading / 데이터 위생
**Priority:** P2
**Trigger:** 전략 누적 지표를 신뢰해야 할 때
**Est:** S
**상태:** 🟡 부분 해결 — 스윕 uid dedup(BL-605)과 화면 문구는 구현됐다 — 잔여는 등록 시 uid 중복 경고와 이미 쌓인 거울 행/중복 계정 행 정리(사용자 승인). (2026-08-09 status-triage-mass 코드 대조)
**트리거 판정:** 미도래 — 동승 조건(전략 누적 지표를 신뢰해야 할 때) + [BL-477] 과 같은 사용자 결정. 거울 행 정리 경로가 2026-08-11 에 닫혔다 (2026-08-11 bl-703-partial-verdicts)
**출처:** 2026-07-28 live-outcome-parity 실측

**원인 / 영향:** `exchange_exits` 실측 — 계정 행이 2개(`0277c150` / `19a8166a`)인데 **둘 다 같은 Bybit uid** 를 가리켜 같은 청산이 계정별로 2행 적재된다. 한쪽은 32행 전부 `matched_order_id IS NULL` 이다.

- 세션 단위 표면은 **무해**하다(한 세션 = 한 계정).
- 전략 누적과 계정 진단에서 **`unattributed_count` 가 부풀려진다**(실측 37 중 다수가 거울 행).
- `aggregate_closed_pnl` 은 계정 스코프라 안전하지만, 계정을 안 거는 새 집계를 만들면 즉시 2배가 된다.

**권장 접근:** 등록 시 거래소 uid 중복을 감지해 경고하거나, 스윕을 uid 단위로 dedupe 한다. 화면은 그때까지 "계정 행마다 중복 적재될 수 있음" 을 명시한다(이번 스프린트에서 문구 반영).
**Risk:** 🟢

**🔁 재확인 (2026-07-29, live-close-completeness 리뷰):** 거울 행이 **실재로 재확인**됐다 — `exchange_exits` 분류 집계에서 `ours` **30행**과 `unknown` **30행**이 건수뿐 아니라 **net 합계까지 −27.6870 으로 동일**했다. 같은 청산이 계정 행 2개에 각각 적재된다는 BL 본문의 진단과 일치한다.

★이 확인은 live-close-completeness 플랜(W4)이 "등재 내용 보강만" 으로 약속했으나 **그 PR 에서 누락**됐고, 사후 Spec 리뷰가 잡아 여기 반영한다. 스코프를 줄인 게 아니라 **적어놓고 안 한 것**이므로 같은 누락이 반복되지 않도록 기록해 둔다.

---

### BL-661

**Priority:** P1
**카테고리:** Backend / trading (청산) · 운영 CLI
**Trigger:** 실자금 전환 전 필수 / 조건부 진입을 쓰는 세션을 내릴 때
**Est:** S
**상태:** 🟡 부분 해결 — 2026-08-10 guards-blind-spots 에서 **거짓 성공을 없앴다**(보고 + exit 3). 포지션 0 인데 미체결 조건부 진입이 있으면 `409 detail={"code":"resting_conditional_entries",…}` 이고 CLI 가 잔량을 찍고 **exit 3** 으로 끝난다. **취소는 미구현**이라 부분이다 — 권장 접근의 「그것을 취소하도록」은 [BL-669](#bl-669) 로 분리했다. 변이 6/6 red · 음성 대조 green
**트리거 판정:** 미도래 — 외생 조건(실자금 전환) + 동승(조건부 진입 세션을 내릴 때). 잔여인 「취소하도록」은 [BL-669] 로 분리됐고 그쪽은 **DEFERRED**(뒷절이 거래소 접촉 승인이다) (2026-08-11 bl-703-partial-verdicts)

**`flatten` 이 「이미 flat」을 내고 exit 0 하는데 조건부 주문은 남아 있다.**

`close_service.py:100-104` 는 `fetch_open_positions` 결과만 보고 비면 `409 no_open_position`
을 낸다. **미체결 조건부 진입 주문은 보지 않는다.** 그런데 운영 CLI
(`live_session_admin.py:383-387`)가 그 예외를 잡아 **`✓ 이미 flat 이다 (no_open_position).
주문을 내지 않았다.` 를 출력하고 `return`** 한다 — 종료 코드 **0**.

⇒ **조건부 주문이 살아 있는 채로 「정리 완료」로 읽힌다.** 그 주문은 나중에 트리거되어
아무도 보고 있지 않은 시점에 포지션을 연다.

★**이 레포는 같은 계열을 이미 겪었다** — 2026-08-08 `down` 이후 `FLAT=YES` 인데 엔진이 재무장해
`d655f560`(FOREIGN sell) + `8d4272fe`(ours buy)가 거래소에 남았고 `EXCLUSIVE=NO` 가 됐다.
그때는 `soak-restart.sh:288-304` 가 die 해서 드러났지만, **`flatten` 자신은 조용했다.**

**왜 지금 아픈가:** [BL-003] runbook §7 rollback 이 `flatten` → `status` 순서인데, `flatten` 이
거짓 성공을 내면 **실자금에서 조건부 주문을 남긴 채 「내렸다」고 판단**하게 된다. runbook 은
「`status` 의 `RESTING_CONDITIONAL` 을 반드시 눈으로 확인하라」로 **문서 방어만** 해 뒀다 —
코드 방어가 아니다.

**권장 접근:** `close_position` 이 포지션과 **조건부 주문을 함께** 보고, 포지션이 없어도
미체결 조건부가 있으면 그것을 취소하도록. 조회 계약은 이미 있다 —
`fetch_open_conditional_orders(creds, symbol, reduce_only=None)`
(`live_session_admin.py:242-244` 가 쓴다. ★`reduce_only=None` 은 협상 불가 계약이다).
CLI 쪽은 `no_open_position` 을 **성공으로 출력하지 마라** — 최소한 조건부 잔량을 함께 찍어라.

**Risk:** 🔴 실자금에서 고아 조건부 주문. 데모에서도 참이지만 손실이 가상이라 안 아팠다.

**출처:** 2026-08-09 bl003-mainnet-runbook (codex 적대 리뷰 발견 2 — 코드 대조로 확정)

---

### BL-774

**Title:** TradingView webhook 이 **body 기반 HMAC** 을 요구한다 — 동적 alert 본문에서 성립하는지 미확인
**Category:** Backend / Trading ingress
**Priority:** P2
**Trigger:** ★사용자가 실제 TradingView alert 로 webhook 을 연결하는 시점 · 또는 그 경로를 문서에 정본으로 올릴 때
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

**상태:** ⬜ Open — 2026-08-16 에 코드 축(body-HMAC + optional idempotency)만 확정. **TradingView 쪽 실측 미착수**
**트리거 판정:** 도래 — 다만 첫 step 은 코드 수리가 아니라 **실측 1건**이다 (2026-08-16 external-comparison)

### BL-822

**Title:** 거래 수 분모 모순 — detail API 가 num_trades 를 **open 포함(13)** 으로 덮어쓰는데 승률은 **완료(12) 기준** 그대로라 화면들이 서로 다른 숫자를 말한다
**Category:** Backend / Backtest serializer + FE 라벨
**Priority:** P2
**출처:** 2026-08-25 qa-sweep J3/J5 (온보딩 완주 실측 → DB·API 대조)

**증상 (실측, backtest `20128227`):** DB metrics = num_trades **12** · win_rate 2/12=16.67%. detail API 는 Sprint 31-E override(`backtest/service.py:825-847` ← `repository.py:366 count_trades_by_direction` = **open+closed**)로 num_trades/total_trades 를 **13** 으로 응답. 결과 — ⑴ 상세 「총 거래 수 13 · 승률 16.67%」 산술 불능(13×16.67%≈2.17) ⑵ 목록(`/backtests`)은 12, 상세는 13 — 같은 실행이 화면마다 다름 ⑶ 온보딩 결과 카드는 13 에 「**진입·청산이 완료된 건수**입니다」 거짓 라벨(`step-4-result.tsx:209`) ⑷ 상세 페이지 안에서도 「체결된 거래 13건」 vs 거래 분포 합 12.
**원인:** override 자체는 의도된 결정(BL-155 — FE 거래 목록 길이와 일치)이나, 승률·라벨·목록이 **완료 기준**을 유지해 분모가 갈라졌다.
**권장 접근:** 두 셈을 **이름으로 가르라** — 「거래 수(미청산 포함) N」과 「완료 거래 M(승률 분모)」를 각각 명시. 최소 수리 = FE 라벨 2곳(온보딩 카드 foot + 상세 지표 카드)과 목록/상세 표기 통일. BE 응답에 completed count 를 별도 필드로 주는 것이 정본 수리.

**상태:** 🔵 ACTIVE — 2026-08-25 qa-sweep 발견, 미수리
**트리거 판정:** 도래 (제품 핵심 축 「결과가 정직하게 보이는가」 직결)

### BL-823

**Title:** 새 전략 위저드 — **자기 세션의 자동저장 초안**에 「이어서 작성하시겠어요?」 복원 모달이 떠 편집을 차단한다
**Category:** FE / Strategy wizard
**Priority:** P2
**출처:** 2026-08-25 qa-sweep J4 (예제 로드 후 ~30초 내 무행동 발화 실측, Fast Refresh 리마운트 없음을 콘솔로 배제)

**증상:** `/strategies/new` 에서 첫 의미 있는 입력(타이핑·예제 로드) 직후, auto-save 가 만든 **지금 이 세션의** 초안을 복원 프롬프트가 「작성 중이던 초안」으로 오인해 blocking 모달이 뜬다. 기본 포커스는 「새로 시작」.
**원인:** `new-strategy-wizard.tsx:67-71` — `shouldPromptRestore = !promptDismissed && hasMeaningfulDraft` 에 「이 마운트에서 사용자가 이미 편집을 시작했다」 가드가 없다. `draft.ts:114 useDraftSnapshot` 이 `useSyncExternalStore` 라이브 구독이라 `useAutoSaveDraft`(`:79`) 의 쓰기를 즉시 되읽는다. 데이터 손실은 없음(「새로 시작」은 저장분만 삭제, 폼 유지 — `:175-178`).
**권장 접근:** 마운트 시점에 초안 존재 여부를 **한 번만** 평가해 프롬프트 게이트로 쓰거나, 이 세션에서 입력이 시작되면 `promptDismissed` 를 자동 set.

**상태:** 🔵 ACTIVE — 2026-08-25 qa-sweep 발견, 미수리
**트리거 판정:** 도래 (전략 등록 진입로의 상시 마찰)

### BL-824

**Title:** 취소 주문 드로어가 취소 시각을 「**체결 시각**」으로 적는다 — rejected 만 갈라놓은 라벨 분기에서 cancelled 가 빠졌다
**Category:** FE / Trading orders (+ BE 기록 의미론)
**Priority:** P2
**출처:** 2026-08-25 qa-sweep J7 (주문 63dea22b 드로어 실측 → DB 전수 대조)

**증상 (실측):** 상태 「취소」· 체결가/체결 수량 「—」 인 주문의 드로어가 「체결 시각 2026-08-14 09:37:49 UTC」를 표시. DB 전수 — cancelled **431/431** 이 `filled_at` 보유, 그중 부분 체결 **0건**. rejected 88/88 도 동일하나 그쪽은 이미 「실패 시각」으로 갈라져 있다.
**원인:** BE 가 종결 전이 시각을 `filled_at` 에 쓴다(rejected 는 `order_repository.py:941-945` 주석으로 문서화). FE 수리(2026-08-15 codex P1, [clock-fill-sweep])가 `order-detail-drawer.tsx:180` 에서 `state === "rejected"` **만** 「실패 시각」으로 분기 — cancelled 는 「체결 시각」 그대로.
**권장 접근:** 최소 수리 = 라벨 분기를 terminal-비체결 상태 전체로 확장(`cancelled` → 「취소 시각」). 정본 수리 = BE 가 cancelled/rejected 의 종결 시각을 `filled_at` 이 아닌 별도 컬럼(또는 null 유지)으로 — 기록 의미론 자체가 오염원이다.

**상태:** 🔵 ACTIVE — 2026-08-25 qa-sweep 발견, 미수리
**트리거 판정:** 도래 (표기 한 줄 수정으로 최소 수리 가능)

