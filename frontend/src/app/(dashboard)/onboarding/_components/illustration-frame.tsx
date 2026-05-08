// 온보딩 일러스트 SVG 프레임 — Sprint 42-polish W2-fidelity
// docs/prototypes/05-onboarding.html 의 풍부한 inline SVG 를 4 variant 로 1:1 모방.
// - code: Pine Script 코드 카드 + dashed 화살표 + bridge target + spark
// - chart: 백테스트 equity curve + chart bars + 축 + active dot
// - trade: BTC/USDT 가격 + uptrend line + BUY 라벨 + arrow
// - complete: 큰 체크 원 + sparkle stars
// prefers-reduced-motion 시 globals.css 가 일괄 disable. 추가 motion-safe wrapper 불필요.
"use client";

export type IllustrationVariant = "code" | "chart" | "trade" | "complete";

export interface IllustrationFrameProps {
  variant: IllustrationVariant;
}

export function IllustrationFrame({ variant }: IllustrationFrameProps) {
  return (
    <div
      data-testid={`illustration-${variant}`}
      className="relative grid min-h-[220px] place-items-center overflow-hidden rounded-[var(--radius-lg)] bg-gradient-to-br from-[#EFF6FF] to-[#F1F5F9] p-5 md:min-h-[340px] md:p-8"
      aria-hidden="true"
    >
      <svg
        className="h-auto w-full max-w-[280px]"
        viewBox="0 0 280 320"
        xmlns="http://www.w3.org/2000/svg"
        role="img"
      >
        <defs>
          <linearGradient id="onb-codeBg" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor="#FFFFFF" />
            <stop offset="1" stopColor="#F8FAFC" />
          </linearGradient>
          <linearGradient id="onb-targetGrad" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0" stopColor="#2563EB" />
            <stop offset="1" stopColor="#1D4ED8" />
          </linearGradient>
          <linearGradient id="onb-chartLine" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0" stopColor="#2563EB" />
            <stop offset="1" stopColor="#3B82F6" />
          </linearGradient>
          <linearGradient id="onb-successGrad" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0" stopColor="#10B981" />
            <stop offset="1" stopColor="#059669" />
          </linearGradient>
          <filter id="onb-codeShadow" x="-10%" y="-10%" width="120%" height="120%">
            <feDropShadow dx="0" dy="4" stdDeviation="6" floodColor="#1E293B" floodOpacity="0.08" />
          </filter>
        </defs>

        {/* 배경 sparkles — 4 variant 공통 */}
        <g opacity="0.8">
          <path d="M30 40 l3 7 l7 3 l-7 3 l-3 7 l-3-7 l-7-3 l7-3 z" fill="#DBEAFE" />
          <path d="M250 70 l2 5 l5 2 l-5 2 l-2 5 l-2-5 l-5-2 l5-2 z" fill="#DBEAFE" />
          <path
            d="M245 250 l2.5 6 l6 2.5 l-6 2.5 l-2.5 6 l-2.5-6 l-6-2.5 l6-2.5 z"
            fill="#BFDBFE"
          />
        </g>

        {variant === "code" && <CodeArt />}
        {variant === "chart" && <ChartArt />}
        {variant === "trade" && <TradeArt />}
        {variant === "complete" && <CompleteArt />}
      </svg>
    </div>
  );
}

/**
 * Code variant — Pine Script 카드 + dashed 화살표 + bridge target.
 * prototype 05-onboarding.html lines 654-757 1:1 transcription.
 */
