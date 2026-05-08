// 404/500/503 에러 페이지 복구 카드 — prototype 11 의 helpful grid / tech-info / ETA+updates 3 variant

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

interface UpdateItem {
  status: "done" | "progress";
  label: string;
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

interface MaintenanceProps {
  variant: "503";
  etaLabel: string; // 예: "약 15분 남음"
  startedAt: string; // 예: "14:10 KST"
  finishesAt: string; // 예: "14:40 KST"
  progressPercent: number; // 0..100
  updates: UpdateItem[];
}

type ErrorRecoveryBoxProps = NotFoundProps | ServerErrorProps | MaintenanceProps;

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
 * - 503: ETA card + 진행 바 + 업데이트 목록
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
                className="group flex flex-col gap-2 rounded-[10px] border border-[color:var(--border)] bg-white p-3.5 text-left transition-all duration-200 ease-out hover:-translate-y-0.5 hover:border-[color:var(--primary)] hover:shadow-md motion-safe:animate-[staggerIn_280ms_ease-out_both]"
              >
                <span className="grid h-8 w-8 place-items-center rounded-lg bg-[color:var(--primary-light)] text-[color:var(--primary)] transition-colors duration-200 group-hover:bg-[color:var(--primary)] group-hover:text-white">
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
              className="h-12 w-full rounded-xl border border-[color:var(--border)] bg-white pl-11 pr-4 font-body text-sm shadow-sm transition-all focus:border-[color:var(--primary)] focus:outline-none focus:ring-[3px] focus:ring-[color:var(--primary)]/12"
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

  if (props.variant === "500") {
    return <ServerErrorCard {...props} />;
  }

  return <MaintenanceCard {...props} />;
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
        <span className="font-mono text-xs text-[#7F1D1D]">{code}</span>
      </div>
      {reqId ? (
        <div className="flex items-center justify-between gap-3 border-t border-[color:var(--destructive)]/15 py-1.5 text-[13px]">
          <span className="font-semibold text-[color:var(--destructive)]">요청 ID</span>
          <span className="flex items-center gap-1.5 font-mono text-xs text-[#7F1D1D]">
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
          <span className="font-mono text-xs text-[#7F1D1D]">{when}</span>
        </div>
      ) : null}
      <p className="mt-2.5 border-t border-[color:var(--destructive)]/15 pt-2.5 text-center text-[11px] font-medium text-[#991B1B]">
        이 정보를 고객센터에 알려주세요
      </p>
    </div>
  );
}

function MaintenanceCard({ etaLabel, startedAt, finishesAt, progressPercent, updates }: MaintenanceProps) {
  const clamped = Math.min(100, Math.max(0, progressPercent));
  return (
    <div data-testid="error-recovery-box" data-variant="503" className="relative z-[2] w-full">
      <div
        role="group"
        aria-label="예상 복구 시간"
        className="mx-auto my-7 max-w-[480px] rounded-[14px] border border-[color:var(--primary-100)] bg-[color:var(--primary-light)] p-6 text-left"
      >
        <div className="mb-3.5 flex items-center gap-3">
          <span
            aria-hidden="true"
            className="grid h-10 w-10 place-items-center rounded-[10px] bg-white text-[color:var(--primary)] shadow-sm"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          </span>
          <div>
            <div className="text-[13px] font-medium text-[color:var(--text-secondary)]">예상 복구 시간</div>
            <div className="font-mono text-2xl font-bold leading-tight text-[color:var(--primary)]">{etaLabel}</div>
          </div>
        </div>
        <div
          role="progressbar"
          aria-valuenow={clamped}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`점검 진행률 ${clamped}%`}
          className="relative my-3 h-2.5 w-full overflow-hidden rounded-full bg-[color:var(--primary-100)]"
        >
          <ProgressFill percent={clamped} />
        </div>
        <p className="font-mono text-[11px] text-[color:var(--text-muted)]">
          점검 시작: {startedAt} · 예상 완료: {finishesAt}
        </p>
      </div>

      <section
        aria-labelledby="updates-title"
        className="mx-auto my-7 max-w-[480px] rounded-xl border border-[color:var(--border)] bg-white p-5 text-left"
      >
        <h2 id="updates-title" className="mb-3 font-display text-[13px] font-semibold text-[color:var(--text-primary)]">
          이번 점검 내용:
        </h2>
        <ul className="flex flex-col gap-2.5" data-testid="error-recovery-updates">
          {updates.map((u, idx) => (
            <li
              key={idx}
              style={{ animationDelay: `${idx * 70}ms` }}
              className="flex items-center gap-2.5 text-[13px] text-[color:var(--text-secondary)] motion-safe:animate-[staggerIn_280ms_ease-out_both]"
            >
              <span
                aria-label={u.status === "done" ? "완료" : "진행 중"}
                className={
                  "grid h-5 w-5 flex-shrink-0 place-items-center rounded-full text-[11px] font-bold transition-colors duration-200 " +
                  (u.status === "done"
                    ? "bg-[color:var(--success-light)] text-[color:var(--success)]"
                    : "bg-[color:var(--primary-light)] text-[color:var(--primary)] motion-safe:animate-pulse")
                }
              >
                {u.status === "done" ? "✓" : "⋯"}
              </span>
              {u.label}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function ProgressFill({ percent }: { percent: number }) {
  // shimmer overlay (motion-reduce 시 비활성)
  const [width] = useState(`${percent}%`);
  return (
    <div
      className="relative h-full overflow-hidden rounded-full bg-gradient-to-r from-[color:var(--primary)] to-[#3B82F6]"
      style={{ width }}
    >
      <div
        aria-hidden="true"
        className="absolute inset-0 motion-safe:animate-[shimmer_1.8s_linear_infinite] motion-reduce:hidden"
        style={{
          background:
            "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.45) 50%, transparent 100%)",
        }}
      />
    </div>
  );
}
