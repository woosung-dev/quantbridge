// 대시보드 홈 — Stage 3 스프린트에서 03-trading-dashboard.html 프로토타입 기반 구현
export default function DashboardPage() {
  return (
    <section className="flex flex-col gap-6 p-6 md:p-8">
      <header className="flex flex-col gap-2">
        <h1 className="font-display text-2xl font-bold md:text-3xl">대시보드</h1>
        <p className="text-sm text-[color:var(--dash-text-muted)]">
          스캐폴드 상태 — 도메인별 위젯은 Stage 3에서 추가됩니다.
        </p>
      </header>
    </section>
  );
}
