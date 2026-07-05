// Optimizer run 상세 라우트 레벨 Suspense fallback — App Router 규약.

import { Skeleton } from "@/components/skeleton";

export default function OptimizerRunLoading() {
  return (
    <main className="container mx-auto space-y-6 px-4 py-6">
      <header className="space-y-2">
        <Skeleton className="h-7 w-64" />
        <Skeleton variant="text" className="w-48" />
      </header>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-20 w-full" />
        ))}
      </div>
      <Skeleton className="h-[320px] w-full" />
    </main>
  );
}
