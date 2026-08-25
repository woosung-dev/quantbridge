# 함정 — CI·e2e

> **진입점은 [`gates-and-traps.md`](./gates-and-traps.md) 다** — 이 파일은 그 §3 함정을 2026-08-21 에 주제별로 나눈 조각이다
> ([ADR-038](../adr/038-docs-top-level-by-question.md) 후속 · 원문 = `git show 9e91809c:docs/development/gates-and-traps.md`).
> **다루는 것:** CI 와 로컬의 차이, 샤딩, e2e 통합·재현, authed 증거, FE 스키마 대조.
> 규율은 ADR-026 ④ 그대로 — 서술만, 지시 금지. 새 함정은 날짜·회차·실측을 적고, 정본 절차가 바뀌면 여기도 같은 PR 에서 고친다.

---

## ★★CI 와 로컬은 같은 명령이어도 **같은 env 가 아니다** (2026-08-01, 실측 5건)

- ★**추적되지 않는 파일로 링크를 걸면 로컬 게이트는 판별력이 0이다** (2026-08-15 ledger-thaw).
  당시 `docs/reports/*.html` 은 `.gitignore` 로 **추적 대상이 아니었다**(2026-08-21 폴더째 철거 — 산출물은 `runs/`).
  `docs/status.md` 에서 그 파일을 마크다운 링크로 걸었더니 **로컬 `docs-audit` 은 rc=0**(파일이
  거기 있으니까)이고 **CI 의 같은 명령이 red** 였다. 로컬 초록은 「내 작업 트리에 있다」만 말한다.
  ⇒ 추적 안 되는 산출물은 **링크가 아니라 경로**(코드 스팬)로 적어라 — `dev-log/*.md` 를 코드
  스팬으로 적는 관용구와 같은 이유다. **커밋 트리로 재는 방법**: `git archive <브랜치> | tar -x -C <임시>`
  하고 거기서 게이트를 돌린다(로컬 트리의 미추적 파일이 섞이지 않는다).

- ★**`Settings` 의 인프라 기본값은 docker-compose 서비스명이다**(`redis://redis:6379/*`).
  워크플로가 그 필드를 **명시 주입하지 않으면** 러너에서 해석 불가 호스트로 붙는다.
  실측: `REDIS_URL` 만 주입돼 있고 `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND`/`REDIS_LOCK_URL`
  이 없어 **backend 5건**이 `Retry limit exceeded ... Celery result store` 로 죽었다.
  **celery 는 `REDIS_URL` 을 읽지 않는다 — 별도 설정이다**(`core/config.py:64-67`).
- ★★**로컬 CI 재현은 이 계열을 구조적으로 못 잡는다** — `.env.local` 이 그 값들을 모두
  `localhost` 로 채운다. "CI 와 같은 스크립트를 돌렸다" 는 **같은 pytest 명령**일 뿐이다.
  ⇒ 감사 테스트 `apps/api/tests/test_ci_workflow_env_parity.py` 가 대신 대조한다(변이로 판별력 증명).
- ★**`env -u` 로 지워도 소용없다** — pydantic-settings 의 `env_file` 이 `.env.local` 에서 다시 채운다.
  CI 를 재현하려면 **지우지 말고 CI 실효값으로 덮어써라**.
- ★**시각 의존 테스트는 스스로 만료된다** — `since=datetime(2026, 7, 25, 1)` 하드코딩 + 7일 롤링 클램프가
  **2026-08-01 00:00 UTC 에 폭발**했다. **실패 값이 실행마다 달라지면 시각 의존을 의심해라.**
  픽스처 시각은 **상대값**(`now - N`)으로 써라.
- ★**CI 가 빨간 것과 CI 가 돌기라도 한 것은 다르다** — main 5회 연속 실패는 테스트가 아니라
  **결제/지출 한도로 잡이 시작조차 안 된 것**이었다(`The job was not started because recent account
payments have failed`). backend 가 `skipped` 면 **게이트는 아무것도 검증하지 않았다.**

