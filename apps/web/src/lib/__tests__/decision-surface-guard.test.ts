// 제품 결정 표면 — 마케팅·웨이트리스트·세션·법무 화면의 직접 문구 회귀 차단.
// 지원 상태의 이름은 marketing-canon 이 단독 소유하고, 그 값의 정합성은 Step 0 테스트가 맡는다.

import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const FRONTEND_ROOT = resolve(__dirname, "../../..");

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
  contents: ReadonlyArray<readonly [path: string, content: string]>;
};

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

function pathsContaining(snapshot: SourceSnapshot, token: string): string[] {
  return snapshot.contents
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
      pathsContaining(snapshot, FORBIDDEN_ACCOUNT_MODE),
      `${FORBIDDEN_ACCOUNT_MODE} 문구가 남은 소스 파일`,
    ).toEqual([]);
  });

  it("결정 3의 범위 밖 거래소 이름이 직접 문구에 없다", () => {
    const snapshot = readDecisionSurfaces();
    expectAllSurfacesRead(snapshot);

    expect(
      pathsContaining(snapshot, FORBIDDEN_OUT_OF_SCOPE_EXCHANGE),
      `${FORBIDDEN_OUT_OF_SCOPE_EXCHANGE} 문구가 남은 소스 파일`,
    ).toEqual([]);
  });
});
