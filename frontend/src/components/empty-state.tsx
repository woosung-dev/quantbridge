// 빈상태 공통 컴포넌트 — Sprint 41 신규 페이지/섹션용 표준 EmptyState.
// 기존 strategy-empty-state / trading-empty-state 와 별도 운영 (점진적 통합).
// Sprint 47 BL-206: variant API (default / search / error / first-run) — icon tint + border 일관성.

import Link from "next/link";
import { type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * EmptyState variant — 페이지/섹션별 의미 구분.
 * - default: 일반 빈 상태 (기본값). neutral 톤.
 * - search: 검색 결과 없음. neutral 톤 + 다른 메시지 hint.
 * - error: 오류로 인해 데이터 없음. destructive border + icon tint.
 * - first-run: 최초 사용자 onboarding. primary border + 강조 톤.
 */
export type EmptyStateVariant = "default" | "search" | "error" | "first-run";

const VARIANT_CONTAINER_CLASSES: Record<EmptyStateVariant, string> = {
  default:
    "border-[color:var(--border-dark,oklch(0.85_0_0))] bg-card",
  search:
    "border-[color:var(--border-dark,oklch(0.85_0_0))] bg-card",
  error:
    "border-[color:var(--destructive,#ef4444)] bg-card",
  "first-run":
    "border-[color:var(--primary,#2563eb)] bg-card",
};

const VARIANT_ICON_CLASSES: Record<EmptyStateVariant, string> = {
  default: "bg-muted text-muted-foreground",
  search: "bg-muted text-muted-foreground",
  error: "bg-[color:var(--destructive,#ef4444)]/10 text-[color:var(--destructive,#ef4444)]",
  "first-run": "bg-[color:var(--primary,#2563eb)]/10 text-[color:var(--primary,#2563eb)]",
};

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
  /** 의미 변형. 미지정 시 default. */
  variant?: EmptyStateVariant;
};

export function EmptyState({
  icon,
  headline,
  description,
  cta,
  className,
  variant = "default",
}: EmptyStateProps) {
  return (
    <div
      role="status"
      data-testid="empty-state"
      data-variant={variant}
      className={cn(
        "qb-empty-card-in mx-auto flex max-w-md flex-col items-center gap-3 rounded-xl border border-dashed px-6 py-12 text-center text-sm",
        VARIANT_CONTAINER_CLASSES[variant],
        className,
      )}
    >
      {icon ? (
        <div
          aria-hidden="true"
          data-testid="empty-state-icon"
          className={cn(
            "qb-empty-icon-in grid size-12 place-items-center rounded-full",
            VARIANT_ICON_CLASSES[variant],
          )}
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
