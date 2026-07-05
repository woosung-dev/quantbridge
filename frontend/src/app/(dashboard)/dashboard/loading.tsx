// 대시보드 코크핏 라우트 레벨 Suspense fallback — App Router 규약.

import { Skeleton } from "@/components/skeleton";

export default function DashboardLoading() {
  return (
    <div className="container mx-auto space-y-6 px-4 py-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
      <Skeleton className="h-[280px] w-full" />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Skeleton variant="card" />
        <Skeleton variant="card" />
      </div>
    </div>
  );
}
