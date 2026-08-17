# 레인 γ 원장 초안 — 오케스트레이터가 `docs/backlog.md` 에 옮긴다

수치는 전부 `C-REPORT.md` 가 정본이다. 여기에 다시 적지 않는다.

---

## 1. [BL-414] 상태줄 교체 (`docs/backlog.md:1809` 구간)

### 지금 (낡음)

```
**상태:** ⏳ 대기 (트리거 미도래) — byBacktest 캐시는 여전히 useLatestStressTest 의 단일 Summary 이고 이력 리스트 화면·페이지 응답 재정의 모두 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
```

### 이렇게 (제안)

```
**상태:** ✅ RESOLVED (2026-08-17 night3 레인 γ) — 백테스트 상세의 스트레스 패널이 이력 표를 갖고 행 선택으로 상세를 바꾼다. `stressTestKeys.byBacktest` 캐시가 단일 Summary → `StressTestListResponse` 로 재정의됐다(원장 권장 접근 그대로). BE 는 `StressTestSummary.headline_metric` 한 필드만 추가 — 목록 API 자체는 이미 있었다. 변이 3/3 red. 미확인 축 2개는 C-REPORT.md 참조(브라우저 실데이터 · authed 캐논).
**트리거 판정:** 도래·소진 — 「스트레스 이력 화면이 디자인 캐논에 추가될 때」가 이 회차에 충족됐다(design-canon rc=0).
```

### ★원장 본문에서 고쳐야 할 것 — 「선행」의 대상

레인 파일은 「페이지 응답이 이미 있으니 원장이 낡았다」고 적었는데 **원장이 옳았다.** 원장의
`**권장 접근:**` 은 BE 엔드포인트가 아니라 **FE React Query 캐시**를 가리킨다. 그 문장은
고칠 것이 없고, 오히려 그대로 이행됐다는 사실을 상태줄에 남기는 것이 맞다.

실제로 「이미 있었다 / 없었다」가 갈린 지점은 따로다.

| 축                                     | 착수 전 실측                                                        |
| -------------------------------------- | ------------------------------------------------------------------- |
| BE 목록 엔드포인트 `GET /stress-tests` | **있었다** (`router.py:102`)                                        |
| BE 목록의 핵심 지표                    | **없었다** — `StressTestSummary` 6필드에 지표 0개 ⇒ 이번에 1개 추가 |
| FE `byBacktest` 캐시 모양              | 단일 `Summary` ⇒ 페이지 응답으로 재정의                             |
| 이력 화면                              | 없었다 ⇒ 신설                                                       |

---

## 2. 신규 [BL-798] 제안 — 목록 질의가 `result` JSONB 를 통째로 읽는다

★**번호 주의.** 프롬프트 정정은 「796 이 아니라 797」이었으나, 레인 α 가 같은 밤에 797 을 썼다
(`8bfed817 wip(web): screen evidence pack … (BL-797)`). 그래서 **798** 로 잡는다.

```
### BL-798

**Title:** `StressTestRepository.list_by_user` 가 목록 응답에 안 쓰는 `result` JSONB 를 전량 읽는다
**Category:** Backend / stress_test 성능
**Priority:** P3
**Trigger:** 한 사용자의 스트레스 실행이 수백 건이 되거나 이력 화면 응답이 눈에 띄게 느려질 때
**Est:** S (1-2h)
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-17 [BL-414] 회차에 확인. `select(StressTest)` 가 전 컬럼을 읽고 `Page[StressTestSummary]` 는 `result` 본문을 안 내보낸다. MC 의 `result.equity_percentiles` 는 5계열 시계열이라 limit=20 이면 전송량이 응답 크기와 무관하게 커진다.
**트리거 판정:** 미도래 — 현재 개발 DB 의 `stress_tests` 행이 0건이고 실사용 규모가 없다.
**출처:** 2026-08-17 night3 레인 γ ([BL-414] 이력 화면)

**원인 / 영향:** [BL-414] 가 추가한 `headline_metric` 은 **이미 읽고 있던** 컬럼에서 파생하므로 비용을 늘리지 않는다. 다만 그 파생 때문에 「목록이 result 를 읽는다」가 이제 의도적 의존이 됐다 — 최적화 시 그 의존을 함께 처리해야 한다.

**권장 접근:** `load_only` 로 목록 질의 컬럼을 좁히되 `result` 는 남기거나(파생에 필요), 대표 지표를 실행 완료 시점에 별도 컬럼으로 비정규화한다. 후자는 [BL-429] 가 optimizer 에서 쓴 패턴과 같다.
```

---

## 3. 다른 원장에 손댈 것 — 없음

`docs/lessons.md` 승격 후보는 이 회차에 없다. 밟은 것 3건은 전부 기존 교훈의 재현이거나
환경 문제였다(C-REPORT.md 「착수 중 밟은 것」).

다만 **한 문장은 갱신 대상**이다 — 격리 슬롯 authed 가 「구조적 불가」라는 판정의 근거가
`mise.toml` 이관 이후 낡았다(`be-isolated`/`fe-isolated` 가 `BETTER_AUTH_URL` 을 슬롯 포트로 덮는다).
남은 장애물은 playwright `webServer` 가 그 task 를 안 거친다는 것 하나다. 그 항목([BL-780]/[BL-781])은
병렬 세션 `stage/bl780-781-gates` 소유라 여기서 고치지 않았다 — **그 세션 산출과 대조해서 판단해라.**
