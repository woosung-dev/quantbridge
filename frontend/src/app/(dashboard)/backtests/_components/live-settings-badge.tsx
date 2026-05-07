// Live mirror / Pine override / Manual / Live blocked Nx 4-state 배지
"use client";

import { Badge } from "@/components/ui/badge";

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
        <Badge variant="outline" data-testid="live-settings-badge-pine">
          Pine override
        </Badge>
      );
    case "live": {
      const pctLabel = livePct != null ? `${livePct}%` : "—";
      return (
        <Badge variant="default" data-testid="live-settings-badge-live">
          {`Live mirror (${pctLabel} · ≈equity 5% 오차)`}
        </Badge>
      );
    }
    case "live_blocked_leverage": {
      const lev = liveLeverage ?? 0;
      return (
        <Badge
          variant="destructive"
          data-testid="live-settings-badge-blocked"
        >
          {`Mirror 불가 (Live leverage ${lev}x — BL-186 후 unlock)`}
        </Badge>
      );
    }
    case "manual":
    default:
      return (
        <Badge variant="secondary" data-testid="live-settings-badge-manual">
          Manual sizing
        </Badge>
      );
  }
}
