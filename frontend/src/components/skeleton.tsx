// 로딩 Skeleton 공통 — Suspense fallback / async 데이터 로드 표준 placeholder.
// shadcn 패턴 (animate-pulse + bg-muted) + qb-specific 변형 (Table / Card / Form).

import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Skeleton({
  className,
  "data-testid": dataTestId = "skeleton",
  ...props
}: HTMLAttributes<HTMLDivElement> & { "data-testid"?: string }) {
  return (
    <div
      data-slot="skeleton"
      data-testid={dataTestId}
      className={cn("animate-pulse rounded-md bg-muted", className)}
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
