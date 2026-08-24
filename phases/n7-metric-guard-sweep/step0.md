# Step 0: 「해로운 자리」를 규칙으로 정의하고 census 에 심는다

## 읽어야 할 파일

- **`phases/n7-common.md`** — 이 회차 공통 금지사항·AC 규율. **먼저 읽어라**
- `apps/api/tests/common/test_metric_guard_census.py` — **이번 lane 의 대상.**
  머리 docstring(`:1-24`)이 census 규칙 전문이다. `_FROZEN_CENSUS`(`:50~`) ·
  `_PROTECTED_SITES`(`:656` 부근) · `test_unguarded_mutation_counts_match_the_frozen_census`(`:394`)
- `apps/api/src/common/metrics_multiproc.py:26` — `record_metric_safely` 정의
- `apps/api/src/tasks/live_signal.py:4146-4230` — **해악의 정본 사례** (아래 참조)

## 배경 — [BL-520] 이 무엇인가, 그리고 왜 지금인가

**계약:** 관측 코드는 주문 경로를 **막을 수 없어야 한다.** metric 은 부수효과이지 업무가 아니다.

★★**이 항목의 Trigger 는 「실자금 cutover 전」인데, 2026-08-23 사용자 결정 ⑴ 로 실자금은
안 간다** ⇒ 그 트리거는 **영구히 발화할 수 없다.** 그런데 원장의 상태줄이 스스로 적었다 —
잔여 결함은 **「지금도 데모에서 발화 가능」**하다. **죽은 트리거가 살아 있는 결함을 지키고
있었다.** 이 lane 은 그 격차를 닫는다.

## 착수 전 실측 (2026-08-24 · CONTROL)

`src/tasks` + `src/trading` 에서 **가드 밖 `qb_*` mutation 이 「해로운 try」 안에 있는 자리 = 4건**.
「해로운 try」 = `except` 가 rollback 하거나 실패 카운터를 올리는, 즉 **업무 결과를 보고하는** try.

| # | 자리 | 지금 무슨 일이 나나 | 모양 |
| --- | --- | --- | --- |
| 1 | `src/tasks/live_signal.py:4201` `qb_live_conditional_sweep_filled_total.inc()` | ★**원장이 지목한 그것.** try@4146 의 `except`(@4219)가 `session.rollback()` + `sweep_cancel_failed` 를 올린다 ⇒ **metric 이 죽으면 「체결됨」이 「취소 실패」로 뒤집힌다** | **A** (try 본문) |
| 2 | `src/tasks/trading.py:2216` `qb_exchange_exit_link_unverified_total.inc()` | try@2027 의 `except`(@2295) ⇒ metric 이 죽으면 **청산 스윕 전체가 중단**된다 | **A** (try 본문) |
| 3 | `src/trading/realtime_publisher.py:55` `qb_rt_publish_failed_total.inc()` | **`except` 본문 안**(try@35 · except@52) ⇒ metric 이 죽으면 **핸들러 자신이 던져 예외가 밖으로 샌다** | **B** (except 본문) |
| 4 | `src/trading/webhook.py:176` `qb_webhook_symbol_rejected_total.inc()` | 같은 모양 (try@173 · except@175) | **B** (except 본문) |

★**모양 A 는 「업무 결과가 뒤집힌다」, 모양 B 는 「예외가 밖으로 샌다」.** 둘 다 실재하고
원인이 다르다. Step 1 이 A, Step 2 가 B 를 맡는다.

★**바로 4줄 아래(`live_signal.py:4212`)에 정답이 이미 있다** —
`record_metric_safely(qb_active_orders.dec)`. **같은 블록 안에서** 한쪽은 감싸져 있고 한쪽은 아니다.

**census 현재 값** (`test_metric_guard_census.py:395-396`):
`len(_FROZEN_CENSUS) == 40` · `sum(_FROZEN_CENSUS.values()) == 83` · 6 케이스 전건 green.
위 4건은 census 에 **각각 count 1 인 키**로 들어 있다(`:80` · `:109` · `:117` · `:120`).

## 작업

1. **위 표를 네가 다시 재라.** 줄 번호는 움직인다. ★**다르면 네 값이 맞다** — `summary` 맨 앞에.
2. **「해로운 try」 판정을 census 파일 안에 규칙으로 심는다.** 지금 census 는 「가드 밖인지」만
   알고 **「그 자리가 해로운지」는 모른다**(파일 머리 docstring 이 스스로 그렇게 적어 뒀다).
   그 한 칸을 메운다:
   - 가드 밖 mutation 을 감싸는 **가장 가까운 `ast.Try`** 를 찾는다
   - 그 `except` 본문이 **업무 결과를 보고하는지** 판정한다 (rollback · `*errors_total` · 실패 로깅)
   - 모양 **A**(try 본문) / **B**(except 본문) 를 구분한다
3. 테스트 2건을 추가한다 (이 step 의 산출):
   - **해로운 자리 목록이 위 4건과 일치**한다
   - ★**공허성 방어**: 그 목록이 비면 실패한다 (`_PROTECTED_SITES` 가 `:656` 에서 쓰는 관용구)
4. ★**이 step 은 소스를 안 고친다.** 자를 먼저 만들고 다음 step 에서 고친다.

## Acceptance Criteria

1. `test -f apps/api/tests/common/test_metric_guard_census.py`
2. `cd apps/api && uv run --env-file .env.local pytest tests/common/test_metric_guard_census.py -q`
3. `cd apps/api && test "$(uv run --env-file .env.local pytest tests/common/test_metric_guard_census.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 8`
4. `cd apps/api && test "$(grep -c 'len(_FROZEN_CENSUS) == 40' tests/common/test_metric_guard_census.py)" -ge 1`
5. `git diff --quiet -- apps/api/src`

★**AC 4 는 「아직 안 고쳤다」의 증인이다** — 래칫은 Step 1 부터 움직인다.
★**AC 5 는 이 step 이 소스를 안 건드린다는 계약이다.**

## `summary` 에 반드시 담을 것

- 재측정한 해로운 자리 목록 (위 표와 **다르면 그 차이를 맨 앞에**)
- 「해로운 try」 판정을 어떻게 구현했는지 · **못 잡는 것**
- 4건 각각의 모양(A/B)과 **구체적 해악 한 줄**

## 금지사항

- **`apps/api/src` 를 이 step 에서 고치지 마라** (AC 5 가 집행한다).
- **`_FROZEN_CENSUS` 를 이 step 에서 줄이지 마라** (AC 4 가 집행한다).
- **`apps/api/AGENTS.md` 에 규칙을 등재하지 마라.** 이유: 그 파일은 **모든 lane 의 프롬프트에
  주입되는 가드레일**이라 주행 중에 바뀌면 lane 마다 다른 규칙을 본다. **문안을 `summary` 에
  적어라** — CONTROL 이 통합 PR 에서 올린다.
- **`apps/api/tests/trading/test_no_strenum_value_access.py` 를 만지지 마라** (다른 lane 소유).
- `phases/n7-common.md` 의 공통 금지사항 전부.
- 커밋하지 마라(커밋은 러너 소관).
