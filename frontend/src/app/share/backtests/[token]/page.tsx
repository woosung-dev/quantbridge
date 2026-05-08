// 백테스트 결과 외부 공유 (public read-only) — Sprint 41 Worker H
import type { Metadata } from "next";
import Link from "next/link";

import { getApiBase } from "@/lib/api-base";
import {
  BacktestDetailSchema,
  type BacktestDetail,
} from "@/features/backtest/schemas";

import { ShareNotFoundState } from "./_components/share-not-found-state";
import { SharePublicBanner } from "./_components/share-public-banner";
import { ShareRevokedState } from "./_components/share-revoked-state";

export const dynamic = "force-dynamic"; // 토큰 lookup → revoke 즉시 반영

interface PageProps {
  params: Promise<{ token: string }>;
}

type FetchResult =
  | { kind: "ok"; data: BacktestDetail }
  | { kind: "revoked" }
  | { kind: "not-found" }
  | { kind: "error"; message: string };

async function fetchShare(token: string): Promise<FetchResult> {
  try {
    const res = await fetch(
      `${getApiBase()}/api/v1/backtests/share/${encodeURIComponent(token)}`,
      { cache: "no-store" },
    );
    if (res.status === 404) return { kind: "not-found" };
    if (res.status === 410) return { kind: "revoked" };
    if (!res.ok) {
      return { kind: "error", message: `HTTP ${res.status}` };
    }
    const json = await res.json();
    const parsed = BacktestDetailSchema.parse(json);
    return { kind: "ok", data: parsed };
  } catch (err) {
    return {
      kind: "error",
      message: err instanceof Error ? err.message : String(err),
    };
  }
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { token } = await params;
  return {
    title: "백테스트 결과 공유 | QuantBridge",
    description: "QuantBridge 에서 만든 백테스트 결과 — 데모 트레이딩 무료 시작",
    openGraph: {
      title: "백테스트 결과 | QuantBridge",
      description: "QuantBridge 백테스트 결과를 확인하세요",
      images: [`/share/backtests/${token}/opengraph-image`],
    },
  };
}

export default async function SharedBacktestPage({ params }: PageProps) {
  const { token } = await params;
  const result = await fetchShare(token);

  if (result.kind === "revoked") {
    return <ShareRevokedState />;
  }
  if (result.kind === "not-found") {
    return <ShareNotFoundState />;
  }
  if (result.kind === "error") {
    return (
      <CenteredCard
        title="잠시 후 다시 시도해 주세요"
        body={`결과를 불러오지 못했습니다: ${result.message}`}
      />
    );
  }

  const bt = result.data;
  const m = bt.metrics ?? null;
  return (
    <>
      <SharePublicBanner />
      <main className="mx-auto max-w-3xl px-6 py-10">
      <header className="mb-6 flex flex-col gap-2">
        <h1 className="font-display text-3xl font-bold">
          {bt.symbol} · {bt.timeframe}
        </h1>
        <p className="text-sm text-muted-foreground">
          {formatRange(bt.period_start, bt.period_end)}
        </p>
      </header>

      {m ? (
        <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="총 수익률" value={`${pct(toNum(m.total_return))}%`} />
          <Stat label="Sharpe" value={fmt(toNum(m.sharpe_ratio))} />
          <Stat label="MDD" value={`${pct(toNum(m.max_drawdown))}%`} />
          <Stat
            label="거래 수"
            value={`${m.num_trades.toLocaleString("ko-KR")}건`}
          />
        </section>
      ) : (
        <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
          결과 지표가 아직 준비되지 않았습니다
        </p>
      )}

      {bt.equity_curve && bt.equity_curve.length > 0 ? (
        <section className="mt-6 rounded-xl border bg-card p-4">
          <h2 className="mb-3 text-sm font-medium">자산 곡선 미리보기</h2>
          <EquitySparkline points={bt.equity_curve} />
        </section>
      ) : null}

      <footer className="mt-10 flex flex-col items-center gap-3 rounded-xl border bg-muted/40 p-6 text-center">
        <p className="text-sm text-muted-foreground">
          QuantBridge 에서 만든 백테스트 결과 — 데모 트레이딩 무료 시작
        </p>
        <Link
          href="/sign-up"
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          QuantBridge 시작하기
        </Link>
      </footer>
      </main>
    </>
  );
}

function CenteredCard({ title, body }: { title: string; body: string }) {
  return (
    <main className="mx-auto flex max-w-md flex-col items-center gap-3 px-6 py-20 text-center">
      <h1 className="font-display text-xl font-bold">{title}</h1>
      <p className="text-sm text-muted-foreground">{body}</p>
      <Link
        href="/"
        className="mt-4 text-sm text-muted-foreground underline hover:text-foreground"
      >
        QuantBridge 홈으로
      </Link>
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <p className="text-[11px] text-muted-foreground">{label}</p>
      <p className="mt-1 font-mono text-base font-semibold">{value}</p>
    </div>
  );
}

function EquitySparkline({
  points,
}: {
  points: BacktestDetail["equity_curve"];
}) {
  if (!points || points.length < 2) return null;
  const values = points.map((p) =>
    typeof p.value === "number" ? p.value : Number(p.value),
  );
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const w = 600;
  const h = 80;
  const stepX = w / (values.length - 1);
  const path = values
    .map((v, i) => {
      const x = i * stepX;
      const y = h - ((v - min) / range) * h;
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      width="100%"
      height={h}
      role="img"
      aria-label="Equity curve sparkline"
      preserveAspectRatio="none"
    >
      <path
        d={path}
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        className="text-primary"
      />
    </svg>
  );
}

function toNum(v: number | string | null | undefined): number | null {
  if (v == null) return null;
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) ? n : null;
}

function pct(n: number | null): string {
  return n == null ? "—" : (n * 100).toFixed(2);
}

function fmt(n: number | null): string {
  return n == null ? "—" : n.toFixed(2);
}

function formatRange(start: string, end: string): string {
  const fmtDate = (s: string) => s.slice(0, 10);
  return `${fmtDate(start)} → ${fmtDate(end)}`;
}
