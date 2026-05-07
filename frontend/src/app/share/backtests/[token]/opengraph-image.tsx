// 백테스트 share OG 이미지 (Next.js 16 ImageResponse API) — Sprint 41 Worker H
import { ImageResponse } from "next/og";

import { getApiBase } from "@/lib/api-base";
import { BacktestDetailSchema } from "@/features/backtest/schemas";

export const runtime = "nodejs";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

interface OGProps {
  params: Promise<{ token: string }>;
}

async function loadDetail(token: string) {
  try {
    const res = await fetch(
      `${getApiBase()}/api/v1/backtests/share/${encodeURIComponent(token)}`,
      { cache: "no-store" },
    );
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
  const sharpe = detail?.metrics?.sharpe_ratio ?? null;
  const mdd = detail?.metrics?.max_drawdown ?? null;

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          background:
            "linear-gradient(135deg, #0b0f1a 0%, #11182b 50%, #0d1326 100%)",
          color: "#f8fafc",
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
            color: "#94a3b8",
          }}
        >
          <span style={{ fontWeight: 700, color: "#60a5fa" }}>QuantBridge</span>
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
          <span style={{ fontSize: 40, color: "#94a3b8", fontWeight: 500 }}>
            {timeframe}
          </span>
        </div>
        <div
          style={{
            marginTop: 60,
            display: "flex",
            gap: 28,
          }}
        >
          <Stat label="총 수익률" value={pct(totalReturn)} accent="#22c55e" />
          <Stat label="Sharpe" value={num(sharpe)} accent="#60a5fa" />
          <Stat label="MDD" value={pct(mdd)} accent="#f87171" />
        </div>
        <div
          style={{
            marginTop: "auto",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            fontSize: 22,
            color: "#94a3b8",
          }}
        >
          <span>quantbridge.app/share</span>
          <span>데모 트레이딩 무료 시작</span>
        </div>
      </div>
    ),
    size,
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent: string;
}) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        padding: "24px 32px",
        borderRadius: 16,
        background: "rgba(255,255,255,0.04)",
        border: "1px solid rgba(255,255,255,0.08)",
        minWidth: 240,
      }}
    >
      <span style={{ fontSize: 20, color: "#94a3b8" }}>{label}</span>
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

function num(v: number | string | null | undefined): string {
  if (v == null) return "—";
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) ? n.toFixed(2) : "—";
}
