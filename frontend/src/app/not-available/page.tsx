// geo-block 에 의해 redirect 되는 안내 페이지. Sprint 43 W14: legal-page-shell centered + email contact.

import { LegalPageShell } from "../_components/legal-page-shell";

const linkClass =
  "underline decoration-[color:var(--border-dark)] underline-offset-4 transition-colors hover:text-[color:var(--text-primary)] hover:decoration-[color:var(--text-primary)]";

export default function NotAvailablePage() {
  return (
    <LegalPageShell
      title="QuantBridge is not available in your region"
      centered
    >
      <p className="text-center text-[16px] leading-[1.7] text-[color:var(--text-secondary)] md:text-[18px]">
        현재 QuantBridge 는 아시아-태평양 지역에서만 제공됩니다. US/EU 거주자는 가입이
        제한되어 있습니다. 서비스 확장 시 waitlist 로 안내드리겠습니다.
      </p>
      <p className="text-center text-[14px] text-[color:var(--text-muted)]">
        Currently serving: Korea · Japan · Singapore · Taiwan · Hong Kong · Southeast Asia.
      </p>
      <p className="text-center text-[14px] text-[color:var(--text-secondary)]">
        문의:{" "}
        <a href="mailto:hello@quantbridge.ai" className={linkClass}>
          hello@quantbridge.ai
        </a>
      </p>
    </LegalPageShell>
  );
}
