// 404 not-found 페이지 — prototype 11 의 404 layout (추천 카드 + 검색) 1:1 visual fidelity

import Link from "next/link";

import { ErrorIllustration } from "@/app/_components/error-illustration";
import { ErrorRecoveryBox } from "@/app/_components/error-recovery-box";

export default function NotFound() {
  return (
    <section
      aria-labelledby="err-404-heading"
      className="relative flex min-h-[calc(100vh-60px)] flex-col items-center justify-center overflow-hidden px-6 py-14 sm:py-20"
    >
      <ErrorIllustration variant="404" />

      <div className="relative z-[2] w-full max-w-[560px] text-center">
        <h1
          id="err-404-heading"
          className="mb-3.5 font-display text-2xl font-bold tracking-tight text-[color:var(--text-primary)] sm:text-[2rem]"
        >
          페이지를 찾을 수 없습니다
        </h1>
        <p className="mx-auto mb-8 max-w-[480px] whitespace-pre-line text-base leading-relaxed text-[color:var(--text-secondary)]">
          {`URL이 변경되었거나 삭제된 페이지입니다.\n주소를 다시 확인하시거나 홈으로 이동해주세요.`}
        </p>

        <div role="group" aria-label="복구 동작" className="relative z-[2] flex flex-wrap justify-center gap-3">
          <Link
            href="/"
            className="inline-flex items-center gap-2 whitespace-nowrap rounded-[10px] bg-[color:var(--primary)] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_8px_20px_rgba(37,99,235,0.28)] transition-all hover:-translate-y-px hover:bg-[color:var(--primary-hover)]"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M3 12l9-9 9 9" />
              <path d="M5 10v10h14V10" />
            </svg>
            홈으로 돌아가기
          </Link>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 whitespace-nowrap rounded-[10px] border border-[color:var(--border-dark)] bg-white px-5 py-2.5 text-sm font-semibold text-[color:var(--text-primary)] transition-colors hover:border-[color:var(--primary)] hover:text-[color:var(--primary)]"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <rect x="3" y="3" width="7" height="7" />
              <rect x="14" y="3" width="7" height="7" />
              <rect x="3" y="14" width="7" height="7" />
              <rect x="14" y="14" width="7" height="7" />
            </svg>
            대시보드로
          </Link>
        </div>

        <ErrorRecoveryBox variant="404" />
      </div>
    </section>
  );
}
