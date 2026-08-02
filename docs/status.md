# QuantBridge — Status

> **업데이트:** 2026-08-02
> **활성 Sprint:** 없음. 다음 작업은 아래 「다음 스프린트」 블록만 읽는다.
> **준비 브랜치:** 없음
> **최근 머지:** `stage/metric-guard-parity` → `main` (PR #525, 2026-08-02)

---

## 🎯 다음 스프린트 — **metric-guard-residual** (가드가 못 막는 자리를 좁히고, 못 막는다는 걸 증명한다)

> ★**이것이 다음 세션의 유일한 진입점이다.** 별도 킥오프 파일을 만들지 않는다.
> 시작 방법: **"다음 스프린트 진행해줘"**. `CONTEXT.md` + 본 파일을 읽고 시작한다.
> ★**`AGENTS.md` 는 읽지 마라 — 자동 로드된다**(`CLAUDE.md` 가 `@AGENTS.md` 하나만 import 한다).
> ★**`CONTEXT.md` 는 반대다 — 자동 로드가 아니라서 읽어야 들어온다.** `.ai/rules/*.md` 도 자동 로드가 아니다.
> ★**`docs/dev-log/INDEX.md` 를 통째로 grep 하지 마라** — `## 최근 12회차` 상단만 읽는다.

**한 줄.** 직전 회차가 머니-패스 계측 **18곳**을 감쌌고 **141곳이 남았다.** 남은 것 대부분은
「감쌀 필요가 없다」가 근거인데, **그 근거가 실측이 아니라 코드 독해**다. 이번 회차는 그 근거를
**집행 가능한 형태로 바꾸거나, 틀렸으면 고친다.**

### 첫 step

1. **baseline 재측정** (`global.md` §7.1). 대조값은 아래 블록.
2. **[BL-580] 잔여 141곳의 근거를 검증한다.** ★수리부터 하지 마라 —
   `trading.py:908/931/1093` · `router.py:376` 을 「실패로 계상하는 except 가 없다」로 뺐는데,
   **그 판정은 코드 독해였다.** 고장 주입으로 **실제 귀결**을 재라(직전 회차가 그렇게 해서
   「오기록」이 실은 **과잉 발주**이기도 하다는 걸 찾았다).
3. **[BL-582] 도달 불가 7종을 게이트로 고정한다** — 지금은 문서에만 있다.
   `PendingOrderSnapshot` 이 exit level 을 갖게 되면 조용히 도달 가능해지는데 **아무도 모른다.**
4. **[BL-576] 잔여** — `stand_down/hedge_mode` · `guard_drop/breach_exceeds_cap`.
   ★`degraded_input` 은 **하지 마라**(유일한 경로가 제3자 API 남용이다).

### ★착수 전 반드시 읽을 것 (직전 회차가 실제로 밟은 것)

1. ★★★**핸드오프의 파일 목록은 조사 범위가 아니라 조사 대상이다** — BL-579 가 지목한 두 파일
   **어디에도 최강 P1 이 없었고** 한 파일은 **P1 0곳**이었다. 그 목록에 갇혀 1차 조사를 낭비했다.
2. ★★★**「고쳤다」와 「그 종류를 다 고쳤다」는 다른 문장이다** — 커밋에 포괄 주장을 썼다가
   G6 가 **같은 결함을 이미 고친 파일 안에서 8곳 더** 찾았다(4곳은 `commit()` 앞이라 **rollback** 까지).
3. ★★★**추론기가 오라클보다 복잡해지면 그건 오라클이 아니다** — zone 추론이 정의마다 **6/13/14**
   를 냈고 「6」은 **내가 박아두고 잊은 40줄 창**의 산물이었다. 추론을 버리고 손으로 동결했다.
4. ★★**게이트를 코드 쓰기 전에 걸어라** — codex G1 2회로 **MAJOR 8건**을 코드 이전에 잡았다.
   그중 하나는 내 테스트가 **실 DB 로 가서 조용히 실패**했을 것이라는 지적이다.
5. ★★**표적 변이를 전체 pytest 와 동시에 돌리지 마라** — 테스트 DB 1벌 + `drop_all`.
   **직전 회차에 내가 밟았고** 그 실행 결과를 폐기했다.
6. ★★**게이트를 파이프에 넣지 마라 · 부분 경로로 재지 마라** — `ruff check src/` 만 돌리고
   「ruff clean」이라고 보고했다가 `final-gates.sh` 에 잡혔다(실제로는 3건 red).
7. ★**소크 종료가 자동 flat 이 아니다」는 무조건 참이 아니다** — 열린 주문이 전부 세션 소유면
   DELETE 만으로 `FLAT=YES` 다. **세션이 소유하지 않은** 것이 있을 때만 수동 정리가 필요하다.

### baseline (2026-08-02 실측 — PR #525 머지 시점)

**BE 3835 passed / 46 skipped** · **FE 1242**(205 파일) · ruff clean · mypy **214** clean ·
마이그레이션 head **`20260801_0001`** ·
가드 밖 mutation **141**(규칙 R1 — 정본은 `backend/tests/common/test_metric_guard_census.py`) ·
`qb_metrics_mutation_failed_total` **0** · `/metrics` **10277 파일 · 635MB**.
★**이 숫자도 대조 대상이다. 첫 step 에서 지금 HEAD 로 다시 재라.**

> ★★**표적 변이는 CONTROL 이 직접 집행한다.** `git checkout` 금지, 문자열 치환 + sha256 복원 대조.
> ★**브랜치 접두사는 `stage/`** (pre-push 훅 화이트리스트). `QB_PRE_PUSH_BYPASS=1` 은 **쓰지 마라**.
> ★**`cd backend` 는 다음 명령까지 이어진다** — 레포 루트 스크립트는 절대경로로.
> ★**pre-commit 이 `ruff format`·`prettier --write` 를 돌린다** — **커밋 후 게이트를 다시 재라**.

## 완료 이력

- 직전 회차 — [`metric-guard-parity`](dev-log/2026-08-02-metric-guard-parity.md)
  (계측 실패가 성공한 발주를 실패로 기록하고 **주문을 하나 더 냈다**. 가드 18곳 · census 159→141)
- 그 앞 — [`context-budget-repair`](dev-log/2026-08-02-context-budget-repair.md)
  (문서·계측만. `INDEX.md` **−92.3%** · 자동 로드 고정비 **−42.2%** · 줄길이 게이트 신설.
  ★**착수 전제 3건 반증** — `CONTEXT.md`·`.ai/rules` 는 자동 로드가 아니다)
- 그 앞 — [`canonical-measurement-surface`](dev-log/2026-08-02-canonical-measurement-surface.md)
- 그 앞 — [`divergence-label-split`](dev-log/2026-08-02-divergence-label-split.md)
- 이번 주 완료 스프린트와 이전 회고 — [`dev-log/INDEX.md`](dev-log/INDEX.md)
- 2026-07-26 이전 status 원문 — [`archive/status-history.md`](archive/status-history.md)
- 열린 BL의 현재 상태 — [`backlog.md`](backlog.md) (`scripts/bl-audit.sh`가 정본)