## CI pytest 샤딩 (2026-08-06 ci-diet)

- ★★★**커버리지 잡을 「별도 병렬 잡으로 옮기는」 것은 이득이 0 이다.** 그 잡이 여전히 full suite 를
  돌아 **임계경로**가 된다(1313s). BL-308/309 래칫이 full-suite transitive 커버를 요구하므로 `ci` 가
  그 잡을 기다려야 하고, 23분은 23분으로 남는다. **옮기는 게 아니라 쪼개야 한다** —
  샤드마다 부분 데이터 → `coverage combine`(합집합) → `--fail-under` 1회.
- ★★**`COVERAGE_CORE=sysmon` 은 이 레포에서 못 쓴다.** `coverage/env.py` 의
  `branch_right_left = pep669 and PYVERSION > (3,14,0,a5)` 때문에 **Python 3.12 + `branch = true`** 조합은
  `core.py` 가 sysmon 을 거부하고 ctrace 로 폴백한다. 계측 배율 실측 **1.770배**(무계측 298.97s vs 계측 529.16s).
- ★★★**커버리지 수치는 샤드 누락을 못 본다.** 샤드 a·b 의 데이터 파일은 **내용이 동일**해서
  `coverage combine` 이 `Skipping duplicate data` 를 찍는다 — 즉 **그 아티팩트가 통째로 사라져도 최종
  수치가 안 움직인다.** 그래서 `backend_coverage` 는 조각 **개수**를 `shards.json` 키 개수와 대조한다.
  ★`actions/upload-artifact@v4` 는 **dot 파일을 기본 제외**한다 — `include-hidden-files: true` 가 빠지면
  정확히 그 상황이 된다(`if-no-files-found: error` 와 이중으로 막는다).
- ★★★**`--durations` 순위로 샤드 경계를 정하면 틀린다 — 그 목록은 「누가 먼저 돌았나」의 함수다.**
  코퍼스 스크립트를 **처음** 파싱하는 테스트가 비용을 전부 물고 이후는 거의 공짜다:
  `test_ast_classifier[i3_drfx]` 는 **단독 42.66s** 인데 **전체 스위트 안에서는 4.58s** 다
  (`i1_utbot` 12.06s vs 0.02s). 알파벳상 앞선 `test_alert_hook` 이 값을 치르는 바람에 이 테스트는
  단일 실행 top-10 에 **아예 없었고**, 그 목록으로 잡은 추정이 **2.2배 빗나갔다**(샤드 a 385s→847s).
  ⇒ **쪼개면 그 비용이 샤드마다 중복된다.** CI 3샤드 합 1796s vs 단일 1278s 의 **+519s 전부**가
  이 중복이다. **이 스위트는 샤딩에 저항한다** — 3-way wall 14.8분이 한계고 재분배로 못 내려간다.
  뿌리 = [BL-598].
- ★★**「고정 오버헤드」로 오진하기 쉽다 — 내가 두 번 그랬다.** 처음엔 F≈305s 라고 모델링했는데,
  샤드 b 로그가 반증했다: **70 테스트에 615.42s 인데 top-10 만 596s** 다(오버헤드 ~20s).
  **한 샤드의 로그를 열어 테스트 시간과 총시간을 대조하기 전에는 오버헤드를 주장하지 마라.**
- ★★**샤드 경계를 로컬 durations 로 정하면 틀린다(2).** CI/로컬 비율이 **균일하지 않다** —
  `test_alert_hook[i3_drfx]` 는 2.73배인데 `test_ast_classifier[i3_drfx]` 는 **27.7배**다.
  후자가 이상한 게 아니라 **첫-접촉 비용을 누가 무느냐가 바뀐 것**이다.
- ★**`--durations=0` 은 전수가 아니다** — `--durations-min` 기본 5ms 아래는 안 찍힌다(4199 중 1016건만).
  합계로 검산해라(291.4s / 298.97s).
