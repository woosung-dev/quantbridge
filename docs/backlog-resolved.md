# QuantBridge — Refactoring Backlog · RESOLVED 본문

> ★**이 파일은 원장의 일부다.** `docs/backlog.md` · `docs/backlog-deferred.md` 와 **한 벌로**
> `tools/scripts/bl-audit.sh` 가 읽는다 — 섹션 수·판정 수는 **세 파일의 합계**이고,
> 인덱스 표 행(`| [BL-nnn](#bl-nnn) | … |`)은 `docs/backlog.md` 에 남아 있다.
> 즉 3면 정합(섹션 · 인덱스 표 · roadmap)이 **세 파일에 걸친다.**
> ★**2026-08-18 — 분할 규칙에 집행처가 생겼다**(`bl-audit` 「파일 배치」 축). 그 전까지 이 규칙은
> 산문이었고, 그래서 2026-08-16 이후 닫힌 **13건이 `backlog.md` 에 그대로 쌓여 있었다.**
>
> ★**왜 갈랐나** ([BL-779], 2026-08-16). 한 파일 안에 수명이 다른 것이 섞여 있었다 —
> RESOLVED 본문이 열린 항목과 같은 파일에 있어 `docs/backlog.md` 를 여는 비용을 상시로 올렸다.
> `docs/README.md` 의 수명 분류 원칙(reference / decisions / dev-log / archive)을 원장 안에서
> 처음 적용한 것이 이 분리다.
>
> ★**이동은 기계적이었다 — 본문은 한 글자도 고치지 않았다.** H2 묶음과 섹션 순서도 원본 그대로다.
> 직전 원문(단일 파일) = `git show 90bca8cb:docs/backlog.md`.
>
> ★**여기에 새 항목을 손으로 적지 마라.** 항목이 RESOLVED 가 되면 `docs/backlog.md` 의 본문을
> 이 파일로 **옮기고** 표 행은 원본에 남긴다. 같은 id 를 양쪽에 두면 `bl-audit` 이
> 「중복 섹션 헤더」로 red 를 낸다(뒤 섹션이 앞 섹션 판정을 덮어쓰기 때문이다).

## P1 — Risk mitigation / 알려진 broken bug 패턴 재발 방어

### BL-022

**Title:** Golden expectations 재생성 (skip #1 해소)
**Priority:** P1
**상태:** ✅ **Resolved** (2026-08-07 backtest-fidelity)

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-024

**Title:** real_broker E2E 본 구현 (nightly cron)
**Category:** Test infra
**Priority:** P1
**Trigger:** Bybit Demo credentials + seed data 첫 준비 시
**Est:** L (8h+)
**출처:** CLAUDE.md Sprint 10 Phase C — "실제 E2E 로직은 nightly 첫 실행 시 credentials + seed data 하에 작성 예정"

**상태:** ✅ **Resolved (2026-08-14, `stage/real-broker-e2e` — 로컬 축).** 실거래소 leg 이 돌았다 — Bybit demo linear perp `BTC/USDT:USDT` 실시장가 1건 → 프로덕션 dispatcher 배선 → 발주 → watchdog `_async_fetch_order_status` 로 `filled` 확정 → 2층 하네스 청산 → **거래소 조회 0 포지션**(정본 경로 `nightly-real-broker-local.sh` = `PASS (skip 0건)`). ★★★**원장 처방 2건 반증** — ⑴ 「**Spot** BTC/USDT」는 하네스를 **거짓 안전망**으로 만든다(flat 판정이 `fetch_open_positions` 인데 spot 엔 포지션이 없다) ⇒ linear perp. ⑵ `db_session` 금지(savepoint commit 이 하네스의 별도 엔진에서 안 보인다). ★★**2층 하네스는 그때까지 한 번도 작동한 적이 없었다**([LESSON-109]) — skeleton skip 으로 REGISTRY 가 늘 비었고, 첫 타깃에 전건 `undecidable`. 원인 = `_execute_order_now` 만 DSN 을 바꿔 **청산이 개발 DB 를 열었다** ⇒ `_test_dsn_in_effect` 공유. 증인은 거래소다 — 수리 전 rc=1+**long 0.001 잔존**, 후 rc=0+**0건**. ★부수: `_verdict` 가 rc 0 을 PASS 로 접어 **5일 연속** skip 을 「통과」로 적고 있었다. **잔여(별건)** = HTTP webhook 층 · CI 축.
**트리거 판정:** ~~도래 — … 잔여 차단(지리 403)은 트리거가 아니라 실행 경로 문제이고 로컬 스케줄로 첫 통과를 봤다 (2026-08-10 bl-trigger-triage)~~
→ ★★★**2026-08-11 ledger-truth 재정의 — 「지리 403」은 더 이상 차단자가 아니고, 진짜 차단자는
「소크와 계정 배타」다. 이 BL 은 소크와 상호배타이며 계정 분리 없이는 영구 SKIP 이다.**

**근거는 우리 코드가 직접 적고 있다** — `tools/scripts/nightly-real-broker-local.sh:135`:

```
_verdict SKIP "소크가 돌고 있다 (활성 세션 ${ACTIVE}개) — 같은 Bybit 계정이라 포지션을 공유한다" 0
```

**로컬 nightly 8회 실측** (`~/Library/Logs/quantbridge/run-*.log`, 2026-08-04~08-10):
**SKIP 4** (전부 위 사유 · 활성 세션 1개) · **BLOCKED 2** (`quantbridge-db` 무응답) ·
**PASS 2**. ⇒ **8회 중 6회가 실거래소를 1바이트도 재지 못했다.**

★★**그 「PASS 2」도 실거래소 검증이 아니다** — 두 런의 pytest 요약이 **둘 다**
`1 passed, 1 skipped` 다(08-10 03:00 KST · 08-04 23:34). 본 섹션이 「로컬 스케줄로 이미 첫
통과를 봤다」고 적은 것은 **하네스 통과**이고, 같은 섹션의 「실거래소는 1바이트도 검증되지
않았다」가 여전히 참이다. ⇒ `_verdict` 가 rc 만 보고 PASS 를 찍는 것 자체가 별건 결함이다
(SKIP 도 **종료 코드 0** 이다 — `:135` 마지막 인자).

★**이것은 시간이 풀 수 없다.** [BL-003] 이 긴 소크 창을 노리는 한 활성 세션은 계속 1개 이상이고
`:135` 는 매번 발화한다. **2026-08-11 사용자 결정: 2번째 Bybit demo 계정을 발급하지 않는다**
⇒ 이 BL 은 「계정 분리」가 선행 조건인 **DEFERRED** 성격이다. 판정어 변경은 3면 정합을 함께
움직여야 하므로 별건으로 남긴다 — 지금 고치는 것은 **차단 사유의 거짓**이다.

**권장 접근:** 자격증명 2종 발급 후 실주문 leg 구현. ★체결 확인을 polling 으로 짜지 마라 — Bybit demo 시장가는 `create_order` 응답에서 `submitted` 로 오고(`providers.py:_map_ccxt_status`) 체결 확정은 WS 가 한다. `_async_fetch_order_status`(`tasks/trading.py:685-707`)를 명시적으로 태우는 설계여야 한다.

### ★2026-08-04 — 자격증명을 넣자 **진짜 차단이 드러났다** (실행 경로 = 로컬 스케줄)

**키 2종은 배치 완료다** — `apps/api/.env.local` + GitHub repo secret 동명 2종. 출처는
`trading.exchange_accounts` `19a8166a`(label `bybit demo`, `exchange_uid` **558689281**)의 거래 가능 키
(같은 uid 를 두 계정 행이 공유한다 — [BL-517](#bl-517)). ⇒ 「키 미발급」은 더는 차단 사유가 아니다.

**그러자 이 워크플로 역사상 pytest 가 처음 실행됐고**(직전 102회는 전부 `alembic` 에서 사망)
이렇게 실패했다 — nightly run `30917972735`:
`403 Forbidden — The Amazon CloudFront distribution is configured to block access from your country`
(`api-demo.bybit.com/v5/market/instruments-info`).

**대조 실측(같은 키, 같은 시각)** — GitHub Actions 러너 `fetch_balance` **403 Forbidden** /
로컬(한국) ✅ USDT 190,352.88 · `load_markets` ✅ 3,091 마켓. ⇒ **키 문제가 아니고 코드로 못 고친다.**
판정은 이슈 #540.

★**사용자 판정(2026-08-04) = B 안, 로컬 스케줄.** GitHub `schedule:` 은 껐고
`tools/scripts/nightly-real-broker-local.sh` 가 launchd 로 매일 03:00(로컬)에 돈다
(`--install` / `--status` / `--uninstall`). 로그 = `~/Library/Logs/quantbridge/`.
★A 안(self-hosted 러너)은 **폐기가 아니라 보류** — CI 통합이 필요해지면 그때 재판단한다.

★**판정 낱말 4종** — `PASS` / `SKIP`(의도된 건너뜀, exit 0) / `FAIL`(exit 1) / `BLOCKED`(전제
미충족 = **측정 못 함**, exit 2). **exit 0 이 「검증됐다」를 뜻하지 않는다** — SKIP 도 0 이다.

★**가드 5종은 주입으로 판별력 5/5 를 증명했다** — 메인 체크아웃 아님 · 자격증명 빔 · DB 무응답
(「판정 불가」를 「이상 없음」으로 접지 않는다) · **소크 충돌**(같은 uid 라 포지션 공유 ⇒ SKIP) ·
지리 차단(CloudFront 403 ⇒ BLOCKED) · pytest 실패(⇒ FAIL).

★**첫 실행 실측(2026-08-04 23:34 KST) = `1 passed, 1 skipped`** — `fetch_balance` 가 실제 Bybit demo
에서 통과했다. 이 레포에서 스케줄 실행으로 실거래소 단언이 통과한 **첫 사례**다. ⇒ 위 상태 줄의
「실거래소는 1바이트도 검증되지 않았다」는 이 시점부터 **더는 참이 아니다.** 나머지 1건은 skeleton
skip 이고 그게 실주문 leg 의 본 작업이다.

**착수 순서 (고정):**

1. ★**충돌 가드 먼저.** nightly 는 03:00 에 도는데 그 시각 소크가 돌면 **같은 계정의 포지션을 서로
   본다**. 진입 **전에** 활성 라이브 세션을 확인하고, 있으면 「소크가 돌고 있다」로 **명시적 skip**.
   없으면 nightly 가 소크 포지션 때문에 오탐으로 빨개진다. 진짜 격리(별도 서브계정)는 소크 재개
   시점의 별도 판단이다.
2. **적대 검증 3건을 먼저 닫아라** — 실주문이 이 코드를 처음 실행시키는 순간 드러난다.
   **F3** `tests/real_broker/_harness.py` 함수 본문 **93% 미실행**(사용 테스트 0개 — 깨진 게 아니라
   **미검증**) · **F12** `flatten_one` 이 `submitted`→`filled` **대기 없이** `fetch_open_positions` 를
   불러 **거짓 residual** 가능(위 §권장 접근의 `_async_fetch_order_status` 설계가 이것이다) ·
   **F6** 계약 감사가 스텝 **순서**·`Upload pytest output` 존재·`timeout-minutes` 를 안 본다.
3. 시나리오 **S2~S13** 구현. 최소 수량으로 — 비용이 아니라 **신호**가 목적이다.
4. ★**멱등·자기정리.** 실패해도 거래소에 포지션·대기 주문을 남기지 마라. `stop` → `flatten` 순서
   계약. **세션 비활성화는 아무것도 flat 하지 않는다** — 이 레포가 3회 덴 함정이다.

---

### BL-025

**Title:** autonomous-parallel-sprints 스킬 patch (BUG-1/2/3 → LESSON-007/008/009)
**Priority:** P1 (다음 자율 병렬 sprint 시 재발 방지)
**상태:** ✅ Resolved — BUG-1(--git-common-dir)·BUG-2(full SIG_ID)·BUG-3(plan worktree-only) 세 패치가 스킬 repo 에 모두 반영돼 있다 (2026-08-09 status-triage-mass 코드 대조)

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-026

**상태:** ✅ **Resolved (2026-08-15 clock-fill-sweep)** — ★**코드 변경 0줄이다. 지목된 작업이 이미 끝나 있었다.** 원장이 가리킨 `test_trust_layer_parity.py:418` 은 데코레이터가 아니라 **묘비명 주석 한 줄**이고, 껍데기 테스트와 `@pytest.mark.skip` 은 **2026-08-11 에 이미 삭제**됐다. 레포 전체에 무조건 `@pytest.mark.skip` **실코드 0건**(히트 2건은 둘 다 과거형 기록 주석). 오라클은 `test_mutation_oracle.py` 로 온전히 이관돼 `@pytest.mark.mutation` **8건**(`:149,181,214,255,298,330,378,416`)이 ADR-020 §10.1 의 「8 mutation」 정족수와 일치한다. **AC 실행 확인**: `uv run pytest --run-mutations tests/strategy/pine_v2/test_mutation_oracle.py` → **7 passed + 1 xpassed (skip 0건, 211.72s)**. ⇒ 이 BL 이 남긴 것은 코드가 아니라 **자기 자신의 낡은 서술**이었다(아래 제목·Est·출처 정정). 종전 근거 `docs/roadmap.md:168` 도 함께 갱신했다.
★★★**2026-08-11 실측 — 제목·Est·권장 접근이 셋 다 반증됐다.**

- **제목의 「skip #4-7, #9-15」(=12건)은 출처가 사라졌다.** `**출처:** TODO.md L20-22` 인데
  `docs/TODO.md` 는 `fcc36bf7`(#485, docs 구조 재편 42→12)에서 **삭제**됐다. 그 번호가 어느
  테스트를 가리켰는지 **레포 어디에도 없다** ⇒ 「12 skip 일괄 활성화」는 대상 집합이 없다.
- **실측 무조건 skip 은 6건이고 그중 mutation 관련은 1건뿐이다** —
  `tests/strategy/pine_v2/test_trust_layer_parity.py:418`. 나머지 5건은
  `test_metrics_auth.py`(3) · `test_runs_error_response.py`(2) 로 **fixture env 부채**이고
  mutation 과 무관하다. `skipif` 는 21건인데 **mutation 게이팅에 쓰이지 않는다.**
- **진짜 게이트는 skip 데코레이터가 아니라 `tests/conftest.py:138-148` 의 마커**
  (`skip_mutation`)다 ⇒ `:418` 데코레이터는 그 위에 겹친 **죽은 껍데기**이고,
  「활성화」의 대상은 fixture 가 아니라 **그 껍데기 제거**다.
- ⇒ **Est 「S (1-2h)」는 근거가 없다.** 12건이 아니라 1건이고, 작업은 「활성화」가 아니라
  「껍데기 제거 후 `--run-mutations` 로 실제로 도는지 확인」이다.

**트리거 판정:** 도래 — 트리거 줄 자신이 「✅ 2026-04-23 완료, 회귀 PR 생성 필요」로 도래를 적었다 (2026-08-10 bl-trigger-triage). ★2026-08-11 유지 — 도래는 맞지만 **범위 재정의가 선행**이다.

**Title:** ~~Mutation fixture 활성화 회귀 검토 (skip #4-7, #9-15)~~ → **Mutation Oracle 이 `--run-mutations` 로 실제로 도는지 확인** (2026-08-15 정정 — 「12 skip 일괄 활성화」는 **대상 집합이 없었다**)
**Category:** Trust Layer / Test infra
**Priority:** P1
**Trigger:** Stage 2c 2차 fixture 활성화 후 (✅ 2026-04-23 완료, 회귀 PR 생성 필요)
**Est:** ~~S (1-2h)~~ → **XS (실행 1회)** — 코드 변경 0줄로 끝났다 (2026-08-15)
**출처:** ~~TODO.md L20-22~~ → **dangling.** `docs/TODO.md` 는 `fcc36bf7` 에서 삭제됐다 — 원문은 git history (2026-08-15 확인)

**권장 접근:** Path β Stage 2c 2차 mutation 8/8 도달 후 12 skip 가 활성화 가능 상태. 회귀 PR 1건으로 일괄 활성화 + 1주 nightly green 후 안정화.

---

## P2 — Hardening / 건강도 작업

### BL-195

**Title:** qb-form-slide-down animation 영구 truncation (max-height 600px + overflow-hidden, 600px 초과 시 hint list 잘림)
**Priority:** P2
**상태:** ✅ Resolved — truncation 원인이던 to{max-height:600px} 가 커밋 188273c9 에서 제거돼 현재 keyframe 에 캡이 없다. (2026-08-09 status-triage-mass 코드 대조)

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-363

**Title:** stress*test `StressTestService.\_execute*\*`4-method boilerplate 추출
**Priority:** P2
**상태:** ✅ Resolved — `\_RunContext`+`\_load_run_context`로 config 단일화, CA/PS 는`\_execute_grid_sweep` 위임 — 권장 처방 전부 구현됨 (2026-08-09 status-triage-mass 코드 대조)

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-392

**Title:** stress_test CA/PS "2D grid sweep" DTO 8-site 평행 정의 통합 (engine dataclass + serializer + OutSchema)
**Priority:** P2
**상태:** ✅ Resolved — 공유 grid_result.py(GridSweepMetricsCell/Result)+serializer 1쌍+schema 1클래스+C4 상수 SSOT+golden 라운드트립 테스트까지 전부 구현됨. (2026-08-09 status-triage-mass 코드 대조)

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-460

**Title:** 백테스트 마진 게이트가 **gross 자본**으로 판정 — 수수료·슬리피지 차감 전 `running_equity` 사용
**Priority:** P2
**상태:** ✅ **Resolved** (2026-08-09 btfix) — 접근 **(a)**. 게이트 전용 net 누적치 `StrategyState.gate_equity` 신설, `_can_afford_entry`·`_open_trade` 만 본다. `running_equity` 는 **gross 유지** → `compute_qty`·Pine `strategy.equity` 불변 → L=1 byte-identity(golden **무변경** 실측). 비용률 = `fees + slippage` 를 `taker_cost_rate` 로 배선(기본 0.0 = 회귀 0, leverage≤1 은 no-op). 오라클 `test_margin_gate_net_equity.py`·`test_margin_gate_cost_wiring.py` — 되돌려 **red 8/8**, 옛 코드는 qty=17 을 **허용**하고 신규는 거절(qty=15 는 양쪽 허용). ★FE 배너 "차감 전 자본으로 판정" 이 거짓이 돼 정정. **잔여** ① 사이징(`percent_of_equity`)은 여전히 gross(BL 이 배제한 축) ② ★게이트가 TP 청산도 taker 로 쳐 **과대**계상(리포트는 BL-104 이후 maker) — 막는 방향이라 fail-closed. 초판 주석의 "모든 체결 taker" 는 **낡은 grounding** 이라 정정(`d570b2ea`).

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-517

**Title:** stand-down 축이 거래소 uid 가 아니라 DB 계정 행 id 다 — 같은 계정을 두 번 등록하면 우회된다
**Priority:** P2
**상태:** ✅ Resolved — 2026-08-10 close-ownership-axis. `account_exclusivity._ownership_scope` 를 모듈 함수 `ownership_scope_ids` 로 추출해 stand-down 이 **재사용**한다(새 가드를 만들지 않았다 — 아래 반박 1 이 지목한 착수 지점 그대로). `_resolve_current_position` 이 `account_repo` 를 받아 uid 형제 행 전량의 활성 세션을 본다. `list_active_by_account` 자체는 **안 건드렸다**(소비자 3곳 중 stand-down 만 넓은 축이 필요하다) — 호출부에서 넓혔다. AST def-use 오라클이 요구하는 `stand_down_reason` 단일 `Assign` + `IfExp` 구조는 그대로다. 시험은 `exchange_uid` **한 필드만** 다른 양성/음성 쌍이고 `_resolve_current_position` 을 통과하는 경로로 잰다 — 순수 함수를 직접 부르면 배선 변이가 green 으로 탈출한다(`backend/AGENTS.md` §10-2). 변이 4/4 red(배선 변이 포함, 도달 확인)

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-662

**Title:** `/dashboard` 가 로컬 배럴로 렌더하지도 않는 컴포넌트 9종을 끌어온다
**Priority:** P2
**상태:** ✅ Resolved (2026-08-09 fe-perf-quartet) — 직접 경로 3줄로 `/dashboard` 클라이언트 JS **1,140,321 B → 954,447 B (−185,874 B · −181.5 kB · −16.3%)**, 청크 17→13, 9종 문자열 지문 **8/9 → 0/9**, `react-hook-form` 전이 의존 **제거**. 양성 대조 `/trading` 은 8/9·바이트 불변

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-663

**Title:** 트레이딩 코크핏이 5초마다 §01~§08 전 서브트리를 재조정한다 (`useNowTick`)
**Priority:** P2
**상태:** ✅ Resolved (2026-08-09 fe-perf-quartet) — KPI 카드를 `unrealized-pnl-kpi.tsx` leaf 로 내려 5초 틱 **과 WS ticker 구독을 함께** 가뒀다. 회귀 = 5초 3회 전진 뒤 §03 자식 렌더 수 불변(변이 M4 로 빨간 것 확인). ★본문의 인과는 **불완전했다**(아래)

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-664

**Title:** 코크핏 새로고침 버튼이 앱 전체 쿼리 캐시를 무효화한다
**Priority:** P2
**상태:** ✅ Resolved (2026-08-09 fe-perf-quartet) — 이 화면이 소비하는 **네** 도메인 루트만 무효화한다(`trading`·`live-sessions`·`strategies`·`alert-rules`). 회귀 = 호출 4회·각 인자가 팩토리 출력·무인자 호출 0회(변이 M1·M5 로 빨간 것 확인)

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-707

**Title:** authed e2e 실패 메시지가 「API 도달 불가」를 「데이터 없음」으로 오지목한다
**Category:** 테스트 / 진단 품질
**Priority:** P2
**Trigger:** authed e2e 를 다시 손댈 때 / 같은 오진이 재발할 때
**Est:** S
**상태:** ✅ **Resolved** (2026-08-14 gate-surface-close) — ★**원장 처방의 기전이 착수 전 반증됐다.** 「`NEXT_PUBLIC_API_URL` 로 1회 fetch 하는 도달성 프로브」는 이 사건에서 **정확히 오답을 낸다** — 그 변수는 `Makefile:380` 이 **Next dev 프로세스에만** inline 주입하고 `playwright.config.ts` 에 dotenv 로딩이 **없어** `pnpm e2e:authed` 는 못 받으며, fallback 은 `:8000` 인데 **2026-08-12 그때 `:8000` 은 살아 있었다**. 표면도 절반이었다 — 단정문은 4개가 아니라 **7개**이고 도달 가능 test 는 **≤6**, 실제 red 는 **12** 였다(나머지는 무문구 타임아웃, 그리고 `authed-tier-c-cockpit.spec.ts:16,38` 은 BE 가 죽으면 오히려 **green**).

⇒ 채택한 처방은 ① **도달성 축을 `transportFail`(=`requestfailed` 갈래)로 신설해 단언**한다. ★초판은 기존 `subresourceFail` 을 그대로 썼는데, 그것은 `>=400` **응답까지** 세므로 레포가 이미 정상으로 문서화한 401/403·429 에 발화한다 — 리뷰 2축(codex·spec)이 독립 수렴해 P1 로 잡았고, **수리 전 트리로 돌린 스위트 2회가 `/strategies`·`/strategies/new` 에서 실제로 오탐을 냈다**(BE 는 살아 있었고 단독 실행은 통과). **응답이 왔다는 것 자체가 도달의 증거**이고 [BL-707] 이 본 신호는 응답이 아예 없는 `ERR_CONNECTION_REFUSED` 였다 ② `EXPECTED_CONSOLE` 에서 **`/net::err_/i` 제거** — 109건을 `hardFailCount` 에서 지운 **침묵의 진짜 출처**가 문구가 아니라 이 allowlist 였다 ③ 신규 setup 프로젝트 `setup-authed-reachability` 를 `chromium-authed` 만 물리게 해 **전량 abort** ④ `probeCount > 0` 단언으로 「0건 = 관측 못 함」이 초록으로 새는 것 차단(§8.6).

**검증 (CONTROL 직접 실측 — 워커는 샌드박스에서 브라우저·`uv` 가 막혀 둘 다 미실행이었다):** **양성** = BE 내림 → 도달성 setup **1건만** red 이고 **83건 abort**(16.0s). 문구 = 「백엔드 도달 불가. 브라우저 실측: 페이지 응답 비정상 0폭, 서브리소스 실패 **16건**. 대상 호스트: localhost:8102」 — `mise run seed` 를 **한 번도 말하지 않는다**. **음성 대조** = BE·FE 짝 맞춤 → **86 passed (4.7m)**, 신규 단언 **무발화**(오탐 0). ★종전 「12건이 각자 다른 거짓말」이 **1건의 참말**로 접혔다.

**★측정 중 같은 병을 2회 더 밟았다 (환경 축, → `status.md` ⓻ 환경 표):** ⑴ 슬롯 2 의 `:3102` 에 **남의 앱**(`Nexus Admin`)이 떠 있었다 — `global.setup.ts:53-66` 의 sign-in status 프로브가 「이 포트에 다른 앱이 떠 있을 수 있다」로 **정확히 말했다**. ⑵ 포트를 옮기자 이번엔 **CORS** 가 막았다 — `mise run be-isolated` 가 `FRONTEND_URL` 을 슬롯 FE 포트로 굳혀 띄우므로 FE 를 다른 포트로 올리면 BE 가 그 origin 을 거부한다(`allow-origin: :3102` 만 응답 · preflight **400**). ★**그때 신규 프로브가 발화했고 그것은 오탐이 아니라 진성 검출이었다** — 화면에서는 이것도 「데이터 없음」으로 보인다.
**트리거 판정:** ~~도래 — 발견 회차가 곧 착수 가능 시점이고 대상 파일도 확정돼 있다~~ → **2026-08-14 완료.** 도래는 옳았고 **대상 파일이 확정돼 있다는 것이 처방이 옳다는 뜻은 아니었다** — 실제 표면은 적어 둔 파일 2개보다 넓었다
**출처:** 2026-08-12 surface-demo-pack (authed 12건 red 의 귀속을 정하다 발견)

**원인 / 영향:** `pnpm e2e:authed` 12건이 이렇게 실패했다:

```
Error: /trading 데이터 전제 미충족 — 등록된 거래소 계정이 없다. /trading 이 빈 상태만 그린다 (`mise run seed`)
Error: 완료된 백테스트 상세 링크를 찾지 못했다 — 캐논 감사가 볼 원장이 없다 (`mise run seed`)
Error: 완료 optimizer run 상세 링크를 찾지 못했다 — 완료 run 시딩 필요
Error: 완료 상태 백테스트를 목록에서 찾지 못했다 (백엔드 8000 에 완료 백테스트 시딩 필요)
```

지시대로 `mise run seed` 를 돌렸더니 **전건 「이미 존재」**(전략 스킵 3 · 실행 스킵 6)였다. DB 실측도
같았다 — 한 사용자가 전략 3 · **완료 백테스트 7** 을 소유하고 있었다.

진짜 원인은 **백엔드가 `:8100` 에 없었던 것**이다. `mise run fe-isolated`(`:3100`)는
`NEXT_PUBLIC_API_URL=:8100` 을 쓰는데 떠 있던 BE 는 `mise run be`(`:8000`)였다. 브라우저 콘솔에
`ERR_CONNECTION_REFUSED` **109건**이 찍혀 있었고, `mise run be-isolated` 로 `:8100` 을 띄운 뒤
**authed 84/84 green · 콘솔 error 109 → 0** 이 됐다.

★**「데이터가 없다」와 「데이터를 못 가져온다」는 화면에서 똑같이 비어 보인다.** 단정문이 빈
목록을 보고 원인을 **추측해서** 적으면, 그 추측이 다음 사람의 30분을 가져간다.

**권장 접근:** 그 단정들 앞에 **API 도달성 프로브**를 둔다 — `NEXT_PUBLIC_API_URL` 로 1회 fetch
하거나 콘솔의 `ERR_CONNECTION_REFUSED` 를 세고, 도달 불가면 **시딩이 아니라 그 사실**을 말한다
(`API 도달 불가: <url> — BE 가 떠 있는지 확인해라 (mise run be-isolated)`). 도달 가능한데 비어 있을
때만 시딩을 지목한다.

**Risk:** 🟡 프로덕션 무해. 다음 세션의 오진 비용이 위험이다.

---

### BL-708

**Title:** `design-canon-calibration` 의 대비 측정이 회차마다 다른 파일에서 실패한다 (「하드 실패 0」 계약이 새는 창)
**Priority:** P2
**상태:** ✅ Resolved (2026-08-12 harness A회차 `feat-bl708`) — 권장 접근 ⑴ 채택 · ⑵(WARN 강등) **기각**. ①**원인이 반증됐다** — 반올림이 아니라 **원격 폰트 404**다. `NavProbe.subresourceFail` 를 먼저 계측하자(계측 전 3회는 19벌 출력이 status/examined/canon 까지 전건 동일해 갈리는 축이 **0**이었다) 계측 후 red 2회에서 갈린 것은 화면·폭뿐이고 정체는 같은 `fonts.gstatic.com` archivo woff2 404 → 콘솔 에러 → hardFail 이었다. ②처방은 「**file:// 대상만 hermetic**」 — `auditUrl` 이 대상 스킴으로 갈라 커밋된 정적 산출물일 때만 비-file 요청을 goto 전에 빈 200 으로 봉인하고 봉인량을 `NavProbe.sealed` 로 리포트에 싣는다(`subresourceFail=0` 을 「네트워크 멀쩡」으로 **오독하지 않게**). 앱 축은 코드 경로조차 안 지난다 — http 5 라우트 실측 전 폭 `sealed=0` 이고 404 프로브의 진짜 `subresourceFail=1` 은 그대로 관측된다. ③판정 계약을 spec 상단에 명문화하고 `assertCalibrationContract()` 한 곳으로 합쳐 **도달 증거**(4폭 status=200 · minExamined>0 · 로컬 subresourceFail=0 · sealed>0)를 함께 단언한다 — 변이 `widths:[1440,375]` 에서 종전 계약은 **초록**이고 새 단언만 red 였다. BL 이 요구한 수용 기준(같은 커밋 N회가 같은 답)은 독립 프로세스 3회 rc=0/0/0 · `22 passed`×3 · ANSI 제거 후 출력 전문 동일 · 최저 대비 4.92/5.41/5.44 고정으로 충족.

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-709

**Title:** 전략 목록 RSC prefetch 가 URL 정렬을 안 읽어 정렬 링크마다 클라이언트 왕복이 하나 더 든다
**Priority:** P3
**상태:** ✅ Resolved — 2026-08-13 step 1~3에서 정렬 화이트리스트와 정규화기를 `features/strategy/sort.ts` 1벌로 공유하고, Next 16 URL `searchParams` 결과를 RSC prefetch·client query/queryKey·select에 일치시켰다. AC의 typecheck/lint/전체 테스트·단일 상수·data-testid·query 정합 검증을 통과했다.

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

## P3 — Nice-to-have / 컨벤션 정합

### BL-306

**Title:** `~/.claude/CLAUDE.md` §5 한국어 콜론 종결 lint mechanism 도입
**Priority:** P3
**상태:** ✅ Resolved (기각) — 2026-08-10 backtest-submit-fix. **전제가 실측으로 반증됐다.**

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-307

**Title:** `~/.claude/CLAUDE.md` §6 한국어 file header lint + 누락 70 file backfill
**Priority:** P3
**상태:** ✅ Resolved — 2026-08-10 bl-307-header-lint. `scripts/header-audit.sh` 신설(BE·FE 공용 1벌) + 위반 **48 → 0** + pre-commit·CI 배선. 하네스 14/14 · 변이 6종 전건 판별.

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-397

**Title:** ~~백테스트 리포트 섹션 **탭** URL 딥링크 (`?section=`)~~ → **재기술: 10개 섹션 중 9개에 앵커 `id` 가 없다**
**Priority:** P3
**상태:** ✅ Resolved — 2026-08-10 fe-shareable-urls. 앵커 10개 + 상단바 보정 + 마운트 1회 해시 재조정. ★**재기술된 처방마저 반증됐다** (아래 종결 절).

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-405 — ❌ CLOSED: not-a-bug (오라클 전제 오류, 2026-07-12 재분류)

**Title:** ~~pine_v2 bool 시리즈 na→False 실체화 — 워밍업 스퓨리어스 시그널~~ → **재분류: 엔진이 TV 정답, 버그 아님**
**Priority:** ~~P2~~ → **CLOSED**
**상태:** ✅ Resolved — ❌ CLOSED: not-a-bug (2026-07-12 재분류). 2026-08-09 backlog-sweep 에서 **상태줄만** 추가했다. 코드 0줄.

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-462

**Title:** 백테스트 목록 Sharpe 정렬이 신·구 컨벤션을 섞어 센다
**Priority:** P3
**상태:** ✅ Resolved (2026-08-11 gate-freshness) — 정렬 결함 자체는 ledger-truth(`1d4d7e0b`)의 `_sharpe_sort_criteria` 등급 정렬(= 권장 접근의 「분리」안)이 이미 닫았고, 이 회차는 낡은 상태줄·FE 고지를 실측으로 정정하고 잔여 주장 2건(재계산·NULL화)을 코드로 기각했다.

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-504

**Title:** ~~ADR-013 / ADR-019 가 존재하지 않는데 진입 문서 4곳이 가리킨다~~ → **ADR-013 인용이 죽은 경로를 가리킨다 (019 는 실재)**
**Priority:** P3
**상태:** ✅ Resolved (2026-08-09 backlog-sweep) — 인용 4곳을 **git tombstone 경로**로 교정. 소급 ADR 작성은 [BL-658] 로 분리. 코드 0줄.

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-514

**Title:** stand-down 이 발화한 것은 알 수 있어도 **왜** 발화했는지는 알 수 없다
**Priority:** P3
**상태:** ✅ Resolved — stand_down 사유가 qb_live_conditional_divergence_total{event,reason} 과 렌더되는 로그 extra 로 둘 다 노출된다(BL-561 포맷터). (2026-08-09 status-triage-mass 코드 대조)

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

## Cross-reference

### BL-413

**Title:** 주문 상세 조회 배선 — BE `GET /orders/{id}` 기존재하나 프로토타입 screen-11 에 상세 affordance(행 확장/드로어) 부재로 defer
**Category:** Frontend / orders
**Priority:** P3
**Trigger:** 주문 상세 화면/드로어가 디자인 캐논(프로토타입)에 추가될 때
**Est:** S (2-4h)
**상태:** ✅ **Resolved (2026-08-15 clock-fill-sweep)** — 주문 상세 드로어를 넣었다. ★**단건 API 배선을 만들지 않았다** — `trading/router.py:296-313` 목록이 단건(`:316`)과 **동일한 `OrderResponse`** 를 내므로 행 객체를 그대로 넘긴다(`getOrder`/`useOrder`/`tradingKeys.detail` 신설 0건). `sheet.tsx` + `delete-dialog.tsx:28` 의 `useMediaQuery` 분기(≤768px Sheet / 그 위 Dialog)를 복제했고 `orders/error.tsx`(AGENTS.md §6 의무, 없었다)를 함께 넣었다. ★**적대 리뷰가 금융 오표시 2건을 잡았다**: 거부 주문도 `filled_at` 이 채워지므로(BE `mark_rejected`) 라벨을 상태별로 갈랐고, 손익은 목록과 같은 SSOT(`displayRealizedPnl`)를 쓴다 — 직접 읽으면 rejected 에 남은 pine_v2 **추정치**가 확정 손실처럼 보인다. ★선택 상태는 **객체가 아니라 id** 로 든다(5초 polling 이 갱신한 값이 드로어에 반영된다). 실브라우저 e2e 로 드로어 개폐 + 취소 버튼 전파 차단 확인. (종전 서술: FE 에 getOrder 배선도 상세 드로어도 없고 프로토타입 screen-11 에도 상세 affordance 가 없어 Trigger 자체가 미도래. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-23 functional-parity 스프린트 defer 판정

**원인 / 영향:** 원장 행이 이미 전 필드(오류 메시지 전문 포함)를 인쇄해 실해는 낮음. 디자인 근거 없는 UI 신설은 캐논 위반이라 배선만 보류.

**권장 접근:** 프로토타입에 상세 affordance 가 생기면 `GET /orders/{id}` (broker 원문/체결 상세) 배선.

---

### BL-424

**Title:** 대시보드 실현손익 카드 foot — 미실현(추정) 부기와 기존 문구가 시각적으로 밀착 (폭 부족)
**Priority:** P3
**상태:** ✅ **Resolved (2026-08-09, W3)** — **재현됐다.** 단 원인은 「폭 부족」이 아니라

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-438

**Title:** 거래소 네이티브 TP/SL·트레일링 청산 손익이 머니-패스에 전혀 계상되지 않음
**Category:** Backend / trading (money path)
**Priority:** P1
**Trigger:** 즉시
**Est:** M (6-8h — 귀속 설계가 핵심)
**출처:** 2026-07-25 money-path-accuracy 계획 단계 실발견 (`context-notes.md` §3.1)

**원인 / 영향:** entry 에 부착한 브래킷 TP/SL 이나 `set_trading_stop` 트레일링이 체결되면 포지션이 닫히지만 **우리 DB 엔 아무 행도 생기지 않는다.** WS `order` 고아 이벤트는 5초 버퍼 후 폐기(`state_handler.py:97-102`, `logger.debug` 만 — 알림 없음), `execution` 토픽은 미구독(`websocket_task.py:330`), reconciler 는 local→exchange 단방향이라 INSERT 하지 않는다(`reconciliation.py:137-148`). Order INSERT 지점은 `OrderService.execute` 2곳뿐이다. 그 다음 바에서 pine_v2 warmup-replay 가 **같은 청산을 스스로 추측**해 이미 flat 인 포지션에 reduce-only close 를 발주하고 → `ProviderError` → `state=rejected` → 모든 손익 쿼리가 `state==filled` 로 걸러낸다. 결과적으로 **브래킷으로 익절/손절된 거래의 손익은 Kill Switch·loss-limit 알림·세션 에쿼티 커브 어디에도 잡히지 않는다.** money-path-accuracy(BL-014 부분)는 "우리가 발주한 청산 주문"만 고쳤으므로 이 구멍은 그대로다.

**★선행 주의(2026-07-25 자체 정정):** 현재 스윕의 `orphan_row` 카운터는 **구멍 크기를 측정하지 못한다.** 스윕 후보가 `list_unsynced_reduce_only_since()` = _우리 자신의_ 미동기화 주문이라, 백필이 정상 동작하는 steady state 에선 후보가 0 → 페이지를 아예 안 가져와 orphan 이 영영 0 으로 읽힌다(dogfood 에서 `groups=0` 실측). 규모를 실측하려면 **활성 계정·심볼을 독립적으로 열거**하는 별도 조회가 선행돼야 한다. 이 BL 의 첫 step = 그 측정 스파이크.

**권장 접근:** 스윕이 이미 `/v5/position/closed-pnl` 페이지를 읽고 있으므로 orphan 행을 (a) 합성 Order 행으로 INSERT(state=filled·reduce_only=true·exchange_order_id=Bybit orderId, 마이그레이션 0 가능하나 멱등성·세션 귀속 설계 필요) 하거나 (b) 별도 exchange-exit 원장을 신설한다. 어느 쪽이든 **세션 귀속**(어느 LiveSignalSession 의 포지션이었나)이 핵심 난점이다. 선행으로 `execution` 토픽 구독을 검토하면 실시간 귀속이 쉬워진다.

**Risk:** 🔴 (리스크 게이트가 실현 손실의 일부를 못 본다 — 한도 초과를 늦게 감지)

**상태:** ✅ **Resolved (2026-08-14 `dde53e68` / #631 — money-path-close 검증).** 대상 선정을
`reduce_only` 에서 **`exchange_exits` 상관 EXISTS**(`_HAS_EXCHANGE_EXIT_ROW`)로 바꿨다.
`list_unsynced_reduce_only`/`list_synced_reduce_only` → `list_*_with_exchange_exit`.
★**JOIN 이 아니라 EXISTS 인 이유**가 독스트링에 있다 — `Order : ExchangeExit` 가 1:N(분할 행)이라
JOIN 은 같은 Order 를 N번 돌려주고 `limit` 예산을 잠식한다. **부수로 head-of-line 차단도 없어진다**
(EXISTS 가 매칭 불가 entry 주문을 술어에서 배제 — 그 잔재는 서버 실측 **91건**이고 `limit=500` +
`filled_at ASC` 라 500 을 넘으면 회수 대상이 영영 안 돌아왔을 것이다).
**검증 (money-path-close, 서버 실데이터 음성 대조)** — 같은 계정·같은 시점에서
`구 술어(reduce_only=t) 0건` vs `신 술어(EXISTS 원장행) 490건 / −1,023.87 USDT`.
표적 pytest 72 passed. **kill-switch 귀속률 6.9% → 98.2%**(잔여 −19.68 은 주문 행 자체가 없는
33건이라 회수 불가). ★**아직 소크에는 안 실렸다** — `.soak/src` pin 이 `4b11da26` 로 #631 보다
앞선다. 재-pin 이 배포다.
**종전 상태 (2026-08-14 money-path-attribution, 참고):** 🟡 부분 해결 — 진단이 교체된 시점의 기록.
구멍은 「청산이 DB 에 안 남는다」가 아니라 **「청산은 `exact` 561건으로 남아 있는데 `list_unsynced_reduce_only` 의 `reduce_only=true` 필터가 백필을 막는다」**이고, 규모는 **490건 / −1,023.87 USDT** 다 — 거래소 실현손익 전량(−1,125.81) 대비 **90.9%**.
★**분모를 반드시 함께 적어라** (codex Q2 + 2차 리뷰 #1). 90.9% = `1,023.87 / 1,125.81`(거래소
실현손익 전량). `order_repository.py:780` 의 **93.1%** 는 이 회차가 「−1,101.89 기준」이라 추정했으나
그 산술은 **92.9%** 라 맞지 않는다 — 93.1% 의 분모는 **미상**이다. 어느 쪽도 확정 인용하지 마라. 종전 상태줄(2026-07-25) 원문은 이 줄 아래 유지한다 — 그 시점 판단의 기록이다.

**종전 판단 (2026-07-25 원문, 참고 — 상태 판정에 쓰지 않는다):** 부분 Resolved — 관측 원장(최근 7일) 까지 (`stage/exit-attribution`). 측정 스파이크가 전제를 뒤집었다 — 거래소 전용 행 4건(행 36.4% · |손익| 55.8%)은 **브래킷이 아니라 앱 밖 수동 청산**이었고, **브래킷 체결은 전 기간 0건**(조건부 주문 4건 전부 `Deactivated`, DB 17행 중 TP/SL 실은 주문 0)이라 이 구멍은 코드 경로상 실재하나 **프로덕션 관측 0 = 잠복**이다. 게다가 거래소 전용 4건 중 우리 포지션은 1건뿐이라 자동 계상은 오차단을 만든다. 사용자 확정 = **관측 원장까지**. 신규 `trading.exchange_exits`(행 단위 원본 + provenance) + 스윕을 계정 독립 열거·최근 7일 창·원장 집계 백필로 재작성 + 분류 7종/귀속 3등급(라벨 전용, `inferred` 는 머니-패스 미투입) + 신규 미귀속 행 1회성 알림.
**트리거 판정:** 도래 — Trigger 줄 자신이 「즉시」다. 조건절이 없고 외생·동승 어휘도 없다(`bl-trigger-sweep` 의 `지금` 축이 낭독으로 같은 판정을 낸다) (2026-08-11 bl-703-partial-verdicts)

**★범위 축소 (2026-07-25, 같은 브랜치).** 과거 90일까지 훑는 기계장치(`exchange_exit_sync_state` 워터마크 · 창 전진 · 잘림 처리)를 **머지 전에 걷어냈다.** 이유 = ① 그걸 만든 직접적 목적(20일 전 미동기화 4건 회수)이 로컬 개발 DB 전소로 소멸 ② 뒤집힌 측정을 스코프에 충분히 반영하지 못한 채 만들었다 ③ **실측 — 그 기계장치는 지속 기제가 아니라 ~13주기(약 65분) 후 영구 자기정지하는 일회성 catch-up 이었다**(워터마크는 주기당 7일 후퇴, horizon 은 매 주기 `now` 에서 재계산되어 전진 → `end_ms <= horizon_ms` 가 영구 latch, DB 영속이라 재시작으로도 안 풀림). 즉 정상 상태에서 축소 전후 동작은 동일하고, 실제로 없어진 것은 **일회성 90일 역사 수입** 하나다. 원장은 이제 **최근 7일만** 담는다 → [BL-452](#bl-452).

**★dogfood 완주 (2026-07-25, 사용자 계정 재등록 후).** 독립 오라클 실측(4행, 합계 −0.12392537) = 원장 적재 결과와 **완전 일치**. 분류·멱등·알림 1회성·§9.5 라이브 worker·authed 전부 실 계정으로 검증. **dogfood 가 진짜 P1 을 하나 더 잡았다** — 신규 미귀속 행 알림이 원장 재조회 시 `classification` 컬럼 타입 문제로 매 사이클 조용히 죽고 있었다(수정 완료, [BL-453](#bl-453)). 백필 종단 검증은 주문 이력 소실로 여전히 불가.

**잔여 = ② 거래소 exit 의 머니-패스 계상 + 과거 이력 적재·백필** — 다음 스프린트가 이 원장 데이터를 근거로 결정한다. 관련 신규 = [BL-444](#bl-444)(loss-limit 알림 스코프) · [BL-446](#bl-446)(cumulative_loss 시간축) · [BL-452](#bl-452)(원장 7일 한계) · [BL-453](#bl-453)(StrEnum 재조회 크래시 패턴).

**★② 재평가 (2026-07-25, exit-money-path §0.5) — "미룬 것" 이 아니라 "현재 데이터로는 정직하게 구현 불가" 다.** 실측이 결론을 강제했다.

```
bracket_tp / bracket_sl / trailing / liquidation = 0 행
matched_order_id IS NOT NULL = 0 · attributed_strategy_id IS NOT NULL = 0
JOIN trading.orders ON exchange_order_id → 0 행
```

원장 행을 머니-패스에 넣으려면 행마다 "어느 세션의 자본이 움직였나" 에 답해야 하는데, 쓸 수 있는 등급은 `exact`(존재 행 0)와 `inferred`(머니-패스 투입 금지)뿐이고 남는 것은 `none` = **귀속 불가**다. 오귀속은 곧 오차단이라 되돌릴 수 없다.

**정직하게 만들 수 있는 유일한 산출물은 귀속 없는 계정 단위 숫자**이고, 그건 Site 2(`DailyLossEvaluator`)의 스코프다. 즉 ② 는 "세션 귀속" 이 아니라 **"거래소 exit 를 포함한 계정 단위 실현손익"** 이라는 별개 설계(원장 직접 조회 + 새 집계 메서드 + Site 2 의 새 가산항)이며 스프린트 하나짜리다. exit-money-path 는 이 결론만 기록하고 착수하지 않았다.

부수 발견 = [BL-457](#bl-457)(`classify_exit` 의 format-only `ours`).

**★★★2026-08-14 money-path-attribution — 위 ② 재평가가 반증됐다. 진단이 틀렸고 진짜 구멍은 옆에 있었다.**

② 는 「원장 행을 머니-패스에 넣으려면 `exact`(존재 행 0)뿐이라 정직하게 구현 불가」라고 적었다.
**두 전제가 다 거짓이다.**

⑴ **`exact` 는 0 이 아니라 561건(94.8%)이다.** ② 가 인용한 `matched_order_id IS NOT NULL = 0` 은
**로컬 개발 DB 를 잰 값**이었다. 소크는 2026-08-07 에 서버로 이관됐고 주문 행은 서버 DB 에만
쌓인다(`filled` 654 vs 로컬 321). 로컬에는 청산만 스윕으로 들어와 「주문 없는 청산」 341건이
생기고 그것이 미귀속 57.6% 로 읽힌다. `soak-disqualifications.jsonl:1` 헤더가 실격 원장에
대해 적어 둔 **「어느 DB 를 봤는가」 함정이 이 원장에도 그대로 적용된다.**

```
서버 DB · 고유 청산 592건 (2026-08-14 실측)
  exact     561건 (94.8%)   −1,105.59
  inferred   17건 ( 2.9%)      +2.51
  none       14건 ( 2.4%)     −22.73
```

⑵ **원장 882행은 고유 청산 592건 + 중복 290행이다.** 같은 `exchange_uid` 에 계정 행이 둘
(`0277c150`·`19a8166a`)이라 각자 같은 창을 적재했고, UNIQUE 축이 `(exchange_account_id,
row_hash)` 라 걸러지지 않았다. [BL-605] 수리(`dedupe_accounts_by_exchange_uid`)는 작동 중이고
**중복 적재는 2026-08-08 에 멈췄다** — 잔재다 → [BL-725](#bl-725).

**★진짜 구멍 — 라벨은 `exact` 인데 손익이 흐르지 않는다.**

```
kill-switch 가 보는 것 (filled 주문 realized_pnl SUM)     −78.02 USDT  ( 6.9%)
거래소 실현손익 전량 (고유 592건)                       −1,125.81 USDT
```

원인은 `list_unsynced_reduce_only`(`repositories/order_repository.py:758-772`)가
`Order.reduce_only.is_(True)` 로 거는 것이다. 소크 전략은 **반전 주문**(`sell 0.058 = 2×0.029`)
을 쓰는데 반전에는 `reduce_only` 를 걸 수 없다 — 걸면 거래소가 포지션 크기까지만 체결해 반전이
깨진다. 그래서 실제 청산 주문 581건이 `reduce_only=false` 이고 백필 대상에서 통째로 빠진다.

```
filled | reduce_only=f | realized_pnl NULL | 581건   ← 백필이 못 본다
filled | reduce_only=t | realized_pnl 채움 |  73건   ← −78.02
회수 가능(원장 매칭 확인)                     490건 / −1,023.87 USDT
```

★**`reduce_only` 는 「내가 요청한 안전장치」이지 「이 주문이 청산했는가」의 답이 아니다.**
Bybit·OKX 어느 계약에서도 그 등가가 성립하지 않는다 — Bybit one-way 는 수량이 포지션을 넘으면
반전하고(실측), OKX 는 `reduceOnly` 가 **net mode 전용**이며 `sz > 포지션`이면 **주문 전체를
거부**한다(auto-trim 없음). OKX long/short 모드에서는 청산 주문이 파라미터와 무관하게 자동
reduce-only 다. 판정의 정본은 **거래소 원장이 그 주문의 청산 행을 갖고 있는가**이고, 그것은
Bybit `closed-pnl`(주문 단위 · 실측 한 주문당 정확히 1행, 592/592) 과 OKX `fills.fillPnl != 0`
("Returns 0 for opening trades") 양쪽에 공통이다.

**잔여 처방 (② 를 대체한다):** `list_unsynced_reduce_only` 의 대상 선정을 `reduce_only` 가
아니라 **`exchange_exits` 조인**으로 바꾼다. 매칭 축은 `exchange_order_id` **정확 동등**이라
추측이 0 이고, evaluator(`kill_switch.py`)는 건드릴 필요가 없다 — `Order.realized_pnl` 이
채워지면 `CumulativeLoss`(strategy 축)·`DailyLoss`(계정 축)가 자동으로 본다. 새 집계 메서드는
`ExchangeExitRepository` 에 둔다(`aggregate_closed_pnl:43` 이 선례).

**이것은 이 항목의 잔여가 아니라 [BL-003](#bl-003) P0 의 미발견 전제다** — mainnet runbook 은
「kill-switch 가 손실을 정확히 본다」를 전제하는데 지금은 6.9% 만 본다.

동반 발견 = [BL-724](#bl-724)(수수료 지배) · [BL-725](#bl-725)(중복 290행) ·
[BL-726](#bl-726)(`rejected` 손익 축) · [BL-728](#bl-728)(`CreateByLiq` 미분류).

---

### BL-448

**Title:** WS 고아 이벤트 `replay_orphan` 이 프로덕션 호출자 0 (dead code)
**Priority:** P3
**상태:** ✅ **Resolved (2026-08-09, W2)** — 두 갈래 중 **제거 + 폐기 메트릭**(사용자 결정). 배선은

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-451

**Title:** 파괴적 마이그레이션 테스트가 env 폴백으로 개발 DB 를 드롭할 수 있는 구조
**Priority:** P2
**상태:** ✅ **Resolved** (2026-08-10, `stage/migration-guard`) — 잔여 3항목 전건 종결. ①판정 SSOT `tests/_db_guard.py` 신설 + 루트 `tests/conftest.py::pytest_configure` 로 **승격**하고 `DATABASE_URL` 폴백을 **금지**했다. ★종전 가드의 실체는 「conftest 에도 같은 폴백이 있다」가 아니라 **배선 부재**였다 — 착수 시 실측으로 `pytest tests/trading/` 이 개발 DB DSN 을 물고 rc=0 으로 1088건을 수집했다(그 경로의 세션 픽스처가 `drop_all` 을 돈다). ②`mise run db-snapshot`/`db-restore` 신설 — 덤프 2.15MB 생성 후 임시 DB 로 복원해 orders 823·strategies 3·**암호화 API 키 2/2** 왕복을 실증했다(개발 DB 무접촉). ③이미 됨 ④`alembic/env.py` 에 `downgrade` 전용 가드 + `-x allow_destructive=1` 탈출구 — `upgrade` 는 통과시켜 `mise run migrate`·entrypoint·CI 무영향(rc=0 실측). 배선 테스트 **14건** + 변이 **8/8** red(도달 8/8). ★`/code-review` 가 변이 5/5 를 통과한 구현에서 결함 4건을 잡았다 — `-x allow_destructive=0` 이 파괴를 **허용**(`bool("0")`), `TEST_DATABASE_URL` 이 `.env.example` 에 **없음**(Golden Rule), rc=3 이 가드 고유 신호가 아님(INTERNALERROR 와 구분 불가), `effective_dsn()` 2층 방어에 **도달 0**. 넷 다 고치고 회귀 변이 M6·M7·M8 로 박았다. 판정 사본 1곳 잔존 → [BL-697](#bl-697).

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-466

**Title:** 레버리지 1 백테스트가 자본을 무제한 음수로 몰 수 있다 (마진 게이트 no-op + 청산 없음)
**Priority:** P2
**상태:** ✅ **Resolved** (2026-08-09 btfix) — 승인안 **(c) 리포트 고지**. ★**새 지표 필드를 만들지 않았다** — `mdd_exceeds_capital` 이 이미 정확히 그 술어다(peak ≥ init_cash > 0 이므로 `max_drawdown < -1` ⟺ `equity_min < 0`). 동치 boolean 을 더하면 정보 없이 golden·trust-layer baseline 만 움직인다(`metrics_snapshot` 이 `dataclasses.fields()` 유도 + 정확 dict 비교라 필드 1개에 71→72 keys). 실측 재현: L=1·사이징 미선언에서 자본 10,000 → **−49,044**(5.9배 손실)인데 플래그는 **이미 True** 였다. 한 것 = ① 실경로 오라클 신설 `tests/backtest/engine/test_capital_exceeded_disclosure.py` — 종전 오라클은 `RawTrade` 를 손조립해 어댑터 내부 함수를 불러 **이 경로를 한 번도 안 밟았다**. 고지 + **동작 불변**(강제 종료 없음·수량 1.0 그대로) + 음성 대조 + JSONB 왕복 4건 ② ★**FE 가 원인을 레버리지로 오귀속**하고 있었다 — 축 라벨 "leverage 시 -100% 초과 가능" 을 사실 진술로 바꾸고, 1x 캡션에 "강제청산이 없어 실제로는 불가능한 결과" 를 더했다. `backend/src` **0줄** 이라 golden baseline 은 구조적으로 무변경.

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-469

**Title:** `market_data.backfill_ohlcv` 태스크가 celery 에 등록돼 있지 않고, docstring 의 실행법도 존재하지 않는다
**Priority:** P3
**상태:** ✅ **Resolved (2026-08-09, W2)** — **등록하지 않고 제거**했다. `src/tasks/market_data_backfill.py`(141줄) + `tests/tasks/test_market_data_backfill.py`(164줄) 삭제.

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-470

**Title:** 캐논 감사 9건이 빈 DB 에서 조용히 통과한다 (데이터 전제 부재)
**Priority:** P2
**상태:** ✅ Resolved — 2026-08-10 fe-close-surface. 4라우트 전부 `minExamined(res) > 0` 단정(감사 코어가 그 값을 이미 내주고 있었는데 spec 이 import 조차 안 했다) + `/backtests`·`/trading` 에 데이터 전제 단정 + `/backtests/:id/trades` 의 `test.skip` 을 `expect` 로 뒤집고 체결 행 ≥1 도 본다. 음성 대조 2건이 **skip 이 아니라 fail** 을 내는 것으로 확인. ★**종전 상태줄이 과소 진단이었다** — `test.skip` 은 `/trades` 1건뿐이고 나머지 셋은 skip 조차 없이 **초록**이었다(문제가 1건이 아니라 4건)

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-472

**Title:** 백테스트 목록이 정상 컨벤션(monthly/daily)에는 각주를 달지 않아 두 기준을 구분할 수 없다
**Category:** Frontend / backtest
**Priority:** P3
**Trigger:** BL-461(sub-daily fallback) 처리 시 함께
**Est:** S
**상태:** ✅ **Resolved (2026-08-15 clock-fill-sweep)** — `backtest-list.tsx:391-393` 의 `: undefined` 를 지워 **4 컨벤션 전부** `sharpe.foot` 을 준다. 문구 신규 작성 **0줄** — `sharpe-convention.ts:53,62` 가 이미 monthly/daily 문구를 반환하고 있었다. red 선확인(`Unable to find an element with the title: 무위험 2%/년 · 월간 수익률 기준`) 후 수리. (종전 서술: 목록 title 이 legacy/unavailable 일 때만 붙고, monthly/daily 는 undefined 라 각주가 없다 — 2026-08-09 status-triage-mass) ★2026-08-10 fe-shareable-urls 가 **착수하지 않고 전제만 대조했다** — 아래 세 줄이 그 결과다.
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

★★**2026-08-10 실측 — 본문 한 문장이 틀렸고, 도메인 값 하나가 빠져 있고, 처방이 하나 더 필요하다.**

- **틀림:** 「리포트는 각주를 달지만 목록은 달지 않는다」 → 목록도 legacy·unavailable 에는 단다
  (`backtest-list.tsx` 의 `sharpe.isLegacy || sharpe.isUnavailable` 조건). 비대칭은 **monthly/daily 에서만** 이다.
  리포트는 `key-stats-strip.tsx` · `metric-groups-section.tsx` 둘 다 **컨벤션과 무관하게 항상** `sharpe.foot` 을 노출한다.
- **누락:** 컨벤션 도메인은 3종이 아니라 **4종**이다 — `tv_monthly_rfr2` · `tv_daily_rfr2` ·
  `unavailable` · **`unavailable_nonpositive_equity`**(`features/backtest/sharpe-convention.ts`).
  처방이 `describeSharpe` 를 그대로 쓰면 넷 다 덮인다.
- **미등재 구멍:** `hasMixedSharpeConventions` 는 `null`(legacy)과 non-null 이 섞일 때만 켜진다.
  **monthly + daily 혼재는 둘 다 non-null 이라 무경고로 통과**한다 — 이 BL 이 지적한 바로 그 상황이
  경고를 못 받는다. 정렬은 BE 가 `sharpe_ratio` 숫자만으로 하고 컨벤션은 보지 않는다(`backtest/repository.py`).

**원인 / 영향:** `backtest-list.tsx` 는 legacy·unavailable 계열에만 `title` 을 단다. `tv_monthly_rfr2` 와 `tv_daily_rfr2` 는 **분모 기간이 다른 별개 척도**인데 목록에서는 둘 다 그냥 숫자로 보여 나란히 정렬된다. 리포트는 각주를 달지만 목록은 달지 않는다.

**Risk:** 🟢

---

### BL-485

**Title:** `FormErrorInline` 이 `detail.detail` 로 폴백하지 않아 공통 컴포넌트를 쓸 수 없다
**Priority:** P3
**상태:** ✅ **Resolved (2026-08-09, W3)** — `parseError` 422 general 분기에

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

## 변경 이력

### BL-533

**Title:** 종료 세션 목록이 같은 엔드포인트를 두 쿼리 키로 조회해 미러 state 를 낳는다
**Priority:** P2
**상태:** ✅ **Resolved (2026-08-09, W3)** — 단 **쿼리 키 통일은 이미 끝나 있었다.**

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-539

**Title:** 방향 불일치 유예가 **시간 경계가 없다** — 평가가 드문드문하면 오래된 strike 가 살아남는다
**Priority:** P3
**상태:** ✅ Resolved — strike 에 봉 시각(\_DIRECTION_STRIKE_BAR_KEY)을 실어 TTL·평가공백 판정까지 구현됐고 전용 테스트가 집행한다 (2026-08-09 status-triage-mass 코드 대조)

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-548

**Title:** (P3) `OutcomeParityPanel` 이 375px 에서 페이지 본문 가로 스크롤 24px 을 만든다
**Priority:** P3
**상태:** ✅ **Resolved (2026-08-09, W3)** — 단 **적힌 24px 은 재현되지 않았고 결론만 살아남았다.**

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-551

**Title:** (P3) 라이브 세션 상세 진입이 URL 파라미터가 아니라 클라이언트 state — 딥링크·새로고침 불가
**Priority:** P3
**상태:** ✅ Resolved — 2026-08-10 fe-shareable-urls. 선택이 `?session=<id>` 로 옮겨갔고 딥링크·새로고침 보존이 실 DB 로 실증됐다. `backend/src` 0줄.

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-556

**Title:** `final-gates.sh` 가 `pnpm e2e`(chromium 4건)를 집행하지 않는다 — CI e2e 잡에는 있다
**Priority:** P2
**상태:** ✅ **Resolved (2026-08-08 fe-canon-and-responsive)** — `final-gates.sh` §4 에

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-559

**Title:** (P3) 진입 완결성 도구 잔여 3건 — 세션 목록 절단 감지 · 사문 라벨 · janitor probe 전이
**Priority:** P3
**상태:** ✅ **Resolved (2026-08-11 gate-surface)** — ①③ 은 구현 완료였고 ②는 **기각**한다. 「사문 라벨을 제거하라」는 처방이 코드 대조로 반증됐다 — 그 라벨이 사문인 것은 **결함이 아니라 설계 의도의 결과**이고, 지우면 마지막 방어선이 발화하는 날의 유일한 증거가 사라진다 (근거는 아래 §2026-08-11)

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-564

**우선순위:** P3
**상태:** ✅ Resolved (2026-08-09 backlog-sweep) — 처방 2건이 **이미 구현돼 있었고** Trigger 도 이미 도래했다. 코드 0줄.

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-586

**우선순위:** P3
**상태:** ✅ **Resolved** (2026-08-07 backtest-fidelity)

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-601

**Priority:** P3
**상태:** ✅ **Resolved (2026-08-09, W2)** — 저장소 메서드 2건은 제거, 하네스 1건은 **제거 대신 게이트 배선**.

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-603

**Priority:** P2
**상태:** ✅ **Resolved (2026-08-07 gap-resync-autopsy 회차)** — 기본값을 실측으로 교체했다.

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-605

**Priority:** P2
**상태:** ✅ **Resolved** (2026-08-09 excl) — 스윕 계정 루프가 `exchange_uid` 로 접힌다(`src/trading/account_identity.py:dedupe_accounts_by_exchange_uid`). 회귀 = `test_sweep_visits_one_row_per_real_exchange_account` — **수리 전 red 를 되돌려 실증**했다(`accounts=2`·조회 2회·원장 2행 → 수리 후 1/1/1). ★같은 회차에서 **테스트 하네스도 고쳤다**: 페이크 `upsert_rows` 가 `row_hash` 단독으로 접고 있어 실제 UNIQUE 축 `(exchange_account_id, row_hash)` 를 흉내내지 못했고, 그래서 **2배 적재를 하네스가 가리고 있었다**. 기존 574행은 그대로 둔다(계정 필터가 소비를 가른다)

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-610

**Priority:** P2 (~~P3~~ — 2026-08-07 전수 재검출로 상향. 인덱스 행은 처음부터 P2 표에 있었고,
**상태:** ✅ **Resolved** (2026-08-08 soak-mortality-repair — 10/10 수리, 재검출 `DANGLING` 0건)

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-611

**Priority:** P2
**상태:** ✅ **Resolved (2026-08-07, PR #554 리뷰 회차)** — 후보 ⑴ 채택. `AGENTS.md` 에

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-612

**Priority:** P3
**상태:** ✅ Resolved (2026-08-09 backlog-sweep) — LESSON-095 승격 → 버퍼 삭제 → INDEX tombstone 전환. 코드 0줄.

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-614

**Priority:** P3
**상태:** ✅ Resolved (2026-08-09 backlog-sweep) — LESSON-096 승격. 3건 중 1건은 **기존 항목 재발**로 기록. 코드 0줄.

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-622

**Priority:** P1
**상태:** ✅ **Resolved (2026-08-07 gap-resync-autopsy 회차)**

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-620

**Priority:** P2
**상태:** ✅ **Resolved (2026-08-07 gap-resync-autopsy 회차)** — 게이트의 기본 취득 경로를

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-621

**Priority:** P3
**상태:** ✅ **Resolved** (2026-08-07 backtest-fidelity)

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-626

**Priority:** P3
**상태:** ✅ Resolved (2026-08-09, W1)

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-627

**Priority:** P3
**상태:** ✅ **Resolved (2026-08-09, W2)** — `--out-dir <path>` 신설(`--confirm` 전용). 라운드트립

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-628

**Priority:** P3
**상태:** ✅ **Resolved (2026-08-08 fe-canon-and-responsive)** — 라이트 `--warning` 을

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-629

**Priority:** P3
**상태:** ✅ **Resolved (2026-08-08 fe-canon-and-responsive)** — 수리 방향 **①(삭제)** 을

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-630

**Priority:** P3
**상태:** ✅ **Resolved (2026-08-08 fe-canon-and-responsive)** — 수리 방향 중 **전자**를

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-631

**Priority:** P2
**상태:** ✅ **Resolved (2026-08-08 bl003-unblock 회차)** — 수리 방향 ⑵ 를 택했다. `scripts/docs-audit.sh` 가 `runtime-check.mjs` 와 `regen_golden.py --check` **둘 다**의 존재+기동을 확인한다(이 BL 이 정의한 「두 도구를 함께」). 출력 축에 `orphan tool startup` 이 추가됐다. ★[BL-602] 를 피해 `frontend/package.json` 은 건드리지 않았다. ★회차 말 실측: `node runtime-check.mjs` **17/17 통과 · exit 0** — 이 회차의 `docs/` 재편(archive 신설)이 이 도구를 다시 죽이지 않았다.

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-633

**Priority:** P1
**상태:** ✅ **Resolved (2026-08-08 bl003-unblock 회차)** — G-A4‴ 소유권 7/27 · G-A6′ 정본 항등식 4/4(반사실은 정의 4가지 어디서도 4/4 불가 · 최대 1/4) · G-A7 계정 결합 27/27 로 이중 호스트 오염을 근인으로 확정했다. ★원안 G-A4′·G-A6 은 회차 도중 반증돼 교체됐다.

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-618

**Priority:** P3
**상태:** ✅ **Resolved (2026-08-08 fe-canon-and-responsive)** — 수리 방향 **①(문서 정렬)**.

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-634

**Priority:** P1
**상태:** ✅ **Resolved** (2026-08-09 excl) — 가드가 `LiveSignalSessionService.register()` 의 **전제조건**으로 들어갔다(`src/trading/services/account_exclusivity.py`, 잔고 스냅샷 뒤 · quota lock 앞). HTTP(`router.py:458`)와 스크립트(`live_session_admin.py:_cmd_start`)가 공유하는 유일한 병목이라 두 경로가 함께 덮인다 — 종전의 유일한 강제였던 `scripts/soak-restart.sh` 는 소크 재시작 경로에만 걸렸다. 판정식은 [BL-639] 가 확정한 그대로(resting conditional · `reduce_only=None` · `order_link_id` 소유권)다. ★**소유권 집합의 계정 축 = `exchange_uid` 형제 행 전량**(BL-639 실패 모드 3 종결) — 스코프 없음은 거부율이 원장 크기를 따라가고, 행 하나로 좁히면 [BL-605] 의 2행 때문에 **우리 주문을 FOREIGN 으로** 판정해 정상 재기동을 영구히 막는다. ★fail-closed — 거래소를 못 읽으면 `ProviderError` 가 올라가 세션이 안 열린다. ★`exclusivity_service` 는 **필수 인자**다(기본값 `None` 은 새 조립부를 조용히 무방비로 만든다). 회귀 = `tests/trading/test_account_exclusivity_guard.py` 6건, **변이 2종으로 판별력 실증**(가드 호출 제거 → 5/6 red · 계정 축을 자기 행으로 좁힘 → 형제 테스트 red)

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-635

**Priority:** P1
**상태:** ✅ **Resolved (2026-08-08 bl003-unblock 회차)** — 서버 게이트 아카이브의 판독 불가를 fail-closed 로 처리했다.

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-637

**Priority:** P2
**상태:** ✅ **Resolved (2026-08-08 bl003-unblock 회차)** — `scripts/bl-audit.sh` 에 우선순위 배치가 **4번째 검사 축**으로 들어갔다. 출력은 「✓ 4면 정합 — 3면(섹션 · 인덱스 표 · 로드맵) + 우선순위 배치」다. ★판별력 주입 시험 **2/2** — BL-626 섹션의 `**Priority:**` 만 P3→P1 로 바꾸자 exit 1(「우선순위 배치 1 건」), 문자열 치환으로 되돌리고 sha256 일치로 원상복구를 증명한 뒤 exit 0.

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-643

**Priority:** P2
**상태:** ✅ **Resolved (2026-08-08 soak-exclusivity-and-observability 회차)** — 술어 2개가

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-642

**Priority:** P2
**상태:** ✅ **Resolved (2026-08-08 soak-exclusivity-and-observability 회차)** — `soak-gate.sh` 의

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-714

**Title:** 마감 게이트가 전제하는 브랜치 상태가 문서에 없다 — 증분 머지 후에는 신호가 구조적으로 초록이 될 수 없다
**Category:** Ops / 게이트 (문서 계약)
**Priority:** P2
**Trigger:** 마감 절차를 다시 쓸 때 / 같은 상태에 또 빠질 때
**Est:** XS-S
**상태:** ✅ **Resolved** (2026-08-14 gate-surface-close) — ★**원장이 적어 둔 처방 2·3 을 착수 전에 기각하고 다른 길로 닫았다.** ⑴ **처방 2(`--range` 탈출구) 기각** — A1 의 방어 대상은 정확히 1개 상태이고 그 **유일한 증인이 하네스 케이스 ⑫**(`signal-check-test.sh:305`, fixture `repo-mbhead`)인데, 변이 `M1` 의 기대 red 집합이 **정확히 `⑫` 하나**다(`:535`, 정확 집합 일치 요구). `--range` 로 `MERGE_BASE` 를 사람이 대체하게 하면 A1 조건이 거짓이 되고 A2 가 초록을 내 **⑫ 가 green = 증인 소멸** ⇒ [BL-706] 이 이미 폐기한 모델의 재도입이다. ⑵ **처방 3(`range:` 첫 줄) 기각** — squash 머지라 브랜치 팁이 HEAD 의 조상이 아니어서(`gates-and-traps.md`, 로컬 165건 중 조상 **0건**) 제3자·CI 가 범위의 실재를 검증할 수 없다. ⑶ **채택 = 입구 거부** — `final-gates.sh` 가 인자 파싱 직후 `merge-base(origin/main,HEAD) == HEAD` 를 검사해 **게이트 체인 진입 전에 거부**한다(`--run eod` 거부와 문형 동일, `origin/main` 부재 시 비발화). A1 은 **한 줄도 안 바꿨고** `signal-check.sh` 는 A1 의 `WHY` 에 처방 문장만 더했다. ⑷ **문서 축** — `gates-and-traps.md` 에 신호 4종 표 · 앵커 **A1~A5** 판정식 · rc 규약(**3=abort, 초록 아님**) · 브랜치 전제를 신설(종전에는 하네스 1줄뿐이었고 판정식이 **전무**했다).

**검증 (CONTROL 직접 집행 — 워커 자기신고 불채택):** 하네스 **26/26** · 변이 **15종 전건 판별**(`M1 → 정확히 ⑫`, 즉 A1 불변) · 음성 대조 N1~N3 red 0건. ★신규 케이스 ㉖ 의 **판별력을 수동 변이로 먼저 확인**한 뒤(입구 거부 블록 461바이트 제거 → 정확히 ㉖ 만 red) 그것을 **영구 변이 M12 로 승격**했다 — 그 전까지 ㉖ 은 **자기를 지키는 변이가 없는 케이스**였다(§8.6).
**트리거 판정:** ~~도래 — 처방이 우리 손 안에 있다~~ → **2026-08-14 완료.** 도래 판정은 맞았고 **처방이 틀렸다.** ★트리거의 「처방이 우리 손 안에 있다」는 **처방이 옳다는 뜻이 아니다** — 두 판단을 같은 줄에 쓰지 마라
**출처:** 2026-08-12 surface-demo-pack (마감에서 실측)

**원인 / 영향:** `tools/scripts/signal-check.sh` 의 `judge_freshness()` 는 **앵커 A1** 을 가장 먼저 본다:

```sh
if [ -n "$MERGE_BASE" ] && [ "$MERGE_BASE" = "$HEAD_SHA" ]; then           # ← 앵커 A1
  CODE="no-branch-commits"; WHY="브랜치 커밋이 0개다 (merge-base == HEAD)"; return 1
fi
if [ "$sha" = "$HEAD_SHA" ]; then                                          # ← 앵커 A2
  CODE="head"; WHY="HEAD 와 동일"; return 0
fi
```

A1 이 A2 **앞**이므로, 전건 머지돼 `merge-base(origin/main, HEAD) == HEAD` 가 된 main 에서는
신호의 sha 가 HEAD 와 **정확히 같아도** 판정이 `stale[no-branch-commits]` rc=1 이다. 실측:

```
screen.ok rc=1 stale: screen.ok @ 93655ee3 [no-branch-commits] — 브랜치 커밋이 0개다 (merge-base == HEAD)
codex.ok  rc=1 stale: codex.ok  @ 93655ee3 [no-branch-commits] — 동일
g9.ok     rc=1 stale: g9.ok     @ 93655ee3 [no-branch-commits] — 동일
vercel.ok rc=1 stale: vercel.ok @ 93655ee3 [no-branch-commits] — 동일
```

★**A1 을 없애면 안 된다** — 그것이 없으면 main 에 서서 `commit: $(git rev-parse HEAD)` 한 줄만 적어도
4종이 전부 통과한다. [BL-706] 이 막으려던 것이 정확히 그것이다.

★**갭은 게이트가 아니라 문서다.** `§G8` 과 `docs/status.md` ⓸ ④ 는 「마지막 커밋 뒤, 클린 트리에서
게이트를 돌려라」라고만 말하고 **「그 커밋이 아직 머지되지 않은 브랜치에 있어야 한다」를 말하지
않는다.** 그리고 §G8 의 순서(「PR 생성까지, squash 는 사용자」)는 그 전제를 **암시만** 한다.
2026-08-12 회차는 사용자 결정으로 「CI 확인 → 즉시 머지」를 반복했고, 마감 시점에 브랜치가 남지
않아 그 상태에 빠졌다. ⇒ **문서를 그대로 따르면서도 게이트가 성립하지 않는 경로가 있다.**

★★그리고 **빈 커밋으로 브랜치를 만들어 초록을 사지 않았다.** 그것이 이 레포가 반복해 밟은 거짓
그린이고, [BL-706] 회차의 「비어 있지 않은 파일 하나로 초록을 만들 수 있었지만 그러지 않았다」와
같은 자리다.

**권장 접근 (셋 중 하나 이상):**

1. **문서에 전제를 명시한다** — 「마감 게이트는 **그 회차의 마지막 PR 브랜치에서**, 머지 **전에**
   돌린다」를 §G8 과 ⓸ ④ 에 박는다. 가장 싸고 이 회차의 사고를 그대로 막는다.
2. **머지된 회차용 탈출구** — `signal-check.sh` 에 `--range <base>..<head>` 를 주면 A1 대신 그 범위로
   판정한다. 단 **범위를 사람이 고를 수 있으면 판별력이 준다** — 기본값 없이 명시 인자만 허용하고,
   범위가 비면 rc=3 으로 판정을 포기해야 한다.
3. **신호에 범위를 적게 한다** — 첫 줄을 `commit: <sha>` 에서 `range: <base>..<head>` 로 확장하고,
   게이트는 그 범위가 **원장(reflog·머지 커밋)에 실재**하는지만 본다.

★**어느 쪽이든 수용 기준에 「A1 을 무력화하지 않았음」을 넣어라** — 변이로 A1 을 지웠을 때 main 에서
빈 신호가 통과하는 것이 다시 red 로 잡혀야 한다.

**Risk:** 🟡 게이트가 안 도는 것이 아니라 **마감 증거를 남길 수 없다.** 이 회차는 구성 게이트를
전부 개별 실행해 증거를 남겼지만, 그것은 `final-gates` 한 줄이 주는 보증과 다르다.

---

## Deferred — trigger 미도래 · 의도적 부활 가능 (구 `_deferred.md` 승격, 2026-08-06)

### BL-644

**Priority:** P3
**상태:** ✅ **Resolved** (2026-08-08, `stage/ztb-w3-responsive`)

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-645

**Priority:** P3
**상태:** ✅ **Resolved (2026-08-09, W3)** — 단 **처방 ③ 은 「가장 싸다」가 아니었다.**

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-646

**Priority:** P3
**상태:** ✅ **Resolved** (2026-08-08, `stage/ztb-w3-responsive`)

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-649

**Priority:** P3
**상태:** ✅ **Resolved** (2026-08-08, `stage/ztb-w3-responsive`)

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-651

**Priority:** P2
**상태:** ✅ **Resolved** (2026-08-09 excl) — `live_session_admin._cmd_status` 의 거래소 조회 루프가 `exchange_uid` 로 접힌다([BL-605](#bl-605) 와 **같은 헬퍼**, 다른 루프). raw SQL 을 걷어내고 `ExchangeAccountRepository.list_by_exchange(bybit)` 로 바꿔 `exchange_uid`·`read_only` 를 얻는다 (Repository 밖 DB 접근 금지 규칙에도 맞다). 회귀 = `tests/trading/test_live_session_admin_status.py` 3건 — **수리 전 red 를 되돌려 실증**했고 그 출력이 CONTROL 실측을 그대로 재현했다(`RESTING_CONDITIONAL=2`, `FOREIGN` 줄 2개 → 수리 후 1/1). ★음성 대조 포함 — 원장이 소유를 주장 못 하는 resting 은 dedup 후에도 `EXCLUSIVE=NO` 로 잡힌다(판별력 불변)

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-653

**Priority:** P2
**상태:** ✅ Resolved (2026-08-09, W1)

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-656

**Priority:** P2
**상태:** ✅ Resolved (2026-08-09, W1)

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-657

**Priority:** P2
**상태:** ✅ Resolved (2026-08-09, W1)

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-672

**Title:** [BL-661] service→CLI `detail` 계약을 **잇는 테스트가 없다** + runbook §7 이 낡았다
**Priority:** P3
**상태:** ✅ **Resolved** (2026-08-11 bl-672-close) — 잔여 2건이 **둘 다 이미 이행돼 있었다.** ⑴ 계약 테스트 = `test_live_session_admin_flatten.py:130` `test_flatten_cli_formats_actual_flat_resting_entry_detail` (2026-08-10 close-ownership-axis 가 넣었다). ⑵ 「runbook §7 갱신 미이행」은 **반증됐다** — `bybit-mainnet-runbook.md:363-372` 이 2026-08-10 정정으로 `no_open_position` 의 새 의미와 **rc 0/1/3/4 분기**를 이미 적고 있다. ★**이 항목은 한 줄도 새로 짜지 않고 닫혔다** — 닫은 것은 코드가 아니라 **원장의 거짓 문장**이다. 「미이행」이라 적힌 것을 문서에게 되물었더니 이행돼 있었다([BL-307]·[BL-703] 에 이은 **네 번째** 실증)

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-665

**Title:** 거래 상세 검색이 키 입력마다 2000건을 다시 정렬한다 (디바운스 없음 + comparator 안 날짜 파싱)
**Priority:** P3
**상태:** ✅ Resolved (2026-08-09 fe-perf-quartet) — decorate·sort·undecorate 로 키를 N회만 파고, 검색은 기존 `useDebouncedValue`(200ms)를 물렸으며 memo dep 을 객체에서 스칼라 8개로 바꿨다. 회귀 3건(동점 안정성 · 디바운스 · 배지↔표↔CSV 스냅샷 일치)은 변이 M2·M3·M6 으로 빨간 것을 확인했다

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-684

**Title:** `close_position` 이 포지션이 **있을 때는** 미체결 조건부 진입을 보고조차 하지 않는다
**Priority:** P1
**상태:** ✅ Resolved — 2026-08-10 close-ownership-axis. 포지션이 있는 경로에서도 미체결 진입 주문을 청산 주문 **앞에** 조회해 `ClosePositionResponse.resting_entries` 로 싣는다. 조회 실패는 청산을 막지 않고 `resting_entries_unknown` 으로 구분한다 — flat 경로의 fail-closed 와 **의도적 비대칭**이다(위험이 반대: flat 에서 fail-open 은 거짓 flat 보고, 포지션 경로에서 fail-closed 는 열린 포지션 봉쇄). CLI 는 rc **4** 신설(0=flat/잔량 없음 · 1=실패 · 3=잔량 있고 주문 미발행 · 4=주문 접수+잔량). 표적 변이 7/7 red(도달 확인 포함). 「조건부 진입」 문구는 **「미체결 진입 주문」**으로 고쳤다 — 필터가 일반 지정가도 잡으므로

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-687

**Title:** pre-commit 의 backend 훅이 스테이징된 py 파일 중 **첫 하나만** 검사한다
**Priority:** P2
**상태:** ✅ **Resolved** (2026-08-10, `stage/precommit-scope`) — 훅 3개를 `"${0#backend/}" "${@#backend/}"` 로 바꿔 스테이징된 py 전량을 넘긴다.

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-688

**Title:** FE `ClosePositionResponseSchema` 가 [BL-684] 의 새 필드를 Zod 에서 버린다
**Priority:** P2
**상태:** ✅ Resolved — 2026-08-10 fe-close-surface. `RestingEntryOrderSchema` 신설 + 두 필드를 `.default()` 로 선언(서버 모델 기본값과 같게)했고, `close-outcome.ts` 가 응답/에러를 다섯 상태로 갈라 `CloseOutcomePanel` 이 그린다. 잔량 있음과 **확인 실패**가 서로 다른 `data-testid` 를 갖고 서로를 배제한다. 변이 6/6 red(도달 확인 포함) · e2e 5건이 실브라우저에서 판정 · Zod strip 을 되돌리면 e2e 3/5 가 빨개진다

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-695

**Title:** `**트리거 판정:**` 줄에 소유자가 없다 — 다음 BL 은 이 줄 없이 등재된다
**Priority:** P3
**상태:** ✅ **Resolved** (2026-08-10, `stage/precommit-scope`) — `docs-audit.sh` 가 ACTIVE/DEFERRED 섹션마다 `**트리거 판정:**` 줄을 **정확히 1개** 요구한다.

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-698

**Title:** `e2e authed` 백테스트 폼 422 케이스 2건이 **main 에서 이미 red** 다
**Priority:** P2
**상태:** ✅ Resolved — 2026-08-10 backtest-submit-fix. **테스트 결함이 아니라 프로덕션 결함이었다.**

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-701

**Title:** soak-gate C1 판정식이 [ADR-024] 의 새 문턱(24h 창 3회)을 반영하지 않는다
**Priority:** P1
**상태:** ✅ **Resolved** (2026-08-11 bl-701-c1-window-count) — `soak_gate_predicate.py` 가 `DEFAULT_REQUIRE_WINDOWS = 3` 과 **자격 창 셈**을 갖고, 판정 문구·`soak-gate.sh` 출력이 **문턱을 하나만** 말한다(`C1 24h 창 1 / 3회 (참고: 누적 69.14h)`). [ADR-024] §판정 술어 표와 §C1 의 🔴 도 함께 닫았다. 변이 **8/8 red** · 음성 대조 = **23.9h 창 3개(합 71.7h) → 0/3**. 테스트 58 → **68** · soak-watch 하네스 14 → **17**. ★★**codex 적대 리뷰가 P1 을 잡았다** — 초판이 커버리지 조각을 그대로 세어 **단일 74h 실행이 3회로 위조**됐다(측정이 나쁠수록 점수가 오르는 fail-open). 자격 창을 **귀속 구간당 최대 1개**로 고쳤다. ★**부수 발견 — 이 수리가 무인 감시를 죽일 뻔했다**: `soak-watch.sh:246` 이 크래시 판별 앵커를 `C1 누적` **문자열**에 걸어 놨고, 그 하네스 픽스처는 옛 서식의 얼린 캡처라 **초록인 채로** 매 실행이 「게이트 크래시」가 됐을 것이다 ⇒ 앵커를 라벨(`C1`)만 잡게 고치고 신 서식 픽스처 + 케이스 ⑪ 추가

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-704

**Title:** `/metrics` fail-closed 를 지켜 주는 것이 실배포 호스트에는 없다 — 부팅 가드가 `app_env=production` 만 본다
**Priority:** P2
**상태:** ✅ **Resolved (2026-08-11 metrics-boot-log)** — 권장 접근 ⑴⑵ 이행. `lifespan()` 이 `metrics_auth=enabled|DISABLED app_env=…` 1줄을 **모든 환경에서** 찍는다(부팅은 안 막는다). 판정은 `_metrics_auth_token()` 하나를 엔드포인트 가드와 공유해 로그와 실제 동작이 갈라질 수 없다. ⑶(노출 판정을 바인딩·프록시로 이관)은 잔여 — 아래 참조

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-705

**Title:** skip 래칫의 스코프 하한이 합계라 한쪽 스코프가 통째로 빠져도 초록이다 + 스캔층 자기검사 부재
**Priority:** P2
**상태:** ✅ **Resolved (2026-08-11 skip-ratchet-scope)** — 권장 접근 ⑴~⑷ 전건 이행 + 신설 하네스 11/11. 하한을 스코프별(`backend/tests` 350 / `backend/src` 150 = 실측 505·217 의 70% 선)로 바꾸고 스코프 경로 부재를 따로 판정한다. 스캔을 `scan(root)` 으로 분리하고 `scripts/skip-ratchet-test.sh` 가 임시 트리로 그 층을 태운다

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-706

**Title:** `final-gates` 신호 4종이 신선도를 안 봐 **남의 회차 파일로 초록**이 난다 — 게다가 문서가 시키는 명령이 그걸 만든다
**Priority:** P1
**상태:** ✅ Resolved (2026-08-11 gate-freshness) — 처방 ⑴+⑵+⑷ 구현: `scripts/signal-check.sh`(첫 줄 `commit: <sha>` 를 merge-base(origin/main,HEAD)..HEAD 범위와 대조, merge-base 실패는 rc=3 abort) + `final-gates.sh` 의 `--run eod` 인자 거부(문서 규율이 아니라 스크립트가 막는다) + 하네스 25케이스·변이 13종. ⑶(재사용 경고)은 ⑴ 이 있으면 잉여라 기각. 실물 대조 — eod 낡은 신호 4종이 이제 `missing[commit-line]` FAIL 이고, origin/main sha 는 `stale[origin-main]`, HEAD/브랜치 커밋은 `signal[head]`/`signal[branch]` 다.

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-702

**Title:** ⓪ 표 정체성 계약에 소유자가 없다 — 살아 있는 행이 원장과 갈려도 게이트가 침묵한다
**Priority:** P1
**상태:** ✅ **Resolved (2026-08-11 ledger-truth)** — `docs-audit.sh` 에 `zero_table_identity` 축 신설 + `scripts/docs-audit-test.sh` 하네스 4/4 + `final-gates.sh` 배선.

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-703

**Title:** PARTIAL 24건이 `**트리거 판정:**` 줄을 갖지 않아 「PARTIAL ∧ 도래」가 구조적 공집합이다
**Priority:** P1
**상태:** ✅ **Resolved** (2026-08-11 bl-703-partial-verdicts) — PARTIAL **24/24** 에 근거를 붙인 `**트리거 판정:**` 줄을 넣었고(도래 5 · 미도래 19), `docs-audit.sh` 의 `trigger_verdicts` 축과 `bl-trigger-sweep.sh` 의 대상 집합이 **둘 다 PARTIAL 을 포함**한다. 하네스 `docs-audit-test.sh` 7/7(신규 3 = PARTIAL 도래/미도래/판정줄 누락). ⓪ 표에 **O~S 5행**이 올라왔다. ★착수 근거였던 「P0 1 + P1 4 가 올라온다」는 **반증됐다** — [BL-003]·[BL-619]·[BL-661] 은 실측으로 미도래이고, 대신 원장이 몰랐던 [BL-639]·[BL-672] 가 올라왔다

> 📦 **본문 접힘 (2026-08-13 docs-diet).** 원문 = `git show 8abd0d67:docs/backlog.md`

### BL-715

**Title:** 브랜치 잔재 62건 — 삭제 안전망이 없어 보류 (원격 23 + 로컬 39)
**Category:** Ops / 레포 위생
**Priority:** P3
**Trigger:** 커밋 491개를 개별 대조할 시간이 확보될 때 / 잔재가 다시 성가셔질 때
**Est:** S-M
**상태:** ✅ **Resolved** (2026-08-14 gate-surface-close — 판정 완료. 삭제 집행은 사용자 결정) — 전수 실측으로 **양 축이 모두 반증**됐다. ⑴ **로컬 축은 이미 소멸**: 원장 「39건 보류」 → 실측 `refs/heads/` = **`main` 1개**(`.git/logs/refs/heads/` 도 `main` 뿐 · `packed-refs` heads 1행). 미머지 339커밋 대조는 **대상이 없다**. ⑵ **원격 축의 분류가 뒤바뀌어 있었다**: 원장 「C(PR 이력 없음) 14 + D 9」 → 실측 **E 9 + C 5 + D 9**. 원장의 C 14 는 `gh pr list --head <이름>` 이 **이름으로만** 매칭한 산물이고, 팁 sha 로 `commits/:sha/pulls` 를 치면 **9건이 머지된 PR #74·#75 head 의 조상**이다. ★**즉 원장이 「안전망 없음」으로 겁내던 9건이 실은 23건 중 sha 안전망을 가진 유일한 집합이었다 — 겁낼 대상과 안심할 대상이 정확히 뒤바뀌어 있었다.** ⑶ 미머지 커밋 합계 **152 = 원장과 일치**(이 수치만은 맞았다). ⑷ 내용 가치 = **0건** — 23건 전부 main 또는 main 역사에 blob 으로 반영·승계됨을 코드 마커로 확인(경로가 [ADR-029] 로 이동해 **경로 존재 검사는 전건 거짓 「main無」**를 낸다 — 내용 grep 으로만 잡힌다). 유일한 미반영 = `TEST_REDIS_LOCK_URL` **1줄**이었고 이 회차가 `apps/api/.env.example` 에 반영했다(Golden Rule 「`.env.example` 에 없는 env 참조 금지」 위반이 실재했다 — `conftest.py:54`).
**트리거 판정:** ~~미도래 — 미머지 491개 대조 비용이 잔재 비용보다 크다~~ → **2026-08-14 도래·완료.** 대조를 서브에이전트에 위임하니 CONTROL 비용이 사실상 0 이었고, 491 중 **339(로컬)는 대상 자체가 없었다**. ★**「비용이 크다」는 트리거 사유는 그 비용을 실제로 재기 전까지 가설이다** — 여기서는 분모의 69%가 존재하지 않았다
**출처:** 2026-08-12 branch-debris (원격 축 = PR #611 · 로컬 축 = 같은 날 후속)

**원인 / 영향:** 2026-08-12 회차가 브랜치를 **안전망 보유 여부**로 갈랐다. git 위상으로는 재확인할 수
없다 — squash 머지라 브랜치 팁이 main 의 조상이 되는 일이 없다(로컬 165건 중 `ANCESTOR` **0건**).

**원격 축** (판정 기준 = GitHub PR 상태)

| 분류                            |  수 | 처분                    |
| ------------------------------- | --: | ----------------------- |
| A — 머지된 PR 보유              | 270 | 261건 삭제 · 9건은 D 로 |
| B — 닫힌(미머지) PR = 버린 작업 |   6 | 6건 삭제                |
| C — PR 이력 없음                |  14 | **보류** (본 BL)        |
| D — A 인데 팁 sha 가 안전망 밖  |   9 | **보류** (본 BL)        |
| 합계                            | 290 | 삭제 267 · 보류 23      |

**로컬 축** (판정 기준 = 안전망 3축 — 팁이 main 조상 / 팁 sha 가 원격 도달 가능 / 팁 sha 가 PR head)

| 분류                               |  수 | 처분                         |
| ---------------------------------- | --: | ---------------------------- |
| L-A — 팁 sha 가 PR head (PRHEAD)   | 121 | 삭제 (`-D`)                  |
| L-B — 팁 sha 가 원격 도달 (REMOTE) |   5 | 삭제 (`-d` 가 그대로 받았다) |
| L-C — 안전망 없음                  |  39 | **보류** (본 BL)             |
| 워크트리 점유 + main               |  12 | 대상 밖                      |
| 합계                               | 177 | 삭제 126 · 보류 39           |

★**로컬 보류 39건이 이 축의 위험이다.** 미머지 339 커밋 중 **337개가 어떤 안전망에도 없다** —
원격에서 도달할 수 없고 어떤 PR 의 head sha 도 아니다. 즉 **이 랩톱에만 있다.** 원격 보류 23건
(안전망 밖 142)보다 회수 불가능성이 크다.

★**안전망 가설을 실증했다 — 표본이 아니라 전건이다.** 「PR 이 있으면 브랜치를 지워도 GitHub 이
sha 를 보관한다」는 프롬프트가 준 전제였다. 삭제한 267건에서 표본 5건을 뽑아
`gh api repos/:o/:r/commits/<sha>` 를 쳤더니 5/5 가 sha 를 돌려줬다. **표본 5건은 121건을 입증하지
않는다**(2026-08-12 codex 적대 리뷰의 지적) — 그래서 `-D` 로 지운 로컬 121건의 팁 sha를 **전건**
조회했고 **121/121 OK, MISS 0** 이다. 음성 대조로 가짜 sha(`000…0`)는 `MISS`, `origin/main` 팁은
`OK` 이므로 이 확인은 판별력이 있다.

★**remote-tracking ref 가 stale 이면 이 판정은 무너진다** — `git rev-list --remotes=origin` 은
**로컬의** `refs/remotes/origin/*` 을 읽는다. 지우기 전에 라이브 원격과 대조해야 한다. 이번 회차는
`git ls-remote --heads origin` 과 대조해 **24개 브랜치가 sha 까지 완전 일치**함을 확인했다(차이는
`origin/HEAD` 한 줄뿐). 가짜 stale ref 를 심으면 이 대조가 잡는다(판별력 확인).

★**D 9건이 이 회차의 발견이다.** 프롬프트는 「A·B 는 PR 이 있으므로 GitHub 이 sha 를 보관하고 복원
버튼이 살아 있다」를 삭제의 안전 근거로 세웠다. 그런데 복원 버튼이 되살리는 것은 **PR 의 head sha**
이지 브랜치의 **현재 팁**이 아니다. 이 9건은 PR 머지 뒤 커밋이 더 쌓여 팁이 어떤 PR head 와도
일치하지 않는다 ⇒ 지우면 미머지 커밋 72개 중 **62개**가 안전망 밖에서 사라진다. 이름축(브랜치명 ↔
PR head ref)만으로 삭제했으면 못 봤고, **해시축(팁 sha ↔ PR head sha) 대조가 잡았다.**

★**「72개 전부」는 과장이었다 — 2026-08-12 codex 적대 리뷰가 잡았다.** 초판은 「미머지 커밋 72개가
안전망 밖」이라고 썼는데, 실제로 세어 보니 그중 **10개는 다른 PR 의 head sha** 였다(그 PR 의 복원
버튼이 되살린다). 팁 sha 가 안전망 밖이라는 것과 **그 브랜치의 모든 커밋이 밖**이라는 것은 다른
명제인데 초판이 둘을 붙여 놨다. 정정 = 62/72. 세는 방법은 표 위의 정의를 봐라.

★**diff 로는 판정할 수 없다** — 2026-08-12 에 실패한 방법이다. 표본 8건이 `파일 1,600여 개 · +17만 /
−31만` 을 냈는데 그것은 브랜치의 고유 작업이 아니라 **3개월치 시간 차이**다(브랜치가 그 시점의 레포
전체를 들고 있다). 판정하려면 미머지 커밋 152개(C 80 + D 72)를 커밋 단위로 읽어 main 반영 여부를
대조해야 한다.

**잔재 23건 원장** — 미머지 = `git rev-list --count main..origin/<브랜치>` (위상적 수치다. squash 머지로
내용은 이미 반영됐을 수 있다). **PR 복원망 밖** = 그 커밋 중 어떤 PR 의 `head.sha` 도 아닌 것의 수
(PR head sha 집합 501개와 전건 대조).

★**이 23건은 지금 안전하다** — 원격 ref 가 살아 있으니 커밋도 원격에서 도달 가능하다. 아래의
「PR 복원망 밖」은 **그 원격 브랜치까지 지웠을 때** 노출되는 수이지 현재 상태가 아니다.
로컬 축의 「안전망 밖」과는 **다른 기준**이다(그쪽은 원격 도달성까지 포함해 이미 밖이다).
2026-08-12 codex 적대 리뷰가 두 수치를 같은 이름으로 부른 것을 지적했고, 이 문단이 그 정정이다.

| 브랜치                                 | 팁 sha     | 마지막 커밋 | 미머지 | PR복원망 밖 | 분류 |
| -------------------------------------- | ---------- | ----------- | -----: | ----------: | ---- |
| `feat/tpsl-phase3-c-fe`                | `3b8e589c` | 2026-06-26  |      1 |           1 | C    |
| `feat/h2s11-a-geo-block`               | `a29067e0` | 2026-04-25  |      1 |           1 | C    |
| `feat/h2s11-b-legal-temporary`         | `da18eb81` | 2026-04-25  |      2 |           2 | C    |
| `feat/h2s11-c-waitlist`                | `aae3b5e7` | 2026-04-25  |      6 |           6 | C    |
| `feat/h2s11-d-onboarding`              | `5cd93921` | 2026-04-25  |      5 |           5 | C    |
| `feat/h2s11-e-service-lock`            | `76439a1a` | 2026-04-25  |     12 |          12 | C    |
| `feat/h2s11-f-slowapi-minor`           | `739369ba` | 2026-04-25  |     12 |          12 | C    |
| `feat/h2s11-g-error-class-allowlist`   | `0fb35351` | 2026-04-25  |     12 |          12 | C    |
| `feat/h2s12-a-slack`                   | `13e7856f` | 2026-04-25  |      3 |           3 | C    |
| `feat/h2s12-c-bybit-ws`                | `65bc86af` | 2026-04-25  |      9 |           9 | C    |
| `feat/h2s9-frontend-mcwfa`             | `6c2b7ea7` | 2026-04-24  |      4 |           4 | C    |
| `feat/h2s9-observability`              | `3452af9d` | 2026-04-24  |      6 |           6 | C    |
| `feat/h2s9-stress-api`                 | `85ba39c2` | 2026-04-24  |      4 |           4 | C    |
| `feat/h2s9-stress-engine`              | `648c578a` | 2026-04-24  |      3 |           3 | C    |
| `worktree-feat-deploy`                 | `611442fb` | 2026-08-07  |      3 |           3 | D    |
| `docs/post-503-sync`                   | `0f4061d0` | 2026-07-30  |      2 |           1 | D    |
| `feat/live-observability`              | `7c6e8006` | 2026-07-28  |      2 |           1 | D    |
| `stage/refactor-audit-tier1`           | `f751f200` | 2026-05-13  |      2 |           1 | D    |
| `chore/sprint56-post-merge-followup`   | `79d5b8e8` | 2026-05-11  |      2 |           1 | D    |
| `stage/h2-sprint26-signal`             | `cb8e62c8` | 2026-05-04  |      9 |           7 | D    |
| `stage/h2-sprint27-beta-prereq-hotfix` | `54b99598` | 2026-05-04  |      3 |           2 | D    |
| `stage/h2-sprint27-dogfood-day1`       | `12ecc15b` | 2026-05-04  |      5 |           4 | D    |
| `feat/sprint6-trading-impl-v2`         | `170e9872` | 2026-04-17  |     44 |          42 | D    |

합계: C 미머지 80 / PR복원망 밖 **80** (PR 이 없으니 전부 밖) · D 미머지 72 / PR복원망 밖 **62**
(나머지 10개는 다른 PR 의 head sha 라 그 PR 의 복원 버튼이 되살린다). 총 152 중 **142**.
다시 말하지만 이 142 는 **원격 ref 까지 지웠을 때**의 노출분이다 — 지금은 원격이 안전망이다.

C 14건 중 13건이 `feat/h2s9`~`h2s12` 계열이고 마지막 커밋이 2026-04-24~25 에 몰려 있다 — 한 회차가
브랜치를 여러 개 끊어 놓고 PR 없이 접었을 가능성이 높다. `worktree-feat-deploy` 는 마지막 커밋이
**2026-08-07(5일 전)** 로 유일하게 최근이며, 워크트리가 잡고 있는 `worktree-feat-deploy2` 와는
**다른 브랜치**다.

**로컬 보류 39건 원장** — 미머지 = `git rev-list --count main..<브랜치>`. **안전망 밖** = 그 커밋 중
`git rev-list --remotes=origin` 으로 도달할 수도 없고 어떤 PR 의 `head.sha` 도 아닌 것 = **이 랩톱에만**
있는 커밋이다.

| 브랜치                             | 팁 sha     | 마지막 커밋 | 미머지 | 안전망 밖 |
| ---------------------------------- | ---------- | ----------- | -----: | --------: |
| `stage/migration-guard`            | `a41d667f` | 2026-08-10  |      1 |         1 |
| `stage/metric-guard-residual`      | `c19b8e60` | 2026-08-03  |      3 |         3 |
| `docs/bl536-citation-anchor`       | `452d3eb9` | 2026-08-01  |      1 |         1 |
| `docs/documentation-architecture`  | `f3a3c93c` | 2026-08-01  |      1 |         1 |
| `wt/divsplit`                      | `fb199bf9` | 2026-08-01  |      2 |         2 |
| `wt/ledgerhygiene`                 | `e4d8531e` | 2026-08-01  |      4 |         4 |
| `tmp/prefix-w1`                    | `7c9f70e8` | 2026-07-31  |      2 |         2 |
| `wt/bracket`                       | `b6cf0f42` | 2026-07-31  |      1 |         1 |
| `wt/docdrift`                      | `5fd77edb` | 2026-07-31  |      1 |         1 |
| `docs/roadmap-sync-post-481`       | `4f059475` | 2026-07-26  |      1 |         1 |
| `tc/alerts-be`                     | `b85a1681` | 2026-07-24  |      6 |         6 |
| `tc/cockpit-fe`                    | `8c2733f5` | 2026-07-24  |     12 |        12 |
| `tc/funding-be`                    | `1fd68b5b` | 2026-07-24  |      1 |         1 |
| `tc/funding-fe`                    | `2dee36d3` | 2026-07-24  |      5 |         5 |
| `tc/optimizer-fe`                  | `9d669375` | 2026-07-24  |      1 |         1 |
| `tc/position-be`                   | `e1f9b3b5` | 2026-07-24  |      1 |         1 |
| `tc/publish-be`                    | `a1561271` | 2026-07-24  |     11 |        11 |
| `tc/realtime-be`                   | `99413d4c` | 2026-07-24  |      1 |         1 |
| `tc/realtime-fe`                   | `2d9b8467` | 2026-07-24  |      6 |         6 |
| `fp/backtest`                      | `975ded17` | 2026-07-23  |      2 |         2 |
| `fp/optimizer`                     | `5c9a0d55` | 2026-07-23  |      2 |         2 |
| `fp/strategies`                    | `4357819f` | 2026-07-23  |      2 |         2 |
| `fp/trading`                       | `dd5f9b58` | 2026-07-23  |      2 |         2 |
| `s7-dashboard`                     | `eafd17e0` | 2026-07-21  |     39 |        39 |
| `w2-report-detail`                 | `221f5148` | 2026-07-21  |      5 |         5 |
| `w3a-backtest-new`                 | `2bcd0e17` | 2026-07-21  |     26 |        26 |
| `w3b-strategies`                   | `d31ab76e` | 2026-07-21  |     11 |        11 |
| `w3c-optimizer`                    | `3fa96622` | 2026-07-21  |     10 |        10 |
| `w3d-orders`                       | `e112052d` | 2026-07-21  |     26 |        26 |
| `w3e-onboarding`                   | `c1b0a243` | 2026-07-21  |     26 |        26 |
| `w3f-live-sessions`                | `107c98fc` | 2026-07-21  |     29 |        29 |
| `w3fix-fidelity`                   | `120c1411` | 2026-07-21  |     29 |        29 |
| `w3g-marketing`                    | `bd907324` | 2026-07-21  |     32 |        32 |
| `w3h-error-pages`                  | `eff58582` | 2026-07-21  |      6 |         6 |
| `worktree-wf_aefca278-eae-1`       | `16d3d55e` | 2026-07-20  |      3 |         3 |
| `integration/tv-parity-dogfood`    | `aa8be31f` | 2026-07-05  |     13 |        11 |
| `chore/bl-238-239-240-cicd-prereq` | `c624a6cb` | 2026-05-11  |      1 |         1 |
| `chore/sprint58-closeout`          | `32b833d6` | 2026-05-11  |     13 |        13 |
| `_eps_local`                       | `dead5c96` | 2026-05-05  |      1 |         1 |

합계: 미머지 **339** · 안전망 밖 **337**. 덩어리가 셋 보인다 — `w2`~`w3h`+`s7-dashboard` **11건**
(2026-07-21, 밖 **239**) · `tc/*` 9건(2026-07-24, 밖 44) · `fp/*` 4건(2026-07-23, 밖 8). 각각 한 회차가
병렬 워커로 끊어 놓고 PR 없이 접은 흔적이다. 나머지 **15건**(밖 46)은 개별 판정이 필요하다.
★이 네 수치는 손으로 세었다가 틀려서(10건/240/16건) `awk` 로 다시 세었다 — 39 = 11+9+4+15,
337 = 239+44+8+46 이 성립한다.

★**내 판정기가 두 번 틀렸고 두 번 다 내가 잡았다.**
⑴ 안전망을 **브랜치 이름 일치**로 봤다 — `feat/tpsl-phase3-fe-perf` 는 원격 `feat/tpsl-phase3-c-fe`
와 **같은 팁 sha**(`3b8e589c`)인데 이름이 달라 「안전망 없음」으로 셌다. 안전망은 이름이 아니라
**sha** 로 본다.
⑵ 고치면서 `git rev-list --all --remotes=origin` 을 썼다. `--all` 이 **로컬 ref 까지** 포함시켜
로컬 브랜치 팁이 자기 자신 때문에 집합에 들어갔다 — **165건 전부 「안전」이라는 항진명제**가 나왔다
(집합 1,635 → `--all` 제거 후 1,034. 601개가 가짜였다). 판별력 시험을 세우고서야 드러났다:
`git commit-tree` 로 원격에 없는 커밋을 만들어 「안전망 밖」으로 판정되는지 확인(PASS), origin/main
팁이 「안 」으로 판정되는지 확인(PASS).

**처방 (다음 회차 몫)**

1. D 9건 — 미머지 커밋 72개(그중 **안전망 밖 62개**가 실제 위험분)를 `git log main..origin/<브랜치>`
   로 읽어 main 반영 여부 판정. 살릴 것이 있으면 cherry-pick, 없으면 삭제.
   위험이 몰린 곳은 `feat/sprint6-trading-impl-v2` **42개**와 `stage/h2-sprint26-signal` **7개**로,
   둘이 62개 중 49개다 — 여기부터 읽어라
2. C 14건 — `feat/h2s9`~`h2s12` 13건을 한 덩어리로 판정(같은 회차 유래로 보인다).
   `feat/tpsl-phase3-c-fe` 는 별건
3. **로컬 39건 — 여기가 더 급하다.** 안전망 밖 337 커밋이 이 랩톱에만 있다. 덩어리부터 쳐라:
   `w`계열 11건(밖 239) → `tc/*` 9건(밖 44) → `fp/*` 4건(밖 8) → 나머지 15건(밖 46).
   살릴 것이 있으면 **브랜치를 지우기 전에 원격으로 push** 해라 — 그러면 안전망이 생겨
   그 뒤로는 원격 축 절차로 넘어간다
4. 삭제 시 이 회차의 4겹 검증(빈 입력 가드 · 양성 대조 · 음성 대조 전건 교차 · 분할 완전성)을
   재사용하고, **판별력 시험을 먼저 세워라** — 이 회차의 안전망 집합이 항진명제였던 적이 있다
5. 삭제 직전 **`git ls-remote --heads origin` 과 로컬 `refs/remotes/origin/*` 을 대조**해라.
   `git rev-list --remotes=origin` 은 로컬 추적 ref 를 읽으므로 stale 이면 「원격에 있다」가
   거짓이 된다. 대조 결과 차이가 `origin/HEAD` 한 줄뿐이어야 정상이다
6. 안전망을 근거로 지울 때는 **후보 전건**의 sha 를 `gh api repos/:o/:r/commits/<sha>` 로 확인해라.
   표본은 전건을 입증하지 않는다 (이번에 121/121 을 돌려 MISS 0 을 확인했다)

**복구 근거**

- 원격 267건의 브랜치명·팁 sha·PR 번호 → `.git/branch-debris-restore-20260812.tsv`
- 로컬 126건의 브랜치명·팁 sha·안전망 종류 → `.git/local-debris-restore-20260812.tsv`
- 둘 다 git 이 추적하지 않는 **로컬 사본**이다. 진짜 안전망은 GitHub 쪽이고, 삭제한 sha 를
  GitHub 이 아직 서빙한다는 것은 로컬 121건 **전건**(121/121 OK) + 원격 표본 5/5 로 확인했다
  (위 「안전망 가설을 실증했다」 참조).

**Risk:** 🟢 (잔재 23건은 `git branch -r` 가독성 말고는 아무것도 막지 않는다)

---

### BL-716

**Title:** dev-log 22회차 반증 카드의 `lessons.md` 승격 누락 (docs-diet 가 버퍼를 승격 없이 비웠다)
**Category:** Docs / 지식 정본
**Priority:** P1
**Trigger:** `lessons.md` 에 자리를 만든 뒤 (stale 항목 `docs/archive/` 강등이 선행) / 다음 문서 회차
**Est:** M
**상태:** ✅ **Resolved** (2026-08-14 gate-surface-close) — 승격 이행 완료. ★**착수 전제 2건이 실측으로 반증됐고, 그 반증이 이 항목의 최대 산출이다.** ⑴ 처방 ⑵ 「반복 3회 이상 패턴을 **카드로 올린다**」는 `lessons.md:12` 자기 규약(「반복 패턴이 동일하면 새 항목 만들지 말고 기존 항목의 **반복 횟수 증가**」)과 충돌한다 — 후보 3종이 **전부 이미 카드/승격 완료** 상태였다. ⑵ 그래서 「자리 확보 선행」도 불필요했다: 정본 동작(누적 갱신 + 3/3 승격)은 줄을 늘리는 게 아니라 **줄였다** — `lessons.md` **362 → 358줄**(cap 400, 여유 42). 이행 = ① [LESSON-101] 「대조기는 자기 입력이 비었는지 먼저 말해야 한다」를 **14회**(dev-log 22줄 중 12 + 기존 2)로 `generator-evaluator-pipeline.md` **§8.6** 승격 ② 「착수 전제 반증」 축(**12/22**)은 이미 §8.1 로 승격돼 있어 **§8.1 에 기저율만 보강**(일화 → 기저율) ③ 선행 수리 2건 — `LESSON-101` **ID 충돌**(`8abd0d67` 이 기존 번호에 덮어썼다) 해소 = harness 판을 **[LESSON-107]** 로 재번호 · 영구 승격 표와 카드 본문의 **죽은 경로 10곳**(`backend/AGENTS.md`·`frontend/AGENTS.md` — [ADR-029] 로 이동) 정정.
**트리거 판정:** ~~미도래 — 선행 조건이 `lessons.md` 의 **자리 확보**다. 현재 362/400줄이라 22건을 1:1 로 올리면 상한을 넘긴다~~ → **2026-08-14 반증.** 「22건 1:1」이 전제였고 그 전제가 규약 위반이었다. 정본 동작으로는 자리 확보가 **선행 조건이 아니다**(실측 −4줄). ★**DEFERRED 판정이 틀린 처방을 근거로 삼으면 항목이 부당하게 잠긴다** — 트리거를 적을 때 처방의 정당성을 같이 재라
**출처:** 2026-08-13 docs-diet · codex 적대 리뷰가 P1 으로 적발(자기신고 후 독립 확인)

**원인 / 영향:** ADR-026 은 기록을 3층으로 설계했다 — **INDEX**(발견 색인) / **lessons.md**(지식 정본) /
**git**(원문 검증). docs-diet 는 버퍼(dev-log 본문)를 비우면서 가운데 층을 채우지 않아, 22회차의 지식이
**발견 층과 검증 층에만** 남았다. §5 가 「git 은 발견 매체가 아니다」라고 못박았으므로 「git 에 있다」는
이 결손의 답이 되지 못한다.

**★이미 확보된 완화:** 22건 각각이 `dev-log/INDEX.md` 에 **★★★반증을 담은 300자 이내 한 줄**을 갖고 있다
(요약이 비어 있던 2건은 삭제 **전에** 본문에서 뽑아 채웠다). 즉 「무엇이 반증됐나」는 온라인에서 읽히고,
잃은 것은 **패턴이 3회 반복됐을 때 규칙으로 승격되는 경로**다.

**처방 — ~~초판~~ → 2026-08-14 재계수로 교체:**

~~1. stale 항목을 archive 로 내려 자리를 만든다. 2. INDEX 22줄에서 반복 3회 이상 패턴만 **카드로 올린다**.~~
→ 정본 동작은 **카드 신설이 아니라 기존 카드의 누적 갱신 + 3/3 도달분 승격**이다(`lessons.md:12`).

**★초벌 후보 3종의 실제 반복 횟수 (모집단 = INDEX 22줄, 스코프 명시 = [LESSON-089]):**

| 후보                                    | 원장 주장    | 실측      | 판정                                                            |
| --------------------------------------- | ------------ | --------- | --------------------------------------------------------------- |
| ① 내 검사기가 판별력 0 / 빈 입력에 초록 | 「5회 이상」 | **12/22** | ✅ 승격 — [LESSON-101] → `generator-evaluator-pipeline.md` §8.6 |
| ② 변이 전건 red 를 통과한 구현에 P1     | 「3회」      | **1/22**  | ❌ **반증 — 문턱 미달**. 승격하지 않는다                        |
| ③ 착수 전제·상속 사실이 반증됐다        | 「3회」      | **12/22** | ✅ 이미 §8.1 승격 상태 ⇒ **기저율 보강만**                      |

★**② 가 1/22 인 것은 나쁜 소식이 아니라 좋은 소식이다** — 22회차 동안 변이 규율을 통과하고도 P1 이
남은 사례가 **1건**(close-ownership-axis)뿐이라는 뜻이다. 원장의 「3회」는 스코프 밖(2026-08-10
migration-guard)까지 끌어와야 겨우 닿는데, 그것이 정확히 [LESSON-089]가 경고한 「스코프를 안 적은
판별력 수치」다. **원장이 자기 항목 안에서 그 병을 재현했다.**

**★남은 결손 1건 (이 회차가 안 고쳤다):** 죽은 경로 10곳을 **어느 게이트도 안 잡았다**.
`docs-audit` 의 `legacy_paths`(`:76-86`)에 [ADR-029] 의 `backend/`→`apps/api/` · `frontend/`→`apps/web/`
가 **없고**, 백틱 코드 스팬은 `link_re`(`:26`)의 `[..](..)` 매칭 밖이라 링크 검사도 못 본다.
`lessons.md` 에 대한 검사는 **줄 수 상한과 깨진 링크 2종뿐**이며 **ID 유일성 검사가 없어**
같은 번호 2장이 초록으로 통과했다 ⇒ [BL-720].

**원문:** 지운 25건 전량 = `git show 8abd0d67:docs/dev-log/<파일명>` (25/25 복구 가능함을 확인했다).

### BL-717

**Title:** API 계약축 PoC — OpenAPI export + 생성 client 후보 비교
**Category:** Architecture / 계약축
**Priority:** P2
**Trigger:** PR-1(모노레포 재배치, [ADR-029]) 머지 후
**Est:** M
**상태:** ✅ **Resolved** (2026-08-13 contract-poc, [ADR-031]) — AC 5종 전부 이행. ① 결정적 export
(`apps/api/scripts/export_openapi.py` → `contracts/openapi/openapi.json`, 2회 sha 동일 + `--check`
양·음성 실증) ② 후보 판정 = **orval(client:'zod') 채택** — zod v4 API 직출력·tsc strict·수기(zod/v4)와
런타임 공존 vitest 3/3. openapi-typescript 는 타입 전용 차점, hey-api 는 0.99/0.98 모두 자체 TS7
의존과 비호환 크래시로 **실행 불가 탈락** ③ 구조 diff: Decimal→string 충실 · **datetime 엄격도
역전**(계약 Z-only vs 수기 offset 허용 — BE 실직렬화 실측 전 런타임 경계 투입 금지) ④ drift 게이트
스케치(ci.yml 미배선 — 도입 회차 몫) ⑤ 번들 = 3endpoint 2.9KB min+gz(zod external·현재 delta 0,
ANALYZE 대비는 판별력 0 이라 esbuild 한계비용으로 대체·사유 ADR 명기). 전면 전환·CI 배선·datetime
실측은 [ADR-031] §비결정.
~~**트리거 판정:** 미도래 — PR-1 미머지.~~ → **2026-08-13 도래**(PR #619 머지)·같은 날 이행.
**출처:** 2026-08-13 monorepo-realign (사용자 결정 ③ 「PoC 먼저」)

**처방:**

1. `apps/api` 에 결정적 openapi.json export — FastAPI `app.openapi()` 덤프 + 키 정렬 직렬화 →
   `contracts/openapi/openapi.json` (같은 코드에서 두 번 export 하면 byte-identical 이어야 한다).
2. 엔드포인트 2~3개(health + strategies list + backtest status 급)로 후보 3종 생성 비교 —
   `openapi-typescript`+`openapi-fetch` / `orval`(Zod 출력 — FE zod v4 체계와 정합 후보) /
   `@hey-api/openapi-ts`. ★도구 현행성은 착수 시 재확인한다.
3. AC — ⑴ 각 산출물 `apps/web` tsc strict 통과 ⑵ zod v4 호환 실증(`zod/v4` import 규칙,
   `apps/web/AGENTS.md` §8 — v3 경로 `"zod"` 금지와 공존하는가) ⑶ 기존 `features/[domain]/api.ts`
   수기 타입과 생성 타입의 구조 diff 리포트 ⑷ CI drift 게이트 스케치(export 재실행 diff=0)
   ⑸ 번들 영향 수치(`ANALYZE=1`).
4. 결론 = 채택 후보 1개 + 도입 범위. **전면 전환은 비목표** — 별도 회차(~~ADR-030~~ →
   **[ADR-031]** 로 기록 — 030 은 harness-pilot-verdict 가 선점, PR #623).

### BL-719

**Title:** 재배치 머지 롤아웃 lockstep — 레포 밖 상태 3종 재설치
**Category:** Ops / 롤아웃
**Priority:** P1
**Trigger:** PR-1 머지 직후 (즉시 착수)
**Est:** S
**상태:** ✅ **해결 완료 (2026-08-13)** — PR #619 머지(12:38Z) 직후 절차 5단계를 순서대로 완주했다(아래
「이행 기록」). 소크 서버 pin `c3a39d0d`(기록 13:02:03Z → worker 재기동 13:02:44Z, mount ns 실측으로
순서 정합) · 맥 롤아웃 완료(스택 6컨테이너 Healthy · strategies 3행 = 볼륨 무손실) · canary #620 이
backend 3레인 발화 + FE 정상 skip 을 실증. 이행 중 실물 결함 1건이 나와 핫픽스 #621 로 닫았다
(`soak-stack.sh` tar `--strip-components` 2→3 — 숫자로 인코딩된 깊이는 리터럴 스윕의 사각).
**트리거 판정:** 이행 완료 — 2026-08-13 PR-1 머지로 도래했고 같은 날 완주. 잔여 없음.
**출처:** 2026-08-13 monorepo-realign

**절차 (순서 엄수):**

1. **소크 서버** — ① `soak-gate.sh --status` 기록 ② pull **전에** 구경로로
   `scripts/soak-gate.sh --uninstall`(pull 후에는 구 스크립트가 없어 systemd 유닛이 죽은 경로를 문다)
   ③ `scripts/soak-stack.sh down`(★소크 창 단절 불가피 — 머지 타이밍은 PASS 표본 직후 권장)
   ④ `git pull` ⑤ `mkdir -p apps/api/.metrics && mv backend/.metrics/*.db apps/api/.metrics/`
   (prometheus counter 연속) + 서버 `.env` 의 구경로 명시값 점검 ⑥ `tools/scripts/soak-stack.sh pin
<merge-sha>` → `up` ⑦ `tools/scripts/soak-gate.sh --install` + 수동 1회 ~~PASS~~ 판독
   (★2026-08-13 이행이 이 전제를 반증 — PASS 판정은 C1 「24h 창 3회」라 **리셋 직후 정의상 불가**.
   실측 가능한 AC 는 「게이트 실행 정상 + C5 측정 무결 6/6 + stack_pinned ✓」이고 그것으로 판정했다.
   codex 적대 리뷰 G6-F1 이 절차·기록의 이 불일치를 지적해 여기 박는다).
2. **맥 LaunchAgent** — `tools/scripts/nightly-real-broker-local.sh --install` 재실행
   (plist ProgramArguments·WorkingDirectory 가 구 `scripts/` 절대경로).
3. **각 체크아웃 untracked 이행** — `.env.local` 2벌 mv · `.venv` 는 mv 금지(`cd apps/api && uv sync`
   재생성) · `.next` 폐기([BL-650]) · `cd apps/web && pnpm install`. 메인은
   `mise run up-isolated-build`(컨텍스트 변경 재빌드) 후 `:8100/health` + `docker volume ls` 불변 확인.
4. **워크트리 전부 재생성** — `tools/scripts/worktree-bootstrap.sh`. 개인 `settings.local.json` 의
   `cd backend` 계열 allow 항목은 각자 갱신.
5. **canary 소PR** — `apps/api` 단독 1줄 변경으로 backend CI 계열(backend·backend_static·
   backend_coverage)이 skip 아닌 실행인지 확인. 이동 PR 자체는 구경로 삭제로도 발화하므로
   **진짜 함정은 머지 후 첫 PR** 이다.

**이행 기록 (2026-08-13 · 단계별):**

1. **서버 lockstep 완주** — uninstall → down → pull → `.metrics/*.db` 이행 → pin `c3a39d0d` → up →
   `--install` + 수동 판독. ★첫 판독 = **FAIL 실격 1건**(tick_stall `de3db35a` 12:57:37~13:03:24Z,
   lag 7.4분)인데 이것은 결함이 아니라 **이 절차의 down 창 자체**다 — 「소크 창 단절 불가피」가 예고한
   그 단절이고 창 리셋은 예정대로(귀속 원장에 operational 등재). ★절차의 「수동 1회 **PASS**」는
   리셋 직후에 정의상 불가능한 요구였다(PASS 는 C1 24h 창 3회) — 실제 확인한 것은 **게이트 실행
   정상 + C5 측정 무결 6/6 + stack_pinned ✓** 이다(2026-08-13 13:34Z 재판독으로 재확인).
2. **맥 LaunchAgent 재설치 완료.**
3. **메인 체크아웃 이행 완료** — `mise run up-isolated-build` 후 6컨테이너 Healthy · strategies 3행 =
   볼륨 무손실. ★잔재 삭제 allowlist 가 처음에 `.env.production.local`·e2e 인증 상태·데모샷을
   몰랐다 — **중단-후-분류**가 시크릿 소실을 막았다(맹목 rm 금지, [ADR-029] 반증 카드).
4. **워크트리는 0벌** — docs-diet(#618)가 전량 제거(브랜치 ref 보존). 재생성은 착수 시
   `tools/scripts/worktree-bootstrap.sh`(실재 확인). `settings.local.json` allowlist 갱신은 각자 몫.
5. **canary #620 발화 확인** — backend·backend_static·backend_coverage 실행(skip 아님) + FE 레인
   정상 skip = 판별력 양방향 확인. 핫픽스 #621 은 서버 pin 단계의 실측 발화가 낳았다.

### BL-720

**Title:** `docs-audit` 의 지식 정본 축 결손 — ID 유일성·[ADR-029] 죽은 경로·백틱 코드 스팬을 아무도 안 본다
**Category:** Ops / 게이트 표면
**Priority:** P2
**Trigger:** 도래 — 결손 3종이 실측으로 확정됐고 처방이 우리 손 안에 있다
**Est:** S
**상태:** ✅ **Resolved** (2026-08-14 gate-pointer-axis) — 축 **2종**을 `docs-audit.sh` 에 심었고 하네스는 7→**12 케이스**다. ★**등재된 처방 3개 중 ②는 이행 불가로 폐기**했고(아래 「처방 재판정」), ①③은 하나의 포인터 축으로 합쳤다. ★**새 축이 실제 트리에서 오탐 3건을 냈다** — 스텁 하네스는 12/12 초록이었고, 진짜 `docs/lessons.md` 에 대고 돌린 뒤에야 드러났다.
**트리거 판정:** 도래 — 조건절이 없다. 대상 파일(`tools/scripts/docs-audit.sh`)과 결손 3종이 확정돼 있고, 각각을 재현하는 입력이 이미 레포 히스토리에 있다 (2026-08-14 gate-surface-close)
**출처:** 2026-08-14 gate-surface-close ([BL-716] 이행 중 발견)

**원인 / 영향:** `docs-audit.sh` 가 `docs/lessons.md` 에 대해 강제하는 것은 **줄 수 상한(400)과 깨진
마크다운 링크 2종뿐**이다. 그 결과 아래 셋이 **전부 초록으로 통과**했다:

1. **ID 유일성 검사 없음** — `8abd0d67` 이 `LESSON-101` 을 이미 존재하는 번호로 등재해 **같은 번호
   카드가 2장**이 됐다. 파일 내 순서도 `101 → 100 → 101` 로 깨졌는데 게이트는 rc=0 이었다.
   (2026-08-14 에 harness 판을 `LESSON-107` 로 재번호해 해소)
2. **[ADR-029] 이동 경로가 `legacy_paths` 에 없다** — `docs-audit.sh:76-86` 의 목록은 `docs/` 내부
   재편만 담고 있고 `backend/`→`apps/api/` · `frontend/`→`apps/web/` 가 **빠져 있다**.
3. **백틱 코드 스팬은 링크 검사 밖** — `link_re`(`:26`)는 마크다운 인라인 링크 문법만 잡는다. 규칙 파일
   포인터는 관례상 `` `apps/api/AGENTS.md` §10 `` 형태의 **코드 스팬**이라 검사에 안 걸린다.

⇒ 2+3 이 겹쳐 `lessons.md` 영구 승격 표 12행 중 **7행이 존재하지 않는 파일을 가리키는 상태**로
남아 있었다(본문 포함 **10곳**). 승격 표는 「본문은 저기 있다」는 **유일한 포인터**이므로, 그것이
죽으면 승격된 지식은 **찾을 수 없다** — ADR-026 이 세운 3층 중 정본 층으로 가는 길이 끊긴 것이다.

**처방 (등재 시점 — ①은 아래에서 반증됐다):**

1. ~~`legacy_paths` 에 `backend/`→`apps/api/` · `frontend/`→`apps/web/` 추가.~~ → **폐기**
2. 코드 스팬 경로 검사 축 신설 — `` `<경로>` `` 중 레포 루트 기준 실재하지 않는 것을 잡는다.
   대상을 `lessons.md` 승격 표처럼 「포인터가 정본인 자리」로 좁혀서 시작해라. → **이행**
3. `lessons.md` ID 유일성 + 오름차순 검사. **음성 대조 의무.** → **이행**

**★처방 재판정 (2026-08-14 착수 전 실측):**

① 은 **이행 불가**다. `legacy_paths` 판정은 `if legacy in text` — **파일 전체 부분문자열**이라
(`docs-audit.sh:100-102`) 예외를 못 준다. 살아 있는 문서(frozen 3종 제외)에 `backend/`·`frontend/`
리터럴이 **147줄**이고, 그중 다수가 **고칠 수 없는 정당한 인용**이다:
[ADR-029](decisions/029-monorepo-standard-layout.md) 의 **이동 매핑 표 자신**(:22-23 — 여기서 지우면
ADR 이 무엇을 옮겼는지 말할 수 없다) · `lessons.md` 의 그때 실측 기록 · `status.md` 재배치 서사.
⇒ 등재문이 스스로 단 경고(「과거 서사는 정당한 인용」)가 **예외가 아니라 지배적 다수**였다.
죽은 포인터는 축 ②가 **이유 불문** 잡으므로(`` `backend/AGENTS.md` `` 도 같은 축에서 red) 흡수했다.

**이행 (2026-08-14 gate-pointer-axis):**

- 축 ㉮ **LESSON ID 유일성 + 오름차순** — 판정 집합은 `^### ` 카드 헤딩 **∪ 승격 표 행**이다.
  실제 사고(`8abd0d67`)가 「표에 이미 있는 101 을 새 카드로 등재」였으므로 헤딩만 보면 다시 샌다.
  ★**결번은 정상**(092·101 은 표로 이동, 086 이하는 archive) — 금지하는 것은 중복과 역순뿐.
  ★현재 레포는 위반 0 이라 **순수 회귀 가드**이고, 그래서 **하네스가 유일한 증인**이다.
- 축 ㉯ **승격 표 백틱 포인터 실재** — 범위는 `## 영구 승격 완료` ~ 다음 `---`/`##` 까지.
- 부수로 `lessons.md` 승격 표의 `generator-evaluator-pipeline.md` 포인터 **10곳**(표 6 + 본문 4)을
  마크다운 링크로 바꿨다 — **맨 파일명은 루트에도 `docs/` 밑에도 없다**. 이제 기존 링크 검사가 덮고
  클릭도 된다. 표에 남은 백틱 7행(`apps/*/AGENTS.md`)은 축 ㉯ 가 덮는다 — **두 축 다 실제 행으로 발화**한다.

**★★이 회차가 밟은 것 — 스텁 초록이 진짜 트리를 보증하지 않는다:**

하네스 11/11 이 초록인 상태에서 진짜 `docs/lessons.md` 에 대고 돌리니 축 ㉯ 가 **9건**을 냈고,
링크 수리 후에도 **3건이 남았다** — 전부 오탐이었다:
`` `tests/<domain>/test_*_commits.py` ``(자리표시자+글롭) · `` `asyncio.<Semaphore/Lock/Event/Queue>` ``
(코드 표현식) · `` `/deepen-modules` ``(슬래시 커맨드). 후보 규칙이 「`/` 를 포함하거나 `.md` 로
끝난다」뿐이었다. 배제 축(`<>*?` 포함 · `/` 로 시작)은 실패 축과 **직교**하므로 죽은 포인터는
그대로 다 걸린다. 케이스 ⑿ 가 그 세 스팬을 **입력으로 그대로** 옮겨 심었다 — 배제를 되돌리면 red.
⇒ **오탐을 내는 검사기는 꺼진다.** 스텁은 「내가 상상한 입력」이고 정본 파일은 「실제 입력」이다.

**★★적대 프로브가 새 축을 **2군데 뚫었다** (2026-08-14 · `/codex` 축 대체 수행):**

codex 는 2회 시도 모두 실패했다(1차 stdin 대기 25분 정지 · 2차 50분에 findings 0 이고 훑던 파일이
이 회차 diff 밖이었다). 그래서 CONTROL 이 직접 프로브 5종을 짰고, **2종이 실제로 뚫었다**:

| 공격                                                           | 결과             |
| -------------------------------------------------------------- | ---------------- |
| 표 ID 를 볼드로 — `\| **LESSON-101** \|` + 같은 번호 카드      | ✗✗ **초록 통과** |
| 헤딩을 링크로 — `### [LESSON-101](#...)` + 표 같은 번호        | ✗✗ **초록 통과** |
| 헤딩 역순 · 볼드+백틱 죽은 포인터 · 표 안 죽은 스크립트 포인터 | ✓ 발화           |

원인 — `^### LESSON-(\d+)\b` 와 `^\|\s*LESSON-(\d+)\s*\|` 가 **마크다운 장식을 통과 못 한다.**
볼드나 링크 하나로 ID 가 수집 집합에서 빠지고 중복이 그대로 샌다. ⇒ **이 축이 막으려는 사고
(`8abd0d67` 의 중복 101)를 서식만 바꿔 재현할 수 있었다.** 수리 = ID 앞의 `*`·`[`·공백을 버리는
`_LESSON_DECOR` 를 두 정규식에 삽입(뒤의 `\b` 유지 — `LESSON-1010` 오인 방지). 프로브 5/5 발화.
하네스에 **영구 케이스 ⒀⒁** 로 심었다(12 → **14 케이스**) — 케이스 ⑿ 과 같은 규율.

★**내 프로브 자신도 한 번 틀렸다** — 이름 문자열의 백틱이 셸 치환을 일으켜 에러를 뱉었고, 그
상태의 「침묵」은 진짜인지 프로브 결함인지 구분할 수 없었다. 따옴표를 고쳐 **다시 재고 나서**
판정했다. **깨진 검사기의 결과는 초록이든 빨강이든 못 믿는다.**

**★이 항목 자신이 §8.6 의 사례다** — 검사기가 보는 표면(줄 수·마크다운 링크)이 실패 표면(ID·경로·
스팬)보다 좁았고, 그래서 초록은 「통과했다」가 아니라 **「그 축을 안 봤다」**였다.
★★그리고 **수리한 축조차 같은 병을 한 겹 더 갖고 있었다** — 서식이라는 축을 안 보고 있었다.

### BL-721

**Title:** 마감 게이트 전량 1회가 15~20분 — CI 가 이미 도는 것을 로컬이 직렬로 중복한다
**Category:** Ops / 게이트 비용
**Priority:** P2
**Trigger:** 도래 — 실측이 있고 처방이 우리 손 안에 있다
**Est:** S
**상태:** ✅ **Resolved** (2026-08-14 gate-2stage) — 게이트를 **2단**으로 갈랐다. `--pre-pr`(무거운 9종 유예, ~1분) → PR push → **CI 와 나란히** `--deferred-only`. ★**유예는 면제가 아니다** — 미룬 것을 `.claude/gates/<슬러그>/deferred.txt` 에 적고 종결 문구를 다르게 내며(「pre-PR 통과 — 이것은 종결 판정이 아니다」), `--deferred-only` 통과만이 그 파일을 지운다. 같은 「✓ 전건 통과」를 냈으면 「초록인데 안 봤다」가 됐을 것이다. 부수로 **게이트별 소요(초)**를 결과표에 실었다 — 다음 사람이 인상이 아니라 수치로 정하라고.
**트리거 판정:** 도래 — 조건절이 없다. 2026-08-14 gate-surface-close 가 전량 게이트를 **3회** 돌리며 회차 시간의 큰 몫을 태웠고, 그 자리에서 실측이 나왔다
**출처:** 2026-08-14 gate-surface-close 회고 (사용자 지적)

**근거 (실측):**

| 게이트                         |                                         소요 | CI 가 도나                     |
| ------------------------------ | -------------------------------------------: | ------------------------------ |
| BE pytest (4,604 passed)       |                                    **379초** | ✅ `backend` 잡이 **샤딩**해서 |
| e2e 3레인                      |                                       ~400초 | ✅ `e2e` 잡                    |
| CI fresh DB alembic · 커버리지 |                                     수십 초~ | ✅                             |
| 나머지 20종                    | 합계 **1분 안쪽** (최장 = FE build **17초**) | 일부만                         |

⇒ 로컬 전량 실행은 CI 를 **직렬·비샤딩으로 한 번 더** 하는 것이었다. 중간 검사로 쓰기엔 너무 비싸서
아무도 중간에 안 돌렸고, 그래서 결함이 **마지막 15분짜리 실행이 끝나고서야** 드러났다(이 회차의
FE lint FAIL 이 정확히 그랬다 — 30초면 알 수 있는 것이었다).

**산출:**

1. `final-gates.sh` — 모드 3종(`full`/`--pre-pr`/`--deferred-only`, 상호 배타) · `--dry-run`(계획만) ·
   유예 원장 · 게이트별 소요 · 모드별 종결 문구.
2. `final-gates-test.sh` **신설**(하네스 8종 → **9종**) — 케이스 8 · 변이 3 · 음성 대조 1.
   `--dry-run` 이 없었으면 이 계약은 **검사할 방법이 없었다**.
3. 문서 4곳 — `AGENTS.md` 개발 원칙 · `gates-and-traps.md` 2단 절차 절 · `status.md` ⓸④ · §G8.

**★이 회차가 밟은 것 2건 (둘 다 기록·수리):**

- **음성 대조가 거짓 보고를 막았다.** 변이 사본을 `$TMP` 에 뒀더니 `final-gates.sh` 의
  `ROOT="$(dirname "$0")/../.."` 가 엉뚱한 곳을 가리켜 **git status 에서 죽었고**, 변이가 무엇이든
  케이스가 전부 같은 이유로 red 였다. 그대로였으면 「변이 3종 전건 판별」이라는 **거짓 보고**가
  나갔다. 잡은 것은 등가 사본 N1 하나다(§8.6).
- **하네스가 내 수정을 잡았다.** `check_signal` 본문에 모드 분기를 넣었더니 `signal-check-test.sh`
  ㉑㉒㉓ 이 red 였다 — 그 하네스가 `record`/`skip_gate` **호출 횟수**로 배선을 고정하고 있었다.
  분기를 `signal_gate` wrapper 로 빼 계약을 지켰다. 앵커 A12 는 `signal_gate "` x4 로 옮기되,
  **신호 게이트 1벌을 지우면 여전히 발화하는지 양성 대조로 확인**했다(x3 발화 → 복원 26/26).

### BL-722

**Title:** `assert-main-checkout.sh` 는 파괴적 타깃의 가드인데 판별력 덮개가 없다
**Category:** Ops / 게이트 표면
**Priority:** P3
**Trigger:** 도래 — §8.7 성문화 중 스윕으로 확정. 대상 파일 1개·판정 3분기로 작다
**Est:** XS
**상태:** ✅ **Resolved** (2026-08-14 gate-pointer-axis) — `tools/scripts/assert-main-checkout-test.sh` 신설, 게이트 하네스 **9→10종**. ★**등재된 처방 2건이 둘 다 뒤집혔다**(아래 「처방 재판정」) — 방법 선택도, 케이스 ⑶ 의 기대 rc 도.
**트리거 판정:** 도래 — 조건절이 없고 대상이 확정돼 있다 (2026-08-14 gate-2stage)
**출처:** 2026-08-14 gate-2stage (§8.7 성문화 부수)

**원인 / 영향:** `assert-main-checkout.sh` 는 「여기는 메인 체크아웃인가」를 **판정**하고 아니면 0 이 아닌
코드로 죽는다. `mise run up`/`down`/`migrate`/`seed` 처럼 **공유 자원**(컨테이너 1벌 · 앱 DB `quantbridge` ·
Redis)을 건드리는 타깃이 이 가드 뒤에 있다. 즉 §8.7 기준으로 **판정기**인데 하네스도 `--selftest` 도
다른 층 테스트도 없다.

**왜 P3 인가 (부풀리지 않는다):** 실패 방향이 비대칭이다. 가드가 **과하게 죽으면** 사람이 즉시 안다
(타깃이 안 돈다). 위험한 방향은 **워크트리인데 「메인이다」로 통과**하는 것뿐이고, 그때 대가는
공유 DB 파손이다. 지금까지 그 사고 기록은 없다.

**처방 (등재 시점):** 임시 트리 fixture 로 ⑴ 메인 체크아웃 → rc=0 ⑵ 워크트리 → rc≠0
⑶ 비 git 디렉터리 → rc≠0 세 케이스 + 판정문을 뒤집는 변이 1종. §8.7 의 세 방법 중
**내장 `--selftest` 가 가장 싸 보인다** — 착수 시 재판단해라.

**★처방 재판정 (2026-08-14 — 등재문이 시킨 대로 재판단했고 둘 다 뒤집혔다):**

1. **방법** — `--selftest` 가 아니라 **별도 하네스**가 싸다. 호출 자리 두 곳이 **전부 이름 규약 기반**
   이다: `Makefile:427` 의 `for h in … ; do bash tools/scripts/$h-test.sh` 와 `final-gates.sh` 의
   `run_gate "<라벨> 하네스" … "$ROOT/tools/scripts/<이름>-test.sh"`. `--selftest` 는 그 루프 밖이라
   **양쪽에 특례 배선**이 필요하고, 게다가 `mise run up` 마다 실행되는 47줄 가드에 테스트 코드를 얹는다.
   별도 하네스는 루프에 이름 하나 + `run_gate` 한 줄이면 끝난다.
2. **케이스 ⑶ 의 기대 rc 가 코드와 반대였다.** 등재문은 「비 git → rc≠0」이라 적었지만
   `assert-main-checkout.sh:32-37` 이 **판정 불가를 의도적으로 통과**시킨다 — 그 주석이 이유까지
   적어 두었다(차단으로 바꾸면 CI·컨테이너에서 정상 타깃이 전부 죽는다). **코드가 맞다.**
   그대로 썼으면 하네스가 프로덕션 동작을 「고장」으로 고정하고, 다음 사람이 가드를 고쳤을 것이다.

**이행:** 케이스 4종(⑴ 메인 rc=0 · ⑵ `git worktree add` rc≠0 · ⑶ 비 git rc=0 · ⑷ 거부문에 메인
경로 포함) + 변이 M1(`:39` 판정 `=`→`!=`) 에서 **⑴⑵ 둘 다 red**. 임시 git 레포 fixture 위에서
**진짜 스크립트**를 돌리고 실제 레포는 안 건드린다(`git worktree list` 실행 전후 동일).

**★부수로 잡은 것 — `final-gates-test.sh` ⑥ 이 환경 의존이라 이 브랜치에서 상시 red 였다.**
`mise run gate-harnesses` 를 처음 돌렸더니 새 하네스가 아니라 **어제 심은 [BL-721] 의 케이스 ⑥**이
빨강이었다. main 에서도 같았다 — 「`BE ruff`·`FE build` 가 `--pre-pr` 에서 `plan` 이어야 한다」는
단언인데 그 둘은 **영역 게이트**라 BE/FE diff 0 인 트리에서는 모드와 무관하게 `skip` 이다.
⇒ **docs·tools 만 고친 모든 브랜치에서 하네스 전체가 빨강**이었다. 재려던 것(모드가 유예하지
않는다)과 재고 있던 것(영역이 골랐다)이 뭉쳐 있었다. ★**첫 수리판은 변이를 통과했다** —
`DEFERRABLE` 에 `BE ruff` 를 넣어도 마크가 안 갈린다(영역 판정이 `run_gate` **앞에서** 빠진다).
그래서 대표를 **항상 계획되는** `BL 감사`·`문서 감사` 로 바꾼 뒤에야 변이 M2 가 red 를 냈다.

**★함께 확정한 것 (사각이 아닌 것들):** 같은 스윕에서 `soak-gate` 를 사각으로 등재할 뻔했는데
**틀렸다** — 판정 로직이 `apps/api/scripts/soak_gate_predicate.py` 에 살고 **pytest 61건**이 덮는다.
셸은 I/O 껍데기다. `context-budget` 는 계측기(보고)라 판정기가 아니다. ⇒ **「`*-test.sh` 가 없다」를
「안 덮였다」로 읽지 마라** — 그 오독 자체가 §8.7 에 박혔다.

### BL-723

**Title:** 영역 판정이 **싼 게이트에만** 붙어 있다 — 가장 비싼 셋이 무조건 돈다
**Category:** Ops / 게이트 비용
**Priority:** P2
**Trigger:** 도래 — 실측이 있고 처방이 우리 손 안에 있다
**Est:** XS
**상태:** ✅ **Resolved** (2026-08-14 gate-pointer-axis) — 사용자 지적으로 등재·즉시 종결.
**트리거 판정:** 도래 — 조건절이 없다. 같은 회차의 `--deferred-only` 실행이 근거를 냈다 (2026-08-14 gate-pointer-axis)
**출처:** 2026-08-14 gate-pointer-axis (사용자 지적 — 「변경 부분이 있을 때 그 영향권을 돌리는 게 맞지 다 돌리는 건 좋지 않다」)

**원인 / 영향 (실측):** 이 회차는 `apps/web`·`apps/api` diff 가 **0줄**인데 `--deferred-only` 가
**11분 10초**를 태웠다:

| 게이트                           |      소요 | 영역 판정   |
| -------------------------------- | --------: | ----------- |
| BE pytest                        | **357초** | ❌ 없음     |
| e2e authed                       | **268초** | ❌ 없음     |
| e2e design-canon                 |  **42초** | ❌ 없음     |
| BE ruff · mypy                   |         — | ✅ `has_be` |
| FE vitest · build · e2e chromium |         — | ✅ `has_fe` |

같은 회차에 **CI 는 `backend`·`frontend`·`e2e` 잡을 전부 `skipping`** 했다(`changes` 잡이 판정).
⇒ **로컬이 CI 보다 더 돌면서 잴 것은 없었다.** 싼 형제는 이미 걸려 있으므로 비대칭 자체가 결함이다.

★종전 코드는 이것을 **의도**라고 적어 뒀다 — 「`design-canon`·`authed` 는 종전대로 무조건 돈다 —
`authed` 는 backend 변경도 문다」. **사유는 옳고 처방이 과했다.** `has_fe` 하나로 못 재는 것이지
「무조건」이 답이 아니다. 답은 `has_fe ∥ has_be` 다.

**처방 (이행 완료):**

1. `BE pytest` → `has_be || [ -z "$BASE" ]` (다른 BE 게이트와 같은 fail-safe 관용구)
2. `e2e design-canon` → `has_fe` — hermetic `file://` 대비 측정([BL-708])이라 서버 무결합
3. `e2e authed` → `has_fe ∥ has_be` — 로그인 후 **데이터 화면**까지 간다. BE 가 죽으면 화면이
   빈다([BL-707] 이 정확히 이 축에서 잡혔다 · 콘솔 `ERR_CONNECTION_REFUSED` 109건)
4. 영역 판정을 **모드 판정보다 앞**에 둔다 — 잴 것이 없는 레인은 유예 원장에도 안 올라간다
   (그래야 `--pre-pr` 유예 수 == `--deferred-only` 실행 수 상보성이 유지된다 · 하네스 ③④)
5. 세 레인 전부 영역이 비면 **정체성 프로브(curl)도 안 돈다** — 종전에는 docs 만 고친 회차에서
   서버가 없으면 e2e 가 **FAIL** 로 적혔다. 잴 것이 없는데 서버를 요구하는 것은 결함이다

**★동반 수리 — 하네스 케이스 3개가 같은 병이었다 (8→9 케이스):**

- **⑤** 「`BE pytest`·`e2e authed` 는 `--pre-pr` 에서 DEFER」 → 그 둘이 영역 게이트가 되는 순간
  거짓이 된다. 대표를 **영역 밖 유예 대상**(`CI fresh DB alembic`·`/codex 적대 리뷰`)으로 옮기고,
  영역 게이트는 **조건부**(full=plan 일 때만 DEFER)로 잰다. 변이 앵커 M3 도 함께 이동.
- **⑥** 이미 같은 병으로 **`main` 에서도 red** 였다(본 회차가 먼저 수리).
- **①** `full_plan >= 20` 하한이 영역이 넓어질수록 줄어드는 양이라 환경 의존 — **plan+skip 행 수**로
  교체했다. 실측으로 정확히 20 이 나와 **한 칸 남아 있었다**.
- **⑨ 신설** — 「비싼 게이트가 싼 형제와 **같은 마크**를 받는다」. ★단언을 **환경 독립**으로 짰다:
  「skip 이어야 한다」로 쓰면 diff 가 있는 브랜치에서 상시 red 라 같은 병을 옮겨 심는 것이다.
  변이 M4(영역 래퍼 제거)에서 red 확인.

**★교훈 — 이 레포는 「환경 의존 단언」을 한 회차에 4번 밟았다.** ⑤⑥①이 전부 「지금 이 트리에서만
참인 것」을 계약으로 굳혀 뒀고, 셋 다 **영역 판정을 넓히는 순간** 드러났다. 게이트 하네스의 단언은
**어느 트리에서 돌려도 참**이어야 한다 — 아니면 그 하네스는 브랜치 종류에 따라 켜졌다 꺼진다.

---

### BL-724

**Title:** ★소크 전략의 경제성 판정 — 수수료가 gross 를 15배로 먹고, 그 전략은 백테스트에서도 진다
**Category:** Backend / trading (money path) · 전략 경제성
**Priority:** P1
**Trigger:** 즉시 — [BL-003] 실자금 cutover 판단 **전**에 답이 나와 있어야 한다
**Est:** M (2-3h — 판정이지 수리가 아니다)
**출처:** 2026-08-14 money-path-attribution ([BL-438](#bl-438) 분석 중 부수 발견)

**원인 / 영향:** 서버 DB 고유 청산 **592건**을 수수료 축으로 갈랐더니 전략은 **흑자**였고 수수료가
그걸 16배로 덮고 있었다.

```
수수료 전 gross   +74.18 USDT
수수료           −1,200.00 USDT
순손익          −1,125.82 USDT   ← 초판 표기 −1,125.81 은 반올림 오차 (codex F7)
```

★**2026-08-14 money-path-close 판정 — 위 「전략은 흑자였다」는 라이브 원장 한 축에서만 참이다.**
아래 「판정」 절이 정본이다.

Bybit `closedPnl` 은 **수수료 차감 순액**이다(검산: gross −1.0788 − 수수료 2.0203 = closedPnl
−3.0991, 실측 일치). 요율은 단면 **0.055%** taker 이고 `openFee/cumEntryValue` =
`closeFee/cumExitValue` 로 확인했다 — 반전 주문의 수수료가 앞 행 `closeFee` 와 뒷 행 `openFee`
로 갈릴 뿐 **이중계상이 아니다**.

★**소크 게이트가 PASS 해도 이 사실은 안 바뀐다.** [BL-003] 은 「며칠 안 죽었는가」를 재고 이
항목은 「돈을 버는가」를 잰다. 게이트를 통과하고 동시에 틀린 결정일 수 있다.

**권장 접근:** 백테스트·스트레스 테스트의 **Cost-Assumption 축이 실측 0.055%×2 를 쓰는지** 대조한다.
어긋나면 백테스트가 낙관적이었다는 뜻이고, 그건 전략 채택 기준 자체를 다시 봐야 한다는 뜻이다.
수리 항목이 아니라 **판정 항목**이다 — 산출물은 「실자금으로 가도 되는가」에 대한 숫자다.

**Risk:** 🔴 (실자금 전환 판단이 잘못된 전제 위에 설 수 있다)

---

### ★판정 (2026-08-14 money-path-close) — 정본

**답: 이 전략으로는 실자금에 가지 않는다. 데모는 계속 돈다.**

**⑴ 라이브 원장 분해** (서버 DB · `DISTINCT ON (row_hash)` 고유 청산 **596건** · `raw` jsonb 의
`openFee`/`closeFee`/`cumEntryValue`/`cumExitValue`):

```
gross PnL   +82.64        회전량 2,189,464 USDT
수수료    −1,204.21        실효율 0.05500% ← 단면 taker 공시치와 소수점까지 일치, maker 체결 0건
net PnL   −1,121.57
            gross PF 1.1486  →  net PF 0.2232      승 223/596(gross) → 99/596(net)
            건당 gross +0.139 USDT  vs  수수료 −2.02 USDT
```

**손익분기 요율 = 단면 0.00377%** (= 82.64 / 2,189,464). 현재 0.055% 의 **1/14.6** 이다.
어느 VIP tier 도 그 근처에 없고, 전량 maker(0.02%)로 가도 여전히 음수다. **비용 축의 개선으로
구제되지 않는다.**

★**그래서 레버는 요율이 아니라 빈도다.** 수수료 = 요율 × 회전량인데 요율은 공시치에 고정이므로
남는 변수는 회전량뿐이다 — **회전 2,189,464 USDT 는 계좌(약 189,427)의 11.6배**다. 이 전략은
「비용 가정이 틀린 전략」이 아니라 **「엣지 대비 너무 자주 도는 전략」**이고, 그래서 이 항목의
처방은 Cost-Assumption 축이 아니라 **전략 설계(진입 빈도)** 쪽에 있다.

**⑵ 권장 접근이 지시한 백테스트 대조 — 코드 SSOT 는 이미 맞다.**
`backtest/engine/types.py:43-44` = `fees 0.00055` / `slippage 0.00014`([BL-603], 2026-08-07).
어긋난 것은 코드가 아니라 **그 전략을 채택할 때 쓴 백테스트 4벌**이다.

```
전략 귀속 — 596건 중 551건(−1,089.10)이 `PbR Pivot Reversal`, 소크가 지금 돌리는 그 전략
그 전략의 백테스트 4벌 profit factor = 0.5663 / 0.6069 / 0.6069 / 0.8555   ← 전부 1 미만
4벌 모두 config fees=0.001 · slippage=0.0005 (2026-07-26 생성 = BL-603 이전 낡은 값)
```

**⑶ 가장 큰 반증 — 「전략은 흑자인데 수수료가 먹었다」는 절반만 참이다.**
두 축을 **「수수료 전」** 으로 맞추면(라이브는 슬리피지가 체결가에 녹아 있고, 백테스트는
엔진이 슬리피지를 **별도 비용으로 차감**한다 — `v2_adapter.py:313,364`. 그래서 백테스트 쪽은
정확히 **「슬리피지 차감 후 · 수수료 전」** 이다. codex F6):

|                            | gross(슬리피지 후) | 수수료   | net       |
| -------------------------- | ------------------ | -------- | --------- |
| 백테스트 `a22faccb` n=1028 | **−34,582**        | 183,978  | −218,560  |
| 라이브 원장 n=596          | **+82.64**         | 1,204.21 | −1,121.57 |

백테스트 쪽 gross 는 **음수**다. 낡은 요율을 실측치로 되돌린 해석적 재계산 `[가정]`
net ≈ **−69,538**(자본 10,000)로 **부호가 안 바뀐다**. 즉 이 항목은 「수수료가 흑자 전략을
먹었다」가 아니라 **「백테스트에서도 지는 전략을 소크에 태웠고 수수료는 그 위에 얹혔다」**이다.

★**소크 게이트는 이 사실을 영원히 못 잡는다** — C1/C2 는 「며칠 안 죽었는가」를 재고 이것은
「돈을 버는가」를 잰다. 게이트 PASS 와 이 판정은 **서로 독립**이다.

**따라오는 조치**: 데모 소크는 [BL-003] C1/C2(안정성) 데이터 수집용으로 **계속 돈다** —
데모라 금전 손실이 0이고, [BL-438] 백필 수리의 실증 표면이기도 하다. 실자금 cutover 는
**「전략 경제성 미충족」으로 차단 유지**한다(사용자 결정 2026-08-14: 「실매매는 진짜 최종에
최종만이다. 데모 기준으로 돌려라」). 분리 등재 = [BL-729](#bl-729)(낡은 비용 가정으로 돌린
백테스트) · [BL-730](#bl-730)(FE 비용 기본값 drift 2곳).

**상태:** ✅ **Resolved — 판정 완료 (2026-08-14 money-path-close).** 답 = **실자금 불가 · 데모 유지**.
손익분기 요율 단면 **0.00377%**(현재의 1/14.6)라 비용 축으로 구제되지 않고, 같은 전략의 백테스트
4벌이 **전부 PF < 1** 이다. 원 표제의 「전략은 흑자였다」는 라이브 한 축에서만 참이었다 — 같은
정의로 맞춘 백테스트 gross 는 **−34,582** 로 음수다. 수리 항목이 아니므로 코드 변경 0.
**트리거 판정:** 도래 — Trigger 줄 자신이 「즉시」다. 조건절이 없다 (2026-08-14 money-path-attribution)

---

### BL-726

**Title:** `rejected` + reduce-only 주문 46건에 `realized_pnl` 이 채워져 있는데 evaluator 가 못 본다
**Category:** Backend / trading (risk gate)
**Priority:** P2
**Trigger:** [BL-438](#bl-438) 백필 수리와 **동승** — 같은 SUM 을 건드린다
**Est:** S (1h)
**출처:** 2026-08-14 money-path-attribution

**원인 / 영향:** 서버 DB 실측 —

```
rejected | reduce_only=t | realized_pnl 채움 | 46건 | +55.32 USDT
```

`CumulativeLossEvaluator`(`kill_switch.py:97-102`)와 `DailyLossEvaluator`(`:150-157`)는 둘 다
`Order.state == OrderState.filled` 로 거르므로 이 46건은 SUM 에 안 들어간다. **어느 쪽이 옳은지
판정된 적이 없다** — 값이 채워졌다는 것은 백필이 그 주문을 청산으로 봤다는 뜻이고, `rejected`
라는 것은 발주가 실패했다는 뜻이라 **두 사실이 모순**이다.

★부호가 **+**라 지금은 게이트를 느슨하게 만드는 쪽이다. 넣으면 손실이 줄어 보인다.

**권장 접근:** 먼저 그 46건이 **왜** `rejected` 인지 판정해라(발주 실패인가, 상태 전이 결함인가).
그 답에 따라 ⑴ `realized_pnl` 을 null-out 하거나 ⑵ evaluator 의 state 필터를
`realized_pnl_synced_at IS NOT NULL` 로 넓힌다. [BL-439](#bl-439) 가 같은 필터를 다른 각도에서
건드리므로 함께 본다.

**Risk:** 🟡 (게이트가 손실을 과소평가하는 방향)

**상태:** ✅ **Resolved — 기각 판정 (2026-08-14 `dde53e68` / #631 + money-path-close 코드 대조).**
**모순이 아니었다.** `Order.realized_pnl` 은 **생성 시점**에 실린다(`order_service.py:393,427`
`realized_pnl=req.realized_pnl`). 생산자는 둘이고 **둘 다 체결 전 추정치**다 —
라이브 축 `live_signal.py:4406`(MP-1, `LiveSignalEvent.realized_pnl` = pine_v2 시뮬) ·
웹훅 축 `router.py:161`(TV alert 필드). ★**어느 쪽이든 결론이 같다.**
★`idempotency_key` 의 `live:` 접두는 **생산자 증명이 못 된다**(codex F1) — 웹훅도 호출자가 준
`Idempotency-Key` 를 그대로 저장한다(`router.py:100-175`). 정본 판별 = `LiveSignalEvent.order_id`
조인(`models.py:674`). 거래소 확정치를 쓰는 경로는 `backfill_exchange_realized_pnl` **과**
`resync_exchange_realized_pnl`(`order_repository.py:828`) **둘**이고(codex F3) **둘 다**
`state==filled` 를 요구하므로 `rejected` 행에 들어갈 수 없다.
증거 — `exchange_order_id` 가 **46건 전부 NULL**(주문 ID 미발급 · 미체결)이고
`error_message` 는 `110017 "current position is zero"` 30건 · `110017 "reduce-only order has same
side"` 15건 · `10005` 1건이다.
★**「거래소에 도달조차 못 했다」로 읽지 마라**(codex F2) — `110017`·`10005` 는 **거래소가 반환한
retCode** 라 요청은 거래소까지 갔고 거절당했다. 정확히는 **「주문 ID 가 발급되지 않았고 체결되지
않았다」**이다. ⇒ **evaluator 의 `state==filled` 필터가 옳다. 동작 변경 0.**
★**원장의 처방 ⑵(「필터를 `realized_pnl_synced_at IS NOT NULL` 로 넓힌다」)는 이 46건에 no-op**
이다(그 컬럼이 46건 전부 NULL). 게다가 채택하면 **아직 백필 안 된 `filled` 주문의 추정 손익까지**
SUM 에서 빠져 게이트가 일시적으로 느슨해진다 — 지금 필터가 더 안전한 쪽이다. 판정 근거는
`kill_switch.py:97-118` 주석에 영속했고 회귀 테스트가 동결한다.
**트리거 판정:** 도래 — [BL-438](#bl-438) 백필 수리 회차에 동승했다 (2026-08-14 money-path-close)

---

### BL-727

**Title:** `soak-gate.sh` 가 맨 `python3` 를 불러 맥에서 판정을 못 낸다
**Category:** Tooling / 게이트
**Priority:** P2
**Trigger:** ★**이미 발화했다** — 2026-08-14 에 맥 판독이 죽었다
**Est:** XS (10분)
**출처:** 2026-08-14 money-path-attribution

**원인 / 영향:** `tools/scripts/soak-gate.sh:706` 이 판정 본체를 맨 `python3` 로 부른다.
맥의 `/usr/bin/python3` 는 **3.9.6** 이라 `soak_gate_predicate.py:329` 의 `itertools.pairwise`
(3.10+)에서 `AttributeError` 로 죽고, 스크립트는 계속 진행해 **`판정: ` 빈 줄**을 인쇄한다.
후속 `json.load` 들도 연쇄로 죽는다. **fail-open 형태다** — 죽었는데 종료 코드로만 티가 난다.

★**같은 함정을 같은 파일이 이미 고쳐 뒀다** — `:449` 가 `uv run python` 을 쓰며 주석에
「시스템 python3 로 돌리면 조용히 실패해 **verdicts 가 늘 0** 이 된다(실측 2026-08-04)」라고
적고 있다. 그 교훈이 **판정 본체에는 적용되지 않았다.**

우회는 `PATH=/opt/homebrew/bin:$PATH`(3.14.6)이고 그것으로 이 회차가 판독했다.

**권장 접근:** `python3` 호출을 `uv run python` 으로 바꾼다. 호출 자리가 여럿이다
(`220·391·471·546·567·572·706·714·715·716·745`) — **판정을 내는 자리를 우선**하고 나머지는
판단해서 처리하되 무엇을 왜 남겼는지 적는다. 서버(Linux)에서는 증상이 안 나므로 **맥에서
음성 대조**를 붙여야 판별력이 증명된다.

**Risk:** 🟡 (게이트가 조용히 판정 불가가 된다 — 소크 판독은 [BL-003] P0 의 입력이다)

**상태:** ✅ **Resolved (2026-08-14 `dde53e68` / #631).** 판정 본체(`soak-gate.sh:706`·`714`~`716`)를
`uv run python` 으로 바꾸고 **빈 출력을 fail-closed** 로 만들었다 — 종전에는 죽고도 진행해 빈
`판정:` 줄을 찍었다. 맥 음성 대조 3단계로 판별력 증명.
**트리거 판정:** 도래 — Trigger 줄 자신이 「이미 발화했다」이고 실측이 있다 (2026-08-14 money-path-attribution)

---

### BL-728

**Title:** `classify_exit` 이 Bybit 강제청산(`CreateByLiq`)을 못 잡는다
**Category:** Backend / trading (분류)
**Priority:** P3
**Trigger:** ★관측 0건 — 강제청산이 실제로 발생하거나 [BL-438](#bl-438) 분류 축을 건드릴 때 **동승**
**Est:** XS (10분)
**출처:** 2026-08-14 money-path-attribution

**원인 / 영향:** `apps/api/src/trading/exit_attribution.py:64` 가
`if "liquidation" in create_type or "adl" in create_type` 로 판정하는데, **Bybit 공식 enum 값은
`CreateByLiq`** 다(문서 확인). casefold 해도 `createbyliq` 라 `"liquidation"` 부분문자열이
**걸리지 않는다**. ADL 쪽(`CreateByAdl_PassThrough`)은 `"adl"` 로 걸린다.

⇒ 강제청산 행이 `ExitClassification.liquidation` 이 아니라 `unknown` 으로 떨어진다.
운영자 알림 본문에서 「강제청산이 있었다」가 사라진다.

★**지금 관측 0건이라 잠복이다.** 데모 계정에 강제청산 이력이 없다 — 실자금 전환 후에는
잠복이 아니게 된다. 인접 미분류 후보로 `CreateByMmRateClose`(마진율 강제감축)도 같은 성질이다.

**권장 접근:** `create_type` 판정을 부분문자열이 아니라 **enum 값 집합**으로 바꾼다 —
이미 `_TAKE_PROFIT_CREATE_TYPES` 등 3개가 그 방식이다(`:14-16`). 같은 자리에
`_LIQUIDATION_CREATE_TYPES = frozenset({"createbyliq", "createbymmrateclose"})` 를 두고
`"adl"` 부분문자열 축은 `_PassThrough` 접미사 때문에 유지한다.

**Risk:** 🟢 (라벨 결함 — 손익 계상에는 영향 없다. 알림 본문만 부정확)

**상태:** ✅ **Resolved (2026-08-14 `dde53e68` / #631).** `create_type` 판정을 부분문자열이 아니라
`_LIQUIDATION_CREATE_TYPES` frozenset 으로 바꿨다(같은 파일 `:14-16` 의 기존 3종과 통일).
`"adl"` 부분문자열 축은 `_PassThrough` 접미사 때문에 유지. 관측은 여전히 0건이다 — 잠복 해소.
**트리거 판정:** 도래 — [BL-438](#bl-438) 회차에 동승했다 (2026-08-14 money-path-close)

---

### BL-729

**Title:** 전략 채택 근거가 된 백테스트 4벌이 낡은 비용 가정(0.001/0.0005)으로 돌았다
**Category:** Backend / backtest (비용 모델) · 전략 채택 기준
**Priority:** P2
**Trigger:** 즉시 — 소크에 태울 전략을 **다시 고를 때** 그 판단의 입력이다
**Est:** S (1h — Cost-Assumption 스트레스 테스트 1회 + 판독)
**출처:** 2026-08-14 money-path-close ([BL-724](#bl-724) 판정 중 부수 발견)

**원인 / 영향:** 소크가 돌리는 `PbR Pivot Reversal` 의 백테스트 4벌이 **전부**
`config fees=0.001 · slippage=0.0005` 로 돌았다(2026-07-26 생성). 그 값은 [BL-603](#bl-603) 이
2026-08-07 에 라이브 원장 실측(`0.00055`/`0.00014`)으로 **교체한 낡은 추정치**다 —
왕복 **0.30%** vs 실측 **0.138%**, 약 **2.2배 비관**이다.

```
backtest id  n      PF       gross_profit  gross_loss   net       fees      slippage   cfg
8174aaaa     1028   0.6069   337,403       555,963      −218,560  183,978   91,989     0.001/0.0005
a22faccb     1028   0.6069   337,403       555,963      −218,560  183,978   91,989     0.001/0.0005
d07fe4af     1028   0.5663   285,627       504,412      −218,786  183,989   91,995     0.001/0.0005
4b18b64e       69   0.8555    26,882        31,424        −4,541    9,710     4,855    0.001/0.0005
```

★**코드 SSOT 는 이미 맞다** — `backtest/engine/types.py:43-44` · `backtest/schemas.py:51,60` 이
`0.00055`/`0.00014` 다. 문제는 **저장된 백테스트가 낡은 config 를 안고 있다**는 것이고,
`config_mapper.py:102-104` 가 그 저장값을 그대로 복원하므로 **재실행해도 스스로 안 고쳐진다.**

★**단 결론은 안 바뀐다** — 실측 요율로 되돌린 해석적 재계산 `[가정]` net ≈ **−69,538**(자본
10,000)로 부호가 유지된다. 이 항목은 [BL-724](#bl-724) 판정을 뒤집는 것이 아니라 **그 판정의
정밀도**를 올린다.

**권장 접근:** `stress_test` 의 **Cost-Assumption** 축이 정확히 이 일을 한다
(`engine/cost_assumption_sensitivity.py:48-56` 이 `dc_replace(base, fees=…, slippage=…)` 로
2D grid sweep). 실측점 `(0.00055, 0.00014)` 을 포함한 격자로 1회 돌려 PF 를 다시 읽어라.
★**FE 프리셋 격자는 못 쓴다** — `stress-test-panel.tsx:93-94` 의 9-cell 이
`fees [0.0005, 0.001, 0.002] × slippage [0.0001, 0.0005, 0.001]` 이라 **현재 기본값이 격자에 없다**.
API 로 격자를 직접 주거나 프리셋을 고쳐라(→ [BL-730](#bl-730) 과 같은 뿌리).
★소크 워커를 쓰므로 **소크가 멈춘 창에서** 돌려라.

**Risk:** 🟡 (전략 채택/기각 판단이 2.2배 비관인 비용 위에 서 있다 — 쓸 만한 전략을 부당 탈락시킬 수 있다)

**상태:** ✅ **Resolved (2026-08-15 soak-survival)** — Cost-Assumption 축을 **실측점 포함 격자**로 1회 돌려 판독했다. 판정 = **[BL-724] 유지**(비용 축으로 구제되지 않는다)
**트리거 판정:** 도래 — Trigger 줄에 조건절이 없다. 다만 착수는 소크 정지 창에 맞춘다 (2026-08-14 money-path-close)

---

## ★2026-08-15 실측 — 「해석적 재계산」을 측정으로 바꿨다

### BL-730

**Title:** FE 비용 기본값 drift 2곳 — 신규 사용자의 첫 백테스트가 왕복 0.30% 로 돈다
**Category:** Frontend / backtest (비용 모델 미러)
**Priority:** P2
**Trigger:** 즉시 — 이미 프로덕션에서 발화 중이다(온보딩 경로)
**Est:** XS (15분)
**출처:** 2026-08-14 money-path-close ([BL-724](#bl-724) 판정 중 부수 발견)

**원인 / 영향:** [BL-603](#bl-603) 이 「두 SSOT + **FE 미러 4곳**」을 고쳤다고 기록했는데
실제 미러는 **5곳**이었고 **2곳이 누락**됐다.

```
apps/web/src/features/backtest/schemas.ts:81,87        zod .default(0.001) / .default(0.0005)
  └ :57-59 주석도 "0.10% 수수료 / 0.05% 슬리피지" 로 낡음
apps/web/src/app/(dashboard)/onboarding/_components/step-3-backtest.tsx:77-78
  └ fees_pct: 0.001, slippage_pct: 0.0005 를 **하드코딩 submit**
```

★**⑵ 가 실제 사고다** — 온보딩은 폼을 안 거치고 곧장 submit 하므로 **신규 사용자의 첫 백테스트가
왕복 0.30%**(실측 대비 2.2배 비관)로 돈다. [BL-603] 이 고치려던 바로 그 증상이 온보딩 경로에
그대로 살아 있다. ⑴ 은 `useBacktestForm.ts:95-96` 이 항상 값을 채워 **가려져 있지만**, 폼을
안 거치는 호출자에게는 반증된 가정이 샌다.

★**인접 3번째** — `stress-test-panel.tsx:93-94` 의 9-cell 프리셋 격자에 현재 기본값
`(0.00055, 0.00014)` 이 **없다**(최저점이 0.0005/0.0001). heatmap 에 「지금 가정」 셀이 빠진다
→ [BL-729](#bl-729) 와 같은 뿌리.

**권장 접근:** 값을 3곳에 또 베끼지 마라 — 이 항목의 원인 자체가 **미러 5벌**이다.
FE 단일 상수(`assumptions-card.tsx:20-21` 의 `DEFAULT_FEES`/`DEFAULT_SLIPPAGE` 가 선례)를
정본으로 삼아 zod default · 온보딩 · 프리셋 격자가 그것을 참조하게 해라.
★**음성 대조** — 온보딩을 실제로 태워 제출 payload 의 `fees_pct` 가 `0.00055` 인지 봐라.
상수만 고치고 화면을 안 보면 [BL-698](#bl-698)(`step="0.0001"` 격자가 submit 을 212 커밋 동안
발화조차 못 시킨 건)을 반복한다.

**Risk:** 🟡 (신규 사용자가 보는 첫 숫자가 2.2배 비관 — 전략을 부당 탈락시킨다)

**상태:** ✅ **Resolved (2026-08-15 soak-survival)** — FE 리터럴 5벌을 `features/backtest/cost-defaults.ts` 단일 상수로 모았다(이미 맞던 3벌 포함 — 안 모으면 다음 조정 때 같은 3/5 문제가 난다). 온보딩 제출 payload 테스트 신설 + stress 프리셋 격자를 기본값 기준 1x/2x/4x 로 교체
**트리거 판정:** 도래 — 온보딩 경로가 이미 프로덕션에서 그 값을 보낸다 (2026-08-14 money-path-close)

---

### BL-731

**Title:** `list_synced_with_exchange_exit` 의 `LIMIT 500` — 재검증 모집단이 단조 증가해 가장 오래된 건이 영구 제외된다
**Category:** Backend / trading (money path)
**Priority:** P2
**Trigger:** ★**이미 발화 조건에 들어갔다** — [BL-438] 백필이 도는 순간 모집단이 73 → 563 이 된다
**Est:** S (1h)
**출처:** 2026-08-14 money-path-close (Lane B 실측 F4 → CONTROL 코드 대조 채택)

**원인 / 영향:** `order_repository.py` 의 `list_synced_with_exchange_exit` 이
`.order_by(Order.filled_at.desc()).limit(500)` 이다. [BL-438](#bl-438) 수리 전에는 이 술어의
모집단이 `reduce_only` 주문 **73건**뿐이라 상한이 닿지 않았다. 수리 후 모집단은
**「원장이 청산으로 증언하는 filled 주문 전량」** 이 되고 서버 실측으로 **563건**이다
⇒ 가장 오래된 **63건이 재검증(`resync_exchange_realized_pnl`)에서 영구 제외**된다.

★**미동기화 축과 성질이 다르다.** `list_unsynced_*` 는 백필이 성공하면 모집단에서 빠지므로
**배수(drain)** 된다 — 상한이 일시적 지연만 만든다. 반면 동기화 축은 **단조 증가**라 한 번
500 을 넘으면 그 초과분이 다시 줄지 않는다. 소크가 계속 도는 한 격차는 벌어지기만 한다.

★**지금 당장 손익이 틀어지지는 않는다** — 재검증은 「체결 직후 refresh 가 분할 행 부분합을
CAS 로 얼린 경우」를 되돌리는 안전망이고, 그 refresh 경로(`_enqueue_closed_pnl_refresh:1227` ·
`_refresh_closed_pnl_with_session:1493`)는 **여전히 `reduce_only` 게이트**라 반전 주문은 애초에
그 경로를 안 탄다. 즉 제외되는 63건은 「고칠 것이 없는」 쪽일 가능성이 높다. **그러나 그것은
지금 게이트가 남아 있기 때문**이고, 그 게이트를 여는 순간(→ [BL-733](#bl-733)) 전제가 깨진다.

**권장 접근:** ⑴ 상한을 키우는 것은 미봉이다(모집단이 계속 는다). ⑵ 커서/배치 순회로 바꾸거나
⑶ 재검증 대상을 **원장 합계와 저장값이 실제로 다른 행**으로 좁혀라(`resync_exchange_realized_pnl`
이 이미 `IS DISTINCT FROM` 가드를 갖고 있으니, 그 판정을 SQL 로 끌어올리면 모집단이 자연히 0 에
수렴한다). ⑶ 이 상한 자체를 무의미하게 만드므로 가장 싸다.
★**음성 대조** — 501건 이상을 만든 픽스처에서 **가장 오래된 행이 결과에 없음**을 먼저 단언해라.
지금 술어로 그 단언이 red 가 나야 이 항목이 실재한다는 증거다.

**Risk:** 🟡 (안전망이 조용히 일부 모집단을 안 본다 — 지금은 무해하나 게이트를 여는 순간 실피해)

**상태:** ✅ **Resolved (2026-08-15 soak-survival)** — `IS DISTINCT FROM` 가드를 SQL 술어로 끌어올려 모집단이 0 으로 수렴한다. 상한도 정렬도 안 바꿨다. 수리 전 red 를 먼저 확인
**트리거 판정:** 도래 — [BL-438](#bl-438) 수리가 머지돼 모집단 증가 조건이 이미 성립했다 (2026-08-14 money-path-close)

---

### BL-733

**Title:** 체결 직후 `closed_pnl` refresh 2곳이 아직 `reduce_only` 게이트다 — 반전 주문 백필이 최대 5분 늦는다
**Category:** Backend / trading (money path)
**Priority:** P2
**Trigger:** ★**순진하게 열면 안 된다** — 아래 「권장 접근」의 술어 설계가 선행이다
**Est:** M (2-3h — 게이트 술어 설계가 핵심)
**출처:** 2026-08-14 money-path-close ([BL-438](#bl-438) 검증 중 발견 — 게이트는 1곳이 아니라 3곳이었다)

**원인 / 영향:** [BL-438](#bl-438) 은 **리포지토리 축(5분 beat 스윕)만** 고쳤다. 체결 직후 경로
2곳은 여전히 `reduce_only` 로 거른다:

```
tasks/trading.py:1227  _enqueue_closed_pnl_refresh        if not order.reduce_only: return    ← 예약조차 안 됨
tasks/trading.py:1493  _refresh_closed_pnl_with_session   if not order.reduce_only: skipped   ← 예약돼도 skip
```

⇒ 반전 주문의 확정 손익은 **최대 5분**(beat 주기) 늦게 들어온다. `reduce_only` 청산은 초 단위다.
kill-switch 는 그 창 동안 손실을 과소평가한다.

★**필터만 지우면 안 된다 — 그러면 더 나빠진다.** **정상 Bybit 선물 entry** 주문은
`closed-pnl` 원장에 대응 행이 없으므로 `fetch_closed_pnl` 이 `None` → `transient` →
**4회 재시도** → `_alert_closed_pnl_unbackfilled` **운영자 알림**을 낸다
(`tasks/trading.py:1783-1791` 실측). 거짓 알림이 쌓이면 알림 자체가 무의미해진다.
★**「entry 마다」는 과장이다**(codex F8) — `_refresh_closed_pnl_with_session` 의 조기 종료는
`order_missing` · `not_filled` · `not_reduce_only` · `no_exchange_order_id` · `account_missing` ·
`unsupported_exchange` · `decrypt_failed` · `no_filled_at` · `already_synced` 로 **9종**이다
(`trading.py:1489-1560`). `transient` → 재시도 → 알림 경로로 가는 것은 **정상 Bybit 선물 ·
`filled` · 필수 데이터 보유** 주문뿐이다.

**권장 접근:** 체결 시점에는 원장 행이 아직 없으므로 [BL-438] 의 EXISTS 축을 그대로 쓸 수 없다.
쓸 수 있는 것은 **체결 후 포지션 관측**이고, 그 판정기가 이미 있다 —
`_reversal_bucket_at_fill`(`tasks/trading.py:1573~`)이 `(position, entry_side, filled_quantity,
submitted_at)` 으로 반전 여부를 판정하고 **증명 못 하면 `unmeasured_*` 로 갈라 두는** 규약까지
갖고 있다. 그 판정을 게이트로 재사용하고 `unmeasured_*` 는 **스윕에 맡겨라**(fail-safe: 늦을 뿐
안 틀린다). 새 판정기를 만들지 마라.

**Risk:** 🟡 (지연 5분 — 손익 자체는 스윕이 결국 맞춘다. 다만 그 5분이 kill-switch 창이다)

**상태:** ✅ **Resolved (2026-08-15 soak-survival)** — `_reversal_bucket_at_fill` 판정을 재사용해 **반전이 증명된 leg 만** refresh 를 예약한다(`unmeasured_*` 는 스윕에 맡긴다). 실행측 게이트에 회귀 테스트 신설 — 종전엔 그 게이트를 지우면 31 passed 였다
**트리거 판정:** 도래 — [BL-438](#bl-438) 이 머지돼 나머지 2곳이 유일한 잔여가 됐다 (2026-08-14 money-path-close)

---

### BL-734

**Title:** ✅ real_broker 하네스의 청산이 **남의 포지션**을 닫아 서버 소크를 죽였다 — [BL-633] 재발
**Category:** Backend / trading (테스트 인프라 · 계정 배타성)
**Priority:** P1
**Trigger:** — (부검 완료 · 이번 회차에서 수리)
**Est:** M
**출처:** 2026-08-15 soak-survival ([BL-732] 부검 중 발견 — 표적이 통째로 바뀌었다)

**원인 / 영향:** 서버 소크 세션 `de3db35a` 가 2026-08-14T04:51:27Z 에 `position_divergence`
(`category=direction`)로 죽었다. **코드 결함이 아니라 같은 Bybit demo 계정에 붙은 외부 주문이
근인이다.** 거래소 closed-pnl 원장 실측:

```
04:44:07  소크 sell 0.058                                    → 서버 숏 −0.029
04:49:56  Buy 0.029  CreateByUser · link=(empty) · conf=inferred   ← 외부
04:50:27  exchange_position=+0.001   (엔진 −0.029982)        ← 남은 잔량과 정확히 일치
04:51:27  같은 값 2연속 → _judge_direction_strike kill → 사망
```

★**소유권 판별이 결정적이었다.** 소크 주문은 예외 없이 `create_type=CreateByStopOrder` +
`order_link_id=<우리 order.id>` + `attribution_confidence=exact` 인데, 문제의 5건(04:49~05:17,
나머지는 `0.001` 크기)은 `CreateByUser` + link 없음/미조인이다. 그 5건은 **개발 DB 에도 테스트
DB 에도 없다** — pytest 세션 픽스처의 `drop_all` 이 자기 기록을 지웠기 때문이다. 시스템은 이미
신고했었다: `04:53:32 exchange_exit_link_id_unverified … classification=unknown`.

★**범인은 `tests/real_broker/_harness.py:flatten_one` 의 3단계**다. `close_position` 은 계정
포지션을 **소유권을 보지 않고** 닫는다. 그리고 4단계 verify-flat 은 `positions` 가 비었으므로
**성공으로 보고**했다 — 남의 포지션을 닫았다는 것을 구조적으로 알 수 없었다. [BL-633](#bl-633)
(맥 로컬 **소크 세션**이 서버 세션을 죽였다)과 **같은 병이고 경로만 다르다** — 이번엔 로컬
**테스트 하네스**다.

**수리(이 회차):** `find_foreign_resting` 을 `scripts/live_session_admin.py:_cmd_status` 의
**인라인에서 함수로 추출**하고(새 판정기를 만들지 않았다) `flatten_one` 이 청산 **전에** 호출한다.
남의 resting 조건부 주문이 하나라도 보이면 청산 경로에 **진입조차 하지 않고** `undecidable` 로
보고한다. 조회 실패도 같다(**fail-closed** — 「남이 있는지 모른다」에서 닫는 것이 이 사고의 형태다).

★판별자는 반드시 `order_link_id` **소유권**이다. 「resting 이 있다」만으로 막으면 우리 자신의
주문에도 걸려 정상 재기동이 영원히 거부된다. ★`reduce_only=None` 이어야 한다 — 기본값 `True` 는
TP/SL 만 주고, 오염을 만드는 것은 **조건부 진입**이다.

★**하네스가 테스트 DB 를 연다는 사실이 판정을 공짜로 만든다** — 그 원장에는 테스트 주문만 있으므로
소크의 조건부 진입은 자동으로 FOREIGN 이 된다.

**검증:** `tests/scripts/test_harness_exclusivity_guard.py` 3건 green. **변이 2건이 서로 다른
테스트를** 정확히 red 로 만들었고 도달도 확인했다 — ⑴ `if foreign:` → `if False:` 는
`test_foreign_resting_blocks_close` 만, ⑵ `except` fail-open 은 `test_probe_failure_blocks_close`
만 죽였다. 양성 대조 = 로컬에서 `live_session_admin.py status` 를 돌리면 서버 소크의 조건부 주문을
`FOREIGN_RESTING=1 · EXCLUSIVE=NO` 로 잡는다.

★**그 테스트를 `tests/real_broker/` 에 두면 안 된다**(실측). `pytest_collection_modifyitems` 가
`"real_broker" in item.keywords` 로 skip 을 주입하는데 `item.keywords` 는 **디렉터리 이름도**
포함한다 — 마커를 안 달아도 `3 skipped` 였다. **가드를 지키는 테스트가 가드와 함께 꺼진다.**

**Risk:** 🔴 → ✅ (소크 생존이 [BL-003] C1/C2 의 유일한 입력이었다)

**상태:** ✅ **Resolved (2026-08-15 soak-survival)** — 가드 + 회귀 3건 + 변이 2건 + 양성 대조
**트리거 판정:** — (부검 완료)

---

### BL-735

**Title:** 소크를 **로컬 맥에서 돌리지 않는다** — 맥이 자면 beat 가 tick 을 잃는다 (운영 규칙)
**Category:** 운영 / BL-003 소크
**Priority:** P1
**Trigger:** ★**이미 발화했다** — 2026-08-14 로컬 소크가 6h33m 만에 죽었다
**Est:** S (규칙 + 문서. 기계 강제는 별건)
**출처:** 2026-08-15 soak-survival

**원인 / 영향:** 로컬 맥 소크 `e9c504f1` 이 6h33m 만에 죽은 것은 **맥이 잠들었기 때문**이다.
`pmset -g log` 대조 — 09:11:59 Clamshell Sleep ↔ `last_evaluated_bar_time=09:11:00` · 09:28:18
Wake ↔ 09:28:46 `gap_resync_deferred`. **beat 가 09:38~12:26 에 168회 중 15회만 tick 을 보냈고,
그 15회가 DarkWake 횟수다.** 깨어난 직후엔 네트워크가 아직 안 붙어 `socket.gaierror` 가 난다.

★`pmset -g custom` 실측 — **AC 전원에서도 `sleep 1`**(1분)이고 `displaysleep 10` 이다. 뚜껑을
닫으면 Clamshell Sleep 은 어떤 설정으로도 안 막힌다. ⇒ **로컬에서 24h 연속 창은 구조적으로 불가능.**

★`docs/status.md` 는 이미 「게이트를 로컬에서 돌리지 마라」를 적고 있었는데 **소크 자체를 로컬에
띄우는 것**은 막지 않았다. 규칙의 사각이었다.

★부수 위험 — 로컬과 서버가 **같은 Bybit demo 계정**(`19a8166a` / uid `558689281`)을 쓴다.
두 곳에서 동시에 돌면 [BL-633]·[BL-734] 가 재발한다.

**권장 접근:** 규칙은 `docs/status.md` 「환경 상태」에 박았다. 기계 강제를 원하면
`soak-stack.sh up` 이 `uname -s == Darwin` 이면 거부하게 하는 것이 최소안이다 — 다만 **개발용
격리 스택까지 막으면 안 되므로** 소크 compose 갈래에서만 판정해야 한다.

**Risk:** 🔴 (이 규칙이 없으면 C1 시계가 계속 6시간대에서 끊긴다)

**상태:** ✅ **Resolved (2026-08-15 clock-fill-sweep)** — 기계 강제가 들어갔다. `soak-stack.sh:_up()` **첫 줄**(= `assert-main-checkout` **앞**)에서 `uname` 이 `Darwin` 이면 rc=2 로 거부하고, `QB_SOAK_ALLOW_DARWIN=1` 이 명시적 탈출구다. ★**위치가 이 작업의 전부다** — 소크 갈래(`soak-stack.sh:38 COMPOSE` + `docker-compose.soak.yml`)와 개발 격리 갈래(`Makefile:26 ISOLATED_COMPOSE`, soak.yml 미포함)는 **파일 자체로 갈리므로** `_up()` 안에 두면 그것만으로 소크에만 걸린다. 반대로 dispatch 밖(스크립트 상단)에 두면 `assert-not-pinned` 경로까지 죽어 `mise run up-isolated` 가 맥에서 통째로 막힌다. 신규 하네스 `tools/scripts/soak-stack-test.sh`(9케이스, PATH 앞단 가짜 `uname` — docker 의존 0)를 만들고 `Makefile:427` 하네스 목록에 등재(10종 → **11종**). **음성 대조**: 가짜 `uname`=Linux 면 가드를 통과해 다음 단계(고정본 없음)에서 멈춘다 — 두 케이스가 같은 rc 로 죽으므로 **메시지로 갈랐다**. 변이 대조: 가드 3줄 제거 시 정확히 그 2케이스가 red. `make -n up-isolated` 에 `soak-stack.sh up` **0회** 확인 (2026-08-15 clock-fill-sweep)
**트리거 판정:** 도래 — 2026-08-14 실사고가 근거다 (2026-08-15 soak-survival)

---

### BL-737

**Title:** 서버 `dev.quantbridge.soak-watch.service` 가 failed 상태다
**Category:** 운영 / 소크 감시
**Priority:** P2
**Trigger:** ★**이미 발화했다** — 2026-08-15 `systemctl --user list-units` 실측
**Est:** S (1h)
**출처:** 2026-08-15 soak-survival

**원인 / 영향:** `systemctl --user list-units --type=service` 실측 —
`dev.quantbridge.soak-watch.service  loaded failed failed  QuantBridge soak watch
(게이트 1회 호출 + 지문 변화 시 텔레그램)`. 표본 타이머
`dev.quantbridge.soak-gate.timer` 는 30분 주기로 **정상 동작 중**(마지막 15:54Z)이므로 표본
수집 자체는 살아 있다. 죽은 것은 **알림 축**이다 — 소크가 죽어도 **텔레그램이 안 온다.**

★2026-08-14 사망(04:51Z)을 아무도 몰랐고 다음 세션이 preflight 에서야 발견한 것이 그 결과다.
★`status.md` 는 watch 가 게이트 타이머를 **대체**한다고 적는데(둘 다 돌면 표본 경합) 실제로는
게이트 타이머만 살아 있다 — **문서와 실태가 갈렸다.** 어느 쪽이 정본인지 함께 정해라.

**Risk:** 🟡 (감시 부재는 사고를 만들지 않지만 **사고를 늦게 알게 만든다**)

**상태:** ✅ **Resolved** (2026-08-15 soak-watch-restore) — ★**사인도 사망 시각도 원장이 적은 것과
달랐다.** ⑴ 사인 = `rc=127`, 유닛의 `ExecStart` 가 `~/quantbridge/scripts/soak-watch.sh` 라는
**재배치 전 경로**였다([ADR-029], PR #619). `_install` 이 `${SCRIPT_DIR}` 를 유닛에 **굽기** 때문이다.
⑵ 사망은 08-14 가 아니라 **2026-08-13 13:52Z 부터** — journal 최초 실패가 그 시각이고 08-07~08-13 은
전부 `Finished` 였다. 상태 파일의 `HEARTBEAT_DATE=2026-08-13` 이 독립 확증이다. **41시간** 침묵했고
그 사이 소크 사망 2건(08-14 04:51 · 12:26)을 아무도 몰랐다.
⑶ 뿌리는 이 BL 이 아니라 **[BL-719] ADR-029 롤아웃 체크리스트의 누락**이다 — 1⑦ 이
`soak-gate.sh --install` 만 적고 soak-watch 를 안 적었다(같은 누락의 다른 판이 [BL-744]).
★정본 결정 = **watch 가 게이트 타이머를 대체한다**(문서·코드 쪽이 맞다). 게이트에 flock 이 없어
병존은 표본 경합이다 — 이 회차에서 **실측했다**: 수동 실행과 타이머가 겹쳐 0.7초 간격으로 표본이
2건 들어갔다(02:00:08.989 / 02:00:09.676). 단 **JSON 손상은 0 이었다**(457줄 전건 유효) — 세션 1개
레코드는 짧아 단일 write 로 나간다. 위험은 인터리브가 아니라 **중복 표본**이었다.
★그래서 이중화 대신 **감시자의 죽음을 알리는 축**을 신설했다 — 감시자는 자기 죽음을 알릴 수 없다.
⑴ `OnFailure=dev.quantbridge.soak-watch-alarm.service`(인라인 curl · **스크립트 파일 비의존**이라
다음 재배치에 면역 · 토큰은 `.env.local` 소싱) ⑵ `--status` 의 **설치본 신선도 판정**(설치된
`ExecStart` 가 지금 이 파일인가 · 낡으면 rc=1). 종전 `--status` 는 「타이머가 waiting」만 찍어
41시간 내내 초록으로 보였다.
**검증:** AC-1 = 타이머 발화가 `Finished` + 지문 `|3|→|1|` 상태 변화 알림 실발사(heartbeat 전진이
증인 — 전송 실패 시 전진 안 한다). AC-2 = drop-in override 로 **이번 사고를 재현**(rc=127) → 알람
유닛 발화 → 원복. AC-3 = `--status` 가 낡은 ExecStart 를 red 로. 하네스
`soak-watch-test.sh` **24/24**(신규 ⑬⑭⑭b⑭c⑮⑮b⑮c). 변이는 **6종 전건 판별**(도달 확인 포함)이나 ★**일회 셸 변이**다 — `soak-watch-test.sh` 에는 `final-gates-test.sh` 같은 **영구 변이 엔진이 없다**. 심고·도달 확인하고·돌리고·원복하는 절차를 손으로 밟았으므로 **지금 재현되지 않는다**(codex P2 지적).
★변이 M-d 가 종전 하네스의 공백을 실증했다 — 가짜 게이트가 `"$@"` 를 무시해서
「게이트를 `--no-collect` 로 부르는」 회귀가 전건 초록이었다(C5 fail-open). 케이스 ⑬ 이 그것을 막는다.

★★★**이 회차 최대 반증 — 내 「AC-2 성공」 보고가 거짓이었고, 그것을 잡은 것은 codex 다.**
codex 가 「systemd 가 `${TELEGRAM_*}` 를 bash 실행 전에 확장해 알람이 무력하다」를 P1 으로 냈다.
나는 `systemctl show -p ExecStart` 를 찍어 **리터럴이 남아 있으니 phantom** 이라고 판정했다.
**그 출력은 확장 _전_ 문자열이다** — 오독이었다. 그 뒤 `--fail` 을 붙이자마자 알람 유닛이
**exit 22** 로 뒤집혔고, 진단 결과는 텔레그램 **HTTP 404**(= 빈 봇 토큰으로 `…/bot/sendMessage`).
⇒ **codex 의 결론은 옳았고 근거만 달랐다.** systemd 에서 리터럴 `$` 는 `$$` 이므로
`$${TELEGRAM_CHAT_ID}` 로 고쳤고, 재실증에서 알람 유닛이 `Result=success`(= HTTP 200)를 냈다.
★두 층의 교훈이 겹쳐 있다 — ⑴ **「유닛이 Finished」는 알림 도착의 증거가 아니다**(`--fail` 이
없으면 404 도 rc=0 이다. 이 회차 주제인 「돌았다 ≠ 발화했다」가 내 검증 자신에게 재현됐다)
⑵ **반증했다고 적기 전에 그 관측이 무엇을 재는지부터 확인해라** — `systemctl show` 는 systemd 의
파싱 결과이지 실행 시점 확장 결과가 아니다. 지금은 `--fail` 덕에 **유닛 상태가 알림 도착의
증인**이고, 하네스가 `$$` 형태와 `--fail` 존재를 케이스로 고정한다.
★codex 7건 중 **phantom 0** — 채택 5건, 등급만 조정 1건(토큰이 curl argv 에 실리는 축은
기존 `_notify:128` 과 **동일 패턴**이라 이 회차가 만든 결함이 아니다 → [BL-745] 로 이월).
**트리거 판정:** 도래 — failed 상태 실측이 근거다 (2026-08-15 soak-survival)

---

### BL-739

**Title:** `final-gates` 의 화면 검증 신호가 FE diff 0 에도 required=1 — `vercel.ok` 와 비대칭이다
**Category:** 운영 / 게이트
**Priority:** P3
**Trigger:** ★**이미 발화했다** — 2026-08-15 soak-survival 이 FE·`src/` diff 0 인데 `screen.ok` 를 요구받았다
**Est:** S (30분)
**출처:** 2026-08-15 soak-survival

**원인 / 영향:** `tools/scripts/final-gates.sh:480-481` —

```
signal_gate "/vercel-react-best-practices" "vercel.ok" "$has_fe" "frontend diff 0"
signal_gate "화면 검증 (playwright 또는 /browse)" "screen.ok" 1 ""
```

윗줄은 `$has_fe` 로 **자동 skip** 되는데 아랫줄만 **하드코딩 1** 이다. 두 신호가 같은 FE 축인데
한쪽만 조건부라 **비대칭**이다. 2026-08-15 회차는 `apps/web/` 0줄 · `apps/api/src/` **0줄**
(변경 = CLI `scripts/` + 테스트 `tests/` + `docs/`)인데도 화면 검증 신호를 요구받았다.

★**이것을 「게이트를 고쳐서 통과」로 풀면 안 된다** — 그 유혹이 정확히 하네스 게이밍이고
`final-gates.sh` 주석 자신이 그것을 금지한다. 그래서 이번 회차는 **게이트를 건드리지 않고**
`screen.ok` 에 「검증 불가」가 아니라 **「검증 대상 부재」의 근거**(`git diff --name-only` 로
프로덕션 코드 0줄)를 적는 것으로 처리했다.

★반대편 위험도 같이 봐라 — `has_fe` 로 자동 skip 하면 **BE 변경이 화면을 깨는 경우**를 놓친다
([BL-707] 계열: CORS·포트가 어긋나면 화면에서 「데이터 없음」으로 보인다). 그래서 단순히
`$has_fe` 로 바꾸는 것이 정답인지도 결정 사항이다. **`apps/api/src/` diff 까지 함께 보는 술어**가
후보다 — 이번처럼 `src/` 가 0줄이면 API 응답이 바뀔 수 없다.

**Risk:** 🟢 (신호의 의미가 흐려지는 축. 지금 무엇을 깨지는 않는다)

**상태:** ✅ **Resolved** (2026-08-15 soak-watch-restore) — 술어 = **`has_fe` ∪ `has_api_src`**.
원장이 경고한 대로 단순 `$has_fe` 를 쓰지 않았다 — `apps/api/src/` 가 0줄일 때만 API 응답이
구조적으로 안 바뀌므로 그때만 「검증 대상 부재」다([BL-707] 계열을 놓치지 않는다).
`has_api_src` 는 `has_be`(`^apps/api/`)보다 좁게 `^apps/api/src/` 로 센다.
★**잴 방법이 먼저 없었다** — 하네스의 판정 표면은 `--dry-run` 인데 `signal_gate` 의 dry-run 분기가
required 를 통째로 삼켜서, 다른 게이트가 이미 표에 보여주는 skip 사유를 신호만 안 보여줬다.
그 노출을 회복시킨 것이 수리의 절반이다(`check_signal` 호출 횟수는 불변 —
`signal-check-test.sh` ㉑㉒㉓ 계약 그대로).
**검증:** `final-gates-test.sh` 케이스 **⑩ 신설**(음성 대조가 앞에 온다 — 지금 트리에서 「필수 아님」,
`apps/api/src` 에 탐침을 두면 「필수」). 변이 **M4·M5 신설**(⑩ 이 자기 변이 없이 들어오지 않게 —
[BL-714] 의 M12 선례). M4 = 술어를 리터럴 1 로 되돌림 → ⑩ red, M5 = `apps/api/src` 축 무력화 → ⑩ red.
전체 **10/10 · 변이 5종 + 음성 대조 1종 전건 판별**.
★**이 회차는 이 수리로 자기 PR 을 통과시키지 않는다** — `screen.ok` 신호는 그대로 남기고
「검증 대상 부재」의 근거를 적는다(직전 회차 선례).
**트리거 판정:** 도래 — 이 회차가 실제로 그 자리에서 멈췄다 (2026-08-15 soak-survival)

---

### BL-741

**Title:** `conftest` 의 `create_all` 이 만든 스키마 위에서 **새 migration 이 충돌**한다
**Category:** 테스트 인프라 / alembic
**Priority:** P2
**Trigger:** ★**이미 발화했다** — 2026-08-15 [BL-731] 인덱스 migration 이 로컬에서 `test_migrations.py` 6건을 red 로 만들었다
**Est:** S (1-2h — 설계 결정이 선행)
**출처:** 2026-08-15 soak-survival ([BL-731] 인덱스 추가 중 발견)

**원인 / 영향:** 테스트 DB 는 두 주체가 만든다 —

- `tests/conftest.py` 세션 픽스처의 `SQLModel.metadata.create_all` (모델을 그대로 반영)
- `alembic upgrade head` (`test_migrations.py` · `CI fresh DB alembic` 게이트)

**둘은 서로를 모른다.** 2026-08-15 실측: `alembic_version = 20260801_0001`(새 migration 이전)인데
`create_all` 이 만든 `ix_exchange_exits_account_order` 는 **이미 존재**했다. 그 상태로
`upgrade head` 가 돌면 `DuplicateTable: relation ... already exists` 로 죽는다.

★**종전에 안 드러난 이유** — migration 이 squash 된 base(`20260801_0001`) **하나뿐**이었다.
`create_all` 이 만드는 것과 base 가 만드는 것이 같고 `alembic_version` 은 이미 head 라
`upgrade` 가 no-op 이었다. **[BL-731] 이 두 번째 migration 을 더하면서 순차 적용이 처음 생겼다.**

★**CI 는 안 걸린다** — `CI fresh DB alembic` 게이트가 throwaway DB 에 alembic 만 돌린다.
걸리는 것은 **로컬에서 pytest 를 한 번이라도 돌린 개발자**다. 그리고 증상이
「내 migration 이 깨졌다」로 보여서 원인을 엉뚱한 데서 찾게 된다(이번에 그랬다).

★즉시 해소법: `drop index if exists trading.<이름>` 후 재실행. **이것은 우회이지 수리가 아니다** —
다음 migration 마다 반복된다.

**권장 접근:** 세 갈래 중 결정이 필요하다.
⑴ **테스트 DB 도 alembic 으로만 만든다** — `create_all` 을 걷어낸다. 가장 정합적이지만 픽스처
속도가 느려지고(모든 migration 순차 적용) 실패 지점이 늘어난다.
⑵ **`create_all` 전에 DB 를 항상 비운다** — 지금도 `drop_all` 은 하는데 **인덱스가 남는 경로**가
있다는 뜻이므로 그 경로부터 찾아야 한다.
⑶ migration 을 `IF NOT EXISTS` 로 쓴다 — 가장 싸지만 **「적용됐는가」를 흐린다**. 권하지 않는다.

★어느 쪽이든 **재발 회귀 테스트**가 함께 가야 한다 — 「create_all 로 만든 DB 에 upgrade head 를
돌리면 통과한다」를 단언하는 케이스가 지금 없다.

**Risk:** 🟡 (프로덕션 무관. 개발자 시간을 먹고 **원인을 오도한다**)

**상태:** ✅ **Resolved (2026-08-15 clock-fill-sweep)** — `conftest.bootstrap_test_schema` 가 `create_all` 직후 `alembic_version` 을 **head 로 stamp** 한다. ★**착수 전제가 반증됐다** — 원장이 적어 둔 「`drop_all` 이 인덱스를 남긴다」는 거짓이다. `ix_exchange_exits_account_order` 는 모델(`trading/models.py:783`)에 있어 metadata 안이고 `DROP TABLE` 이 같이 가져간다. migration 전용 인덱스 13건도 전부 테이블이 metadata 안이라 생존 경로가 아니다. **`drop_all` 밖에 실제로 남는 것은 `public.alembic_version` 하나뿐**이고(근거: `tests/test_migrations.py:158-159` 가 대조 시 이 테이블을 명시적으로 pop 한다), 스키마는 모델-head 인데 버전만 낡아서 `20260815_0001`(유일한 맨몸 `op.create_index`)이 이미 있는 인덱스를 또 만들었다. ★**지우기만 하면 안 된다** — 버전이 없으면 `upgrade head` 가 base 부터 돌아 여전히 죽는다. 회귀 테스트 `test_upgrade_head_survives_the_create_all_bootstrap` 은 head 앞 리비전을 **일부러 심어** 사고를 결정적으로 재현한다(안 그러면 red 가 `test_alembic_roundtrip` 실행 순서에 좌우된다). red 실측 = `DuplicateTable: relation "ix_exchange_exits_account_order" already exists` · 수리 후 BE **4633 passed** (2026-08-15 clock-fill-sweep)
**트리거 판정:** 도래 — 실제로 red 를 만들었다 (2026-08-15 soak-survival)

---

### BL-743

**Title:** 서버 DB 에 alembic migration 을 적용하는 경로가 없다 — 첫 두 번째 migration 에서 드러났다
**Category:** 운영 / 배포
**Priority:** P1
**Trigger:** ★**이미 발화했다** — 2026-08-15 `ix_exchange_exits_account_order` 가 로컬엔 있고 서버엔 없다
**Est:** S (1-2h — 절차 결정이 선행)
**출처:** 2026-08-15 soak-survival ([BL-731] 인덱스 추가 후 실측)

**원인 / 영향:** 2026-08-15 실측 —

```
로컬 개발 DB   alembic_version = 20260815_0001   인덱스 있음
서버 소크 DB   alembic_version = 20260801_0001   인덱스 **없음**
```

`.github/workflows/` 에 **배포 워크플로가 없고**(ci · live-smoke · nightly 뿐), 소크 배포는
`soak-stack.sh down → pin → up` 이다. 그런데 **`pin` 은 `apps/api/src` 스냅샷만 뜬다** —
`alembic/` 은 그 밖이라 **DB 스키마는 영원히 안 따라온다.**

★종전에 안 드러난 이유: migration 이 squash base **하나뿐**이었고 서버 DB 는 그 시점에 만들어졌다.
**[BL-731] 이 두 번째를 더하면서 처음으로 격차가 생겼다.**

★**지금 당장 깨지지는 않는다** — 인덱스는 성능 축이라 없어도 동작한다(서버 원장 892행에서
`Seq Scan`). 위험한 것은 **다음 migration 이 컬럼/제약을 건드릴 때**다. 그때는 pin 한 코드가
없는 컬럼을 읽고 조용히 죽는다.

★★[BL-741] 과 다른 축이다 — 그쪽은 **테스트 DB** 에서 `create_all` 과 alembic 이 부딪히는 것이고,
이쪽은 **서버 DB** 에 migration 이 아예 도달하지 않는 것이다.

**권장 접근:** ⑴ `soak-stack.sh up` 이 기동 전에 `alembic upgrade head` 를 돌리게 한다 —
정합적이지만 **소크 창 중에 DDL 이 도는 것**을 뜻하므로 그 안전성 판단이 선행이다.
⑵ 별도 `soak-stack.sh migrate` 를 두고 사람이 명시적으로 부른다 — `pin` 과 같은 등급의
「명시적 배포 행위」로 취급. ★현재 절차서(status.md 재기동 8단계)에 그 자리가 없다.

★★**「alembic 마이그레이션」은 `status.md` ⓵ 의 비목표(사용자 결정 대기)다.** 2026-08-15 회차가
codex 의 인덱스 지적을 받아 **migration 을 하나 만들었고**(로컬 적용·CI 통과) 그것이 이 항목의
계기다. 서버 적용은 더 큰 결정이므로 **비목표 문구부터 갱신**하고 시작해라 — 「금지」인지
「승인 후 허용」인지가 지금 모호하다.

**Risk:** 🔴 (지금은 성능뿐이나, 스키마를 바꾸는 migration 이 오면 **소크가 조용히 죽는다**)

**상태:** ✅ **Resolved** (2026-08-15 soak-watch-restore) — ★**가설보다 컸다.** 「`pin` 이 `alembic/`
을 안 뜬다」는 참이지만 그건 증상이고, 뿌리는 **소크 스택에 migration 적용 단계가 아예 없다**는
것이었다: 소크 compose 6서비스에 **api 롤이 없고**(`run_alembic_with_lock` 을 부르는 유일한 롤),
celery 는 `command:` override 로 entrypoint 의 롤 분기를 통째로 우회한다
(`apps/api/docker-entrypoint.sh:117` passthrough). 즉 `pin` 경로를 넓혀도 안 고쳐진다.
채택 = **권장 ⑵ `soak-stack.sh migrate`**(기본 dry-run + `--confirm`, `soak-restart.sh` 문형).
⑴(`up` 이 자동 upgrade)을 기각한 이유 = 창 중 DDL 이 **암묵적으로** 돌아 「무엇이 언제 스키마를
바꿨나」에 답할 수 없게 된다. `pin` 과 같은 등급의 명시적 배포 행위로 뒀다.
★**결정적 검증을 코드에 박았다** — upgrade 뒤 `docker exec ${DB_CONTAINER} psql` 로 **게이트가 보는
그 DB** 를 다시 읽어 head 와 대조한다. `.env.local` 이 다른 DB 를 가리키고 있었다면 upgrade 는
성공하고 여기서 실패한다(조용한 오적용을 막는 유일한 축).
★**곁가지 2건 — `SOAK_WATCHED_PATHS`(`soak-stack.sh:101`)가 두 곳에서 침묵하고 있었다.**
⑴ `scripts` 는 [ADR-029] 재배치로 **존재하지 않는 경로**가 됐다(2026-08-13부터 게이트 스크립트
감시 축이 죽어 있었다) — 없는 경로의 `git log -- <path>` 는 오류가 아니라 **빈 출력**이라
「누락 없음」과 구분되지 않는다. ⑵ `apps/api/alembic` 이 처음부터 없어서 서버 DB 가 뒤처진
채로도 「누락 커밋 0개」가 나왔다. 둘 다 교정했다.
★내 dry-run 초판도 반증됐다 — `alembic history -r A:B` 가 **A 를 포함**해서 「적용 대기 2 항목」을
찍었는데 실제 대기는 1개였다(운영자가 보는 유일한 정보라 그대로면 오독). awk 로 `<cur> ->` 줄까지만 센다.
**서버 적용 완료** (사용자 승인) — `20260801_0001 → 20260815_0001`. 검증: `trading` 스키마 인덱스
집합이 로컬과 **완전 일치**(diff 0), 적용 전후 게이트 C3 실격 0 유지 · C5 6/6 · C2 9.22h → 9.50h 계속 증가.
★**codex 적대 리뷰가 3건을 더 잡았고 전건 채택했다** — ⑴ 사후 재확인만으로는 **오적용을 못 막는다**
(다른 DB 를 _먼저_ 바꾼 뒤에야 실패하고 그 DDL 은 되돌릴 수 없다) ⇒ upgrade **전에**
`DATABASE_URL` 이 `docker port ${DB_CONTAINER}` 의 published endpoint 를 가리키는지 대조한다.
⑵ 맨 `alembic upgrade head` 는 레포에 이미 있는 **advisory lock 래퍼를 우회**한다
(`docker-entrypoint.sh:52-55` 가 쓰는 그것) ⇒ `run_alembic_with_lock` 을 같은 lock key 로 재사용한다.
⑶ `alembic history` 실패가 **「0 항목」으로 보였다**(fail-open) ⇒ rc 를 보고 전제 미충족(2)으로 죽는다.
그리고 `migrate --confirm --typo` 가 조용히 집행되던 것도 막았다.
**도달 확인 포함 실증** — 로컬 `alembic_version` 만 임시로 되돌려(스키마 불변·dry-run) 새 경로를
실제로 지나게 했다: 사전 대조 `✓`, 대기 1항목 정확, 이력에 없는 revision 에서 **rc=2**(종전이면
「0 항목」으로 초록이었을 자리다), 여분 인자 rc=1. 직후 원복 확인.
**트리거 판정:** 도래 — 로컬/서버 `alembic_version` 불일치가 실측됐다 (2026-08-15 soak-survival)

---

### BL-744

**Title:** 서버 `quantbridge-api.service` 가 **좀비**였다 — 죽으면 영원히 안 돌아온다
**Category:** 운영 / 서버 systemd
**Priority:** P1
**Trigger:** ★**이미 발화했다** — 2026-08-15 `/proc/<pid>/cwd -> …/backend (deleted)` 실측
**Est:** S (30분)
**출처:** 2026-08-15 soak-watch-restore ([BL-737] 부검 중 발견 — 프롬프트·원장 어디에도 없었다)

**원인 / 영향:** [BL-737] 과 **같은 뿌리**([ADR-029] 재배치의 서버측 잔존)인데 더 위험했다.

```
MainPID=3169921   ExecMainStartTimestamp=2026-08-07 12:26:50 UTC   (재시작 이력 0)
/proc/3169921/cwd -> /home/ubuntu/quantbridge/backend (deleted)
ExecStart=/home/ubuntu/quantbridge/backend/.venv/bin/uvicorn        ← 파일 없음
                    /home/ubuntu/quantbridge/apps/api/.venv/bin/…   ← 이쪽에 있다
```

08-07 에 뜬 프로세스가 **삭제된 inode 를 붙들고** 살아 있었을 뿐이다. `Restart=always` 인데
`ExecStart` 가 사라졌으므로 **한 번 죽으면 rc=203/EXEC 로 영구 실패 루프**다. systemd 자신이
그것을 알고 있었다 — 재시작 시 `Current command vanished from the unit file` 을 남겼다.

★**소크에 직결한다** — 이 API 가 C5⑷ prometheus 스크레이프 대상(`:8100/metrics`)이다.
게다가 `Environment=PROMETHEUS_MULTIPROC_DIR=…/backend/.metrics` 가 게이트의
`METRICS_DIR=${ROOT}/apps/api/.metrics`(`soak-gate.sh:61`)와 **어긋나** 있어서, HTTP 갈래가
죽었을 때의 파일 폴백조차 API 롤 카운터를 못 봤다. [BL-719] 롤아웃 1⑤ 가 `.metrics` **파일**은
옮겼지만 그것을 가리키는 **유닛의 환경변수**는 안 고쳤다.

★**뿌리 = [BL-719] 체크리스트에 「서버 systemd 유저 유닛 점검」항목이 없다.** 1⑦ 은
`soak-gate.sh --install` 하나만 적었고, ⑤ 는 `.env` 의 구경로만 점검하라고 했다. 그 결과
같은 재배치가 **세 곳**을 남겼다 — soak-watch 유닛([BL-737]) · 이 API 유닛 · 그리고
`SOAK_WATCHED_PATHS` 의 `scripts`([BL-743] 곁가지). 다음 재배치 때는 **유닛 파일의 절대경로
전수**를 점검 항목으로 둬라(`grep -l quantbridge ~/.config/systemd/user/*`).

**Risk:** 🔴 (지금 도는 것은 무사하지만 **재부팅·OOM·크래시 한 번이면 API 가 영구 사망**하고,
그때 C5⑷ 가 함께 무너진다)

**상태:** ✅ **Resolved** (2026-08-15 soak-watch-restore) — 유닛 3곳 교정
(`WorkingDirectory` · `PROMETHEUS_MULTIPROC_DIR` · `ExecStart` 를 전부 `apps/api` 로) 후 재시작.
`APP_ENV` 는 **올리지 않았다** — 유닛 주석이 적은 대로 production 이면 `PROMETHEUS_BEARER_TOKEN`
이 강제되어 게이트의 스크레이프가 401 이 되고 C5⑷ 가 영구 false 다.
**검증:** `/health` 200 · `/metrics` 무인증 **401**(fail-closed 유지, [BL-704]) · bearer 200(414줄) ·
`/proc/<새 pid>/cwd` 가 `apps/api` · 재시작 전후 게이트 C3 실격 0 유지 · C5 6/6.
★실수 하나를 기록한다 — 재시작 4초 뒤에 친 curl 이 `http=000` 이라 「기동 실패」로 읽을 뻔했다.
uvicorn 은 **12초** 걸렸다(01:54:37 재시작 → 01:54:49 `Application startup complete`).
**트리거 판정:** 도래 — 삭제된 cwd 와 부재하는 ExecStart 가 실측됐다 (2026-08-15 soak-watch-restore)

---

### BL-747

**Title:** 감시 타이머의 위상이 **사람이 손으로 돌리면 밀린다** — 표본 간격이 C4 한계까지 간다
**Category:** 운영 / 소크 감시
**Priority:** P2
**Trigger:** ★**이미 발화했다** — 2026-08-15 AC-2 강제 발화 뒤 표본 간격 53분 실측
**Est:** XS (20분)
**출처:** 2026-08-15 soak-watch-restore (회차를 닫은 **뒤** 무인 발화를 확인하다 발견)

**원인 / 영향:** `OnUnitActiveSec=30min` 은 **마지막 활성화 기준**이다. 강제 발화 실증이나
장애 재현으로 유닛을 한 번 손으로 돌리면 그 시각부터 30분이 다시 세어져 **위상이 밀린다.**

```
간격 = (강제 발화 시각 − 마지막 정상 표본 시각) + 30분
     = d + 30      (d ≤ 29)
     ⇒ 최악 59분 · C4 한계 60분 → 여유 1분
     그런데 systemd 기본 AccuracySec = 1분  ⇒ 여유는 사실상 0
```

실측: [BL-737] 회차의 AC-2 강제 발화(02:20·02:22) 뒤 표본이 **02:00:09 → 02:53:20 = 53분**
간격으로 벌어졌다. C4 는 통과했지만 **7분 남았다.**

★**이 회차가 만든 위험이다.** 감시자를 고치려고 강제 발화 실증을 한 것이 그 자체로 표본
간격을 밀었다 — 9.50h 를 벌어놓고 **검증 때문에** C4 공백 → 실격 → T0 리셋으로 갈 수 있었다.

★**회차를 닫은 뒤에 발견했다.** 게이트 2단·머지까지 끝낸 다음 「타이머가 **스스로** 도는 것을
아직 못 봤다」로 무인 발화를 확인하러 갔다가 나왔다. 종결 판정 뒤의 관측이 값을 낸 사례다.

**Risk:** 🟡 (한 번의 강제 발화로는 한계를 안 넘지만 여유가 없고, 대가가 **T0 리셋**이다)

**상태:** ✅ **Resolved** (2026-08-15 soak-watch-restore 후속) — `OnCalendar=*:00/30` +
`AccuracySec=30s` 로 **벽시계에 못박았다**. 사람이 중간에 몇 번을 돌리든 위상이 안 밀린다.
`Persistent=true` 는 유지(재부팅·정지 구간에서 놓친 발화를 따라잡는다).
**검증:** 서버 실증 — 강제 발화 **전후 모두 `NEXT=03:30:00`** 으로 불변(종전 설정이면 03:32 로
밀렸을 자리다) · 그 강제 발화 자체는 `Result=success`. 하네스 케이스 **⑭d** 신설 — ★**존재 확인이 아니라 `[Timer]` 키 집합 동등**으로 잰다.
codex 가 초판의 구멍을 잡았다: 「`OnCalendar` 가 있나」만 보면 `AccuracySec` 이 지워져도, 두 번째 `OnCalendar=*:15/30` 이 **추가**돼도(= 15분마다 발화) 통과한다. 집합 동등으로 바꾼 뒤 일회 셸 변이 **4종**이 전부 red 를 냈다 — M-g(위상 되돌리기)·**M-h(`AccuracySec` 삭제)**·**M-i(둘째 `OnCalendar` 추가)**·M-j(`Persistent` 삭제). **가운데 둘은 초판이 못 잡던 것**이다.
**트리거 판정:** 도래 — 53분 간격이 실측됐다 (2026-08-15 soak-watch-restore)

---

### BL-748

**Title:** 소크 게이트 C4 가 **공허 통과**한다 — 볼 창이 0개면 「표본 공백 0건 ✓」가 나온다
**Category:** 운영 / BL-003 게이트 판정
**Priority:** P2
**Trigger:** ★이미 발화했다 — 2026-08-15 판독이 「C4 표본 공백 0건 ✓」와 「표본 간격 최대 326.4분」을 같은 출력에 찍고 있었다
**Est:** S (판정식 1줄 + 분기 + 테스트 4건)
**출처:** 2026-08-15 clock-fill-sweep ([BL-641] 처방 축 확정 과정에서 부수 발견)

**원인 / 영향:** `soak_gate_predicate.py` 의 C4 는 `for entry in clean:` 로 **귀속 창 안에서만** 표본
공백을 세고 `C4_ok = not gaps` 로 판정했다. `clean`(검증된 귀속 창)이 비면 루프가 **0회**라 빈
리스트를 얻고 **통과**한다. 「볼 게 없다」가 「이상 없다」로 보고되는 **fail-open** 이다.

실측 대조 — 2026-08-15 04:51Z 판독에서 「최대 326.4분」을 낸 것은 C4 가 아니라 세션·창 필터가
**없는** 보고용 계산(`:809-815`)이다. 로컬 코퍼스로 재현하니 상위 공백 5개(최대 **1524.5분**)가
**전부 귀속 구간 바깥**이라 C4 는 한 건도 세지 않았다. ⇒ 소크가 **관측 없이 흘러간 구간**을 게이트가
「tick 연속성 정상」으로 보고할 수 있었다. 이 게이트는 [BL-003](#bl-003) P0 의 유일한 판정자다.

**처방 (2026-08-15 적용):**

- `C4_ok = bool(clean) and not gaps` + 새 조건 키 `C4_no_window`.
- 판정 분기를 `if not conditions["C4_ok"]:` 로 바꾸고 **사유 문장을 갈랐다** — 「공백 N건」과
  「귀속 창이 0개」를 같은 문장으로 찍으면 운영자가 정상으로 읽는다. 그것이 이 결함이 오래 산 방식이다.
- 판정어는 **UNKNOWN 측정불가**다(FAIL 아님). 볼 창이 없는 것은 위반이 아니라 판정 불가다.

**함께 고친 소품 2건 (같은 파일):**

- `darkness_computed` 가 `is not None` → **`isinstance(dict)`**. 종전에는 dict 가 아닌 값이 오면
  C5 는 ✓ 인데 셸은 「어둠 비율: ✗ 계산 실패 (C5 위반)」을 찍었다 — **판정과 표시가 다른 말을 했다.**
- 어둠 분자 집합이 `soak_gate_predicate.py:85`(**아무도 참조 안 하는 죽은 상수**)와
  `soak-gate.sh:548`(하드코딩 리터럴) **두 곳에 복제**돼 있었다. 셸은 시스템 python 인라인이라
  술어를 import 할 수 없으므로 코드를 합치는 대신 **동등성을 테스트로 못박았다**.

**검증:** `test_soak_gate_predicate.py` **72 passed**. 신규 4건 = 공허 통과 차단 · **음성 대조**(정상
판독은 계속 `C4_ok` ✓ + PASS — 없으면 `C4_ok=False` 고정으로도 통과해 판별력 0) · darkness 타입 ·
셸↔술어 집합 동등. **변이 대조**: `C4_ok` 를 `not gaps` 로 되돌리면 정확히 공허 통과 케이스가 red.
★**서버 무접촉** — 서버는 `git pull` 을 하지 않으므로 이 수정은 진행 중인 창에 닿지 않는다.

**Risk:** 🟢 (판정을 **더 엄격하게** 만드는 방향이다 — 초록에 가까워지는 변경이 아니다)

**상태:** ✅ **Resolved (2026-08-15 clock-fill-sweep)** — 등재와 수리를 같은 회차에 했다.
**트리거 판정:** 도래 — 실측 출력이 근거다 (2026-08-15 clock-fill-sweep)

---

### BL-754

**Title:** rate limit 이 프록시 뒤에서 **전 사용자 공용 버킷**으로 붕괴한다
**Category:** Security / rate limit
**Priority:** P2
**Trigger:** ★**이미 발화 중이다** — 공개 전환([BL-071]) 전까지는 사용자가 1명이라 증상이 안 보일 뿐이다. 2번째 사용자가 붙는 순간 도래
**Est:** ~~S (auth dependency 1줄 + `TRUSTED_PROXIES` 설정 + 회귀)~~ → **2026-08-16 정정: M** (아래 ★반증)
**출처:** 2026-08-15 surface-truth 아키텍처 감사 §C-1 · 2026-08-16 production-readiness 코드 대조로 Est 정정

**원인 / 영향:** `rate_limit_key` 는 `request.state.user_id` 를 먼저 보는데 **아무도 그 값을
세팅하지 않는다** — 함수 docstring 이 스스로 자백한다(「현재 Phase B: request.state.user_id 는
미세팅 상태 → 항상 IP fallback」). 그리고 `TRUSTED_PROXIES` 기본값이 **빈 문자열**이라
`_client_ip_or_xff` 는 XFF 를 무시하고 `client.host` 를 쓴다.

⇒ Cloudflare 터널 뒤 배포에서는 **모든 요청의 `client.host` 가 127.0.0.1** 이다. 전 사용자가
`ip:127.0.0.1` **하나의 버킷**을 공유한다 — 한 사람이 한도를 태우면 나머지가 429 를 받고,
공격자는 혼자서 전체를 잠글 수 있다.

★★**2026-08-16 반증 — 종전 「권장 접근 ⑴ = auth dependency 1줄」은 성립하지 않는다.**
`install_rate_limit` 이 `SlowAPIMiddleware` 를 **ASGI 미들웨어**로 붙이는데(`rate_limit.py:176-198`,
설치 지점 `main.py:323-325`), ASGI 미들웨어는 **라우팅·의존성 해석보다 먼저** 돈다. 반면
`get_current_user`(`auth/dependencies.py:50-55`)는 `Depends` 라 라우트 핸들러 직전에 돈다.
⇒ 인증 의존성이 `request.state.user_id` 를 세팅해도 **미들웨어의 `default_limits=["100/minute"]`
판정에는 반영되지 않는다** — 그 시점에 키가 이미 확정됐다. 고쳐지는 것은
`@limiter.limit(...)` **데코레이터 12곳**(waitlist·optimizer·stress_test·backtest·strategy·convert)
뿐이고 **나머지 전 엔드포인트는 그대로 `ip:127.0.0.1` 공용 버킷**이다.
★부수 — `authenticate_clerk_request`(`realtime/auth.py:21-48`)는 파라미터가 `Requestish` 라
WebSocket 경로에서 `.state` 가 없는 `SimpleNamespace` mock 도 받는다. 「1줄 세팅」이 간단하지
않은 두 번째 이유다.

★★**기존 테스트 2건이 이 항목을 무증거로 만든다** (`apps/api/tests/common/test_rate_limit.py`):
⑴ `test_per_user_isolation`(`:86`)이 프로덕션 `rate_limit_key` 대신 **인라인 lambda `key_func`**
(`:96-99`)을 쓴다 ⇒ 「user 격리 초록」이 프로덕션 코드에 대한 증거가 **아니다**.
`rate_limit_key` 를 직접 호출하는 테스트는 **0건**.
⑵ `:121-149` 는 **현재 버그를 정상 동작으로 고정**한다(`assert r3.status_code == 429  # 같은
client.host 로 묶임`, `:148`) — 수리하면 이 단언이 반드시 깨진다.

**권장 접근 (2026-08-16 재기술):** ⑴ **인증 전용 ASGI 미들웨어**를 세워 `SlowAPIMiddleware`
**이전에** `request.state.user_id` 를 채우거나, `SlowAPIMiddleware` 를 걷어내고 전 엔드포인트를
데코레이터로 옮긴다 ⑵ 배포 호스트 `TRUSTED_PROXIES` 에 터널 대역을 넣는다
⑶ **음성 대조 필수** — 신뢰 대역 밖에서 온 XFF 는 여전히 무시돼야 한다(위조 차단)
⑷ **먼저 `rate_limit_key` 자체를 겨누는 테스트를 세워라** — 지금 초록은 판별력이 없다.

**Risk:** 🟡 (⑵ 를 너무 넓게 잡으면 XFF 위조로 한도 우회가 열린다)

**상태:** ✅ **Resolved (2026-08-16 beta-cutover)** — `_RateLimitIdentityMiddleware` 를 `SlowAPIMiddleware` **바깥**에 세워 `request.state.user_id` 를 채우고(검증기는 `realtime/auth._decode` 재사용 · DB 미접촉 · 거부하지 않음), `CF-Connecting-IP` 를 XFF leftmost 보다 우선한다(CF 는 XFF 를 덮어쓰지 않고 **붙이므로** leftmost 는 클라이언트가 심을 수 있다). `TRUSTED_PROXIES` 는 이 배포에서 **`127.0.0.1/32`** 다 — cloudflared 가 `network_mode: host` 라 uvicorn 이 보는 peer 가 루프백이고, `.env.example` 2종의 「Cloudflare 대역」 안내가 틀렸다. ★★**첫 테스트가 판별력 0 이었다** — `@limiter.limit` 데코레이터 엔드포인트는 키를 **핸들러 래퍼 안**에서 계산해 미들웨어 순서 변이가 초록으로 통과했다. 순서가 갈리는 곳은 `default_limits`(= 데코레이터 없는 엔드포인트) 하나뿐이라 fixture 를 바꿨고, 그 뒤 변이 **4/4 red**. ★원장의 「기존 테스트 2건이 무증거·버그고정」은 **절반만 참** — `test_per_user_isolation` 은 인라인 lambda key_func 라 무증거가 맞지만, `test_unauthenticated_uses_client_host_when_no_xff` 는 「신뢰 안 된 XFF 는 무시한다」는 **옳은 fail-safe 계약**이라 유지했다
**트리거 판정:** 도래 — 기전은 지금 성립한다. 다만 **영향**이 사용자 2명부터이고 실제 수리가 M(미들웨어 구조 변경)이라 공개 전환([BL-071])과 동승이 합리적이다 (2026-08-16 production-readiness)

---

### BL-757

**Title:** 시크릿 스캐너가 **0건**이고 `.gitignore` 가 `.env.prod` 계열을 안 막는데, 추적되는 `.env.prod.example` 이 그 작명을 유도한다
**Category:** Security / CI
**Priority:** P2
**Trigger:** ★**이미 발화 가능하다** — 다음에 누가 `.env.prod` 를 만드는 순간
**Est:** S (gitleaks CI job 1개 + `.gitignore` 3줄)
**출처:** 2026-08-15 surface-truth 아키텍처 감사 §A-1·A-2

**원인 / 영향:** `git check-ignore` 실측 — `.env.prod` / `.env.production` / `.env.staging`
셋 다 **무시되지 않는다**. 그런데 `apps/api/.env.prod.example` 이 추적되고 있어 그 이름이
정확히 사람이 따라 쓸 이름이다. 그리고 gitleaks/trufflehog/detect-secrets/dependabot/CodeQL 이
`.github/`·`.husky/`·`tools/` 어디에도 **없다**(grep 0건) ⇒ 실수로 커밋된 키를 **아무도 못 잡는다**.

★이 레포는 암호화된 거래소 API 키를 다루고 `TRADING_ENCRYPTION_KEYS` 를 env 로 받는다.
그 키가 한 번 히스토리에 들어가면 rotate 없이는 회수 불가다.

**권장 접근:** ⑴ `.gitignore` 에 `.env.prod*` / `.env.production*` / `.env.staging*` ⑵ CI 에
gitleaks job 1개 ⑶ **음성 대조** — `.env.*.example` 은 계속 추적돼야 한다(그것이 문서다).

**Risk:** 🟢

★★**2026-08-16 착수 — 노출은 3곳에서 관측됐지만 수리 표면은 루트 1파일이다.**
`git check-ignore --no-index` 로 9경로(3이름 × 루트·api·web)를 재니 **전부 뚫려 있었다**.
그래서 처음에 `.gitignore` **3파일 모두**에 같은 줄을 넣었는데, **그것이 과잉이었다** —
슬래시 없는 gitignore 패턴은 **재귀 적용**이라 루트의 `.env.prod*`/`.env.production*`/
`.env.staging*` + `!.env*.example` 5줄이 `apps/api/.env.prod` · `apps/web/.env.production` 까지
전부 덮는다(실측: 하위 2파일을 원복한 상태에서 **9경로 미차단 0건** · `.example` 4건 추적 유지).
부정 규칙이 load-bearing 임은 ablation 으로 확인했다(그 줄을 빼면 추적 중인
`apps/api/.env.prod.example` 이 `.env.prod*` 에 잡힌다).

★★**하위 복제를 되돌린 이유는 중복 자체가 아니라 대가다.** `apps/web/**` 에 diff 가 생기면
`final-gates` 의 `has_fe` 가 1이 되어 FE 게이트 3종과 화면·vercel 신호가 강제되고,
**`final-gates-test.sh` 케이스 ⑩**(「apps/web·apps/api/src diff 0 인데 신호가 필수인가」)이
**이 브랜치에서 상시 red** 가 된다(2026-08-16 codex P1 · 실측 rc=1). 시크릿을 한 줄도 더
막아주지 않으면서 회차 비용만 올린다. ⇒ 루트에만 두고, **복제하지 마라**를 그 자리 주석에 박았다.
★이 하네스는 `Makefile` 의 `gate-harnesses` 목록에만 있고 `final-gates.sh` 의 `run_gate` 에는
없어서 **pre-PR 게이트가 그것을 못 봤다** — codex 가 아니었으면 CI 에서야 알았다.

★**검증기의 무증거를 한 번 밟았다** — `git check-ignore` 는 기본적으로 **추적 파일을 건너뛴다**.
그래서 `.example` 4종이 「무시 안 됨」으로 나온 것이 규칙 덕인지 추적 중이라서인지 구분되지 않았다.
`--no-index` 로 재측정해야 규칙 출처까지 확정된다.

★★★**히스토리 전량 스캔에서 실제 시크릿 2건이 나왔다 — 「0건」이 아니었다.**
`gitleaks git . --log-opts=--all` 로 **1,056 커밋**을 훑어 `fb47978c`(2026-04-25, PR #71) 의
`docs/superpowers/plans/2026-04-24-h2-sprint10-phase-a2.md:224,286` 에서
`TRADING_ENCRYPTION_KEYS` 44자 Fernet 리터럴 2건을 찾았다.
**판정 = rotate 불요.** sha256 대조로 확인했다(값 미출력): 히스토리 키 `9b2d3222…` 는 로컬
`.env`(`841af2dc…`)·`apps/api/.env.local`(`60c1787c…`)·**서버**(`a371e6bb…`) 어느 것과도
**불일치**한다 — 그 회차 워크트리 스모크용 일회성 키다. 그 파일은 이미 삭제돼 현재 트리에 없다
(그래서 워킹트리 스캔은 0건이다). ★**히스토리에서는 지워지지 않는다** — 재감사 명령을 `ci.yml`
주석에 실측 그대로 남겼다.

★**CI 잡 안에 자기검사(positive control) 스텝을 본 스캔 앞에 뒀다.** 바이너리 다운로드가 깨지거나
allowlist 가 넓어지면 본 스캔은 **영구 0건 = 영구 초록**이 된다 — 이 레포가 반복해 밟은 형태다.
매 실행마다 `$RUNNER_TEMP` 에 가짜 키를 심어 그것을 반증한다.
★스캔 방식은 `gitleaks dir`(워킹트리)다. 커밋 범위 스캔은 `fetch-depth: 0`(히스토리 213MB)이
필요하고 **base/head 가 어긋나면 0 커밋 스캔 후 초록** 이라는 fail-open 이 있다. `dir` 는 상태가
없어 그 구멍이 없고, `pull_request` 가 머지 프리뷰를 checkout 하므로 「머지되면 main 에 남는 파일
전체」라는 정확한 질문에 답한다. 실측 18.3MB / 0.5초.

★★**함정 — 같은 명령을 로컬 개발 트리에서 돌리면 6,795건이 나온다.** `gitleaks dir` 은
`.gitignore` 를 존중하지 않아 `node_modules/`(6,779건)와 **gitignore 된 `.env`·
`apps/api/.env.local` 실파일**(16건)까지 읽는다. CI 는 `actions/checkout` 트리라 그것들이 애초에
없어 0건이다 — 조건이 다른 것이지 설정이 틀린 것이 아니다. 로컬에서 CI 와 같은 답을 보려면
`git ls-files -co --exclude-standard` 목록만 임시 트리에 복사해 스캔해라(2026-08-16 실측:
**1,663 파일 · `no leaks found` · rc=0**, 같은 트리에 가짜 키 1개를 심으면 **rc=1 · 1건**).
★이 소음을 줄이겠다고 경로 allowlist 를 넣으면 CI 에서 그 디렉터리가 통째로 무방비가 된다.
이 함정을 `ci.yml` 의 본 스캔 스텝 주석에 실측째로 박았다 — 다음 사람이 같은 자리에서 놀란다.

**상태:** ✅ **Resolved (2026-08-16 production-readiness)** — `.gitignore` 3파일 + `.gitleaks.toml`(값 단위 allowlist 4개, 경로 면제 0) + `ci.yml` `secret_scan` 잡(`ci` 집계 잡의 `needs`·`check` 양쪽 배선). 판별력 증명 4종 실행: 양성(가짜 키 2건 검출 rc=1) · 음성(제거 후 0건 rc=0) · `--no-index` 9경로 전건 무시 + `.example` 4건 추적 유지 · 히스토리 1,056커밋(위 2건 발견·rotate 불요)
**트리거 판정:** 해소 — 2026-08-16 에 수리 완료 (2026-08-16 production-readiness)

---

### BL-766

**Title:** e2e row 로케이터가 헤더 행을 잡을 수 있다 — 단언이 무증거로 통과한다
**Category:** Test / FE e2e
**Priority:** P2
**Trigger:** ★`apps/web/e2e/` 의 표 기반 spec 을 손대는 회차 · 또는 e2e 초록을 근거로 종결 판정을 낼 때
**Est:** S (로케이터 치환 + 음성 대조)
**출처:** 2026-08-15 surface-truth 회차가 실물 1건을 잡음 → 2026-08-16 deploy-activation 전수 감사

**원인 / 영향:** `page.locator("tr", { hasText: "…" })` 는 `<thead>` 의 헤더 행도 후보로 잡는다.
헤더에 그 문자열이 있으면 `.first()` 가 **헤더 행을 집고**, 그 뒤의 단언은 데이터가 하나도
없어도 통과한다 — **초록이 「그 화면이 동작한다」를 말하지 않는다.**

**2026-08-16 실측** (`apps/web/e2e/` · spec 26개):

- `tr` 계열 로케이터 **9건**
- 그중 **헤더 행을 잡을 수 있는 것 5건** — 예:
  `authed-functional-parity.spec.ts:144` (`hasText: "대기"`) · `:150` (`"체결"`) · `:211` (`"전송"`)
- 안전 패턴 `getByRole('row')` 사용 **0건**

**권장 접근:** ⑴ `page.getByRole('row', { name: … })` 또는 `tbody tr` 로 범위를 좁힌다
⑵ ★**음성 대조가 이 항목의 핵심이다** — 표를 비운 상태에서 그 단언이 **red 인지** 확인해라.
지금 형태는 빈 표에서도 초록일 수 있고, 그것이 이 항목이 존재하는 이유다
⑶ 5건을 한 번에 고치지 말고 **음성 대조가 red 를 내는 것부터** 고친다 (판별력 없는 것을
먼저 고치면 무엇이 좋아졌는지 못 잰다)

**Risk:** 🟡 (수리 자체는 안전하나, 고친 뒤 **원래 잡아야 했던 결함이 드러날 수 있다**)

**상태:** ✅ **Resolved (2026-08-16 beta-cutover)** — `authed-functional-parity.spec.ts` 3곳(`:144`/`:150`/`:211`)을 `tbody tr` 로 옮기고 `authed-row-locator-guard.spec.ts` 신설. ★**원장의 「9건 중 5건 위험」은 지금 트리에서 3건**이고, 데이터를 채워 실측하니 **실제로 무증거였던 것은 1건**이다 — 헤더가 「체결가」·「체결 수량」을 갖고 있어 `hasText:"체결"` 만 충돌했다(`trCount=2`, first 가 헤더). 「대기」·「전송」은 `trCount=1` 로 잠재 위험이었다. ★★**원장이 처방한 음성 대조 「빈 표에서 red 인지 보라」가 틀렸다** — 주문 0건이면 이 화면은 표 대신 빈 상태 UI 를 그려 **헤더째 사라지고**, 위험한 패턴도 안전한 패턴도 똑같이 0 이라 두 단언이 판별력 없이 통과한다. 그 사실은 가드 초판이 앞에 둔 「표가 렌더됐는가」 전제 확인 한 줄이 잡았다. 대조는 **데이터가 있는 상태**에서 세운다
**트리거 판정:** 도래 — 감사가 끝났고 대상이 특정됐다. 다만 단독 착수보다 e2e 를 손대는 회차 동승이 싸다 (2026-08-16 deploy-activation)

---

### BL-767

**Title:** DB 백업이 **스케줄·오프서버 보관·복원 실증 셋 다 0건**이다 — self-host 를 고르면 그것이 유일한 안전망이다
**Category:** Ops / 백업 · 재해복구
**Priority:** P1
**Trigger:** ★**도래했다** — [ADR-033] 이 self-host TimescaleDB CE 를 확정한 순간 백업이 우리 책임이 됐다
**Est:** M
**출처:** 2026-08-15 G1 리포트 §6 · 2026-08-16 production-readiness 착수

**원인 / 영향:** 도구(`mise run db-snapshot`/`db-restore`, `Makefile:294-333`)는 **이미 있었다**. 없던 것은
셋이다 — ⑴ 스케줄 ⑵ 오프서버 보관 ⑶ **복원 실증**. 서버 DB 는 24MB 이고 덤프는 2.4MB 라 비용이
문제가 아니라 **아무도 안 걸어 뒀다**는 것이 문제다. 인스턴스·디스크 유실이 나면 소크 이력·전략·
백테스트가 통째로 사라진다.

★**복원을 한 번 실제로 해 보기 전에는 백업이 있다고 말하지 않는다.** 이 레포는 「있다고 여겨진
가드가 실제로는 그 경로를 안 지나던」 사례를 이미 겪었다([LESSON-087]·[LESSON-109]).

**넣은 것 (2026-08-16):** `tools/scripts/db-backup.sh`(`run` / `verify-restore` / `--install` /
`--uninstall` / `--status`) + 짝 하네스 `db-backup-test.sh` **39건**(skip 0). 게이트 등록까지 같은
회차에 했다 — `Makefile` 하네스 목록 11→**13종**(디스크 경보와 함께) · `final-gates.sh` `run_gate`.
★**지은 자리에서 바로 등록한다** — 「존재하고 초록인데 호출자가 0」인 고아 하네스가 생기는 경로가
정확히 「등록을 다음 회차로 미루는 것」이다([BL-601]·[BL-631]).

★**같은 호스트에서 검증된 절차를 이식했다** — 다른 앱(truewords)이 6시간마다 `pg_dump -Fc` →
`pg_restore --list` 무결성 → **OCI Object Storage(Instance Principal — 개인키 없음)** → 보관기간
정리를 돌리고 있었다(마지막 실행 11MB · 보관 60개 / 639M). 레포 grep 은 rclone/restic/boto3 전부
0건이라 「오프서버 자산 없음」으로 보였지만 **호스트에는 있었다**. 셸 OCI CLI 경로라 2026-08-06 의
`boto3` 제거 결정과도 충돌하지 않는다.

★★**핵심 안전 계약 — `run` 은 컨테이너를 기동/정지/재시작하지 않는다.** `docker exec` + `docker cp`
만 쓴다. `up`/`down`/`pin` 은 24시간 소크 창을 끊기 때문이다. 하네스가 docker 스텁으로 argv 를
전수 기록해 금지어를 검출하고, **그 검출기 자신의 양성·음성 대조**까지 둔다(로그가 비어서 통과하는
것을 막는다). 뮤테이션 **9/10 적발**.

★★**반증 — `timescaledb_pre_restore()` 가 이 스키마에서는 무효과다.** 착수 AC 가 「이것이 절차의
핵심」이라 못박았는데 실측은 유무가 **관측 가능한 차이를 하나도 만들지 않았다**: 양쪽 다
`pg_restore` rc=0 · stderr 0줄 · chunk 59 · 21,649행 · 복원본 INSERT 가 새 chunk 로 라우팅 ·
`drop_chunks()` 정상. 호출을 **지워도 하네스 39/39 초록**이다. [가정] hypertable 1개뿐이고
continuous aggregate·압축·정책이 0건이라 훅이 할 일이 없다 — [ADR-033] 실측표의 「고유 기능 사용처
0건」과 일치한다. ⇒ **호출은 유지한다**(공식 문서가 정본이고 비용 0). 단 두 파일 모두에
**「이 축은 무증거 — 테스트가 지킨다고 적지 마라」**를 명시했다.
★**버전은 여전히 진짜 제약이다** — 덤프와 복원의 확장 버전이 다르면 catalog version mismatch 로
죽는다. 로컬·서버가 같은 `timescale/timescaledb:2.14.2-pg15` 라 지금은 만족한다.

**설계 판단 3건:** ⑴ 사이드카 `<dump>.meta` — 「기대값과 불일치면 rc≠0」의 기대값 출처가 없었다.
살아 있는 DB 와 비교하면 drift 로 위양성이 나므로 덤프 **앞뒤로 두 번** 재서 `[min,max]` 구간으로
기록한다. 메타가 없으면 fail-open 하지 않고 **rc=2**. ⑵ **rc=3 = 로컬 정상 + 원격 업로드만 실패** —
「업로드 실패로 백업을 실패시키지 마라」와 「조용히 묻히면 안 된다」를 동시에 만족시키는 형태.
systemd 는 3 도 실패로 세므로 `OnFailure` 알람은 그대로 발화한다. `oci` 부재도 rc=3 이다(truewords
판은 조용히 넘어가는데, 그러면 「원격 사본 0」이 무기한 안 보인다). ⑶ `sudo docker` 를 박지 않는다 —
서버 `ubuntu` 는 이미 docker 그룹이고, sudo 가 필요한 곳은 `/opt/backups`(root:root) 파일 쪽이라
거기서 한 번만 판정한다. 박으면 sudo 가 PATH 를 재설정해 하네스 스텁이 안 걸린다.

★★**2026-08-16 실측 — 전용 버킷을 만들 수 없다.** 이 VM 의 Instance Principal 정책은
`manage objects` 는 주는데 **버킷 생성 권한이 없다**: `oci os bucket create quantbridge-backups`
가 **409 `BucketAlreadyExists`** 를 주는데 `oci os bucket get` 은 **404** 다 — 즉 **존재하지도
않는데 만들 수도 없다**(409 메시지가 「이미 있거나 권한이 없다」로 두 경우를 뭉갠다. `get` 으로
갈라야 한다). ⇒ 다른 앱의 `truewords-backups` 를 공유한다(put → list → delete probe 로 쓰기
가능 확인). 그때 우리 것의 경계가 **파일명 규칙에만** 의존하면 저쪽이 규칙을 바꾸는 순간 섞이므로
`QB_BACKUP_PREFIX` 를 신설했다(하네스 ⑪d 양성 · ⑪e 음성 · 변이 대조 red 확인 · 41 → **43건**).
운영 설정 = `QB_BACKUP_BUCKET=truewords-backups QB_BACKUP_PREFIX=quantbridge`.
★그 버킷의 **90일 lifecycle** 이 우리 객체에도 적용된다(로컬 보관 14일보다 길어 문제없다).
★전용 버킷이 생기면 `QB_BACKUP_PREFIX=` 를 비우면 된다 — 코드 변경 없이 갈린다.

**Risk:** 🟢 (읽기 + 파일 생성만. 컨테이너 무조작이 하네스로 강제된다)

★★**2026-08-16 서버 발효 — 검증 3종 전건 통과.** PR #643 머지 뒤 서버에 설치하고 1회 실행했다.

| 검증                     | 결과                                                                                                                                                                                |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ⑴ 덤프·메타 생성         | `/opt/backups/quantbridge-20260815T170040Z.dump` **2,315,852 B** + `.meta` 272 B · 대상 증명 ✓(`quantbridge-db`/`quantbridge`·2.14.2·:5433) · 테이블 19 · ohlcv 12,937행 · chunk 59 |
| ⑵ OCI 객체 존재          | `quantbridge/quantbridge-20260815T170040Z.dump`(2315852) + `.meta`(272) — **prefix 적용 확인**                                                                                      |
| ⑶ ★**소크 C2 전후 불변** | before **24.0007h** → after **24.0007h** · C1 1/3 유지 · C3 0 · C5 6/6. 누적만 24.0007→24.4040h 로 자랐다(창 2 정상 진행) ⇒ **백업이 창을 끊지 않는다는 것이 실측으로 증명됐다**    |

타이머 = `03,09,15,21:00`(다른 앱 백업 00/06/12/18 과 어긋나게) · `OnFailure` 알람 유닛 동반.
★`pg_dump` 가 `hypertable`·`chunk`·`continuous_agg` 에 대해 **circular FK 경고**를 낸다(TimescaleDB
내부 카탈로그). 복원 실증이 로컬에서 성공했으므로 실제 장애는 아니지만, 복원 절차를 바꿀 때
`--disable-triggers` 힌트를 다시 읽어라.

**상태:** ✅ **Resolved (2026-08-16 production-readiness)** — 스크립트·하네스 43건·게이트 등록·복원 실증·**서버 설치·오프서버 업로드·C2 불변 증명**까지 완료. 전용 버킷은 권한이 없어 공유 버킷 + `quantbridge/` prefix 로 간다(위 실측)
**트리거 판정:** 해소 — [ADR-033] 조건 ⑴ 이 서버에서 발효했다 (2026-08-16 production-readiness)

---

### BL-768

**Title:** 디스크 사용률을 **아무도 안 본다** — 디스크 풀이 Redis AOF 를 죽이고 celery 를 통째로 멈춘 전례가 있다
**Category:** Ops / 관측성
**Priority:** P2
**Trigger:** ★**도래했다** — [ADR-033] 조건 ⑵ · 그리고 [BL-767] 이 백업 파일로 디스크를 **쓰기 시작한다**
**Est:** S
**출처:** 2026-08-15 G1 리포트 §6 · 2026-08-16 production-readiness 착수

**원인 / 영향:** `df`·`shutil.disk_usage` 를 부르는 감시 코드가 레포 전체에 **0줄**이었다(2026-08-16
grep — 히트 4건은 전부 주석 문구). 2026-08-14T06:04:11Z 로컬 Docker VM 이 94% 에서 Redis AOF 쓰기에
실패했고 celery 가 `Unrecoverable error` 로 통째 정지했다([BL-736]).

★**그 사고는 로컬에서 났지만 서버도 구조가 같다** — 서버 `quantbridge-redis` 도 `appendonly=yes`
이고(2026-08-16 실측 `aof_enabled:1`) 소크 스택·백업 덤프·다른 앱 셋이 **디스크 한 벌**
(`/dev/sda1` 97G)을 공유한다. 서버에서 나면 24시간 창이 통째로 날아간다.
★**착수 전제 정정** — 프롬프트는 이 레인의 근거로 「94% 실사고」를 들었지만 그것은 **로컬 맥**이고
**서버는 40%(59G 여유)** 다. 근거는 「이미 위험하다」가 아니라 「쓰기 시작하는데 보는 눈이 없다」다.

**넣은 것 (2026-08-16):** `tools/scripts/lib/notify-telegram.sh`(`soak-watch.sh:105-142` `_notify()`
추출 — 선례 `lib/pre-push-ref-guard.sh`) + `tools/scripts/disk-guard.sh` + 하네스 `disk-guard-test.sh`
**19건**. `soak-watch.sh` 는 얇은 래퍼로 lib 에 위임하되 **`QB_SOAK_*` env 이름과 반환값을 그대로
유지**해 서버 유닛·기존 하네스가 무수정으로 돈다(회귀 확인: `soak-watch-test.sh` **25/25**, lib 를
숨기면 rc=1 — 음성 대조).

★**소크 감시와 분리했다** — soak-watch 에 얹으면 소크가 내려간 순간 디스크 감시도 사라진다.
타이머는 매시 **15분**(soak-watch 가 00·30분을 쓴다). `OnCalendar` 벽시계 고정 —
`OnUnitActiveSec` 은 마지막 활성화 기준이라 사람이 손으로 한 번 돌리면 위상이 밀린다([BL-737] 실측 53분).

★**알림을 먼저 쏘고 상태를 나중에 저장한다.** 디스크가 꽉 차면 상태 파일 쓰기부터 실패한다 —
저장이 앞서면 정작 알려야 할 그 순간에 알림 없이 죽는다. 하네스 ⑨ 가 그 순서를 잰다(전송 실패 시
`NOTIFIED_DATE` 미전진).

★**「늘 쏘는 경보」도 결함이다** — 사람이 무시하게 되어 결국 안 쏘는 것과 같아진다. OK 는 조용하고,
WARN 이 이어지면 **하루 1회만** 재고지한다. 하네스가 그 음성 대조 4건(①④⑦⑪)을 갖는다.
★`df` 판독 실패는 rc=1 이다 — fail-open 이면 「디스크는 괜찮다」로 읽힌다(하네스 ⑧).

★**하네스 자신이 위양성을 한 번 냈다** — `$$` 이스케이프 검사가 `$$TELEGRAM_BOT_TOKEN` 을 찾는데
실제 유닛은 `$${TELEGRAM_BOT_TOKEN}`(중괄호)이다. 정본 `soak-watch-test.sh:450` 은
`grep -qF 'bot$${TELEGRAM_BOT_TOKEN}'` 로 **고정 문자열 + 중괄호까지** 본다. 검사기를 정본에 맞췄다.

**Risk:** 🟢 (읽기 전용 판독 + 알림 1건)

★★**2026-08-16 서버 발효 — 양성·음성 대조를 실물로 돌렸다.**
설치 후 타이머가 매시 15분에 돈다(soak-watch 00/30 과 어긋나게 · `OnFailure` 알람 동반).
⑴ **양성** — `QB_DISK_WARN_PCT=1` 로 강제 발화: `--dry-run` 으로 본문을 먼저 확인한 뒤 실발화,
**rc=0**(= 텔레그램이 HTTP **200** 을 돌려줬다) · 상태 `LEVEL=WARN`.
★`%{http_code}` 를 직접 판정하므로 「유닛이 Finished」와 다르다 — 200 은 **도착**의 증거다.
⑵ **음성/회복** — 임계를 기본(80%)으로 되돌려 1회: **rc=0** · 상태 `LEVEL=OK` 로 전이하며
회복 알림 발화. ⇒ 「발화 조건은 상태값이 아니라 **전이**」가 실물에서 확인됐다.
⑶ `--status` = 사용률 40%(여유 58.6G) · **설치본 신선도 ✓**(ExecStart·알람 유닛 env 둘 다).

**상태:** ✅ **Resolved (2026-08-16 production-readiness)** — lib 추출·`disk-guard.sh`·하네스 19건·게이트 등록·soak-watch 회귀(25/25)·**서버 설치·양성 대조 발화(HTTP 200)·회복 전이·신선도 판정**까지 완료
**트리거 판정:** 해소 — [ADR-033] 조건 ⑵ 가 서버에서 발효했다 (2026-08-16 production-readiness)

---

### BL-770

**Title:** `alembic check` 가 rc=255 — 스키마 drift 검사가 설정 결함으로 죽어 있다
**Category:** Backend / migration
**Priority:** P1
**Trigger:** ★도래 — `models.py` 를 바꾸는 모든 회차가 이 검사에 의존한다
**Est:** S (env.py 2줄 + include_schemas 1줄 + 회귀 테스트)
**출처:** 2026-08-16 외부 레포 비교 분석(finsight) 지적 → 같은 날 코드·실행 대조로 확정

**원인 / 영향:** `alembic upgrade head` 는 성공하지만 `alembic check` 는 **rc=255** 다
(2026-08-16 로컬 개발 DB 실측). 원인이 실제 drift 가 아니라 **검사기 자신의 설정 결함** 둘이다:

- **⑴ 모델 import 누락 2종** — `alembic/env.py:23-28` 이 6개 도메인(`auth`·`backtest`·`market_data`·
  `strategy`·`stress_test`·`trading`)만 import 한다. `src/optimizer/models.py`·`src/waitlist/models.py`
  는 `table=True` 를 갖는데 빠져 있어, `SQLModel.metadata` 에 등록되지 않는다
  ⇒ 검사기가 `optimization_runs`·`waitlist_applications` 를 **「removed table」** 로 본다
- **⑵ `include_schemas` 미설정** — `env.py:135-148` 에 `include_schemas` 가 **0건**이다.
  `trading` 스키마의 테이블(`trading.exchange_exits`·`trading.live_signal_events`·
  `trading.live_signal_states`·`trading.funding_rates`·`trading.ohlcv` 등)이 DB 쪽에서 안 보여
  **「added table」** 로 잡힌다

⇒ 지금 `alembic check` 는 **참 drift 와 설정 잡음을 구분할 수 없다.** 검사기가 있으나 판별력이 0 이고,
그 사실이 [BL-749] — 타입·제약 drift 미검출 — 와 겹쳐 **migration 정합의 방어면이 이름만 남았다.**

★**착수 전 반드시 확인할 것** — 이 둘을 고치면 **진짜 drift 가 드러날 수 있다.** 그때 나오는 diff 를
「고쳐야 할 red」로 볼지 「검사기가 과하게 잡는 것」으로 볼지 판정 기준을 먼저 정해라. `compare_type=True`
는 이미 켜져 있다(`env.py:137,148`).

**권장 접근:** ⑴ import 2줄 추가 ⑵ `include_schemas=True` 를 두 `configure()` 에 ⑶ ★**음성 대조** —
모델에 컬럼 하나를 임시로 더해 `check` 가 **rc!=0 을 내는지** 확인해라. 지금은 늘 red 라 그 확인이
무의미하고, 고친 뒤에야 판별력을 잴 수 있다 ⑷ 초록이 된 뒤 CI 게이트로 승격을 검토

**Risk:** 🟡 (검사기를 살리면 잠자던 drift 가 CI 를 막을 수 있다 — 그것이 이 항목의 목적이다)

★**2026-08-17 auth-selfhost 에서 수리했다** — [ADR-034] 가 `auth_*` 5테이블을 metadata 에
선언하면서 이 검사기를 살려야만 했다(동승). 고친 것은 원장이 적은 그대로 둘이다:
`env.py` 에 `optimizer`·`waitlist` 모델 import 2줄 + 두 `configure()` 에 `include_schemas=True`.

★★**그리고 원장이 경고한 「잠자던 진짜 drift」가 실제로 하나 드러났다** — `ohlcv_time_idx`.
판정: **우리 것이 아니다.** `create_hypertable()` 이 자동 생성하는 시간 인덱스라 모델에 선언하면
`create_all` 경로(테스트 DB)에서 중복 생성이 되고, 지우면 hypertable 성능 근간이 사라진다.
⇒ `include_object` 필터로 제외했다(`_TIMESCALE_OWNED_INDEXES`). 그 밖의 drift 는 **0건**이었다.

★**음성 대조** — 고치기 전에는 `alembic check` 가 늘 red 라 판별력이 0 이었다. 수리 뒤
`upgrade head` → `check` **rc=0** 을 받았고, 같은 회차의 migration 을 쓰기 전에는 rc=255
(우리가 의도한 변경만 열거)를 받았다. 즉 이 검사기는 이제 **차이가 있을 때만** 운다.

**상태:** ✅ **Resolved (2026-08-17 auth-selfhost)** — `alembic check` rc=0. 원인 2종 수리 + 드러난 실 drift 1건 판정 완료
**트리거 판정:** 해소 — 검사기가 참 drift 와 설정 잡음을 구분한다 (2026-08-17 auth-selfhost)

---

### BL-772

**Title:** LLM 변환 502 가 내부 예외 타입·메시지를 응답 본문에 반사한다
**Category:** Backend / 보안 (정보 노출)
**Priority:** P2
**Trigger:** ★도래 — 1줄이고 단독 착수 가능
**Est:** S
**출처:** 2026-08-16 외부 레포 비교 분석(finsight) 지적 → 같은 날 코드 대조로 확정

**원인 / 영향:** `src/strategy/convert/router.py:32` —
`detail=f"LLM 변환 중 예외 발생: {type(exc).__name__}: {exc}"`.
외부 SDK(Anthropic·Gemini)의 예외 문자열이 **그대로 사용자 응답에 실린다.** SDK 예외 메시지는
엔드포인트 URL·모델명·요청 ID·때로는 요청 본문 일부를 담는다.

★**이것은 2026-08-15 surface-truth 의 「API secret 이 422 body 에 평문 반사」와 같은 계열**이다.
그 회차가 닫은 것은 422 축이었고, 이 502 축은 남아 있었다.

**권장 접근:** ⑴ 응답에는 고정 문구, 상세는 `logger.exception` 으로만 ⑵ ★상관 ID 를 응답에 넣고
로그에 같은 ID 를 남겨라 — 사용자가 문의할 때 추적 가능해야 무언가를 지운 대가가 상쇄된다
⑶ 음성 대조 = 예외를 강제로 일으켜 응답 본문에 예외 클래스명이 **없는지** 확인

**Risk:** 🟢

**상태:** ✅ **Resolved (2026-08-16 beta-cutover)** — ★**누출 표면이 원장의 1곳이 아니라 3곳이었다**: ⑴ `router.py` 502 detail(원장이 지목) ⑵ `router.py` 503 detail — `service.py` 3곳이 SDK 예외의 타입·본문을 **자기 RuntimeError 메시지에 f-string 으로 심고** 있었고 라우터가 `str(exc)` 를 그대로 실었다 ⑶ ★`service.py` 의 `fallback_warnings` — Anthropic→Gemini fallback 시 SDK 문자열이 `warnings[]` 로 **200 응답 본문**에 실렸다(실패 경로가 아니라 **성공 경로**라 훨씬 자주 노출). 셋 다 고정 문구 + 요청별 `error_id`(로그와 잇는 상관 ID)로 바꾸고 상세는 `logger.exception` 으로만. 변이 **3/3 red**(각기 다른 테스트가 잡았다)
**트리거 판정:** 해소 — 2026-08-16 beta-cutover 에서 종결

---

### BL-775

**Title:** `sprint46-tier3-nth #14`(단축키 도움말)가 **전체 authed 실행에서만** 비결정적으로 red
**Category:** Test / e2e 안정성
**Priority:** P3
**Trigger:** ★이미 발화 중이다 — `final-gates --deferred-only` 의 `e2e authed` 레그가 이것 하나로 red 가 된다
**Est:** S (원인 계측 → 예산 조정 또는 대기 조건 교체)
**출처:** 2026-08-17 auth-selfhost 마감 게이트

**원인 / 영향:** 전체 authed 실행 **5회 중 3회**에서 `#14 단축키 help dialog` 가
`getByRole('heading', { name: '키보드 단축키' })` 5초 예산을 넘겨 실패했다. 나머지 2회는 통과했고
(그중 1회는 `--deferred-only` 의 **86/86 PASS**), **단독 실행 1.2초 · 파일 전체 실행 14/14** 다.

★**auth-selfhost 회차의 변경 탓이 아니다** — `AccountButton` 에 Dialog 를 넣기 **전** 실행에서도
같은 케이스가 실패했고, Dialog 를 넣은 뒤 실행에서 통과한 적도 있다. 즉 상관이 없다.

★**같은 회차에 다른 spec 3개도 각 1회씩 red 였고 전부 타임아웃**이었다(`#1 Backtest form`
`waitForRequest` 15초 · `/backtests` 캐논 `waitForSelector` 25초 · `/strategies/:id/edit` 캐논).
공통점은 「값이 틀렸다」가 아니라 **「제 시간에 안 왔다」**이고, 실행 시간이 3.5~4분이며 그 맥의
load average 가 5.88(사용자 데스크톱 앱과 경합)이었다.

**권장 접근:** ⑴ ★**먼저 재라** — 조용한 머신에서 3회 연속 돌려 red 가 재현되는지 확인한다.
재현 안 되면 원인은 경합이고 이 항목은 「환경 조건 문서화」로 닫힌다 ⑵ 재현되면 `#14` 의 5초
예산이 이 스위트에서 **가장 짧다**는 점부터 본다 — 도움말 다이얼로그는 `?` dispatch → React
상태 → Base UI mount 3단이라 dev 서버가 바쁠 때 5초가 빠듯하다 ⑶ ★**예산만 늘리지 마라** —
그러면 진짜 회귀도 함께 못 잡는다. `expect.poll` 이나 명시적 mount 신호로 **대기 조건 자체**를
바꾸는 쪽이 낫다 ⑷ 부수로, 이 스위트는 `--workers=1` 인데 3.5분이 걸린다 — 병렬화 가능 여부도 같이 본다

**Risk:** 🟢 (테스트 안정성. 프로덕션 동작과 무관)

**관측 이력:** 2026-08-17 에 5회 실행으로 관측(3 red / 2 green). ★**2026-08-16 beta-cutover 에서 3회 더 관측(1 green 206s / 2 red 208s·202s) — 누적 3 green / 5 red.** ★★**실패 케이스가 회차마다 바뀐다** — red 1회차는 `#14 단축키`(5.9s, 예산 5s) **+** `#1 Backtest form`(16.0s) 둘이었고, red 2회차는 **`#1` 하나뿐이고 `#14` 는 통과**했다. **전부 타임아웃**이다. ⇒ 「`#14` 의 5초 예산이 짧다」보다 **머신 경합**을 훨씬 강하게 가리킨다 — 특정 케이스가 아니라 **그때 느린 것**이 진다. 원장의 권장 접근 ⑵(`#14` 예산부터 본다)는 이 관측으로 **우선순위가 내려간다.** ★**원장이 처방한 「조용한 머신 3회 연속」은 아직 못 했다** — 그 회차의 맥이 FE dev·API·ssh 를 동시에 돌리고 있어 조건 자체가 성립하지 않았다(관측을 늘렸을 뿐 판정은 그대로다). ★**CI 로는 못 가른다** — [ADR-034] 로 CI 인증 secret 이 0개가 되어 CI `e2e` 잡은 공개 레인만 돈다. 원인 미확정
★★**2026-08-16 layout-alignment — 원인이 확정됐다. 머신 경합이 아니라 하이드레이션 경쟁이다.**
격리 슬롯(FE :3100 · BE :8100)에서 이 케이스만 **결정적으로** red 였고, 탐침으로 기전을 분리했다.
테스트는 `/trading` 의 「트레이딩 코크핏」 제목이 보이자마자 `?` keydown 을 document 에 쏜다.
그런데 `ShortcutHelpDialog` 는 **`(dashboard)/layout.tsx` 서브트리**에 있고 그 `useEffect` 가
document 리스너를 붙이는 시점은 **페이지 제목 가시 시점과 다르다.** 실측(같은 mock·같은 경로):

| 대기                     | `[role=dialog]` | 제목 텍스트 | `shortcut-list` |
| ------------------------ | --------------- | ----------- | --------------- |
| 없음(실제 테스트와 동일) | false           | false       | false           |
| 3초                      | true            | true        | true            |

즉 예산 5초가 짧은 것이 아니라 **리스너가 아직 없을 때 이벤트를 쏘는 것**이다. 콘솔 오류 0,
`role="heading"`(H2) 정상 노출, 컴포넌트·`ui/dialog.tsx`·`(dashboard)/layout.tsx` 모두 그 회차에서
**diff 0**. ⇒ 「그때 느린 것이 진다」는 종전 해석은 증상이 맞고 원인이 아니었다.

**권장 접근(개정):** ⑴ 예산을 늘리지 마라 — 진짜 회귀도 같이 못 잡는다. ⑵ keydown 을 쏘기 전에
**리스너 부착을 기다려라** — 예: `ShortcutHelpDialog` 에 `data-shortcut-ready` 를 달고
`await expect(page.locator('[data-shortcut-ready]')).toBeAttached()` 로 동기화한다.
그러면 이 테스트가 재는 것이 「단축키가 동작하는가」로 좁혀지고 하이드레이션 타이밍과 분리된다.

**상태:** ✅ **Resolved** — 2026-08-16 layout-alignment. 원인 확정(하이드레이션 경쟁) 후 테스트 쪽만 고쳤다: 리스너가 붙을 때까지 `?` dispatch 를 `toPass` 로 재시도한다(예산은 안 늘렸다). **authed 90/90 전건 통과**(종전 89/90). ★변이 대조 — 핸들러를 무력화하면 red 이므로 판별력이 남아 있다. 프로덕션 코드 변경 0.
★★**잔여 관측 — 이것으로 authed 가 항상 초록이라고 읽지 마라.** 수리 후 전량 실행 **4회 중 3회 green** (단독 2회 · 게이트 2회 중 1회). red 였던 1회는 **어느 케이스인지 못 봤다** — 그 회차 명령이 출력을 `| tail` 로 잘랐고 뒤이은 통과 실행이 `test-results/` 아티팩트를 지웠다. #14 의 기전은 변이 대조로 닫혔으므로 이 항목은 Resolved 지만, 원장의 종전 관측(「실패 케이스가 회차마다 바뀐다」 — `#1 Backtest form` 타임아웃 전례)이 가리키던 **다른 케이스의 잔여 경합은 열려 있다.** 재발하면 **출력을 자르지 말고** 케이스 이름부터 잡아라.
**트리거 판정:** 도래 — 마감 게이트의 authed 레그가 이것 때문에 red 다. 다만 프로덕션 영향이 0이라 P3 (2026-08-17 auth-selfhost · 2026-08-16 원인 확정)

---

### BL-788

**Title:** `tests/conftest.py` 의 `create_all` 스키마 범위가 **import 목록으로만** 정의된다 — 빠진 모델은 조용히 안 만들어지고 head 로 stamp 된다
**Category:** 테스트 / 인프라
**Priority:** P2
**Trigger:** 도래 — 2026-08-17 에 `auth_*` 5테이블이 실제로 빠져 있었다
**Est:** S (등록 테이블 수를 재는 검사면 1개)
**출처:** 2026-08-17 야간 레인 β — 두 BL 어느 쪽도 아니라 레인이 별건으로 넘겼고 CONTROL 이 등재

**원인 / 영향:** `bootstrap_test_schema` 는 `SQLModel.metadata.create_all` 로 스키마를 만든 뒤 `alembic_version` 을 **생 SQL 로** head stamp 한다. `create_all` 이 만드는 것은 **그 순간 metadata 에 등록된** 테이블뿐이므로, 파일 머리의 모델 import 목록이 곧 스키마 범위다. `src/auth/better_auth_tables.py` 를 import 하는 곳이 `alembic/env.py` **하나뿐**이라 fresh DB 에는 `auth_*` 5테이블이 **없는 채로 head 가 적혔고**, `test_migrations.py` 의 `downgrade base` 가 `DROP TABLE auth_jwks` 에서 죽었다. 이전에 migration 이 돈 DB 에는 그 테이블이 남아 있어 통과한다.

★**이것이 원장의 기준선을 오염시켰다** — 「BE 4759 passed」는 거짓이 아니라 **더러운 DB 에서 잰 값**이었다. fresh DB 에서는 `2 failed, 4757 passed` 이고, 이 회차의 migration 을 뺀 대조군에서도 같은 2건이 같은 이유로 실패했다.

★★**표적 실행으로는 구조적으로 안 보인다.** CONTROL 이 그 import 를 지우고 fresh DB 에서 `test_migrations.py` **단독**을 돌렸더니 **20 passed rc=0** 이었다. 전량 실행에서만 red 가 된다(수집 단계에서 다른 모듈이 `auth` 쪽을 import 하는지로 갈린다). 즉 이 결함군은 **전량 pytest 만이 증인**이다.

**처방:** import 한 줄은 [BL-785] 회차가 이미 넣었다(수리 완료). 남은 것은 **재발 방지**다 — 「`SQLModel.metadata` 에 등록된 테이블 수 == 기대치」를 재는 검사면이 없어서, 다음에 모델 파일이 추가되고 conftest import 가 빠지면 같은 일이 반복된다. [BL-782] 와 같은 병의 다른 층이라는 것도 함께 적어라(`create_all` 경로 ≠ migration 경로 — 저기는 컬럼 타입, 여기는 테이블 존재).

**Risk:** 🟢 (검사면 추가. 프로덕션 코드 무변경)

**상태:** ✅ **Resolved** — 2026-08-17 metadata-scope (PR #662). 신규 `apps/api/tests/test_metadata_table_coverage.py` **4다리** — 선언 축 2(`tests/conftest.py`·`alembic/env.py` 가 census 의 표 선언 모듈을 **모듈 최상위에서** import 하는가) + 실행 축 2(자식에서 `tests.conftest` 만 import 했을 때 등록 표 == census / `alembic/env.py` 를 오프라인으로 태워 `configure()` 가 받은 `target_metadata` 를 대조). 기대치는 `src/**` AST census 에서 도출하므로 **하드코딩이 없다**. 착수 시 red(`{'src.optimizer.models': ['optimization_runs']}`) → 수리 후 green 실측. 변이 12종+ · 전량 BE pytest **4782 passed, 0 failed**(기존 슬롯 DB · fresh DB 각 1회).
★**본문이 적은 인과가 거짓이었다.** 「`tests/optimizer/` 9파일이 **수집 단계에서 우연히 import** 하므로 수집 순서 의존」이 아니라 `tests/conftest.py:70` → `src/main.py:447 create_app()` → stress_test router → dependencies → service → `src.optimizer.models` 의 **5홉 전이 import** 이고 수집과 무관하다. 결함은 「깨져 있었다」가 아니라 **「무관한 배선에 기대고 있었다」**였다 → [LESSON-120].
★**기준선도 정정한다.** 위 「fresh DB 에서 `2 failed, 4757 passed`」는 슬롯 3 에서 재현되지 않는다 — 그 2건의 원인이던 `better_auth_tables` 누락을 [BL-785] 회차가 이미 넣었기 때문이다. 실측 2회 모두 0 failed.
★**동승 정리 — 범위 목록이 3벌 → 2벌.** `tests/test_migrations.py:36-49` 의 「누락 방지용 explicit import」를 삭제했다(2026-04-16 도입, stress_test·waitlist·optimizer·better_auth_tables **4개 누락 상태로 넉 달 생존**. 부모 conftest 가 전부 등록하므로 기여 0 이었고, 이름이 주장하는 성질을 스스로 못 지켜 오히려 누락을 가렸다).
★★**이 회차가 자신에 대해 반증한 것 2건 — 둘 다 「주석이 코드보다 앞서 나갔다」다.** ⑴ 「파서가 못 보는 선언 형태는 실행 축이 정체불명으로 잡는다」 → 실행 축은 **import 된 모듈만** 본다. ⑵ 「`alembic check` 가 보는 것과 같은 객체다」 → 오프라인/온라인은 **다른 `configure()` 호출**이다(codex 수리 뒤 독립 검증자가 온라인 쪽만 비워 4/4 초록을 냈다). 최종판은 주장을 **「`configure()` 들이 같은 모듈 전역 이름을 넘기는 것을 AST 로 정적 확인했고, 그 이름이 가리키는 값을 오프라인 실행으로 실측했다」**로 낮췄다. 알면서 남긴 census 사각 3종 = [BL-796].
**트리거 판정:** 도래 — 결함이 실재했고 기준선을 오염시킨 것이 실측됐다

---

### BL-795

**Title:** 「authed 스위트 red」의 **두 번째 원인** — Turbopack 영속 캐시 물림. [BL-784] 와 증상이 같다
**Category:** 테스트 / 개발 환경
**Priority:** P3
**Trigger:** 도래 — 2026-08-17 회차에서 실제로 3/3 red 를 냈다
**Est:** S (판정식을 문서에 한 줄)
**출처:** 2026-08-17 야간 레인 α — 회차 중 밟은 환경 함정

**원인 / 영향:** authed 가 3/3 red 로 나온 구간이 있었고 원인은 rate limit 이 아니라 Turbopack 영속 캐시였다. 증상은 `○ Compiling /sign-in/[[...sign-in]] ...` 에서 next-server 가 **CPU 0.0%** 로 멈추고 `global.setup.ts:65` 의 `page.goto('/sign-in')` 이 120초 timeout 으로 죽는 것이다(그 뒤 89건 `did not run`). `curl /sign-in` 은 240초를 넘겨도 응답이 없었다. `apps/web/.next` 를 치우고 재기동하면 `/sign-in` 이 **0.79초**에 컴파일된다.

★**같은 증상에 원인이 둘이라는 것이 [BL-784] 가 넉 달을 끈 이유와 같은 모양이다.** 구분하는 판정식: **실패가 `setup` 단계에서 나고 BE 429 가 0건**이면 캐시 쪽이다(429 가 있으면 [BL-784] 축).

**처방:** 그 판정식을 `gates-and-traps.md` §환경 또는 `docs/lessons.md` 에 한 줄. [BL-650] 이 이미 같은 캐시가 낡은 CSS 로 음성 대조를 거짓 통과시킨 전례를 갖고 있다 — 그 항목과 나란히 두면 「Turbopack 캐시는 서버 재기동을 넘어 산다」가 한자리에 모인다.

**Risk:** 🟢 (문서)

**상태:** ✅ **Resolved** — 2026-08-17 e2e-truth (PR #663). `gates-and-traps.md` 의 429 축([BL-784]) 바로 다음에 **2원인 대조표**를 넣었다 — 실패가 `setup` 단계에서 나고 429 가 **0건**이면 캐시 쪽, 처방은 `rm -rf apps/web/.next`. 종전 「★복구 = 재기동뿐 … 지우지 말고 재기동해라」를 폐기하고 「재기동 먼저, 남으면 서버를 죽인 뒤 캐시 제거」로 통합했다.
★★**「모순 문장이 남아 있지 않다」는 수용 기준을 이 회차가 두 번 틀렸다.** 잔존 확인을 `gates-and-traps.md` **한 파일**에서만 돌린 것이 원인이다. ⑴ 3렌즈 적대 리뷰가 `docs/reference/operations/workflows/generator-evaluator-pipeline.md:142`(하필 `AGENTS.md` 가 메타-방법론 정본으로 지목한 파일의 §G4) 에서 같은 처방이 살아 있는 것을 찾았다. ⑵ `/codex` 가 [BL-650] 본문의 「dev 가 이상하면 `rm -rf .next` 부터가 유일한 처방」을 찾았다(이 원장 PR 이 정정). ⇒ **잔존 확인은 처음부터 `git grep -- docs/` 전체여야 했다.** 지금은 `git grep "재기동뿐" -- docs/` 의 히트가 **전부 폐기 선언 안의 인용**이다.
★**정직한 한계** — 이 항목의 산출물은 전부 산문이라 판정식의 참·거짓을 잴 검사면이 **구조적으로 없다**. 수용 기준을 「판정식이 맞다」가 아니라 「두 원인이 한자리에서 대조되고 모순되는 종전 문장이 남아 있지 않다」로 두고 닫았다. 판정식 자체의 실증은 **다음 authed red 회차**에 달려 있다.
**트리거 판정:** 도래 — 이 회차가 실제로 밟았고 원인을 특정했다

---

## ★2026-08-18 backlog-triage 이관 — `backlog.md` 에 남아 있던 RESOLVED 13건

> ★**분할이 절반만 돼 있었다.** [BL-779] 가 RESOLVED 118건을 내렸는데 그 뒤 회차들이 닫은
> 항목은 `backlog.md` 에 그대로 쌓였다 — 규칙이 산문이라 아무도 집행하지 않았다.
> 2026-08-18 에 남은 13건을 내리고 **집행처를 `bl-audit.sh` 에 만들었다.**

### BL-414

**Title:** 스트레스 테스트 이력 리스트 UI — `GET /stress-tests` 목록 API 기존재하나 프로토타입 17벌에 이력 화면 부재로 defer (A7-lite 로 최신 1건 복원만 해소)
**Category:** Frontend / backtest 리포트
**Priority:** P3
**Trigger:** 스트레스 이력 화면이 디자인 캐논에 추가될 때
**Est:** S-M (3-5h)
**상태:** ✅ **Resolved (2026-08-17 night3 레인 γ)** — `stressTestKeys.byBacktest` 캐시가 `StressTestListResponse` 를 담고(`useStressTestHistory`), `stress-test-history-table.tsx` 가 종류·상태·대표 지표·실행 시각을 표로 그리며 행 선택이 상세를 갈아끼운다. BE 는 `StressTestSummary.headline_metric` 한 필드만 늘었다(MC `max_drawdown_p95` · WFA `degradation_ratio` · CA/PS 최저 sharpe — 저장된 result 에서 읽고 새로 계산하지 않는다). 진행 중 행이 있을 때만 2초 폴링. 변이 3/3 red + CONTROL 변이 1건(기본 선택=최신) red.
**트리거 판정:** — (Resolved)
**출처:** 2026-07-23 functional-parity 스프린트 defer 판정

**원인 / 영향:** 리로드 소실(기능 격차의 본질)은 A7-lite 가 해소. 과거 실행 브라우징만 미지원이었다.

**권장 접근(이행됨):** 이력 리스트 도입 시 `stressTestKeys.byBacktest` 캐시를 단일 Summary 에서 페이지 응답으로 재정의해야 함 (A7-lite 구현 노트). ★**원장의 「페이지 응답」은 BE 엔드포인트가 아니라 FE React Query 캐시를 가리켰다** — 레인 파일이 그것을 BE 축으로 오독했고 코드 대조가 바로잡았다. 처방 자체는 옳았다.

**남은 것:** 1페이지 상한 20건은 유지하되 넘으면 화면이 고지한다([BL-798] 이 전송 비용 축을 잇는다). authed 캐논(`/backtests/[id]`)은 슬롯 배선이 [BL-780]/[BL-781] 소유라 이 회차에서 못 돌렸다.

---

### BL-427

**Title:** 전략 목록 파라미터 열 / 수명주기 칩(초안·검증·배포) 미렌더 — 백엔드 스키마 부재
**Category:** Frontend / backend schema
**Priority:** P3
**Trigger:** 전략 파라미터/수명주기 UI 요구 시
**Est:** M (4-8h, BE 스키마 + FE)
**상태:** ✅ **Resolved — 원장이 낡았고, 「낡았다」고 알려준 문서도 한 칸 낡았다 (2026-08-17 night3 CONTROL 코드 대조)** — BE `strategy/schemas.py:193-194` 에 `param_count`·`lifecycle` 이 있고 **FE 도 이미 렌더한다**: `strategy-list.tsx:449` 가 파라미터 열(`<td className="num">{s.param_count ?? EMPTY_CELL}</td>`), `:417`·`:423` 이 수명주기 칩(`STRATEGY_LIFECYCLE_LABEL` + `data-lifecycle`), `:554` 가 카드 뷰 라벨이다. 파일 헤더 주석(`:4`)이 「서버가 내려주는 파라미터 수·수명주기 칩을 함께 표시한다」라 적고 있고, 상태줄이 주장한 **「FE 미렌더 사유 주석」은 strategy 도메인에 0건**이다. `strategy-list.test.tsx:119`·`:331-333` 이 lifecycle 칩 3종을 단언한다. ★이 회차의 야간 오케스트레이터 문서는 이 항목을 「BE 필드 존재, **FE 렌더만 남았다**」로 적었는데 그것도 사실과 달랐다 — 원장 정정 문서가 같은 방향으로 한 번 더 낡아 있었다.
**트리거 판정:** — (Resolved)
**출처:** 2026-07-24 perf-surface (캐논 프로토타입엔 존재하나 StrategyListItem 스키마에 파라미터·lifecycle 필드 없음 → §4.9 미렌더 유지)

**원인 / 영향:** 캐논 screen 은 전략별 파라미터 요약 + 수명주기 칩을 그리나, `StrategyListItem` 에 해당 필드가 없어 perf-surface 는 성과 3칸만 노출하고 파라미터/칩은 의도적으로 미렌더. 데이터 모델 확장 전까지 표면 불가.

**권장 접근:** Strategy 파라미터 요약 + lifecycle 상태를 list 응답에 파생/영속 후 FE 칩 렌더. 스키마 우선.

---

### BL-429

**Title:** 대시보드 §03 최적화 완료행 수익률/MDD 역산 미표시(`—` 고정)
**Category:** Frontend / backend
**Priority:** P3
**Trigger:** 대시보드에서 최적화 best 성과를 목록 단계에서 보고 싶을 때
**Est:** S-M (best_params 대응 backtest metric 역산 또는 denormalize)
**상태:** ✅ **Resolved (2026-08-17 night3 레인 β)** — §03 최적화 행이 백테스트 행과 **같은 열·같은 의미**의 숫자(수익률·MDD)를 그린다. 값 없는 실행은 여전히 빈칸이고 **0 이 아니다**. 갈래 ⒜(best 백테스트 metric denormalize) 채택 — ⒝(objective_value)는 run 마다 단위가 갈려 한 열에 두 컨벤션이 섞이고, `/optimizer` 목록이 이미 ⒝ 를 열 제목까지 갖춰 구현하고 있다. `models.py` 무변경이라 **alembic migration 없다**. 변이 3/3 red + CONTROL 변이 1건(열 구분) red.
**트리거 판정:** — (Resolved)
**출처:** 2026-07-24 perf-surface A3 (§03 병합에서 최적화 행은 수익률/MDD 를 `—`+"결과는 최적화 상세에서 확인" 으로 고정. best 지표 역산은 후속)

**원인 / 영향:** ~~OptimizationRun 은 param_space/result(iterations) 만 보유, best 조합의 백테스트 metric 은 목록에 없어~~ → **2026-08-17 반증**: grid_search 는 `result` JSONB 의 `cells[]` 가 cell 마다 `total_return`·`max_drawdown` 을 갖고 `best_cell_index` 도 있으며 목록 응답이 `result` 를 **통째로** 싣는다. 즉 그 숫자는 **이미 클라이언트에 도착해 있었고** 없던 것은 꺼내는 이름이었다. 진짜로 metric 이 없던 것은 bayesian·genetic 둘이다(`objective_value` 만 보관하고 `outcome.result.metrics` 를 계산 후 버렸다). 이 차이가 설계의 절반을 정했다 — grid 는 엔진 변경 0, 나머지 둘만 best 하나를 붙잡게 했다.

**권장 접근(이행됨):** result 의 best_params → 대응 backtest metric 매핑을 denormalize. 「재계산 시점 문제」는 **DB 컬럼이 아니라 응답 파생**으로 두어 없앴다(쓰기 경로가 안 늘고 원본과 어긋날 수 없다).

**후속:** 목록 응답이 `result` 를 통째로 싣는 전송 비용은 [BL-799] 로 분리했다.

---

### BL-430

**Title:** 전략 목록 성과 정렬(수익률/샤프) SORT_OPTIONS 미제공
**Category:** Frontend
**Priority:** P3
**Trigger:** 전략을 최근 성과 순으로 정렬하고 싶을 때
**Est:** S (2-3h; BE latest_backtest 정렬 축 + FE SORT_OPTIONS 확장)
**상태:** ✅ **Resolved — 원장이 낡았다 (2026-08-17 night3 CONTROL 코드 대조)** — 상태줄이 적은 세 가지가 **전부 거짓**이었다: ⑴ `features/strategy/sort.ts:7` `STRATEGY_SORT_OPTIONS` 는 4옵션이고 `total_return`(「수익률 높은 순」)·`sharpe_ratio`(「샤프 높은 순」)를 포함한다 ⑵ 정렬은 클라 로컬이 아니라 URL 파라미터를 통한 **서버 정렬**이다(`router.replace` 로 `order_by`/`order` 세팅) ⑶ BE `strategy/router.py:76` 에 `order_by: Literal["updated_at","name","total_return","sharpe_ratio"]` 가 있다. `sort.test.ts` 도 존재한다. **구현 시점은 [BL-710] 이 2026-08-12 에 「셋 다 BL-430/BL-427 구현이 만든 것」이라 적은 것에서 역산된다** — 즉 08-09 판정 이후 08-12 이전이고, 그 3일치 역행을 아무도 안 봤다.
**트리거 판정:** — (Resolved)
**출처:** 2026-07-24 perf-surface A2 stretch 미실행 (SORT_OPTIONS 는 recent/name 만; 성과 3칸은 표기만, 정렬 축 부재)

**원인 / 영향:** 성과 열은 노출됐으나 전략 목록은 마지막수정/이름 정렬만 지원. latest_backtest 성과 기준 정렬 부재로 우열 비교가 목록 단계에서 제한적.

**권장 접근:** `latest_completed_by_strategy_ids` 결과를 정렬 축으로 노출(서버 정렬) + FE SORT_OPTIONS 에 수익률/샤프 추가. 클라 정렬은 페이지 한정이라 지양.

---

### BL-602

**Priority:** P3
**카테고리:** DX / 커밋 훅 (prettier 플러그인 해석)
**Trigger:** `apps/web/` 안의 `*.json` / `*.md` / `*.yml` 을 커밋해야 할 때
**Est:** S
**상태:** ✅ **Resolved (2026-08-17 야간 통합).** ★**대상이 이미 사라져 있었다 — 아무도 몰랐다.** 처방(루트 devDependencies 에 `prettier-plugin-tailwindcss`)이 `71f7101e`(2026-08-09) — **이 BL 과 무관한 목적의 커밋** — 에 얹혀 들어갔고, 그 뒤 8일간 원장은 계속 「대기」였다. 레인 γ 의 DEFERRED 178건 재판정이 잡아냈다(그 회차의 ① 판정 **유일한 1건**). ★★**메시지로는 판별이 안 된다** — prettier 는 **ignore 된 파일에도** 「All matched files use Prettier code style!」 + rc=0 을 낸다. 그래서 γ 는 플러그인을 **실제로 떼어** 원문 오류가 문자 그대로 재현되는 것을 확인했고, 통합 회차는 `.prettierignore` 회피 3줄을 **지운 뒤에** 다시 쟀다 — 그러자 `apps/web/AGENTS.md`·`README.md` 가 **rc=1**(그동안 한 번도 포맷된 적 없다), `CLAUDE.md` 는 rc=0. 음성 대조로 `contracts/openapi`(여전히 ignore)가 rc=0 임을 확인해 판별력을 증명했다. 두 파일은 `prettier --write` 로 정렬했다(표 정렬만, 33+/32-). **이연 부채 2건 처리** — ① `apps/web/README.md` 의 구 `.ai/rules/frontend.md` 참조는 **이미 없다**(grep 0건, 앞선 회차가 지웠다) ② `apps/web/AGENTS.md` 의 「미등재 경계 900px 5곳은 [BL-646]」은 [BL-646] 이 Resolved 라 거짓이었다 → `DESIGN.md §4.3.1` 등재 사실 + 실사용 5곳(`globals.css:1972·2042·2175·2271·3300`)으로 정정했다.
**트리거 판정:** 도래 — 처방이 이미 이행돼 있었다 (2026-08-17 재판정)

**루트 prettier 가 `apps/web/` 안의 json/md/yml 을 포맷하지 못한다.**

**실측 재현 (2026-08-06):**

```
$ ./node_modules/.bin/prettier --check apps/web/package.json
[error] Cannot find package 'prettier-plugin-tailwindcss' imported from .../quant-bridge/noop.js

$ ./node_modules/.bin/prettier --check docs/reference/operations/gates-and-traps.md
All matched files use Prettier code style!     ← 루트 밖 파일은 정상
```

**뿌리.** `apps/web/.prettierrc` 가 `"plugins": ["prettier-plugin-tailwindcss"]` 를 선언한다.
루트 `package.json` 의 lint-staged 는 `*.{json,md,yml,yaml}` 을 **레포 전역**으로 잡아 **루트**
prettier 로 돌리는데, 루트 `node_modules` 는 husky/lint-staged/prettier **3개뿐**이라(설계상
루트는 도구 전용) 그 플러그인을 해석하지 못한다. prettier 3.x 가 플러그인을 **CWD 기준**으로
찾기 때문에 `apps/web/node_modules` 에 있어도 못 본다.

**증상.** `apps/web/package.json` 을 포함해 커밋하면 pre-commit 이 `prettier --write` 에서
죽고, 같은 실행에서 eslint 가 `KILLED` 로 함께 넘어져 원인이 가려진다. 이번 회차에는
`package.json` 에 `e2e:ci` 스크립트를 넣으려다 막혀 **ci.yml 인라인으로 우회**했다.

★**과거에 통과한 이력이 있다**(`apps/web/package.json` 을 담은 커밋 4건). 그래서 「원래 안 되던
것」이 아니라 **어느 시점에 깨진 것**이다 — prettier/pnpm 버전이나 hoisting 변화가 후보다.
고치기 전에 **언제부터 깨졌는지 먼저 확인해라**(그 4 커밋 시점의 prettier 버전 대조).

**처리 방향(택1, 조사 후 결정):** ① 루트 devDependencies 에 `prettier-plugin-tailwindcss` 추가
② lint-staged 의 `*.{json,md,yml,yaml}` 글로브에서 `apps/web/**` 를 빼고 frontend 전용 항목을 신설
③ `apps/web/.prettierrc` 의 plugins 를 해석 가능한 절대/상대 경로로.
★**`--no-verify` 는 답이 아니다**(레포 규약 금지).

**Risk:** 🟢 DX 문제이고 프로덕션 무관. 다만 **막히면 커밋 자체가 안 된다.**

**★이연 부채 목록 — 본 BL 이 닫히면 함께 고친다.**

1. (2026-08-06 docs-overhaul) `apps/web/README.md:39` 의 구 `.ai/rules/frontend.md` 참조 →
   `apps/web/AGENTS.md` 로 갱신.
2. (2026-08-08 zero-touch-bundle) `apps/web/AGENTS.md:271` 의 「미등재 경계
   `@media (max-width: 900px)` 5곳은 [BL-646]」이 **이제 거짓이다** — [BL-646] 은 Resolved 이고
   `DESIGN.md §4.3.1` 이 900 을 **콘텐츠 그리드 전용 6번째 경계로 등재**했다. 같은 §10 사다리
   표에 900 행도 필요하다([BL-646] 본문이 이미 지목).
   ★**[확인 필요] 이 항목은 지금도 고칠 수 있을지 모른다** — `.prettierignore:12` 에
   `apps/web/AGENTS.md` 가 들어 있어 루트 prettier 가 건너뛴다(2026-08-08 실측:
   `prettier --check apps/web/AGENTS.md` **exit 0**, 대조군 `apps/web/package.json` exit 1).
   즉 이 파일에 한해 pre-commit 사망 조건이 성립하지 않는다. 이연한 이유는 트랩이 아니라
   **회차 제약**(zero-touch-bundle 은 `apps/web/` md 무접촉으로 착수했다)이다. 다음 회차가
   이 두 줄 중 어느 쪽이 맞는지 커밋 한 번으로 확정해라.

**출처:** 2026-08-06 e2e-consolidation (커밋 시도 중 실측 재현)

---

### BL-773

**Title:** 백테스트·옵티마이저가 실행 시점의 **mutable** Pine 을 다시 읽는다 — 결과가 무엇을 검증했는지 알 수 없다
**Category:** Backend / 재현성 (strategy · backtest · optimizer)
**Priority:** P1
**Trigger:** ★백테스트 결과를 승격 근거로 쓰기 전 · 또는 다중 사용자/공유 링크가 신뢰 대상이 될 때
**Est:** L (불변 버전 테이블 + migration + 3경로 배선 + 기존 행 백필)
**출처:** 2026-08-16 외부 레포 비교 분석(finsight) 지적 → 같은 날 코드 대조로 3경로 전부 확정

**원인 / 영향:** `Backtest` 행은 **무엇을 실행했는지 기록하지 않는다.** `backtest/models.py:41-144`
가 저장하는 것은 `strategy_id`·symbol·timeframe·기간·capital·config 뿐이고, 실행 당시의
**pine_source · source hash · parser/engine version · 데이터 snapshot** 은 **한 건도 없다**
(`grep -rn "strategy_version\|source_hash\|dataset_snapshot" apps/api/src` = **0건**, 2026-08-16 실측).

**세 경로가 전부 실행 시점에 현재 Strategy 를 다시 읽는다:**

| 경로        | 위치                                | 무엇을 읽나                                                  |
| ----------- | ----------------------------------- | ------------------------------------------------------------ |
| 제출 검증   | `backtest/service.py:168`           | `analyze_coverage(strategy.pine_source)` — 제출 시점         |
| worker 실행 | `backtest/service.py:284` → `:348`  | `find_by_id_and_owner(...)` 재조회 후 `strategy.pine_source` |
| optimizer   | `optimizer/service.py:236` → `:249` | 부모 백테스트가 아니라 **현재** Strategy 의 Pine             |

그리고 `strategy/service.py:371` — `strategy.pine_source = data.pine_source` 는 **기존 백테스트
존재 여부와 무관하게** 덮어쓴다.

⇒ 실현 가능한 시나리오 둘:
⑴ Pine A 로 제출 → 큐 대기 중 Pine B 로 수정 → worker 가 **B 를 실행**하고 결과를 **A 를 검증하고
제출한 백테스트 행**에 저장한다 ⑵ Pine A 백테스트 완료 → Strategy 를 B 로 수정 → 그 백테스트에서
Optimizer 실행 → **B 를 최적화**한다.

★**긴급도에 대한 정직한 판정** — 실자금 Live 는 [ADR-032] 로 2026-08-14 에 **이미 기각**됐고 현재
경계는 Bybit demo 다. 따라서 이 결함이 지금 **돈을 잃히지는 않는다.** 그러나 ⑴ 공유 링크
([BL-397]/[BL-551] 로 이미 존재)가 남에게 보이는 숫자이고 ⑵ Trust Layer 가 보장하는 것은
「인터프리터가 TradingView 와 같은가」이지 **「이 결과가 어느 소스에서 나왔는가」가 아니다.**
재현성은 Trust Layer 의 사각지대다.

**권장 접근:** ⑴ 불변 `StrategyVersion`(pine_source · source_hash · parser_version · created_at) 신설,
`Strategy` 는 최신 버전을 가리킨다 ⑵ `Backtest` 에 `strategy_version_id` + `engine_version` 추가,
worker 는 **버전을 읽고 Strategy 를 읽지 않는다** ⑶ optimizer 는 부모 백테스트의 버전을 상속
⑷ ★**데이터 snapshot 은 2단계로 미뤄라** — OHLCV 해시는 TimescaleDB 재적재 정책과 얽혀 있어
이 항목의 L 을 XL 로 만든다. 소스 재현성부터 닫는다 ⑸ ★**음성 대조** — 「제출 후 Pine 을 바꾸고
실행」 테스트를 먼저 red 로 세워라. 지금 그 테스트는 **없다**

★**migration 이 필요하다** — 2026-08-15 사용자 결정에 따라 파일 생성·로컬/CI 적용은 허용이고
**서버 소크 DB 적용만 명시 승인**이다. 소크 창을 보고 착수 시점을 정해라.

**Risk:** 🟠 (백테스트 실행 경로의 핵심을 바꾼다 — 소크가 도는 동안은 착수 시점을 골라야 한다)

**상태:** ✅ **Resolved (2026-08-17, PR #650 머지 `eeff8898`).** 불변 `StrategyVersion` 스냅샷 + 최신 버전 포인터 + `Backtest.strategy_version_id`·`engine_version` + 백필 migration. Backtest worker·coverage 와 Optimizer 가 **부모 Backtest 의 스냅샷** 을 쓴다. 게이트 2단 rc=0(BE **4753** · e2e authed 90 · fresh DB alembic) · 유예 원장 소멸. ★★**CONTROL 표적 변이 5/5 red.** ★그중 **M5(`set_current_version` no-op)는 원장 처방에 없던 변이**인데 최초에 **1154 passed 로 초록 누출**이었다 — 「Strategy 는 최신 버전을 가리킨다」에 커버리지 0 이고 포인터가 죽으면 제출마다 버전 행이 폭증한다. 테스트 신설 후 재삽입해 red 확인. ★실데이터 대조 — 백테스트 7행 전부 pin(NULL 0) · 브라우저 생성 시 `strategy_versions` 3→4 + `source_hash` 재계산 일치. ★★**표적 초록 + 변이 5/5 를 통과한 구현에 전량 회귀 5건**(낡은 mock) — 2단 게이트가 잡았다([LESSON-116]). **잔여 분리** — [BL-782] alembic drift · **[BL-783] P1** Stress Test · [BL-784] e2e 비결정
**트리거 판정:** 도래 — 대상이 특정됐고 단독 착수 가능하다. 다만 L 이고 migration 이 붙으므로 소크 창과 조율한다 (2026-08-16 external-comparison)

---

### BL-780

**Title:** `final-gates-test.sh` 케이스 ⑩ 의 음성 대조가 **브랜치 내용에 의존**한다 — FE 를 건드리는 회차에서는 상시 red
**Category:** 게이트 하네스
**Priority:** P3
**Trigger:** 도래 — `apps/web/` 을 건드리는 모든 회차가 로컬에서 이것을 본다
**Est:** S (합성 시나리오로 음성 대조를 밀봉)
**출처:** 2026-08-16 layout-alignment — 자기 회차에서 실제로 밟음

**원인 / 영향:** 케이스 ⑩(`[BL-739]` screen.ok required 술어)의 음성 대조는
`final-gates-test.sh:191` 주석대로 **「둘 다 0줄인 지금」**을 전제한다. 그런데 그 「지금」은
**하네스가 만드는 상태가 아니라 실행 시점 브랜치의 diff** 다. `apps/web/` 을 한 줄이라도
건드린 브랜치에서 돌리면 `screen.ok` 가 **올바르게** 필수가 되고, 하네스는 그것을 실패로 읽는다.

★**게이트는 옳고 하네스가 틀렸다.** 양성 대조(`PROBE_SRC` 로 `apps/api/src` 탐침 생성)는
합성인데 음성 대조만 환경에 맡겨져 있다 — 비대칭이 원인이다.

★**CI 에서는 안 드러난다.** `actions/checkout@v4` 기본 체크아웃에 `refs/remotes/origin/main` 이
없어 `BASE=""` → `CHANGED=""` → `has_fe=0` 이 되므로 음성 대조가 우연히 성립한다. 즉
**로컬에서만 red 이고 CI 는 초록**이라, 로컬 게이트를 믿지 못하게 만드는 쪽으로만 작동한다.

**권장 접근:** ⑴ 음성 대조도 양성처럼 **합성**으로 만든다 — 임시 orphan 커밋이나
`CHANGED` 주입 훅으로 「FE·api/src 0줄」 상태를 하네스가 직접 세운다
⑵ 그게 무거우면 최소한 **전제를 검사**해라 — 브랜치 diff 에 `apps/web/`·`apps/api/src/` 가
있으면 케이스 ⑩ 을 `SKIP`(사유 명시)으로 내리고 실패로 세지 않는다. 조용히 통과시키지 마라
⑶ ★**「필수 아님」이 한 번도 안 나오는 상태로 두지 마라** — 그것이 이 케이스가 처음 잡으려던
바로 그 병(판별력 0)이다

**Risk:** 🟢 (하네스만. 게이트 본체 동작에는 영향 없다)

**상태:** ✅ **Resolved (2026-08-17, PR #651 머지 `d28bf28f`).** 케이스 ⑩ 의 음성 대조를 합성으로 세웠다. `final-gates.sh` 에 **`--dry-run` 한정** 영역 주입 훅 `QB_FG_FAKE_CHANGED` 를 두고(실행 모드에서 주면 **rc=1 로 거부** — 조용히 먹으면 그 순간 게이트 우회로가 된다), ⑩ 을 3절로 재작성했다: ⑴ 합성 음성 → 「필수 아님」 ⑵ 합성 양성 BE 축 → 「필수」 ⑶ 실물 양성(종전 `PROBE_SRC` 탐침) → 「필수」. ⑶ 을 남긴 이유는 훅만 보는 항진명제가 되지 않게 하기 위해서다. ★★**CONTROL 통제 대조로 판별력을 확정했다** — `apps/web` 을 건드리는 임시 커밋을 얹은 **같은 트리**에서 **구판 하네스 9/10 rc=1(실패 ⑩ 하나) · 수정판 10/10 rc=0** 이고, 임시 커밋을 걷어낸 뒤 HEAD sha 복원까지 확인했다. 우회 가능성도 실측으로 닫았다 — 실행 모드에서 `QB_FG_FAKE_CHANGED` 는 **값이 있든 비어 있든** rc=1 이다(`${VAR+x}` 판정). ★**변이 M6 신설** — 훅 대입문을 죽이면 절 ⑴·⑵ 가 서로 반대의 답을 요구하므로 **어느 트리에서든** 한쪽이 깨진다(환경 독립 변이)
**트리거 판정:** 도래 — FE 를 건드리는 회차마다 로컬 하네스가 red 로 읽힌다 (2026-08-16 layout-alignment)

### BL-781

**Title:** 격리 슬롯에서 **authed e2e 가 구조적으로 불가능**하다 — **격리 task** 가 `BETTER_AUTH_URL` 을 슬롯 포트로 안 맞춘다
**Category:** Ops / 워크트리 · 인증
**Priority:** P2
**Trigger:** 도래 — 워크트리에서 FE 를 건드리는 모든 회차가 마감 게이트의 authed 레그를 못 돈다
**Est:** S (`mise.toml` 2줄 + env 문서 1줄 — 종전 「Makefile 2줄」은 [ADR-036] 으로 낡았다)
**출처:** 2026-08-16 layout-alignment — 실제로 밟고 trace 로 원인 확정

**원인 / 영향:** `grep BETTER_AUTH Makefile` = **0건**. `fe-isolated` 는 `NEXT_PUBLIC_API_URL`·
`PORT` 를 슬롯 포트로 맞추고 `be-isolated` 는 `FRONTEND_URL`·`WAITLIST_INVITE_BASE_URL` 까지
맞추는데, **`BETTER_AUTH_URL` 만 빠졌다.** 그 값은 `.env.local` 의 `http://localhost:3000` 으로
남고, 앱은 `:3100` 에서 서빙된다.

⇒ Better Auth 가 브라우저 로그인을 **전건 `403 {"code":"INVALID_ORIGIN"}`** 으로 거부한다.
`e2e/global.setup.ts` 가 실패해 **authed 88건이 아예 실행되지 않는다.**

★**이것이 왜 지금까지 안 드러났나 — 두 겹으로 가려져 있었다.**
⑴ **curl 로는 200 이 난다** — Origin 헤더가 없으면 검사를 안 거친다. 그래서 「인증은 된다」는
오판이 쉽다(이 회차가 실제로 그 순서로 오판했다).
⑵ [ADR-034] 이전 Clerk 은 포트를 안 봤다. 즉 **self-host 전환이 격리 레인을 깨뜨렸는데
그 레인을 재검증한 회차가 없었다.** 「있다고 여겨진 것이 그 경로를 안 지났다」의 또 한 사례.
⑶ CI 도 못 잡는다 — `ci.yml:500` 이 authed project 를 안 돌린다(`:446`·`:482` 가 명시).

**권장 접근:** ⑴ `fe-isolated`·`be-isolated` 에 `BETTER_AUTH_URL=http://localhost:$(QB_FE_PORT)` 를
추가한다 — 두 줄이다. FE 와 BE 가 **같은 값**이어야 한다(어긋나면 JWT `iss`/`aud` 불일치로 전건 401)
⑵ ★**음성 대조를 붙여라** — 값을 안 맞춘 상태로 `global.setup.ts` 가 **INVALID_ORIGIN 으로 죽는지**
확인한다. 안 죽으면 그 검사는 판별력이 없다
⑶ `worktree-parallel.md` 에 「authed e2e 는 슬롯 포트와 `BETTER_AUTH_URL` 이 짝이어야 한다」를 적는다 —
`.env` 짝 표(§ 워크트리 필수 파일)와 같은 자리다

**Risk:** 🟡 (검증 레인만. 프로덕션 인증에는 영향 없다 — 거기서는 URL 이 맞다)

**상태:** ✅ **Resolved (2026-08-17, PR #651 머지 `d28bf28f` — 슬롯 2 실측).** 격리 슬롯에서 `pnpm e2e:authed` 가 **90 passed / rc=0** 으로 돌았다. 수리 자체는 [ADR-036] 회차가 러너를 옮기며 이미 들어가 있었고(`mise.toml:312` be-isolated · `:330` fe-isolated 가 **같은 표현식** `BETTER_AUTH_URL="http://localhost:${QB_FE_PORT}"`), 이 회차가 한 것은 **증명**이다. ★**변이 2종이 서로 다른 사인을 냈다** — ⑴ `fe-isolated` 에서 그 줄을 빼면 `global.setup.ts` 가 `page.waitForURL` 60s timeout 으로 죽어 **authed 스위트가 아예 실행되지 않는다**(`POST /api/auth/sign-in/email` 이 `Origin: http://localhost:3102` 에 **403 `INVALID_ORIGIN`**) ⑵ FE·BE 를 서로 다르게 두면 setup 은 **통과**하고 BE authed API 가 전건 401 이 되어 **12 failed / 78 passed** 다. ★★**`curl` 은 이 검사를 안 거친다** — 같은 엔드포인트가 `Origin` 헤더 없이는 자격증명 검사까지 도달해 401 을 낸다. 2026-08-16 회차가 `curl` 을 먼저 쳐 「인증은 된다」고 오판한 경로가 이것이다. **판정 증인은 브라우저다.** 짝 규칙과 이 함정은 `docs/reference/operations/worktree-parallel.md` §6 에 있다
**트리거 판정:** 도래 — 워크트리 FE 회차마다 발현한다 (2026-08-16 layout-alignment)

### BL-782

**Title:** `alembic check` 의 rc=0 은 **그 DB 에 대해서만** 참이었다 — migration 으로만 만든 DB 에서는 `trading.funding_rates.exchange` 타입 drift 로 실패한다
**Category:** DB / migration 무결성
**Priority:** P2
**Trigger:** 도래 — [BL-770] 이 「rc=0 을 처음 달성」이라 적은 그 보증이 지금 성립하지 않는 DB 가 실재한다
**Est:** M (판정 기준 확정이 본체. 타입 변환 자체는 살아 있는 컬럼이라 데이터 위험이 따로 있다)
**출처:** 2026-08-17 sprint-parallel-lanes — [BL-773] 레인이 AC-5 를 돌리다 밟았고 CONTROL 이 `origin/main` 대조로 선재 확정

**원인 / 영향:** `apps/api/src/trading/models.py:438` 이 `exchange: ExchangeName`(enum)로 선언하는데
`apps/api/alembic/versions/20260421_0001_add_funding_rates_table.py:29` 는 `sa.Column("exchange", sa.String(length=32))`
로 만든다. **그 타입을 바꾼 migration 은 레포에 존재하지 않는다**(전수 grep 0건). 따라서
`alembic upgrade head` 로만 만든 DB 에 `alembic check` 를 돌리면 `modify_type` 이 잡혀 rc=1 이다 —
이 회차 실측이고 `origin/main` 에서도 같다.

★**이것이 원장을 반증한다.** [BL-770] 은 「`alembic check` rc=0 이 처음」이라고 닫혔는데, 그 측정은
**다른 방식으로 만들어진 DB**(개발 DB / `create_all` 스키마)에 대한 것이었다. [BL-749] 가 적은
「스키마 동등성 검사가 컬럼 **이름만·한 방향만** 본다」와 같은 자리에서 만난다 — 이름 층에서는
같고 타입 층에서 갈린다. ⇒ **migration 방어면은 아직 이름만 남아 있다.**

**권장 접근:** ⑴ ★**먼저 판정 기준을 정해라** — `alembic check` 를 어느 DB 에 대고 재는 것이
정본인가(migration-only DB 가 맞다). 지금은 그 정의가 없어 같은 명령이 환경마다 다른 답을 낸다
⑵ 그 다음 drift 를 닫는다. 선택지는 **모델을 `str`(VARCHAR 32)로 낮추기** 와
**migration 에 `ALTER TYPE ... USING` 추가**다. 후자는 살아 있는 컬럼이라 값 검증이 선행이다
⑶ ★**전량을 한 번에 켜지 마라** — [BL-749] 가 적은 대로 다른 drift 가 같이 쏟아지면 게이트가
상시 red 가 된다. 축을 하나씩 켜라

**Risk:** 🟠 (살아 있는 컬럼의 타입 변환. 되돌리기가 비싸다)

**상태:** ✅ **Resolved (2026-08-17 야간 gate-pins, PR #658).** 판정 기준을 **migration-only DB** 로 확정해 `gates-and-traps.md` §환경에 적었다 — migration 이 프로덕션 스키마를 만드는 유일한 경로이기 때문이다. 그 기준으로 남아 있던 **유일한 drift**(`trading.funding_rates.exchange` VARCHAR(32) → `exchangename`)를 migration `20260817_0002` 로 닫았고(DDL 문 1개), 게이트 `CI fresh DB alembic` 과 **CI `backend` 잡** 둘 다 `upgrade head` 뒤에 `alembic check` 까지 돈다. ★**[BL-770] 의 「rc=0 이 처음」은 개발 DB 에 대한 참이었다** — 그 DB 는 `create_all` 이력이 섞여 컬럼이 이미 enum 인데 migration 계보로만 만들면 `varchar(32)` 다. 같은 명령이 DB 마다 다른 답을 냈고 그 사실이 어디에도 안 적혀 있었다. ★모델을 낮추지 않고 migration 을 올린 근거: 같은 enum 을 쓰는 `exchange_accounts.exchange` 는 `20260416_2206` 에서 이미 native enum 이라, 모델을 `str` 로 낮추면 같은 개념의 두 컬럼이 서로 다른 타입이 된다.

CONTROL 이 AC-6/AC-7 을 독립 재현했다(throwaway DB `alembic check` rc=0 / migration 을 뺀 fresh DB rc=255,
사유는 그 컬럼의 `modify_type` 하나뿐). `funding_rates` 는 hypertable 이 아니다(hypertable 은 `ts.ohlcv` 뿐).
★**서버 소크 DB 에는 적용하지 않았다** — 적용 전 `SELECT DISTINCT exchange FROM trading.funding_rates` 로
값을 먼저 세라. 라벨 밖 값이 있으면 `USING` 캐스트가 트랜잭션째 롤백한다(소리 내며 실패하며 조용한 손상은
아니다) → [BL-790]. 후속 후보: `funding_rate_repository.py` 의 `cast(exchange, String)` 은 이제 구조적으로
불필요하나 migration 이 안 닿은 DB 를 위해 남겼다 — 전 배포처가 head 에 도달하면 걷어내고
`ix_funding_rates_exchange_symbol` 를 되찾을 수 있다.
**트리거 판정:** 도래 — 검사 대상 DB 를 바꾸는 순간 재현되고, [BL-773] 회차가 실제로 밟았다

### BL-783

**Title:** **Stress Test 도 실행 시점의 mutable Pine 을 다시 읽는다** — [BL-773] 이 닫은 것과 같은 결함이 네 번째 소비자에 남았다
**Category:** 도메인 / 재현성
**Priority:** P1
**Trigger:** 도래 — [BL-773] 이 머지되는 순간 「재현성을 닫았다」가 이 경로에 대해 거짓이 된다
**Est:** M ([BL-773] 의 optimizer 처방을 그대로 옮긴다 — 호출 3곳 + 테스트)
**출처:** 2026-08-17 sprint-parallel-lanes — [BL-773] 에 대한 적대 리뷰(P2-1). CONTROL 이 코드 대조로 확인

**원인 / 영향:** `apps/api/src/stress_test/service.py:326`(`_load_run_context`)이
`find_by_id_and_owner(bt.strategy_id, bt.user_id)` 로 **현재 Strategy** 를 읽고, `:360`(walk-forward) ·
`:380` · `:427` 세 곳이 `ctx.strategy.pine_source` 를 엔진에 넘긴다.
`grep -c 'strategy_version' apps/api/src/stress_test/service.py` = **0건**.

`StressTest.backtest_id`(`stress_test/models.py`)가 **부모 Backtest 를 참조**하므로 구조가
optimizer 와 정확히 같다 — optimizer 는 [BL-773] 에서 `bt.strategy_version_id` 로 부모 스냅샷을
쓰게 바뀌었는데 stress_test 만 남았다.

**재현:** Pine A 로 백테스트 제출 → 완료 → 전략을 Pine B 로 수정 → 그 백테스트에
walk-forward / cost-assumption / param-stability 실행 ⇒ **B 가 실행되고 결과는 A 의 백테스트에 매달려 표시된다.**

★★**원장 자신이 이 소비자를 빠뜨렸다.** [BL-773] 본문은 「**3경로** 확정」이라 적었는데
`CONTEXT.md` 는 이미 「Optimizer·**Stress Test** 는 backtest 의 `run_backtest` 엔진을 재실행한다 …
v2_adapter 변경은 이 **3 소비자**에 동시 영향」이라고 적고 있었다. **처방이 헌법보다 좁았고,
헌법을 읽었으면 그 자리에서 보였다.**

**권장 접근:** ⑴ `_load_run_context` 가 `bt.strategy_version_id` 로 스냅샷을 읽게 한다
([BL-773] 의 `optimizer/service.py` 처방과 동형) ⑵ `test_strategy_version_pinning.py` 의 optimizer
케이스를 stress_test 로 복제해 **구현 전 red** 를 먼저 확인해라 ⑶ Monte Carlo 는 완료 Backtest 의
trades 재표집이라 엔진을 재실행하지 않는다 — 대상에서 빼라(`CONTEXT.md` Relationships)

**Risk:** 🟡 (경로가 이미 검증된 처방이고 소비자가 격리돼 있다)

**상태:** ✅ **Resolved (2026-08-17 야간 레인 β, PR #654 `316b0541`).** 엔진 재실행 3경로가 전부 부모 Backtest 에 핀된 `StrategyVersion.pine_source` 스냅샷을 쓴다. `_RunContext.strategy: Strategy` → `pine_source: str` 로 타입을 좁혀 **호출부에서 현재 소스를 다시 읽을 문 자체를 닫았고**(되돌리는 변이가 타입이 아니라 테스트에서 잡힌다), 핀 조회는 `_resolve_pinned_pine_source` 한 곳이다. `strategy_version_id` NULL 인 legacy 행만 현재 Strategy 로 떨어지고 그 경로는 `stress_test_run_without_pinned_strategy_version` 경고를 남긴다. `grep -c strategy_version .../stress_test/service.py` **0 → 7**. 신규 `test_strategy_version_pinning.py` 6건은 **구현 전 red**(실패 사유가 `'…version B…' != '…version A…'` — 설정 오류가 아니라 결함 재현). AC-3 은 diff 로 확정(MC 관련 줄 **0건**, `_execute_monte_carlo` 는 `strategy`·`_load_run_context` 를 한 번도 참조하지 않는다).
★**표적 변이 5/5 red 이고 3경로가 각각 독립으로 red** — 하나씩 되돌리면 그 경로의 테스트만 정확히 깨진다. ★CONTROL 이 **레인이 쓰지 않은 변이**(`engine_fn` 호출부만)를 따로 심어 재확인: rc=1 · 정확히 2 failed, 나머지 핀 테스트 3건 green 유지. 게이트 2단 rc=0 · 전량 BE pytest **4759 passed**(기준선 4753 + 신규 6) · e2e authed 90 passed · 유예 원장 소멸.
★**낡은 mock 2곳이 이 회차에도 있었다**([LESSON-116] 재현) — `_bt()` 의 `SimpleNamespace` 에 `id`·`strategy_version_id` 가 없어 라우팅 3건이 `AttributeError` 로 깨졌고, config-propagation 의 bare `AsyncMock` 은 `get_version_by_id` 가 MagicMock 을 돌려줘 **초록이면서도 무엇을 실행하는지 말할 수 없는** 상태였다. ★**부수 관측** — `backtests.strategy_version_id` FK 가 `ondelete="RESTRICT"` 라 「핀은 있는데 스냅샷 행이 없다」는 **오늘의 DB 에서 도달 불가**다(그 분기만 repo mock, 이유는 docstring). ★**미채택 1건 → [BL-787]** — optimizer 의 `engine_version` 가드는 옮기지 않았다(범위 밖 + AC 없음, 옮기면 동작이 바뀐다).
**트리거 판정:** 도래 — [BL-773] 머지와 동시에 발화했고 2026-08-17 에 닫혔다

### BL-784

**Title:** `e2e authed` 레그가 **게이트 실행에서만 비결정적으로 red** 다 — 기전 미확정, 가설 2개가 실측으로 반증됐다
**Category:** 테스트 / e2e 안정성
**Priority:** P2
**Trigger:** 도래 — 2026-08-17 에 게이트 안에서 **2회 연속** 재현됐다
**Est:** S (수리는 각 지점 2~3줄. 본체는 변이로 판별력을 증명하는 것)
**출처:** 2026-08-17 sprint-parallel-lanes — [BL-773] 이 e2e authed 레그를 발화시키면서 처음 드러났다

**원인 / 영향:** ★★**기전이 확정되지 않았다.** 2026-08-17 에 게이트 실행에서 e2e authed 가 여러 차례
red 였는데 실패 테스트가 실행마다 갈렸고, 단독 실행은 항상 green 이었다. 세운 가설 **둘 다 실측으로 반증**됐다.

| 가설                                                                          | 근거                                                                                                                                     | 판정     |
| ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| `click({force:true})` 가 actionability 를 건너뛰어 하이드레이션 전에 발화한다 | `force` 를 그대로 둔 경로에서 같은 테스트가 **통과**                                                                                     | **반증** |
| BE pytest 가 e2e 시드 데이터를 지운다                                         | 같은 게이트 실행에서 데이터 의존 4지점(`/backtests` · `/backtests/:id/trades` · `/strategies/:id/edit` · `/backtests/:id`) **전부 통과** | **반증** |

남은 후보는 **개발 서버 부하 상황의 렌더·응답·DOM 발견 지연**이지만, **실패 시점의 network trace 가 없어
더 좁힐 근거가 없다.** 실패한 테스트들은 라이브 목록에서 ID 를 발견하고 둘은 1.5초 고정 대기 후 DOM 을 읽는다.

★**증상 오인 주의** — 「제출 버튼을 눌렀는데 POST 가 없다」는 2026-08-10 프로덕션 사고(브라우저가 submit 을
발화조차 안 했다)와 **같은 모양**이라 원인을 코드 쪽으로 오해하기 쉽다. 이 회차가 실제로 그렇게 오판했다.

★**이번 회차 코드와는 인과가 없다** — [BL-773] 브랜치의 `apps/web` diff 는 0 이었고, 처음 실패한
`sprint46-tier1-critical.spec.ts:69` 는 `page.route()` 로 strategies·backtests API 를 **전수 stub** 한다.

★★**왜 지금까지 안 보였나 — 그 레그가 안 돌았다.** `final-gates.sh:378` 의 `e2e authed` 술어는
`has_fe ∪ has_be` 다. 2026-08-17 회차의 세 브랜치 중 그 영역을 건드린 것은 [BL-773] 하나뿐이라
**#651·#652 는 이 레그가 skip 된 채 유예 원장이 지워졌다.** 영역 판정으로는 옳은 skip 이지만
「원장이 지워졌다 = 종결」이 담는 증거량은 **브랜치마다 다르다.**

**이 회차가 한 것:** `sprint46-tier1-critical.spec.ts` 의 제출 동기화를 보강했다(그 자체로 나쁘지 않다).
★**그 변경이 원인을 고쳤다고 주장하지 않는다** — 변이가 red 를 내지 못했다.

**권장 접근:** ⑴ ★**먼저 증거를 만들어라 — 지금 없는 것은 처방이 아니라 관측이다.** 게이트 실행에
`trace: 'on'` 을 걸어 실패 시점 network·DOM 을 남겨라. 그것 없이는 네 번째 가설도 같은 운명이다
⑵ 실패 테스트들의 공통점(라이브 목록에서 ID 발견 · 1.5초 고정 대기)을 축으로 삼아 **고정 대기를 조건 대기로** 바꿔라
⑶ ★**어떤 수리든 변이로 판별력을 증명해라.** 이 회차는 수리 후 변이가 red 를 안 내서 「고쳤다」고 말할 수 없었다
⑷ ★**timeout 예산을 늘리지 마라** — 진짜 회귀도 못 잡게 된다([BL-775] 회차 교훈)
⑸ 잔존 `force: true` 2곳(`sprint46-tier3-nth.spec.ts:559` · `dogfood-flow.spec.ts:152`)은 **인과 미확정**이다.
기전이 확정되기 전에 손대지 마라

**Risk:** 🟡 (테스트 전용. 다만 잘못 고치면 판별력이 사라져 진짜 회귀를 놓친다)

**상태:** ✅ **Resolved (2026-08-17 야간 bl784-fix, PR #659).** 기전은 직전 회차가 확정했고(지연이 아니라 **거부** — BE 전역 `default_limits=["100/minute"]` 이 신원 단위로 authed 스위트를 429 로 끊는다. 한 신원 × 90 테스트 × 요청 4~8건이라 60초 창을 상시 소진하고, 대부분이 단언 없는 배지 프로브라 **하필 단언 대상이 걸린 회차만 red** 였다), 이 회차가 수리했다. **한도 자체는 [BL-754] 가 세운 프로덕션 방어물이라 안 건드렸다**(`default_limits` diff 0줄) — e2e 신원 **하나만** 면제한다.

발화 조건은 둘이고 둘 다 필요하다: ⑴ `app_env` 가 **정확히 `development`** ⑵ 검증된 JWT 의 `email` 이 `E2E_RATE_LIMIT_EXEMPT_EMAIL` 과 일치(양쪽 `strip().lower()`). 설정이 비면 아무도 면제되지 않는다 — **비교보다 설정 검사를 먼저** 둔 이유다. 판정: authed 연속 3회 rc=0(90 passed) · BE 429 **0건**. 판별력은 한도를 `5/minute` 로 낮춰 증명했다 — 완화 no-op 이면 **429 913건에 8 failed**, 켜면 **0건에 90 passed**.

★**⑴ 이 화이트리스트인 것이 적대 리뷰의 산물이다.** 초판은 `settings.is_production`(블랙리스트)이었는데 `is_production` 은 **staging 을 거짓으로 본다**. 부팅 검사도 `_enforce_production_safety` 의 조기 반환 **뒤**에 있어 staging 에서는 실행조차 안 됐다 — 즉 **staging 인스턴스에는 두 층이 모두 없었다**. CONTROL 이 두 층을 다 화이트리스트로 바꾸고 부팅 검사를 validator 맨 앞으로 옮겼다(변이: 각각 되돌리면 새 staging 테스트 2건만 red, 35 passed).

★**[BL-773] 의 `sprint46-tier1-critical.spec.ts:69` 가 이번에 재현됐다.** 직전 회차는 재현하지 못했고 「그 spec 은 `page.route()` 로 전수 stub 이라 BE 429 를 안 탄다」고 적혀 있었는데 **거짓이다** — `page.route` 를 19곳 쓰지만 전수가 아니다. 한도를 낮춰 429 를 강제하면 그 테스트가 실패 8건에 들어가고 완화를 켜면 통과한다. 즉 [BL-773] 의 최초 실패와 이 수리가 같은 축이고, 이 축은 더 이상 차단자가 아니다.

★★**코드만 머지하면 안 고쳐진다** — `E2E_RATE_LIMIT_EXEMPT_EMAIL` 은 `.env.local` 값이고 그 파일은 커밋 대상이 아니다. 메인 체크아웃 `apps/api/.env.local` 에 `E2E_RATE_LIMIT_EXEMPT_EMAIL=e2e@dogfood.local` 이 있어야 발화한다(값은 `apps/web/.env.local` 의 `E2E_AUTH_EMAIL` 과 같아야 한다). 2026-08-17 통합 시 넣었다. **이 변수를 어떤 배포 환경의 env 에도 넣지 마라** — `APP_ENV` 가 누락되면 두 층 다 development 로 읽는다(2026-08-15 에 실제로 그 상태로 돈 호스트가 있었다). 변수가 없으면 `APP_ENV` 가 어떻든 아무도 면제되지 않는다.

남은 한계 = [BL-794] (면제가 신원 소유를 증명하지 않는다) · 같은 증상의 두 번째 원인 = [BL-795] (Turbopack 캐시 물림)
★★**전제 2건 반증** — ⑴ 「단독 실행은 항상 green」이 **거짓**(단독 3회 중 1회 red). 「게이트에서만」이라는 축 자체가 틀렸고 게이트는 그 레그를 **돌린 유일한 것**이었다 ⑵ 반증됐던 「pytest 가 시드를 지운다」 가설의 출처가 **테스트의 오도 문구**였다(`:108` 이 429 를 「데이터 시딩 필요」라고 보고한다). ★재현 **15회 중 4회 red**(부하 없음 1/9 · 합성 부하 2 조건 3/6) — 부하는 원인이 아니라 확률 요인이다.
★계측 도입 — `PW_ARTIFACT_RUN` 관측 모드(`playwright.config.ts`) + 재현 하네스(`tools/scripts/e2e-authed-repro.sh`, shape 3종).
★★**증거가 없던 이유가 확인 행위였다** — playwright 는 매 실행 setup 에 `outputDir` 을 통째로 지우고 project 7종이 `test-results/` 하나를 공유해서, 게이트 red 뒤 「단독으로도 실패하나」를 돌리는 순간 그 trace 가 파괴된다([LESSON-117]). ★**적대 리뷰가 그 계측기에서 P2 3건**을 찾아 같은 PR 에서 닫았다 — 그중 `PW_ARTIFACT_RUN=..` 가 `outputDir` 을 `apps/web/<project>` 로 만들어 **소스 디렉터리를 지우는** 건이 있었다(수리 + 테스트 6건 + 변이 판별력 증명).
**★남은 것 (수리 회차의 처방):** ⑴ **한도를 e2e 신원에서만 풀거나 넓혀라** — `default_limits` 는 프로덕션 방어물이니 지우지 말고 개발/e2e 프로필에서만. **면제가 프로덕션 경로로 새지 않는다는 음성 대조 필수** ⑵ FE 가 `Retry-After` 를 존중하게 한다(429 에 `retry-after: 7` 이 있었는데 React Query 는 1.15초 뒤 한 번 치고 포기했다 — e2e 와 무관하게 실사용자에게도 옳다) ⑶ 목록·배지 요청이 **전부 쌍으로** 나간다 → [BL-786] ⑷ ★**timeout 예산을 늘리지 마라** — 429 는 기다린다고 안 풀리고 진짜 회귀만 못 잡게 된다 ⑸ 수리 뒤 한도를 인위적으로 낮춰(`5/minute`) 해당 테스트가 red 가 되는지로 판별력을 증명해라
**★미확정:** [BL-773] 회차에서 최초 실패한 `sprint46-tier1-critical.spec.ts:69` 는 **재현하지 못했다** — 그 테스트는 `page.route()` 로 전수 stub 이라 BE 429 를 안 탄다. 같은 원인인지 모른다. 429 가 그 회차 실패 **전건**을 설명하는지도 확인 안 됐다
**트리거 판정:** 도래 — `apps/web` 또는 `apps/api/src` 를 건드리는 회차마다 게이트에서 재현된다

### BL-785

**Title:** 게이트가 [ADR-036] 의 버전 SSOT 를 **우회**한다 — `final-gates.sh` 가 PATH 의 `pnpm`·`uv` 를 부른다
**Category:** Infra / 게이트
**Priority:** P2
**Trigger:** 도래 — 2026-08-17 에 `CI frozen-lockfile` 게이트가 이 이유로 red 였다
**Est:** S (호출 3~4곳을 `mise exec --` 경유로. 본체는 **어느 도구가 대상인지 전수**하는 것)
**출처:** 2026-08-17 sprint-parallel-lanes — 통합 브랜치 마감 게이트에서 밟았다

**원인 / 영향:** `tools/scripts/final-gates.sh:489` 가
`bash -c 'cd "$0/apps/web" && pnpm install --frozen-lockfile'` 로 **PATH 의 `pnpm`** 을 부른다.
[ADR-036] 은 도구 버전의 SSOT 를 `mise.toml` 하나로 못박았지만 **게이트는 그 핀을 안 쓴다.**

실측(같은 워크트리 · 같은 명령 · diff 0):

| 무엇                                 | 버전       | rc                                          |
| ------------------------------------ | ---------- | ------------------------------------------- |
| PATH `pnpm` (게이트가 쓰는 것 — nvm) | **8.15.9** | **1** (`ERR_PNPM_LOCKFILE_BREAKING_CHANGE`) |
| `mise exec -- pnpm` ([ADR-036] 핀)   | **9.12.0** | **0**                                       |

`apps/web/pnpm-lock.yaml` 은 `lockfileVersion: "9.0"` 이라 pnpm 8 로는 읽을 수 없다.
★**증상이 「내 PR 이 lockfile 을 깼다」로 보인다** — 실제로는 lockfile·`package.json` diff 가 **0** 인
브랜치에서도 red 다. 이 회차가 실제로 그 오인 경로를 밟았다.

★**이것은 [ADR-036] 이 예고한 드리프트의 잔여다.** 그 회차가 「pnpm 이 한 레포에 메이저 2개」를 실측하고
`mise.toml` 로 모았는데, **소비자 중 게이트가 안 따라왔다.** AGENTS.md 는 「터미널에서 직접 칠 때만
`mise activate` 가 필요하다」고 적지만 게이트는 스크립트라 그 예외에 안 들어간다.

**권장 접근:** ⑴ ★**먼저 전수해라** — `final-gates.sh` 와 `tools/scripts/*` 에서 `pnpm`·`uv`·`node` 를
직접 부르는 자리를 전부 찾아라. pnpm 1곳만 고치면 같은 병이 `uv` 축에 남는다
⑵ `mise exec --` 경유로 바꾸거나, 스크립트 진입부에서 shim 을 PATH 앞에 세운다(git 훅이 이미 그렇게 한다)
⑶ ★**음성 대조** — PATH 에 낡은 도구를 일부러 둔 상태에서 게이트가 **여전히 초록**인지 확인해라.
그래야 「핀을 쓴다」가 증명된다
⑷ CI 는 이 병이 없다(워크플로가 버전을 명시) — **로컬에서만 red** 라 로컬 게이트 신뢰만 깎는다.
[BL-780] 이 닫은 것과 같은 계열의 비대칭이다

**Risk:** 🟡 (게이트 전용. 다만 고치기 전까지 로컬 마감이 이 한 건으로 막힌다)

**상태:** ✅ **Resolved (2026-08-17 야간 gate-pins, PR #658).** 로컬 스크립트 5종이 `tools/scripts/lib/mise-shim-path.sh` 로 shim 을 PATH 앞에 세운다. `mise exec --` 대신 이쪽을 고른 근거는 셋이다 — ⑴ `mise exec --` 는 `mise` 바이너리가 PATH 에 있어야 하는데 이 병의 전형적 셸은 「shim 은 있는데 mise 는 활성화 안 된」 셸이다(shim 은 자기완결 바이너리라 `PATH=shims:/usr/bin:/bin` 에서도 9.12.0 을 낸다) ⑵ `final-gates.sh` 의 호출 지점이 17곳이고 대부분 `bash -c '…'` 문자열 안이라 17곳을 고치면 17곳이 다시 새는 표면이 된다 ⑶ `.husky/pre-commit`·`pre-push` 가 **이미 그 관용구**다. 재유입은 새 게이트 `tool-pin-audit.sh` + 하네스 13케이스가 막는다(`mise run gate-harnesses` 13→14종). **음성 대조로 종결했다** — 가짜 `pnpm`/`uv`/`node`(`exit 1`)를 PATH 앞에 세운 채 수리 전 코드는 `CI frozen-lockfile` rc=1, 수리 후는 rc=0(`pnpm` 축과 `uv` 축 각각). ★**서버(`truewords-oracle`)에서 도는 `soak-*.sh` 6종은 안 고쳤다** — 그 환경의 mise 존재를 확인할 수 없고 접속이 금지다. 근거는 「없을 수도 있으니」가 아니라 **「모르니」**다.

★**이 회차가 만든 회귀 1건을 이 회차가 잡았다** — `docs-audit.sh` 에 핀을 넣자 `docs-audit-test.sh` 가
fixture 트리에 `lib/` 를 안 옮겨 19케이스가 전부 rc=1 이 됐고, 표적 테스트 13건은 전부 초록이었다.
잡은 것은 **게이트 전량 실행**이다.

★**적대 리뷰가 잡은 P2 를 CONTROL 이 같은 PR 에서 수리했다** — 감사기가 스캔 루트를 `QB_TOOL_PIN_ROOT`
env 만 보고 정했고 `final-gates` 가 루트를 명시하지 않아, 위반을 심은 트리에서
`QB_TOOL_PIN_ROOT=<빈 트리>` 하나로 rc=1 → **rc=0 + 「✓ 위반 0건」 초록**이 났다. `signal-check.sh` 가
콜드 리뷰 P2-1 에서 겪고 `--root` 로 닫은 바로 그 결함이라 그 관용구를 재사용했고, 대상 0개면 rc=3
abort 도 넣었다(「볼 것이 없으면 통과」 — 소크 C4 와 같은 병). 남은 사각은 [BL-791]·[BL-792].
**트리거 판정:** 도래 — `apps/web` 이 없는 브랜치에서도 이 게이트는 돌고, 그때마다 red 다

### BL-786

**Title:** 목록·배지 API 요청이 **전부 쌍으로** 나간다 — 같은 URL 이 같은 순간에 두 번
**Category:** 프런트 / 네트워크
**Priority:** P2
**Trigger:** 도래 — trace 에 이미 찍혀 있다
**Est:** S (어디서 두 번 나가는지 찾는 것이 일의 대부분)
**출처:** 2026-08-17 야간 레인 α — [BL-784] 기전 추적 중 trace 실측

**원인 / 영향:** [BL-784] 의 실패 회차 trace 에서 `GET /api/v1/backtests?limit=20&offset=0&order_by=created_at&order=desc`
가 **578ms 에 두 번** 나갔다(하나는 200, 쌍둥이가 429). 목록만이 아니라 **내비 배지 프로브도 전부 쌍**이었다.

이것 자체로는 화면이 깨지지 않는다 — 그래서 넉 달간 아무도 못 봤다. 문제는 **비용**이다.
authed e2e 는 한 신원으로 90 테스트를 도는데, 요청이 두 배면 BE 의 `100/minute` 창을 **두 배 속도로**
소진한다. [BL-784] 의 429 는 이 중복이 없었으면 창을 절반만 먹었다.

★**실사용자에게도 그대로 나간다.** 대시보드를 열 때마다 같은 쿼리가 두 번 간다.

**권장 접근:** ⑴ ★**먼저 어디서 두 번 나가는지 확정해라** — React Query 키 중복 / 컴포넌트가 두 번 마운트
(StrictMode) / 레이아웃과 페이지가 같은 훅을 각자 부름 중 어느 것인지. **추측하지 말고 trace 로 갈라라**
⑵ StrictMode 이중 실행이면 개발 전용이라 e2e 조건과 프로덕션이 갈린다 — 그 경우 [BL-784] 의 산술이 바뀐다
⑶ 재현 계측은 이미 있다 — `PW_ARTIFACT_RUN` 관측 모드로 trace 를 남기고 network 타임라인을 읽어라

**Risk:** 🟢 (읽기 요청 중복 제거. 다만 원인이 StrictMode 면 「고칠 것이 없다」로 끝날 수 있다)

**상태:** ✅ **Resolved (2026-08-17 야간 bl786-dup, PR #660).** 원인은 StrictMode 가 **아니다** — React Query 키의 첫 인자 `uid` 가 한 화면 로드 안에서 `"anon"` → 진짜 id 로 바뀌어(세션 왕복 전까지 `useAuthCtx` 가 `anon` 을 낸다) 모든 목록·배지 쿼리가 **두 키로 각각 한 번씩** 나갔다. ★**「동시에 두 번」이 「한 번 마운트되고 두 번 요청」이 아니었다** — 두 요청이 같은 ms 에 나간 것은 둘 다 `getAuthToken()` 해소를 기다렸다가 함께 풀렸기 때문이다. 가설을 가른 방법 셋: ⒜ 프로덕션 standalone 빌드에서 **동일 재현**(StrictMode 배제) ⒝ DOM 셸 개수 1벌(이중 마운트 배제) ⒞ uid 전이를 타임라인으로 계측(확정). 수리는 ⑴ SSR 이 아는 `userId` 를 첫 렌더에 넘겨(`ServerIdentityProvider` + `useAuthCtx`, 세션 도착 후에는 세션이 정본) 키 churn 을 없애고 ⑵ `/backtests` 의 SSR prefetch 키를 클라이언트와 **같은 생성자**(`features/backtest/list-query.ts`)에서 만든 것이다 — 후자는 계획에 없던 두 번째 결함으로, prefetch 키가 `{limit, offset}` 이고 클라이언트는 `order_by`·`order` 까지 넣어 **SSR 이 가져온 목록이 넉 달간 통째로 버려지고 있었다**. 검사면 신설 = `e2e/api-request-dedup.spec.ts`(앵커 미관측 시 「측정 실패」로 red — 빈 입력이 초록으로 새는 길을 막았다).

브라우저 요청 `/backtests` 10→4 · `/dashboard` 15→8 · `/strategies` 6~7→3 이고 **dev 와 prod 가 같다**.
★**대가를 측정했다** — layout 이 쿠키를 읽으면서 dashboard **static 라우트가 16→8** 로 준다
(대조 빌드 2회, layout 만 교체). 유지 판단의 근거와 대안은 [BL-793].
★적대 리뷰 P2 를 CONTROL 이 수리했다 — `retry: 1` + 1초 백오프가 측정 창 안이라 429 한 건이 「중복」으로
읽혔다(이 게이트가 **가짜 red 를 내는 장치**였다). 실패 응답을 따로 모아 중복 판정보다 **먼저**
「측정 오염」으로 red 를 낸다.
**트리거 판정:** 도래 — 관측 증거가 이미 있다

### BL-779

**Title:** `docs/backlog.md` 가 분할 후에도 **407k 토큰** — RESOLVED 를 내려 21.5% 만 내려갔고 40% 목표가 남았다
**Category:** 문서 / 컨텍스트 예산
**Priority:** P2
**Trigger:** 도래 — 이미 grep 없이는 열 수 없는 크기다
**Est:** M (분할 설계가 본체. 기계적 이동은 그다음)
**출처:** 2026-08-16 표준 레이아웃 정렬 — `tools/scripts/context-budget.sh` 실측

**원인 / 영향:** ★★**등재 당시 수치가 세 축에서 틀렸다 — 2026-08-16 재측정으로 정정한다.**
본문은 「1,019,776**자**」로 적었는데 그것은 **바이트**다. `AGENTS.md`·`context-budget.sh` 는
읽는 비용을 **문자**로 재라고 정한다(한국어는 UTF-8 에서 자당 3바이트라 1.47배 부풀었다).

| 축       | 등재 당시 표기   | 재측정 (2026-08-16, 분할 전)        |
| -------- | ---------------- | ----------------------------------- |
| 크기     | 1,019,776 **자** | 바이트 1,034,606 / **문자 704,265** |
| tok      | 511,772          | **518,339**                         |
| 줄       | 10,252           | **10,429**                          |
| 섹션     | 323              | **328**                             |
| RESOLVED | 117              | **118**                             |

`docs/` 전체에서 단일 최대이고 `decisions/` 34파일 합계의 2.9배다. RESOLVED 118건 본문이
Open 항목과 **같은 파일에** 있다.

★**줄 길이 상한(1,000자)은 이미 지키고 있다** — 문제는 줄이 아니라 **파일 수명이 섞여 있는 것**이다.
`docs/README.md` 의 수명 분류 원칙(reference / decisions / dev-log / archive)이 backlog 안에서는
적용된 적이 없다.

**권장 접근:** ⑴~⑷ 는 **2026-08-16 bl779-backlog-split 에서 이행했다.** 남은 것은 ⑸ 하나다.

1. ~~★**먼저 재라** — RESOLVED 117건이 차지하는 바이트를 세라. 그것이 분할의 상한이다~~ →
   **쟀고, 그 상한이 이 항목의 목표를 못 채운다.** RESOLVED 118건 본문 = **151,599자 = 원본의 21.5%**.
   나머지는 DEFERRED 178건 37.6% · 섹션 밖(헤더·인덱스 표·산문) 26.9% · PARTIAL 9.1% · ACTIVE 4.8% 다.
2. ~~`docs/backlog-resolved.md` 로 RESOLVED 를 내리고 원본에는 한 줄 색인만 남긴다~~ → **완료.**
   본문 118건을 기계적으로 옮겼고(H2 묶음·섹션 순서 보존, 본문 0자 수정) 인덱스 표 행은 원본에 남겼다.
3. ~~★**`bl-audit.sh`·`docs-audit.sh` 가 `BACKLOG` 경로를 상수로 갖는다**~~ → **완료 — 대상이 넷이었다.**
   `bl-audit.sh`·`docs-audit.sh` 외에 **`bl-trigger-sweep.sh`·`context-budget.sh`** 도 같은 상수를 갖고 있었다.
   ★특히 `bl-trigger-sweep --selftest` 는 양성 픽스처(BL-438)가 RESOLVED 라 **고치지 않았으면 죽었고**,
   음성 픽스처(BL-022)는 **항진명제로 초록**이 됐다 — #618 docs-diet 이 BL-451 픽스처에서 밟은 그 모양이다.
4. ~~★**음성 대조 필수** — 이동 후 `bl-audit.sh` 전체 수(현재 323)가 같은지 확인한다~~ → **완료.**
   판정 4종 전건이 같다(ACTIVE 8 / PARTIAL 24 / RESOLVED 118 / DEFERRED 178 = 328). ★DEFERRED 를
   빼고 세면 「DEFERRED 만 못 읽는」 변이가 초록으로 샌다. 머리줄이 **파일별 섹션 수**를 찍는 것도
   같은 이유다 — 합계만 보면 「한쪽을 못 읽는 것」과 「그 회차에 섹션이 준 것」이 구분되지 않는다.
5. ★**남은 축 두 갈래.** 둘 다 이 회차에서 **의도적으로 안 했다** — 판단 근거를 실측과 함께 남긴다.

   ⒜ ★**옮긴 74행의 `#bl-nnn` 앵커가 이 파일 안에서 죽어 있다**(2026-08-16 적대 리뷰 P1). 행은 남았고
   본문은 저쪽으로 갔으니 클릭해도 안 움직인다. **어느 게이트도 안 잡는다** — `bl-audit` 은 링크 목적지가
   아니라 id 문자열만 읽고, `docs-audit` 은 `#` 뒤를 버린 뒤 파일 존재만 본다.
   ★**단순 재지정은 다른 게이트를 깬다**: 행을 `backlog-resolved.md#bl-nnn` 로 바꾸면 prettier 가 ID 열을
   19자 넓혀 이 파일 **최장 줄 993 → 1,012자**가 되고 **1,000자 상한**을 밟는다(실측).
   ⇒ 값이 나오는 길은 **참조식 링크**다 — `| [BL-724][r724] |` + 파일 끝에 `[r724]: backlog-resolved.md#bl-724`.
   ID 칸이 **14자로 오히려 줄어** 상한을 안 밟는다. 대신 원장에 링크 문법이 하나 늘고
   `bl-audit` 의 행 정규식·하네스에 갈래가 하나 붙는다.
   ★**레포 밖 링크 6곳(ADR-032·033 · system-architecture · instrument-symbol-boundary)은 이미 고쳤다.**

   ⒝ ★**40% 감축은 RESOLVED 만으로는 도달할 수 없다.** 실측 감축은 **21.2%**(704,265 → 555,195자)이고
   ⑴ 의 상한이 그 천장이다. 표 행까지 내려도 30.0% 다. 남은 질량은 **DEFERRED 178건 265,092자(37.6%)** 뿐이고,
   그것을 `backlog-deferred.md` 로 되돌리는 것은 2026-08-06 에 `_deferred.md` 를 합쳤던 결정을 뒤집는 것이라
   **사용자 결정 사항**이다.

**Risk:** 🟠 (원장은 이 레포의 기억이다. 검사기를 먼저 고치지 않고 옮기면 3면 정합이 조용히 죽는다)

**상태:** ✅ **Resolved (2026-08-18 backlog-triage)** — 감축 목표 **40% 초과 달성: 50.5%**.
`docs/backlog.md` 문자 **594,309 → 294,462**(tok 437,411 → 216,724 · 줄 8,134 → 2,321).
처방 = 이 섹션이 사용자 결정으로 남겨 둔 그것 — **DEFERRED 180건을 `backlog-deferred.md` 로 내린다**.
★**분할의 축을 「무엇을 내릴까」가 아니라 「판정어」로 고정했다** — `backlog.md` = ACTIVE ∪ PARTIAL + 인덱스 표 전량 ·
`backlog-deferred.md` = DEFERRED · `backlog-resolved.md` = RESOLVED. 셋이 전부이고 겹치지 않는다.
★★**같이 드러난 것 — 1차 분할이 이미 반쯤 풀려 있었다.** 2026-08-16 이후 닫힌 **RESOLVED 13건이 전부
`backlog.md` 에 다시 쌓여 있었다**. 규칙이 산문이라 아무 게이트도 안 잡았다([BL-643] 이 「산문 처방 3회
실패 뒤 집행처」를 배운 그 자리다) ⇒ `bl-audit.sh` 에 **「파일 배치」 축**을 신설했다(판정어 ↔ 사는 파일, 어긋나면 rc=1).
★검증 = 판정 4종 **전건 불변**(ACTIVE 9 / DEFERRED 180 / PARTIAL 25 / RESOLVED 133 · 전체 347) ·
하네스 22→**26 케이스**(양성 2 · 음성 1 · ABORT 1) · 축 무력화 변이 M2 에서 신규 2건만 red ·
`bl-trigger-sweep --selftest` 17→**18**(셋째 조각 배선 음성 대조, 변이 rc=1).
★**앵커 접두사는 되돌렸다** — 행마다 +18자가 P2 표 패딩을 줄 길이 상한(1,000자) 위로 밀었다(985 → 1,012 실측) → [BL-801].
(종전 판정 = 「Open — 감축 목표 40% 가 열려 있다」, 2026-08-16 bl779-backlog-split)
★**판정을 PARTIAL 로 올리지 않은 것은 의도다.** 이 회차의 수용 기준이 「판정 4종 전건이 이동 전후로
같을 것」(ACTIVE 8 / PARTIAL 24 / RESOLVED 118 / DEFERRED 178)이라, 자기 판정을 바꾸면 그 음성 대조가
자기 자신 때문에 깨진다. 남은 축 ⑸ 를 닫을 때 함께 올려라 — 그때 P2 인덱스 표 행에 🟡 도 같이 붙인다.
**트리거 판정:** 도래 — 이미 세션마다 grep 으로만 접근 가능한 크기이고 계속 자란다 (2026-08-16 layout-alignment)
