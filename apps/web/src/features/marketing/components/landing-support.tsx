// 랜딩 03 지원 현황 (.sup-grid) — 거래소 지원 5행 표. screen-14-landing.html 이식.
// 지원으로 적은 것은 실제로 주문이 오간 것만. 공동 원장은 lib/marketing-canon.ts.
import { ExchangeSupportTable } from "@/components/exchange-support-table";
import { ROADMAP_DISCLAIMER } from "@/lib/marketing-canon";

export function LandingSupport() {
  return (
    <section className="section rise d4" id="support" aria-label="지원 현황">
      <header className="section-head">
        <p className="eyebrow">지원 현황</p>
        <h2 className="section-title">지금 연결되는 거래소</h2>
        <p className="section-desc">
          지원한다고 적은 것은 실제로 주문이 오간 것만입니다. 계획 단계는 계획이라고 적습니다.
        </p>
      </header>

      <div className="sup-grid">
        <div className="card sup-table">
          <div className="card-head">
            <div>
              <h3 className="card-title">거래소별 연동 상태</h3>
              <p className="card-sub">지원으로 적은 항목은 실제로 주문이 오간 것만입니다.</p>
            </div>
          </div>
          <ExchangeSupportTable ariaLabel="거래소별 연동 상태" />
          <p className="sup-note">{ROADMAP_DISCLAIMER}</p>
        </div>
      </div>
    </section>
  );
}
