// 모든 e2e spec 이 playwright project 에 **정확히 하나** 물려 있는지 동결한다.
//
// ★왜 필요한가. `playwright.config.ts` 의 project 는 `testMatch` 정규식으로 spec 을 고른다.
// 그 목록이 **파일명 열거식**이면, 새 spec 을 추가하고 목록에 안 적었을 때 그 spec 은
// **발견조차 되지 않는다** — 테스트가 0건 실행돼도 playwright 는 초록이다. 설정 파일의
// 주석이 스스로 그 위험을 경고하고 있었다("열거식 testMatch 라 파일명을 여기 넣지 않으면
// spec 이 발견조차 안 된다 (coverage 함정)"). 실제로 `sprint55-optimizer-bayesian` 이
// 고아가 된 전력이 있다.
//
// ★반대 방향도 막는다. 한 spec 이 **두 project** 에 물리면 같은 테스트가 중복 실행된다.
// 이 감사를 처음 돌렸을 때 `live-smoke.spec.ts` 가 정확히 그 상태였다 —
// `chromium` 의 `/smoke\.spec\.ts$/` 가 앵커가 없어 `live-smoke.spec.ts` 까지 잡았고,
// 전용 project(`chromium-live-smoke`)와 겹쳤다. 그래서 `pnpm e2e` 가 live-smoke 를
// 매번 덤으로 돌리고 있었다.
//
// ★이 테스트는 config 를 **파싱**하지 않고 **import** 한다 — 정규식을 문자열로 다시 쓰면
// 실제 배선이 아니라 내 복사본을 검사하게 된다(이 레포가 반복해서 밟은 함정).
//
// ★★**세 번째 구멍 — 「project 에 물렸다」는 「어디선가 돈다」가 아니다** ([BL-789], 2026-08-17).
// 위 두 감사는 spec ↔ project 배선만 본다. 그런데 `chromium-authed` 는 **PR CI 에서 한 번도
// 호출되지 않는다** — `.github/workflows/*.yml` 이 부르는 것은 `--project=chromium` ·
// `chromium-live-smoke` · `chromium-design-canon` 뿐이다. 즉 authed 계열 spec 20개는
// CI 실행 표면이 0 이고, **CI 전건 초록이 그 spec 들의 통과를 뜻하지 않는다.** 아래
// 「CI 실행 표면」 감사가 그 사실을 코드로 고정한다 — CI 에서 안 도는 project 는
// `LOCAL_ONLY` 에 **사유와 함께** 등재돼야 하고, 새 project 를 만들고 워크플로에 안
// 배선하면 빨개진다.
//
// ★★★**이 감사는 「무엇이 그것을 발화시키나」를 세 번 틀렸다** (2026-08-17 적대 리뷰 실측).
// 셋 다 fail-**open** 이었고, 셋 다 이 파일이 막으려던 바로 그 병(「산문을 배선으로 읽는다」·
// 「돌았다고 적혀 있는데 실제로는 0건」)의 다른 문법이었다:
//   ⑴ `--project=` 를 YAML **본문 전체**에서 찾아 `- name: TODO --project=X 되살리기` 같은
//      **스텝 제목**을 실행으로 셌다 → 이제 `run:` 스텝의 셸 본문만 본다(`runScripts`).
//   ⑵ `.github/workflows/*.yml` 을 **전량 동등하게** 읽어 schedule/dispatch 전용 워크플로에
//      배선해도 「CI 에서 돈다」였다 → 이제 `on:` 에 `pull_request` 계열이 있는 것만 센다.
//   ⑶ `--project` 없는 맨 `playwright test`(= 전 project 실행, `pnpm e2e:all` 이 그 형태)를
//      「fail-closed 라 괜찮다」고 적어 뒀는데, 기존 `--project=` 호출과 **공존**하는 순간
//      fail-open 이었다 → 이제 전 project 실행으로 모델링한다.
// ★그리고 이 파일 자신이 **CI 에서 안 돌 수 있었다** — `ci.yml` 의 `frontend` 필터가
// `apps/web/**` 뿐이라 **워크플로만 고친 PR** 에서는 이 감사가 통째로 skip 됐다(= 감사의
// 입력을 고치는 회차에 감사가 안 돈다). `ci.yml` 의 `frontend:` 필터와 `final-gates.sh` 의
// FE vitest 조건에 `.github/workflows/**` 를 넣어 닫았다.

