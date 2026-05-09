// 랜딩 페이지 "어떻게 작동하나요?" 4 step 섹션
import type { ReactNode } from "react";

interface StepItem {
  number: string;
  title: string;
  description: string;
  icon: ReactNode;
}

const STEPS: StepItem[] = [
  {
    number: "01",
    title: "전략 업로드",
    description: "Pine Script 파일을 업로드하면 자동으로 파싱 및 변환됩니다.",
    icon: (
      <>
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="17,8 12,3 7,8" />
        <line x1="12" y1="3" x2="12" y2="15" />
      </>
    ),
  },
  {
    number: "02",
    title: "백테스트 실행",
    description: "과거 데이터로 전략 성과를 빠르게 검증합니다.",
    icon: (
      <>
        <line x1="18" y1="20" x2="18" y2="10" />
        <line x1="12" y1="20" x2="12" y2="4" />
        <line x1="6" y1="20" x2="6" y2="14" />
      </>
    ),
  },
  {
    number: "03",
    title: "파라미터 최적화",
    description: "Grid·Bayesian·Genetic 알고리즘이 최적 설정을 자동 탐색합니다.",
    icon: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
      </>
    ),
  },
  {
    number: "04",
    title: "자동 매매 시작",
    description: "검증된 전략으로 데모 또는 라이브 트레이딩을 시작합니다.",
    icon: <polygon points="5,3 19,12 5,21 5,3" />,
  },
];

export function LandingHowItWorks() {
  return (
    <section
      id="how-it-works"
      className="bg-white px-6 py-20"
      aria-labelledby="how-it-works-heading"
    >
      <div className="mx-auto max-w-[1200px]">
        <div className="mb-12 text-center">
          <div
            aria-hidden
            className="mx-auto mb-4 h-[3px] w-12 rounded-sm bg-[color:var(--primary)]"
          />
          <h2
            id="how-it-works-heading"
            className="font-display text-[clamp(1.75rem,3vw,2.25rem)] font-bold text-[color:var(--text-primary)]"
          >
            어떻게 작동하나요?
          </h2>
          <p className="mx-auto mt-3 max-w-[520px] text-base text-[color:var(--text-secondary)]">
            전략 업로드부터 자동 매매까지 4단계로 끝납니다
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s, i) => (
            <article
              key={s.number}
              className="relative rounded-[14px] border border-[color:var(--border)] bg-[color:var(--bg)] p-7 shadow-[0_1px_3px_rgba(0,0,0,0.04)] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_8px_24px_rgba(0,0,0,0.06)] motion-safe:animate-[fadeInUp_500ms_ease-out_both]"
              style={{ animationDelay: `${i * 80}ms` }}
            >
              <div className="font-mono text-xs font-semibold tracking-wider text-[color:var(--primary)]">
                {s.number}
              </div>
              <div className="mt-4 flex size-11 items-center justify-center rounded-full bg-[color:var(--primary-light)]">
                <svg
                  aria-hidden
                  className="size-[22px]"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="var(--primary)"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  {s.icon}
                </svg>
              </div>
              <h3 className="mt-4 font-display text-base font-semibold text-[color:var(--text-primary)]">
                {s.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-[color:var(--text-secondary)]">
                {s.description}
              </p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
