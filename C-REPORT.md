# 레인 γ 보고 — [BL-414] 스트레스 테스트 이력 화면

브랜치 `stage/night3-bl414-stress-history` · 슬롯 5 (FE 3105 / BE 8105 / pytest DB `quantbridge_w5_test`)
기준 `origin/main` = `acdc12c5`

**한 줄 결과** — 스트레스 테스트 이력이 백테스트 상세 패널 안에 표로 보이고, 행을 고르면 그 실행의
상세로 바뀐다. BE 는 목록 응답에 대표 지표 1개(`headline_metric`)만 더했다. AC 8개 중 7개 충족,
AC-8(레인 α 증거 게이트)은 α 가 아직 WIP 이라 미실행.

---

## AC-1 — 대상이 실재하는가 (착수 전 코드 확인)

원장이 낡았을 가능성을 먼저 봤다. **셋 다 지금도 참이었다.**

| 원장·레인 파일이 적은 것 | 코드 실측 (`acdc12c5`)                                                                                                                                                           |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FE 가 최신 1건만 부른다  | **참** — `stress-test-panel.tsx:63` `useLatestStressTest(backtestId)`, 그 fetcher 는 `listStressTests(backtestId, **1**, token)` 뒤 `page.items[0] ?? null` (`hooks.ts:345-353`) |
| BE 목록 API 가 이미 있다 | **참** — `stress_test/router.py:102` `@router.get("", response_model=Page[StressTestSummary])`, `backtest_id` 쿼리 필터 있음                                                     |
| 이력 리스트 화면이 없다  | **참** — `features/backtest/components/` 에 이력 컴포넌트 0건                                                                                                                    |

**`StressTestSummary` 필드 (변경 전 6개)** — `id` · `backtest_id` · `kind` · `status` · `created_at` ·
`completed_at`. 레인 파일이 「목록에 필요한 것」으로 든 4종 중 **종류·상태·생성 시각은 있었고 핵심
지표는 없었다.** ⇒ 이 레인은 FE 전용이 아니고, BE 는 **그 한 필드만** 늘었다.

### ★원장 문장의 실제 뜻 — 레인 파일의 읽기가 틀렸다

레인 파일은 원장의 「선행: 이력 화면 캐논 + 페이지 응답 캐시」를 두고 **"그 「페이지 응답」이 이미
`Page[StressTestSummary]` 로 있다"** 고 적었다. 원장 본문을 열어 보면 그 문장은 BE 엔드포인트를
가리키는 것이 아니다.

> **권장 접근:** 이력 리스트 도입 시 `stressTestKeys.byBacktest` 캐시를 단일 Summary 에서
> **페이지 응답으로 재정의**해야 함 (A7-lite 구현 노트). — `docs/backlog.md:1809` BL-414

즉 대상은 **FE React Query 캐시**였고, 그 캐시는 실제로 단일 `Summary` 를 담고 있었다(위 표 1행).
**원장의 처방은 옳았고 그대로 이행했다** — `byBacktest` 키가 이제 `StressTestListResponse` 를 담는다.
레인 파일이 BE 엔드포인트와 FE 캐시를 같은 말로 읽은 것이다.

---

## 무엇을 만들었나

**화면 배치는 ⒜(패널 확장)** 를 골랐다. 근거는 비용이다 — ⒝(새 라우트)는
`authed-canon-remaining.spec.ts` 가 잔여 authed 라우트를 전부 가져가므로 감사 대상이 하나 늘고,
그 감사는 이 워크트리에서 돌릴 수 없다(아래 AC-6). 맥락도 안 끊긴다.

| 파일                                                                      | 무엇                                                                                                   |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `apps/api/src/stress_test/schemas.py`                                     | `StressTestHeadlineMetric{key,value}` 신설 + `StressTestSummary.headline_metric` (nullable, 기본 None) |
| `apps/api/src/stress_test/serializers.py`                                 | `headline_metric_from(kind, status, result)` + `_worst_cell_sharpe`                                    |
| `apps/api/src/stress_test/service.py`                                     | `list()` 가 `_to_summary()` 경유 — `model_validate(from_attributes)` 로는 파생 필드를 못 채운다        |
| `apps/web/src/features/backtest/components/stress-test-history-table.tsx` | **신규** 이력 표 (종류·상태·대표 지표·실행 시각·액션)                                                  |
| `apps/web/src/features/backtest/components/stress-test-panel.tsx`         | `useLatestStressTest` → `useStressTestHistory`, 표를 상세 위에 얹고 행 선택으로 상세 교체              |
| `apps/web/src/features/backtest/hooks.ts`                                 | `useStressTestHistory` (limit 20) + `stressTestHistoryRefetchInterval` · `useLatestStressTest` 제거    |
| `apps/web/src/features/backtest/labels.ts`                                | 종류·상태·지표명·헤더·무데이터 라벨                                                                    |
| `apps/web/src/features/backtest/schemas.ts`                               | `headline_metric` (`.nullable().default(null)`)                                                        |
| `contracts/openapi/openapi.json`                                          | 재생성 (+35/−1, StressTest 스키마 2곳)                                                                 |

