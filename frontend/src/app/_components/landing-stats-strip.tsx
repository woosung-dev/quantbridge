// 랜딩 KPI strip — 4개 통계 (활성 전략 / 가동률 / 거래량 / 평점)
const STATS = [
  { value: "10,000+", label: "활성 전략" },
  { value: "99.97%", label: "시스템 가동률" },
  { value: "$2.4B+", label: "총 거래량" },
  { value: "4.8", label: "사용자 평점" },
] as const;

export function LandingStatsStrip() {
  return (
    <section
      aria-label="플랫폼 통계"
      className="border-y border-[color:var(--border)] bg-[color:var(--bg-alt)] px-6 py-12"
    >
      <div className="mx-auto grid max-w-[1200px] grid-cols-2 gap-8 md:grid-cols-4">
        {STATS.map((s) => (
          <div key={s.label} className="text-center">
            <div className="font-mono text-3xl font-extrabold text-[color:var(--text-primary)] md:text-4xl">
              {s.value}
            </div>
            <div className="mt-2 text-sm text-[color:var(--text-muted)]">
              {s.label}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
