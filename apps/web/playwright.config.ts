import { defineConfig, devices } from "@playwright/test";

import { getBaseURL, getFrontendPort, hasConfiguredBaseURL } from "./e2e/_base-url";

// Sprint FE-01 LESSON-004: React Query + Next.js 조합 infinite loop 검출용 E2E.
// vitest jsdom이 못 잡는 Fast Refresh / StrictMode / Query refetch 케이스 실제 브라우저 재현.
//
// CI/로컬 모두 pnpm dev 사용 — prod build는 Clerk API 의존 페이지가 prerender 실패.
// dev는 Clerk placeholder key로도 기동 가능. CI ubuntu는 초기 컴파일이 느리니 240s 대기.
//
// Sprint 25 — projects 분리 (codex G.0 iter 1 P1 #4 + iter 2 P2 #3):
//   chromium         — public routes only (smoke.spec.ts)
//   chromium-authed  — Clerk authed only (trading-ui, dogfood-flow). storageState 의존
//   setup            — global.setup.ts 가 chromium-authed 시작 전 storageState 발급
//
// chromium-authed 는 fullyParallel:false + --workers=1 (script 명시) 이중 보장 —
// 공유 storageState flake 차단.
const isCI = !!process.env.CI;
const baseURL = getBaseURL();
const fePort = getFrontendPort();

// [BL-784] 관측 모드 — `PW_ARTIFACT_RUN=<이름>` 을 주면 그 회차의 아티팩트를 격리 보관한다.
//
// ★왜 필요한가 (2026-08-17 실측). playwright 는 매 실행의 setup 단계에서 **`outputDir` 을 통째로
//   지운다**(`runner/tasks.js` `createRemoveOutputDirsTask`). 이 레포의 project 7종은 전부 기본
//   `test-results/` 를 공유하므로 **어떤 `--project` 로 돌리든 직전 회차 증거가 사라진다.**
//   게이트는 `e2e chromium` → `e2e design-canon` → `e2e authed` 를 이 순서로 부르고, 그 뒤에
//   사람이 「단독으로도 실패하나」를 확인하려고 한 번 더 돌리는 순간 **게이트 실패의 trace 가
//   그 확인 행위 자체에 의해 파괴된다.** [BL-784] 가 「실패 시점 trace 가 없다」였던 이유가 이것이다.
//
// 켜면 셋이 바뀐다: 회차 전용 `outputDir` · `trace: "on"`(실패 안 해도 남는다) ·
// 회차별 `results.json`(테스트별 통과/실패 목록).
//
// ★한 회차 안에서 레그가 서로를 지우지 않게 **project 별로 한 겹 더 나눈다.** 게이트는 한 번
//   실행에서 e2e 를 세 번 부르므로, 이 겹이 없으면 `PW_ARTIFACT_RUN` 을 하나 걸어도 마지막
//   레그가 앞의 둘을 지운다 — 고치려던 병이 그대로 재현된다.
// ★★겹은 **project 설정**으로 준다. `process.argv` 에서 `--project` 를 읽는 방식은 틀렸다 —
//   config 는 워커 프로세스에서도 평가되는데 워커의 argv 에는 그 플래그가 없어서, 지움 계산
//   (메인)과 아티팩트 기록(워커)이 **서로 다른 디렉터리**를 가리킨다. 2026-08-17 에 실제로
//   `<회차>/chromium-authed/results.json` 과 `<회차>/all/<테스트>/trace.zip` 으로 갈렸다.
const sanitizeArtifactSegment = (value: string) => value.replace(/[^A-Za-z0-9._-]/g, "-");

const rawArtifactRun = process.env.PW_ARTIFACT_RUN?.trim();
const artifactRun = rawArtifactRun ? sanitizeArtifactSegment(rawArtifactRun) : undefined;
const artifactDirFor = (projectName: string) =>
  artifactRun ? `test-results/${artifactRun}/${projectName}` : undefined;

// reporter 는 메인 프로세스에서 한 번만 평가되므로 여기서는 argv 를 봐도 안전하다. 이름을
// project 겹과 맞춰 두면 `results.json` 이 그 project 의 아티팩트와 같은 폴더에 떨어진다.
function getProjectFilterSegment(): string {
  const argv = process.argv;
  const names: string[] = [];
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i] ?? "";
    const next = argv[i + 1];
    if (arg.startsWith("--project=")) {
      names.push(arg.slice("--project=".length));
    } else if (arg === "--project" && next !== undefined) {
      names.push(next);
    }
  }
  return names.length > 0 ? sanitizeArtifactSegment(names.join("+")) : "all";
}

