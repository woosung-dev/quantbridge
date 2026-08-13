// 주문 블로터 라우트 레벨 Suspense fallback — App Router 규약.

import { Skeleton } from "@/components/skeleton";

export default function OrdersLoading() {
  return (
    <div className="container mx-auto space-y-6 px-4 py-6">
      <header className="space-y-2">
        <Skeleton className="h-7 w-36" />
        <Skeleton variant="text" className="w-64" />
      </header>
      <div className="space-y-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} variant="list-row" />
        ))}
      </div>
    </div>
  );
}
