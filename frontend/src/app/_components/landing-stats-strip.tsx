// landing Beta 정직 표시 — Multi-Agent QA BL-270 fix (Sprint 60 S2)
const HONEST_STATS = [
  { value: "Beta", label: "현재 단계" },
  { value: "Open", label: "feedback 환영" },
  { value: "Dogfood", label: "초기 사용자" },
  { value: "v2.0", label: "최신 버전" },
] as const;

export function LandingStatsStrip() {
  return (
    <section
      aria-label="현재 단계"
      className="border-y border-[color:var(--border)] bg-[color:var(--bg-alt)] px-6 py-12"
    >
      <div className="mx-auto grid max-w-[1200px] grid-cols-2 gap-8 md:grid-cols-4">
        {HONEST_STATS.map((s) => (
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
