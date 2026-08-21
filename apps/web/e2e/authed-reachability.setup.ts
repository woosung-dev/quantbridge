import { resolve } from "node:path";

import { test as setup } from "@playwright/test";

import { getBaseURL } from "./_base-url";
import { assertAuthedReachability } from "./authed-reachability-assert";
import { auditUrl, formatCanonResult } from "./design-canon-audit";

const STORAGE_STATE = resolve(__dirname, ".auth/storageState.json");

setup("authed 백엔드 도달성 확인", async ({ browser }) => {
  const url = new URL("/trading", getBaseURL()).toString();
  const res = await auditUrl(browser, url, {
    label: "/trading authed 도달성 setup",
    widths: [1440],
    contextOptions: { storageState: STORAGE_STATE },
  });
  process.stdout.write(`${formatCanonResult(res)}\n`);
  assertAuthedReachability(res);
});
