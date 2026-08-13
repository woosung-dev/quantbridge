import { expect } from "@playwright/test";

import type { CanonAuditResult } from "./design-canon-audit";
import {
  formatAuthedReachabilityFailure,
  isAuthedReachable,
  summarizeAuthedReachability,
} from "./authed-reachability";

/**
 * authed 캐논·setup 이 공유하는 도달성 계약.
 *
 * `design-canon-calibration`의 계약처럼, probe 전체를 먼저 단언해
 * "0 건"이 "관측하지 못함"으로 통과하는 것을 막는다.
 */
export function assertAuthedReachability(res: CanonAuditResult): void {
  const summary = summarizeAuthedReachability(res.probes, res.url);
  const message = `${formatAuthedReachabilityFailure(res.label, summary)}\n${res.url}`;

  expect(summary.probeCount, message).toBeGreaterThan(0);
  expect(isAuthedReachable(summary), message).toBe(true);
}