import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import config from "../../playwright.config";

const E2E_DIR = path.resolve(__dirname, "../../e2e");
const REPO_ROOT = path.resolve(__dirname, "../../../..");
const WORKFLOW_DIR = path.join(REPO_ROOT, ".github/workflows");
const WEB_PACKAGE_JSON = path.resolve(__dirname, "../../package.json");

/**
 * CI 에서 **의도적으로** 안 도는 project — 이름 → 사유.
 *
 * ★사유 없이 넣지 마라. 이 상수는 「빠뜨린 것」과 「일부러 뺀 것」을 가르는 유일한 장치이고,
 * 사유가 없으면 다음 사람은 둘을 구분할 수 없다.
 */
const LOCAL_ONLY: Record<string, string> = {
  "chromium-authed":
    "[BL-789] 1단계만 착수 — CI 에 authed 잡을 신설하려면 CI 전용 시더 + 로그인 배선이 필요하고, " +
    "[ADR-034] 가 CI 인증 secret 을 0개로 만든 결정이라 그 반전은 사용자 결정 사항이다. " +
    "★그래서 **CI 초록은 authed 통과의 증거가 아니다** — 증인은 로컬 실행뿐이다" +
    "(`final-gates.sh` 의 `e2e authed` 레그 · `mise run fe-e2e-authed` · `pnpm e2e:authed` · " +
    "`tools/scripts/e2e-authed-repro.sh`).",
  setup:
    "`global.setup.ts` — E2E_AUTH_* 계정으로 로그인해 storageState 를 발급한다. `chromium-authed` 전용 dependency 라 " +
    "그것이 CI 로 올라가기 전까지 같이 로컬 전용이다([BL-789]).",
  "setup-authed-reachability":
    "authed API 도달성 프로브. `chromium-authed` 전용 dependency 라 같이 로컬 전용이다([BL-789]).",
};

/** PR 체크로 발화하는 트리거 — 이것이 없으면 「PR 이 초록이다」와 무관한 워크플로다. */
const PR_TRIGGERS = ["pull_request", "pull_request_target", "merge_group"];

