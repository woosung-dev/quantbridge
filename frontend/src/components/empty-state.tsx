// 빈상태 공통 컴포넌트 — Sprint 41 신규 페이지/섹션용 표준 EmptyState.
// 기존 strategy-empty-state / trading-empty-state 와 별도 운영 (점진적 통합).

import Link from "next/link";
import { type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type EmptyStateCta = {
  label: string;
  href?: string;
  onClick?: () => void;
};

export type EmptyStateProps = {
  icon?: ReactNode;
  headline: string;
  description?: string;
  cta?: EmptyStateCta;
  className?: string;
};

export function EmptyState({
  icon,
  headline,
  description,
  cta,
  className,
}: EmptyStateProps) {
  return (
    <div
      role="status"
      data-testid="empty-state"
      className={cn(
        "qb-empty-card-in mx-auto flex max-w-md flex-col items-center gap-3 rounded-xl border border-dashed border-[color:var(--border-dark,oklch(0.85_0_0))] bg-card px-6 py-12 text-center text-sm",
        className,
      )}
    >
      {icon ? (
        <div
          aria-hidden="true"
          data-testid="empty-state-icon"
          className="qb-empty-icon-in grid size-12 place-items-center rounded-full bg-muted text-muted-foreground"
        >
          {icon}
        </div>
      ) : null}
      <h2
        data-testid="empty-state-headline"
        className="qb-empty-heading-in font-display text-base font-semibold leading-tight text-foreground text-balance"
      >
        {headline}
      </h2>
      {description ? (
        <p
          data-testid="empty-state-description"
          className="qb-empty-body-in text-sm leading-relaxed text-muted-foreground text-balance"
        >
          {description}
        </p>
      ) : null}
      {cta ? <EmptyStateCtaButton cta={cta} /> : null}
    </div>
  );
}

function EmptyStateCtaButton({ cta }: { cta: EmptyStateCta }) {
  // mt-2 + stagger 등장 + Primary hover (shadow upgrade — DESIGN.md --btn-primary-shadow-hover).
  const ctaClassName =
    "qb-empty-cta-in mt-2 shadow-[var(--btn-primary-shadow,_0_4px_14px_rgba(37,99,235,0.25))] transition-shadow duration-200 hover:shadow-[var(--btn-primary-shadow-hover,_0_6px_20px_rgba(37,99,235,0.35))]";

  if (cta.href) {
    return (
      <Button
        render={<Link href={cta.href} />}
        nativeButton={false}
        data-testid="empty-state-cta"
        className={ctaClassName}
      >
        {cta.label}
      </Button>
    );
  }
  return (
    <Button
      type="button"
      data-testid="empty-state-cta"
      onClick={cta.onClick}
      className={ctaClassName}
    >
      {cta.label}
    </Button>
  );
}
