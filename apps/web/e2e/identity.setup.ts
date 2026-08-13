// 공개 스위트가 `global.setup.ts` 를 타지 않아 정체성 프로브가 없었다.
// `reuseExistingServer` 와 겹치면 남의 앱을 감사하고 초록이 날 수 있다.
// 공개 앱의 응답과 title만 확인하며 Clerk와 환경 변수는 건드리지 않는다.

import { test as setup } from "@playwright/test";

import { getBaseURL } from "./_base-url";

setup("공개 앱 정체성 확인", async ({ page }) => {
  const requestURL = new URL("/", getBaseURL()).toString();
  const response = await page.goto(requestURL, { timeout: 120_000 });
  const status = response?.status() ?? "응답 없음";
  const title = await page.title();

  if (status !== 200 || !title.includes("QuantBridge")) {
    throw new Error(
      `[e2e identity] 공개 앱 정체성 확인 실패. 요청 URL: ${requestURL}, 받은 status: ${status}, 실제 title 원문: ${JSON.stringify(title)}`,
    );
  }
});
