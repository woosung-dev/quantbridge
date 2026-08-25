// 웨이트리스트 02 제품 (.feat-row) — 지금 로컬에서 도는 범위 4장. screen-17-waitlist.html 이식.
import type { ReactNode } from "react";

interface ProductCard {
  icon: ReactNode;
  title: string;
  desc: string;
  points: string[];
}

const CARDS: ProductCard[] = [
  {
    icon: (
      <>
        <polyline points="16 18 22 12 16 6" />
        <polyline points="8 6 2 12 8 18" />
      </>
    ),
    title: "Pine Script 파싱",
    desc: "TradingView 전략 소스를 읽어 지원 여부를 판정합니다.",
    points: [
      "지원하지 않는 함수가 하나라도 있으면 전체를 미지원으로 판정합니다.",
      "부분 실행은 하지 않습니다. 절반만 맞는 결과를 내지 않기 위해서입니다.",
    ],
  },
  {
    icon: (
      <>
        <line x1="6" y1="20" x2="6" y2="14" />
        <line x1="12" y1="20" x2="12" y2="4" />
        <line x1="18" y1="20" x2="18" y2="10" />
      </>
    ),
    title: "백테스트",
    desc: "바 단위 이벤트 루프 자체 인터프리터가 봉을 하나씩 지나가며 주문을 체결합니다.",
    points: [
      "체결 가정, 수수료, 슬리피지를 리포트에 함께 인쇄합니다.",
      "매수후보유 대비 초과분을 같은 화면에서 비교합니다.",
    ],
  },
  {
    icon: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" />
      </>
    ),
    title: "파라미터 탐색과 스트레스 테스트",
    desc: "그리드, 베이지안, 유전 알고리즘 세 방식으로 파라미터를 훑습니다.",
    points: [
      "몬테카를로와 워크포워드로 결과가 우연인지 확인합니다.",
      "구간을 나눠 재최적화하는 방식이라 학습 구간 성적을 성과로 쓰지 않습니다.",
    ],
  },
  {
    icon: <path d="M3 12h4l3-7 4 14 3-7h4" />,
    title: "거래소 연결",
    desc: "검증한 전략을 같은 코드 경로로 Bybit 데모 계정에 붙입니다.",
    points: [
      "API 키는 암호화해 저장하고 화면에 다시 표시하지 않습니다.",
      "주문을 한 번에 멈추는 킬 스위치를 세션마다 둡니다.",
    ],
  },
];

export function WaitlistProduct() {
  return (
    <section className="section rise d2" id="build" aria-label="무엇을 만들고 있나">
      <div className="section-head">
        <p className="eyebrow">
          <span className="num">01</span> 제품
        </p>
        <h2 className="section-title">무엇을 만들고 있나.</h2>
        <p className="section-desc">지금 로컬에서 실제로 돌아가는 범위만 적습니다.</p>
      </div>

      <div className="feat-row">
        {CARDS.map((c) => (
          <article key={c.title} className="card cta">
            <span className="cta-icon" aria-hidden="true">
              <svg
                aria-hidden="true"
                viewBox="0 0 24 24"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                {c.icon}
              </svg>
            </span>
            <h3 className="cta-title">{c.title}</h3>
            <p className="cta-desc">{c.desc}</p>
            <ul className="feat-list">
              {c.points.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          </article>
        ))}
      </div>
    </section>
  );
}