- ★★**샤드 3벌 합계 > 전체 1벌** — 로컬 688.9s vs 529.2s(**+30%**). 세션 startup·fixture 가 샤드마다
  반복된다. 잡이 병렬이라 벽시계는 줄지만 **러너 분은 늘어난다**.
- ★★★**등가성은 aggregate 로 주장하지 마라.** `TOTAL` 이 같아도 파일별로 다를 수 있다.
  전체 1벌의 데이터를 따로 보관해 두고 `coverage report` 출력을 **diff** 해서 완전 일치를 보여라.
- ★★**`$ARGS` 를 따옴표 없이 펼치는 검증은 반드시 `bash -c` 로 해라.** 이 세션 셸은 **zsh** 이고
  zsh 는 기본적으로 word-splitting 을 **안 한다** — 인자 전체가 한 덩어리로 들어가 `pytest` 가
  `ERROR: file or directory not found: tests/strategy --ignore=…` 로 죽는다. CI 는 bash 라 정상이다.
  **하네스가 거짓 red 를 냈다.** 그래서 `shard_paths.py` 가 공백 경로를 거부해 그 가정을 집행한다.
- ★**소크·다른 pytest 와 동시에 돌리지 마라.** `tests/conftest.py` 세션 픽스처가 `quantbridge_test` 에
  `drop_all`+`create_all` 을 하므로 **진행 중인 다른 실행의 DB 를 도중에 날린다.**

## e2e spec 을 통합할 때 (2026-08-06 e2e-consolidation)

- ★★★**「A 는 B 에 포함된다」를 assertion 단위로 확인하기 전에 지우지 마라 — 두 번 틀렸다.**
  ⑴ 핸드오프는 `sprint32-dogfood-gate.spec.ts`(306L) 전체가 sprint46 tier 에 「거의 완전 포함」
  이라 했지만, 실제로 겹치는 건 4 테스트 중 **1개**뿐이었다. 나머지 셋은 저장소에서 **유일하게**
  `equity-pane-wrapper` · `drawdown-pane-wrapper` · `axis-label-bar` · 차트 범례 3항목 ·
  MDD `자본 초과` 캡션을 검사하고 있었다.
  ⑵ 그리고 **나도 같은 실수를 한 단계 아래에서 반복했다** — 그 「겹치는 1개」(422)마저 실제로는
  다른 요소를 본다. tier1 은 `backtest-form-unsupported-card`(빌트인 UL), 구 sprint32 는
  `backtest-form-friendly-message`(사람이 읽는 안내)로 **`FormErrorInline` 이 내보내는 별개 두
  testid**다(`form-error-inline.tsx:127` vs `:145`). 그대로 뒀으면 후자를 검사하는 spec 이 0개가 됐다.
  ⇒ **파일 이름·테스트 제목이 아니라 `getByTestId`/`getByRole` 인자를 grep 해서 대조해라.**
- ★★**playwright `testMatch` 열거식은 조용히 샌다.** 새 spec 을 목록에 안 적으면 **발견조차 안 되고**
  playwright 는 초록이다. 이제 `chromium-authed` 는 **잔여 전체**를 가져가고 다른 project 몫만
  `testIgnore` 로 뺀다. `src/__tests__/e2e-project-wiring.test.ts` 가 고아·중복을 둘 다 막는다.
- ★★**정규식에 앵커가 없으면 다른 spec 을 삼킨다.** `/smoke\.spec\.ts$/` 가 **`live-smoke.spec.ts`
  까지** 잡아 전용 project 와 겹쳤고, `pnpm e2e` 가 live-smoke 를 매번 덤으로 돌리고 있었다.
  감사 테스트를 **먼저 써서 red 로 확인**한 뒤 고쳤다(고아 0 · 중복 1 로 정확히 지목).
