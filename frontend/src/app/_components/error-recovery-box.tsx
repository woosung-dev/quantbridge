// 404/500 에러 페이지 복구 카드 — prototype 11 의 helpful grid(404) / tech-info(500) 2 variant.
// (503 maintenance 카드는 S9 에서 삭제. 타입은 NotFoundProps | ServerErrorProps 두 가지뿐.)

"use client";

import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

interface HelpfulItem {
  href: string;
  title: string;
  path: string;
  icon: React.ReactNode;
}

interface NotFoundProps {
  variant: "404";
  items?: HelpfulItem[];
}

interface ServerErrorProps {
  variant: "500";
  requestId?: string;
  errorCode?: string;
  occurredAt?: string;
  helpHref?: string;
}

type ErrorRecoveryBoxProps = NotFoundProps | ServerErrorProps;

const DEFAULT_HELPFUL: HelpfulItem[] = [
  {
    href: "/strategies",
    title: "내 전략 보기",
    path: "/strategies",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
        <polyline points="16 18 22 12 16 6" />
        <polyline points="8 6 2 12 8 18" />
      </svg>
    ),
  },
  {
    href: "/backtests",
    title: "백테스트 결과",
    path: "/backtests",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
        <line x1="12" y1="20" x2="12" y2="10" />
        <line x1="18" y1="20" x2="18" y2="4" />
        <line x1="6" y1="20" x2="6" y2="16" />
      </svg>
    ),
  },
  {
    href: "/dashboard",
    title: "대시보드",
    path: "/dashboard",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
        <rect x="3" y="3" width="7" height="7" />
        <rect x="14" y="3" width="7" height="7" />
        <rect x="3" y="14" width="7" height="7" />
        <rect x="14" y="14" width="7" height="7" />
      </svg>
    ),
  },
];

/**
 * 에러 페이지 복구 카드 — variant 별 prototype 11 1:1.
 *
 * - 404: 추천 카드 grid + 검색 input (검색 form 은 dummy, blur 시 noop)
 * - 500: tech-info-box (요청ID + 복사 + sonner toast + 시각)
 *
 * (503 maintenance 카드는 프로덕션 소비자가 없어 S9 에서 삭제. 점검 페이지는
 *  app/maintenance/page.tsx 가 ErrorIllustration 만으로 자체 레이아웃을 그린다.)
 *
 * clipboard 미지원 / 실패 시 sonner toast.error fallback.
 */
export function ErrorRecoveryBox(props: ErrorRecoveryBoxProps) {
  if (props.variant === "404") {
    const items = props.items ?? DEFAULT_HELPFUL;
    return (
      <div data-testid="error-recovery-box" data-variant="404" className="relative z-[2] w-full">
        <section aria-labelledby="suggest-title" className="mt-12">
          <h2
            id="suggest-title"
            className="mb-3 text-center font-display text-sm font-semibold text-[color:var(--text-secondary)]"
          >
            찾으시는 페이지가 있으신가요?
          </h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {items.map((item, idx) => (
              <Link
                key={item.href}
                href={item.href}
                style={{ animationDelay: `${idx * 60}ms` }}
                className="group flex flex-col gap-2 rounded-[10px] border border-[color:var(--border)] bg-card p-3.5 text-left transition-all duration-200 ease-out hover:-translate-y-0.5 hover:border-[color:var(--primary)] hover:shadow-md motion-safe:animate-[staggerIn_280ms_ease-out_both]"
              >
                <span className="grid h-8 w-8 place-items-center rounded-lg bg-[color:var(--primary-light)] text-[color:var(--primary)] transition-colors duration-200 group-hover:bg-[color:var(--primary)] group-hover:text-[color:var(--primary-foreground)]">
                  {item.icon}
                </span>
                <span className="text-[13px] font-semibold text-[color:var(--text-primary)]">{item.title}</span>
                <span className="font-mono text-[11px] text-[color:var(--text-muted)]">{item.path}</span>
              </Link>
            ))}
          </div>
        </section>

        <section className="mt-9">
          <label
            id="search-title"
            htmlFor="err-search-input"
            className="mb-2.5 block text-center text-[13px] font-medium text-[color:var(--text-secondary)]"
          >
            원하는 기능을 검색하세요
          </label>
          <div className="relative mx-auto max-w-[480px]">
            <span
              aria-hidden="true"
              className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[color:var(--text-muted)]"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
            </span>
            <input
              id="err-search-input"
              type="search"
              placeholder="예: 백테스트, Pine Script 변환, 최적화..."
              autoComplete="off"
              className="h-12 w-full rounded-xl border border-[color:var(--border)] bg-card pl-11 pr-4 font-body text-sm shadow-sm transition-all focus:border-[color:var(--primary)] focus:outline-none focus:ring-[3px] focus:ring-[color:var(--primary)]/12"
            />
          </div>
          <p className="mt-3.5 text-center text-xs text-[color:var(--text-muted)]">
            자주 찾는 페이지:
            <Link href="/strategies/new" className="mx-0.5 font-medium text-[color:var(--text-secondary)] hover:text-[color:var(--primary)]">
              {" "}전략 만들기{" "}
            </Link>
            <span className="mx-1 text-[color:var(--border-dark)]">·</span>
            <Link href="/backtests/new" className="mx-0.5 font-medium text-[color:var(--text-secondary)] hover:text-[color:var(--primary)]">
              백테스트
            </Link>
            <span className="mx-1 text-[color:var(--border-dark)]">·</span>
            <Link href="/dashboard" className="mx-0.5 font-medium text-[color:var(--text-secondary)] hover:text-[color:var(--primary)]">
              대시보드
            </Link>
          </p>
        </section>
      </div>
    );
  }

  return <ServerErrorCard {...props} />;
}