/** YAML 통줄 주석 제거. */
function stripYamlComments(text: string): string {
  return text
    .split("\n")
    .filter((line) => !/^\s*#/.test(line))
    .join("\n");
}

function matchAll(text: string, re: RegExp): string[] {
  return [...text.matchAll(re)].map((m) => m[1] ?? "");
}

/**
 * 이 워크플로가 **PR 체크로 발화하는가** — 최상위 `on:` 에 `pull_request` 계열이 있는가.
 *
 * ★★없으면 「CI 에서 돈다」로 세면 안 된다. `trust-layer-nightly.yml`(schedule+dispatch) 나
 * `nightly-real-broker.yml`(dispatch 전용) 에 `--project=chromium-authed` 를 배선하는 것만으로
 * 이 감사를 통과시킬 수 있었고, 그때도 **PR CI 는 authed 를 0회 돈다** — 이 절이 막으려던
 * 거짓 초록 그 자체다(2026-08-17 적대 리뷰가 실측으로 재현).
 * ★`push:` 는 세지 않는다 — 머지 **뒤**에 도는 트리거라 PR 을 막지 못한다.
 * ★키가 `"on":` 로 따옴표에 싸인 형태도 받는다(`nightly-real-broker.yml` 이 그렇다).
 */
function isPullRequestGated(workflowText: string): boolean {
  const lines = stripYamlComments(workflowText).split("\n");
  for (let i = 0; i < lines.length; i++) {
    const head = /^(["']?)on\1\s*:(.*)$/.exec(lines[i] ?? "");
    if (!head) continue;
    const block = [head[2] ?? ""]; // `on: [push, pull_request]` 인라인 형태
    for (let j = i + 1; j < lines.length; j++) {
      const line = lines[j] ?? "";
      if (line.trim() === "") continue;
      if (!/^\s/.test(line)) break; // 다음 최상위 키
      block.push(line);
    }
    const text = block.join("\n");
    return PR_TRIGGERS.some((t) => new RegExp(`\\b${t}\\b`).test(text));
  }
  return false;
}

/**
 * 워크플로에서 **`run:` 스텝의 셸 본문만** 뽑는다.
 *
 * ★★`name:`·`if:`·`env:` 같은 스칼라 값은 실행이 아니다. YAML 본문 전체를 정규식으로 훑으면
 * `- name: TODO 언젠가 --project=chromium-authed 를 되살릴 것` 같은 **스텝 제목**이 배선으로
 * 읽힌다 — 이 파일이 주석에 대해 막아 둔 병이 다른 문법으로 그대로 남아 있었다(적대 리뷰 실측).
 * `ci.yml`·`live-smoke.yml` 은 이미 `- name: Run live smoke (chromium-live-smoke project)` 같은
 * 서술형 스텝명을 쓰므로 가상의 위험이 아니다.
 *
 * ★한계: `uses:` 액션의 `with:` 인자로 playwright 를 부르는 형태는 모델링하지 않는다. 그 경우
 * 「아무 데서도 안 돈다」로 읽혀 아래 ⑶ 이 빨개진다 = fail-closed.
 *
 * ★★**접기(`>`)와 그대로(`|`)를 구분해야 한다.** `ci.yml` 의 e2e 스텝이 `run: >` 로 한 명령을
 * 두 줄에 쓴다 — 이것을 줄바꿈으로 이어 붙이면 `pnpm exec playwright test` 와
 * `--project=…` 가 **다른 명령**으로 쪼개져 「`--project` 없는 맨 호출」로 오독된다
 * (실제로 첫 구현이 그렇게 읽어 authed 를 「CI 에서 돈다」로 판정했다).
 */
function runScripts(text: string): string[] {
  const lines = text.split("\n");
  const out: string[] = [];
  for (let i = 0; i < lines.length; i++) {
    const head = /^(\s*(?:-\s+)?)run:(.*)$/.exec(lines[i] ?? "");
    if (!head) continue;
    const keyCol = (head[1] ?? "").length;
    const first = (head[2] ?? "").trim();
    const isIndicator = /^[|>][-+]?\d*$/.test(first);
    // `|` = 그대로(줄이 곧 명령) · `>` 와 지시자 없는 평문 = 접기(줄이 공백으로 이어진다).
    const joiner = first.startsWith("|") ? "\n" : " ";
    const body = first === "" || isIndicator ? [] : [first];
    let j = i + 1;
    for (; j < lines.length; j++) {
      const line = lines[j] ?? "";
      if (line.trim() === "") continue;
      if (line.length - line.trimStart().length <= keyCol) break;
      body.push(line.trim());
    }
    i = j - 1;
    out.push(body.join(joiner));
  }
  return out;
}

/**
 * 셸 본문을 「명령」 단위로 쪼갠다 — `--project` 유무를 명령마다 따로 봐야 한다.
 * ★역슬래시 줄바꿈은 먼저 잇는다. 안 그러면 `playwright test \` + `--project=X` 가 두 명령이
 * 되고, 앞 조각이 「맨 호출」로 읽혀 전 project 실행으로 오판된다(fail-open).
 */
function splitCommands(script: string): string[] {
  return script.replace(/\\\n/g, " ").split(/\n|&&|\|\||[;|]/);
}

/**
 * 워크플로 본문이 **실제로 실행하는** playwright project 이름.
 *
 * ★주석을 먼저 지운다. `ci.yml` 은 「P1 4라우트는 전부 authed 라 로컬 `pnpm e2e:authed` 몫이고
 * CI 에는 없다」 같은 산문을 갖고 있다 — 산문을 배선으로 읽으면 이 감사는 정확히 반대 답을 낸다.
 * 이 레포는 **주석 문자열이 감사기를 통과시킨 사고**를 이미 겪었다(2026-08-16 layout-alignment).
 * ★한계: 줄 끝 인라인 `#` 주석은 안 지운다(YAML 문자열 안의 `#` 과 구분 불가).
 *
 * ★`pnpm <script>` 도 푼다 — `package.json` 스크립트가 `--project=` 를 품고 있으면 그것도 실행이다.
 * ★★`--project` **없는** `playwright test` 는 **전 project 실행**으로 센다. `package.json` 의
 * `e2e:all` 이 정확히 그 형태다. 종전 주석은 이것을 「모델링 안 함 = fail-closed」라고 적었는데
 * 반대였다 — 다른 `--project=` 호출과 공존하면 `direct` 가 비지 않아 ABORT 도 안 걸리고,
 * authed 가 CI 에서 실제로 도는데도 `LOCAL_ONLY` 의 「CI 에서 안 돈다」가 거짓인 채 초록이 된다.
 */
function executedProjects(
  workflowText: string,
  scripts: Record<string, string>,
  allProjects: string[],
): Set<string> {
  const out = new Set<string>();
  const resolved = new Set<string>(); // pnpm 스크립트 순환 방지

  const walk = (script: string): void => {
    for (const cmd of splitCommands(script)) {
      const named = matchAll(cmd, /--project(?:=|\s+)([A-Za-z0-9_.:-]+)/g).filter(Boolean);
      for (const n of named) out.add(n);
      if (named.length === 0 && /\bplaywright\s+test\b/.test(cmd))
        for (const n of allProjects) out.add(n);
      for (const invoked of matchAll(cmd, /\bpnpm(?:\s+run)?\s+([A-Za-z0-9:_-]+)/g)) {
        if (resolved.has(invoked)) continue;
        resolved.add(invoked);
        const next = scripts[invoked];
        if (next) walk(next);
      }
    }
  };

  for (const runBody of runScripts(stripYamlComments(workflowText))) walk(runBody);
  return out;
}

/** `dependencies` 를 따라 전이 폐포 — CI 가 부른 project 의 dependency 도 CI 에서 돈다. */
function withDependencies(seed: Set<string>): Set<string> {
  const deps = new Map(
    (config.projects ?? []).map((p) => [p.name ?? "", (p.dependencies ?? []) as string[]]),
  );
  const out = new Set(seed);
  const queue = [...seed];
  while (queue.length > 0) {
    for (const d of deps.get(queue.shift() as string) ?? []) {
      if (!out.has(d)) {
        out.add(d);
        queue.push(d);
      }
    }
  }
  return out;
}

/**
 * `e2e/` **재귀** spec 목록 (codex P2).
 *
 * ★playwright 는 `testDir` 아래를 재귀 수집한다. 직속 파일만 훑으면 앞으로 생길
 * `e2e/foo/new.spec.ts` 가 고아여도 이 감사가 초록이다 — 감사가 막으려던 바로 그 구멍이
 * 감사 자신에게 생긴다.
 */
function specFiles(dir = E2E_DIR, prefix = "e2e"): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const rel = `${prefix}/${entry.name}`;
    if (entry.isDirectory()) {
      if (entry.name === "node_modules" || entry.name === ".auth") continue;
      out.push(...specFiles(path.join(dir, entry.name), rel));
    } else if (entry.name.endsWith(".spec.ts")) {
      out.push(rel);
    }
  }
  return out.sort();
}

/**
 * playwright 가 그 파일을 이 project 에 넣는가 — testMatch/testIgnore 를 실제 값으로 평가.
 *
 * ★**모델링할 수 없는 형태는 통과시키지 않고 던진다** (codex P2). playwright 는 string 패턴을
 * glob 으로, 경로를 절대경로로 다룬다. 여기서 그걸 `endsWith` 로 흉내 내면 감사는 초록인데
 * 실제 배선은 다른 상태가 만들어질 수 있다. 현재 배선은 전부 RegExp 라 정확하고, 누군가
 * string/glob 을 도입하는 순간 **조용히 부정확해지는 대신 빨개진다.**
 */
function matches(pattern: unknown, relPath: string): boolean {
  if (pattern instanceof RegExp) return pattern.test(relPath);
  if (Array.isArray(pattern)) return pattern.some((p) => matches(p, relPath));
  if (pattern === undefined || pattern === null) return false;
  throw new Error(
    `이 감사는 RegExp 패턴만 충실히 모델링한다. 받은 것: ${JSON.stringify(pattern)}\n` +
      "playwright 의 glob/절대경로 의미론과 어긋날 수 있으므로 통과시키지 않는다. " +
      "패턴을 RegExp 로 바꾸거나, 이 함수를 playwright 실제 의미론으로 확장해라.",
  );
}

function owningProjects(relPath: string): string[] {
  return (config.projects ?? [])
    .filter((p) => {
      const name = p.name ?? "";
      if (name === "setup") return false; // global.setup.ts 전용 — spec 이 아니다
      if (!matches(p.testMatch, relPath)) return false;
      if (p.testIgnore && matches(p.testIgnore, relPath)) return false;
      return true;
    })
    .map((p) => p.name ?? "(unnamed)");
}

describe("e2e project 배선", () => {
  it("모든 spec 이 정확히 한 project 에 속한다", () => {
    const files = specFiles();
    expect(files.length).toBeGreaterThan(10); // 음성 대조 — 수집이 죽으면 여기서 잡는다

    const orphans: string[] = [];
    const duplicates: Array<[string, string[]]> = [];

    for (const f of files) {
      const owners = owningProjects(f);
      if (owners.length === 0) orphans.push(f);
      else if (owners.length > 1) duplicates.push([f, owners]);
    }

    expect(
      { orphans, duplicates },
      `고아(어느 project 에도 안 물려 실행조차 안 됨): ${JSON.stringify(orphans)}\n` +
        `중복(두 project 에서 같은 spec 을 돌림): ${JSON.stringify(duplicates)}`,
    ).toEqual({ orphans: [], duplicates: [] });
  });

  it("authed project 는 열거식이 아니라 잔여 전체를 가져간다", () => {
    // ★열거식으로 되돌아가면 새 authed spec 이 다시 조용히 누락된다.
    //   `testMatch` 에 개별 파일명이 나열돼 있으면 빨개진다.
    const authed = (config.projects ?? []).find((p) => p.name === "chromium-authed");
    expect(authed, "chromium-authed project 가 사라졌다").toBeTruthy();

    const src = String(authed?.testMatch);
    expect(
      src.includes("trading-ui") || src.includes("dogfood-flow"),
      `chromium-authed.testMatch 가 파일명을 열거하고 있다: ${src}\n` +
        "잔여 전체를 가져가고 다른 project 몫만 testIgnore 로 빼는 형태여야 한다.",
    ).toBe(false);
  });

  it("authed 전용 도달성 setup 만 chromium-authed 를 막는다", () => {
    const projects = config.projects ?? [];
    const reachability = projects.find((p) => p.name === "setup-authed-reachability");
    const authed = projects.find((p) => p.name === "chromium-authed");
    const publicChromium = projects.find((p) => p.name === "chromium");

    expect(reachability, "authed 도달성 setup project 가 사라졌다").toBeTruthy();
    expect(reachability?.testMatch).toEqual(/authed-reachability\.setup\.ts$/);
    expect(reachability?.dependencies).toEqual(["setup", "setup-identity"]);
    expect(authed?.dependencies).toEqual(["setup-authed-reachability"]);
    expect(publicChromium?.dependencies).toEqual(["setup-identity"]);
  });
});

const ALL_PROJECTS = ["chromium", "chromium-authed", "chromium-design-canon"];

describe("CI 실행 표면 ([BL-789])", () => {
  it("주석·스텝 이름 같은 **산문**은 실행으로 세지 않는다", () => {
    // ★양성/음성 대조를 같이 둔다. 이 감사의 판별력은 「산문을 배선으로 읽지 않는다」에
    //   달려 있으므로 그것을 따로 증명한다. 픽스처는 인라인이다 — 실파일 문구에 앵커를
    //   걸면 그 문구가 바뀌는 순간 이 시험이 무엇을 재는지 알 수 없게 된다.
    const scripts = { "e2e:authed": "playwright test --project=chromium-authed" };
    const fixture = [
      "jobs:",
      "  e2e:",
      "    steps:",
      "      # P1 4라우트는 전부 authed 라 로컬 `pnpm e2e:authed` 몫이고 CI 에는 없다.",
      "      - name: TODO 언젠가 --project=chromium-authed 를 되살릴 것",
      "        run: |",
      "          # pnpm exec playwright test --project=chromium-design-canon",
      "          pnpm exec playwright test --project=chromium",
    ].join("\n");

    expect(executedProjects(fixture, scripts, ALL_PROJECTS)).toEqual(new Set(["chromium"]));

    // 음성 대조 ① — 주석을 안 지우면 답이 달라진다(= 주석 제거가 하중을 받고 있다).
    expect(executedProjects(fixture.replace(/^(\s*)#/gm, "$1"), scripts, ALL_PROJECTS)).toEqual(
      new Set(["chromium", "chromium-design-canon"]),
    );

    // 음성 대조 ② — **같은 문자열**을 `run:` 으로 옮기면 잡힌다. 즉 위 결과가
    //   「못 찾아서」가 아니라 「스텝 제목이라서」임을 증명한다(항진명제 차단).
    const asRun = fixture.replace(
      "      - name: TODO 언젠가 --project=chromium-authed 를 되살릴 것",
      "      - run: pnpm exec playwright test --project=chromium-authed",
    );
    expect(executedProjects(asRun, scripts, ALL_PROJECTS)).toEqual(
      new Set(["chromium", "chromium-authed"]),
    );
  });

  it("`--project` 없는 `playwright test` 는 전 project 실행으로 센다", () => {
    // ★`package.json` 의 `e2e:all` 이 이 형태다. 모델링하지 않으면 authed 가 CI 에서
    //   실제로 도는데도 감사가 못 본다(fail-open).
    const bare = "      - run: pnpm exec playwright test";
    expect(executedProjects(bare, {}, ALL_PROJECTS)).toEqual(new Set(ALL_PROJECTS));

    // 스크립트 경유도 같다.
    const viaScript = "      - run: pnpm e2e:all";
    expect(executedProjects(viaScript, { "e2e:all": "playwright test" }, ALL_PROJECTS)).toEqual(
      new Set(ALL_PROJECTS),
    );

    // 음성 대조 — `playwright install` 은 실행이 아니다.
    expect(
      executedProjects("      - run: pnpm exec playwright install --with-deps chromium", {}, [
        ...ALL_PROJECTS,
      ]),
    ).toEqual(new Set());
  });

  it("PR 에서 발화하지 않는 워크플로는 CI 실행으로 세지 않는다", () => {
    const nightly = ["on:", "  schedule:", '    - cron: "0 18 * * *"', "  workflow_dispatch:"].join(
      "\n",
    );
    const dispatchOnly = ['"on":', "  # schedule:", '  #   - cron: "0 18 * * *"', "  workflow_dispatch:"].join("\n"); // prettier-ignore
    const pr = ["on:", "  pull_request:", "    branches: [main]"].join("\n");

    expect(isPullRequestGated(nightly)).toBe(false);
    expect(isPullRequestGated(dispatchOnly)).toBe(false); // `"on":` 따옴표 형태
    expect(isPullRequestGated(pr)).toBe(true);
    expect(isPullRequestGated(["on: [push, pull_request]"].join("\n"))).toBe(true); // 인라인 flow
    expect(isPullRequestGated(["on:", "  push:", "    branches: [main]"].join("\n"))).toBe(false);

    // ★실파일 대조 — 픽스처만 재면 실 워크플로 문법에 대해 아무 말도 못 한다.
    expect(
      isPullRequestGated(readFileSync(path.join(WORKFLOW_DIR, "ci.yml"), "utf8")),
      "ci.yml 이 PR 게이트가 아니라고 나왔다 — 파서가 죽었거나 트리거가 바뀌었다.",
    ).toBe(true);
  });

  it("모든 project 는 PR CI 에서 실제로 돌거나 LOCAL_ONLY 에 사유와 함께 등재돼 있다", () => {
    const projectNames = (config.projects ?? []).map((p) => p.name ?? "").filter(Boolean);
    const workflows = readdirSync(WORKFLOW_DIR).filter(
      (f) => f.endsWith(".yml") || f.endsWith(".yaml"),
    );
    const scripts = (
      JSON.parse(readFileSync(WEB_PACKAGE_JSON, "utf8")) as { scripts?: Record<string, string> }
    ).scripts;

    // ★양쪽이 비면 ABORT. 0건을 「일치」로 읽으면 판별력이 0 이다(이 레포 상습 사고).
    if (projectNames.length === 0) throw new Error("ABORT — playwright project 를 0개 읽었다.");
    if (workflows.length === 0) throw new Error(`ABORT — ${WORKFLOW_DIR} 에 워크플로가 0개다.`);
    if (!scripts) throw new Error(`ABORT — ${WEB_PACKAGE_JSON} 에 scripts 가 없다.`);

    const anyWorkflow = new Set<string>(); // 트리거 무관 — 오타 검출용
    const direct = new Set<string>(); // PR 게이트 워크플로만 — 「CI 초록」의 근거
    const prGated: string[] = [];
    for (const f of workflows) {
      const text = readFileSync(path.join(WORKFLOW_DIR, f), "utf8");
      const names = executedProjects(text, scripts, projectNames);
      for (const n of names) anyWorkflow.add(n);
      if (!isPullRequestGated(text)) continue;
      prGated.push(f);
      for (const n of names) direct.add(n);
    }
    if (prGated.length === 0)
      throw new Error("ABORT — PR 에서 발화하는 워크플로를 0개 골랐다. 트리거 파서가 죽었다.");
    if (direct.size === 0)
      throw new Error(
        "ABORT — PR 워크플로에서 실행되는 playwright project 를 0개 추출했다. 파서가 죽었다.",
      );

    const inCI = withDependencies(direct);

    // ⑴ 워크플로가 부르는 이름이 config 에 실재하는가 (오타 = 조용한 0건 실행).
    //   ★여기만 트리거를 안 본다 — nightly 의 오타도 「돈다고 적혀 있는데 0건」이다.
    expect(
      [...anyWorkflow].filter((n) => !projectNames.includes(n)),
      `워크플로가 존재하지 않는 project 를 부른다 — playwright 는 그것을 0건으로 돌고 초록이다.`,
    ).toEqual([]);

    // ⑵ LOCAL_ONLY 가 낡지 않았는가 (사라진 project 의 면제가 남아 있으면 다음 신설을 가린다).
    expect(
      Object.keys(LOCAL_ONLY).filter((n) => !projectNames.includes(n)),
      "LOCAL_ONLY 에 config 에 없는 project 가 남아 있다. 지워라.",
    ).toEqual([]);

    // ⑶ 본체 — PR CI 에서 실행되지도, 면제되지도 않은 project 는 아무 데서도 안 도는 것이다.
    expect(
      projectNames.filter((n) => !inCI.has(n) && !LOCAL_ONLY[n]?.trim()),
      "이 project 는 PR 에서 발화하는 워크플로 어디에서도 실행되지 않는다.\n" +
        "워크플로에 --project= 로 배선하거나, LOCAL_ONLY 에 **사유와 함께** 등재해라.\n" +
        `PR 게이트 워크플로: ${JSON.stringify(prGated.sort())}\n` +
        `그것들이 실제로 부르는 것: ${JSON.stringify([...direct].sort())}`,
    ).toEqual([]);

    // ⑷ 면제와 실행이 겹치면 LOCAL_ONLY 사유가 거짓이다.
    //   ★`direct` 가 아니라 `inCI` 로 잰다 — 전이 dependency 로만 CI 에 편입된 project 는
    //     ⑶ 이 `inCI` 로 통과시키므로, ⑷ 이 `direct` 만 보면 「로컬 전용」이라는 **거짓 사유**가
    //     그대로 늙는다(2026-08-17 적대 리뷰). 두 단언의 기준을 같은 집합으로 맞춘다.
    expect(
      Object.keys(LOCAL_ONLY).filter((n) => inCI.has(n)),
      "LOCAL_ONLY 인데 PR CI 에서 실제로 돈다(직접 호출 또는 dependency 경유) — 사유가 거짓이 됐으니 목록에서 빼라.",
    ).toEqual([]);
  });
});