- ★**config 를 파싱하지 말고 import 해라.** 정규식을 문자열로 다시 쓰면 실제 배선이 아니라 내
  복사본을 검사하게 된다. 감사 통과 후에도 `playwright test --list` 로 **실제 선택 집합**을
  대조해라(1 + 1 + 4 + 14 = 20 전량 일치 확인).
- ★**`--list` 출력은 `[project] › file.spec.ts` 형식이다** — `e2e/` 접두를 기대한 grep 은 빈 결과를
  내고, 그걸 「선택 0건」으로 오독하기 쉽다.
- ★**e2e 를 로컬 검증할 땐 `PLAYWRIGHT_BASE_URL` 을 반드시 고정해라.** 안 주면 `webServer` +
  `reuseExistingServer` 가 :3000 의 **남의 앱**을 그대로 쓴다(이 머신 :3000 = 다른 제품).
  정체성 프로브(`<title>` 에 QuantBridge)를 먼저 통과시켜라.
- ★★**`test.describe.configure({ mode: "serial" })` 은 음성 대조를 지운다.** serial 은 앞 시험이
  깨지면 **뒤를 skip** 한다. 음성 대조를 뒤쪽에 두는 파일에서는 실패하는 순간 「구분이 되는가」라는
  판정 자체가 사라지고, 리포트에는 `1 failed / N did not run` 만 남는다.
  ★**`chromium-authed` 에는 얹을 이유도 없다** — config 가 이미 `fullyParallel: false` 이고
  `pnpm e2e:authed` 가 `--workers=1` 을 준다(이중 보장). 공유 storageState flake 방지 목적이라면
  **이미 달성돼 있다.** 2026-08-10 실측 — 신규 spec 5건 중 3건이 음성 대조라 serial 을 뺐다.

## e2e 가 게이트에서만 red 일 때 — 증거를 남기고 조건을 재현하는 법 ([BL-784], 2026-08-17)

- ★★★**playwright 는 매 실행의 setup 에서 `outputDir` 을 통째로 지운다.** 근거는 관용구가 아니라
  코드다 — `runner/tasks.js` 의 `createRemoveOutputDirsTask` 가 `--project` 필터에 걸린 project 들의
  `outputDir` 을 `removeFolders` 한다. 이 레포의 project 7종은 **전부 기본 `test-results/` 하나를
  공유**하므로 어떤 `--project` 로 돌리든 **직전 회차의 trace·video·screenshot 이 사라진다.**
  ⇒ **「게이트에서 실패했으니 단독으로도 실패하나 확인해 보자」가 그 실패의 증거를 파괴한다.**
  [BL-784] 가 「실패 시점 network trace 가 없다」였던 이유가 이것이고, 설정(`retain-on-failure`)은
  처음부터 정상이었다. 2026-08-17 실측 — 일부러 실패시킨 spec 의 `trace.zip`·`video.webm`·
  `test-failed-1.png` 이 남은 것을 확인한 뒤 `pnpm e2e`(**다른 project**)를 한 번 돌리자
  `test-results/` 에 `.last-run.json` 만 남았다.
- **관측 모드 — `PW_ARTIFACT_RUN=<이름>`** (`apps/web/playwright.config.ts`). 켜면 셋이 바뀐다:
  `outputDir` = `test-results/<이름>/<--project 값>` · `trace: "on"`(실패하지 않아도 남는다) ·
  `test-results/<이름>/<project>/results.json`(테스트별 통과/실패 목록).
  ★**`<--project 값>` 겹이 필수다** — 게이트는 한 번 실행에서 e2e 를 세 번 부르므로 그 겹이 없으면
  마지막 레그가 앞의 둘을 지운다(고치려던 병이 그대로 재현된다).
  ★비용: `trace: "on"` 은 authed 90 테스트 기준 **회차당 약 250MB** 다. 상시로 켜지 마라.
