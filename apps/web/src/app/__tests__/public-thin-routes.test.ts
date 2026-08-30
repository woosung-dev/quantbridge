import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const WEB_ROOT = resolve(__dirname, "../../..");

const ROUTES = [
  {
    path: "src/app/pricing/page.tsx",
    featureImport: "@/features/marketing/components/pricing-page",
  },
  {
    path: "src/app/invite/[token]/page.tsx",
    featureImport: "@/features/waitlist/components/invite-page",
  },
  {
    path: "src/app/share/backtests/[token]/page.tsx",
    featureImport: "@/features/backtest/components/share/shared-backtest-page",
  },
] as const;

describe("공개 route FSD Lite 조립 경계", () => {
  it.each(ROUTES)(
    "$path 는 metadata/params와 feature view 조립만 보유한다",
    ({ path, featureImport }) => {
      const source = readFileSync(resolve(WEB_ROOT, path), "utf-8");

      expect(source).toContain(featureImport);
      expect(source).not.toContain("fetch(");
      expect(source.split("\n").length).toBeLessThan(40);
    },
  );
});
