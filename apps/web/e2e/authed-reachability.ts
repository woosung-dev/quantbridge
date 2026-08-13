import type { NavProbe } from "./design-canon-audit";

export interface AuthedReachabilitySummary {
  probeCount: number;
  statusFailureCount: number;
  subresourceFailCount: number;
  targetHosts: string[];
}

function hostFromURL(url: string): string {
  try {
    return new URL(url).host || url;
  } catch {
    return url;
  }
}

/** 브라우저가 실제로 기록한 probe 만으로 authed API 도달성을 판정한다. */
export function summarizeAuthedReachability(
  probes: readonly NavProbe[],
  targetURL: string,
): AuthedReachabilitySummary {
  const targetHosts = new Set<string>();
  let statusFailureCount = 0;
  let subresourceFailCount = 0;

  for (const probe of probes) {
    if (probe.status !== 200) statusFailureCount++;
    subresourceFailCount += probe.subresourceFail;
    for (const host of probe.subresourceFailHosts) targetHosts.add(host);
  }

  if (targetHosts.size === 0) targetHosts.add(hostFromURL(targetURL));

  return {
    probeCount: probes.length,
    statusFailureCount,
    subresourceFailCount,
    targetHosts: [...targetHosts].sort(),
  };
}

export function isAuthedReachable(summary: AuthedReachabilitySummary): boolean {
  return (
    summary.probeCount > 0 && summary.statusFailureCount === 0 && summary.subresourceFailCount === 0
  );
}

export function formatAuthedReachabilityFailure(
  label: string,
  summary: AuthedReachabilitySummary,
): string {
  return (
    `${label} — 백엔드 도달 불가. 브라우저 실측: 페이지 응답 비정상 ${summary.statusFailureCount}폭, ` +
    `서브리소스 실패 ${summary.subresourceFailCount}건. 대상 호스트: ${summary.targetHosts.join(", ")}.`
  );
}
