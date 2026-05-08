// 공유 링크 404 시각 안내 — W8 ErrorIllustration 패턴 차용 (검색/존재 X 모티프)
import Link from "next/link";

/**
 * 잘못된 token / 이미 삭제된 백테스트 (HTTP 404) 시 노출되는 화면.
 *
 * - 96px 원형 아이콘 wrap (돋보기 모티프) + section radial background (primary tone)
 * - 큰 backdrop 글자 ("404") — error-illustration 패턴과 일치
 * - "QuantBridge 시작하기" CTA + 홈 이동 보조 링크
 */
export function ShareNotFoundState() {
  return (
    <main className="relative mx-auto flex min-h-[80vh] max-w-md flex-col items-center justify-center overflow-hidden px-6 py-20 text-center">
      <div
        aria-hidden="true"
        data-testid="share-not-found-bg"
        className="pointer-events-none absolute inset-0 z-0 bg-[radial-gradient(ellipse_at_top,_#EFF6FF_0%,_var(--bg)_60%)]"
      />
      <div
        aria-hidden="true"
        data-testid="share-not-found-backdrop"
        className="pointer-events-none absolute left-1/2 top-1/2 z-0 select-none font-display text-[clamp(6rem,15vw,9rem)] font-extrabold leading-[0.9] tracking-tight text-[color:var(--primary-light)]"
        style={{ transform: "translate(-50%, -58%)" }}
      >
        404
      </div>
      <div
        data-testid="share-not-found-icon"
        className="relative z-[2] mb-6 grid h-24 w-24 place-items-center rounded-3xl bg-gradient-to-br from-[color:var(--primary-light)] to-[color:var(--primary-100)] shadow-lg motion-safe:animate-[errIllustEnter_360ms_cubic-bezier(0.34,1.56,0.64,1)_both]"
        aria-hidden="true"
      >
        <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
          {/* 돋보기 모티프 — 백테스트 결과 미발견 의미 */}
          <circle
            cx="24"
            cy="24"
            r="14"
            stroke="#2563EB"
            strokeWidth="2.5"
            fill="#EFF6FF"
          />
          <line
            x1="35"
            y1="35"
            x2="48"
            y2="48"
            stroke="#2563EB"
            strokeWidth="3"
            strokeLinecap="round"
          />
          <line
            x1="18"
            y1="22"
            x2="30"
            y2="22"
            stroke="#93C5FD"
            strokeWidth="2"
            strokeLinecap="round"
          />
          <line
            x1="18"
            y1="26"
            x2="26"
            y2="26"
            stroke="#93C5FD"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
      </div>
      <h1 className="relative z-[2] font-display text-2xl font-bold text-[color:var(--card-foreground)]">
        공유 링크를 찾을 수 없습니다
      </h1>
      <p className="relative z-[2] mt-2 max-w-sm text-sm text-[color:var(--muted-foreground)]">
        잘못된 링크이거나 이미 삭제된 백테스트입니다.
        <br />
        링크가 정확한지 다시 확인해 주세요.
      </p>
      <div className="relative z-[2] mt-6 flex flex-col items-center gap-2 sm:flex-row">
        <Link
          href="/sign-up"
          className="inline-flex h-9 items-center rounded-md bg-[color:var(--primary)] px-4 text-sm font-medium text-[color:var(--primary-foreground)] shadow-sm transition-all duration-200 ease-out hover:-translate-y-px hover:bg-[color:var(--primary-hover)] hover:shadow-md"
        >
          QuantBridge 시작하기
        </Link>
        <Link
          href="/"
          className="text-sm text-[color:var(--muted-foreground)] underline-offset-4 transition-colors duration-200 ease-out hover:text-[color:var(--card-foreground)] hover:underline"
        >
          홈으로 돌아가기
        </Link>
      </div>
    </main>
  );
}
