// Optimizer 목록 라우트 레벨 Suspense fallback — App Router 규약. C 셸(.page/.card/.sk) 정합.

export default function OptimizerLoading() {
  return (
    <main className="page" aria-busy="true">
      <div className="card">
        <div className="card-body">
          <span className="sk sk-line" style={{ width: "30%", height: 24 }} />
          <span className="sk sk-line" style={{ width: "60%" }} />
        </div>
      </div>
      <div className="section">
        <div className="card">
          <div className="card-body">
            {Array.from({ length: 5 }).map((_, i) => (
              <span key={i} className="sk sk-line" style={{ width: "100%", height: 14 }} />
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
