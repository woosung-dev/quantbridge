// 랜딩 02 작동 방식 (.lp-steps) — 4단계. screen-14-landing.html 이식.
// 각 단계는 앞 단계 결과를 그대로 받는다.

interface Step {
  num: string;
  title: string;
  desc: string;
}

const STEPS: Step[] = [
  {
    num: "STEP 1",
    title: "전략 등록",
    desc: "Pine Script 를 넣으면 파싱 결과와 지원 여부를 먼저 확인합니다. 지원되지 않으면 여기서 멈춥니다.",
  },
  {
    num: "STEP 2",
    title: "백테스트",
    desc: "심볼, 기간, 수수료와 슬리피지 가정을 정해 실행합니다. 리포트에 그 가정이 함께 남습니다.",
  },
  {
    num: "STEP 3",
    title: "최적화와 OOS 검증",
    desc: "파라미터를 탐색한 뒤 구간을 나눠, 탐색에 쓰지 않은 기간으로 다시 확인합니다.",
  },
  {
    num: "STEP 4",
    title: "데모 실행",
    desc: "데모 계정에 배포해 주문과 포지션이 의도대로 도는지 지켜봅니다. 실자금은 그다음 이야기입니다.",
  },
];

export function LandingHowItWorks() {
  return (
    <section className="section rise d3" id="how" aria-label="작동 방식">
      <header className="section-head">
        <p className="eyebrow">작동 방식</p>
        <h2 className="section-title">네 단계로 진행합니다</h2>
        <p className="section-desc">
          각 단계는 앞 단계의 결과를 그대로 받습니다. 중간을 건너뛰면 다음 화면에서 무엇이 빠졌는지
          표시합니다.
        </p>
      </header>

      <div className="lp-steps">
        {STEPS.map((s) => (
          <article key={s.num} className="card lp-step">
            <span className="lp-step-num">{s.num}</span>
            <h3 className="lp-step-title">{s.title}</h3>
            <p className="lp-step-desc">{s.desc}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
