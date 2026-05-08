// 법무 4 페이지 (privacy / terms / disclaimer / not-available) 공통 layout shell — Sprint 43 W14.

import Link from "next/link";
import type { ReactNode } from "react";

interface LegalPageShellProps {
  /** 페이지 H1 제목 (영문/한글 병기). */
  title: string;
  /** breadcrumb 표시용 짧은 라벨 (예: "Privacy"). 없으면 breadcrumb 생략. */
  breadcrumbLabel?: string;
  /** 우상단 배지 라벨 (예: "Beta 임시본"). 없으면 생략. */
  badgeLabel?: string;
  /** 본문 자유 ReactNode (callout · section · footer 등). */
  children: ReactNode;
  /** 푸터 미세 텍스트 (예: "최종 개정: 2026-04-25 ..."). 없으면 생략. */
  footnote?: string;
  /** 중앙 정렬 + Hero 형태 (not-available 같은 짧은 페이지). 기본 false. */
  centered?: boolean;
}

/**
 * 법무 4 페이지 공통 shell.
 *
 * - max-w 720px content + px-6 py-14 (모바일 ≥ tablet 일관)
 * - breadcrumb (Home / [라벨]) — 명시 시
 * - Typography hierarchy: h1 28px / h2 22px / h3 18px / body 16px / sub 14px (children 측 소비)
 * - centered=true 면 not-available 같은 짧은 안내 페이지용 hero layout
 */
export function LegalPageShell({
  title,
  breadcrumbLabel,
  badgeLabel,
  children,
  footnote,
  centered = false,
}: LegalPageShellProps) {
  const containerLayout = centered
    ? "items-center justify-center text-center py-20"
    : "py-14";

  return (
    <main
      id="main-content"
      data-testid="legal-page-shell"
      className={`mx-auto flex min-h-[calc(100vh-4rem)] max-w-[720px] flex-col gap-6 px-6 ${containerLayout}`}
    >
      {breadcrumbLabel && !centered ? (
        <nav
          aria-label="breadcrumb"
          data-testid="legal-page-breadcrumb"
          className="text-[13px] text-[color:var(--text-muted)]"
        >
          <Link
            href="/"
            className="hover:text-[color:var(--text-secondary)] hover:underline"
          >
            Home
          </Link>
          <span className="mx-2 text-[color:var(--border-dark)]">/</span>
          <span className="text-[color:var(--text-secondary)]">{breadcrumbLabel}</span>
        </nav>
      ) : null}

      <header
        className={
          centered
            ? "flex flex-col items-center gap-3"
            : "flex flex-wrap items-center justify-between gap-3 border-b border-[color:var(--border)] pb-5"
        }
      >
        <h1
          className={
            "font-display font-extrabold tracking-[-0.02em] text-[color:var(--text-primary)] " +
            (centered
              ? "text-[28px] leading-tight md:text-[32px]"
              : "text-[28px] leading-tight")
          }
        >
          {title}
        </h1>
        {badgeLabel ? (
          <span
            data-testid="legal-page-badge"
            className="inline-flex items-center rounded-full border border-amber-500/40 bg-amber-50 px-2.5 py-1 text-[12px] font-medium text-amber-900"
          >
            {badgeLabel}
          </span>
        ) : null}
      </header>

      <div className="flex flex-col gap-6 text-[16px] leading-[1.7] text-[color:var(--text-secondary)]">
        {children}
      </div>

      {footnote ? (
        <p className="border-t border-[color:var(--border)] pt-4 text-[13px] text-[color:var(--text-muted)]">
          {footnote}
        </p>
      ) : null}
    </main>
  );
}
