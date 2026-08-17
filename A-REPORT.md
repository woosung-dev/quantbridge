# 레인 α — [BL-784] e2e authed 비결정성: 관측 결과

**결론: 기전이 확정됐다. 지연이 아니라 거부다 — BE 의 전역 레이트리밋 `100/minute` 이
authed e2e 스위트를 429 로 끊는다.** 실패 시점의 trace 를 잡아 읽었고, 응답 헤더가
`x-ratelimit-limit: 100 · x-ratelimit-remaining: 0` 이었다. 화면에는 `API 429 /api/v1/backtests` 가
그대로 떠 있었다. 남아 있던 「부하로 렌더·응답이 늦다」 가설은 이 증거로 **반증**된다.

이 레인은 계측만 하고 수리는 하지 않았다(레인 지시). 수리 처방은 맨 아래에 적었다.

## 수용 기준 판정

| AC   | 요구                                                              | 판정                    | 근거                                                              |
| ---- | ----------------------------------------------------------------- | ----------------------- | ----------------------------------------------------------------- |
| AC-1 | 게이트 조건 authed 실행 3회 이상 + 회차별 통과/실패 목록이 파일로 | **충족**                | **15회** 실행. `results.json` 6건 원본 + 하네스 요약 전량 (§4·§7) |
| AC-2 | 실패 재현 시 trace 존재 + 타임라인을 읽어 보고                    | **충족**                | 실패 4회, trace 4건 확보. 타임라인·429 헤더 §2                    |
| AC-3 | 3회 모두 green 이면 「재현 실패」 + 환경 차이 표                  | **해당 없음**(재현했다) | 표는 그래도 남겼다 §6                                             |
| AC-4 | config 변경 전후를 같은 명령으로 대조                             | **충족**                | 양방향 확인 + sha256 복원 대조 §5                                 |

---

## 1. 왜 지금까지 증거가 없었나 — 확인 행위가 증거를 지웠다

`playwright.config.ts` 의 `trace: "retain-on-failure"` 는 **처음부터 정상 작동**했다. 실패한
테스트의 `trace.zip`·`video.webm`·`test-failed-1.png` 는 매번 기록됐다. 사라진 이유는 따로 있다.

playwright 는 **매 실행의 setup 단계에서 `outputDir` 을 통째로 지운다**
(`playwright/lib/runner/tasks.js` `createRemoveOutputDirsTask` → `removeFolders([outputDir])`).
이 레포의 project 7종은 **전부 기본 `test-results/` 하나를 공유**한다. 그래서

- 게이트가 `e2e chromium` → `e2e design-canon` → `e2e authed` 를 부르면 뒤 레그가 앞 레그를 지우고,
- 게이트가 red 를 낸 뒤 사람이 **「단독으로도 실패하나」를 확인하려고 한 번 더 돌리는 순간**
  그 게이트 실패의 trace 가 **그 확인 행위 자체에 의해 파괴된다.**

실측(2026-08-17):

| 순서 | 명령                                                        | `test-results/` 상태                                                          |
| ---- | ----------------------------------------------------------- | ----------------------------------------------------------------------------- |
| 1    | 일부러 실패시킨 spec 을 `--project=chromium-authed` 로 실행 | `_artifact-probe-…/{trace.zip,video.webm,test-failed-1.png,error-context.md}` |
| 2    | `pnpm e2e` (**다른** project)                               | `.last-run.json` **하나만** — 1의 산출물 전멸                                 |

★이 함정은 이 회차에서 **나 자신을 한 번 더 물었다.** 아래 §5 의 변이 M1 을 심고 돌리자
그때까지 모은 9회분 `results.json`·trace 가 같은 기전으로 전부 삭제됐다. 살아남은 것은
`.claude/bl784-evidence/` 로 옮겨 둔 사본과 하네스 요약뿐이다(§7 참조).

---

## 2. 확정된 기전

실패 회차 = `gate-load-2`, 실패 테스트 =
`authed-canon-remaining.spec.ts:226` (`/backtests — 성과 목록 11열 + 서버 정렬`).