**대표 지표는 새로 계산하지 않는다.** 저장된 result 에서 그대로 읽는다 — MC `max_drawdown_p95`,
WFA `degradation_ratio`(`"Infinity"` 리터럴 보존), CA/PS 는 non-degenerate cell 중 **최저 sharpe**.
CA/PS 만 셀 순회가 들어가는데, 그것은 heatmap 이 이미 sharpe 를 주 지표로 칠하고
degenerate/None 셀을 `—` 로 비우는 관례를 따른 것이다(`param-stability-heatmap.tsx:79-107`).

**폴링을 하나 더 붙였다.** 이력 행 중 `queued`/`running` 이 있으면 2초 폴링, 전부 종결이면 멈춘다.
안 그러면 상세 패널은 「완료」를 그리는데 같은 화면의 이력 행은 「대기」로 남아 한 화면이 두 가지를 말한다.

---

## 수용 기준별 판정

| AC                                      | 판정                                       | 근거                                                                                                                                                                                  |
| --------------------------------------- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AC-1 대상 실재 확인                     | ✅                                         | 위 표 3행 + `StressTestSummary` 필드 6개 열거                                                                                                                                         |
| AC-2 2건 이상일 때 2건 이상 보인다      | ⚠️ **두 층에서 참, 브라우저에서는 미확인** | 아래                                                                                                                                                                                  |
| AC-3 종류·상태 구분                     | ✅                                         | 라벨 SSOT 경유 4종 + 상태 칩. 패널 테스트가 「워크포워드」·「몬테카를로」 동시 노출을 단언                                                                                            |
| AC-4 빈 이력 ≠ 실패 실행                | ✅                                         | ⑴ 0건 → 전용 문구 ⑵ FAILED → 상태 「실패」 + 지표 칸 `EMPTY_CELL`. BE 도 FAILED 에 `headline_metric=None` (result 가 남아 있어도)                                                     |
| AC-5 그 구분을 재는 테스트              | ✅                                         | 변이 3/3 red (아래 표)                                                                                                                                                                |
| AC-6 캐논 통과                          | ✅(design-canon) / ➖(authed)              | `pnpm e2e:design-canon` **rc=0, 44 passed**. 새 라우트를 안 만들었으므로 `authed-canon-remaining` 신규 편입 없음                                                                      |
| AC-7 FE vitest · e2e chromium · BE 전량 | ✅                                         | 아래 수치                                                                                                                                                                             |
| AC-8 레인 α 증거 게이트                 | ➖ **미실행**                              | α 브랜치 `stage/night3-evidence-gate` 가 작성 시점에 WIP 커밋 1건(`8bfed817`)뿐이고 산출이 완성되지 않았다. 그 파일을 내 브랜치로 들이면 레인 A 소유 파일을 만지게 되므로 하지 않았다 |

### 수치 (이 문서가 정본)

| 측정                                                     | 값                                                                                                   |
| -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| BE 전량 pytest (`925f276a` — 이 회차 BE 최종 상태)       | **4791 passed · 32 skipped · rc=0** (378s)                                                           |
| BE 전량 pytest (`8fa66200` — 라우터 이력 테스트 추가 전) | 4790 passed · 32 skipped · rc=0                                                                      |
| BE `tests/stress_test/`                                  | 135 passed(추가 전) → 신규 2파일 9 passed · 둘 다 rc=0                                               |
| FE vitest 전량                                           | **220 files · 1436 tests · rc=0** (이력 표·신규 케이스 포함 상태에서 측정)                           |
| e2e `chromium`                                           | 4 passed · rc=0                                                                                      |
| e2e `chromium-design-canon`                              | 44 passed · rc=0                                                                                     |
| 캐논 스코프 인구조사                                     | no-raw-enum-labels **117** (기준선 111) · no-internal-ids 205 · design-canon-source 339 — 셋 다 증가 |
| `final-gates.sh --run bl414 --pre-pr`                    | 1차 **rc=1** — `BE openapi drift` 1건. 아래 「최종 확인」이 재실행 결과다                            |

### AC-2 를 어디까지 확인했고 무엇을 못 했나

**확인한 것 둘.**

1. **실 DB + 실 라우터** — `tests/stress_test/test_router_list_history.py`. 한 백테스트에 실행 **3건**
   (COMPLETED MC / FAILED WFA / QUEUED PS)과 **다른** 백테스트에 1건을 실제 행으로 넣고
   `GET /api/v1/stress-tests?backtest_id=…` 를 친다. `total==3`, 종류 3종 전부 응답에 있고,
   다른 백테스트 행은 안 섞이며, 완료 행만 `headline_metric` 을 갖는다.
