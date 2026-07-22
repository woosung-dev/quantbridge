// 주문 크기 source 4상태 배지 — C 디자인 언어 이식(W3-A). 프로토타입 .chip 톤(neutral/accent/warn) 소비.
"use client";

export type SizingSource = "pine" | "live" | "manual" | "live_blocked_leverage";

export interface LiveSettingsBadgeProps {
  source: SizingSource;
  liveLeverage?: number | null;
  livePct?: number | null;
}

export function LiveSettingsBadge({
  source,
  liveLeverage,
  livePct,
}: LiveSettingsBadgeProps) {
  switch (source) {
    case "pine":
      return (
        <span className="chip accent" data-testid="live-settings-badge-pine">
          Pine 지정
        </span>
      );
    case "live": {
      const pctLabel = livePct != null ? `${livePct}%` : "미지정";
      return (
        <span className="chip accent" data-testid="live-settings-badge-live">
          {`Live 미러 (${pctLabel} · 약 equity 5% 오차)`}
        </span>
      );
    }
    case "live_blocked_leverage": {
      const lev = liveLeverage ?? 0;
      return (
        <span className="chip warn" data-testid="live-settings-badge-blocked">
          {`미러 불가 (Live 레버리지 ${lev}x · 준비 중)`}
        </span>
      );
    }
    case "manual":
    default:
      return (
        <span className="chip" data-testid="live-settings-badge-manual">
          수동 입력
        </span>
      );
  }
}
