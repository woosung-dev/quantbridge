// 랜딩 마케팅 헤더 (.lp-header) — 브랜드 + 앵커 메뉴 + 로그인/시작 CTA + 모바일 햄버거.
// screen-14-landing.html 이식. 요금제는 별도 /pricing 페이지라 nav 앵커에서 뺐다.
"use client";

import { useState } from "react";
import Link from "next/link";

const NAV_ANCHORS = [
  { href: "#features", label: "기능" },
  { href: "#how", label: "작동 방식" },
  { href: "#support", label: "지원 현황" },
  { href: "#faq", label: "FAQ" },
] as const;

export function LandingNav() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="lp-header">
      <a className="lp-brand" href="#main-content" aria-label="QuantBridge 홈으로">
        <span className="brand-mark" aria-hidden="true">
          <svg
            aria-hidden="true"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="3 17 9 11 13 15 21 7" />
            <polyline points="15 7 21 7 21 13" />
          </svg>
        </span>
        <span className="brand-name">QuantBridge</span>
      </a>

      <button
        className="hamburger"
        type="button"
        aria-label={menuOpen ? "메뉴 닫기" : "메뉴 열기"}
        aria-expanded={menuOpen}
        aria-controls="lp-nav"
        onClick={() => setMenuOpen((v) => !v)}
      >
        <svg
          aria-hidden="true"
          width="19"
          height="19"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        >
          <line x1="4" y1="7" x2="20" y2="7" />
          <line x1="4" y1="12" x2="20" y2="12" />
          <line x1="4" y1="17" x2="20" y2="17" />
        </svg>
      </button>

      <nav className={menuOpen ? "lp-nav open" : "lp-nav"} id="lp-nav" aria-label="페이지 안 이동">
        {NAV_ANCHORS.map((a) => (
          <a key={a.href} href={a.href} onClick={() => setMenuOpen(false)}>
            {a.label}
          </a>
        ))}
        <Link href="/sign-in" className="lp-nav-login" onClick={() => setMenuOpen(false)}>
          로그인
        </Link>
      </nav>

      <div className="lp-actions">
        <Link className="btn btn-ghost lp-login" href="/sign-in">
          로그인
        </Link>
        <Link className="btn btn-primary" href="/sign-up">
          시작하기
        </Link>
      </div>
    </header>
  );
}
