# Step 3: 자기 변이 검증 + 회귀 — live-signal 세션·이벤트 저장소 + waitlist 저장소

## 읽어야 할 파일

- ★**`apps/api/AGENTS.md`** — FastAPI 3-Layer · Decimal-first · Celery prefork-safe (§2/§3/§9).
  ★그 디렉터리 파일을 열면 자동 로드된다([ADR-027]) — 안 열렸으면 직접 읽어라
- `apps/api/src/trading/repositories/live_signal_session_repository.py` — **이번 회차의 대상**
- `apps/api/src/trading/repositories/live_signal_event_repository.py` — **이번 회차의 대상**
- `apps/api/src/waitlist/repository.py` — **이번 회차의 대상**
- `apps/api/tests/tasks/test_worker_task_lifecycle.py` · `apps/api/tests/trading/test_alert_rule_repository_contract.py`
  — **5차가 남긴 관용구 정본.** 베끼지 말고 열어서 모양을 따라라

## 이 lane 이 만드는 파일

- `apps/api/tests/trading/test_live_signal_repositories.py`
- `apps/api/tests/waitlist/test_waitlist_repository.py`

## 착수 전 실측 (2026-08-22 · CONTROL · `concurrency = greenlet,thread` 교정본)

| 대상 | 커버 | 미커버 | 미커버 줄 |
| --- | --- | --- | --- |
| `live_signal_session_repository.py` | **66.7%** (★AC 기준 **50.9%**) | 29/98 | `43,46-48,90,104,198,203,220,233,240-242,253,269,330-332,340-350` |
| `live_signal_event_repository.py` | **60.3%** (★AC 기준 **58.6%**) | 21/54 | `28,31,34,54-55,57,59,94,99-100,103,106,115,119,125,131,137,196,206,210,220` |
| `src/waitlist/repository.py` | 67.9% (★AC 기준 **60.4%**) | 13/49 | `41,46,55-57,59-61,64,66,71-72,94` |

★★**이 수치는 `[tool.coverage.run]` 에 `concurrency = greenlet,thread` 를 넣고 잰 값이다.**
그 설정이 없으면 SQLAlchemy greenlet 전환 뒤의 줄이 전부 미커버로 나와 **거짓으로 낮게** 나온다
(5차 실측: `outcome_parity_service.py` 80% → 100%). 사전 배치 PR 이 그 설정을 이미 넣었다.

★★★**「전량 스위트」와 「AC 기준」이 다르다 — 네가 넘어야 하는 것은 AC 기준이다.**
AC 는 `tests/trading tests/waitlist` 만 돌린다. 다른 디렉터리의 테스트가 이 모듈을 import 하며 덮던 몫은
그 실행에 **안 들어온다**. 그래서 착수 전 값이 전량 스위트보다 낮다 — 위 표의 「★AC 기준」이
**네 시작점**이고, AC 의 하한은 그 값 위에서 정했다. 두 수치를 섞어 읽지 마라.

## 이 lane 만의 사실

★**이 lane 은 진짜 DB 를 쓴다** — AC 가 `.env.local` 을 통째로 소싱한다

★★**이 lane 은 진짜 DB 를 쓴다.** `apps/api/AGENTS.md` §3 — Repository 계층은
  DB 접근의 유일한 자리이고, 페이크로 갈아끼우면 **재는 것이 없어진다.**
  5차의 `tests/trading/test_alert_rule_repository_contract.py` 가 정본 관용구다 — 열어 봐라.
★★★**5차가 여기서 `blocked` 를 한 번 맞았다** — 워크트리 슬롯의 테스트 DB 가
  **이전 회차가 남긴 낡은 스키마**였다. `drop_all` 이 없는 제약을 DROP 하려다 죽는다.
  그 증상이 보이면 **소스를 고치지 말고** `blocked` 로 남겨라 — 환경 문제다.
★★**「실행 우회는 커버가 아니다」** — 5차에서 `AlertRuleRepository` 의 11줄이 미커버였던
  이유는 두 테스트가 **클래스를 통째로 페이크로 갈아끼웠기** 때문이다. 이름이 맞는
  테스트 파일이 있다고 그 줄이 돌았다는 뜻이 아니다.
