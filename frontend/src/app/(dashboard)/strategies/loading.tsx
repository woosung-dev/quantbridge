// 전략 리스트 라우트 레벨 Suspense fallback — App Router 규약.
// server prefetch가 실패하거나 streaming 지연 시 노출.

export default function StrategiesLoading() {
  return (
    <div className="mx-auto max-w-[1200px] px-6 py-8">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <div className="mb-2 h-7 w-32 animate-pulse rounded bg-[color:var(--bg-alt)]" />
          <div className="h-4 w-48 animate-pulse rounded bg-[color:var(--bg-alt)]" />
        </div>
        <div className="h-9 w-24 animate-pulse rounded bg-[color:var(--bg-alt)]" />
      </header>
      <div className="mb-6 h-9 w-full animate-pulse rounded bg-[color:var(--bg-alt)]" />
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="h-36 animate-pulse rounded-[var(--radius-lg)] bg-[color:var(--bg-alt)]"
          />
        ))}
      </div>
    </div>
  );
}
