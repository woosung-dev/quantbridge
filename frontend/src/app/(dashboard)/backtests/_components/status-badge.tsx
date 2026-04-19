import { Badge } from "@/components/ui/badge";
import type { BacktestStatus } from "@/features/backtest/schemas";

interface StatusMeta {
  label: string;
  variant: "default" | "secondary" | "destructive" | "outline";
}

const STATUS_META: Record<BacktestStatus, StatusMeta> = {
  queued: { label: "대기 중", variant: "secondary" },
  running: { label: "실행 중", variant: "default" },
  cancelling: { label: "취소 중", variant: "secondary" },
  completed: { label: "완료", variant: "outline" },
  failed: { label: "실패", variant: "destructive" },
  cancelled: { label: "취소됨", variant: "outline" },
};

export function BacktestStatusBadge({ status }: { status: BacktestStatus }) {
  const meta = STATUS_META[status];
  return (
    <Badge variant={meta.variant} data-status={status}>
      {meta.label}
    </Badge>
  );
}

export { STATUS_META };
