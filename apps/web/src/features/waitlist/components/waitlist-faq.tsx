// 웨이트리스트 04 FAQ (.faq-item) — 3문항 + 프로토타입 고지. screen-17-waitlist.html 이식.
// 날짜를 지어내지 않고, 집계 근거 없는 수치는 싣지 않는다(정직성).
import { ROADMAP_DISCLAIMER } from "@/lib/marketing-canon";

interface FaqItem {
  question: string;
  answer: string;
}

const FAQ_ITEMS: FaqItem[] = [
  {
    question: "언제 공개되나요?",
    answer:
      "정하지 않았습니다. 지금은 개발자 본인이 로컬에서 매일 쓰면서 고치는 단계이고, 이 단계가 끝나야 다음을 정합니다. 날짜를 지어내 적지 않겠습니다.",
  },
  {
    question: "등록하면 무엇을 받게 되나요?",
    answer:
      "공개 준비가 시작되면 그 사실을 알리는 메일 한 통을 받습니다. 뉴스레터, 할인 안내, 제휴 메일은 보내지 않습니다. 주소는 다른 곳에 넘기지 않고, 해지 요청을 받으면 지웁니다.",
  },
  {
    question: "지금 어떤 거래소에 연결할 수 있나요?",
    answer: `지금 연결되는 거래소는 Bybit 하나뿐이며 데모 환경만 제공합니다. ${ROADMAP_DISCLAIMER}`,
  },
];

export function WaitlistFaq() {
  return (
    <section className="section rise d4" id="faq" aria-label="자주 묻는 질문">
      <div className="section-head">
        <p className="eyebrow">
          <span className="num">03</span> 자주 묻는 것
        </p>
        <h2 className="section-title">먼저 답해 두는 세 가지.</h2>
        <p className="section-desc">등록 전에 알고 있어야 손해가 없는 내용입니다.</p>
      </div>

      <div className="card">
        {FAQ_ITEMS.map((item) => (
          <div key={item.question} className="faq-item">
            <h3 className="faq-q">{item.question}</h3>
            <p className="faq-a">{item.answer}</p>
          </div>
        ))}
        <div className="disclaimer">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="9" />
            <line x1="12" y1="11" x2="12" y2="16.5" />
            <line x1="12" y1="7.5" x2="12" y2="7.6" />
          </svg>
          <span>
            이 화면의 폼은 실제로 전송됩니다. 다만 사용자 수와 거래량 같은 집계 수치는 근거가 없어
            어디에도 싣지 않았습니다.
          </span>
        </div>
      </div>
    </section>
  );
}
