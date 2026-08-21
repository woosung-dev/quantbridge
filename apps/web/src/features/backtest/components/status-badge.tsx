// 백테스트 실행 상태 배지 — 라벨은 용어 SSOT, variant 는 shadcn 표현 계층.
import { Badge } from "@/components/ui/badge";
import { BACKTEST_STATUS_LABEL } from "@/features/backtest/labels";
import type { BacktestStatus } from "@/features/backtest/schemas";
import { statusLabelOf } from "@/lib/labels";

type BadgeVariant = "default" | "secondary" | "destructive" | "outline";

// variant 는 라벨(용어)이 아니라 shadcn Badge 의 표현 결정이라 이 파일에 남긴다.
// 라벨 문자열은 BACKTEST_STATUS_LABEL(용어 SSOT)에서만 온다.
const STATUS_VARIANT: Record<BacktestStatus, BadgeVariant> = {
  queued: "secondary",
  running: "default",
  cancelling: "secondary",
  completed: "outline",
  failed: "destructive",
  cancelled: "outline",
};

export function BacktestStatusBadge({ status }: { status: BacktestStatus }) {
  const variant = STATUS_VARIANT[status];
  const { label } = statusLabelOf(BACKTEST_STATUS_LABEL, status, "backtest.status");
  return (
    <Badge
      variant={variant}
      data-status={status}
      className="transition-colors duration-200 ease-out"
    >
      {label}
    </Badge>
  );
}

export { STATUS_VARIANT };
