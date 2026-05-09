// 랜딩 다크 대시보드 mockup — 사이드바 + 헤더 + KPI 4 + 차트 + 포지션 + 봇 + 체결 (정적 데모)
import type { ReactNode } from "react";

const KPIS = [
  {
    label: "총 자산",
    value: "$124,580.23",
    sub: "+$2,340 (+1.92%)",
    subTone: "green" as const,
    showLiveDot: true,
  },
  {
    label: "일일 수익",
    value: "+$2,340.15",
    valueTone: "green" as const,
    sub: "7일 연속 수익",
  },
  { label: "활성 봇", value: "7 / 12", sub: "2 일시정지 · 3 정지" },
  { label: "오픈 포지션", value: "4", sub: "3 롱 · 1 숏" },
];

const POSITIONS = [
  { pair: "BTC/USDT", side: "LONG" as const, pnl: "+12.4%", entry: "$48,250", size: "0.15 BTC" },
  { pair: "ETH/USDT", side: "SHORT" as const, pnl: "-2.1%", entry: "$3,250", size: "2.0 ETH" },
  { pair: "SOL/USDT", side: "LONG" as const, pnl: "+8.7%", entry: "$131.00", size: "10 SOL" },
  { pair: "AVAX/USDT", side: "LONG" as const, pnl: "+5.2%", entry: "$34.00", size: "50 AVAX" },
];

const BOTS = [
  { name: "MA Crossover v2", symbol: "BTC/USDT · 4h 실행", pnl: "+$340", count: "23건", state: "active" as const },
  { name: "RSI Divergence", symbol: "ETH/USDT · 2h 실행", pnl: "+$180", count: "12건", state: "active" as const },
  { name: "Bollinger Band", symbol: "SOL/USDT · 6h 실행", pnl: "+$95", count: "31건", state: "active" as const },
  { name: "Grid Trading", symbol: "ADA/USDT · 일시정지", pnl: "+$62", count: "45건", state: "paused" as const },
];

const TRADES = [
  { time: "14:23", action: "BUY" as const, sym: "BTC 0.05", price: "$67,843" },
  { time: "14:15", action: "SELL" as const, sym: "ETH 2.0", price: "$3,180" },
  { time: "13:48", action: "BUY" as const, sym: "SOL 10", price: "$142.50" },
  { time: "13:32", action: "SELL" as const, sym: "BTC 0.03", price: "$67,950" },
  { time: "13:12", action: "BUY" as const, sym: "AVAX 50", price: "$35.80" },
];

const SIDEBAR_NAV = [
  { label: "대시보드", active: true },
  { label: "전략", active: false },
  { label: "템플릿", active: false },
  { label: "백테스트", active: false },
  { label: "트레이딩", active: false },
  { label: "거래소", active: false },
];

