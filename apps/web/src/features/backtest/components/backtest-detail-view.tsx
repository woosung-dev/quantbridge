"use client";

// 백테스트 리포트 상세 — C 디자인 언어 이식(W2). variant-c 리포트 헤더(.report + 칩) + 상태 분기.
// 완료 상태만 BacktestReportShell(번호 섹션 IA)이 전담. 대기/실행 중/실패/취소는 StateBox·스켈레톤
// 으로 재스킨한다. 상태 라벨·톤은 용어 SSOT(BACKTEST_STATUS_LABEL) → CHIP_TONE_CLASS 로 파생.
// 백테스트 진행은 도메인상 인쇄 가능하나 서버가 % 를 보고하지 않아 스켈레톤(shimmer)으로만 알린다
// (§4.9 예외 + 캐논 rule 13: 무한 애니메이션은 shimmer 하나 · 펄스/블링크 금지).

import { AlertTriangleIcon, ArrowLeftIcon, CheckIcon } from "lucide-react";
import Link from "next/link";
import { useEffect } from "react";

import { BACKTEST_STATUS_LABEL } from "@/features/backtest/labels";
import { useBacktest, useBacktestProgress } from "@/features/backtest/hooks";
import type { BacktestStatus } from "@/features/backtest/schemas";
import { formatDate } from "@/features/backtest/utils";
import { StateBox } from "@/components/state-box";
import { CHIP_TONE_CLASS } from "@/lib/labels";

import { BacktestReportShell } from "@/features/backtest/components/report/backtest-report-shell";
import { RerunButton } from "@/features/backtest/components/rerun-button";
import { ShareButton } from "@/features/backtest/components/share-button";

const TERMINAL_STATUSES = ["completed", "failed", "cancelled"] as const;

export function BacktestDetailView({ id }: { id: string }) {
  const detail = useBacktest(id);
  const progress = useBacktestProgress(id);

  // Terminal 전환 시 detail refetch — queued→completed 감지되면 initial cache (metrics=null)
  // 를 신선화. LESSON-004 guard: primitive dep (string) + stable function reference.
  const progressStatus = progress.data?.status;
  const detailStatus = detail.data?.status;
  const refetchDetail = detail.refetch;
  useEffect(() => {
    if (!progressStatus) return;
    if (!(TERMINAL_STATUSES as readonly string[]).includes(progressStatus)) return;
    if (detailStatus === progressStatus) return;
    refetchDetail();
  }, [progressStatus, detailStatus, refetchDetail]);

  if (detail.isLoading) {
    return <DetailSkeleton />;
  }

  if (detail.isError || !detail.data) {
    return (
      <main className="page">
        <section className="card">
          <div className="card-body">
            <StateBox
              tone="failed"
              testId="backtest-detail-error"
              icon={<AlertTriangleIcon />}
              title="백테스트 정보를 불러오지 못했습니다."
              body={
                detail.error
                  ? detail.error.message
                  : "네트워크 또는 서버 상태 일시적 오류일 수 있습니다."
              }
              code={`GET /api/v1/backtests/${id}`}
            >
              <button className="btn btn-ghost" type="button" onClick={() => detail.refetch()}>
                다시 시도
              </button>
            </StateBox>
          </div>
        </section>
      </main>
    );
  }

  const bt = detail.data;
  const effectiveStatus: BacktestStatus = progress.data?.status ?? bt.status;
  const isTerminal = (TERMINAL_STATUSES as readonly string[]).includes(effectiveStatus);
  const { label: statusLabel, tone: statusTone, showCheckIcon } =
    BACKTEST_STATUS_LABEL[effectiveStatus];

  const isInProgress =
    effectiveStatus === "queued" ||
    effectiveStatus === "running" ||
    effectiveStatus === "cancelling";

  return (
    <main className="page">
      {/* ===== 리포트 헤더 ===== */}
      <section className="card" aria-label="리포트 개요">
        <div className="report">
          <div>
            <h1 className="report-title">
              {bt.symbol} · {bt.timeframe}
            </h1>
            <div className="report-meta">
              {/* symbol·timeframe 은 바로 위 h1 이 이미 말한다 — 같은 헤더 안 중복 칩 금지. */}
              <span className={CHIP_TONE_CLASS[statusTone]}>
                {showCheckIcon ? <CheckIcon aria-hidden="true" /> : null}
                {statusLabel}
              </span>
              <span className="chip">Bybit</span>
              <span className="chip">
                {formatDate(bt.period_start)} ~ {formatDate(bt.period_end)}
              </span>
              <span className="chip accent">바 단위 이벤트 루프</span>
              <span className="chip">{bt.id.slice(0, 8)}</span>
            </div>
          </div>
          <div className="report-actions">
            {effectiveStatus === "completed" ? (
              <ShareButton backtestId={bt.id} isEnabled />
            ) : null}
            <RerunButton backtest={bt} isEnabled={isTerminal} />
            <Link className="btn btn-ghost" href="/backtests">
              <ArrowLeftIcon aria-hidden="true" />
              목록
            </Link>
          </div>
        </div>
      </section>

      {/* ===== 상태 분기 ===== */}
      {isInProgress ? (
        <InProgressCard status={effectiveStatus} />
      ) : null}

      {effectiveStatus === "failed" ? (
        <section className="card" aria-label="실행 실패">
          <div className="card-body">
            <StateBox
              tone="failed"
              testId="backtest-failed-state"
              icon={<AlertTriangleIcon />}
              title="백테스트가 실패했습니다."
              body={progress.data?.error ?? bt.error ?? "알 수 없는 오류로 실행이 중단되었습니다."}
              code={`GET /api/v1/backtests/${id}`}
            >
              <button
                className="btn btn-ghost"
                type="button"
                onClick={() => {
                  detail.refetch();
                  progress.refetch();
                }}
              >
                새로고침
              </button>
            </StateBox>
            <p className="state-note" style={{ marginTop: 12 }}>
              같은 파라미터로 다시 실행하려면 위 재실행 버튼을 누르세요.
            </p>
          </div>
        </section>
      ) : null}

      {effectiveStatus === "cancelled" ? (
        <section className="card" aria-label="실행 취소">
          <div className="card-body">
            <StateBox
              testId="backtest-cancelled-state"
              title="취소된 백테스트입니다."
              body="사용자가 실행을 취소했습니다. 위 재실행 버튼으로 같은 파라미터를 다시 실행할 수 있습니다."
            />
          </div>
        </section>
      ) : null}

      {effectiveStatus === "completed" && !bt.metrics ? (
        <section className="card" aria-busy="true" aria-label="결과 준비 중">
          <div className="card-body">
            <div className="sk sk-line" style={{ width: "40%" }} aria-hidden="true" />
            <p className="state-note" style={{ marginTop: 12 }}>
              결과를 불러오는 중입니다. 잠시만 기다려 주세요.
            </p>
          </div>
        </section>
      ) : null}

      {effectiveStatus === "completed" && bt.metrics ? (
        <BacktestReportShell backtest={bt} currentId={id} />
      ) : null}
    </main>
  );
}

