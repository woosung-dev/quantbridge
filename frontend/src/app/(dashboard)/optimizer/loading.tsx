// Optimizer 목록 라우트 레벨 Suspense fallback — App Router 규약.

import { Skeleton } from "@/components/skeleton";

export default function OptimizerLoading() {
  return (
    <div className="container mx-auto space-y-6 px-4 py-6">
      <header className="space-y-2">
        <Skeleton className="h-7 w-44" />
        <Skeleton variant="text" className="w-80" />
      </header>
      <div className="flex flex-wrap items-center gap-3">
        <Skeleton className="h-10 w-[240px]" />
        <Skeleton className="h-10 w-52" />
        <Skeleton className="h-10 w-40" />
      </div>
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} variant="list-row" />
        ))}
      </div>
    </div>
  );
}
