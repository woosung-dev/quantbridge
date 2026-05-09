// 랜딩 페이지 푸터 — Brand + Legal 활성 + 소셜 placeholder. 외부 페이지 (블로그/문서/채용) 미존재 컬럼은 비활성 처리
import Link from "next/link";

interface FooterLink {
  label: string;
  href?: string;
}

interface FooterColumn {
  heading: string;
  links: FooterLink[];
}

const FOOTER_COLUMNS: FooterColumn[] = [
  {
    heading: "Product",
    links: [
      { label: "기능", href: "#features" },
      { label: "사용법", href: "#how-it-works" },
      { label: "요금제", href: "#pricing" },
      { label: "FAQ", href: "#faq" },
    ],
  },
  {
    heading: "Resources",
    links: [{ label: "문서 (준비 중)" }, { label: "API 레퍼런스 (준비 중)" }],
  },
  {
    heading: "Company",
    links: [{ label: "소개 (준비 중)" }, { label: "연락처 (준비 중)" }],
  },
  {
    heading: "Legal",
    links: [
      { label: "이용약관", href: "/terms" },
      { label: "개인정보처리방침", href: "/privacy" },
      { label: "면책조항", href: "/disclaimer" },
    ],
  },
];

export function LandingFooter() {
  return (
    <footer
      aria-labelledby="footer-heading"
      className="border-t border-[color:var(--border)] bg-[color:var(--bg-alt)] px-6 py-14"
    >
      <h2 id="footer-heading" className="sr-only">
        푸터
      </h2>
      <div className="mx-auto max-w-[1200px]">
        <div className="grid grid-cols-2 gap-10 md:grid-cols-3 lg:grid-cols-5">
          <div className="col-span-2 lg:col-span-1">
            <Link
              href="/"
              className="flex items-center gap-2 font-display text-base font-bold text-[color:var(--text-primary)]"
            >
              <svg
                width="28"
                height="28"
                viewBox="0 0 28 28"
                fill="none"
                aria-hidden
              >
                <path
                  d="M4 20C4 20 8 8 14 8C20 8 24 20 24 20"
                  stroke="#2563EB"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                />
                <path
                  d="M2 18C2 18 7 10 14 10C21 10 26 18 26 18"
                  stroke="#0F172A"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
              <span>QuantBridge</span>
            </Link>
            <p className="mt-3 max-w-[240px] text-sm text-[color:var(--text-secondary)]">
              Pine Script 전략을 백테스트부터 자동 매매까지 한 번에.
            </p>
          </div>

          {FOOTER_COLUMNS.map((col) => (
            <div key={col.heading}>
              <h3 className="text-sm font-semibold text-[color:var(--text-primary)]">
                {col.heading}
              </h3>
              <ul className="mt-3 space-y-2">
                {col.links.map((link) => (
                  <li key={link.label}>
                    {link.href ? (
                      link.href.startsWith("#") ? (
                        <a
                          href={link.href}
                          className="text-sm text-[color:var(--text-secondary)] transition-colors hover:text-[color:var(--primary)]"
                        >
                          {link.label}
                        </a>
                      ) : (
                        <Link
                          href={link.href}
                          className="text-sm text-[color:var(--text-secondary)] transition-colors hover:text-[color:var(--primary)]"
                        >
                          {link.label}
                        </Link>
                      )
                    ) : (
                      <span className="text-sm text-[color:var(--text-muted)]">
                        {link.label}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col gap-4 border-t border-[color:var(--border)] pt-6 md:flex-row md:items-center md:justify-between">
          <span className="text-xs text-[color:var(--text-muted)]">
            © 2026 QuantBridge. All rights reserved.
          </span>
          <p className="text-xs text-[color:var(--text-muted)]">
            본 서비스는 투자 자문이 아니며, 모든 트레이딩 결정과 결과는
            사용자 본인의 책임입니다.
          </p>
        </div>
      </div>
    </footer>
  );
}
