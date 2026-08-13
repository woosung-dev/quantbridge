// Optimizer run 상세 라우트 레벨 Suspense fallback — App Router 규약. C 셸(.page/.card/.kpi/.sk) 정합.

export default function OptimizerRunLoading() {
  return (
    <main className="page" aria-busy="true">
      <div className="card">
        <div className="card-body">
          <span className="sk sk-line" style={{ width: "40%", height: 24 }} />
          <span className="sk sk-line" style={{ width: "70%" }} />
        </div>
      </div>
      <div className="section">
        <div className="kpi-row">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="card kpi">
              <span className="sk sk-line" style={{ width: "60%" }} />
              <span className="sk sk-line" style={{ width: "80%", height: 24, marginTop: 10 }} />
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