2. **렌더** — 패널에 2건을 주면 `stress-test-history-row` 가 **2개** 나온다.

**못 한 것 — 브라우저에서 실행 2건이 든 실제 화면을 보지 못했다.** 이유는 데이터가 아니라 환경이다.

- 개발 DB `quantbridge` 의 `stress_tests` 행이 **0건**이다(읽기 전용 조회로 확인).
- 행을 만들려면 ⑴ celery 를 타거나(워크트리 금지 — worker 가 메인 `src` 를 mount 한다)
  ⑵ 공유 개발 DB 에 직접 INSERT 해야 한다(다른 레인·메인과 1벌 공유라 하지 않았다).
- authed e2e 로 API 시드를 하는 길도 막혀 있다 — 아래 AC-6 항목.

**「데이터가 없어서 확인 못 했다」로 끝내지 않으려고 위 ⑴을 실 DB 로 세웠다.** 다만 그것은 API 층의
증거이지 화면의 증거는 아니다. 화면 층 증거는 컴포넌트 렌더뿐이다 — 이 구분을 흐리지 않는다.

### authed 캐논을 왜 안 돌렸나 — 메모리의 「구조적 불가」는 절반만 참이었다

`/backtests/[id]` 는 내가 바꾼 화면이고 `authed-canon-remaining.spec.ts` 가 감사하는 라우트다.
돌릴 수 있는지 실측했다.

- 종전 판정([BL-781] 메모)은 「격리 슬롯 authed 는 ADR-034 이후 구조적 불가 — `BETTER_AUTH_URL` 이
  슬롯 포트로 안 간다」였다. **그 근거는 이제 낡았다** — `mise.toml` 의 `be-isolated`(:312)와
  `fe-isolated`(:330)가 **둘 다 `BETTER_AUTH_URL` 을 슬롯 FE 포트로 덮는다**.
- 그러나 playwright 의 `webServer` 는 `mise run fe-isolated` 가 아니라 **`pnpm dev --port <포트>` 를
  직접 부른다**(`playwright.config.ts:185-190`). 그 경로에는 덮어쓰기가 없고, 워크트리
  `apps/web/.env.local` 은 `BETTER_AUTH_URL=http://localhost:3000` · `NEXT_PUBLIC_API_URL=…:8000`
  이라 **메인 슬롯을 가리킨다.**
- ⇒ 미리 `mise run fe-isolated` 를 띄워 `reuseExistingServer` 로 물리면 이론상 가능하다. 하지만
  그 배선을 세우는 것이 [BL-780]/[BL-781] 자체이고 **그 항목은 병렬 세션(`stage/bl780-781-gates`)이
  지금 들고 있다.** 내 범위 밖이라 손대지 않았다.

이 절은 **판정을 뒤집은 것이 아니라 근거를 갱신한 것**이다. 결과(내가 authed 를 못 돌렸다)는 같다.

---

## 표적 변이 — 3/3 red

각 변이는 문자열 치환 쌍으로 심고, 앵커 1건 확인 → sha256 변경 확인 → 테스트 → 역치환 →
**sha256 이 원본과 일치**까지 확인했다(`git checkout` 미사용).

| #   | 변이                                                  | 대상                            | 기대                | 실측                                                                   |
| --- | ----------------------------------------------------- | ------------------------------- | ------------------- | ---------------------------------------------------------------------- |
| 1   | 패널이 최신 1건만 쓰게 되돌린다 (`items.slice(0, 1)`) | `stress-test-panel.tsx`         | 「2건 렌더」 red    | **rc=1** — 「이력이 2건이면 2행이 보인다」 + 「행을 고르면 …」 2건 red |
| 2   | FAILED 빈칸 분기를 `"0"` 으로                         | `stress-test-history-table.tsx` | 「FAILED 빈칸」 red | **rc=1** — 해당 1건 red                                                |
| 3   | 빈 이력 분기를 통째로 삭제                            | `stress-test-history-table.tsx` | 「0건 빈 상태」 red | **rc=1** — 해당 1건 + 부수 1건 red                                     |

변이 1 은 원래 「목록 훅을 `useLatestStressTest` 로 되돌린다」였는데, 그 훅을 이 회차에 제거했으므로
**같은 결과를 만드는 최소 치환**(첫 1건만 남기기)으로 바꿔 심었다. 재는 것은 같다.

변이 3 이 무관한 케이스 하나(「MC completed … 둘 다 렌더」)도 red 로 만들었다. 빈 분기가 사라지면
0건일 때도 `<table>` 이 렌더돼 그 케이스의 `getByRole("table")` 이 모호해지기 때문이다. 표적 케이스는
따로 red 였으므로 판별력에는 영향이 없다.

