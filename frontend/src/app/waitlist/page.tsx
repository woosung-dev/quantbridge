// 웨이트리스트 페이지 (/waitlist) — C 디자인 언어 이식. screen-17-waitlist.html.
// 히어로(소개+등록 폼) → 제품 → 지원 현황(거래소 표) → FAQ. 랜딩/요금제 CTA 의 ?email= 프리필.
import type { Metadata } from "next";
import Link from "next/link";

import { ExchangeSupportTable } from "@/components/exchange-support-table";
import { ROADMAP_DISCLAIMER } from "@/lib/marketing-canon";

import { WaitlistFaq } from "./_components/waitlist-faq";
import { WaitlistFormCard } from "./_components/waitlist-form-card";
import { WaitlistHeader } from "./_components/waitlist-header";
import { WaitlistHero } from "./_components/waitlist-hero";
import { WaitlistProduct } from "./_components/waitlist-product";

export const metadata: Metadata = {
  title: "웨이트리스트 · QuantBridge",
  description:
    "QuantBridge 공개 준비가 시작되면 알림을 받도록 등록합니다. 대기자 수나 순번은 집계하지 않습니다.",
};

export default async function WaitlistPage({
  searchParams,
}: {
  searchParams: Promise<{ email?: string }>;
}) {
  const { email } = await searchParams;
  const defaultEmail = typeof email === "string" ? email : "";

  return (
    <div className="waitlist-page">
      <WaitlistHeader />

      <main className="main" id="main-content">
        <div className="page">
          {/* 히어로 + 등록 폼 */}
          <section className="hero-split rise d1" aria-label="소개와 등록">
            <WaitlistHero />
            <WaitlistFormCard defaultEmail={defaultEmail} />
          </section>

          {/* 01 제품 */}
          <WaitlistProduct />

          {/* 02 지원 현황 */}
          <section className="section rise d3" id="support" aria-label="지원 현황">
            <div className="section-head">
              <p className="eyebrow">
                <span className="num">02</span> 거래소
              </p>
              <h2 className="section-title">지금 붙어 있는 거래소.</h2>
              <p className="section-desc">
                아래 두 줄이 현재 연결을 확인한 전부입니다. 나머지는 아직 코드가 없습니다.
              </p>
            </div>

            <div className="card">
              <ExchangeSupportTable ariaLabel="거래소별 연동 상태" />
              <div className="disclaimer">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <circle cx="12" cy="12" r="9" />
                  <line x1="12" y1="11" x2="12" y2="16.5" />
                  <line x1="12" y1="7.5" x2="12" y2="7.6" />
                </svg>
                <span>{ROADMAP_DISCLAIMER}</span>
              </div>
            </div>
          </section>

          {/* 03 FAQ */}
          <WaitlistFaq />

          {/* 푸터 */}
          <footer className="foot">
            <span>QuantBridge · 개인 프로젝트 · woosung</span>
            <span className="foot-links">
              <Link href="/">소개</Link>
              <a href="#build">제품</a>
              <a href="#support">지원 현황</a>
              <a href="#faq">FAQ</a>
            </span>
          </footer>
        </div>
      </main>
    </div>
  );
}
