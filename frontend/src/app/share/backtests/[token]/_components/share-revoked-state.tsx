// 공유 링크 410 (revoked) 시각 안내 — W8 ErrorIllustration 패턴 차용 (link 상태 전용 SVG)
import Link from "next/link";

/**
 * 백테스트 공유 토큰이 소유자에 의해 해제(revoke)된 경우 (HTTP 410) 노출되는 화면.
 *
 * - 96px 원형 아이콘 wrap (끊어진 link 모티프) + section radial background
 * - 큰 backdrop 글자 ("LINK") — `error-illustration.tsx` 의 `clamp(6rem,15vw,9rem)` 토큰 매칭
 * - "QuantBridge 시작하기" CTA 로 가입 유도, 보조 링크로 홈 이동
 *
 * `not-found-state.tsx` 와 시각 패턴은 동일하지만 SVG icon / backdrop 단어만 다름.
 */
export function ShareRevokedState() {
  return (
    <main className="relative mx-auto flex min-h-[80vh] max-w-md flex-col items-center justify-center overflow-hidden px-6 py-20 text-center">
      {/* section radial background */}
      <div
        aria-hidden="true"
        data-testid="share-revoked-bg"
        className="pointer-events-none absolute inset-0 z-0 bg-[radial-gradient(ellipse_at_top,_#FEF2F2_0%,_var(--bg)_60%)]"
      />
      {/* backdrop 큰 글자 */}
      <div
        aria-hidden="true"
        data-testid="share-revoked-backdrop"
        className="pointer-events-none absolute left-1/2 top-1/2 z-0 select-none font-display text-[clamp(5rem,12vw,7.5rem)] font-extrabold leading-[0.9] tracking-tight text-[#FEE2E2]"
        style={{ transform: "translate(-50%, -58%)" }}
      >
        LINK
      </div>
      {/* 96px 원형 아이콘 wrap */}
      <div
        data-testid="share-revoked-icon"
        className="relative z-[2] mb-6 grid h-24 w-24 place-items-center rounded-3xl bg-gradient-to-br from-[#FEF2F2] to-[color:var(--destructive-light)] shadow-lg motion-safe:animate-[errIllustEnter_360ms_cubic-bezier(0.34,1.56,0.64,1)_both]"
        aria-hidden="true"
      >
        <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
          {/* 끊어진 사슬 모티프 */}
          <path
            d="M22 18L14 26"
            stroke="#DC2626"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
          <path
            d="M34 38L42 30"
            stroke="#DC2626"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
          <rect
            x="6"
            y="22"
            width="16"
            height="12"
            rx="6"
            stroke="#DC2626"
            strokeWidth="2.5"
            fill="#FEE2E2"
            transform="rotate(-30 14 28)"
          />
          <rect
            x="34"
            y="22"
            width="16"
            height="12"
            rx="6"
            stroke="#DC2626"
            strokeWidth="2.5"
            fill="#FEE2E2"
            transform="rotate(-30 42 28)"
          />
          {/* 끊김 표시 */}
          <line
            x1="26"
            y1="22"
            x2="30"
            y2="34"
            stroke="#DC2626"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
        </svg>
      </div>
      <h1 className="relative z-[2] font-display text-2xl font-bold text-[color:var(--card-foreground)]">
        공유 링크가 해제되었습니다
      </h1>
      <p className="relative z-[2] mt-2 max-w-sm text-sm text-[color:var(--muted-foreground)]">
        백테스트 소유자가 이 링크를 비공개로 전환했습니다.
        <br />
        새 링크가 필요하면 공유한 분께 다시 요청해 주세요.
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