function ServerErrorCard({ requestId, errorCode, occurredAt }: ServerErrorProps) {
  const code = errorCode ?? "500 Internal Server Error";
  const reqId = requestId ?? "";
  const when = occurredAt ?? "";
  // 복사 후 1.6초 동안 check icon stagger 노출 (sonner toast 와 함께 시각적 피드백 강화).
  const [hasCopied, setHasCopied] = useState(false);

  const handleCopy = async () => {
    if (!reqId) return;
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard) {
        await navigator.clipboard.writeText(reqId);
        toast.success("요청 ID가 복사되었습니다", { description: reqId });
        setHasCopied(true);
        window.setTimeout(() => setHasCopied(false), 1600);
        return;
      }
      throw new Error("clipboard unavailable");
    } catch {
      toast.error("자동 복사를 못 했습니다", { description: reqId });
    }
  };

  return (
    <div
      data-testid="error-recovery-box"
      data-variant="500"
      role="group"
      aria-label="에러 기술 정보"
      className="relative z-[2] mx-auto my-8 max-w-[480px] rounded-[10px] border border-[color:var(--destructive)]/20 bg-[color:var(--destructive-light)] p-4 text-left"
    >
      <div className="flex items-center justify-between gap-3 py-1.5 text-[13px]">
        <span className="flex items-center gap-2 font-semibold text-[color:var(--destructive)]">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          오류 코드
        </span>
        <span className="font-mono text-xs text-[color:var(--destructive)]">{code}</span>
      </div>
      {reqId ? (
        <div className="flex items-center justify-between gap-3 border-t border-[color:var(--destructive)]/15 py-1.5 text-[13px]">
          <span className="font-semibold text-[color:var(--destructive)]">요청 ID</span>
          <span className="flex items-center gap-1.5 font-mono text-xs text-[color:var(--destructive)]">
            <span data-testid="error-recovery-request-id">{reqId}</span>
            <button
              type="button"
              aria-label={hasCopied ? "요청 ID 복사 완료" : "요청 ID 복사"}
              onClick={handleCopy}
              data-copied={hasCopied || undefined}
              className="grid h-[26px] w-[26px] place-items-center rounded-md bg-[color:var(--destructive)]/10 text-[color:var(--destructive)] transition-all duration-200 hover:bg-[color:var(--destructive)]/20 data-[copied]:bg-[color:var(--success-light)] data-[copied]:text-[color:var(--success)]"
            >
              {hasCopied ? (
                <svg
                  key="copied"
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  aria-hidden="true"
                  className="motion-safe:animate-[copySuccess_280ms_cubic-bezier(0.34,1.56,0.64,1)_both]"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              ) : (
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                </svg>
              )}
            </button>
          </span>
        </div>
      ) : null}
      {when ? (
        <div className="flex items-center justify-between gap-3 border-t border-[color:var(--destructive)]/15 py-1.5 text-[13px]">
          <span className="font-semibold text-[color:var(--destructive)]">발생 시각</span>
          <span className="font-mono text-xs text-[color:var(--destructive)]">{when}</span>
        </div>
      ) : null}
      <p className="mt-2.5 border-t border-[color:var(--destructive)]/15 pt-2.5 text-center text-[11px] font-medium text-[color:var(--destructive)]">
        이 정보를 고객센터에 알려주세요
      </p>
    </div>
  );
}

