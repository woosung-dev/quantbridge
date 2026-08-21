// BL-498 — 거래소 계정에 남아 있는 포지션을 세션과 무관하게 렌더하고 청산까지 연결한다.
"use client";

import { useState } from "react";
import { useIsMutating } from "@tanstack/react-query";
import { AlertTriangleIcon, RefreshCwIcon } from "lucide-react";

import { StateBox } from "@/components/state-box";
import {
  isAccepted,
  outcomeFromError,
  outcomeFromResponse,
  type CloseOutcome,
} from "@/features/live-sessions/close-outcome";
import { CloseOutcomePanel } from "@/features/live-sessions/components/close-outcome-panel";
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
  closePositionMutationKey,
  useAccountPositions,
  useClosePosition,
} from "@/features/live-sessions/hooks";
import type { AccountPositionRow } from "@/features/live-sessions/schemas";

import { EMPTY_CELL, directionLabel, formatPositionReturn } from "./open-positions-table";

const UNSUPPORTED_BODY: Record<string, string> = {
  live_mode_stub: "라이브 모드 계정의 포지션 조회는 아직 제공되지 않습니다.",
  exchange_unsupported: "이 거래소의 포지션 조회는 아직 지원하지 않습니다.",
};

// 청산 불가 사유. 버튼을 주고 눌렀을 때 실패시키지 않고, 왜 못 닫는지를 먼저 말한다.
const CLOSE_BLOCKED_BODY: Record<string, string> = {
  // 주문 원장 행은 `strategy_id` 를 요구한다. 임의 전략에 붙여 닫으면 원장이 거짓 귀속을 갖는다.
  no_owning_session: "이 계정·심볼로 만든 세션이 없어 원장에 귀속할 수 없습니다.",
  // 감소전용 시장가 청산은 one-way 단일 leg 만 지원한다(양방향은 어느 leg 인지 추론 불가).
  hedge_unsupported: "양방향 포지션은 화면에서 청산할 수 없습니다. 거래소에서 정리해주세요.",
  read_only_key: "이 API 키는 읽기 전용이라 화면에서 청산할 수 없습니다.",
  position_side_unsupported: "거래소 포지션 방향을 해석할 수 없어 화면에서 청산할 수 없습니다.",
};

export type AccountTarget = {
  id: string;
  label: string;
  exchangeUid?: string | null;
  readOnly?: boolean | null;
};

type Row = AccountPositionRow & {
  accountId: string;
  accountLabel: string;
  exchangeUid: string | null;
  readOnly: boolean | null;
};

function collapseRows(rows: readonly Row[]): Row[] {
  const ungrouped: Row[] = [];
  const groups = new Map<string, Row[]>();
  for (const row of rows) {
    if (row.exchangeUid === null || row.close_blocked_reason === "hedge_unsupported") {
      ungrouped.push(row);
      continue;
    }
    const key = `${row.exchangeUid}\u0000${row.symbol}`;
    const group = groups.get(key);
    if (group) group.push(row);
    else groups.set(key, [row]);
  }

  for (const group of groups.values()) {
    const closable = group.find(
      (row) =>
        row.readOnly !== true &&
        row.closable_session_id !== null &&
        row.close_blocked_reason === null,
    );
    if (closable) {
      ungrouped.push(closable);
      continue;
    }
    const survivor = group.find((row) => row.readOnly !== true) ?? group[0];
    if (!survivor) continue;
    ungrouped.push({
      ...survivor,
      closable_session_id: null,
      close_blocked_reason: group.every((row) => row.readOnly === true)
        ? "read_only_key"
        : (survivor.close_blocked_reason ?? "no_owning_session"),
    });
  }
  return ungrouped;
}

function TableHeaders() {
  return (
    <thead>
      <tr>
        <th scope="col">심볼</th>
        <th scope="col">방향</th>
        <th scope="col" className="num">
          수량
        </th>
        <th scope="col" className="num">
          진입가
        </th>
        <th scope="col" className="num">
          마크가
        </th>
        <th scope="col" className="num">
          미실현
        </th>
        <th scope="col" className="num">
          수익률
        </th>
        <th scope="col" className="num">
          청산가
        </th>
        <th scope="col" className="num">
          레버리지
        </th>
        <th scope="col">계정</th>
        <th scope="col">청산</th>
      </tr>
    </thead>
  );
}

