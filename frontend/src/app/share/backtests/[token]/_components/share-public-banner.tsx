// 공유 링크 상단 안내 banner — 외부 방문자에게 read-only 컨텍스트 + signup CTA 노출
import Link from "next/link";

/**
 * 외부 공유 링크 (`/share/backtests/[token]`) 상단에 고정되는 안내 banner.
 *
 * - 좌측: "공유 링크 · 읽기 전용" 라벨 + 이 페이지가 누군가의 백테스트 결과 1개를 보여줄 뿐임을 명시
 * - 우측: signup CTA (`/sign-up`) — 가입 시 본인 백테스트를 만들 수 있다는 다음 액션 유도
 * - aria-live=polite + role=region 으로 외부 viewer 가 banner 존재를 인지하도록 함
 *
 * 토큰: --primary-light / --primary / --border / --muted-foreground (light theme 만 사용).
 */
export function SharePublicBanner() {
  return (
    <div
      role="region"
      aria-live="polite"
      aria-label="공유 링크 안내"
      data-testid="share-public-banner"
      className="border-b border-[color:var(--border)] bg-[color:var(--primary-light)]"
    >
      <div className="mx-auto flex max-w-3xl flex-col items-start gap-3 px-6 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-2 sm:items-center">
          <span
            aria-hidden="true"
            className="mt-0.5 inline-flex h-5 items-center rounded-full bg-[color:var(--primary)] px-2 text-[10px] font-semibold uppercase tracking-wider text-[color:var(--primary-foreground)] sm:mt-0"
          >
            공유 링크
          </span>
          <p className="text-sm text-[color:var(--card-foreground)]">
            <span className="font-medium">읽기 전용 백테스트 결과입니다.</span>
            <span className="ml-1 text-[color:var(--muted-foreground)]">
              가입하면 본인 전략으로 백테스트를 만들 수 있습니다.
            </span>
          </p>
        </div>
        <Link
          href="/sign-up"
          className="inline-flex h-8 shrink-0 items-center rounded-md bg-[color:var(--primary)] px-3 text-xs font-medium text-[color:var(--primary-foreground)] shadow-sm transition hover:bg-[color:var(--primary-hover)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--primary)]"
        >
          QuantBridge 시작하기
        </Link>
      </div>
    </div>
  );
}
