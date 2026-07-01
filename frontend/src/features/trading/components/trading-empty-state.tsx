import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";

type TradingEmptyStateProps = {
  icon: LucideIcon;
  title: string;
  description: string;
  ctaLabel?: string;
  ctaHref?: string;
};

export function TradingEmptyState({
  icon: Icon,
  title,
  description,
  ctaLabel,
  ctaHref,
}: TradingEmptyStateProps) {
  return (
    <div className="mx-auto max-w-md rounded-[var(--radius-lg)] border border-dashed border-border-dark bg-card p-8 text-center">
      <div className="mx-auto mb-4 grid size-12 place-items-center rounded-full bg-primary-light text-primary">
        <Icon className="size-6" strokeWidth={1.5} />
      </div>
      <h3 className="text-base font-semibold text-foreground">
        {title}
      </h3>
      <p className="mt-2 text-sm text-text-secondary">
        {description}
      </p>
      {ctaLabel && ctaHref && (
        <div className="mt-5 flex justify-center">
          <Button render={<Link href={ctaHref} />} nativeButton={false} size="sm">
            {ctaLabel}
          </Button>
        </div>
      )}
    </div>
  );
}
