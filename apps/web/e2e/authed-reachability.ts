// authed 백엔드 도달성 판정 — 「없는 것」과 「못 가져오는 것」을 가른다 ([BL-707])
//
// ★판정 축이 `subresourceFail` 이 아니라 `transportFail` 인 이유 (2026-08-14, 리뷰 2축 수렴).
//   `subresourceFail` 은 `>=400` 응답까지 센다. 그런데 **응답이 왔다는 것 자체가 도달의 증거**이고,
//   이 레포는 401/403 과 429 를 authed 스위트의 정상 아티팩트로 이미 문서화했다
//   (`authed-canon-p1.spec.ts` 의 `EXPECTED_CONSOLE` — 「연속 4폭 감사가 백엔드를 치면 나는
//   스위트 환경 아티팩트」). 그 축으로 도달성을 물으면 **BE 가 멀쩡한 회차에 429 하나로**
//   authed 전량이 「백엔드 도달 불가」로 abort 한다 — 이 단언이 막으려던 바로 그 오지목이다.
//   [BL-707] 이 실제로 본 신호는 `ERR_CONNECTION_REFUSED` **109건**, 즉 응답이 아예 없는 갈래다.

import type { NavProbe } from "./design-canon-audit";

export interface AuthedReachabilitySummary {
  probeCount: number;
  /** 문서 응답이 200 이 아니었던 폭 수. 화면 자체가 안 온 경우다. */
  statusFailureCount: number;
  /** 전송 실패(`requestfailed`) 총 건수. 도달성 판정의 주축이다. */
  transportFailCount: number;
  /** 전송 실패가 난 호스트. 비어 있으면 감사 대상 호스트로 떨어진다(아래 format 이 갈라 쓴다). */
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
  let transportFailCount = 0;

  for (const probe of probes) {
    if (probe.status !== 200) statusFailureCount++;
    transportFailCount += probe.transportFail;
    for (const host of probe.transportFailHosts) targetHosts.add(host);
  }

  // ★전송 실패 호스트가 없을 때만 감사 대상 URL 의 호스트로 떨어진다. 이때 이 값은
  //   「실패한 곳」이 아니라 「무엇을 보던 중이었나」다 — format 이 문구를 갈라 쓴다.
  if (targetHosts.size === 0) targetHosts.add(hostFromURL(targetURL));

  return {
    probeCount: probes.length,
    statusFailureCount,
    transportFailCount,
    targetHosts: [...targetHosts].sort(),
  };
}

export function isAuthedReachable(summary: AuthedReachabilitySummary): boolean {
  return (
    summary.probeCount > 0 && summary.statusFailureCount === 0 && summary.transportFailCount === 0
  );
}

export function formatAuthedReachabilityFailure(
  label: string,
  summary: AuthedReachabilitySummary,
): string {
  // ★probe 0 은 「도달 못 했다」가 아니라 「재지 못했다」다. 둘을 같은 문구로 내면 이 단언이
  //   막으려던 오지목([BL-707])을 이 단언 자신이 저지른다 — 「실패 0건」과 프론트 호스트를
  //   나란히 적어 놓고 「백엔드 도달 불가」라고 우기는 꼴이 된다.
  if (summary.probeCount === 0) {
    return (
      `${label} — 도달성을 **관측하지 못했다**. 브라우저 probe 가 0건이라 도달/미도달을 가를 ` +
      `근거가 없다(감사 대상: ${summary.targetHosts.join(", ")}). 감사가 실제로 돌았는지부터 확인해라.`
    );
  }
  return (
    `${label} — 백엔드 도달 불가. 브라우저 실측: 페이지 응답 비정상 ${summary.statusFailureCount}폭, ` +
    `전송 실패 ${summary.transportFailCount}건. 실패 호스트: ${summary.targetHosts.join(", ")}. ` +
    `★4xx·429 응답은 이 셈에 안 들어간다 — 응답이 왔다는 것은 도달했다는 뜻이다.`
  );
}