```
TimeoutError: page.waitForSelector: Timeout 25000ms exceeded.
  - waiting for locator('[data-testid^="backtest-row-"]') to be visible
```

### trace 타임라인 (AC-2)

| t (문서 요청 기준) | 무엇이                                                                   | 결과            |
| ------------------ | ------------------------------------------------------------------------ | --------------- |
| 0ms                | `GET /backtests` (문서)                                                  | **200**, 200ms  |
| 70–280ms           | chunk·CSS·폰트 37건                                                      | **전부 200**    |
| 451ms              | `/api/auth/get-session`                                                  | 200 (51ms)      |
| 520ms              | `/api/auth/token`                                                        | 200 (42ms)      |
| 578ms              | `GET /api/v1/backtests?limit=20&offset=0&order_by=created_at&order=desc` | **200** (122ms) |
| 578ms              | **같은 URL 쌍둥이 요청**                                                 | ★**429** (31ms) |
| 1727ms             | React Query 재시도, 같은 URL                                             | ★**429** (5ms)  |
| ~1.8s–26.8s        | 새 요청 없음. 표 행이 끝내 안 나타남                                     | TimeoutError    |

**요청은 나갔다. 서버는 늦지 않았다(31ms · 5ms).** 서버가 즉시 거절했다.

429 응답 헤더:

```
x-ratelimit-limit: 100
x-ratelimit-remaining: 0
x-ratelimit-reset: 1786910332.001098
retry-after: 7
```

### 코드 대조

`apps/api/src/common/rate_limit.py:122` — `Limiter(..., default_limits=["100/minute"])`.
**신원(JWT `sub`) 단위 · 전역**이다. `GET /backtests` 라우트에는 개별 `@limiter.limit` 가 없으므로
이 전역 한도가 그대로 적용된다(`@limiter.limit("10/minute")` 는 같은 파일의 **POST** 에만 붙어 있다).

### 왜 「실행마다 다른 테스트가 실패」하나

authed e2e 는 **한 사용자로 90 테스트**를 연달아 돌고, 페이지마다 BE 요청을 4~8건
(목록 + 내비 배지 3종 + strategies) 낸다. 60초 창이 상시로 소진된다 —
이 밤 하나의 BE 로그에 **429 가 616건**이었다.

대부분의 429 는 테스트가 단언하지 않는 **내비 배지 프로브**(`limit=1`)라 조용히 지나간다.
**하필 단언 대상 목록 요청이 소진된 창에 걸린 회차만 red** 다. 그래서 실패 지점이 실행마다 갈린다.
같은 테스트의 green 회차(`gate-be-3`) trace 는 같은 URL 이 **200 (83ms · 308ms)** 이고 그대로 진행한다.

### 화면은 무엇을 보여줬나

실패 페이지 스냅샷(`error-context.md`):

```yaml
- alert:
    - paragraph: 목록을 불러오지 못했습니다.
    - paragraph: API 429 /api/v1/backtests
    - paragraph: GET /api/v1/backtests
    - button "다시 시도"
```

★사이드바 배지는 「백테스트 7개」로 정상이었다 — `limit=1` 프로브는 429 를 피했다.
**UI 는 옳게 동작했다.** 테스트가 기다린 행이 없었을 뿐이다.

★`retry-after: 7` 이 붙어 있었다. React Query 는 +1.15초에 한 번 더 쳐서 또 429 를 받고 포기했다.
**7초를 기다렸으면 통과했을 요청**을 25초 동안 기다리기만 했다.

### 두 번째 확증 — **단독 실행**에서도 같은 기전으로 red 가 났다

`solo-2`(앞선 것이 아무것도 없는 대조군, 부하 없음) 에서 **다른 테스트**가 실패했다:
`authed-canon-remaining.spec.ts:108` (`/strategies/:id/edit`).

```
Error: 목록에서 실존 전략 편집 링크를 찾지 못했습니다 (데이터 시딩 필요)
```

trace 를 열면 645ms 에 나간 `strategies` 목록 요청 **4건이 전부 429**
(`x-ratelimit-limit: 100` · `remaining: 0` · `retry-after: 1`), 1668ms 재시도도 429.
같은 시각의 `orders`·`backtests` 배지 프로브는 200 이었다 — **한 신원의 창을 나눠 쓰다가
목록 쪽이 먼저 걸렸다.**

