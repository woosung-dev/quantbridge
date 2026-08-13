// Sprint 25 — storageState 부재 / 만료 감지 helper.
//
// global.setup.ts 가 매 e2e:authed 실행 시 storageState 새로 발급 (clerk.signIn()).
// 만료 자체는 setup 단계에서 protected route 검증으로 catch.
// 본 helper 는 spec 파일이 직접 storageState 존재만 확인할 때 사용 (선택).
//
// 사용처: trading-ui.spec.ts / dogfood-flow.spec.ts 의 test.beforeAll 또는 fixture.

import * as fs from "node:fs";
import * as path from "node:path";

const STORAGE_PATH = path.resolve(
  process.cwd(),
  "e2e/.auth/storageState.json",
);

export function expectStorageStateReady(): void {
  if (!fs.existsSync(STORAGE_PATH)) {
    process.stderr.write(
      [
        "",
        "[e2e:authed] storageState.json missing.",
        "  Regenerate: pnpm e2e:authed (global.setup.ts auto-issues via clerk.signIn())",
        "  Prereq: frontend/.env.local must contain CLERK_PUBLISHABLE_KEY,",
        "          CLERK_SECRET_KEY, E2E_CLERK_USER_EMAIL, E2E_CLERK_USER_PASSWORD.",
        "",
      ].join("\n"),
    );
    throw new Error("storageState missing");
  }
}

// Page-level helper: spec test.beforeEach 에서 호출하여 real backend leak 가드.
// codex G.0 iter 2 P2 #5: page.route() mock 만으로는 leak 보장 부족. request 이벤트
// 직접 hook 후 unmocked URL 만 잡음.
//
// `mock-handled` query param 첨부된 fulfill 은 통과 (route handler 내부에서 추가 가능)
// 또는 더 간단히 — 모든 unmocked path 가 fulfill 안 되면 page.route() 에서 자동 abort.
//
// 본 함수는 leak 감지만, mock 자체는 spec 파일에서 page.route() 로 등록.

import type { Page } from "@playwright/test";

export function attachLeakGuard(page: Page, apiBase: string): void {
  page.on("request", (req) => {
    const url = req.url();
    if (!url.startsWith(apiBase)) return;
    // Playwright 가 page.route() 로 fulfill 한 요청도 request 이벤트는 발생.
    // 단 fulfill 된 경우 response 가 mock 으로 응답 → real backend hit 안 함.
    // Leak 감지 = response 가 real network 에서 옴. Playwright 의 frame.attribute() 로
    // postData / matched route 직접 검증 어려움 → 대신 request 가 실제로
    // localhost:8100 (격리 stack) hit 했는지는 console 로 출력.
    // Strict 검증은 spec 파일에서 expect(unmockedUrls).toHaveLength(0) 로.
    process.stderr.write(`[e2e leak guard] backend request: ${url}\n`);
  });
}
