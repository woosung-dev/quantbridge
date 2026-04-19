import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";

type TradingEmptyStateProps = {
  icon: LucideIcon;
  title: string;
  description: string;
  ctaLabel: string;
  ctaHref: string;
};

export function TradingEmptyState({
  icon: Icon,
  title,
  description,
  ctaLabel,
  ctaHref,
}: TradingEmptyStateProps) {
  return (
    <div className="mx-auto max-w-md rounded-[var(--radius-lg)] border border-dashed border-[color:var(--border-dark)] bg-white p-8 text-center">
      <div className="mx-auto mb-4 grid size-12 place-items-center rounded-full bg-[color:var(--primary-light)] text-[color:var(--primary)]">
        <Icon className="size-6" strokeWidth={1.5} />
      </div>
      <h3 className="text-base font-semibold text-[color:var(--text-primary)]">
        {title}
      </h3>
      <p className="mt-2 text-sm text-[color:var(--text-secondary)]">
        {description}
      </p>
      <div className="mt-5 flex justify-center">
        <Button render={<Link href={ctaHref} />} nativeButton={false} size="sm">
          {ctaLabel}
        </Button>
      </div>
    </div>
  );
}