export function LandingDashboardShowcase() {
  return (
    <section
      aria-labelledby="dash-showcase-heading"
      className="bg-[color:var(--bg)] px-6 py-20"
    >
      <div className="mx-auto max-w-[1200px]">
        <div className="mb-12 text-center">
          <div
            aria-hidden
            className="mx-auto mb-4 h-[3px] w-12 rounded-sm bg-[#6366F1]"
          />
          <h2
            id="dash-showcase-heading"
            className="font-display text-[clamp(1.75rem,3vw,2.25rem)] font-bold text-[color:var(--text-primary)]"
          >
            실시간 트레이딩 대시보드
          </h2>
          <p className="mx-auto mt-3 max-w-[560px] text-base text-[color:var(--text-secondary)]">
            포지션, 봇, 체결을 한 화면에서 모니터링하세요 — 실제 제품 미리보기
          </p>
        </div>

        <div
          aria-label="QuantBridge 대시보드 미리보기"
          className="overflow-hidden rounded-[16px] border border-white/5 bg-[#0B1120] text-[#EDEDEF] shadow-[0_24px_60px_rgba(15,23,42,0.4)]"
        >
          <div className="grid grid-cols-1 md:grid-cols-[180px_1fr]">
            {/* 사이드바 */}
            <aside className="hidden border-r border-white/5 bg-[#0F172A] p-4 md:block">
              <div className="mb-6 flex items-center gap-2 px-2 font-display text-sm font-bold text-white">
                <svg width="22" height="22" viewBox="0 0 28 28" fill="none" aria-hidden>
                  <path d="M4 20C4 20 8 8 14 8C20 8 24 20 24 20" stroke="#6366F1" strokeWidth="2.5" strokeLinecap="round" />
                  <path d="M2 18C2 18 7 10 14 10C21 10 26 18 26 18" stroke="#EDEDEF" strokeWidth="2" strokeLinecap="round" />
                </svg>
                QuantBridge
              </div>
              <nav className="flex flex-col gap-1">
                {SIDEBAR_NAV.map((n) => (
                  <span
                    key={n.label}
                    className={`rounded-md px-3 py-2 text-xs font-medium ${
                      n.active
                        ? "bg-white/10 text-white"
                        : "text-[#8A8F98]"
                    }`}
                  >
                    {n.label}
                  </span>
                ))}
                <div className="my-3 h-px bg-white/5" />
                <span className="rounded-md px-3 py-2 text-xs font-medium text-[#8A8F98]">
                  알림
                </span>
              </nav>
            </aside>

            {/* 메인 */}
            <div>
              {/* 헤더 */}
              <header className="flex flex-wrap items-center gap-4 border-b border-white/5 px-5 py-3">
                <div className="inline-flex rounded-md bg-white/5 p-0.5 text-[10px] font-semibold">
                  <span className="rounded bg-[#6366F1] px-2.5 py-1 text-white">
                    DEMO
                  </span>
                  <span className="px-2.5 py-1 text-[#8A8F98]">LIVE</span>
                </div>
                <div className="hidden h-4 w-px bg-white/10 md:block" />
                <div className="flex items-center gap-2 font-mono text-xs">
                  <span className="text-[#8A8F98]">BTC/USDT</span>
                  <span className="font-bold text-white">$67,843.52</span>
                  <span className="text-[#34D399]">+1.24%</span>
                </div>
                <div className="ml-auto hidden gap-5 lg:flex">
                  <BalanceItem label="잔고" value="$124,580" />
                  <BalanceItem label="오늘 P&L" value="+$2,340" tone="green" />
                </div>
              </header>

              {/* 콘텐츠 */}
              <div className="space-y-4 p-5">
                {/* KPI 4 */}
                <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                  {KPIS.map((k) => (
                    <div
                      key={k.label}
                      className="rounded-[10px] border border-white/5 bg-white/[0.03] p-3"
                    >
                      <div className="flex items-center gap-1.5 text-[10px] font-medium text-[#8A8F98]">
                        {k.showLiveDot === true && (
                          <span
                            className="size-1.5 rounded-full bg-[#34D399] motion-safe:animate-[livePulse_1.6s_ease-in-out_infinite]"
                            aria-hidden
                          />
                        )}
                        {k.label}
                      </div>
                      <div
                        className={`mt-1 font-mono text-lg font-bold ${
                          k.valueTone === "green" ? "text-[#34D399]" : "text-white"
                        }`}
                      >
                        {k.value}
                      </div>
                      <div
                        className={`mt-0.5 text-[10px] ${
                          k.subTone === "green" ? "text-[#34D399]" : "text-[#8A8F98]"
                        }`}
                      >
                        {k.sub}
                      </div>
                    </div>
                  ))}
                </div>

                {/* 차트 + 포지션 */}
                <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1.7fr_1fr]">
                  <Panel
                    title={
                      <span className="flex items-center gap-1.5">
                        <span
                          className="size-1.5 rounded-full bg-[#34D399] motion-safe:animate-[livePulse_1.6s_ease-in-out_infinite]"
                          aria-hidden
                        />
                        BTC/USDT 실시간
                      </span>
                    }
                    right={
                      <div className="flex gap-1 font-mono text-[10px]">
                        {["1m", "5m", "15m", "1h", "1D"].map((t) => (
                          <span
                            key={t}
                            className={`rounded px-1.5 py-0.5 ${
                              t === "15m"
                                ? "bg-[#6366F1] text-white"
                                : "text-[#8A8F98]"
                            }`}
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    }
                  >
                    <PriceChart />
                  </Panel>

                  <Panel
                    title="오픈 포지션 (4)"
                    right={
                      <span className="text-[10px] text-[#6366F1]">전체 보기</span>
                    }
                  >
                    <ul className="space-y-2.5">
                      {POSITIONS.map((p) => (
                        <li
                          key={p.pair}
                          className="rounded-md border border-white/5 bg-white/[0.02] p-2.5"
                        >
                          <div className="flex items-center gap-2 text-xs">
                            <span className="font-semibold text-white">
                              {p.pair}
                            </span>
                            <span
                              className={`rounded px-1.5 py-0.5 text-[9px] font-bold ${
                                p.side === "LONG"
                                  ? "bg-[#34D399]/20 text-[#34D399]"
                                  : "bg-[#F87171]/20 text-[#F87171]"
                              }`}
                            >
                              {p.side}
                            </span>
                            <span
                              className={`ml-auto font-mono font-semibold ${
                                p.pnl.startsWith("-")
                                  ? "text-[#F87171]"
                                  : "text-[#34D399]"
                              }`}
                            >
                              {p.pnl}
                            </span>
                          </div>
                          <div className="mt-1 flex justify-between font-mono text-[10px] text-[#8A8F98]">
                            <span>진입 {p.entry}</span>
                            <span>{p.size}</span>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </Panel>
                </div>

                {/* 봇 + 체결 */}
                <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                  <Panel
                    title="운영 중인 봇 (7)"
                    right={
                      <span className="text-[10px] text-[#6366F1]">관리 →</span>
                    }
                  >
                    <ul className="space-y-2">
                      {BOTS.map((b) => (
                        <li
                          key={b.name}
                          className="flex items-center gap-2 rounded-md border border-white/5 bg-white/[0.02] px-2.5 py-2 text-xs"
                        >
                          <span
                            className={`size-2 shrink-0 rounded-full ${
                              b.state === "active"
                                ? "bg-[#34D399]"
                                : "bg-[#FBBF24]"
                            }`}
                            aria-hidden
                          />
                          <div className="min-w-0 flex-1">
                            <div className="truncate font-medium text-white">
                              {b.name}
                            </div>
                            <div className="truncate text-[10px] text-[#8A8F98]">
                              {b.symbol}
                            </div>
                          </div>
                          <span className="font-mono font-semibold text-[#34D399]">
                            {b.pnl}
                          </span>
                          <span className="font-mono text-[10px] text-[#8A8F98]">
                            {b.count}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </Panel>

                  <Panel
                    title="최근 체결"
                    right={
                      <span className="text-[10px] text-[#8A8F98]">오늘 23건</span>
                    }
                  >
                    <ul className="space-y-1.5">
                      {TRADES.map((t, i) => (
                        <li
                          key={`${t.time}-${i}`}
                          className="flex items-center gap-3 font-mono text-xs"
                        >
                          <span className="w-10 text-[#8A8F98]">{t.time}</span>
                          <span
                            className={`rounded px-1.5 py-0.5 text-[9px] font-bold ${
                              t.action === "BUY"
                                ? "bg-[#34D399]/20 text-[#34D399]"
                                : "bg-[#F87171]/20 text-[#F87171]"
                            }`}
                          >
                            {t.action}
                          </span>
                          <span className="flex-1 text-white">{t.sym}</span>
                          <span className="text-[#8A8F98]">{t.price}</span>
                        </li>
                      ))}
                    </ul>
                  </Panel>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function BalanceItem({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "green";
}) {
  return (
    <div>
      <div className="text-[10px] text-[#8A8F98]">{label}</div>
      <div
        className={`font-mono text-sm font-bold ${tone === "green" ? "text-[#34D399]" : "text-white"}`}
      >
        {value}
      </div>
    </div>
  );
}

function Panel({
  title,
  right,
  children,
}: {
  title: ReactNode;
  right?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="rounded-[12px] border border-white/5 bg-white/[0.02] p-4">
      <div className="mb-3 flex items-center justify-between text-xs font-semibold text-white">
        <div>{title}</div>
        {right}
      </div>
      {children}
    </div>
  );
}

function PriceChart() {
  return (
    <svg
      role="img"
      aria-label="BTC/USDT 가격 차트"
      viewBox="0 0 560 200"
      className="w-full"
      preserveAspectRatio="none"
    >
      <defs>
        <linearGradient id="dashChartGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#34D399" stopOpacity="0.28" />
          <stop offset="100%" stopColor="#34D399" stopOpacity="0" />
        </linearGradient>
      </defs>
      <line x1="40" y1="30" x2="555" y2="30" stroke="rgba(255,255,255,0.04)" strokeWidth="1" />
      <line x1="40" y1="80" x2="555" y2="80" stroke="rgba(255,255,255,0.04)" strokeWidth="1" />
      <line x1="40" y1="130" x2="555" y2="130" stroke="rgba(255,255,255,0.04)" strokeWidth="1" />
      <text x="4" y="34" fill="#8A8F98" fontSize="9" fontFamily="JetBrains Mono">68K</text>
      <text x="4" y="84" fill="#8A8F98" fontSize="9" fontFamily="JetBrains Mono">67.5K</text>
      <text x="4" y="134" fill="#8A8F98" fontSize="9" fontFamily="JetBrains Mono">67K</text>
      <text x="90" y="185" fill="#8A8F98" fontSize="9" fontFamily="JetBrains Mono" textAnchor="middle">10:00</text>
      <text x="210" y="185" fill="#8A8F98" fontSize="9" fontFamily="JetBrains Mono" textAnchor="middle">11:00</text>
      <text x="330" y="185" fill="#8A8F98" fontSize="9" fontFamily="JetBrains Mono" textAnchor="middle">12:00</text>
      <text x="450" y="185" fill="#8A8F98" fontSize="9" fontFamily="JetBrains Mono" textAnchor="middle">13:00</text>
      <path
        d="M45,140 C70,138 90,130 110,125 C135,118 155,122 180,115 C205,108 225,98 250,92 C275,86 295,88 320,80 C345,72 365,62 390,55 C415,48 435,52 460,42 C485,32 510,28 535,25 L535,160 L45,160 Z"
        fill="url(#dashChartGrad)"
      />
      <path
        d="M45,140 C70,138 90,130 110,125 C135,118 155,122 180,115 C205,108 225,98 250,92 C275,86 295,88 320,80 C345,72 365,62 390,55 C415,48 435,52 460,42 C485,32 510,28 535,25"
        stroke="#34D399"
        strokeWidth="2"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <line x1="40" y1="25" x2="555" y2="25" stroke="#34D399" strokeWidth="1" strokeDasharray="3,3" opacity="0.5" />
      <rect x="515" y="16" width="45" height="18" rx="3" fill="rgba(52,211,153,0.18)" />
      <text x="537" y="28" fill="#34D399" fontSize="9" fontFamily="JetBrains Mono" fontWeight="700" textAnchor="middle">67,843</text>
      <circle cx="180" cy="115" r="4" fill="#34D399" />
      <circle cx="180" cy="115" r="6" fill="none" stroke="#34D399" strokeWidth="1" opacity="0.5" />
      <text x="195" y="110" fill="#34D399" fontSize="8" fontFamily="JetBrains Mono">Long</text>
      <circle cx="390" cy="55" r="4" fill="#FBBF24" />
      <text x="402" y="50" fill="#FBBF24" fontSize="8" fontFamily="JetBrains Mono">Exit +3.2%</text>
    </svg>
  );
}