- ★★**「게이트 실행」은 한 모양이 아니다 — 영역 판정이 브랜치마다 다른 집합을 켠다.**
  `e2e authed` 의 술어만 `has_fe ∪ has_be` 이고(`final-gates.sh:378`) `FE vitest`·`FE build`·
  `e2e chromium`·`e2e design-canon` 은 `has_fe` 뿐이다. 그래서 **BE 만 건드린 브랜치에서는
  `e2e authed` 앞에 도는 것이 `BE pytest` 하나뿐**이고, FE 를 건드린 브랜치에서는 `pnpm build` +
  e2e 두 레그가 앞선다. 재현하려면 **어느 모양이었는지부터 확정해라** — [BL-784] 가 관측된
  회차([BL-773])는 `apps/web` diff 가 0 이라 **be-branch 모양**이었다.
- **재현 하네스 = `tools/scripts/e2e-authed-repro.sh <라벨> [반복횟수]`.**
  `QB_REPRO_SHAPE=be-branch`(기본, `BE pytest → e2e:authed`) / `fe-branch`(`build → chromium →
design-canon → authed`). 회차마다 `PW_ARTIFACT_RUN` 을 달리 주므로 **앞 회차 증거가 살아남는다.**
- ★**서버는 짝으로 띄워라** — `mise run be-isolated` **와** `mise run fe-isolated`. FE 만 띄우면
  playwright 가 자기 `webServer` 를 올리는데 그 프로세스는 `BETTER_AUTH_URL` 을 못 받아 로그인이
  403 `INVALID_ORIGIN` 으로 죽는다. 2026-08-17 회차가 이것으로 한 번 오진했다.
  `curl` 은 생존 확인 전용이다 — Origin 헤더가 없어 그 검사를 안 거친다.
- ★★★**그래서 무엇이었나 — `authed` 레그는 BE 의 전역 레이트리밋에 걸린다.**
  `apps/api/src/common/rate_limit.py:122` 가 `default_limits=["100/minute"]` 을 **신원 단위**로 건다.
  authed e2e 는 **한 사용자로 90 테스트**를 연달아 돌고 페이지마다 BE 요청을 4~8건(목록 + 내비
  배지 3종 + strategies) 내므로 60초 창을 넘긴다. 2026-08-17 실측 — 한 밤의 BE 로그에 **429 가
  616건**이었다. 대부분은 테스트가 단언하지 않는 배지 프로브라 조용히 지나가고, **하필 단언
  대상 목록 요청이 걸린 회차만 red** 다. 그래서 「실패 테스트가 실행마다 갈린다」가 나온다.
  ⇒ **원인은 지연이 아니라 거부다.** trace 타임라인에서 그 목록 요청은 **31ms · 5ms 만에 429** 로
  돌아왔고 화면에는 `API 429 /api/v1/backtests` 가 그대로 떠 있었다. 「부하로 렌더가 늦다」는
  가설을 이 증거가 반증한다 — 늦은 것이 아니라 서버가 즉시 거절했다.
  ★★**「단독 실행은 항상 green」도 거짓이다.** 단독도 같은 90 테스트를 같은 신원으로 돌리므로
  429 는 똑같이 난다. 같은 날 **단독 3회 중 1회가 red** 였고(`authed-canon-remaining.spec.ts:108`)
  그 실패 응답도 `x-ratelimit-limit: 100 · remaining: 0` 이었다. 즉 **「게이트에서만」이라는 축이
  틀렸다** — 게이트는 원인이 아니라 그 레그를 돌린 유일한 것이었다. 재현 15회 중 4회 red
  (부하 없음 1/9 · 합성 부하 3/6)이고, 부하는 원인이 아니라 **확률을 올리는 요인**이다.
  ★★★**실패 문구를 믿지 마라.** `:108` 은 429 를 「목록에서 실존 전략 편집 링크를 찾지
  못했습니다 (**데이터 시딩 필요**)」라고 보고한다. [BL-784] 가 세웠다가 반증한 가설
  「BE pytest 가 e2e 시드 데이터를 지운다」의 출처가 바로 이 문구다 — 데이터는 멀쩡했다.