★`live_signal_event_repository.py` 는 54 stmt 중 21 이 미커버다 — **작은 파일이라
  케이스 몇 개로 크게 오른다.** 거기부터 시작하는 편이 빠르다.

## 작업

**네가 쓴 테스트가 실제로 무엇을 잡는지 스스로 증명한다.**

1. **변이를 심어라 (최소 3건).** 대상 소스에 **값·분기 수준**의 변이를 하나씩 넣고 red 를
   확인한 뒤 **원상 복구**한다. 예: 비교 연산자 방향 · 기본값 상수 · `and`↔`or` ·
   조기 return 추가. ★**타입 힌트 변경은 변이가 아니다**(런타임이 안 바뀐다).
   ★복구는 마지막 AC 의 `git diff --quiet` 가 강제한다
2. **red 가 안 난 변이가 있으면 그 자리를 덮는 케이스를 추가**한다
3. **회귀** — AC 가 `tests/trading tests/waitlist` 전량을 돌린다. ruff check·format 도 AC 에 있다

## `summary` 에 반드시 담을 것

- 심은 변이 3건 각각의 **위치 · 무엇을 바꿨나 · red 였나** (표로)
- red 가 안 났던 변이가 있다면 **무엇을 추가해 잡았는지**
- 최종 커버리지 수치

## Acceptance Criteria

1. `test -f apps/api/tests/trading/test_live_signal_repositories.py -a -f apps/api/tests/waitlist/test_waitlist_repository.py`
2. `cd apps/api && uv run --env-file .env.local pytest tests/trading tests/waitlist -q --cov=src/trading/repositories --cov=src/waitlist --cov-report=json:.coverage.harness.json`
3. `python3 tools/harness/assert_be.py apps/api/.coverage.harness.json --target src/trading/repositories/live_signal_session_repository.py --min-cov 82 --target src/trading/repositories/live_signal_event_repository.py --min-cov 84 --target src/waitlist/repository.py --min-cov 85`
4. `cd apps/api && test "$(uv run --env-file .env.local pytest tests/trading/test_live_signal_repositories.py tests/waitlist/test_waitlist_repository.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 22`
5. `git diff --quiet -- apps/api/src/trading/repositories/live_signal_session_repository.py apps/api/src/trading/repositories/live_signal_event_repository.py apps/api/src/waitlist/repository.py`
6. `cd apps/api && uv run ruff check tests/trading/test_live_signal_repositories.py tests/waitlist/test_waitlist_repository.py`
7. `cd apps/api && uv run ruff format --check tests/trading/test_live_signal_repositories.py tests/waitlist/test_waitlist_repository.py`

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `apps/api/AGENTS.md` 의 필수 항목(3-Layer 경계 · Decimal · 한국어 헤더 주석)을 지켰는지 확인한다.
3. 사람 개입이 필요하면 `status:"blocked"` + `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **대상 소스를 한 줄도 고치지 마라.** 이유: 이 lane 은 커버리지 lane 이다.
  ★소스에 결함이 보이면 **고치지 말고 `summary` 에 적어라** — 5차에서 그렇게 [BL-819] 를 잡았다.
- **`.skip`·`xfail` 로 통과시키지 마라.** ★`xfail(strict=True)` 는 「제품 코드가 틀렸다」를
  원장에 박는 주장이다 — 코드 대조 없이 쓰면 AC·변이·diff 가 전부 통과시킨다(1차 실증).
- **celery worker·웹소켓·거래소에 실제로 붙지 마라.** 이유: AC 가 외부 상태에 의존하면
  간헐 red 가 되고, 러너는 그것을 실패로 판정한다.
- **`docs/**` 를 만지지 마라.** 이유: 12 lane 이 같은 원장 파일을 고치면 병합이 통째로 충돌한다.
- **`mise run up/down/migrate/seed` 를 하지 마라.** 이유: 컨테이너·앱 DB 는 1벌 공유라 함께 깨진다.
- 커밋하지 마라(커밋은 러너 소관).
