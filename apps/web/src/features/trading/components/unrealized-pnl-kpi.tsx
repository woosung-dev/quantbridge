"use client";

// §01 네 번째 KPI — 미실현 손익 추정. [BL-663] 로 코크핏에서 분리해 나온 leaf 다.
//
// ★분리 이유가 백로그 본문과 다르다. [BL-663] 은 「5초 틱이 전 서브트리를 재조정한다」고
//   적었지만 코드 대조에서 인과가 불완전했다 — 재조정 원천이 **둘**이다:
//     ⑴ `useNowTick(5_000)` 의 5초 setState
//     ⑵ `useUnrealizedPnlEstimate` → `useRealtimeStore(useShallow(...))` 의 WS ticker 구독.
//        `applyTicker`(realtime/store.ts)가 매 틱 **새 TickerEntry** 를 넣으므로 shallow 비교가
//        깨지고, 활성 세션 심볼이 틱할 때마다 구독 컴포넌트가 재렌더된다 — 5초보다 훨씬 잦다.
//   ⑴만 떼면 활성 세션이 있는 동안은 거의 아무것도 안 준다. 반대로 활성 세션이 0건이면
//   ⑵는 안 돌지만 그땐 `latestTs === null` 이라 `isTickerStale` 이 항상 false 다.
//   ⇒ 둘을 **같은 leaf 안에** 두는 것이 처방이다.
//
// ★사거리를 정확히 적는다(codex 적대 리뷰가 초안의 과장을 잡았다). 이 분리가 지키는 것은
//   **`TradingCockpit` 본체와 그 렌더가 낳는 §01~§07 서브트리**다. **§08 은 아니다** —
//   `session-diagnostics.tsx:241-242` 가 `useRealtimeStore` 의 `status`·`lastEventTs` 를 **스스로**
//   구독하고, `realtime-bridge.tsx:62` 가 ticker 를 포함한 모든 envelope 에서 `recordEvent` 를
//   부르므로 §08 은 WS 이벤트마다 계속 재렌더된다. 그것은 §08 자신의 구독이지 코크핏 경유가
//   아니므로 범위가 이미 격리돼 있고, 이 회차의 표적도 아니다.

import { useEffect, useState } from "react";

import { useUnrealizedPnlEstimate, type LiveSession } from "@/features/live-sessions";

const TICKER_STALE_MS = 15_000;

function useNowTick(intervalMs: number): number {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs]);

  return now;
}

// 손익 톤 — 옵티마이저 pnlTone 과 같은 0-중립 규약(양수 pos / 음수 neg / 0 중립).
// 프로토타입 screen-01:1188 은 kpi-value mono pos 로 물들인다.
function pnlTone(v: number): string {
  if (v > 0) return " pos";
  if (v < 0) return " neg";
  return "";
}

function formatEstimatedPnl(value: number): string {
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return `${sign}${Math.abs(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} USDT`;
}

interface UnrealizedPnlKpiProps {
  /** 활성 라이브 세션. 이 카드가 WS ticker 를 구독하는 단위다. */
  sessions: readonly LiveSession[];
}

export function UnrealizedPnlKpi({ sessions }: UnrealizedPnlKpiProps) {
  const unrealized = useUnrealizedPnlEstimate(sessions);
  const now = useNowTick(5_000);
  const isTickerStale = unrealized.latestTs !== null && now - unrealized.latestTs > TICKER_STALE_MS;

  return (
    <article className="card kpi">
      <p className="kpi-label">미실현 손익 · 추정</p>
      <p
        className={`kpi-value mono${unrealized.total === null ? "" : pnlTone(unrealized.total)}`}
        data-testid="kpi-unrealized-pnl"
      >
        {unrealized.total === null ? (
          <span className="kpi-na">시세 수신 대기</span>
        ) : (
          <>
            {formatEstimatedPnl(unrealized.total)}
            {isTickerStale ? <span className="kpi-value-tag">시세 지연</span> : null}
          </>
        )}
      </p>
      <p className="kpi-foot">
        실시간 마크가격 × 미청산 수량 추정치. §03 거래소 보고값(/positions)과 다를 수 있습니다.
      </p>
    </article>
  );
}
