// 대시보드 라우트 레벨 Suspense fallback (S7) — C 디자인 언어 골격 스켈레톤.
// 실제 페이지의 report 헤더 + KPI 4칸 + 카드 자리를 .sk 로 잡아 레이아웃 이동을 줄인다.

export default function DashboardLoading() {
  return (
    <main className="page" aria-busy="true" aria-label="대시보드 불러오는 중">
      <section className="card">
        <div className="card-body">
          <div className="sk sk-line" style={{ width: "40%", height: 28 }} />
          <div className="sk sk-line" style={{ width: "60%", marginTop: 14 }} />
        </div>
      </section>

      <div className="kpi-row" style={{ marginTop: 28 }}>
        {Array.from({ length: 4 }).map((_, i) => (
          <article key={i} className="card kpi">
            <div className="sk sk-line" style={{ width: "50%" }} />
            <div className="sk sk-line" style={{ width: "70%", height: 28, marginTop: 12 }} />
            <div className="sk sk-line" style={{ width: "90%", marginTop: 12 }} />
          </article>
        ))}
      </div>

      <div className="card" style={{ marginTop: 28 }}>
        <div className="card-body">
          <div className="sk-bars" aria-hidden="true">
            {[52, 34, 80, 61, 43, 74, 29, 66].map((h, i) => (
              <span key={i} className="sk" style={{ height: `${h}%` }} />
            ))}
          </div>
          <div className="sk sk-line" style={{ width: "58%", marginTop: 14 }} />
        </div>
      </div>
    </main>
  );
}
