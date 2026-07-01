// 랜딩 페이지 상단 sticky nav (logo + 앵커 메뉴 + 로그인/CTA + 모바일 햄버거)
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Menu, X } from "lucide-react";

import { ThemeToggle } from "@/components/ui/theme-toggle";

const NAV_ANCHORS = [
  { href: "#features", label: "기능" },
  { href: "#how-it-works", label: "사용법" },
  { href: "#pricing", label: "요금제" },
  { href: "#faq", label: "FAQ" },
] as const;

export function LandingNav() {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    document.body.style.overflow = menuOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [menuOpen]);

  return (
    <>
      <nav
        aria-label="주요"
        className={`sticky top-0 z-40 border-b bg-card/90 backdrop-blur transition-shadow duration-200 ${
          scrolled
            ? "border-[color:var(--border)] shadow-card"
            : "border-transparent"
        }`}
      >
        <div className="mx-auto flex h-16 max-w-[1200px] items-center justify-between px-6">
          <Link
            href="/"
            className="flex items-center gap-2 font-display text-base font-bold text-[color:var(--text-primary)]"
          >
            <BrandLogo />
            <span>QuantBridge</span>
          </Link>

          <div className="hidden items-center gap-8 md:flex">
            {NAV_ANCHORS.map((a) => (
              <a
                key={a.href}
                href={a.href}
                className="text-sm font-medium text-[color:var(--text-secondary)] transition-colors hover:text-[color:var(--text-primary)]"
              >
                {a.label}
              </a>
            ))}
          </div>

          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Link
              href="/sign-in"
              className="hidden text-sm font-medium text-[color:var(--text-secondary)] transition-colors hover:text-[color:var(--text-primary)] md:inline"
            >
              로그인
            </Link>
            <Link
              href="/sign-up"
              className="hidden h-9 items-center rounded-md bg-primary px-4 text-sm font-semibold text-primary-foreground shadow-btn-primary transition-all duration-200 hover:-translate-y-px hover:bg-primary-hover hover:shadow-btn-primary-hover md:inline-flex"
            >
              무료로 시작하기
            </Link>
            <button
              type="button"
              aria-label="메뉴 열기"
              aria-expanded={menuOpen}
              aria-controls="landing-mobile-menu"
              className="inline-flex size-11 items-center justify-center rounded-md text-[color:var(--text-primary)] transition-colors hover:bg-[color:var(--bg-alt)] md:hidden"
              onClick={() => setMenuOpen(true)}
            >
              <Menu className="size-5" aria-hidden="true" />
            </button>
          </div>
        </div>
      </nav>

      {menuOpen && (
        <div
          id="landing-mobile-menu"
          role="dialog"
          aria-modal="true"
          aria-label="모바일 메뉴"
          className="fixed inset-0 z-50 bg-black/40 md:hidden"
          onClick={(e) => {
            if (e.target === e.currentTarget) setMenuOpen(false);
          }}
        >
          <div className="ml-auto flex h-full w-[80%] max-w-[320px] flex-col gap-1 bg-card p-6 shadow-2xl">
            <div className="mb-4 flex items-center justify-between">
              <ThemeToggle />
              <button
                type="button"
                aria-label="메뉴 닫기"
                className="inline-flex size-11 items-center justify-center rounded-md text-[color:var(--text-primary)] transition-colors hover:bg-[color:var(--bg-alt)]"
                onClick={() => setMenuOpen(false)}
              >
                <X className="size-5" aria-hidden="true" />
              </button>
            </div>
            {NAV_ANCHORS.map((a) => (
              <a
                key={a.href}
                href={a.href}
                onClick={() => setMenuOpen(false)}
                className="rounded-md px-3 py-3 text-base font-medium text-[color:var(--text-primary)] hover:bg-[color:var(--bg-alt)]"
              >
                {a.label}
              </a>
            ))}
            <Link
              href="/sign-in"
              onClick={() => setMenuOpen(false)}
              className="rounded-md px-3 py-3 text-base font-medium text-[color:var(--text-primary)] hover:bg-[color:var(--bg-alt)]"
            >
              로그인
            </Link>
            <Link
              href="/sign-up"
              onClick={() => setMenuOpen(false)}
              className="mt-2 rounded-md bg-primary px-4 py-3 text-center text-base font-semibold text-primary-foreground shadow-btn-primary hover:bg-primary-hover"
            >
              무료로 시작하기
            </Link>
          </div>
        </div>
      )}
    </>
  );
}

function BrandLogo() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden>
      <path d="M4 20C4 20 8 8 14 8C20 8 24 20 24 20" stroke="var(--primary)" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M2 18C2 18 7 10 14 10C21 10 26 18 26 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}
