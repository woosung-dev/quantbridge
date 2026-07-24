// 활성 라이브 세션별 거래소 포지션 대조 표를 렌더한다.
"use client";

import { useState } from "react";
import { AlertTriangleIcon, RefreshCwIcon } from "lucide-react";

import { StateBox } from "@/components/state-box";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  useClosePosition,
  useLiveSessionsPositions,
  type LiveSessionPositionRow,
} from "@/features/live-sessions/hooks";
import type { LiveSession, LiveSessionPositions } from "@/features/live-sessions/schemas";

export const POSITION_VERDICT_HEADING: Record<LiveSessionPositions["diff"]["verdict"], string> = {
  match: "거래소와 일치",
  qty_mismatch: "거래소와 수량이 일치하지 않습니다.",
  side_mismatch: "거래소와 방향이 일치하지 않습니다.",
  exchange_only: "거래소에만 포지션이 있습니다.",
  local_only: "전략에만 열린 거래가 있습니다.",
  unknown: "포지션 대조 상태를 확인할 수 없습니다.",
};

const POSITION_UNSUPPORTED_BODY: Record<string, string> = {
  live_mode_stub: "라이브 모드의 포지션 대조는 아직 제공되지 않습니다.",
  exchange_unsupported: "이 거래소의 포지션 대조는 아직 지원하지 않습니다.",
  spot_position_api_unsupported: "현물 세션의 포지션 대조는 아직 지원하지 않습니다.",
  settings_unset: "전략 레버리지 설정이 없어 포지션을 대조할 수 없습니다.",
};

const EMPTY_CELL = "—";

function directionLabel(side: string): string {
  if (side === "long") return "롱";
  if (side === "short") return "숏";
  if (side === "flat") return "플랫";
  return "확인 불가";
}

export function formatPositionReturn(
  side: string,
  entryPrice: string | null,
  markPrice: string | null,
): string | null {
  if (entryPrice === null || markPrice === null || (side !== "long" && side !== "short")) {
    return null;
  }
  const entry = Number(entryPrice);
  const mark = Number(markPrice);
  if (!Number.isFinite(entry) || !Number.isFinite(mark) || entry === 0) return null;
  const result = side === "long" ? (mark - entry) / entry : (entry - mark) / entry;
  return `${(result * 100).toFixed(2)}%`;
}

function TableHeaders() {
  return (
    <thead>
      <tr>
        <th scope="col">심볼</th>
        <th scope="col">방향</th>
        <th scope="col" className="num">수량</th>
        <th scope="col" className="num">진입가</th>
        <th scope="col" className="num">마크가</th>
        <th scope="col" className="num">미실현</th>
        <th scope="col" className="num">수익률</th>
        <th scope="col" className="num">익절</th>
        <th scope="col" className="num">손절</th>
        <th scope="col" className="num">청산가</th>
        <th scope="col" className="num">레버리지</th>
        <th scope="col">세션(전략)</th>
        <th scope="col">대조</th>
        <th scope="col">청산</th>
      </tr>
    </thead>
  );
}

function PositionRow({
  row,
  resolveStrategyName,
  canClose,
  isClosing,
  onClose,
}: {
  row: LiveSessionPositionRow;
  resolveStrategyName?: (sessionId: string, fallback: string) => string;
  canClose: boolean;
  isClosing: boolean;
  onClose: (row: LiveSessionPositionRow) => void;
}) {
  const { position } = row;
  const returnValue = formatPositionReturn(position.side, position.entry_price, position.mark_price);
  const pnl = Number(position.unrealized_pnl);
  const returnNumber = returnValue === null ? null : Number(returnValue.slice(0, -1));
  return (
    <tr>
      <td className="mono-l">{row.symbol}</td>
      <td><span className={`side ${position.side}`}>{directionLabel(position.side)}</span></td>
      <td className="num">{position.size}</td>
      <td className="num">{position.entry_price ?? EMPTY_CELL}</td>
      <td className="num">{position.mark_price ?? EMPTY_CELL}</td>
      <td className={`num ${Number.isFinite(pnl) && pnl < 0 ? "neg" : Number.isFinite(pnl) && pnl > 0 ? "pos" : ""}`}>
        {position.unrealized_pnl ?? EMPTY_CELL}
      </td>
      <td className={`num ${returnNumber !== null && returnNumber < 0 ? "neg" : returnNumber !== null && returnNumber > 0 ? "pos" : ""}`}>
        {returnValue ?? EMPTY_CELL}
      </td>
      <td className="num">{position.take_profit_price ?? EMPTY_CELL}</td>
      <td className="num">{position.stop_loss_price ?? EMPTY_CELL}</td>
      <td className="num">{position.liquidation_price ?? EMPTY_CELL}</td>
      <td className="num">{position.leverage ?? EMPTY_CELL}</td>
      <td>{resolveStrategyName?.(row.sessionId, row.sessionLabel) ?? row.sessionLabel}</td>
      <td>{POSITION_VERDICT_HEADING[row.verdict]}</td>
      <td>
        {canClose ? (
          <button
            className="btn btn-xs btn-danger"
            type="button"
            disabled={isClosing}
            onClick={() => onClose(row)}
          >
            {isClosing ? "청산 중..." : "청산"}
          </button>
        ) : (
          <span title="데모 계정 포지션만 수동 청산할 수 있습니다.">{EMPTY_CELL}</span>
        )}
      </td>
    </tr>
  );
}

