// FastAPI 호출 경계 — `apiFetch` 밖에서 백엔드를 직접 `fetch` 하는 파일은 아래 목록이 전부다.
import { readdirSync, readFileSync } from "node:fs";
import { join, relative, resolve } from "node:path";

import { describe, expect, it } from "vitest";

const SRC_ROOT = resolve(__dirname, "../..");

// `apiFetch` 본체와, 그것을 못 쓰는 이유가 있는 곳. 늘리려면 여기에 이유와 함께 적는다.
const ALLOWED = new Set([
  "lib/api-client.ts", // apiFetch 본체
  "lib/auth.ts", // 서버 beforeDelete 훅 — 토큰을 `auth.api.getToken` 으로 직접 발급해 싣는다
  "app/share/backtests/[token]/opengraph-image.tsx", // 공개 share 엔드포인트 — 토큰 없이 부른다
  "features/backtest/components/share/shared-backtest-page.tsx", // 공개 share 본문 — 404/410 을 분기로 받는다
  "features/trading/components/test-order-webhook.ts", // webhook — 쿼리의 HMAC token 으로 인증한다
  "features/waitlist/api.ts", // invite 검증 — 400/404 를 throw 가 아니라 분기로 받는다
]);

// 기준 = 백엔드 base URL 을 쥔 파일이 `fetch(` 를 직접 부르는가. Next 내부 라우트(`/api/auth/token`)와
// 정적 자산 fetch 는 base URL 을 쓰지 않으므로 세지 않는다.
const RAW_FETCH = /(?<!\w)fetch\s*\(/;
const BACKEND_BASE = /\b(getApiBase|API_BASE_URL)\b/;

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) {
      return ["__tests__", "__mocks__", "generated"].includes(entry.name) ? [] : sourceFiles(path);
    }
    return /\.tsx?$/.test(entry.name) && !/\.test\.tsx?$/.test(entry.name) ? [path] : [];
  });
}

function fetchesBackendDirectly(source: string): boolean {
  return RAW_FETCH.test(source) && BACKEND_BASE.test(source);
}

describe("FastAPI 호출 경계", () => {
  it("검출기는 직접 fetch 를 보고, apiFetch 호출과 내부 라우트 fetch 는 세지 않는다", () => {
    expect(fetchesBackendDirectly("await fetch(getApiBase() + path);")).toBe(true);
    expect(fetchesBackendDirectly("await apiFetch(getApiBase() + path);")).toBe(false);
    expect(fetchesBackendDirectly("await window.fetch(API_BASE_URL + path);")).toBe(true);
    expect(fetchesBackendDirectly("router.prefetch(href); getApiBase();")).toBe(false);
    expect(fetchesBackendDirectly('await fetch("/api/auth/token");')).toBe(false);
  });

  it("apiFetch 밖에서 백엔드를 직접 fetch 하는 파일은 목록과 같다", () => {
    const files = sourceFiles(SRC_ROOT);
    expect(files.length).toBeGreaterThan(100);

    const found = files
      .map((path) => relative(SRC_ROOT, path))
      .filter((rel) => fetchesBackendDirectly(readFileSync(join(SRC_ROOT, rel), "utf-8")));

    expect(
      found.filter((rel) => !ALLOWED.has(rel)),
      "apiFetch() 를 써라 (lib/api-client.ts — 토큰·401 재발급·ApiError 를 한 곳에서 처리한다)",
    ).toEqual([]);
    expect(
      [...ALLOWED].filter((rel) => !found.includes(rel)),
      "더는 직접 fetch 하지 않는 파일이 목록에 남아 있다 — 지워라",
    ).toEqual([]);
  });
});
