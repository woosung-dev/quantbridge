// 이 가드는 이미지·번역 리소스·런타임 응답 문자열을 못 잡는다.
// 정적 분석으로 닿지 않는 표면이므로 스캔 범위에 넣지 않는다.
// 제품 결정 표면 — 마케팅·웨이트리스트·세션·법무 화면의 직접 문구 회귀 차단.
// 지원 상태의 이름은 marketing-canon 이 단독 소유하고, 그 값의 정합성은 Step 0 테스트가 맡는다.

import { existsSync, readFileSync, readdirSync } from "node:fs";
import { relative, resolve } from "node:path";

import { describe, expect, it } from "vitest";

const FRONTEND_ROOT = resolve(__dirname, "../../..");
const SOURCE_ROOT = resolve(FRONTEND_ROOT, "src");
const GUARD_PATH = "src/lib/__tests__/decision-surface-guard.test.ts";
const SOURCE_SCAN_EXCLUDED_FILES = new Set([
  // 지원 상태의 이름은 이 가드가 아닌 marketing-canon 테스트가 단독 검증한다.
  "src/lib/marketing-canon.ts",
  // 과거 Bybit 단일화 이식 주석은 런타임 제품 문구가 아니다.
  "src/features/trading/schemas.ts",
  "src/lib/zod-v4-resolver.ts",
]);

const DECISION_SURFACE_PATHS = [
  "src/app/page.tsx",
  "src/app/pricing/page.tsx",
  "src/app/privacy/page.tsx",
  "src/app/terms/page.tsx",
  "src/components/exchange-support-table.tsx",
  "src/features/marketing/components/landing-faq.tsx",
  "src/features/marketing/components/landing-features.tsx",
  "src/features/waitlist/components/waitlist-faq.tsx",
  "src/features/waitlist/components/waitlist-hero.tsx",
  "src/features/live-sessions/components/live-session-form.tsx",
] as const;

const FORBIDDEN_ACCOUNT_MODE = ["메인", "넷"].join("");
const FORBIDDEN_OUT_OF_SCOPE_EXCHANGE = ["O", "K", "X"].join("");

type SourceSnapshot = {
  missingPaths: string[];
  contents: SourceContents;
};

type SourceContents = ReadonlyArray<readonly [path: string, content: string]>;

function readDecisionSurfaces(): SourceSnapshot {
  const missingPaths: string[] = [];
  const contents: Array<readonly [path: string, content: string]> = [];

  for (const relativePath of DECISION_SURFACE_PATHS) {
    const absolutePath = resolve(FRONTEND_ROOT, relativePath);
    if (!existsSync(absolutePath)) {
      missingPaths.push(relativePath);
      continue;
    }
    contents.push([relativePath, readFileSync(absolutePath, "utf-8")]);
  }

  return { missingPaths, contents };
}

function isExcludedSourceDirectory(relativePath: string): boolean {
  // 테스트에는 가드가 찾는 금지 토큰의 정의·단언 데이터가 있어 제품 표면이 아니다.
  if (relativePath.split("/").includes("__tests__")) {
    return true;
  }

  // Better Auth 서버 라우트는 화면 제품 결정을 표현하지 않는다.
  return relativePath === "src/app/api";
}

function isExcludedSourceFile(relativePath: string): boolean {
  // 가드 자신은 금지 토큰을 정의하므로 자기 검사에서 제외한다.
  if (relativePath === GUARD_PATH) {
    return true;
  }

  return SOURCE_SCAN_EXCLUDED_FILES.has(relativePath);
}