★★**이것이 [BL-784] 의 두 전제를 동시에 무너뜨린다.**
⑴ 「단독 실행은 항상 green」— 거짓이다. 이 회차 단독 3회 중 **1회 red**.
그러므로 이 결함은 「게이트 전용」이 아니라 **누적 요청 속도에 걸린 확률 사건**이다.
⑵ 반증됐던 가설 「BE pytest 가 e2e 시드 데이터를 지운다」의 **출처가 이 문구**다 —
테스트가 429 를 「데이터 시딩 필요」라고 보고한다. 데이터는 멀쩡했고 요청이 거부됐을 뿐이다.
**테스트의 실패 문구가 수사를 엉뚱한 데로 보냈다.**

### 표본 전체 — 실패 4회, 원인 4/4 동일

15회 중 red 4회(`gate-load-2` · `solo-2` · `gate2-1` · `gate2-3`). **네 회차 모두** 실패 응답이
`x-ratelimit-limit: 100` · `x-ratelimit-remaining: 0` 이었다. 실패 테스트는 `:221` 3회 · `:108` 1회 —
둘 다 `authed-canon-remaining.spec.ts` 의 **라이브 목록 발견 지점**이다.

---

## 3. 계측 — 무엇을 바꿨나

### `apps/web/playwright.config.ts` — 관측 모드 `PW_ARTIFACT_RUN`

환경변수 `PW_ARTIFACT_RUN=<이름>` 이 있을 때만 켜진다(없으면 종전 동작 그대로).

- `outputDir` = `test-results/<이름>/<project>` — **project 항목마다** 설정한다
- `trace: "on"` — 실패하지 않아도 남는다(green 대조가 있어야 실패를 읽을 수 있다)
- reporter 에 `json` 추가 → `test-results/<이름>/<project>/results.json`

★**겹을 `process.argv` 의 `--project` 로 만들면 틀린다.** config 는 워커 프로세스에서도
평가되는데 워커 argv 에는 그 플래그가 없다. 초판이 그래서 지움 계산(메인)과 아티팩트
기록(워커)이 갈려 `<회차>/chromium-authed/results.json` 과 `<회차>/all/<테스트>/trace.zip` 로
찢어졌다. **project 설정으로 주는 것이 정답**이고 지금은 그렇게 돼 있다.
(reporter 경로만 메인에서 한 번 평가되므로 argv 를 봐도 안전하다.)

★비용: `trace: "on"` 은 authed 90 테스트 기준 **회차당 약 250MB**. 상시로 켜지 마라.

### `tools/scripts/e2e-authed-repro.sh` — 게이트 조건 재현 하네스 (신규)

`QB_REPRO_SHAPE` 로 게이트의 **세 모양**을 가른다. 모양이 갈리는 이유는 `final-gates.sh:378` 의
영역 판정이다 — `e2e authed` 만 술어가 `has_fe ∪ has_be` 이고 나머지 FE 게이트는 `has_fe` 뿐이다.

| shape             | authed 앞에 도는 것                                | 어떤 브랜치의 게이트인가                                |
| ----------------- | -------------------------------------------------- | ------------------------------------------------------- |
| `be-branch`(기본) | `BE pytest`                                        | ★[BL-784] 가 관측된 모양([BL-773] 은 `apps/web` diff 0) |
| `fe-branch`       | `pnpm build` → `e2e chromium` → `e2e design-canon` | `apps/web` 을 건드린 브랜치                             |
| `standalone`      | 없음                                               | 대조군 — 「단독은 항상 green」의 그 조건                |

`QB_REPRO_LOAD=<N>` 은 authed 레그가 **도는 동안** 형제 레인 N 개를 흉내 낸다
(`vitest run --maxWorkers=2` 반복). ★이것은 재현이 아니라 **합성**이다.

### `docs/reference/operations/gates-and-traps.md`

