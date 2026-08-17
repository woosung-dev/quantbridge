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
// 위 두 감사는 spec ↔ project 배선만 본다. 그런데 `chromium-authed` 는 **CI 에서 한 번도
// 호출되지 않는다** — `.github/workflows/*.yml` 이 부르는 것은 `--project=chromium` ·
// `chromium-live-smoke` · `chromium-design-canon` 뿐이다. 즉 authed 계열 spec 20개는
// 로컬 `final-gates.sh` 밖에서는 실행 표면이 0 이고, **CI 전건 초록이 그 spec 들의 통과를
// 뜻하지 않는다.** 아래 「CI 실행 표면」 감사가 그 사실을 코드로 고정한다 — CI 에서 안 도는
// project 는 `LOCAL_ONLY` 에 **사유와 함께** 등재돼야 하고, 새 project 를 만들고 워크플로에
// 안 배선하면 빨개진다.

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
    "★그래서 **CI 초록은 authed 통과의 증거가 아니다** — 로컬 `final-gates.sh` 의 `e2e authed` 만이 증인이다.",
  setup:
    "`global.setup.ts` — E2E_AUTH_* 계정으로 로그인해 storageState 를 발급한다. `chromium-authed` 전용 dependency 라 " +
    "그것이 CI 로 올라가기 전까지 같이 로컬 전용이다([BL-789]).",
  "setup-authed-reachability":
    "authed API 도달성 프로브. `chromium-authed` 전용 dependency 라 같이 로컬 전용이다([BL-789]).",
};

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
 * 워크플로 본문이 **실제로 실행하는** playwright project 이름.
 *
 * ★주석을 먼저 지운다. `ci.yml` 은 「P1 4라우트는 전부 authed 라 로컬 `pnpm e2e:authed` 몫이고
 * CI 에는 없다」 같은 산문을 갖고 있다 — 산문을 배선으로 읽으면 이 감사는 정확히 반대 답을 낸다.
 * 이 레포는 **주석 문자열이 감사기를 통과시킨 사고**를 이미 겪었다(2026-08-16 layout-alignment).
 * ★한계: 줄 끝 인라인 `#` 주석은 안 지운다(YAML 문자열 안의 `#` 과 구분 불가).
 *
 * ★`pnpm <script>` 도 푼다 — `package.json` 스크립트가 `--project=` 를 품고 있으면 그것도 실행이다.
 * ★한계: `--project` 없는 `playwright test`(= 전 project 실행)는 모델링하지 않는다. 쓰이면
 * 거짓 red 가 나지만 그 방향은 fail-closed 다.
 */
function executedProjects(workflowText: string, scripts: Record<string, string>): Set<string> {
  const body = stripYamlComments(workflowText);
  const names = matchAll(body, /--project(?:=|\s+)([A-Za-z0-9_.:-]+)/g);
  for (const invoked of matchAll(body, /\bpnpm(?:\s+run)?\s+([A-Za-z0-9:_-]+)/g)) {
    const script = scripts[invoked];
    if (script) names.push(...matchAll(script, /--project(?:=|\s+)([A-Za-z0-9_.:-]+)/g));
  }
  return new Set(names.filter(Boolean));
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

describe("CI 실행 표면 ([BL-789])", () => {
  it("주석 안의 실행처럼 보이는 문장은 실행으로 세지 않는다", () => {
    // ★양성 대조. 이 감사의 판별력은 「주석을 지운다」에 달려 있으므로 그것을 따로 증명한다.
    //   픽스처는 인라인이다 — 실파일 문구에 앵커를 걸면 그 문구가 바뀌는 순간 이 시험이
    //   무엇을 재는지 알 수 없게 된다.
    const scripts = { "e2e:authed": "playwright test --project=chromium-authed" };
    const fixture = [
      "      # P1 4라우트는 전부 authed 라 로컬 `pnpm e2e:authed` 몫이고 CI 에는 없다.",
      "      # - run: pnpm exec playwright test --project=chromium-authed",
      "      - run: pnpm exec playwright test --project=chromium",
    ].join("\n");

    expect(executedProjects(fixture, scripts)).toEqual(new Set(["chromium"]));
    // 음성 대조 — 주석을 안 지우면 정확히 반대 답이 난다(= 이 시험은 판별력이 있다).
    expect(executedProjects(fixture.replace(/^\s*#/gm, ""), scripts)).toEqual(
      new Set(["chromium", "chromium-authed"]),
    );
  });

  it("모든 project 는 워크플로에서 실제로 돌거나 LOCAL_ONLY 에 사유와 함께 등재돼 있다", () => {
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

    const direct = new Set<string>();
    for (const f of workflows) {
      for (const name of executedProjects(
        readFileSync(path.join(WORKFLOW_DIR, f), "utf8"),
        scripts,
      ))
        direct.add(name);
    }
    if (direct.size === 0)
      throw new Error(
        "ABORT — 워크플로에서 실행되는 playwright project 를 0개 추출했다. 파서가 죽었다.",
      );

    const inCI = withDependencies(direct);

    // ⑴ 워크플로가 부르는 이름이 config 에 실재하는가 (오타 = 조용한 0건 실행).
    expect(
      [...direct].filter((n) => !projectNames.includes(n)),
      `워크플로가 존재하지 않는 project 를 부른다 — playwright 는 그것을 0건으로 돌고 초록이다.`,
    ).toEqual([]);

    // ⑵ LOCAL_ONLY 가 낡지 않았는가 (사라진 project 의 면제가 남아 있으면 다음 신설을 가린다).
    expect(
      Object.keys(LOCAL_ONLY).filter((n) => !projectNames.includes(n)),
      "LOCAL_ONLY 에 config 에 없는 project 가 남아 있다. 지워라.",
    ).toEqual([]);

    // ⑶ 본체 — 실행되지도, 면제되지도 않은 project 는 아무 데서도 안 도는 것이다.
    expect(
      projectNames.filter((n) => !inCI.has(n) && !LOCAL_ONLY[n]?.trim()),
      "이 project 는 .github/workflows/*.yml 어디에서도 실행되지 않는다.\n" +
        "워크플로에 --project= 로 배선하거나, LOCAL_ONLY 에 **사유와 함께** 등재해라.\n" +
        `워크플로가 실제로 부르는 것: ${JSON.stringify([...direct].sort())}`,
    ).toEqual([]);

    // ⑷ 면제와 실행이 겹치면 LOCAL_ONLY 사유가 거짓이다.
    expect(
      Object.keys(LOCAL_ONLY).filter((n) => direct.has(n)),
      "LOCAL_ONLY 인데 워크플로가 실제로 부른다 — 사유가 거짓이 됐으니 목록에서 빼라.",
    ).toEqual([]);
  });
});
