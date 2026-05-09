// 랜딩 FAQ — <details> 네이티브 토글 (JS 무필요, accessibility 우수)
interface FaqItem {
  question: string;
  answer: string;
}

const FAQ: FaqItem[] = [
  {
    question: "QuantBridge는 어떤 거래소를 지원하나요?",
    answer:
      "CCXT 라이브러리를 기반으로 Binance, Bybit, OKX, Upbit, Bithumb, Coinbase 등 100개 이상의 글로벌 거래소를 지원합니다. 지원 거래소는 계속 추가되고 있습니다.",
  },
  {
    question: "Pine Script 외에 다른 언어도 지원하나요?",
    answer:
      "현재는 TradingView Pine Script를 주력으로 지원합니다. Python 전략 직접 작성 기능은 Pro 플랜에서 지원되며, 추후 MetaTrader MQL 지원도 예정되어 있습니다.",
  },
  {
    question: "백테스트 데이터는 얼마나 제공되나요?",
    answer:
      "Starter 플랜은 최근 1년, Pro 플랜은 최대 10년간의 OHLCV 데이터를 제공합니다. 1분봉부터 일봉까지 다양한 타임프레임을 지원합니다.",
  },
  {
    question: "라이브 트레이딩의 최소 자본금은?",
    answer:
      "플랫폼 자체의 최소 자본금 제한은 없습니다. 각 거래소의 최소 주문 금액만 충족하면 됩니다. 데모 트레이딩으로 먼저 검증하시는 것을 권장합니다.",
  },
  {
    question: "API Key 보안은 어떻게 보장되나요?",
    answer:
      "모든 API Key는 AES-256 암호화로 저장됩니다. 출금 권한이 없는 키만 등록 가능하며, 모든 접근은 감사 로그로 기록됩니다. SOC 2 Type II 인증을 준비 중입니다.",
  },
  {
    question: "환불 정책은 어떻게 되나요?",
    answer:
      "Pro 플랜은 결제 후 14일 이내 전액 환불이 가능합니다. 연간 결제의 경우 사용 기간에 비례하여 환불됩니다.",
  },
];

export function LandingFaq() {
  return (
    <section
      id="faq"
      className="bg-[color:var(--bg)] px-6 py-20"
      aria-labelledby="faq-heading"
    >
      <div className="mx-auto max-w-[800px]">
        <div className="mb-12 text-center">
          <div
            aria-hidden
            className="mx-auto mb-4 h-[3px] w-12 rounded-sm bg-[color:var(--primary)]"
          />
          <h2
            id="faq-heading"
            className="font-display text-[clamp(1.75rem,3vw,2.25rem)] font-bold text-[color:var(--text-primary)]"
          >
            자주 묻는 질문
          </h2>
        </div>

        <div className="flex flex-col gap-3">
          {FAQ.map((item) => (
            <details
              key={item.question}
              className="group rounded-[12px] border border-[color:var(--border)] bg-white open:shadow-[0_4px_14px_rgba(0,0,0,0.05)]"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-4 text-base font-semibold text-[color:var(--text-primary)]">
                <span>{item.question}</span>
                <svg
                  aria-hidden
                  className="size-5 shrink-0 text-[color:var(--text-muted)] transition-transform duration-200 group-open:rotate-180"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <polyline points="6,9 12,15 18,9" />
                </svg>
              </summary>
              <div className="border-t border-[color:var(--border)] px-5 py-4 text-sm leading-relaxed text-[color:var(--text-secondary)]">
                {item.answer}
              </div>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
