import { describe, expect, it } from "vitest";

import { assertAuthedReachability } from "../../e2e/authed-reachability-assert";
import type { CanonAuditResult } from "../../e2e/design-canon-audit";

const unreachableResult: CanonAuditResult = {
  label: "/trading",
  url: "http://localhost:3102/trading",
  overflow: [],
  contrast: [],
  canon: [],
  tiny: [],
  focus: [],
  motion: [],
  console: [],
  themeProbe: null,
  probes: [
    {
      w: 1440,
      status: 200,
      examined: 12,
      subresourceFail: 2,
      subresourceFailHosts: ["localhost:8102"],
      sealed: 0,
    },
  ],
};

describe("authed 도달성 단언", () => {
  it("도달 불가 probe를 통과시키지 않는다", () => {
    expect(() => assertAuthedReachability(unreachableResult)).toThrow();
  });
});
