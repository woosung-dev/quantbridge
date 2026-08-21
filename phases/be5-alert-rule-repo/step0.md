# Step 0: alert-rule-repo

## 읽어야 할 파일

- `apps/api/src/trading/repositories/alert_rule_repository.py` (75줄) — **이번 테스트의 대상**
- `apps/api/src/trading/models.py` — `AlertRule`(732줄~) · `AlertRuleType`(94) · `AlertChannel`(101) ·
  `LiveSignalSession`. ★**`AlertRule` 의 필드와 `__table_args__` 의 CHECK/Index 는 그 파일을 열어 확인해라**
- `apps/api/tests/trading/test_alert_rule_repository.py` — ★★**이름은 같지만 이 클래스를 안 쓴다**(아래 배경).
  **다만 시딩 관용구**(`_seed_user_strategy_account`)는 여기서 베껴라. **이 파일을 수정하지 마라**
- `apps/api/tests/trading/conftest.py` — `user` · `strategy` 픽스처
- `apps/api/tests/trading/test_parity_repository.py` — 실DB repository 테스트의 시딩 선례

## 배경

★★**착수 전 CONTROL 이 전량 스위트 커버리지로 쟀다 (2026-08-21 · `concurrency=greenlet,thread` 교정본):**

```
src/trading/repositories/alert_rule_repository.py   33 stmt   11 missed   67%   20, 23, 35-37, 40-45, 48-54, 69-75
```

| 메서드                                 | 상태                                              |
| -------------------------------------- | ------------------------------------------------- |
| `list_by_session`                      | ✅ 커버됨                                         |
| `list_active_loss_rules_with_sessions` | ✅ 커버됨(`tests/tasks/test_alert_rules_task.py`) |
| `commit` / `rollback`                  | ❌ 20 / 23                                        |
| `create`                               | ❌ 35-37                                          |
| `get_active_by_id`                     | ❌ 40-45                                          |
| `deactivate`                           | ❌ 48-54                                          |
| `find_active_watchdog_rules_for`       | ❌ 69-75                                          |

★★★**「기존 테스트가 있다」가 두 겹으로 거짓이었다 — CONTROL 이 코드로 대조했다:**

1. `tests/trading/test_alert_rule_repository.py` 는 **이름만 같다.** import 는
   `LiveSignalSessionRepository`·`OrderRepository` 뿐이고 `AlertRuleRepository` 를 **한 번도 안 쓴다.**
2. `tests/tasks/test_alert_rules_task.py:116` 과 `tests/trading/test_fetch_order_status_task.py:451,502` 는
   `monkeypatch.setattr(..., "AlertRuleRepository", _Rules)` 로 **이 클래스를 페이크로 치환**한다 —
   **실행 우회는 커버가 아니다.**

★**이 저장소의 판정은 전부 SQL `WHERE` 절 안에 있다** — 파이썬 분기는 `result.rowcount or 0` 하나뿐이다.
그래서 **fake session 으로는 판별력이 0** 이고, 이 lane 만 **실 DB**(`db_session`)를 쓴다.

★**착수 전 CONTROL 실측 — 구조 (모듈을 직접 읽어 확인했다):**

| 메서드                                       | 판정                                                                                                           |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `list_by_session(session_id)`                | `session_id` 일치 **+ `is_active == True`** + `created_at.desc()`                                              |
| `create(rule)`                               | `session.add` → `flush` → 그 rule 반환 (**commit 안 함**)                                                      |
| `get_active_by_id(rule_id)`                  | `id` 일치 **+ `is_active == True`** → `scalar_one_or_none()`                                                   |
| `deactivate(rule_id)`                        | `update(...).where(id).where(is_active == True).values(is_active=False, updated_at=now)` → **`rowcount or 0`** |
| `list_active_loss_rules_with_sessions`       | join + **3중 필터**: rule active · `rule_type == loss_limit` · **`LiveSignalSession.is_active == True`**       |
| `find_active_watchdog_rules_for(session_id)` | `session_id` + `rule_type == watchdog` + `is_active == True`                                                   |
| `commit` / `rollback`                        | 세션에 그대로 위임                                                                                             |

★**`AlertRule` 에는 CHECK 제약이 있다** — `loss_limit` 이면 `threshold_percent` **필수**,
`watchdog` 이면 **NULL 이어야 한다**(`ck_alert_rules_type_threshold`). 시딩할 때 이것을 지켜라.
★그리고 `uq_alert_rules_active_type` 인덱스가 있다 — **조건을 파일에서 직접 확인**하고 시드를 맞춰라.

## 작업

`apps/api/tests/trading/test_alert_rule_repository_contract.py` **하나**를 신설한다.
`db_session` + `tests/trading/conftest.py` 의 `user`·`strategy` 픽스처를 쓴다.
`ExchangeAccount` → `LiveSignalSession` → `AlertRule` 을 직접 심어라.

### 최소한 이 여덟을 덮어라 (케이스 ≥8)

1. ★★**`create` 후 `flush` 로 id 가 생기고, `commit` 없이도 같은 세션에서 조회된다** —
   반환된 객체가 넣은 그 rule 인지(동일성) 재라
2. ★★★**`get_active_by_id` 가 비활성 규칙을 안 준다** — 활성/비활성 둘을 심고, 활성은 나오고
   **비활성은 `None`** 이다. ★**이것이 `is_active == True` 필터를 재는 유일한 케이스다**
