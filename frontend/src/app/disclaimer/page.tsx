// Disclaimer (면책조항) — 법무 임시본. Sprint 43 W14: legal-page-shell + accent-amber risk callout.

import type { Metadata } from "next";

import { LegalCallout } from "../_components/legal-callout";
import { LegalPageShell } from "../_components/legal-page-shell";

export const metadata: Metadata = {
  title: "Disclaimer · QuantBridge",
  description: "QuantBridge Beta 면책조항 (법무 임시본)",
};

const headingClass =
  "text-[22px] font-semibold leading-snug tracking-[-0.01em] text-[color:var(--text-primary)]";

export default function DisclaimerPage() {
  return (
    <LegalPageShell
      title="Disclaimer / 면책조항"
      breadcrumbLabel="Disclaimer"
      badgeLabel="Beta 임시본"
      footnote="최종 개정: 2026-04-25 (Beta 임시본). 정식 개정본은 H2 말 공지."
    >
      <LegalCallout label="[법무 임시 — 법적 효력 제한적]">
        본 문서는 H2 Beta 단계의 임시 템플릿입니다. H2 말 (~2026-06-30) 한국 변호사 검토본으로
        교체 예정.
      </LegalCallout>

      <section className="space-y-3">
        <h2 className={headingClass}>1. No Investment Advice</h2>
        <p>
          QuantBridge (이하 &ldquo;서비스&rdquo;) 가 제공하는 백테스트, 지표, 알림, 자동매매 기능은
          <strong> 투자 자문 (investment advice) 이 아닙니다</strong>. 사용자는 본인 책임 하에
          거래 결정을 내려야 하며, 필요 시 자격 있는 금융 자문가와 상의해야 합니다.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className={headingClass}>2. Trading Risk / 거래 위험</h2>
        <LegalCallout label="중요 경고:">
          암호화폐 파생상품 거래는 <strong>원금 전액 손실</strong>을 포함한 높은 위험을 수반합니다.
          레버리지 거래 시 손실은 투입 자본을 초과할 수 있습니다. 과거 백테스트 성과는 미래
          성과를 보장하지 않으며, 시장 상황·거래소 정책·네트워크 장애 등 다양한 요인으로 인해
          실제 결과가 백테스트와 상이할 수 있습니다.
        </LegalCallout>
      </section>

      <section className="space-y-3">
        <h2 className={headingClass}>3. Service Availability</h2>
        <p>
          서비스는 &ldquo;있는 그대로 (as-is)&rdquo; 제공되며, 가용성·정확성·적시성에 대해 어떠한
          보증도 하지 않습니다. 기술적 장애, 거래소 API 변경, 네트워크 지연, Kill Switch 작동 등으로
          인해 거래 실행이 지연되거나 실패할 수 있습니다.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className={headingClass}>4. Geographic Restrictions</h2>
        <p>
          서비스는 현재 <strong>아시아-태평양 지역</strong>에서만 제공됩니다. 미국, 영국, EU 27개국
          거주자의 가입 및 이용이 제한됩니다.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className={headingClass}>5. Limitation of Liability</h2>
        <p>
          QuantBridge 운영자는 서비스 사용으로 인한 직접·간접·우발적·특별·결과적 손해에 대해
          법이 허용하는 최대 한도 내에서 <strong>어떠한 책임도 지지 않습니다</strong>. 이는 데이터
          손실, 거래 손실, 영업 기회 상실, 기술적 장애를 포함하되 이에 한정되지 않습니다.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className={headingClass}>6. English Summary</h2>
        <p className="italic text-[color:var(--text-muted)]">
          QuantBridge is a Beta testing platform. Not investment advice. Trading cryptocurrency
          derivatives involves substantial risk including total loss of capital. Service provided
          as-is without warranty. Available in Asia-Pacific only. Operator disclaims liability to
          the fullest extent permitted by law.
        </p>
      </section>
    </LegalPageShell>
  );
}
