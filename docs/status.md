# QuantBridge — Status

> **업데이트:** 2026-08-02
> **활성 Sprint:** 없음. 다음 작업은 아래 「다음 스프린트」 블록만 읽는다.
> **준비 브랜치:** 없음
> **최근 머지:** `stage/canonical-measurement-surface` → `main@b476327e` (PR #520, 2026-08-02)

---

## 🎯 다음 스프린트 — **metric-guard-parity** (계측 실패가 머니-패스를 오기록하는 자리를 닫는다)

> ★**이것이 다음 세션의 유일한 진입점이다.** 별도 킥오프 파일을 만들지 않는다.
> 시작 방법: **"다음 스프린트 진행해줘"**. `CONTEXT.md` + `AGENTS.md` + 본 파일을 읽고 시작한다.

**한 줄.** 직전 회차가 「손 SQL 을 쓸 이유」를 없앴다. 그 과정에서 **계측 자체가 머니-패스를
오기록할 수 있는 자리 127곳**이 드러났고, 그중 **2곳은 거래소 쓰기 성공 직후**다 —
계측이 던지면 **성공한 발주가 「실패」로 기록**된다.

### 왜 이것이 최대 리스크인가 (근거는 `roadmap.md` 「현재 최대 리스크」 블록)

| 축                              | 실측                                                              |
| ------------------------------- | ----------------------------------------------------------------- |
| 가드 밖 mutation **코드 표면**  | **127곳** (`record_metric_safely` / `_count_safely` 밖)           |
| 그중 **머니-패스 직후**         | **6곳**                                                           |
| 그중 **P1** (성공→실패 오기록)  | **2곳**                                                           |
| **관측된 발생**                 | **0회** — 단 가드 밖은 자기 실패를 셀 counter 가 없다             |
| 렌더 경로 실패 이력             | `qb_metrics_render_fallback_total` = **2** (mmap 계층 무결 아님)  |
| `/metrics` 볼륨                 | **9423 파일 · 582MB**, counter/histogram 은 **영구 누적**         |

★**「관측 발생 0회」를 「위험 없음」으로 읽지 마라** — 가드된 지점의 실패가 0회라는 뜻이다.
정본 = [BL-579](backlog.md#bl-579).

### 첫 step

1. **baseline 재측정** (`global.md` §7.1). 대조값은 아래 블록.
2. **[BL-579] P1 2곳부터** — `_count_safely` 를 `tasks/trading.py`·`services/order_service.py` 로
   끌어올린다. ★**전 127곳 일괄 변경 금지** — 크기 대비 회귀 위험이 크고, 이 레포는
   「스펙 밖 일괄 리팩토링」으로 검증 범위를 흐린 이력이 있다.
3. **[BL-576] 잔여 3 event 프로덕션 확인** — 직전 창(37분)에서 `exchange_divergence` ·
   `degraded_input` · `guard_drop` 은 **한 번도 발화하지 않았다.** 5 중 2만 확인된 상태다.
   ★**기다리지 말고 발화 조건을 만들어라** — 직전 회차가 `stand_down` 을 그렇게 유도했다.
4. **`/metrics` 영구 누적** — 9423 파일이 mmap 실패 확률의 분모를 키운다. 크기를 재고 판단해라.

### ★착수 전 반드시 읽을 것

1. ★★★**「도구로 막는다」고 선언해도 습관은 안 바뀐다** — 직전 회차 CONTROL 이 그 선언을 한
   회차 안에서 **손 술어를 다시 썼고**(psql 안 retCode 정규식) **남의 축 숫자를 인용했다**(34 vs 33).
   **선언 말고 도구를 써라.**
2. ★★**신규 counter 를 프로덕션에서 증명하려면 미리 실체화해야 한다** — 라벨 있는 counter 는
   첫 발화 전까지 series 가 없어 **차분으로 읽을 수 없다**. `_touch_safely` 관용구.
3. ★★**소크 종료가 자동 flat 이 아니다** — 세션 DELETE 204 뒤에도 포지션·resting 이 남는다.
   **주문 취소 → 포지션 청산**을 따로 해라. 착수 시점 flat 확인도 의무다(직전 회차에 고아 포지션이 있었다).
4. ★**`other` reason 5종은 구조적 도달 불가** — 「13 series 존재」를 기능 증거로 인용하지 마라.
   **증거는 오직 차분이다.**
5. ★**[BL-574]·[BL-578] 수리는 여전히 보류**다. 재는 방법만 바뀌었다(아래 명령).

### 손 SQL 대신 쓸 것 (직전 회차 산출물)

```bash
cd backend && set -a; . ./.env.local; set +a
uv run python scripts/entry_completeness_report.py --question <name> --since <ISO> [--until <ISO>]
```

`<name>` ∈ `conditional_population` · `resting_truncation_risk` · `entry_race_rejections`.
**exit 0 = 미발화(보류 유지) · 3 = 발화(BL 되살린다) · 1 = 판정 불가.**
판정 불가 사유 3종 = **절단** · **표본 없음** · **출처 미상 거절 존재**(retCode 를 못 읽어
C1 인지 아닌지 모르는 행이 있으면 「아니다」로 수렴시키지 않는다).
★매 실행이 **정본 술어와 함정**을 함께 인쇄하고, **양성 대조**(창이 비지 않았다는 증거)를
항상 같이 낸다. ★그 대조는 「문턱-1」이 **아니다** — resting 은 문턱 `> 20` 에 대조 `> 1`,
C1 은 문턱 `>= 3` 에 대조 `>= 1` 이다. 출력이 **실제로 센 술어를 글자로** 말한다.
★낡은 롤링 창을 줘도 **기준선 배제를 자동 적용**하고 그 사실을 출력한다(§G1.1 규율 6).

### 사전등록 판정 문턱

★★**여기에 판정식을 쓰지 마라.** 정본은
[`reference/operations/workflows/generator-evaluator-pipeline.md` **§G1.1**](reference/operations/workflows/generator-evaluator-pipeline.md).
회차별 인스턴스는 **dev-log** 에 쓴다. 특히 **규율 2b**(판정 없음으로 떨어지는 조합이 없는가)와
**규율 3**(문턱에 숫자가 박혀 있는가)을 먼저 대조해라 — 직전 회차에 **내 사전등록 조건 ③이
구조적으로 달성 불가**였고 착수 후에야 드러났다.

### 하지 않는 것

**BL-565**(구조적 측정 불가) · **BL-553 PbR 재시도** · **BL-578 수리** · **BL-574 수리** ·
**C1 시장가 전환**(머니-패스 변경) · **BL-579 전 127곳 일괄 변경**.

### baseline (2026-08-02 실측 — `sprint/canonical-measurement-surface` 종료 시점)

**BE 3820 passed / 46 skipped**(착수 3804 대비 **+16**) · **FE 1242**(205 파일, **+5**) ·
ruff clean · mypy **214** clean ·
마이그레이션 head **`20260801_0001`**(이번 회차 **+0**) ·
`scripts/bl-audit.sh` **exit 0**(active **149** / 전체 **236**) · `scripts/docs-audit.sh` **exit 0**.

★**active 가 149 로 안 변한 이유** — BL-577 Resolved(**−1**) + BL-579 신설(**+1**). 전체는 235→**236**.
★**이 숫자도 대조 대상이다. 첫 step 에서 지금 HEAD 로 다시 재라.**

> ★★**표적 변이는 CONTROL 이 직접 집행한다.** 직전 회차 4종 전건 판별했고 **음성 대조 1종이
> 무효**였다(내 변이가 동치가 아니었다 — 정의만 rename). `git checkout` 금지, 문자열 치환 + sha256.
> ★**게이트를 파이프에 넣지 마라** — 직전 회차에 `pytest | tail` 로 **exit code 가 tail 의 것**이 됐다.
> ★**`cd backend` 는 다음 명령까지 이어진다** — 레포 루트 스크립트는 절대경로로.
> ★**한 파일씩 완결된 상태로 저장해라** — 워커 watchfiles 가 중간 상태를 물어 Traceback 이 났다.
> ★**브랜치 접두사는 `stage/` 다** — pre-push 훅이 `stage|feat|fix|chore|docs|test|refactor|hotfix`
> 화이트리스트를 강제한다(ADR-017 · BL-555). `sprint/` 로 만들면 push 가 거부된다.
> `QB_PRE_PUSH_BYPASS=1` 은 있지만 **쓰지 마라** — 가드를 뚫는 것이 이 레포가 반복해 당한 방식이다.
> ★**`herdr agent prompt` 는 붙여넣기만 한다** — `send-keys enter` 후 `agent get` 으로 `working` 확인까지가 발송.

## 완료 이력

- 직전 회차 — [`canonical-measurement-surface`](dev-log/2026-08-02-canonical-measurement-surface.md)
- 그 앞 — [`divergence-label-split`](dev-log/2026-08-02-divergence-label-split.md)
- 이번 주 완료 스프린트와 이전 회고 — [`dev-log/INDEX.md`](dev-log/INDEX.md)
- 2026-07-26 이전 status 원문 — [`archive/status-history.md`](archive/status-history.md)
- 열린 BL의 현재 상태 — [`backlog.md`](backlog.md) (`scripts/bl-audit.sh`가 정본)