---

## 착수 중 밟은 것 · 남긴 것

**⑴ 슬롯 5 pytest DB 가 낡아 있었다 (내 변경과 무관).** 첫 `tests/stress_test/` 실행이 **22 errors** 였고
원인은 `constraint "fk_strategies_strategy_version_id_strategy_versions" of relation "strategies" does
not exist` — conftest 의 `SQLModel.metadata.drop_all` 이 지우려는 제약이 DB 에 없었다(alembic 이
만든 스키마 위에 `create_all` 계보가 겹친 상태). `quantbridge_w5_test` **하나만** 지정해
`public`/`ts`/`trading` 스키마를 재생성했고 그 뒤 rc=0. 개발 DB 는 건드리지 않았다.

**⑵ 캐논 가드가 내 헤더 상수를 원시 enum 으로 잡았다.** `{STRESS_TEST_HISTORY_HEADER.kind}` 는
한국어 헤더 문자열을 그리는 코드인데, `no-raw-enum-labels` 는 JSX 자식의 **멤버체인 마지막
세그먼트**로 판정하므로 `kind`·`status` 키가 걸렸다. **가드를 넓히지 않고** 키 이름을
`kindColumn`/`statusColumn` 등으로 비켰다 — 가드는 실제 위반도 이 규칙으로 잡으므로 완화하면
판별력이 준다.

**⑶ 다른 레인과 겹치는 파일이 하나 있다 — `contracts/openapi/openapi.json`.** 레인 B 도
`2bf3e7cf chore(contracts): regenerate …` 로 같은 파일을 재생성했다. 둘 다 **생성물**이라 머지 후
한 번 재생성하면 정리된다. 내 diff 는 `StressTestHeadlineMetric` 신설 + `StressTestSummary` 2줄로
optimizer 쪽과 겹치는 줄이 없다.

**⑷ BL 번호 — 다음은 797 이 아니라 798 이다.** 프롬프트 정정은 「796 이 아니라 797」이었는데,
작성 시점에 레인 α 가 `8bfed817 wip(web): screen evidence pack … (BL-797)` 로 797 을 이미 썼다.

---

## 확인하지 못한 것 (그대로 적는다)

- **브라우저에서 이력 2건이 든 실제 화면** — 위 AC-2 항목. 데이터가 없고 만들 길이 워크트리에서 막혔다.
- **authed 캐논(`/backtests/[id]`)** — 위 AC-6 항목. 배선이 다른 레인 소유다.
- **레인 α 증거 게이트로 만든 before/after** — α 가 WIP.
- **목록 응답의 전송 비용.** `list_by_user` 는 `select(StressTest)` 라 **`result` JSONB 를 통째로**
  읽는다(내 변경 이전부터). MC 의 `equity_percentiles` 는 5계열 시계열이라 20행이면 무겁다.
  내 파생은 이미 읽고 있던 컬럼을 쓰므로 **비용을 늘리지 않지만 줄이지도 않았다.** 별건으로 남긴다
  (ledger 의 BL-798 제안).
- **실사용 지표 눈금.** `worst_cell_sharpe` 가 사용자가 기대하는 「대표」인지는 실사용자 확인을
  못 했다. 코드 관례(heatmap 주 지표)에 맞춘 선택이다.

---

## 최종 확인 (마지막 커밋 뒤 실측)

`--pre-pr` 은 마지막 커밋 뒤에 돌린다. 게이트 원장(`.claude/gates/bl414/deferred.txt`)의 sha 가
레인 HEAD 와 같아야 CONTROL 이 통과로 세므로, 이 절을 채운 커밋 **뒤에** 한 번 더 돌린다.

| 항목                                                    | 결과                                     |
| ------------------------------------------------------- | ---------------------------------------- |
| `final-gates.sh --run bl414 --pre-pr` (2차, `f91d0966`) | **rc=0** — 실행 25종 전부 PASS, 유예 8종 |

1차에서 유일하게 걸린 `BE openapi drift` 는 계약 재생성으로 닫혔고 2차에서 PASS 다.
유예된 것 중 **BE pytest · e2e chromium · e2e design-canon 셋은 내가 따로 돌려 rc=0 을 확인했다**
(위 수치 표). 나머지 유예분(e2e authed · CI fresh DB alembic · 신호 4종)은 계약상 아침
오케스트레이터 몫이거나 이 워크트리에서 못 도는 것들이다.

이 절을 쓴 커밋 뒤에 `--pre-pr` 을 한 번 더 돌려 유예 원장(`.claude/gates/bl414/deferred.txt`)의
sha 를 레인 HEAD 에 맞춘다 — CONTROL 의 통과 판정식이 그 sha 를 본다.