const reporterDir = artifactRun
  ? `test-results/${artifactRun}/${getProjectFilterSegment()}`
  : undefined;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: isCI,
  retries: isCI ? 2 : 0,
  workers: isCI ? 1 : undefined,
  reporter: reporterDir
    ? [["list"], ["json", { outputFile: `${reporterDir}/results.json` }]]
    : isCI
      ? [["github"], ["list"]]
      : "list",
  use: {
    baseURL,
    trace: artifactRun ? "on" : "retain-on-failure",
    video: "retain-on-failure",
    screenshot: "only-on-failure",
    // Sprint 25 — Next.js 16 dev server 첫 page render JIT 컴파일 5-30초.
    // setup pre-warm 후 cache hit 으로 빨라지지만 안전망으로 navigation 60s, action 30s.
    navigationTimeout: 60_000,
    actionTimeout: 30_000,
  },
  projects: [
    {
      name: "setup",
      outputDir: artifactDirFor("setup"),
      testMatch: /global\.setup\.ts$/,
    },
    {
      name: "setup-identity",
      outputDir: artifactDirFor("setup-identity"),
      testMatch: /identity\.setup\.ts$/,
    },
    {
      // authed API 요청을 실제 브라우저에서 한 번 관측한다. 공개 project 는 물지 않는다.
      name: "setup-authed-reachability",
      outputDir: artifactDirFor("setup-authed-reachability"),
      testMatch: /authed-reachability\.setup\.ts$/,
      dependencies: ["setup", "setup-identity"],
    },
    {
      // ★앵커가 필요하다. `/smoke\.spec\.ts$/` 는 접두가 없어 **`live-smoke.spec.ts` 까지**
      //   잡았고, 전용 project(`chromium-live-smoke`)와 겹쳐 `pnpm e2e` 가 live-smoke 를
      //   매번 덤으로 돌리고 있었다(2026-08-06 `e2e-project-wiring.test.ts` 가 실측으로 적발).
      name: "chromium",
      outputDir: artifactDirFor("chromium"),
      testMatch: /(^|\/)smoke\.spec\.ts$/,
      use: { ...devices["Desktop Chrome"] },
      dependencies: ["setup-identity"],
    },
    // Sprint 31-D BL-157 — live dev smoke gate (.github/workflows/live-smoke.yml 전용).
    // public pages (Clerk 미의존) console.error / pageerror 0 검증 — chart lib
    // SSR/CSR boundary throw 같은 dogfood Day 3 currentColor 회귀 차단.
    // 별도 project 로 분리한 이유: 기본 `chromium` 은 smoke.spec.ts 만 매치하므로
    // live-smoke 는 명시적 --project 호출 (e2e 워크플로우 영향 없음).
    {
      name: "chromium-live-smoke",
      outputDir: artifactDirFor("chromium-live-smoke"),
      testMatch: /live-smoke\.spec\.ts$/,
      use: { ...devices["Desktop Chrome"] },
      dependencies: ["setup-identity"],
    },
    // C 디자인 언어 이식 S0 — 인증 없는 디자인 캐논 게이트.
    // 공개 라우트만 쓰므로 CI 에서 돌릴 수 있다 (`pnpm e2e:design-canon`).
    // P1 4라우트는 전부 authed 라 `chromium-authed` 몫이고 로컬 전용이다.
    {
      name: "chromium-design-canon",
      outputDir: artifactDirFor("chromium-design-canon"),
      testMatch: /design-canon-.*\.spec\.ts$/,
      use: { ...devices["Desktop Chrome"] },
      dependencies: ["setup-identity"],
    },
    {
      name: "chromium-authed",
      outputDir: artifactDirFor("chromium-authed"),
      // Sprint 38 BL-188 v3 D — `backtest-live-mirror` 추가 (5 case Live mirror E2E).
      // Sprint 46 W2 — `sprint46-tier1-critical` 추가 (5 case Tier 1 critical user journey).
      // Sprint 46 W3 — `sprint46-tier2-high` 추가 (4 case Tier 2 dogfood polish).
      // Sprint 46 W4 — `sprint46-tier3-nth` 추가 (Tier 3 polish 7 시나리오).
      // C 이식 W3-C — `sprint55-optimizer-bayesian` 재작성 완료(현행 UX: SelectWithDisplayName 피커 +
      //   "최적화 알고리즘" aria-label + "베이지안 탐색 새 실행")로 skip 해제 + 배선.
      // C 이식 S0 — `authed-canon-p1` 추가 (P1 4라우트 디자인 캐논 baseline, 로컬 전용).
      // C 이식 W2 — `authed-canon-remaining` 추가 (잔여 authed 라우트 캐논 게이트, /backtests/[id] 등).
      //   열거식 testMatch 라 파일명을 여기 넣지 않으면 spec 이 발견조차 안 된다 (coverage 함정).
      //   W3-C — 고아 spec `sprint55-optimizer-bayesian` 재작성 후 재배선.
      // functional-parity — `authed-functional-parity` 추가 (주문취소 A2 / nav-count B2 /
      //   backtest_count B1 / 대시보드 링크 A1 회귀 가드 5 case).
      //
      // ★2026-08-06 — **열거식을 뒤집었다.** 예전에는 파일명 14개를 여기 나열했고, 새 authed
      //   spec 을 추가하면서 이 줄을 안 고치면 **그 spec 이 발견조차 안 됐다**(위 주석이 스스로
      //   경고하던 "coverage 함정"이고 `sprint55-optimizer-bayesian` 이 실제로 고아였던 전력).
      //   이제 **잔여 전체**를 가져가고 다른 project 몫만 `testIgnore` 로 뺀다 — 신규 authed
      //   spec 은 파일을 만들기만 하면 자동으로 돈다.
      //   ★열거식으로 되돌아가거나 배선이 겹치면 `src/__tests__/e2e-project-wiring.test.ts` 가 막는다.
      testMatch: /\.spec\.ts$/,
      testIgnore: [
        /(^|\/)smoke\.spec\.ts$/, // chromium
        /live-smoke\.spec\.ts$/, // chromium-live-smoke
        /design-canon-.*\.spec\.ts$/, // chromium-design-canon
      ],
      fullyParallel: false,
      use: {
        ...devices["Desktop Chrome"],
        storageState: "e2e/.auth/storageState.json",
      },
      dependencies: ["setup-authed-reachability"],
    },
  ],
  webServer: hasConfiguredBaseURL()
    ? undefined
    : {
        command: `pnpm dev --port ${fePort}`,
        url: baseURL,
        reuseExistingServer: !isCI,
        timeout: isCI ? 240_000 : 120_000,
        stdout: "pipe",
        stderr: "pipe",
      },
});
