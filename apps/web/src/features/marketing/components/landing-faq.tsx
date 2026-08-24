// 랜딩 05 FAQ (.lp-faq) — <details> 네이티브 토글. screen-14-landing.html 이식.
// 답을 모르는 항목은 모른다고 적는다(정직성).
import { ROADMAP_DISCLAIMER } from "@/lib/marketing-canon";

interface FaqItem {
  question: string;
  paragraphs: string[];
  open?: boolean;
}

const FAQ_ITEMS: FaqItem[] = [
  {
    question: "어떤 거래소를 지원하나요?",
    open: true,
    paragraphs: [
      "지금 연결되는 거래소는 Bybit 하나뿐이며 데모 환경만 제공합니다.",
      ROADMAP_DISCLAIMER,
      "거래소 연결은 CCXT 를 씁니다. 라이브러리가 지원한다고 해서 이 도구가 지원하는 것은 아니라서, 주문이 실제로 오간 것만 지원으로 적습니다.",
    ],
  },
  {
    question: "Pine Script 는 어디까지 지원하나요?",
    paragraphs: [
      "지원 함수 목록은 파싱 결과 화면에서 그때그때 보여 줍니다. 미지원 함수가 하나라도 들어 있으면 전체를 지원되지 않음으로 처리하고 실행하지 않습니다.",
      "일부만 실행해서 그럴듯한 숫자를 내놓는 쪽이 더 위험하다고 봤습니다. TradingView 와 결과가 다르면 그것부터 고칩니다.",
    ],
  },
  {
    question: "데이터는 어디서 오고 범위는 어디까지인가요?",
    paragraphs: [
      "거래소가 공개하는 OHLCV 를 받아 시계열 DB 에 저장해 두고 씁니다. 미리 수집해 둔 심볼과 기간 안에서만 조회됩니다.",
      "이 페이지에 인용한 대표 실행은 BTC/USDT 1h, 2024-01-01 부터 2026-04-14 까지 20,064봉입니다.",
    ],
  },
  {
    question: "실거래 리스크는 어떻게 보나요?",
    paragraphs: [
      "자동매매는 손실을 낼 수 있고, 과거 성과는 미래 수익을 보장하지 않습니다. 백테스트가 좋았다는 사실은 앞으로도 좋을 것이라는 근거가 되지 않습니다.",
      "그래서 데모 실행을 먼저 거치도록 순서를 잡았고, 손실 한도와 Kill Switch 를 기본으로 둡니다. 투자 판단과 그 결과는 사용하는 사람 몫입니다.",
    ],
  },
  {
    question: "지금 쓸 수 있나요?",
    paragraphs: [
      "아직 공개 서비스가 아닙니다. 가입도 요금제도 없고, 만든 사람이 로컬에서 혼자 씁니다.",
      "이 페이지는 언젠가 공개할 때 쓸 초안이라, 없는 실적을 적지 않고 지금 사실만 적어 뒀습니다.",
    ],
  },
];

export function LandingFaq() {
  return (
    <section className="section rise d6" id="faq" aria-label="자주 묻는 질문">
      <header className="section-head">
        <p className="eyebrow">FAQ</p>
        <h2 className="section-title">먼저 물어볼 만한 것들</h2>
        <p className="section-desc">답을 모르는 항목은 모른다고 적었습니다.</p>
      </header>

      <div className="lp-faq">
        {FAQ_ITEMS.map((item) => (
          <details key={item.question} className="lp-faq-item" open={item.open}>
            <summary>
              {item.question}
              <span className="lp-faq-sign" aria-hidden="true">
                +
              </span>
            </summary>
            <div className="lp-faq-a">
              {item.paragraphs.map((p) => (
                <p key={p}>{p}</p>
              ))}
            </div>
          </details>
        ))}
      </div>
    </section>
  );
}