- ★★★**같은 증상에 원인이 둘이다 — 먼저 어느 쪽인지 가려라** ([BL-795], 2026-08-17).
  「authed 스위트가 빨갛다」는 [BL-784] 축(**BE 레이트리밋 429**)과 [BL-795] 축(**Turbopack
  영속 캐시 물림**) 둘 다에서 나온다. 증상만으로는 구분이 안 되고, 원인을 정하기 전에
  처방을 고르면 [BL-784] 가 넉 달을 끈 모양이 그대로 반복된다.

  | 축                      | 어디서 죽나                                                      | BE 로그의 429 | 처방                                                    |
  | ----------------------- | ---------------------------------------------------------------- | ------------- | ------------------------------------------------------- |
  | [BL-784] 레이트리밋     | 개별 spec — 실행마다 **다른** 테스트가 깨진다                    | **있다**      | 신원 단위 한도(위 항목) · `e2e-authed-repro.sh` 로 재현 |
  | [BL-795] Turbopack 캐시 | `setup` 단계 — `global.setup.ts:65` 의 `/sign-in` goto 120s 초과 | **0건**       | dev 서버를 죽이고 `rm -rf apps/web/.next` 후 재기동     |

  ★**구분식 = 「실패가 `setup` 단계에서 나고 BE 로그의 429 가 0건이면 캐시 쪽이다.」**
  `setup` 이 죽으면 뒤 spec 은 전부 `did not run` 이라 **실패 1건 + 미실행 89건**이라는
  독특한 모양이 남는다 — 429 축은 반대로 앞 spec 들이 통과한 뒤 중간에서 갈린다.
  2026-08-17 실측 — `○ Compiling /sign-in/[[...sign-in]] ...` 에서 next-server 가 **CPU 0.0%**
  로 멈췄고 `curl /sign-in` 은 240초를 넘겨도 응답이 없었다. `.next` 를 치우고 재기동하니
  같은 라우트가 **0.79초**에 컴파일됐다.
  ★**크기를 진단 문턱으로 쓰지 마라.** 근거는 여전히 두 점(1.99GB 사망 · 593MB 무해)뿐이고
  그 사이 어디가 문턱인지는 아무도 모른다 — 판정은 **크기가 아니라 위 표의 두 축**으로 해라.
  단 2026-08-25 [BL-650] 종결로 `mise run fe` 는 `.next/dev/cache` ≥ 1GB 면 기동 전에
  **자동 소각**한다(사망점 절반에서 끊는 보수 정책 — 예방이지 진단이 아니다).

## CI 초록은 **authed 통과의 증거가 아니다** ([BL-789], 2026-08-17)

- ★★★**authed 계열 e2e 는 GitHub CI 에서 한 번도 돈 적이 없다.** 워크플로가 부르는 playwright
  project 는 `ci.yml` e2e 스텝의 `chromium` · `chromium-live-smoke` · `chromium-design-canon` 과
  `live-smoke.yml:62` 의 `chromium-live-smoke` 뿐이다. `chromium-authed` 를 부르는 줄은
  `.github/workflows/` 전체에 **없다** — 그 **이름** 자체는 워크플로에 0회 등장하고
  (`grep -c chromium-authed .github/workflows/*.yml` 전건 0), 「authed 는 CI 에 없다」고 적은
  산문 주석 두 줄(`ci.yml` e2e 잡 머리말·design-canon 주석)이 스크립트 이름 `pnpm e2e:authed`
  를 품고 있을 뿐이다. ★그래서 **감사기가 `pnpm <script>` 를 푸는 순간** 그 주석이 배선으로
  읽힌다 — 산문을 배선으로 읽지 마라(주석 제거가 그 감사의 하중 지점이다).
