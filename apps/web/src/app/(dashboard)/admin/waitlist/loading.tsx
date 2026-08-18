// Admin waitlist 라우트 레벨 Suspense fallback — App Router 규약 (trading/loading.tsx 관례).
// 본문 셸(max-w-[1200px] px-6 py-8)과 같은 골격: 헤더 + KPI strip 3칸 + 표 자리.

import { Skeleton, TableSkeleton } from "@/components/skeleton";

export default function AdminWaitlistLoading() {
  return (
    <div className="mx-auto max-w-[1200px] space-y-6 px-6 py-8">
      <header className="space-y-2">
        <Skeleton className="h-7 w-48" />
        <Skeleton variant="text" className="w-72" />
      </header>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Skeleton variant="card" className="h-28" />
        <Skeleton variant="card" className="h-28" />
        <Skeleton variant="card" className="h-28" />
      </div>
      <TableSkeleton rows={6} columns={8} />
    </div>
  );
}