`### e2e 가 게이트에서만 red 일 때 — 증거를 남기고 조건을 재현하는 법 ([BL-784], 2026-08-17)`
절 신설: 아티팩트 소실 기전 · 관측 모드 사용법 · 세 모양 · 서버 짝 기동 · 그리고 429 기전.

---

## 4. 재현 결과 (AC-1)

서버는 `mise run be-isolated` + `mise run fe-isolated` 로 짝으로 띄웠다(슬롯 3 · FE :3103 · BE :8103).

**총 15회.** 4회 red — **그 4회의 실패 응답이 전부 `x-ratelimit-limit: 100` · `remaining: 0`** 이었다.

| 회차            | shape      | 부하   | BE pytest     | authed rc | 소요 | 판정                      |
| --------------- | ---------- | ------ | ------------- | --------- | ---- | ------------------------- |
| gate-repro-1    | fe-branch  | 없음   | —             | 0         | 224s | 90 PASS                   |
| gate-repro-2    | fe-branch  | 없음   | —             | 0         | 212s | 90 PASS                   |
| gate-repro-3    | fe-branch  | 없음   | —             | 0         | 214s | 90 PASS                   |
| gate-be-1       | be-branch  | 없음   | rc=1 · 514s ※ | 0         | 207s | 90 PASS                   |
| gate-be-2       | be-branch  | 없음   | rc=0 · 371s   | 0         | 216s | 90 PASS                   |
| gate-be-3       | be-branch  | 없음   | rc=0 · 374s   | 0         | 215s | 90 PASS                   |
| gate-load-1     | be-branch  | 합성 2 | rc=0 · 370s   | 0         | 226s | 90 PASS                   |
| **gate-load-2** | be-branch  | 합성 2 | rc=0 · 369s   | **1**     | 251s | 89 PASS / **FAIL `:221`** |
| gate-load-3     | be-branch  | 합성 2 | rc=0 · 370s   | 0         | 227s | 90 PASS                   |
| solo-1          | standalone | 없음   | —             | 0         | 224s | 90 PASS                   |
| **solo-2**      | standalone | 없음   | —             | **1**     | 220s | 89 PASS / **FAIL `:108`** |
| solo-3          | standalone | 없음   | —             | 0         | 223s | 90 PASS                   |
| **gate2-1**     | be-branch  | 합성 2 | rc=0 · 368s   | **1**     | 262s | 89 PASS / **FAIL `:221`** |
| gate2-2         | be-branch  | 합성 2 | rc=0 · 368s   | 0         | 240s | 90 PASS                   |
| **gate2-3**     | be-branch  | 합성 2 | rc=0 · 369s   | **1**     | 255s | 89 PASS / **FAIL `:221`** |

`:221` = `authed-canon-remaining.spec.ts:221` (`/backtests` 성과 목록) ·
`:108` = 같은 파일 `:108` (`/strategies/:id/edit`). **둘 다 라이브 목록에서 ID 를 발견하는 지점**이다.

조건별 red 비율:

| 조건                                           | red / 회차 |
| ---------------------------------------------- | ---------- |
| 부하 없음 (fe-branch · be-branch · standalone) | **1 / 9**  |
| 합성 부하 2 (be-branch)                        | **3 / 6**  |

부하는 원인이 아니라 **확률을 올리는 요인**이다 — 느려질수록 60초 창에 요청이 더 몰린다.

※ `gate-be-1` 의 pytest rc=1 은 이 워크트리 테스트 DB(`quantbridge_w3_test`)의 낡은 스키마
탓이다(`fk_strategies_strategy_version_id_strategy_versions` 부재 → setup ERROR 654건).
같은 실행의 `drop_all` 이 스키마를 다시 세워서 이후 회차는 전건 rc=0 이다. **부하는 재현됐다**
(502초 · 4098 passed). 실제 게이트에서는 pytest 가 green 이었으므로 이 한 회차는
게이트 조건과 어긋난다 — 그래서 표에 적어 둔다.

### 중단한 시도 1건 — 합성 부하가 과했다