function CodeArt() {
  return (
    <>
      {/* Code card */}
      <g filter="url(#onb-codeShadow)">
        <rect
          x="20"
          y="50"
          width="180"
          height="160"
          rx="12"
          fill="url(#onb-codeBg)"
          stroke="#E2E8F0"
        />
        {/* title bar dots */}
        <circle cx="36" cy="66" r="3.5" fill="#F87171" />
        <circle cx="48" cy="66" r="3.5" fill="#FBBF24" />
        <circle cx="60" cy="66" r="3.5" fill="#34D399" />
        <text
          x="80"
          y="70"
          fontFamily="JetBrains Mono, monospace"
          fontSize="9"
          fill="#94A3B8"
        >
          strategy.pine
        </text>
        <line x1="28" y1="82" x2="192" y2="82" stroke="#F1F5F9" />

        {/* code lines — Pine v5 mock */}
        <g fontFamily="JetBrains Mono, monospace" fontSize="9">
          <text x="30" y="98" fill="#94A3B8">
            1
          </text>
          <text x="46" y="98" fill="#7C3AED">
            {"//@version=5"}
          </text>

          <text x="30" y="114" fill="#94A3B8">
            2
          </text>
          <text x="46" y="114" fill="#2563EB">
            strategy
          </text>
          <text x="92" y="114" fill="#475569">
            (
          </text>
          <text x="97" y="114" fill="#059669">
            &quot;EMA Cross&quot;
          </text>

          <text x="30" y="130" fill="#94A3B8">
            3
          </text>
          <text x="46" y="130" fill="#2563EB">
            fast
          </text>
          <text x="68" y="130" fill="#475569">
            =
          </text>
          <text x="76" y="130" fill="#DC2626">
            ema
          </text>
          <text x="94" y="130" fill="#475569">
            (close,
          </text>
          <text x="128" y="130" fill="#F59E0B">
            12
          </text>
          <text x="140" y="130" fill="#475569">
            )
          </text>

          <text x="30" y="146" fill="#94A3B8">
            4
          </text>
          <text x="46" y="146" fill="#2563EB">
            slow
          </text>
          <text x="68" y="146" fill="#475569">
            =
          </text>
          <text x="76" y="146" fill="#DC2626">
            ema
          </text>
          <text x="94" y="146" fill="#475569">
            (close,
          </text>
          <text x="128" y="146" fill="#F59E0B">
            26
          </text>
          <text x="140" y="146" fill="#475569">
            )
          </text>

          <text x="30" y="162" fill="#94A3B8">
            5
          </text>
          <text x="46" y="162" fill="#7C3AED">
            if
          </text>
          <text x="60" y="162" fill="#475569">
            ta.crossover(fast,
          </text>
          <text x="152" y="162" fill="#475569">
            slow)
          </text>

          <text x="30" y="178" fill="#94A3B8">
            6
          </text>
          <text x="52" y="178" fill="#475569">
            strategy.entry(
          </text>
          <text x="120" y="178" fill="#059669">
            &quot;L&quot;
          </text>
          <text x="135" y="178" fill="#475569">
            ,
          </text>
          <text x="145" y="178" fill="#2563EB">
            long
          </text>
          <text x="168" y="178" fill="#475569">
            )
          </text>

          <text x="30" y="194" fill="#94A3B8">
            7
          </text>
          {/* caret blink */}
          <rect
            x="46"
            y="186"
            width="6"
            height="10"
            fill="#2563EB"
            style={{ animation: "onb-caret-blink 1.1s infinite" }}
          />
        </g>
      </g>

      {/* Arrow — dashed marching line + arrowhead */}
      <g stroke="#2563EB" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round">
        <path
          d="M210 130 C 230 130, 230 180, 210 200"
          strokeDasharray="4 5"
          style={{ animation: "onb-arrow-march 1.4s linear infinite" }}
        />
        <path d="M205 195 l8 8 l-2 -11 z" fill="#2563EB" />
      </g>

      {/* Bridge target — QuantBridge mark */}
      <g transform="translate(170 225)">
        <circle cx="45" cy="40" r="46" fill="url(#onb-targetGrad)" />
        <circle
          cx="45"
          cy="40"
          r="46"
          fill="none"
          stroke="#2563EB"
          strokeOpacity="0.15"
          strokeWidth="6"
        />
        <g
          stroke="#fff"
          strokeWidth="2.4"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M24 48 h42" />
          <path d="M28 48 V34 a6 6 0 0 1 6 -6 h22 a6 6 0 0 1 6 6 v14" />
          <path d="M36 48 v-6" />
          <path d="M54 48 v-6" />
          <path d="M45 48 v-14" />
        </g>
      </g>

      {/* Small spark near target */}
      <circle
        cx="218"
        cy="220"
        r="4"
        fill="#FBBF24"
        style={{ animation: "onb-spark-pulse 1.6s infinite" }}
      />
    </>
  );
}

/**
 * Chart variant — 백테스트 equity curve.
 * 카드 + 축 + 막대 + line + 우측 등장 dot.
 */
function ChartArt() {
  // 막대 7개 — 좌→우 점층 상승
  const bars = [
    { x: 40, h: 30, fill: "#DBEAFE" },
    { x: 60, h: 50, fill: "#DBEAFE" },
    { x: 80, h: 42, fill: "#DBEAFE" },
    { x: 100, h: 70, fill: "#BFDBFE" },
    { x: 120, h: 60, fill: "#BFDBFE" },
    { x: 140, h: 90, fill: "#93C5FD" },
    { x: 160, h: 78, fill: "#93C5FD" },
  ];
  return (
    <>
      {/* Card */}
      <g filter="url(#onb-codeShadow)">
        <rect
          x="20"
          y="50"
          width="240"
          height="220"
          rx="14"
          fill="url(#onb-codeBg)"
          stroke="#E2E8F0"
        />
        {/* header */}
        <text
          x="36"
          y="78"
          fontFamily="Plus Jakarta Sans, sans-serif"
          fontSize="11"
          fontWeight="700"
          fill="#0F172A"
        >
          Equity Curve
        </text>
        <text
          x="36"
          y="94"
          fontFamily="JetBrains Mono, monospace"
          fontSize="9"
          fill="#94A3B8"
        >
          backtest · 6mo
        </text>
        {/* P&L badge */}
        <g transform="translate(196 70)">
          <rect width="48" height="20" rx="10" fill="#D1FAE5" />
          <text
            x="24"
            y="14"
            textAnchor="middle"
            fontFamily="JetBrains Mono, monospace"
            fontSize="10"
            fontWeight="600"
            fill="#059669"
          >
            +18.4%
          </text>
        </g>

        {/* axis */}
        <line x1="36" y1="240" x2="244" y2="240" stroke="#E2E8F0" />
        <line x1="36" y1="120" x2="36" y2="240" stroke="#E2E8F0" />

        {/* bars — bottom-up rising */}
        <g>
          {bars.map((b, i) => (
            <rect
              key={i}
              x={b.x}
              y={240 - b.h}
              width="14"
              height={b.h}
              rx="3"
              fill={b.fill}
              style={{
                transformOrigin: `${b.x + 7}px 240px`,
                animation: `onb-chart-bar-rise 600ms ${i * 80}ms ease-out both`,
              }}
            />
          ))}
        </g>

        {/* equity line — points roughly above bars */}
        <polyline
          points="44,210 64,180 84,188 104,148 124,156 144,116 164,128 184,108 204,124 224,98"
          fill="none"
          stroke="url(#onb-chartLine)"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* active dot at the rightmost point */}
        <circle cx="224" cy="98" r="5" fill="#2563EB">
          <animate attributeName="r" values="4;6;4" dur="1.6s" repeatCount="indefinite" />
        </circle>
        <circle cx="224" cy="98" r="9" fill="#2563EB" opacity="0.18">
          <animate attributeName="r" values="7;13;7" dur="1.6s" repeatCount="indefinite" />
        </circle>
      </g>
    </>
  );
}

