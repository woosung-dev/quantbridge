// 전략 리스트 라우트 레벨 Suspense fallback — C 디자인 언어(screen-06) 표 스켈레톤.
// server prefetch 실패/스트리밍 지연 시 노출. 목록 컴포넌트의 .sk .sk-cell 골격과 같다.

export default function StrategiesLoading() {
  return (
    <main className="page" aria-busy="true" aria-label="전략 목록 불러오는 중">
      <section className="card" aria-label="전략 목록 개요">
        <div className="card-body">
          <span className="sk sk-line" style={{ width: "160px" }} aria-hidden="true" />
        </div>
      </section>
      <section className="section">
        <div className="card">
          <div className="table-wrap">
            <table className="trades runs-table">
              <tbody>
                {Array.from({ length: 6 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 5 }).map((__, j) => (
                      <td key={j}>
                        <span className="sk sk-cell" />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </main>
  );
}