3. ★★**`deactivate` 가 1을 반환하고 실제로 비활성이 된다** — 그 뒤 `get_active_by_id` 가 `None` 이다
4. ★★★**이미 비활성인 규칙을 `deactivate` 하면 `0` 이다** — `where(is_active == True)` 가 없으면 1이 나온다.
   ★**이것이 `rowcount or 0` 과 그 필터를 함께 재는 축이다**
5. ★★**없는 id 를 `deactivate` 하면 `0`** — 예외가 아니다
6. ★★★**`find_active_watchdog_rules_for` 의 3중 필터** — 같은 세션에 **watchdog 활성 · watchdog 비활성 ·
   loss_limit 활성**을 심고 **watchdog 활성 하나만** 나오는지 재라. **다른 세션의 watchdog 활성**도 심어
   안 나오는지 재라(총 4행 중 1행). ★세 필터 중 어느 하나를 지워도 red 가 나게 배치해라
7. ★★**`list_by_session` 의 정렬과 필터** — 같은 세션에 `created_at` 이 다른 활성 2행 + 비활성 1행을 심고
   **활성 2행이 최신 우선**으로 나오는지 재라. ★`created_at` 을 **명시로 다르게** 심어라
   (같은 값이면 정렬 변이가 안 잡힌다)
8. ★**`commit` / `rollback` 위임** — `create` 후 `rollback` 하면 그 행이 사라지고, `commit` 하면 남는다.
   ★**루트 conftest 의 `db_session` 은 savepoint 격리라 바깥 트랜잭션이 따로 있다** —
   **관측한 것을 박아라.** 예상과 다르면 `summary` 에 적고 그 층에서 잴 수 있는 것만 재라
9. (선택) **`list_active_loss_rules_with_sessions` 의 세션-활성 필터** — 이미 커버된 메서드지만
   **`LiveSignalSession.is_active == False` 인 세션의 loss_limit 규칙이 빠지는지**는 확인해 두면 값이 있다.
   기존 테스트와 겹치면 `summary` 에 적고 건너뛰어라

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/trading/test_alert_rule_repository_contract.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/trading/test_alert_rule_repository_contract.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 8
cd apps/api && uv run --env-file .env.local pytest tests/trading/test_alert_rule_repository.py tests/trading/test_alert_rule_service.py tests/trading/test_alert_rules_api.py -q
cd apps/api && uv run ruff check tests/trading/test_alert_rule_repository_contract.py && uv run ruff format --check tests/trading/test_alert_rule_repository_contract.py
```

★2번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 **rc=4**(CONTROL 실측 2026-08-21).
★3번째는 인접 회귀다 — `tests/trading` **전량은 넣지 않았다**(느리고 8 lane 에서 곱해진다).
★`--env-file .env.local` 을 빼지 마라 — DB 가드가 rc=3 으로 거부한다. **이 lane 은 실 DB 를 쓴다** —
`TEST_DATABASE_URL` 이 워크트리 슬롯의 `quantbridge_w{N}_test` 를 가리키는지 확인해라.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 케이스 수와 **⑻에서 관측한 savepoint 격리의 실제 동작**을 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- ★**`src/trading/repositories/alert_rule_repository.py` 를 수정하지 마라.** 이유: 이 회차의 계약은
  「테스트만 추가하고 대상 소스는 0줄 변경」이다. 결함을 발견하면 **고치지 말고 `status:"blocked"` +
  `blocked_reason`** 으로 멈춰라
- ★★**`tests/trading/test_alert_rule_repository.py` 를 수정하거나 이름을 바꾸지 마라.** 이유: 이름이
  헷갈리지만 그 파일은 **다른 것을 재고 있고**(`sum_filled_realized_pnl` · 닫힌 세션 창) 이 lane 소유가 아니다.
  새 파일은 `_contract.py` 접미로 간다
- ★★**`AlertRuleRepository` 를 monkeypatch 하지 마라.** 이유: **그것이 기존 테스트들이 한 일이고,
  그래서 이 클래스가 11줄 미커버로 남았다.** 이 lane 은 **진짜 클래스를 진짜 DB 로** 돌리는 것이 목적이다
- ★★**`mise run up|down|migrate|seed` 를 부르지 마라.** 이유: 컨테이너와 앱 DB 는 1벌 공유라 함께 깨진다.
  워크트리의 `TEST_DATABASE_URL` 이 이미 슬롯별 테스트 DB 를 가리킨다
- ★★**`DATABASE_URL` 만 단독으로 주입하지 마라.** 이유: 세션 픽스처의 `drop_all` 이 **개발 DB 를 겨냥**한다.
  `--env-file .env.local` 로 통째 소싱해라
- ★★**`xfail(strict=True)` 를 쓰지 마라. 이유:** 「제품 코드가 지금 틀렸다」를 원장에 박는 주장인데
  **AC·변이·사람 diff 세 층이 전부 통과시킨다**([LESSON-121]). 근거는 `summary` 에 적고 테스트는 지금 동작을 고정해라
- ★**재지 않은 값을 단언하지 마라.** 이유: step 의 산문은 세션에게 AC 와 구별되지 않는다([LESSON-122]).
  `AlertRule` 의 필드·CHECK·인덱스 조건은 **`models.py` 를 열어 확인**하고 써라
- ★**`conftest.py`(루트·`tests/trading/`) · `pyproject.toml` · `shards.json` 무변경**(8 lane 동시 실행 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — 시딩 헬퍼는 이 테스트 파일 안에 둬라(선례에서 **베껴 오되 import 하지 마라**)
- **새 pytest 마커를 쓰지 마라** — `--strict-markers` 라 `pyproject.toml` 을 함께 고쳐야 하고 그것이 공유 파일이다
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