/**
 * Trade variant — BTC/USDT live + BUY signal.
 */
function TradeArt() {
  return (
    <>
      {/* Card */}
      <g filter="url(#onb-codeShadow)">
        <rect
          x="20"
          y="50"
          width="240"
          height="220"
          rx="14"
          fill="url(#onb-codeBg)"
          stroke="#E2E8F0"
        />
        {/* symbol */}
        <text
          x="36"
          y="84"
          fontFamily="Plus Jakarta Sans, sans-serif"
          fontSize="13"
          fontWeight="700"
          fill="#0F172A"
        >
          BTC/USDT
        </text>
        <text
          x="36"
          y="108"
          fontFamily="JetBrains Mono, monospace"
          fontSize="20"
          fontWeight="700"
          fill="#0F172A"
        >
          68,420
        </text>
        <text
          x="120"
          y="108"
          fontFamily="JetBrains Mono, monospace"
          fontSize="13"
          fontWeight="600"
          fill="#059669"
        >
          +2.34%
        </text>

        {/* mini chart */}
        <polyline
          points="36,200 70,178 102,188 134,156 168,162 200,134 236,124"
          fill="none"
          stroke="url(#onb-chartLine)"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* dashed grid */}
        <line x1="36" y1="148" x2="244" y2="148" stroke="#E2E8F0" strokeDasharray="3 4" />
        <line x1="36" y1="200" x2="244" y2="200" stroke="#E2E8F0" strokeDasharray="3 4" />

        {/* BUY signal pill at last point */}
        <g transform="translate(196 220)">
          <rect width="56" height="28" rx="14" fill="#2563EB" />
          <g
            transform="translate(10 14)"
            stroke="#fff"
            strokeWidth="2"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="0" y1="0" x2="8" y2="0" />
            <polyline points="4 -4 8 0 4 4" />
          </g>
          <text
            x="38"
            y="18"
            fontFamily="Plus Jakarta Sans, sans-serif"
            fontSize="10"
            fontWeight="700"
            fill="#fff"
            textAnchor="middle"
          >
            BUY
          </text>
        </g>

        {/* heartbeat dot */}
        <circle cx="236" cy="124" r="4" fill="#2563EB">
          <animate attributeName="r" values="3;5;3" dur="1.4s" repeatCount="indefinite" />
        </circle>
        <circle cx="236" cy="124" r="9" fill="#2563EB" opacity="0.18">
          <animate attributeName="r" values="6;12;6" dur="1.4s" repeatCount="indefinite" />
        </circle>
      </g>
    </>
  );
}

