"use client";

// H2 Sprint 11 Phase D Step 4: 백테스트 결과 요약 + CTA.
// 총수익 / 승률 / 트레이드 수 3 지표만 간결히 표시 — 상세는 /backtests/:id 로.

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  CheckCircle2Icon,
  ChartNoAxesCombinedIcon,
  ExternalLinkIcon,
  TriangleAlertIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { useBacktest } from "@/features/backtest/hooks";

import { MetricTile } from "@/components/metric-tile";

function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "—";
  }
  return `${(value * 100).toFixed(2)}%`;
}

export function Step4Result({
  backtestId,
  onFinish,
}: {
  backtestId: string | null;
  onFinish: () => void;
}) {
  const router = useRouter();
  const detail = useBacktest(backtestId ?? undefined);
  const metrics = detail.data?.metrics ?? null;

  const totalReturn = metrics?.total_return ?? null;
  const winRate = metrics?.win_rate ?? null;
  const numTrades = metrics?.num_trades ?? null;

  // 결과 조회 실패 시 "완주!" 축하 헤드라인을 띄우지 않는다 (Surface Trust — 실데이터 없는 성공 표기 금지).
  if (backtestId && detail.isError) {
    return (
      <div>
        <div className="mb-5 flex items-center gap-3">
          <div className="grid size-12 place-items-center rounded-full bg-[color:var(--destructive)]/10">
            <TriangleAlertIcon
              className="size-6 text-[color:var(--destructive)]"
              strokeWidth={1.8}
            />
          </div>
          <div>
            <h2 className="font-display text-xl font-bold">
              결과를 불러오지 못했습니다
            </h2>
            <p className="text-xs text-[color:var(--text-muted)]">
              백테스트 결과를 가져오는 중 문제가 발생했습니다. 대시보드에서 다시
              확인해주세요.
            </p>
          </div>
        </div>

        <div className="mt-6 flex items-center justify-end gap-3">
          <Button
            onClick={() => {
              onFinish();
              router.push("/dashboard");
            }}
            aria-label="대시보드로 이동"
          >
            대시보드로 이동
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-5 flex items-center gap-3">
        <div className="grid size-12 place-items-center rounded-full bg-[color:var(--success)]/10">
          <CheckCircle2Icon
            className="size-6 text-[color:var(--success)]"
            strokeWidth={1.8}
          />
        </div>
        <div>
          <h2 className="font-display text-xl font-bold">첫 백테스트 완주!</h2>
          <p className="text-xs text-[color:var(--text-muted)]">
            결과 요약을 확인하고 대시보드에서 본 작업을 시작하세요.
          </p>
        </div>
      </div>

      <div className="mb-5 grid grid-cols-3 gap-3">
        <MetricCard label="총수익률" value={formatPercent(totalReturn)} />
        <MetricCard label="승률" value={formatPercent(winRate)} />
        <MetricCard
          label="트레이드 수"
          value={numTrades === null ? "—" : String(numTrades)}
        />
      </div>

      {detail.isLoading && (
        <p className="mb-5 text-xs text-[color:var(--text-muted)]">
          결과 불러오는 중…
        </p>
      )}

      {backtestId && (
        <Link
          href={`/backtests/${backtestId}`}
          className="mb-6 inline-flex items-center gap-1.5 text-xs font-medium text-[color:var(--primary)] underline-offset-2 hover:underline"
        >
          <ChartNoAxesCombinedIcon className="size-3.5" />
          상세 리포트 보기
          <ExternalLinkIcon className="size-3" />
        </Link>
      )}

      <div className="mt-6 flex items-center justify-end gap-3">
        <Button
          onClick={() => {
            onFinish();
            router.push("/dashboard");
          }}
          aria-label="대시보드로 이동"
        >
          시작하기 →
        </Button>
      </div>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return <MetricTile label={label} value={value} size="sm" />;
}
