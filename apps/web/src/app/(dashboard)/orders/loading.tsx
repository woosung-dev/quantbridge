// 주문 블로터 라우트 레벨 Suspense fallback — App Router 규약.

import { Skeleton } from "@/components/skeleton";

const ORDER_SKELETON_ROW_KEYS = [
  "row-1",
  "row-2",
  "row-3",
  "row-4",
  "row-5",
  "row-6",
  "row-7",
  "row-8",
];

export default function OrdersLoading() {
  return (
    <div className="container mx-auto space-y-6 px-4 py-6">
      <header className="space-y-2">
        <Skeleton className="h-7 w-36" />
        <Skeleton variant="text" className="w-64" />
      </header>
      <div className="space-y-2">
        {ORDER_SKELETON_ROW_KEYS.map((key) => (
          <Skeleton key={key} variant="list-row" />
        ))}
      </div>
    </div>
  );
}
