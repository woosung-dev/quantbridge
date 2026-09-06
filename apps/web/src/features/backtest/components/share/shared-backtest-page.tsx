// 백테스트 결과 외부 공유 (public read-only) — Sprint 41 Worker H
import Link from "next/link";

import { getApiBase } from "@/lib/api-base";
import { BacktestDetailSchema, type BacktestDetail } from "@/features/backtest/schemas";
import { describeSharpe } from "@/features/backtest/sharpe-convention";
import { deriveTradeCounts } from "@/features/backtest/trade-counts";

import { ShareNotFoundState } from "@/features/backtest/components/share/share-not-found-state";
import { SharePublicBanner } from "@/features/backtest/components/share/share-public-banner";
import { ShareRevokedState } from "@/features/backtest/components/share/share-revoked-state";

// ★`export const dynamic` 은 여기 두면 **무효**다 — 라우트 세그먼트 설정은 `app/**/page.tsx` 에서만
//   읽힌다. 유효본 = `app/share/backtests/[token]/page.tsx` 의 `force-dynamic`(토큰 lookup → revoke 즉시 반영).

type FetchResult =
  | { kind: "ok"; data: BacktestDetail }
  | { kind: "revoked" }
  | { kind: "not-found" }
  | { kind: "error" };

async function fetchShare(token: string): Promise<FetchResult> {
  try {
    const res = await fetch(`${getApiBase()}/api/v1/backtests/share/${encodeURIComponent(token)}`, {
      cache: "no-store",
    });
    if (res.status === 404) return { kind: "not-found" };
    if (res.status === 410) return { kind: "revoked" };
    if (!res.ok) {
      console.error("Shared backtest request failed", { status: res.status });
      return { kind: "error" };
    }
    const json = await res.json();
    const parsed = BacktestDetailSchema.parse(json);
    return { kind: "ok", data: parsed };
  } catch (error) {
    console.error("Shared backtest request failed", {
      errorType: error instanceof Error ? error.name : "unknown",
    });
    return { kind: "error" };
  }
}

export async function SharedBacktestPage({ token }: { token: string }) {
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
        body="결과를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요."
      />
    );
  }

  const bt = result.data;
  const m = bt.metrics ?? null;
  return (
    <>
      <SharePublicBanner />
      <main className="mx-auto max-w-3xl px-6 py-10">
        <header className="mb-6 flex flex-col gap-2 motion-safe:animate-[sharePopIn_280ms_ease-out_both]">
          <h1 className="font-display text-3xl font-bold">
            {bt.symbol} · {bt.timeframe}
          </h1>
          <p className="text-sm text-muted-foreground">
            {formatRange(bt.period_start, bt.period_end)}
          </p>
        </header>

        {m ? (
          <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { label: "총 수익률", value: `${pct(toNum(m.total_return))}%` },
              {
                label: "Sharpe",
                // 공개 표면이라 더 중요하다 — degenerate 실행을 `0.00` 으로 내보내면
                // 링크를 받은 사람은 검증할 방법이 없다.
                value: describeSharpe(m.sharpe_convention, toNum(m.sharpe_ratio)).display,
              },
              { label: "MDD", value: `${pct(toNum(m.max_drawdown))}%` },
              {
                // ★BL-822 — 단일 숫자만 보이는 표면은 **완료 거래**로 통일한다.
                //   detail 응답의 num_trades 는 미청산까지 포함한 수라 목록 화면과
                //   어긋나고, 링크를 받은 사람에겐 대조할 수단이 없다.
                label: "완료 거래",
                value: `${deriveTradeCounts(m).completed.toLocaleString("ko-KR")}건`,
              },
            ].map((stat, idx) => (
              <Stat
                key={stat.label}
                label={stat.label}
                value={stat.value}
                animationDelay={idx * 70}
              />
            ))}
          </section>
        ) : (
          <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground motion-safe:animate-[sharePopIn_280ms_ease-out_both]">
            결과 지표가 아직 준비되지 않았습니다
          </p>
        )}

        {bt.equity_curve && bt.equity_curve.length > 0 ? (
          <section
            className="mt-6 rounded-lg border bg-card p-4 motion-safe:animate-[sharePopIn_320ms_ease-out_240ms_both]"
            style={{ animationDelay: "240ms" }}
          >
            <h2 className="mb-3 text-sm font-medium">자산 곡선 미리보기</h2>
            <EquitySparkline points={bt.equity_curve} />
          </section>
        ) : null}

        <footer className="mt-10 flex flex-col items-center gap-3 rounded-lg border bg-muted/40 p-6 text-center motion-safe:animate-[sharePopIn_320ms_ease-out_360ms_both]">
          <p className="text-sm text-muted-foreground">
            QuantBridge 에서 만든 백테스트 결과 — 데모 트레이딩 무료 시작
          </p>
          <Link
            href="/sign-up"
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-btn-primary transition-colors duration-200 ease-out hover:bg-primary-hover"
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
      <Link href="/" className="mt-4 text-sm text-muted-foreground underline hover:text-foreground">
        QuantBridge 홈으로
      </Link>
    </main>
  );
}

