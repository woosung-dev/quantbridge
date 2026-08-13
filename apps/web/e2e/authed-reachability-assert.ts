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

  // ★`probeCount > 0` 을 따로 단언하지 않는다. `isAuthedReachable` 이 이미 그 항을 포함하므로
  //   중복인데, 그보다 나쁜 것은 **먼저 발화해 진단 문구를 가로챈다**는 점이다 — probe 0 에서
  //   사람이 보는 것이 「관측하지 못했다」가 아니라 `toBeGreaterThan(0)` 이 된다(2026-08-14 실측).
  expect(isAuthedReachable(summary), message).toBe(true);
}