function scanSourceFiles(): SourceContents {
  const contents: Array<readonly [path: string, content: string]> = [];

  function visit(directory: string) {
    for (const entry of readdirSync(directory, { withFileTypes: true }).sort((a, b) =>
      a.name.localeCompare(b.name),
    )) {
      const absolutePath = resolve(directory, entry.name);
      const relativePath = relative(FRONTEND_ROOT, absolutePath);

      if (entry.isDirectory()) {
        if (!isExcludedSourceDirectory(relativePath)) {
          visit(absolutePath);
        }
        continue;
      }

      if (
        (relativePath.endsWith(".ts") || relativePath.endsWith(".tsx")) &&
        !isExcludedSourceFile(relativePath)
      ) {
        contents.push([relativePath, readFileSync(absolutePath, "utf-8")]);
      }
    }
  }

  visit(SOURCE_ROOT);
  return contents;
}

function expectAllSurfacesRead(snapshot: SourceSnapshot) {
  expect(DECISION_SURFACE_PATHS.length).toBeGreaterThanOrEqual(7);
  expect(snapshot.missingPaths).toEqual([]);
  expect(snapshot.contents).toHaveLength(DECISION_SURFACE_PATHS.length);
  expect(
    snapshot.contents.reduce(
      (totalBytes, [, content]) => totalBytes + Buffer.byteLength(content),
      0,
    ),
  ).toBeGreaterThan(0);
}

function pathsContaining(contents: SourceContents, token: string): string[] {
  return contents
    .filter(([, content]) => content.toLowerCase().includes(token.toLowerCase()))
    .map(([path]) => path);
}

describe("제품 결정 표면 부재 가드", () => {
  it("명시한 소스 파일이 모두 존재하고 실제로 읽혔다", () => {
    expectAllSurfacesRead(readDecisionSurfaces());
  });

  it("결정 1의 금지 토큰이 직접 문구에 없다", () => {
    const snapshot = readDecisionSurfaces();
    expectAllSurfacesRead(snapshot);

    expect(
      pathsContaining(snapshot.contents, FORBIDDEN_ACCOUNT_MODE),
      `${FORBIDDEN_ACCOUNT_MODE} 문구가 남은 소스 파일`,
    ).toEqual([]);
  });

  it("결정 3의 범위 밖 거래소 이름이 직접 문구에 없다", () => {
    const snapshot = readDecisionSurfaces();
    expectAllSurfacesRead(snapshot);

    expect(
      pathsContaining(snapshot.contents, FORBIDDEN_OUT_OF_SCOPE_EXCHANGE),
      `${FORBIDDEN_OUT_OF_SCOPE_EXCHANGE} 문구가 남은 소스 파일`,
    ).toEqual([]);
  });

  it("스캔 집합이 하한선 10파일을 포함한다", () => {
    const scannedPaths = scanSourceFiles().map(([path]) => path);

    expect(scannedPaths).toEqual(expect.arrayContaining([...DECISION_SURFACE_PATHS]));
  });

  it("스캔한 파일 수가 하한선보다 크다", () => {
    expect(scanSourceFiles().length).toBeGreaterThan(DECISION_SURFACE_PATHS.length);
  });

  it("금지 문자열을 담은 합성 소스를 위반으로 잡는다", () => {
    const syntheticSource = [
      ["src/synthetic.tsx", `${FORBIDDEN_ACCOUNT_MODE} ${FORBIDDEN_OUT_OF_SCOPE_EXCHANGE}`],
    ] as const;

    expect(pathsContaining(syntheticSource, FORBIDDEN_ACCOUNT_MODE)).toEqual(["src/synthetic.tsx"]);
    expect(pathsContaining(syntheticSource, FORBIDDEN_OUT_OF_SCOPE_EXCHANGE)).toEqual([
      "src/synthetic.tsx",
    ]);
  });

  it("스캔한 소스 전체에 금지 문자열이 없다", () => {
    const scannedSources = scanSourceFiles();

    expect(pathsContaining(scannedSources, FORBIDDEN_ACCOUNT_MODE)).toEqual([]);
    expect(pathsContaining(scannedSources, FORBIDDEN_OUT_OF_SCOPE_EXCHANGE)).toEqual([]);
  });
});