function Stat({
  label,
  value,
  animationDelay = 0,
}: {
  label: string;
  value: string;
  animationDelay?: number;
}) {
  return (
    <div
      style={{ animationDelay: `${animationDelay}ms` }}
      className="rounded-lg border bg-card p-3 transition-colors duration-200 ease-out hover:border-border-dark motion-safe:animate-[staggerIn_280ms_ease-out_both]"
    >
      <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 font-mono text-base font-semibold">{value}</p>
    </div>
  );
}

/** 스파크라인 가로 픽셀당 1 표본이면 충분하다 — 그 이상은 화면에 나타나지 않는다. */
const SPARKLINE_MAX_SAMPLES = 600;

function EquitySparkline({ points }: { points: BacktestDetail["equity_curve"] }) {
  if (!points || points.length < 2) return null;

  // `equity_curve` 는 **OHLCV 바 하나당 1 포인트**다(백엔드 `_compute_equity_curve`
  // = "bar-by-bar equity 재구성"). 1년 1분봉이면 ~525,600 포인트다.
  //
  // 그래서 두 가지를 하면 안 된다.
  //  ① `Math.min(...values)` — spread 는 인자 개수 상한이라 큰 배열에서
  //     RangeError 로 던진다(Node 22 실측 임계 ≈ 124,000). 이 페이지는
  //     `force-dynamic` 서버 컴포넌트라 던지면 **공개 공유 링크가 500** 이 된다.
  //  ② 포인트마다 path 명령을 1개씩 붙이기 — 52만 포인트면 path 문자열만
  //     수 MB 라 HTML 응답이 그만큼 부푼다.
  //
  // 스케일은 전체를 한 번만 훑어 **정확하게** 잡고, 그리는 점만 솎아낸다.
  const w = 600;
  const h = 80;
  const total = points.length;

  let min = Number.POSITIVE_INFINITY;
  let max = Number.NEGATIVE_INFINITY;
  for (let i = 0; i < total; i += 1) {
    const raw = points[i]?.value;
    const v = typeof raw === "number" ? raw : Number(raw);
    if (!Number.isFinite(v)) continue;
    if (v < min) min = v;
    if (v > max) max = v;
  }
  if (!Number.isFinite(min) || !Number.isFinite(max)) return null;

  const range = max - min || 1;
  const stride = Math.max(1, Math.ceil(total / SPARKLINE_MAX_SAMPLES));
  const lastIndex = total - 1;
  const segments: string[] = [];
  for (let i = 0; i < total; i += stride) {
    const raw = points[i]?.value;
    const v = typeof raw === "number" ? raw : Number(raw);
    if (!Number.isFinite(v)) continue;
    const x = (i / lastIndex) * w;
    const y = h - ((v - min) / range) * h;
    segments.push(`${segments.length === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`);
  }
  // 솎아내기가 마지막 점을 건너뛰면 커브가 끝에서 잘려 보인다.
  if (lastIndex % stride !== 0) {
    const raw = points[lastIndex]?.value;
    const v = typeof raw === "number" ? raw : Number(raw);
    if (Number.isFinite(v)) {
      const y = h - ((v - min) / range) * h;
      segments.push(`L${w.toFixed(1)},${y.toFixed(1)}`);
    }
  }
  if (segments.length < 2) return null;
  const path = segments.join(" ");
  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      width="100%"
      height={h}
      role="img"
      aria-label="Equity curve sparkline"
      preserveAspectRatio="none"
    >
      <path d={path} fill="none" stroke="currentColor" strokeWidth="2" className="text-primary" />
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

function formatRange(start: string, end: string): string {
  const fmtDate = (s: string) => s.slice(0, 10);
  return `${fmtDate(start)} → ${fmtDate(end)}`;
}
