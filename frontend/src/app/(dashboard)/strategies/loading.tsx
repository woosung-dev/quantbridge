// 전략 리스트 라우트 레벨 Suspense fallback — App Router 규약.
// server prefetch가 실패하거나 streaming 지연 시 노출.
// Sprint 47 BL-206: animate-pulse 직접 사용 → Skeleton variant API 로 SSOT 일원화.

import { Skeleton } from "@/components/skeleton";

export default function StrategiesLoading() {
  return (
    <div className="mx-auto max-w-[1200px] px-6 py-8">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <Skeleton className="mb-2 h-7 w-32" />
          <Skeleton variant="text" className="w-48" />
        </div>
        <Skeleton className="h-9 w-24" />
      </header>
      <Skeleton className="mb-6 h-9 w-full" />
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} variant="card" />
        ))}
      </div>
    </div>
  );
}
