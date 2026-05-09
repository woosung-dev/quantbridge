// 랜딩 Bento — 4 cell 비대칭 grid (백테스트 성과 / 리스크 지표 / Pine Script / 실시간 모니터링)
const STRATEGY_BARS = [
  { label: "전략A", pct: "+24.5%", height: 75, positive: true },
  { label: "전략B", pct: "+18.2%", height: 55, positive: true },
  { label: "전략C", pct: "+12.8%", height: 40, positive: true },
  { label: "전략D", pct: "-3.4%", height: 25, positive: false },
  { label: "전략E", pct: "+21.1%", height: 65, positive: true },
] as const;

const LIVE_STRATEGIES = [
  { name: "BTC MA Cross", status: "실행 중 · +12.4%", state: "active" },
  { name: "ETH Momentum", status: "실행 중 · +8.7%", state: "active" },
  { name: "SOL RSI Reversal", status: "일시정지 · -1.2%", state: "paused" },
  { name: "AVAX Breakout", status: "실행 중 · +5.2%", state: "active" },
] as const;

export function LandingBento() {
  return (
    <section
      aria-labelledby="bento-heading"
      className="bg-[color:var(--bg)] px-6 py-20"
    >
      <div className="mx-auto max-w-[1200px]">
        <div className="mb-12 text-center">
          <div
            aria-hidden
            className="mx-auto mb-4 h-[3px] w-12 rounded-sm bg-[color:var(--primary)]"
          />
          <h2
            id="bento-heading"
            className="font-display text-[clamp(1.75rem,3vw,2.25rem)] font-bold text-[color:var(--text-primary)]"
          >
            한눈에 보는 플랫폼
          </h2>
          <p className="mx-auto mt-3 max-w-[520px] text-base text-[color:var(--text-secondary)]">
            백테스트, 리스크, 코드, 실시간 — 핵심 4개 영역을 한 번에
          </p>
        </div>

        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3 lg:grid-rows-[auto_auto]">
          {/* Cell A: 백테스트 성과 비교 (wide on lg) */}
          <article className="rounded-[14px] border border-[color:var(--border)] bg-white p-7 shadow-[0_1px_3px_rgba(0,0,0,0.04)] lg:col-span-2">
            <h3 className="font-display text-base font-semibold text-[color:var(--text-primary)]">
              백테스트 성과 비교
            </h3>
            <p className="mt-1 text-sm text-[color:var(--text-muted)]">
              5개 전략의 월간 수익률 비교
            </p>
            <div className="mt-6 flex items-end justify-between gap-3">
              {STRATEGY_BARS.map((b) => (
                <div
                  key={b.label}
                  className="flex flex-1 flex-col items-center gap-1.5"
                >
                  <span
                    className={`font-mono text-xs font-semibold ${b.positive ? "text-[#059669]" : "text-[#DC2626]"}`}
                  >
                    {b.pct}
                  </span>
                  <div
                    className="w-full rounded-t-md transition-all duration-500"
                    style={{
                      height: `${b.height * 1.8}px`,
                      background: b.positive ? "#34D399" : "#F87171",
                    }}
                  />
                  <span className="text-xs text-[color:var(--text-muted)]">
                    {b.label}
                  </span>
                </div>
              ))}
            </div>
          </article>

          {/* Cell B: 리스크 지표 */}
          <article className="rounded-[14px] border border-[color:var(--border)] bg-white p-7 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
            <h3 className="font-display text-base font-semibold text-[color:var(--text-primary)]">
              리스크 지표
            </h3>
            <div className="mt-5 space-y-4">
              <RiskRow label="Max Drawdown" value="12.3%" tone="bad" width={45} />
              <RiskRow label="VaR (95%)" value="4.8%" tone="warn" width={25} />
              <RiskRow label="Sharpe Ratio" value="2.47" tone="good" width={70} />
            </div>
          </article>

          {/* Cell C: Pine Script 코드 */}
          <article className="rounded-[14px] border border-[color:var(--border)] bg-[#0B1120] p-6 text-[color:#EDEDEF] shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
            <h3 className="font-display text-base font-semibold text-white">
              Pine Script
            </h3>
            <pre className="mt-4 overflow-x-auto font-mono text-[11px] leading-relaxed">
              <code>
                <span className="text-[#8A8F98]">{"// QuantBridge 전략 예시"}</span>
                {"\n"}
                <span className="text-[#C084FC]">{"//@version=5"}</span>
                {"\n"}
                <span className="text-[#60A5FA]">strategy</span>(
                <span className="text-[#34D399]">&quot;MA Cross&quot;</span>,{" "}
                <span className="text-[#FBBF24]">overlay</span>=
                <span className="text-[#C084FC]">true</span>)
                {"\n\n"}
                <span className="text-[#FBBF24]">fast</span> ={" "}
                <span className="text-[#60A5FA]">ta.sma</span>(
                <span className="text-[#60A5FA]">close</span>,{" "}
                <span className="text-[#F472B6]">12</span>)
                {"\n"}
                <span className="text-[#FBBF24]">slow</span> ={" "}
                <span className="text-[#60A5FA]">ta.sma</span>(
                <span className="text-[#60A5FA]">close</span>,{" "}
                <span className="text-[#F472B6]">26</span>)
                {"\n\n"}
                <span className="text-[#C084FC]">if</span>{" "}
                <span className="text-[#60A5FA]">ta.crossover</span>(
                <span className="text-[#FBBF24]">fast</span>,{" "}
                <span className="text-[#FBBF24]">slow</span>)
                {"\n  "}
                <span className="text-[#60A5FA]">strategy.entry</span>(
                <span className="text-[#34D399]">&quot;Long&quot;</span>,{" "}
                <span className="text-[#60A5FA]">strategy.long</span>)
              </code>
            </pre>
          </article>

          {/* Cell D: 실시간 모니터링 (wide on lg) */}
          <article className="rounded-[14px] border border-[color:var(--border)] bg-white p-7 shadow-[0_1px_3px_rgba(0,0,0,0.04)] lg:col-span-2">
            <h3 className="font-display text-base font-semibold text-[color:var(--text-primary)]">
              실시간 모니터링
            </h3>
            <p className="mt-1 text-sm text-[color:var(--text-muted)]">
              활성 전략 상태
            </p>
            <ul className="mt-5 divide-y divide-[color:var(--border)]">
              {LIVE_STRATEGIES.map((s) => (
                <li
                  key={s.name}
                  className="flex items-center gap-3 py-3 text-sm"
                >
                  <span
                    className={`size-2.5 shrink-0 rounded-full ${
                      s.state === "active"
                        ? "bg-[#34D399] motion-safe:animate-[livePulse_1.6s_ease-in-out_infinite]"
                        : "bg-[#FBBF24]"
                    }`}
                    aria-hidden
                  />
                  <span className="flex-1 font-medium text-[color:var(--text-primary)]">
                    {s.name}
                  </span>
                  <span className="text-xs text-[color:var(--text-muted)]">
                    {s.status}
                  </span>
                </li>
              ))}
            </ul>
          </article>
        </div>
      </div>
    </section>
  );
}

function RiskRow({
  label,
  value,
  tone,
  width,
}: {
  label: string;
  value: string;
  tone: "good" | "warn" | "bad";
  width: number;
}) {
  const valueColor =
    tone === "good"
      ? "text-[#059669]"
      : tone === "warn"
        ? "text-[#D97706]"
        : "text-[#DC2626]";
  const barColor =
    tone === "good"
      ? "bg-[#A7F3D0]"
      : tone === "warn"
        ? "bg-[#FEF3C7]"
        : "bg-[#FECACA]";
  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <span className="text-[color:var(--text-secondary)]">{label}</span>
        <span className={`font-mono font-semibold ${valueColor}`}>{value}</span>
      </div>
      <div className="mt-1.5 h-1.5 rounded-full bg-[color:var(--bg-alt)]">
        <div
          className={`h-full rounded-full ${barColor}`}
          style={{ width: `${width}%` }}
        />
      </div>
    </div>
  );
}
