// 인증 공급자 seam 경계 — `useSession`·`getAuthToken` 을 쓰는 곳은 `use-auth-ctx.ts` 하나다.
import { readdirSync, readFileSync } from "node:fs";
import { join, relative, resolve } from "node:path";

import { describe, expect, it } from "vitest";

const SRC_ROOT = resolve(__dirname, "../..");

// seam 본체와 공급자 모듈 자신만 허용한다. 늘리려면 여기에 이유와 함께 적는다.
const ALLOWED = new Set(["hooks/use-auth-ctx.ts", "lib/auth-client.ts"]);

// `@/lib/auth-client` (또는 상대 경로)에서 두 이름 중 하나를 가져오는 import 문.
const SEAM_IMPORT =
  /import\s+(?:type\s+)?\{([^}]*)\}\s+from\s+["'](?:@\/lib\/auth-client|(?:\.{1,2}\/)+(?:lib\/)?auth-client)["']/g;
const SEAM_NAMES = /\b(useSession|getAuthToken)\b/;
// 구조 분해 없이 클라이언트 객체로 우회하는 형태.
const CLIENT_BYPASS = /\bauthClient\s*\.\s*(useSession|getAuthToken)\b/;

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) {
      return ["__tests__", "__mocks__", "generated"].includes(entry.name) ? [] : sourceFiles(path);
    }
    return /\.tsx?$/.test(entry.name) && !/\.test\.tsx?$/.test(entry.name) ? [path] : [];
  });
}

function usesProviderDirectly(source: string): boolean {
  if (CLIENT_BYPASS.test(source)) return true;
  for (const match of source.matchAll(SEAM_IMPORT)) {
    if (SEAM_NAMES.test(match[1] ?? "")) return true;
  }
  return false;
}

describe("AuthCtx 공급자 경계", () => {
  it("검출기는 seam 본체의 import 를 본다 (빈 스캔이 초록이 되지 않게)", () => {
    const seam = readFileSync(join(SRC_ROOT, "hooks/use-auth-ctx.ts"), "utf-8");
    expect(usesProviderDirectly(seam)).toBe(true);
    expect(usesProviderDirectly("const s = authClient.useSession();")).toBe(true);
    expect(usesProviderDirectly('import { signOut } from "@/lib/auth-client";')).toBe(false);
  });

  it("seam 밖에서 useSession·getAuthToken 을 직접 가져오지 않는다", () => {
    const files = sourceFiles(SRC_ROOT);
    expect(files.length).toBeGreaterThan(100);

    const offenders = files
      .map((path) => relative(SRC_ROOT, path))
      .filter((rel) => !ALLOWED.has(rel))
      .filter((rel) => usesProviderDirectly(readFileSync(join(SRC_ROOT, rel), "utf-8")));

    expect(
      offenders,
      "useAuthCtx() 를 써라 (hooks/use-auth-ctx.ts → uid·userId·isSignedIn·user·getToken)",
    ).toEqual([]);
  });
});
