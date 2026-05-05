// Sprint 33 BL-174 list-only — Empty/Failed/Loading state 통일 컴포넌트.
// trading-empty-state pattern 복제 + variant (default/destructive) + iconClassName (animate-spin 등).
// scope = live-session 도메인 전용. Sprint 34+ generic refactor 후보.

import type { LucideIcon } from "lucide-react";

type Variant = "default" | "destructive";

type Props = {
  icon: LucideIcon;
  iconClassName?: string;
  title: string;
  description: string;
  variant?: Variant;
  testId?: string;
};

export function LiveSessionStateView({
  icon: Icon,
  iconClassName,
  title,
  description,
  variant = "default",
  testId,
}: Props) {
  const isError = variant === "destructive";
  const toneText = isError ? "text-destructive" : "text-muted-foreground";
  const iconBg = isError ? "bg-destructive/10 text-destructive" : "bg-muted text-muted-foreground";

  return (
    <div
      className="rounded-md border border-dashed p-6 text-center"
      data-testid={testId}
      role={isError ? "alert" : "status"}
    >
      <div
        className={`mx-auto mb-2 grid size-10 place-items-center rounded-full ${iconBg}`}
      >
        <Icon
          className={`size-5${iconClassName ? ` ${iconClassName}` : ""}`}
          strokeWidth={1.5}
        />
      </div>
      <p className="text-sm font-medium">{title}</p>
      <p className={`mt-1 text-xs ${toneText}`}>{description}</p>
    </div>
  );
}
