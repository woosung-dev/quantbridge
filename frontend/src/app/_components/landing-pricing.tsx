// 랜딩 요금제 — Starter (무료) / Pro ($49/월 인기) / Enterprise (문의) 3 plan
import Link from "next/link";

interface PricingPlan {
  name: string;
  price: string;
  priceSuffix?: string;
  description: string;
  features: string[];
  cta: { label: string; href?: string; disabled?: boolean };
  highlighted?: boolean;
}

const PLANS: PricingPlan[] = [
  {
    name: "Starter",
    price: "무료",
    description: "개인 트레이더를 위한 시작점",
    features: [
      "전략 3개",
      "기본 백테스트",
      "1년 데이터",
      "데모 트레이딩",
      "커뮤니티 지원",
      "기본 지표",
      "이메일 알림",
      "API 접근",
    ],
    cta: { label: "무료로 시작", href: "/sign-up" },
  },
  {
    name: "Pro",
    price: "$49",
    priceSuffix: "/월",
    description: "진지한 퀀트 트레이더를 위한 풀 패키지",
    features: [
      "무제한 전략",
      "고급 백테스트",
      "10년 데이터",
      "스트레스 테스트",
      "파라미터 최적화",
      "라이브 트레이딩",
      "우선 지원",
      "고급 API",
      "Webhook 알림",
      "멀티 거래소",
    ],
    cta: { label: "출시 예정", disabled: true },
    highlighted: true,
  },
  {
    name: "Enterprise",
    price: "문의",
    description: "기관 및 팀을 위한 맞춤 솔루션",
    features: [
      "전용 인프라",
      "커스텀 API",
      "전담 매니저",
      "SLA 보장",
      "SSO 인증",
      "감사 로그",
      "온프레미스 옵션",
      "교육 지원",
    ],
    cta: { label: "출시 예정", disabled: true },
  },
];

export function LandingPricing() {
  return (
    <section
      id="pricing"
      className="bg-white px-6 py-20"
      aria-labelledby="pricing-heading"
    >
      <div className="mx-auto max-w-[1200px]">
        <div className="mb-12 text-center">
          <div
            aria-hidden
            className="mx-auto mb-4 h-[3px] w-12 rounded-sm bg-[color:var(--primary)]"
          />
          <h2
            id="pricing-heading"
            className="font-display text-[clamp(1.75rem,3vw,2.25rem)] font-bold text-[color:var(--text-primary)]"
          >
            심플한 요금제
          </h2>
          <p className="mx-auto mt-3 max-w-[520px] text-base text-[color:var(--text-secondary)]">
            언제든 변경하거나 취소할 수 있습니다
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-3 md:items-stretch">
          {PLANS.map((plan) => {
            const isHi = plan.highlighted === true;
            return (
              <article
                key={plan.name}
                className={`relative flex flex-col rounded-[14px] border p-7 transition-all duration-200 ${
                  isHi
                    ? "border-[color:var(--primary)] bg-white shadow-[0_8px_30px_rgba(37,99,235,0.18)] md:scale-[1.03]"
                    : "border-[color:var(--border)] bg-white shadow-[0_1px_3px_rgba(0,0,0,0.04)] hover:-translate-y-0.5 hover:shadow-[0_8px_24px_rgba(0,0,0,0.06)]"
                }`}
              >
                {isHi && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-[color:var(--primary)] px-3 py-1 text-xs font-semibold text-white shadow-[0_2px_8px_rgba(37,99,235,0.4)]">
                    인기
                  </span>
                )}

                <h3 className="font-display text-lg font-bold text-[color:var(--text-primary)]">
                  {plan.name}
                </h3>
                <div className="mt-3 flex items-baseline gap-1">
                  <span className="font-mono text-4xl font-extrabold text-[color:var(--text-primary)]">
                    {plan.price}
                  </span>
                  {plan.priceSuffix && (
                    <span className="text-sm text-[color:var(--text-muted)]">
                      {plan.priceSuffix}
                    </span>
                  )}
                </div>
                <p className="mt-2 text-sm text-[color:var(--text-secondary)]">
                  {plan.description}
                </p>

                <ul className="mt-6 flex flex-1 flex-col gap-2.5">
                  {plan.features.map((f) => (
                    <li
                      key={f}
                      className="flex items-start gap-2 text-sm text-[color:var(--text-secondary)]"
                    >
                      <svg
                        aria-hidden
                        className="mt-0.5 size-4 shrink-0 text-[color:var(--primary)]"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <polyline points="20,6 9,17 4,12" />
                      </svg>
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>

                {plan.cta.disabled === true || plan.cta.href === undefined ? (
                  <span
                    aria-disabled="true"
                    className="mt-7 inline-flex h-11 cursor-not-allowed items-center justify-center rounded-md border border-dashed border-[color:var(--border)] bg-[color:var(--bg-alt)] px-5 text-sm font-medium text-[color:var(--text-muted)]"
                  >
                    {plan.cta.label}
                  </span>
                ) : (
                  <Link
                    href={plan.cta.href}
                    className={`mt-7 inline-flex h-11 items-center justify-center rounded-md px-5 text-sm font-semibold transition-all duration-200 ${
                      isHi
                        ? "bg-[color:var(--primary)] text-white shadow-[0_4px_14px_rgba(37,99,235,0.25)] hover:-translate-y-px hover:bg-[color:var(--primary-hover)]"
                        : "border border-[color:var(--border)] bg-white text-[color:var(--text-primary)] hover:border-[color:var(--primary)] hover:text-[color:var(--primary)]"
                    }`}
                  >
                    {plan.cta.label}
                  </Link>
                )}
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