첫 부하 시도(`gate-be-load`)는 워커를 `pnpm test`(워커 수 = 코어 수) 무한 루프로 돌렸고
**load average 가 217** 까지 갔다. 형제 레인 2개는 그런 부하를 만들지 않는다 — 그 조건에서
나온 실패는 원인을 지목하는 게 아니라 **새 원인을 만든 것**이다. 회차 1의 authed 레그 도중
중단하고 워커를 `--maxWorkers=2` 로 유계화한 뒤 다시 돌렸다(그 결과가 위 `gate-load-*`).
하네스에 상한 4 를 박아 뒀다. 중단된 회차는 위 표에 넣지 않았다.

---

## 5. 표적 변이 (AC-4)

| 변이                                                                                                        | 기대                        | 실측                                                                                                                                                   | 판정    |
| ----------------------------------------------------------------------------------------------------------- | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ------- |
| M1 — `const rawArtifactRun = process.env.PW_ARTIFACT_RUN?.trim();` → `= undefined;` (관측 모드 전체 무력화) | 실패 시 아티팩트가 사라진다 | 실패 spec 산출물이 `test-results/` 공유 자리에 떨어지고, 다음 `pnpm e2e` 한 번에 **전멸**. 덤으로 앞서 격리해 둔 `test-results/verify/` 까지 함께 삭제 | **red** |

- 심기·되돌리기 모두 **문자열 치환 쌍**(`git checkout` 미사용).
- 복원 확인은 심을 때 쓰지 않은 방법 — **sha256 대조**:
  `de8fed0c6ffef4aa1abb418a5554eee3dcda68c0d8579b9dc2716f70e40ac86c` 일치.
- 복원 뒤 같은 명령을 다시 돌려 `test-results/post/chromium-authed/…/trace.zip` 이
  후속 `pnpm e2e` 실행 뒤에도 **생존**함을 확인했다.

★즉 AC-4 의 「바꾸기 전에는 안 남고 바꾼 뒤에는 남는다」를 **같은 명령쌍으로** 양방향 확인했다.

---

## 6. 게이트 실행 vs 단독 실행 — 환경 차이 (AC-3)

AC-3 은 「3회 모두 green 이면」의 조건절이라 이번에는 발동하지 않는다(재현했다).
다만 표는 다음 회차가 쓸 것이므로 남긴다.

| 축                  | 게이트 실행 (2026-08-17 실패 회차)                             | 이번 재현               | 단독 실행     |
| ------------------- | -------------------------------------------------------------- | ----------------------- | ------------- |
| authed 앞에 도는 것 | `BE pytest` 379s (`has_be=1·has_fe=0`)                         | 같음 (369–374s)         | 없음          |
| 동시 프로세스       | 워크트리 레인 **3개**가 각자 게이트                            | 1레인 + **합성** 부하 2 | 보통 1        |
| loadavg (authed 중) | [확인 불가 — 기록 없음]                                        | 4.4 → 15.1              | 3~5           |
| FE 서버 기동        | `PLAYWRIGHT_BASE_URL` 지정 → playwright `webServer` **미기동** | 같음                    | 같아야 한다 ★ |
| workers             | 1 (`pnpm e2e:authed` 가 명시)                                  | 같음                    | 같음          |
| retries             | 0 (로컬)                                                       | 같음                    | 같음          |
| 실패 아티팩트       | 후속 실행에 삭제됨                                             | 회차별 보존             | —             |
| **BE 요청 누적**    | 90 테스트 × 4~8 요청, 한 신원                                  | 같음                    | 같음          |

★**단독 실행에서 `PLAYWRIGHT_BASE_URL` 을 빼면 안 된다.** playwright 가 자기 `webServer` 를
올리는데 그 프로세스는 `BETTER_AUTH_URL` 을 못 받아 로그인이 403 `INVALID_ORIGIN` 으로 죽는다.
직전 회차가 이것으로 한 번 오진했다.

★★**「단독은 항상 green」은 실측으로 거짓이다.** 단독 실행도 같은 90 테스트를 같은 신원으로
돌리므로 429 는 똑같이 발생한다. 갈리는 것은 **어느 요청이 소진된 창에 걸리느냐**뿐이고,
실제로 이 회차의 단독 3회 중 1회가 red 였다(§2). **「게이트에서만」이라는 축 자체가 틀렸다** —
게이트는 원인이 아니라 그 회차에 그 레그를 **돌린 유일한 것**이었을 뿐이다.

