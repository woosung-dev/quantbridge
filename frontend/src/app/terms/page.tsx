// Terms of Service (이용약관) — Beta 단계 초안. Sprint 43 W14: legal-page-shell + callout 통일.

import type { Metadata } from "next";

import { LegalCallout } from "../_components/legal-callout";
import { LegalPageShell } from "../_components/legal-page-shell";

export const metadata: Metadata = {
  title: "Terms of Service · QuantBridge",
  description: "QuantBridge Beta 이용약관",
};

const headingClass =
  "text-[22px] font-semibold leading-snug tracking-[-0.01em] text-[color:var(--text-primary)]";
const bodyListClass = "list-disc space-y-1.5 pl-6 text-[16px] leading-[1.7]";

export default function TermsPage() {
  return (
    <LegalPageShell
      title="Terms of Service / 이용약관"
      breadcrumbLabel="Terms"
      badgeLabel="Beta"
      footnote="최종 개정: 2026-04-25. 정식 개정본은 H2 말 공지."
    >
      <LegalCallout label="[Beta 단계 — 사용자와 함께 다듬는 중입니다]">
        본 약관은 H2 Beta 단계 초안입니다. H2 말 (~2026-06-30) 한국 변호사 검토본으로
        교체 예정.
      </LegalCallout>

      <section className="space-y-3">
        <h2 className={headingClass}>1. Acceptance of Terms</h2>
        <p>
          QuantBridge (이하 &ldquo;서비스&rdquo;) 에 가입하거나 이용함으로써 사용자는 본 약관과
          Disclaimer / Privacy Policy 에 동의한 것으로 간주됩니다.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className={headingClass}>2. Eligibility</h2>
        <ul className={bodyListClass}>
          <li>만 19세 이상 자연인 또는 적법 설립된 법인.</li>
          <li>미국, 영국, EU 27개국 거주자는 가입 제한.</li>
          <li>해당 거래소 (Bybit, OKX 등) 의 KYC 를 직접 통과한 계정 소유자.</li>
          <li>제재 대상자 (OFAC, EU 제재 리스트) 는 이용 불가.</li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className={headingClass}>3. Account Security / 계정 보안</h2>
        <p>
          사용자는 거래소 API Key, Clerk 계정 비밀번호, MFA 토큰의 기밀성을 유지할 책임이
          있습니다. 서비스는 API Key 를 AES-256 으로 암호화하여 저장하되, 사용자의 부주의로
          인한 유출·도용에 대한 책임을 지지 않습니다.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className={headingClass}>4. Prohibited Conduct / 금지 행위</h2>
        <ul className={bodyListClass}>
          <li>서비스 역공학 (reverse engineering), 자동화된 대량 요청 (DDoS, scraping)</li>
          <li>타인의 계정 사용, 계정 판매·양도</li>
          <li>자금세탁, 시세 조작, 기타 법 위반 목적 이용</li>
          <li>서비스 API 키·전략 코드를 무단 재배포</li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className={headingClass}>5. Fees / 수수료</h2>
        <p>
          Beta 단계 (H1~H2) 는 무료. H3 이후 유료 티어 도입 예정이며, 별도 공지 후 신규 사용자부터
          적용. 기존 Beta 사용자에게는 합리적 유예 기간 제공.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className={headingClass}>6. Termination / 이용 정지</h2>
        <p>
          본 약관 위반, 기술적 장애 방지, 법적 요구에 응하기 위해 사전 통지 없이 계정을 정지하거나
          서비스를 종료할 수 있습니다. 사용자는 언제든지 계정 삭제를 요청할 수 있으며, 30일 내
          관련 데이터가 제거됩니다 (법적 보존 의무 제외).
        </p>
      </section>

      <section className="space-y-3">
        <h2 className={headingClass}>7. Governing Law / 준거법</h2>
        <p>
          본 약관은 대한민국 법을 준거법으로 하며, 분쟁 발생 시 서울중앙지방법원을 제1심 전속
          관할 법원으로 합니다.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className={headingClass}>8. Changes to Terms</h2>
        <p>
          본 약관은 서비스 개선·법령 변경 시 수정될 수 있으며, 중요한 변경은 가입 이메일 또는
          대시보드 공지로 최소 7일 전 통지합니다.
        </p>
      </section>
    </LegalPageShell>
  );
}