- **규모** — `apps/web/e2e/*.spec.ts` **29개** 중 공개 project 몫이 9개(`smoke` 1 · `live-smoke` 1 ·
  `design-canon-*` 7)이고, `chromium-authed` 의 `testMatch: /\.spec\.ts$/` 가 가져가는 **나머지
  20개가 CI 실행 0회**다. ★그 20개가 **전부 로그인을 요구하는 것은 아니다** —
  `invite-token-page.spec.ts` 는 `test.use({ storageState: { cookies: [], origins: [] } })` 로
  **세션 없이** 도는 공개 라우트 계약 시험이고, `testMatch` 가 잔여를 전부 가져가서 authed 몫이
  됐을 뿐이다. ⇒ 그 파일은 **인증 secret 없이도 오늘 공개 project 로 옮길 수 있다**(아래 2단계
  「사용자 결정」에 묶이지 않는다).
- **실행처** — CI 가 안 돈다는 것이 「실행처가 하나」라는 뜻은 아니다. 로컬에 최소 넷이다:
  `tools/scripts/final-gates.sh` 의 `e2e authed` 레그 · `mise run fe-e2e-authed` ·
  `pnpm e2e:authed` 직접 호출 · `tools/scripts/e2e-authed-repro.sh`(위 [BL-784] 축 재현 처방).
  **게이트 판정의 증인은 `final-gates.sh` 레그 하나**지만, 재현 경로를 그 하나로 좁히지 마라.
- ⇒ **PR 이 CI 전건 초록이면서 authed 게이트가 red 인 채로 머지될 수 있다.** 반대로 「CI 가
  초록이었다」를 **로컬 authed red 의 음성 대조 근거로 쓰면 그 근거는 무효다** — 그 잡은
  authed 를 애초에 돌리지 않았다. 원장에 그렇게 적힌 항목이 실재한다([BL-668] 의 음성 대조 ②).
- **회귀 방지** — `apps/web/src/__tests__/e2e-project-wiring.test.ts` 의 「CI 실행 표면」 감사가
  `playwright.config.ts` 의 project 이름과 `.github/workflows/*.yml` 을 **양쪽 실파일에서 파싱해**
  대조한다. CI 에서 안 도는 project 는 `LOCAL_ONLY` 상수에 **사유와 함께** 등재해야 하고
  (★사유는 `[BL-NNN]`/`[ADR-NNN]` **원장 식별자를 최소 1개** 품어야 한다), 새 project 를
  만들고 워크플로에 안 배선하면 빨개진다.
  ★★**그 감사의 초판이 fail-open 이 네 갈래였다** (2026-08-17 적대 리뷰 — 전부 「무엇이 그것을
  발화시키나」를 안 본 것이다). ⑴ `--project=` 를 YAML **본문 전체**에서 찾아 `- name:` 스텝
  **제목**을 배선으로 셌다 → `run:` 셸 본문만 본다. ⑵ 워크플로를 트리거 무관하게 동등히 읽어
  **schedule/dispatch 전용** 파일에 배선해도 통과였다 → `on:` 에 `pull_request` 계열이 있는
  것만 센다. ⑶ `--project` 없는 맨 `playwright test`(= 전 project 실행, `pnpm e2e:all` 이 그
  형태)를 「fail-closed」라 적어 뒀는데 다른 호출과 **공존하면 fail-open** 이었다 → 전 project
  실행으로 모델링한다. ⑷ ★그 감사 **자신이 CI 에서 안 돌 수 있었다** — `ci.yml` 의 `frontend`
  필터가 `apps/web/**` 뿐이라 **워크플로만 고친 PR** 에서 통째로 skip 됐다(로컬 `final-gates.sh`
  의 `has_fe` 도 같았다). 둘 다 `.github/workflows/**` 를 물게 고쳤다.
  ★★★**2차 적대 리뷰가 두 갈래를 더 찾았다** (같은 날). ⑸ **`--project=` 를 명령 종류도 도달성도
  안 보고 셌다** — `run: echo --project=chromium-authed` 한 줄이나 `if: false` 스텝, 그리고
  `false && … || true` 로 **리터럴로 죽은 셸 분기**가 전부 「CI 에서 돈다」로 읽혔다. 실측 —
  `LOCAL_ONLY` 를 통째로 비운 채 `false && … || true` **한 줄**만 넣었더니 **10/10 초록**이었고
  playwright 는 0회 돌았다. → 이제 `if: false` job/step 을 지우고, 리터럴 단락 평가로 도달
  불가한 명령을 버린 뒤, **playwright 를 실제로 부르는 명령 안에서만** `--project=` 를 센다.
  ⑹ **면제 사유를 「공백 아닌 문자열」로만 재서** `{"new-project": "."}` 로 전건 초록이었다 →
  원장 식별자를 강제한다(위 괄호).
  ★**그 감사가 재지 못하는 것을 파일 머리 주석에 명시했다** — `paths:` 필터 · 입력 의존 `if:`
  조건식 · 리터럴이 아닌 셸 조건 · `uses:` 액션/재사용 워크플로. 정적 YAML 파싱의 원리적
  한계라 완전 해결은 아래 2단계 몫이다. 특히 **`live-smoke.yml` 에 authed 를 배선하고 면제를
  지우면 감사는 초록인데** 그 워크플로의 `paths:` 가 `apps/web/e2e/**` 를 안 물어 **authed spec
  만 고친 PR 에서는 0회**다 — 「감사가 초록이다」를 「PR 에서 돈다」로 읽지 마라.
