// 랜딩 01 기능 (.lp-feat-grid) — 6장의 기능 카드. screen-14-landing.html 이식.
// 각 카드는 무엇을 하고 무엇을 하지 않는지 note 로 밝힌다(정직성).
import type { ReactNode } from "react";

interface Feature {
  icon: ReactNode;
  title: string;
  desc: string;
  note: string;
}

const FEATURES: Feature[] = [
  {
    icon: (
      <>
        <polyline points="16 18 22 12 16 6" />
        <polyline points="8 6 2 12 8 18" />
      </>
    ),
    title: "Pine Script 파싱",
    desc: "붙여 넣은 전략을 구문 트리로 읽어 어떤 함수와 입력을 쓰는지 목록으로 보여 줍니다.",
    note: "미지원 함수가 하나라도 있으면 전체를 지원되지 않음으로 처리합니다. 부분 실행은 하지 않습니다.",
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
    desc: "봉을 하나씩 순회하면서 진입과 청산, 수수료와 슬리피지를 그대로 재현합니다. 리포트에 실행 가정을 함께 인쇄합니다.",
    note: "바 단위 이벤트 루프 자체 인터프리터",
  },
  {
    icon: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" />
      </>
    ),
    title: "파라미터 최적화",
    desc: "그리드, 베이지안, 유전 세 가지 탐색으로 파라미터 조합을 훑습니다. 자동으로 정답을 골라 주지 않고 결과를 늘어놓습니다.",
    note: "그리드는 조합 최대 9개. 베이지안과 유전은 평가 최대 100회.",
  },
  {
    icon: <path d="M3 12h4l3-7 4 14 3-7h4" />,
    title: "스트레스 테스트",
    desc: "거래 순서를 뒤섞고, 구간을 잘라 다시 최적화하고, 파라미터를 흔들어 성과가 얼마나 버티는지 확인합니다.",
    note: "몬테카를로 · 워크포워드 · 파라미터 안정성",
  },
  {
    icon: (
      <>
        <rect x="4" y="3" width="16" height="18" rx="2" />
        <line x1="8" y1="8" x2="16" y2="8" />
        <line x1="8" y1="12" x2="16" y2="12" />
        <line x1="8" y1="16" x2="13" y2="16" />
      </>
    ),
    title: "데모 트레이딩",
    desc: "데모 계정에 실제 주문을 냅니다. 라이브와 같은 코드 경로를 쓰기 때문에 배선 오류가 여기서 먼저 드러납니다.",
    note: "Bybit 데모 · Bybit 메인넷",
  },
  {
    icon: (
      <>
        <path d="M12 3l7.5 3.4v5.2c0 4.4-3.1 7.9-7.5 9.4-4.4-1.5-7.5-5-7.5-9.4V6.4L12 3z" />
        <line x1="12" y1="9" x2="12" y2="13.5" />
        <line x1="12" y1="16.5" x2="12.01" y2="16.5" />
      </>
    ),
    title: "리스크 가드와 Kill Switch",
    desc: "주문 한도와 손실 한도를 넘으면 세션을 멈추고 신규 주문을 막습니다. 수동 Kill Switch 로도 즉시 중단합니다.",
    note: "한도 위반 시 세션 자동 비활성",
  },
];

export function LandingFeatures() {
  return (
    <section className="section rise d2" id="features" aria-label="기능">
      <header className="section-head">
        <p className="eyebrow">기능</p>
        <h2 className="section-title">전략 하나를 끝까지 확인하는 데 필요한 것들</h2>
        <p className="section-desc">
          여섯 가지가 한 줄기로 이어집니다. 각 기능이 무엇을 하고 무엇을 하지 않는지 카드 아래에
          적었습니다.
        </p>
      </header>

      <div className="lp-feat-grid">
        {FEATURES.map((f) => (
          <article key={f.title} className="card lp-feat">
            <span className="cta-icon" aria-hidden="true">
              <svg
                aria-hidden="true"
                viewBox="0 0 24 24"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                {f.icon}
              </svg>
            </span>
            <h3 className="lp-feat-title">{f.title}</h3>
            <p className="lp-feat-desc">{f.desc}</p>
            <p className="lp-feat-note">{f.note}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