---

## 7. 확인하지 못한 것 · 이 보고서가 주장하지 않는 것

- ★**[BL-773] 회차에서 최초로 실패했다는 `sprint46-tier1-critical.spec.ts:69` 는 재현하지 못했다.**
  그 테스트는 `page.route()` 로 strategies·backtests 를 전수 stub 하므로 **BE 429 를 안 탄다.**
  증상(「제출을 눌렀는데 POST 가 없다」)도 이번에 잡은 것과 다르다. **같은 원인인지 미확정**이다.
  이번 6회+3회 실행에서 그 테스트는 954–1091ms 로 전건 통과했다(actionTimeout 30초 대비 여유 30배).
- **429 가 그 회차의 실패 전건을 설명하는지는 모른다.** 확인한 것은 이번에 잡은 1건이다.
- **loadavg 임계값을 모른다.** 부하 없이 6회 green, 합성 부하 2에서 3회 중 1회 red 였다.
  표본이 작아 확률을 말할 수 없다.
- **`gate-be-1` 의 pytest rc=1** 은 게이트 조건과 어긋난다(§4 ※).
- ★**앞 9회분(`gate-repro-*`·`gate-be-*`·`gate-load-*`)의 `results.json`·`trace.zip` 원본은
  변이 M1 실행이 지웠다.** 그래서 뒤 6회(`solo-*`·`gate2-*`)를 다시 돌려 원본을 남겼다.
  앞 9회의 rc·소요는 하네스 요약에서, per-test 판정은 삭제 전에 뽑아 둔 값에서 왔다.
- 증거는 `.claude/bl784-evidence/` 에 있다(`.claude/*` 가 gitignore 대상이라 게이트를 더럽히지 않고,
  playwright 의 `test-results/` 삭제도 못 미친다):
  실패 trace 3건(`gate2-1` · `gate2-3` · `solo-2`) · 네트워크 타임라인·429 헤더 덤프 ·
  green 대조 타임라인 · `results.json` 6건 · 하네스 요약 · BE 429 표본 · 분석 스크립트 3종.

---

## 8. 게이트

`mise exec -- tools/scripts/final-gates.sh --run bl784-trace --pre-pr` → **rc=0** (80초).
FE typecheck·lint·vitest·build·캐논 스코프 + 감사/하네스 17종 PASS. BE 영역은 diff 0 이라 skip.

**유예 8종** — `.claude/gates/bl784-trace/deferred.txt` 에 남아 있다. 야간 계약이 `--deferred-only`
를 금지하므로 이 원장은 **아침에 push 한 뒤** 지워야 한다. 유예 목록:
`e2e chromium` · `e2e design-canon` · `e2e authed` · `CI fresh DB alembic` ·
`/vercel-react-best-practices` · 화면 검증 · `/codex 적대 리뷰` · `★G9`.

★유예된 `e2e authed` 는 **이 레인이 하네스로 15회 돌렸다**(§4). 다만 그것은 게이트의 신호가
아니므로 원장은 그대로 남는다 — **원장이 남아 있으면 종결이 아니다.**

---

## 9. 다음 회차 처방 (이 레인은 수리하지 않는다)

기전이 확정됐으므로 [BL-784] 의 권장 접근 ⑵(「고정 대기를 조건 대기로」)는 **번지수가 틀렸다** —
1.5초 고정 대기가 문제가 아니라 요청이 **거부**된 것이다. 대신:

1. ★**한도를 e2e 신원에서만 풀거나 넓혀라.** 가장 곧은 수리다. `default_limits` 는 프로덕션
   방어물이므로 지우지 말고, 개발/e2e 프로필에서만 값을 키우거나 면제 신원을 둔다.
   ★**음성 대조 필수** — 면제가 프로덕션 경로로 새지 않는지 확인해라.
2. **FE 가 `Retry-After` 를 존중하게 한다.** 429 응답에 `retry-after: 7` 이 있었고 React Query 는
   1.15초 뒤 한 번 치고 포기했다. 이건 e2e 와 무관하게 **실사용자에게도 옳은 동작**이다.