- ★**아직 안 닫혔다 — 1단계만 했다.** CI 에 authed 잡을 세우려면 CI 전용 시더 + 로그인 배선이
  필요하고, [ADR-034] 가 CI 인증 secret 을 0개로 만든 결정이라 그 반전은 **사용자 결정**이다.
  그때까지 authed 게이트의 증인은 로컬 `final-gates.sh` 레그 하나뿐이다.

## 신규 BE 필드는 FE `.strict()` 스키마와 **항상** 대조해라 (2026-07-30, codex 적대 리뷰 MAJOR)

> ★★★**읽기 경로가 정상인 것은 쓰기 경로가 정상이라는 증거가 아니다.**

`StrategySettings` 에 필드를 추가하면 BE 가 그것을 **`default=None` 으로 emit** 하고
`strategy/service.py` 의 `update_settings` 가 `settings.model_dump()` 를 **그대로 JSONB 에 저장**한다.
FE `StrategySettingsSchema` 는 `.strict()` 라 모르는 키에서 **파싱이 실패**한다
⇒ **설정을 한 번만 저장해도 그 전략의 FE 파싱이 영구히 깨진다.**

★**GET 응답에는 그 키가 없어서**(BE 가 DB JSONB 를 그대로 돌려준다) **화면을 3개 돌아도 안 잡힌다.**
저장 경로에서만 터진다. 실제로 워커·평가자 둘 다 "동작 영향 없음" 으로 오판했고 codex 가 잡았다.
→ **BE 설정 스키마에 필드를 더하면 같은 PR 에서 `apps/web/src/features/strategy/schemas.ts` 를 고쳐라.**

★**그리고 `nullable` 필드면 FE 폼의 초기값 정규화까지 같은 PR 에서 해라** (2026-08-01, BL-570).
`schemas.ts` 를 맞추는 건 **파싱**을 맞추는 것이고, 깨지는 다음 자리는 **폼 초기값**이다 —
null 저장 → 초기 DOM 값 `""` → `setValueAs` 는 change 에서만 도는데 `z.number()…` 가 `""` 를 거부
→ `handleSubmit` 이 조용히 막고, 그 폼이 `formState.errors` 를 안 그리면 **아무 피드백도 없다.**
★**무편집 저장을 눌러봐야 보인다** — GET 도 「편집 후 저장」도 멀쩡해서 세 회차를 살아남았다.
