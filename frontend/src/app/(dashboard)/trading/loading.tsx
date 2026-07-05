// 트레이딩 대시보드 라우트 레벨 Suspense fallback — App Router 규약.

import { Skeleton } from "@/components/skeleton";

export default function TradingLoading() {
  return (
    <div className="container mx-auto space-y-6 px-4 py-6">
      <header className="space-y-2">
        <Skeleton className="h-7 w-48" />
        <Skeleton variant="text" className="w-72" />
      </header>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Skeleton variant="card" />
        <Skeleton variant="card" />
      </div>
      <div className="space-y-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} variant="list-row" />
        ))}
      </div>
    </div>
  );
}
