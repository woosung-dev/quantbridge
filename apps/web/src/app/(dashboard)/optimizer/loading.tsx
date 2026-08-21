// Optimizer 목록 라우트 레벨 Suspense fallback — App Router 규약. C 셸(.page/.card/.sk) 정합.

const OPTIMIZER_LINE_KEYS = ["line-1", "line-2", "line-3", "line-4", "line-5"];

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
            {OPTIMIZER_LINE_KEYS.map((key) => (
              <span key={key} className="sk sk-line" style={{ width: "100%", height: 14 }} />
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
