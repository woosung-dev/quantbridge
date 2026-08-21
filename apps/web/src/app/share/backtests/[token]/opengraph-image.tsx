// 백테스트 share OG 이미지 (Next.js 16 ImageResponse API) — Sprint 41 Worker H
// 색상: 정적 렌더라 CSS 변수 불가 → lib/brand-palette.ts 다크 팔레트 상수 참조 (하드코딩 hex 금지)
import { ImageResponse } from "next/og";

import { getApiBase } from "@/lib/api-base";
import { BRAND_PALETTE } from "@/lib/brand-palette";
import { BacktestDetailSchema } from "@/features/backtest/schemas";
import { describeSharpe } from "@/features/backtest/sharpe-convention";

// 다크 디폴트 브랜드와 일치 — OG 는 카본/스틸 다크 팔레트 고정
const P = BRAND_PALETTE.dark;

export const runtime = "nodejs";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

interface OGProps {
  params: Promise<{ token: string }>;
}

async function loadDetail(token: string) {
  try {
    const res = await fetch(`${getApiBase()}/api/v1/backtests/share/${encodeURIComponent(token)}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return BacktestDetailSchema.parse(await res.json());
  } catch {
    return null;
  }
}

export default async function OG({ params }: OGProps) {
  const { token } = await params;
  const detail = await loadDetail(token);
  const symbol = detail?.symbol ?? "—";
  const timeframe = detail?.timeframe ?? "";
  const totalReturn = detail?.metrics?.total_return ?? null;
  const sharpeDisplay = describeSharpe(
    detail?.metrics?.sharpe_convention,
    detail?.metrics?.sharpe_ratio,
  ).display;
  const mdd = detail?.metrics?.max_drawdown ?? null;

  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        background: P.bg,
        color: P.textPrimary,
        padding: 64,
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          fontSize: 24,
          color: P.textSecondary,
        }}
      >
        <span style={{ fontWeight: 700, color: P.primary }}>QuantBridge</span>
        <span style={{ opacity: 0.5 }}>·</span>
        <span>백테스트 결과</span>
      </div>
      <div
        style={{
          marginTop: 28,
          display: "flex",
          alignItems: "baseline",
          gap: 18,
          fontSize: 84,
          fontWeight: 800,
          letterSpacing: "-0.02em",
        }}
      >
        <span>{symbol}</span>
        <span style={{ fontSize: 40, color: P.textSecondary, fontWeight: 500 }}>{timeframe}</span>
      </div>
      <div
        style={{
          marginTop: 60,
          display: "flex",
          gap: 28,
        }}
      >
        <Stat label="총 수익률" value={pct(totalReturn)} accent={P.bullish} />
        <Stat label="Sharpe" value={sharpeDisplay} accent={P.primary} />
        <Stat label="MDD" value={pct(mdd)} accent={P.bearish} />
      </div>
      <div
        style={{
          marginTop: "auto",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          fontSize: 22,
          color: P.textMuted,
        }}
      >
        <span>quantbridge.app/share</span>
        <span>데모 트레이딩 무료 시작</span>
      </div>
    </div>,
    size,
  );
}

function Stat({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        padding: "24px 32px",
        borderRadius: 10, // DESIGN.md §5 radius-lg (카드)
        background: P.card,
        border: `1px solid ${P.border}`, // 플랫 + 1px 보더 (글래스 rgba 폐기)
        minWidth: 240,
      }}
    >
      <span style={{ fontSize: 20, color: P.textSecondary }}>{label}</span>
      <span
        style={{
          marginTop: 8,
          fontSize: 56,
          fontWeight: 800,
          color: accent,
          fontFamily: "ui-monospace, monospace",
        }}
      >
        {value}
      </span>
    </div>
  );
}

function pct(v: number | string | null | undefined): string {
  if (v == null) return "—";
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) ? `${(n * 100).toFixed(1)}%` : "—";
}
