# Step 2: [BL-547] 원장 seed 창 watermark 를 남긴다

## 읽어야 할 파일

- `phases/n9-common.md`
- `docs/backlog.md` 의 `### BL-547` 절 — **권장 접근이 이 step 의 설계다**
- `apps/api/src/tasks/live_signal.py` — 대상. 아래 심볼로 찾아라(줄 번호는 낡았다):
  - `_POSITION_EPOCH_KEY` · `_DIRECTION_MISMATCH_KEY` · `_LEDGER_SHADOW_KEY` — **따라야 할 marker 관용구**
  - `_LedgerGapSeed` · `_ledger_gap_seed` · `_LEDGER_GAP_SEED_NONE` — seed 자료형과 생산자
  - `_probe_gap_resync_state` — seed 를 **공백 tick 에만** 계산하는 그 자리
  - `sanitized_report` 를 만드는 자리 — marker 를 JSONB 에 얹는 관용구
- `apps/api/src/trading/models.py` 의 `last_strategy_state_report` 필드 정의

## 배경 (결함)

`ledger_seed` 는 공백 재동기 tick **한 번만** 계산된다. 다음 tick 은 공백이 아니므로 원장을 읽지
않는다. 재생이 그 진입을 스스로 다시 만들지 못하면 엔진은 다시 flat 이 되고, 발산은
`exchange_only` 로 분류돼 **counter 만 올리고 세션을 죽이지 않는다** — 시끄러운 사망이 한 tick 뒤
**조용한 고아**로 바뀐다. 트리거는 2026-08-11 에 도래했다
(`qb_live_position_divergence_total{category="exchange_only"}` = 3.0 실측).

## 작업 — 이 step 은 **기록**만 한다 (재도출은 step 3)

1. 모듈 상수 `_LEDGER_SEED_SINCE_KEY = "_qb_ledger_seed_since"` 를 추가한다.
   자리·주석 형식은 `_POSITION_EPOCH_KEY` 옆을 따른다.
2. seed 가 **`outcome="seedable"`** 로 산출된 tick 에, 그 창의 시작 시각
   (`_probe_gap_resync_state` 가 `list_fills_since(since=...)` 에 넘긴 값)을
   `sanitized_report[_LEDGER_SEED_SINCE_KEY]` 에 **aware UTC isoformat 문자열**로 남긴다.
   형식은 `_POSITION_EPOCH_KEY` 와 **같아야 한다**.
3. 읽기 헬퍼를 하나 둔다 — 이전 리포트에서 marker 를 파싱해 `datetime | None` 을 낸다.
   **파싱 실패·타입 불일치는 `None`**(= marker 없음)으로 떨어뜨린다. 이유: 이 값은 JSONB 라
   어떤 문자열이든 들어올 수 있고, 여기서 예외를 던지면 **평가 tick 전체가 죽는다.**

## 벗어나면 안 되는 계약

- **마이그레이션 0.** 새 컬럼도 새 저장소도 만들지 마라 — `last_strategy_state_report` 는 이미
  매 tick upsert 된다. 이유: 이 결함은 아직 **실측된 적 없는 이론적 경로**이고, 측정되지 않은
  필요 위에 상태 저장소를 짓지 않는다는 것이 이 항목의 프레임이다([BL-541] 과 같은 계열).
- **엔진 산출 키와 이름을 겹치게 두지 마라.** 밑줄 접두어 `_qb_` 가 「엔진 산출물이 아님」 표시다.
- **판정은 바꾸지 마라.** 이 step 은 marker 를 **쓰기만** 한다. 아무 판정도 이 값을 아직 읽지 않는다.

## 테스트

`apps/api/tests/tasks/` 에 **테스트 이름에 `ledger_seed_watermark` 를 포함**해 2개 이상 만든다
(AC 가 `-k 'ledger_seed_watermark'` 로 센다):

1. `outcome="seedable"` 인 tick 이 marker 를 리포트에 남긴다 — 값이 aware UTC isoformat 이다
2. `outcome` 이 seedable 이 아닌 tick 은 marker 를 **남기지 않는다**(음성 대조)

## Acceptance Criteria

- `test "$(grep -c '_qb_ledger_seed_since' apps/api/src/tasks/live_signal.py)" -ge 2`
- `cd apps/api && uv run --env-file .env.local pytest tests/tasks -q -k 'seed or watermark or gap'`
- `-k 'ledger_seed_watermark'` 로 수집되는 테스트 ≥2
- `cd apps/api && uv run ruff check src/tasks/live_signal.py`

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. **step 1 이 세운 metric 가드가 여전히 통과하는지 확인해라** —
   `cd apps/api && uv run --env-file .env.local pytest tests/common/test_metric_safety_guard.py -q`.
   새 코드에 raw metric 을 넣었다면 그 가드가 red 가 된다.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **alembic migration 을 만들지 마라. 이유:** 이 설계의 전제가 「마이그레이션 0」이다. 새 컬럼이
  필요하다고 판단되면 설계가 틀린 것이니 `blocked` 로 세워라.
- **판정 로직(정렬·발산 분류·킬 조건)을 이 step 에서 건드리지 마라. 이유:** 기록과 판정을 한 step 에
  섞으면 회귀가 났을 때 어느 쪽이 원인인지 못 가른다. 판정은 step 3 이다.
- 커밋하지 마라(커밋은 러너 소관).