// 대기/실행 중/취소 중 — 서버가 진행 % 를 보고하지 않아 스켈레톤(shimmer)으로만 알린다.
function InProgressCard({ status }: { status: "queued" | "running" | "cancelling" }) {
  const label =
    status === "queued" ? "대기" : status === "cancelling" ? "취소 중" : "실행 중";
  return (
    <section className="card" aria-busy="true" aria-label={`${label} 상태`} data-testid="backtest-in-progress">
      <div className="card-body">
        <div className="sk-bars" aria-hidden="true">
          {[46, 72, 30, 88, 54, 66, 38, 78].map((h, i) => (
            <span key={i} className="sk" style={{ height: `${h}%` }} />
          ))}
        </div>
        <div className="sk sk-line" style={{ width: "58%" }} aria-hidden="true" />
        <p className="state-note" style={{ marginTop: 12 }}>
          {label}입니다. 결과가 준비되면 자동으로 화면이 채워집니다. 30초 간격으로 다시 확인합니다.
        </p>
      </div>
    </section>
  );
}

// 상세 로딩 스켈레톤 — 헤더 카드 + 요약 자리. 라우트 loading.tsx 도 이것을 재사용한다
// (클라 컴포넌트를 서버 loading 에서 import 하는 것은 App Router 에서 합법).
export function DetailSkeleton() {
  return (
    <main className="page" aria-busy="true" data-testid="backtest-detail-skeleton">
      <section className="card" aria-hidden="true">
        <div className="report">
          <div>
            <span className="sk" style={{ display: "block", width: 220, height: 32 }} />
            <div className="report-meta">
              {/* 실헤더 칩 5개(상태·Bybit·기간·엔진·ID)와 개수를 맞춘다. */}
              {Array.from({ length: 5 }).map((_, i) => (
                <span key={i} className="sk" style={{ display: "block", width: 74, height: 26 }} />
              ))}
            </div>
          </div>
        </div>
      </section>
      <section className="section" aria-hidden="true">
        <div className="kpi-row">
          {Array.from({ length: 4 }).map((_, i) => (
            <article key={i} className="card kpi">
              <span className="sk" style={{ display: "block", width: 88, height: 12 }} />
              <span className="sk" style={{ display: "block", width: 120, height: 30, marginTop: 12 }} />
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