3. **중복 요청을 줄인다.** trace 에서 목록·배지 요청이 **전부 쌍으로** 나갔다(같은 URL 2건).
   그 쌍이 창을 두 배로 먹는다. 어디서 두 번 나가는지가 별도 조사거리다.
4. ★**timeout 예산을 늘리지 마라** — 429 는 기다린다고 풀리지 않는다(`retry-after` 만큼 자면 풀리지만
   그건 대기가 아니라 재시도다). 늘리면 진짜 회귀만 못 잡게 된다.
5. **수리 뒤 판별력 증명** — 한도를 인위적으로 낮춰(예: `5/minute`) 해당 테스트가 red 가 되는지
   확인해라. 그것이 이 축의 변이다.

---

## 9. codex 적대 리뷰 처분 (2026-08-17, CONTROL 실행)

게이트 `/codex 적대 리뷰` 로 이 브랜치를 다시 걸었다. **P1 0건 · P2 3건**이고, 셋 다
**코드로 대조해 참임을 확인한 뒤** 채택했다(phantom finding 차단 규칙).

| #   | finding                                                                                        | 코드 대조                                                                                                                                                                   | 처분                     |
| --- | ---------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| 1   | `playwright.config.ts:41` — `PW_ARTIFACT_RUN=..` 가 `outputDir` 을 `test-results/` 밖으로 뺀다 | **참.** `sanitizeArtifactSegment` 는 `[^A-Za-z0-9._-]` 를 치환하는데 `.` 이 **허용 문자**라 `..` 가 그대로 통과한다. 실측: `test-results/../chromium` = `apps/web/chromium` | 수리 + 테스트 신설       |
| 2   | `e2e-authed-repro.sh:47` — 반복횟수 `0` 이 유효값이라 아무것도 안 돌리고 초록                  | **참.** `case` 가 비정수만 막는다. 실측: `probe 0` → 「실패 0 / 0」 + rc=0                                                                                                  | 수리 (`≥1` 강제, rc=1)   |
| 3   | `e2e-authed-repro.sh:151` — 실패를 세고도 항상 `exit 0`                                        | **참.** 무조건 `exit 0`                                                                                                                                                     | **의미를 문서화** (아래) |

**1번이 가장 무겁다** — 이 회차가 발견한 기전(playwright 가 `outputDir` 을 통째로 지운다)이
증거가 아니라 **소스 트리**를 겨누는 형태였다. 기존 배선 테스트는 환경 변수 없이 config 를
import 하므로 그 경로를 안 지났다 — 「가드가 있다」가 아니라 「그 경로가 지나는가」로 재라는
규칙(`apps/api/AGENTS.md` §10.1)의 사례가 하나 더 나왔다.

신설 `apps/web/src/__tests__/e2e-artifact-dir-containment.test.ts` (6건). config 를 **파싱하지 않고
`vi.resetModules()` + 동적 import** 로 다시 평가한다 — 정규식을 복사해 쓰면 배선이 아니라 사본을 잰다.

**변이로 판별력을 증명했다.** `sanitizeArtifactSegment` 를 수리 전 한 줄로 되돌리면
`.. (상위 탈출)` 케이스 **1건만** red 이고 나머지 5건은 green — 그 케이스가 정확히 이 결함을 잰다.
복원은 문자열 치환 쌍으로 하고 **sha256** `149c6d6e…` 바이트 동일로 확인했다(심을 때 안 쓴 방법).

**3번은 동작을 안 바꿨다.** 이것은 게이트가 아니라 **관측기**이고 red 는 찾으려던 것이다.
실패에 rc=1 을 주면 **성공한 재현이 실패로 보고된다.** 대신 헤더에 종료 코드의 뜻을 못박았다 —
`rc=0` 은 「요청한 회차를 전부 돌렸다」이지 「전부 통과했다」가 아니고, `rc≠0` 은 **돌리지 못한
경우**(인자 오류·서버 부재)뿐이다. 회차별 판정은 요약 줄과 `results.json` 이 갖는다.