function PositionRow({ row, onClose }: { row: Row; onClose: (row: Row) => void }) {
  const isClosing =
    useIsMutating({
      mutationKey: closePositionMutationKey({
        sessionId: row.closable_session_id ?? "",
        symbol: row.symbol,
      }),
    }) > 0;
  const { position } = row;
  const returnValue = formatPositionReturn(
    position.side,
    position.entry_price,
    position.mark_price,
  );
  const pnl = Number(position.unrealized_pnl);
  const returnNumber = returnValue === null ? null : Number(returnValue.slice(0, -1));
  return (
    <tr>
      <td className="mono-l">{row.symbol}</td>
      <td>
        <span className={`side ${position.side}`}>{directionLabel(position.side)}</span>
      </td>
      <td className="num">{position.size}</td>
      <td className="num">{position.entry_price ?? EMPTY_CELL}</td>
      <td className="num">{position.mark_price ?? EMPTY_CELL}</td>
      <td
        className={`num ${Number.isFinite(pnl) && pnl < 0 ? "neg" : Number.isFinite(pnl) && pnl > 0 ? "pos" : ""}`}
      >
        {position.unrealized_pnl ?? EMPTY_CELL}
      </td>
      <td
        className={`num ${returnNumber !== null && returnNumber < 0 ? "neg" : returnNumber !== null && returnNumber > 0 ? "pos" : ""}`}
      >
        {returnValue ?? EMPTY_CELL}
      </td>
      <td className="num">{position.liquidation_price ?? EMPTY_CELL}</td>
      <td className="num">{position.leverage ?? EMPTY_CELL}</td>
      <td>{row.accountLabel}</td>
      <td>
        {row.closable_session_id !== null && row.close_blocked_reason === null ? (
          <button
            className="btn btn-xs btn-danger"
            type="button"
            disabled={isClosing}
            onClick={() => onClose(row)}
            data-testid={`account-position-close-${row.symbol}`}
          >
            {isClosing ? "청산 중..." : "청산"}
          </button>
        ) : (
          <span data-testid={`account-position-blocked-${row.symbol}`}>
            {CLOSE_BLOCKED_BODY[row.close_blocked_reason ?? ""] ??
              "이 포지션은 화면에서 청산할 수 없습니다."}
          </span>
        )}
      </td>
    </tr>
  );
}

