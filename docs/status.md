# QuantBridge — Status

> **업데이트:** 2026-08-03
> **활성 Sprint:** 없음. 다음 작업은 아래 「다음 스프린트」 블록만 읽는다.
> **준비 브랜치:** `stage/metric-guard-residual` (커밋 완료 · PR 미생성)
> **최근 머지:** `stage/metric-guard-parity` → `main` (PR #525, 2026-08-02)

---

## 🎯 다음 스프린트 — **gate-trustworthiness** (게이트가 통과했다는 말을 믿을 수 있게 만든다)

> ★**이것이 다음 세션의 유일한 진입점이다.** 별도 킥오프 파일을 만들지 않는다.
> 시작 방법: **"다음 스프린트 진행해줘"**. `CONTEXT.md` + 본 파일을 읽고 시작한다.
> ★**`AGENTS.md` 는 읽지 마라 — 자동 로드된다**(`CLAUDE.md` 가 `@AGENTS.md` 하나만 import 한다).
> ★**`CONTEXT.md` 는 반대다 — 자동 로드가 아니라서 읽어야 들어온다.** `.ai/rules/*.md` 도 자동 로드가 아니다.
> ★**`docs/dev-log/INDEX.md` 를 통째로 grep 하지 마라** — `## 최근 12회차` 상단만 읽는다.

**한 줄.** 직전 회차가 부수적으로 **BE 스위트가 실행 순서에 따라 red/green 이 바뀐다**는 것을
기존 테스트로 재현 확정했다([BL-583]). 이 레포는 BE pytest 수치를 baseline 대조와 판정 근거로
쓰는데, **그 수치가 운에 의존하면 「게이트 통과」가 증거가 아니다.** 먼저 이것을 고친다.

### 첫 step

1. **baseline 재측정** (`global.md` §7.1). 대조값은 아래 블록.
   ★**두 번 재라 — `-p no:randomly` 로 한 번, 기본(랜덤) 순서로 한 번.** 두 값이 다르면
   그 자체가 [BL-583] 의 현재 크기다.
2. **[BL-583] 뿌리를 규명한다.** 재현은 이미 있다(백로그에 명령 그대로). 배제된 가설 2개도 적어 뒀다 —
   **거기서부터 시작해라.** ★수리보다 **크기 측정**이 먼저다: 순서를 바꿔가며 몇 개 테스트가
   흔들리는지 세라(`-p no:randomly` vs 여러 시드).
3. **[BL-580] 잔여 129곳 중 아직 코드 독해인 것** — `order_service.py` 10곳(blast radius 0) ·
   `trading.py` closed_pnl 7곳(`already_synced` 수렴). ★직전 회차에 명시 4곳이 **전건 반증**됐다.
   같은 방법(고장 주입 + 사이트별 postcondition)으로 재라.
4. **[BL-582] 반증된 2종** — 코퍼스에 발현 전략이 없어 프로덕션 유도는 전략 등록이 선행돼야 한다.
   급하지 않다. ★`degraded_input` 은 **영구 제외**(제3자 API 남용).

### ★착수 전 반드시 읽을 것 (직전 회차가 실제로 밟은 것)

1. ★★★**「~라서 안전하다」는 산문은 조사 대상이다** — BL-580 이 4곳을 「실패로 계상하는 `except`
   가 없다」로 뺐는데 고장 주입해 보니 **4곳 전건이 H1**(성공을 실패로 보고)이었다.
   **판정 9곳 중 「가드 없이 유지」가 0곳**이다.
2. ★★★**미검증 구간이 「불가능」으로 기록된다** — BL-582 의 「도달 불가 7종」 중 2종은
   **게이트 테스트가 스냅샷을 손조립해서** 엔진 쪽을 한 번도 안 본 결과였다. 엔진을 직접 돌리니
   값이 나왔다. **「테스트가 없다」와 「일어날 수 없다」를 같은 칸에 적지 마라.**
3. ★★★**내 사전등록 변이 하나가 판별력 0 이었다**(M2). 「폭파 대상이 안 던지게 바꾼다」는
   코드가 정상 동작하므로 **green** 이 난다. 실행 전에 발견해 역방향(프로덕션 언랩)으로 교체했다.
   **변이를 적을 때 「이게 red 를 내는 이유」를 한 줄 같이 적어라.**
4. ★★**기계적 스윕은 방향이 있다** — 「가드 옆 raw」 규칙이 `_count_safely` **앞**만 봐서
   **뒤**에 있는 2곳을 놓쳤다. 수리 중 테스트 red 로 발견했다. 규칙의 맹점을 규칙과 함께 적어라.
5. ★★**게이트를 코드 쓰기 전에 걸어라** — codex G1 1회로 **BLOCKING 3 + MAJOR 4**, 그중
   **3건이 설계를 교체**했다. 코드를 쓴 뒤였다면 전부 재작업이었다.
6. ★**`awk length()` 는 바이트를 센다** — 줄길이 상한은 **문자**로 재라(Python `len()`).
   바이트로 재면 한글 줄이 전부 「초과」로 보인다.
7. ★★**표적 변이를 전체 pytest 와 동시에 돌리지 마라** — 테스트 DB 1벌 + `drop_all`.
8. ★★**게이트를 파이프에 넣지 마라 · 부분 경로로 재지 마라**(`ruff check src/` 만 돌리면 놓친다).

### baseline (2026-08-03 실측 — `stage/metric-guard-residual` 커밋 후)

**BE 3848 passed / 46 skipped** · **FE 1242**(205 파일) · ruff clean · mypy **214** clean ·
마이그레이션 head **`20260801_0001`** ·
가드 밖 mutation **129**(규칙 R1 — 정본은 `backend/tests/common/test_metric_guard_census.py`,
45키 141 → **43키 129**) · `/metrics` **10524 파일 · 650MB**(BL-581 Trigger 20000 미달).
★**이 숫자도 대조 대상이다. 첫 step 에서 지금 HEAD 로 다시 재라.**
★**BE 수치는 [BL-583] 때문에 순서 의존일 수 있다** — 위 값은 기본(랜덤) 순서 1회 실행이다.

> ★★**표적 변이는 CONTROL 이 직접 집행한다.** `git checkout` 금지, 문자열 치환 + sha256 복원 대조.
> ★**브랜치 접두사는 `stage/`** (pre-push 훅 화이트리스트). `QB_PRE_PUSH_BYPASS=1` 은 **쓰지 마라**.
> ★**`cd backend` 는 다음 명령까지 이어진다** — 레포 루트 스크립트는 절대경로로.
> ★**pre-commit 이 `ruff format`·`prettier --write` 를 돌린다** — **커밋 후 게이트를 다시 재라**.

## 완료 이력

- 직전 회차 — [`metric-guard-residual`](dev-log/2026-08-03-metric-guard-residual.md)
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
