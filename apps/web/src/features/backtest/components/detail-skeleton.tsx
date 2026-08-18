// 백테스트 리포트 로딩 스켈레톤 — 라우트 loading.tsx 와 뷰(isLoading)가 공유하는 shape 정본.
// ★독립 모듈인 이유: loading.tsx 가 backtest-detail-view(리포트 섹션 전체 그래프를 정적
//   import)를 물면 폴백이 페이지와 같은 대형 청크에 묶여, 코드가 내려오는 동안 폴백을 못
//   그린다 — loading 경계의 존재 이유가 죽는다 (/vercel-react-best-practices, 2026-08-18).
export function DetailSkeleton() {
  return (
    <main className="page" aria-busy="true" data-testid="backtest-detail-skeleton">
      <section className="card" aria-hidden="true">
        <div className="report">
          <div>
            <span className="sk" style={{ display: "block", width: 220, height: 32 }} />
            <div className="report-meta">
              {/* 실헤더 칩 5개(상태·Bybit·기간·엔진·ID)와 개수를 맞춘다. */}
              {Array.from({ length: 5 }).map((_, i) => (
                <span key={i} className="sk" style={{ display: "block", width: 74, height: 26 }} />
              ))}
            </div>
          </div>
        </div>
      </section>
      <section className="section" aria-hidden="true">
        <div className="kpi-row">
          {Array.from({ length: 4 }).map((_, i) => (
            <article key={i} className="card kpi">
              <span className="sk" style={{ display: "block", width: 88, height: 12 }} />
              <span className="sk" style={{ display: "block", width: 120, height: 30, marginTop: 12 }} />
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