function PositionFootnote() {
  return (
    <>
      <p className="table-foot-note">
        §01 미실현(추정)과 이 표의 거래소 보고값은 다를 수 있으며 임의로 맞추지 않습니다.
      </p>
      <p className="table-foot-note">
        거래소가 포지션에 보고한 TP/SL만 표시 (별도 조건부 주문으로 건 TP/SL은 포함되지 않을 수 있습니다).
      </p>
    </>
  );
}

export function OpenPositionsTable({
  sessions,
  demoSessionIds,
  resolveStrategyName,
}: {
  sessions: readonly LiveSession[];
  demoSessionIds: ReadonlySet<string>;
  resolveStrategyName?: (sessionId: string, fallback: string) => string;
}) {
  const positions = useLiveSessionsPositions(sessions);
  const closePosition = useClosePosition();
  const [closeTarget, setCloseTarget] = useState<LiveSessionPositionRow | null>(null);
  const [closeError, setCloseError] = useState<string | null>(null);

  const handleClose = async () => {
    if (!closeTarget) return;
    try {
      await closePosition.mutateAsync({
        sessionId: closeTarget.sessionId,
        symbol: closeTarget.symbol,
      });
      setCloseTarget(null);
    } catch (error) {
      setCloseError(error instanceof Error ? error.message : "청산 요청을 보내지 못했습니다.");
    }
  };

  if (sessions.length === 0) {
    return (
      <div className="card" data-testid="open-positions-table">
        <div className="card-body">
          <StateBox
            testId="open-positions-no-sessions"
            title="활성 라이브 세션이 없습니다."
            body="활성 세션이 생기면 거래소 보고 포지션을 세션별로 대조합니다."
          />
        </div>
      </div>
    );
  }

  if (positions.isLoading || positions.isPending) {
    return (
      <div className="card" data-testid="open-positions-table" aria-busy="true">
        <div className="card-body"><div className="sk" style={{ height: 160 }} /></div>
      </div>
    );
  }

  if (positions.isError) {
    return (
      <div className="card" data-testid="open-positions-table">
        <div className="card-body">
          <StateBox
            tone="failed"
            testId="open-positions-error"
            icon={<AlertTriangleIcon />}
            title="포지션을 다시 불러오지 못했습니다."
            body="거래소 응답을 확인하지 못했습니다."
            code="GET /api/v1/live-sessions/{session_id}/positions · 503"
          >
            <button className="btn btn-ghost" type="button" onClick={() => void positions.refetch()}>
              <RefreshCwIcon aria-hidden="true" />
              다시 시도
            </button>
          </StateBox>
        </div>
      </div>
    );
  }

  if (positions.rows.length === 0 && positions.unsupported.length === 0) {
    return (
      <div className="card" data-testid="open-positions-table">
        <div className="card-body">
          <StateBox
            testId="open-positions-empty"
            title="열린 포지션이 없습니다."
            body="활성 세션의 거래소 보고값에서 열린 포지션을 찾지 못했습니다."
          />
        </div>
        <PositionFootnote />
      </div>
    );
  }

  return (
    <>
      <div className="card" data-testid="open-positions-table">
        <div className="card-head">
          <div>
            <h3 className="card-title">세션별 대조</h3>
            <p className="card-sub">대조 시각 {positions.latestFetchedAt ?? "확인 불가"}</p>
          </div>
        </div>
        <div className="table-wrap">
          <table className="trades" aria-label="세션별 열린 포지션 대조">
            <TableHeaders />
            <tbody>
              {positions.rows.map((row, index) => (
                <PositionRow
                  key={`${row.sessionId}-${row.symbol}-${row.position.side}-${index}`}
                  row={row}
                  resolveStrategyName={resolveStrategyName}
                  canClose={demoSessionIds.has(row.sessionId)}
                  isClosing={
                    closePosition.isPending &&
                    closePosition.variables?.sessionId === row.sessionId &&
                    closePosition.variables.symbol === row.symbol
                  }
                  onClose={(target) => {
                    setCloseError(null);
                    setCloseTarget(target);
                  }}
                />
              ))}
              {positions.unsupported.map((item) => (
                <tr key={item.sessionId} data-testid="open-positions-unsupported">
                  <td colSpan={14}>
                    {item.symbol} · {resolveStrategyName?.(item.sessionId, item.sessionLabel) ?? item.sessionLabel} · {POSITION_UNSUPPORTED_BODY[item.reason ?? ""] ?? "포지션 대조 조건을 확인하지 못했습니다."}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <PositionFootnote />
      </div>
      <Dialog
        open={closeTarget !== null}
        onOpenChange={(open) => {
          if (!open) {
            setCloseError(null);
            setCloseTarget(null);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>포지션 청산</DialogTitle>
            <DialogDescription>
              이 작업은 {closeTarget?.symbol}의 거래소 계정 단위 순 포지션을 평탄화하는 감소전용 시장가 주문을 냅니다. 세션이 활성 상태면 다음 평가에서 다시 진입할 수 있으며, 수동 청산은 봇을 중단하지 않습니다.
            </DialogDescription>
          </DialogHeader>
          {closeError ? <p className="notice-inline" role="alert">{closeError}</p> : null}
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setCloseTarget(null)}>
              취소
            </Button>
            <Button variant="destructive" onClick={() => void handleClose()} disabled={closePosition.isPending}>
              청산 실행
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
