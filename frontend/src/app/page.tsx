// 랜딩 페이지 — Stage 3 스프린트에서 프로토타입(docs/prototypes/00-landing.html) 기반으로 구현
export default function LandingPage() {
  return (
    <main className="mx-auto max-w-[1200px] px-6 py-20">
      <section className="flex flex-col gap-6">
        <span className="inline-flex w-fit items-center gap-2 rounded-full border border-[color:var(--primary-100)] bg-[color:var(--primary-light)] px-4 py-1.5 text-xs font-medium text-[color:var(--primary)]">
          QuantBridge — Stage 0 scaffold
        </span>
        <h1 className="font-display text-4xl font-extrabold tracking-tight md:text-5xl lg:text-6xl">
          Pine Script를 실전 트레이딩으로.
        </h1>
        <p className="max-w-[560px] text-base text-[color:var(--text-secondary)] md:text-lg">
          TradingView 전략을 백테스트하고, 스트레스 테스트로 강건성을 검증한 뒤 데모/라이브
          트레이딩까지 한 번에 연결하는 퀀트 플랫폼입니다.
        </p>
      </section>
    </main>
  );
}
