// 백테스트 목록 라우트 레벨 Suspense fallback — C 디자인 언어 골격 스켈레톤.
// 실화면(BacktestList)의 .page 헤더 카드 + 실행 목록 표 자리를 .sk 로 잡아
// 레이아웃 이동을 줄인다. 목록 화면에 없는 KPI 그리드는 그리지 않는다.

export default function BacktestsLoading() {
  return (
    <main className="page" aria-busy="true" aria-label="백테스트 목록 불러오는 중">
      <section className="card">
        <div className="report">
          <div>
            <div className="sk sk-line" style={{ width: 160, height: 28 }} />
            <div className="report-meta">
              {/* 실헤더 칩 3개(건수·Bybit·엔진)와 개수를 맞춘다. */}
              {Array.from({ length: 3 }).map((_, i) => (
                <span key={i} className="sk" style={{ display: "block", width: 96, height: 26 }} />
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="section" aria-hidden="true">
        <div className="card">
          <div className="table-wrap">
            <table className="trades runs-table">
              <tbody>
                {Array.from({ length: 6 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 11 }).map((__, j) => (
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
