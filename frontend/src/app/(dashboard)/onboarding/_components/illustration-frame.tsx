// 온보딩 일러스트 SVG 프레임 — Sprint 42-polish W2
// variant 별 단순 SVG (placeholder 수준). prefers-reduced-motion 시 animation disable.
// prototype 05 의 풍부한 SVG 중 핵심만 발췌.
"use client";

export type IllustrationVariant = "code" | "chart" | "trade" | "complete";

export interface IllustrationFrameProps {
  variant: IllustrationVariant;
}

export function IllustrationFrame({ variant }: IllustrationFrameProps) {
  return (
    <div
      data-testid={`illustration-${variant}`}
      className="grid min-h-[220px] place-items-center overflow-hidden rounded-[var(--radius-lg)] bg-gradient-to-br from-[color:var(--primary-light)] to-[color:var(--bg-alt)] p-6 md:min-h-[340px] md:p-8"
      aria-hidden="true"
    >
      <svg
        className="h-auto w-full max-w-[280px]"
        viewBox="0 0 280 280"
        xmlns="http://www.w3.org/2000/svg"
      >
        {variant === "code" && <CodeArt />}
        {variant === "chart" && <ChartArt />}
        {variant === "trade" && <TradeArt />}
        {variant === "complete" && <CompleteArt />}
      </svg>
    </div>
  );
}

function CodeArt() {
  return (
    <g>
      <rect x="20" y="40" width="240" height="200" rx="14" fill="#fff" stroke="#E2E8F0" />
      <circle cx="36" cy="60" r="4" fill="#F87171" />
      <circle cx="50" cy="60" r="4" fill="#FBBF24" />
      <circle cx="64" cy="60" r="4" fill="#34D399" />
      <line x1="20" y1="80" x2="260" y2="80" stroke="#F1F5F9" />
      <text x="40" y="110" fontFamily="JetBrains Mono, monospace" fontSize="11" fill="#7C3AED">
        {"//@version=5"}
      </text>
      <text x="40" y="130" fontFamily="JetBrains Mono, monospace" fontSize="11" fill="#2563EB">
        strategy
      </text>
      <text x="100" y="130" fontFamily="JetBrains Mono, monospace" fontSize="11" fill="#059669">
        &quot;EMA Cross&quot;
      </text>
      <text x="40" y="150" fontFamily="JetBrains Mono, monospace" fontSize="11" fill="#475569">
        fast = ema(close, 12)
      </text>
      <text x="40" y="170" fontFamily="JetBrains Mono, monospace" fontSize="11" fill="#475569">
        slow = ema(close, 26)
      </text>
      <rect
        x="40"
        y="180"
        width="6"
        height="12"
        fill="#2563EB"
        className="motion-safe:animate-pulse"
      />
    </g>
  );
}

function ChartArt() {
  return (
    <g>
      <rect x="20" y="40" width="240" height="200" rx="14" fill="#fff" stroke="#E2E8F0" />
      <polyline
        points="40,200 80,160 120,180 160,120 200,140 240,80"
        fill="none"
        stroke="#2563EB"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <line x1="40" y1="220" x2="240" y2="220" stroke="#E2E8F0" />
      <line x1="40" y1="60" x2="40" y2="220" stroke="#E2E8F0" />
      <circle cx="240" cy="80" r="6" fill="#2563EB" className="motion-safe:animate-pulse" />
    </g>
  );
}

function TradeArt() {
  return (
    <g>
      <rect x="20" y="40" width="240" height="200" rx="14" fill="#fff" stroke="#E2E8F0" />
      <text x="40" y="80" fontFamily="Inter, sans-serif" fontSize="13" fontWeight="600" fill="#0F172A">
        BTC/USDT
      </text>
      <text x="40" y="105" fontFamily="JetBrains Mono, monospace" fontSize="20" fontWeight="700" fill="#059669">
        +2.34%
      </text>
      <g
        stroke="#2563EB"
        strokeWidth="2.4"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M40 180 L100 150 L160 165 L220 130" />
      </g>
      <g transform="translate(180 180)">
        <path
          d="M0 0 L40 0 L40 30 L0 30 Z"
          fill="#2563EB"
          opacity="0.15"
        />
        <text x="20" y="20" fontFamily="Inter, sans-serif" fontSize="11" fontWeight="600" fill="#2563EB" textAnchor="middle">
          BUY
        </text>
      </g>
    </g>
  );
}

function CompleteArt() {
  return (
    <g>
      <circle cx="140" cy="140" r="80" fill="#D1FAE5" />
      <circle cx="140" cy="140" r="60" fill="#059669" />
      <path
        d="M115 140 L135 160 L170 120"
        fill="none"
        stroke="#fff"
        strokeWidth="6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="60" cy="60" r="6" fill="#FBBF24" className="motion-safe:animate-pulse" />
      <circle cx="220" cy="80" r="4" fill="#FBBF24" className="motion-safe:animate-pulse" />
      <circle cx="240" cy="220" r="5" fill="#FBBF24" className="motion-safe:animate-pulse" />
    </g>
  );
}
