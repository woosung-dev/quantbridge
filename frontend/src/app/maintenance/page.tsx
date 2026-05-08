// 503 점검 페이지 — prototype 11 의 503 layout (ETA + 진행 바 + 업데이트 목록) 1:1 visual fidelity

import Link from "next/link";

import { ErrorIllustration } from "@/app/_components/error-illustration";
import { ErrorRecoveryBox } from "@/app/_components/error-recovery-box";

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

        <ErrorRecoveryBox
          variant="503"
          etaLabel="약 15분 남음"
          startedAt="14:10 KST"
          finishesAt="14:40 KST"
          progressPercent={60}
          updates={[
            { status: "done", label: "백테스트 엔진 성능 개선 (vectorbt v0.27)" },
            { status: "done", label: "실시간 차트 최적화" },
            { status: "progress", label: "데이터베이스 정리 중" },
          ]}
        />

        <div role="group" aria-label="복구 동작" className="relative z-[2] flex flex-wrap justify-center gap-3">
          <Link
            href="/"
            className="inline-flex items-center gap-2 whitespace-nowrap rounded-[10px] bg-[color:var(--primary)] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_8px_20px_rgba(37,99,235,0.28)] transition-all hover:-translate-y-px hover:bg-[color:var(--primary-hover)]"
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
