// 랜딩 04 성능 (.perf-grid) — 대표 실행 1회 측정값 3개 + 조건. screen-14-landing.html 이식.
// 조건 없는 속도 형용사 금지(_KIT.md §4.8). 공동 원장은 lib/marketing-canon.ts.
import { PERF_DISCLAIMER, PERF_FIGURES } from "@/lib/marketing-canon";

export function LandingPerformance() {
  return (
    <section className="section rise d5" aria-label="성능 표기">
      <header className="section-head">
        <p className="eyebrow">
          <span className="num">04</span> 성능
        </p>
        <h2 className="section-title">속도는 조건과 함께 적습니다</h2>
        <p className="section-desc">
          조건 없는 초고속 같은 표현은 쓰지 않습니다. 아래는 대표 실행 한 번을 측정한 값입니다.
        </p>
      </header>

      <div className="card">
        <div className="perf-grid">
          {PERF_FIGURES.map((f) => (
            <div key={f.value} className="perf-cell">
              <p className="perf-v mono">{f.value}</p>
              <p className="perf-k">{f.note}</p>
            </div>
          ))}
        </div>
        <p className="sup-note">{PERF_DISCLAIMER}</p>
      </div>
    </section>
  );
}
