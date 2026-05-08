// Sprint 43 W13 — /waitlist FAQ accordion (native details/summary, 외부 첫인상 신뢰도 보강)
// design source: ui-ux-pro-max master "FAQ accordion" + DESIGN.md border/text 토큰

interface FaqItem {
  question: string;
  answer: string;
}

const FAQ_ITEMS: FaqItem[] = [
  {
    question: "Beta 는 무료인가요?",
    answer:
      "네, Beta 기간 동안 모든 기능 무료입니다. 정식 출시 시 가격 정책을 별도 안내드립니다. Beta 참여자는 평생 할인 혜택이 적용됩니다.",
  },
  {
    question: "TradingView Pro+ 가 꼭 필요한가요?",
    answer:
      "Pro+ 이상이어야 webhook 알림을 외부로 발송할 수 있습니다. 무료 플랜은 알림이 화면에만 뜨므로 자동매매가 불가능합니다.",
  },
  {
    question: "어떤 거래소를 지원하나요?",
    answer:
      "현재 Bybit (Demo + Mainnet) 와 OKX (Demo) 를 지원합니다. Binance, Bitget 은 H2 로드맵에 포함되어 있습니다.",
  },
  {
    question: "초대장은 언제 받을 수 있나요?",
    answer:
      "신청 후 1-2 주 안에 회신 드립니다. 매주 5-10 명씩만 초대하기 때문에 안정화 단계가 끝나면 cohort 가 확대됩니다.",
  },
  {
    question: "Demo 환경에서 진짜 돈을 잃지 않나요?",
    answer:
      "Bybit Demo Trading 환경은 가상 자금으로 작동합니다. 실거래(Mainnet) 전환은 사용자가 직접 키를 등록하고 명시적으로 활성화해야만 가능합니다.",
  },
];

export function WaitlistFaq() {
  return (
    <section
      aria-labelledby="waitlist-faq-heading"
      className="space-y-4"
    >
      <h2
        id="waitlist-faq-heading"
        className="font-display text-xl font-bold tracking-tight text-[color:var(--text-primary)]"
      >
        자주 묻는 질문
      </h2>
      <div className="space-y-2">
        {FAQ_ITEMS.map((item) => (
          <details
            key={item.question}
            className="group rounded-md border border-[color:var(--border)] bg-white px-4 py-3 transition-colors duration-200 ease-out hover:border-[color:var(--accent-amber)]/40"
          >
            <summary className="flex cursor-pointer items-center justify-between gap-4 text-sm font-semibold text-[color:var(--text-primary)] [&::-webkit-details-marker]:hidden">
              <span>{item.question}</span>
              <span
                aria-hidden="true"
                className="flex h-5 w-5 flex-none items-center justify-center rounded-full bg-[color:var(--accent-amber-light)] text-xs font-bold text-[color:var(--accent-amber)] transition-transform duration-[250ms] ease-[cubic-bezier(0.4,0,0.2,1)] group-open:rotate-45"
              >
                +
              </span>
            </summary>
            <p className="mt-3 text-sm leading-relaxed text-[color:var(--text-secondary)] motion-safe:group-open:animate-[accordionSlide_250ms_ease-out_both]">
              {item.answer}
            </p>
          </details>
        ))}
      </div>
    </section>
  );
}
