import { test as setup } from "@playwright/test";

import { getBaseURL } from "./_base-url";

setup("verify public app identity", async ({ page, baseURL }) => {
  const requestURL = new URL("/", baseURL ?? getBaseURL()).toString();
  const response = await page.goto(requestURL, { timeout: 120_000 });
  const status = response?.status() ?? "응답 없음";
  const title = await page.title();

  if (status !== 200 || !title.includes("QuantBridge")) {
    throw new Error(
      `[e2e identity] 공개 앱 정체성 확인 실패. 요청 URL: ${requestURL}, status: ${status}, 실제 title 원문: ${JSON.stringify(title)}`,
    );
  }
});
