// 로딩 Skeleton 공통 — Suspense fallback / async 데이터 로드 표준 placeholder.
// shadcn 패턴 (animate-pulse + bg-muted) + qb-specific 변형 (Table / Card / Form).
// Sprint 44 W C3: shimmer 1.5s overlay 옵션 + radius 토큰 정합 (--radius-sm = 6px = rounded-md).
// Sprint 47 BL-206: variant API (text / card / list-row / chart / table-cell) — animate-pulse SSOT 일원화.

import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/**
 * Skeleton variant — 페이지/컴포넌트별 자주 쓰이는 placeholder shape 사전 정의.
 * - text: 작은 텍스트 라인 (h-4)
 * - card: 카드/그리드 placeholder (h-36 + radius-lg)
 * - list-row: 테이블/리스트 행 (h-12)
 * - chart: 차트/대형 영역 (h-64)
 * - table-cell: 좁은 셀 (h-6 w-24)
 *
 * 모든 variant 는 `className` 으로 height/width 를 override 가능 (twMerge 충돌 해결).
 */
export type SkeletonVariant =
  | "text"
  | "card"
  | "list-row"
  | "chart"
  | "table-cell";

const VARIANT_CLASSES: Record<SkeletonVariant, string> = {
  text: "h-4 w-full",
  card: "h-36 w-full rounded-[var(--radius-lg)]",
  "list-row": "h-12 w-full",
  chart: "h-64 w-full",
  "table-cell": "h-6 w-24",
};

export type SkeletonProps = HTMLAttributes<HTMLDivElement> & {
  "data-testid"?: string;
  /** shimmer overlay (1.5s) 활성화. 카드/리포트 등 명시적 강조가 필요한 곳에 사용. 기본 false (animate-pulse 만). */
  shimmer?: boolean;
  /** placeholder shape variant. 미지정 시 height/width 없이 base class 만 적용 (legacy 호환). */
  variant?: SkeletonVariant;
};

export function Skeleton({
  className,
  "data-testid": dataTestId = "skeleton",
  shimmer = false,
  variant,
  ...props
}: SkeletonProps) {
  return (
    <div
      data-slot="skeleton"
      data-testid={dataTestId}
      data-variant={variant}
      className={cn(
        "animate-pulse rounded-md bg-muted",
        variant && VARIANT_CLASSES[variant],
        shimmer && "qb-skeleton-shimmer",
        className,
      )}
      {...props}
    />
  );
}

export function TableSkeleton({
  rows = 5,
  columns = 4,
  className,
}: {
  rows?: number;
  columns?: number;
  className?: string;
}) {
  return (
    <div
      data-testid="table-skeleton"
      role="status"
      aria-label="목록을 불러오는 중"
      className={cn("flex flex-col gap-3", className)}
    >
      <div className="flex gap-3">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton
            key={`hdr-${i}`}
            className="h-4 flex-1"
            data-testid="table-skeleton-header-cell"
          />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={`row-${r}`} className="flex gap-3">
          {Array.from({ length: columns }).map((_, c) => (
            <Skeleton
              key={`row-${r}-col-${c}`}
              className="h-8 flex-1"
              data-testid="table-skeleton-row-cell"
            />
          ))}
        </div>
      ))}
    </div>
  );
}

export function CardSkeleton({ className }: { className?: string }) {
  return (
    <div
      data-testid="card-skeleton"
      role="status"
      aria-label="카드를 불러오는 중"
      className={cn(
        "flex flex-col gap-3 rounded-xl border bg-card p-4",
        className,
      )}
    >
      <Skeleton className="h-5 w-1/3" />
      <Skeleton className="h-4 w-2/3" />
      <Skeleton className="h-20 w-full" />
    </div>
  );
}

export function FormSkeleton({
  fields = 3,
  className,
}: {
  fields?: number;
  className?: string;
}) {
  return (
    <div
      data-testid="form-skeleton"
      role="status"
      aria-label="폼을 불러오는 중"
      className={cn("flex flex-col gap-5", className)}
    >
      {Array.from({ length: fields }).map((_, i) => (
        <div
          key={`field-${i}`}
          data-testid="form-skeleton-field"
          className="flex flex-col gap-1.5"
        >
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-10 w-full" />
        </div>
      ))}
    </div>
  );
}
