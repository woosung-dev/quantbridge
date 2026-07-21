// 503 점검 페이지 — ErrorIllustration(503) + 안내 문구 + 홈 복귀 링크.
// (프로토타입 11 의 ETA·진행 바·업데이트 목록은 실데이터가 없어 S9 에서 제거했다.)

import Link from "next/link";

import { ErrorIllustration } from "@/app/_components/error-illustration";

export default function MaintenancePage() {
  return (
    <section
      aria-labelledby="err-503-heading"
      className="relative flex min-h-[calc(100vh-60px)] flex-col items-center justify-center overflow-hidden px-6 py-14 sm:py-20"
    >
      <ErrorIllustration variant="503" />

      <div className="relative z-[2] w-full max-w-[560px] text-center">
        <h1
          id="err-503-heading"
          className="mb-3.5 font-display text-2xl font-bold tracking-tight text-[color:var(--text-primary)] sm:text-[2rem]"
        >
          서비스 점검 중입니다
        </h1>
        <p className="mx-auto mb-8 max-w-[480px] whitespace-pre-line text-base leading-relaxed text-[color:var(--text-secondary)]">
          {`더 나은 서비스 제공을 위해 시스템을 업데이트하고 있습니다.\n잠시 후 다시 이용해주세요.`}
        </p>

        <div role="group" aria-label="복구 동작" className="relative z-[2] flex flex-wrap justify-center gap-3">
          <Link
            href="/"
            className="inline-flex items-center gap-2 whitespace-nowrap rounded-[10px] bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow-btn-primary transition-all hover:-translate-y-px hover:bg-primary-hover"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M3 12l9-9 9 9" />
              <path d="M5 10v10h14V10" />
            </svg>
            홈으로
          </Link>
        </div>
      </div>
    </section>
  );
}