/**
 * Complete variant — 큰 체크 + sparkle.
 */
function CompleteArt() {
  return (
    <>
      {/* outer glow ring */}
      <circle cx="140" cy="160" r="92" fill="#D1FAE5" opacity="0.65" />
      <circle cx="140" cy="160" r="76" fill="#D1FAE5" />
      {/* core circle */}
      <circle cx="140" cy="160" r="60" fill="url(#onb-successGrad)" />
      <path
        d="M115 160 L135 180 L170 140"
        fill="none"
        stroke="#fff"
        strokeWidth="7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* sparkle stars around the check */}
      <g fill="#FBBF24">
        <path d="M50 80 l3 7 l7 3 l-7 3 l-3 7 l-3-7 l-7-3 l7-3 z">
          <animate attributeName="opacity" values="0.4;1;0.4" dur="1.8s" repeatCount="indefinite" />
        </path>
        <path d="M230 70 l2.5 6 l6 2.5 l-6 2.5 l-2.5 6 l-2.5-6 l-6-2.5 l6-2.5 z">
          <animate attributeName="opacity" values="0.4;1;0.4" dur="2.1s" repeatCount="indefinite" />
        </path>
        <path d="M240 240 l2 5 l5 2 l-5 2 l-2 5 l-2-5 l-5-2 l5-2 z">
          <animate attributeName="opacity" values="0.4;1;0.4" dur="1.6s" repeatCount="indefinite" />
        </path>
      </g>

      {/* small confetti bits */}
      <g>
        <circle cx="80" cy="240" r="3" fill="#3B82F6" opacity="0.7" />
        <circle cx="220" cy="260" r="3" fill="#A78BFA" opacity="0.7" />
        <rect x="60" y="120" width="6" height="6" rx="1" fill="#F472B6" opacity="0.7" />
        <rect x="216" y="170" width="6" height="6" rx="1" fill="#34D399" opacity="0.7" />
      </g>
    </>
  );
}