export function AccountPositionsTable({ accounts }: { accounts: readonly AccountTarget[] }) {
  const queries = useAccountPositions(accounts);
  const [closeTarget, setCloseTarget] = useState<Row | null>(null);
  const closePosition = useClosePosition(
    closeTarget?.closable_session_id
      ? { sessionId: closeTarget.closable_session_id, symbol: closeTarget.symbol }
      : undefined,
  );
  const [closeOutcome, setCloseOutcome] = useState<CloseOutcome | null>(null);

  const handleClose = async () => {
    if (!closeTarget?.closable_session_id) return;
    try {
      const outcome = outcomeFromResponse(await closePosition.mutateAsync());
      // 잔량도 없고 조회도 성공했으면 더 말할 것이 없다. 그때만 조용히 닫는다.
      if (outcome.kind === "clean") {
        setCloseTarget(null);
        return;
      }
      setCloseOutcome(outcome);
    } catch (error) {
      // ★`ApiError.message` 는 `API 422 /api/v1/…` 라 사람에게 아무것도 알려주지 않는다.
      //   서버가 `detail` 에 실제 사유를 싣는다(`no_open_position`·`settings_unset` 등).
      //   409 잔량은 문장 말고 주문 목록까지 들고 온다.
      setCloseOutcome(outcomeFromError(error));
    }
  };

  if (accounts.length === 0) {
    return (
      <div className="card" data-testid="account-positions-table">
        <div className="card-body">
          <StateBox
            testId="account-positions-no-accounts"
            title="등록된 거래소 계정이 없습니다."
            body="계정을 등록하면 세션과 무관하게 남아 있는 포지션을 표시합니다."
          />
        </div>
      </div>
    );
  }

  const isLoading = queries.some((query) => query.isLoading);
  // ★전부 실패했더라도 **보여줄 것이 남아 있으면** 에러 박스로 덮지 않는다. 낡은
  //   값이라도 감추면 노출이 사라진 것처럼 읽힌다 — 아래에서 계정별로 "최신이
  //   아니다" 를 말한다. 정말 아무것도 없을 때만 에러 박스로 떨어진다.
  const isError =
    queries.length > 0 &&
    queries.every((query) => query.isError) &&
    queries.every((query) => query.data === undefined);

  if (isLoading) {
    return (
      <div className="card" data-testid="account-positions-table" aria-busy="true">
        <div className="card-body">
          <div className="sk" style={{ height: 120 }} />
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="card" data-testid="account-positions-table">
        <div className="card-body">
          <StateBox
            tone="failed"
            testId="account-positions-error"
            icon={<AlertTriangleIcon />}
            title="계정 포지션을 불러오지 못했습니다."
            body="거래소 응답을 확인하지 못했습니다."
            code="GET /api/v1/exchange-accounts/{account_id}/positions · 503"
          >
            <button
              className="btn btn-ghost"
              type="button"
              onClick={() => queries.forEach((query) => void query.refetch())}
            >
              <RefreshCwIcon aria-hidden="true" />
              다시 시도
            </button>
          </StateBox>
        </div>
      </div>
    );
  }

  const rows: Row[] = [];
  const unsupported: { accountId: string; accountLabel: string; reason: string | null }[] = [];
  // ★계정 하나가 실패해도 나머지는 보여준다. 그런데 실패한 계정을 **행에서 지우면**
  //   "이 계정에 포지션이 없다" 로 읽힌다 — 잔여 노출 관리 표에서 그건 정확히 반대의
  //   거짓말이다. 실패는 실패라고 말하고 그 계정만 다시 시도하게 한다.
  const failed: {
    accountId: string;
    accountLabel: string;
    hasStaleData: boolean;
    retry: () => void;
  }[] = [];
  const settleCoins = new Set<string>();
  let truncated = false;
  let latestFetchedAt: string | null = null;

  for (const [index, query] of queries.entries()) {
    const account = accounts[index];
    if (!account) continue;
    const data = query.data;
    if (query.isError) {
      // 성공 이력이 있으면 React Query 가 마지막 payload 를 남긴다. 그 값은 최신이
      // 아니므로 그대로 두되(지우면 노출이 숨는다) 낡았다고 명시한다.
      failed.push({
        accountId: account.id,
        accountLabel: account.label,
        hasStaleData: data !== undefined,
        retry: () => void query.refetch(),
      });
    }
    if (!data) continue;
    // ★`fetched_at` 은 성공한 조회에서만 취한다. 실패한 계정의 낡은 시각이 헤더의
    //   "조회 시각" 을 최신으로 물들이면 낡음이 그 한 줄에 가려진다.
    if (
      !query.isError &&
      data.fetched_at &&
      (!latestFetchedAt || data.fetched_at > latestFetchedAt)
    ) {
      latestFetchedAt = data.fetched_at;
    }
    if (!data.supported) {
      unsupported.push({
        accountId: account.id,
        accountLabel: account.label,
        reason: data.reason,
      });
      continue;
    }
    if (!query.isError) {
      settleCoins.add(data.settle_coin);
      if (data.truncated) truncated = true;
    }
    for (const row of data.rows) {
      rows.push({
        ...row,
        accountId: account.id,
        accountLabel: account.label,
        exchangeUid: account.exchangeUid ?? null,
        readOnly: account.readOnly ?? null,
      });
    }
  }

  const visibleRows = collapseRows(rows);

  if (visibleRows.length === 0 && unsupported.length === 0 && failed.length === 0) {
    return (
      <div className="card" data-testid="account-positions-table">
        <div className="card-body">
          <StateBox
            testId="account-positions-empty"
            title="계정에 남아 있는 포지션이 없습니다."
            body="등록된 거래소 계정에서 열린 포지션을 찾지 못했습니다."
          />
        </div>
        <ScopeFootnote settleCoins={settleCoins} truncated={truncated} />
      </div>
    );
  }

  return (
    <>
      <div className="card" data-testid="account-positions-table">
        <div className="card-head">
          <div>
            <h3 className="card-title">계정 잔여 포지션</h3>
            <p className="card-sub">조회 시각 {latestFetchedAt ?? "확인 불가"}</p>
          </div>
        </div>
        <div className="table-wrap">
          <table className="trades" aria-label="계정별 잔여 포지션">
            <TableHeaders />
            <tbody>
              {visibleRows.map((row) => (
                <PositionRow
                  key={`${row.accountId}-${row.symbol}-${row.position.side}`}
                  row={row}
                  onClose={(target) => {
                    setCloseOutcome(null);
                    setCloseTarget(target);
                  }}
                />
              ))}
              {unsupported.map((item) => (
                <tr key={item.accountId} data-testid="account-positions-unsupported">
                  <td colSpan={11}>
                    {item.accountLabel} ·{" "}
                    {UNSUPPORTED_BODY[item.reason ?? ""] ??
                      "포지션 조회 조건을 확인하지 못했습니다."}
                  </td>
                </tr>
              ))}
              {failed.map((item) => (
                <tr key={`failed-${item.accountId}`} data-testid="account-positions-account-error">
                  <td colSpan={11}>
                    {item.accountLabel} · <strong>포지션을 불러오지 못했습니다.</strong>{" "}
                    {item.hasStaleData
                      ? "위에 보이는 이 계정의 값은 마지막으로 성공한 조회 결과이며 최신이 아닙니다."
                      : "이 계정에 남은 포지션이 있는지 확인하지 못했습니다."}{" "}
                    <button className="btn btn-xs btn-ghost" type="button" onClick={item.retry}>
                      다시 시도
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <ScopeFootnote settleCoins={settleCoins} truncated={truncated} />
      </div>
      <Dialog
        open={closeTarget !== null}
        onOpenChange={(open) => {
          if (!open) {
            setCloseOutcome(null);
            setCloseTarget(null);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>포지션 청산</DialogTitle>
            <DialogDescription>
              이 작업은 {closeTarget?.symbol}의 거래소 계정 단위 순 포지션을 평탄화하는 감소전용
              시장가 주문을 냅니다. 주문 원장에는 이 계정·심볼로 만든 가장 최근 세션의 전략으로
              기록됩니다. 그 세션이 아직 활성이면 다음 평가에서 다시 진입할 수 있으며, 수동 청산은
              봇을 중단하지 않습니다. 주문은 접수 후 비동기로 체결되므로 결과는 §05 주문 원장에서
              확인하세요.
            </DialogDescription>
          </DialogHeader>
          <CloseOutcomePanel outcome={closeOutcome} />
          <DialogFooter className="gap-2">
            {closeOutcome !== null && isAccepted(closeOutcome) ? (
              // 주문은 이미 나갔다. 남은 동작은 「읽었다」뿐이고 재제출은 오답이다.
              <Button
                variant="outline"
                onClick={() => {
                  setCloseOutcome(null);
                  setCloseTarget(null);
                }}
              >
                확인
              </Button>
            ) : (
              <>
                <Button
                  variant="outline"
                  onClick={() => setCloseTarget(null)}
                  disabled={closePosition.isPending}
                >
                  취소
                </Button>
                <Button
                  variant="destructive"
                  onClick={() => void handleClose()}
                  disabled={closePosition.isPending}
                >
                  청산 실행
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

function ScopeFootnote({
  settleCoins,
  truncated,
}: {
  settleCoins: ReadonlySet<string>;
  truncated: boolean;
}) {
  if (settleCoins.size === 0) return null;
  return (
    <>
      {/* 거래소가 "더 있다"(nextPageCursor)고 말했는데 우리는 한 페이지만 읽는다.
          조용히 자르면 "이게 전부" 라는 거짓말이 된다. */}
      {truncated ? (
        <p className="table-foot-note">
          거래소가 더 많은 포지션이 있다고 응답했습니다. 이 표는 첫 200건만 보여줍니다.
        </p>
      ) : null}
      <p className="table-foot-note">
        {[...settleCoins].join(", ")} 정산 선물(무기한·만기물)만 조회합니다. 다른 정산통화나 인버스
        계약의 포지션은 이 표에 나타나지 않습니다.
      </p>
    </>
  );
}
