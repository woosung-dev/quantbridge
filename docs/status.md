# QuantBridge — Status

> **업데이트:** 2026-08-02
> **활성 Sprint:** 없음. 다음 작업은 아래 「다음 스프린트」 블록만 읽는다.
> **준비 브랜치:** `stage/metric-guard-parity` (PR 미생성 — 사용자 승인 대기)
> **최근 머지:** `docs/status-post-merge-sync` → `main@6ee0b2c7` (PR #521, 2026-08-02)

---

## 🎯 다음 스프린트 — **미지정**

> ★**직전 회차(`metric-guard-parity`)가 아직 머지되지 않았다.** 다음 회차 지정은 그 PR 이
> 머지된 뒤에 한다 — 머지 전에 지정하면 「PR 준비 중인 브랜치를 가리키는 다음 스프린트」가
> 되어 PR #521 이 고친 바로 그 표류가 재발한다.
>
> **지금 할 일 = `stage/metric-guard-parity` PR 생성·머지.**
> 회고 = [`dev-log/2026-08-02-metric-guard-parity.md`](dev-log/2026-08-02-metric-guard-parity.md).

### 머지 후 다음 회차 후보 (우선순위 순)

1. ★**[BL-580] 계측 가드 잔여** — 이번 회차가 18곳을 감쌌고 **141곳이 남았다.** 그중
   `trading.py:908/931/1093` · `router.py:376` 은 raw `qb_active_orders.dec()` 이지만
   **거절/취소 확정 뒤라 실패로 계상하는 except 가 없다**(그래서 이번 스코프에서 뺐다).
   ★**승격 규칙이 사전등록돼 있다** — `qb_metrics_mutation_failed_total` 의 **창 차분이
   0 을 벗어나는 순간** 즉시 승격(절대값 아님, `CounterBasis.delta` 로만 읽는다).
2. **[BL-576] 잔여 3 series 프로덕션 확인** — 이번에 `exchange_divergence` 를 유도로 확인해
   **2 → 3/6** 이 됐다. 남은 것은 `stand_down/hedge_mode`(계정 position mode 전환 필요) ·
   `guard_drop/breach_exceeds_cap`(확률적). ★`degraded_input` 은 **제3자 API 남용 없이는
   유도 불가**라 제외했다 — 자연 발화를 기다리거나 MITM 하네스가 필요하다.
3. **[BL-581] `/metrics` 영구 누적** — **10277 파일 · 635MB · distinct PID 1968**.
   ★**counter 파일 삭제 금지** — `entry_completeness.py` 가 재기동 생존을 전제로 창 차분을 잰다.
4. **[BL-574] · [BL-578]** — 여전히 **측정 완료 · 수리 보류**.

### ★착수 전 반드시 읽을 것 (이번 회차가 실제로 밟은 것)

1. ★★★**핸드오프의 파일 목록은 조사 범위가 아니라 조사 대상이다** — [BL-579] 가 지목한 두 파일
   어디에도 최강 P1 이 없었고, 그중 한 파일은 **P1 이 0곳**이었다. 내 1차 조사가 그 목록에
   갇혔다.
2. ★★★**「고쳤다」와 「그 종류를 다 고쳤다」는 다른 문장이다** — 커밋 메시지에 포괄 주장을 썼다가
   G6 가 **같은 결함이 내가 이미 고친 파일 안에 8곳 더** 있음을 보였다(4곳은 `commit()` 앞이라
   **더 나쁘다** — 계측 예외가 terminal DB 전이를 rollback 한다).
3. ★★★**추론기가 오라클보다 복잡해지면 그건 오라클이 아니다** — 「머니-패스 zone」을 AST 로
   추론하려다 정의를 바꿀 때마다 **6/13/14** 를 얻었다. 그중 「6」은 **내가 프로토타입에 박아둔
   임의의 40줄 창**이 만든 값이었다. **추론을 버리고 손으로 동결**했다.
4. ★★**게이트는 코드 쓰기 전에 걸어라** — codex G1 을 2회 돌려 **MAJOR 8건**을 코드 이전에 잡았다.
   그중 하나는 내 고장 주입 테스트가 **실 DB 로 가서 조용히 실패**했을 것이라는 지적이었다.
5. ★★**표적 변이를 전체 pytest 와 동시에 돌리지 마라** — 테스트 DB 는 `quantbridge_test` 하나이고
   세션 픽스처가 `drop_all + create_all` 을 돈다. **이번에 내가 밟았고** 그 실행 결과를 폐기했다.
6. ★**소크 종료가 자동 flat 이 아니다」는 무조건 참이 아니다** — 이번엔 세션 DELETE 직후
   `FLAT=YES` 였다(열린 주문이 **전부 세션 소유 조건부 진입**이라 비활성화가 취소했다).
   그 함정은 **세션이 소유하지 않은 포지션·주문이 있을 때** 성립한다.

### baseline (2026-08-02 실측 — `stage/metric-guard-parity` 종료 시점)

**BE 3835 passed / 46 skipped**(착수 3820 대비 **+15**) · **FE 1242**(205 파일, **+0**) ·
ruff clean · mypy **214** clean ·
마이그레이션 head **`20260801_0001`**(이번 회차 **+0**) ·
가드 밖 mutation **141**(착수 159, 규칙 R1) · `qb_metrics_mutation_failed_total` **0**.
★`scripts/bl-audit.sh` · `docs-audit.sh` 는 **PR 전 재실행 의무**(BL 3건 신설분 반영).

## 완료 이력

- 직전 회차 — [`metric-guard-parity`](dev-log/2026-08-02-metric-guard-parity.md) (PR 준비 중)
- 그 앞 — [`canonical-measurement-surface`](dev-log/2026-08-02-canonical-measurement-surface.md)
- 그 앞 — [`divergence-label-split`](dev-log/2026-08-02-divergence-label-split.md)
- 이번 주 완료 스프린트와 이전 회고 — [`dev-log/INDEX.md`](dev-log/INDEX.md)
- 2026-07-26 이전 status 원문 — [`archive/status-history.md`](archive/status-history.md)
- 열린 BL의 현재 상태 — [`backlog.md`](backlog.md) (`scripts/bl-audit.sh`가 정본)
