"use client";

// 주문 상세 — 목록이 이미 가진 OrderResponse 를 그대로 표시한다. 단건 조회를 추가하지 않는다.

import type { ReactNode } from "react";
import { CopyIcon } from "lucide-react";

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
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { formatDate, formatTimeSeconds } from "@/features/backtest/utils";
import {
  ORDER_CSV_EXTRA_HEADER,
  ORDER_FLAG_LABEL,
  ORDER_MARGIN_MODE_LABEL,
  ORDER_REALIZED_PNL_SOURCE_LABEL,
  ORDER_SIDE_LABEL,
  ORDER_STATE_LABEL,
  ORDER_TRIGGER_BY_LABEL,
  ORDER_TRIGGER_DIRECTION_LABEL,
  ORDER_TYPE_LABEL,
} from "@/features/trading/labels";
import type { Order } from "@/features/trading/schemas";
import { useMediaQuery } from "@/hooks/use-media-query";
import { EMPTY_CELL } from "@/lib/labels";

import { displayRealizedPnl, realizedPnlSource } from "./orders-blotter";

type OrderDetailDrawerProps = {
  order: Order | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

type DetailItem = {
  label: string;
  value: ReactNode;
  className?: string;
};

type OrderDetailBodyProps = {
  order: Order;
  onClose: () => void;
  variant: "sheet" | "dialog";
};

function formatOrderDateTime(value: string | null): string {
  if (value == null) return EMPTY_CELL;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${formatDate(value)} ${formatTimeSeconds(value)} UTC`;
}

function DetailList({ items }: { items: readonly DetailItem[] }) {
  return (
    <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {items.map((item) => (
        <div
          key={item.label}
          className={`border-border bg-muted/30 min-w-0 rounded-lg border p-3 ${item.className ?? ""}`}
        >
          <dt className="text-muted-foreground text-xs">{item.label}</dt>
          <dd className="text-foreground mt-1 text-sm break-words">{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function CopyableId({ label, value }: { label: string; value: string }) {
  const handleCopy = () => {
    if (typeof navigator === "undefined" || navigator.clipboard == null) return;
    void navigator.clipboard.writeText(value).catch(() => undefined);
  };

  return (
    <span className="flex min-w-0 items-center gap-2">
      <code className="min-w-0 flex-1 font-mono text-xs break-all">{value}</code>
      <button
        className="btn btn-ghost btn-xs shrink-0"
        type="button"
        aria-label={`${label} 복사`}
        title={`${label} 복사`}
        onClick={handleCopy}
      >
        <CopyIcon aria-hidden="true" />
        복사
      </button>
    </span>
  );
}

function OrderDetailBody({ order, onClose, variant }: OrderDetailBodyProps) {
  const HeaderEl = variant === "sheet" ? SheetHeader : DialogHeader;
  const TitleEl = variant === "sheet" ? SheetTitle : DialogTitle;
  const DescriptionEl = variant === "sheet" ? SheetDescription : DialogDescription;
  const FooterEl = variant === "sheet" ? SheetFooter : DialogFooter;
  const orderState = ORDER_STATE_LABEL[order.state].label;
  const triggerBy =
    order.trigger_by == null
      ? EMPTY_CELL
      : (ORDER_TRIGGER_BY_LABEL[order.trigger_by] ?? "거래소 기준가");
  const triggerDirection =
    order.trigger_direction == null
      ? EMPTY_CELL
      : (ORDER_TRIGGER_DIRECTION_LABEL[order.trigger_direction] ?? "조건 방향 미상");

  return (
    <>
      <HeaderEl>
        <TitleEl>{order.symbol} 주문 상세</TitleEl>
        <DescriptionEl>목록에 이미 불러온 주문 원장 정보를 표시합니다.</DescriptionEl>
      </HeaderEl>

      <section className="space-y-3" aria-labelledby="order-detail-summary">
        <h3 id="order-detail-summary" className="text-sm font-medium">
          주문 정보
        </h3>
        <DetailList
          items={[
            { label: "주문 ID", value: <CopyableId label="주문 ID" value={order.id} /> },
            {
              label: "전략 ID",
              value:
                order.strategy_id == null ? (
                  EMPTY_CELL
                ) : (
                  <CopyableId label="전략 ID" value={order.strategy_id} />
                ),
            },
            {
              label: "거래소 계정 ID",
              value:
                order.exchange_account_id == null ? (
                  EMPTY_CELL
                ) : (
                  <CopyableId label="거래소 계정 ID" value={order.exchange_account_id} />
                ),
            },
            { label: "거래소 주문번호", value: order.exchange_order_id ?? EMPTY_CELL },
            { label: "멱등성 키", value: order.idempotency_key ?? EMPTY_CELL },
            { label: "상태", value: orderState },
            {
              label: "주문 유형",
              value: order.type == null ? EMPTY_CELL : ORDER_TYPE_LABEL[order.type],
            },
            { label: "주문 방향", value: ORDER_SIDE_LABEL[order.side] },
            { label: "수량", value: order.quantity },
            { label: "주문가", value: order.price ?? EMPTY_CELL },
          ]}
        />
      </section>

      <section className="space-y-3" aria-labelledby="order-detail-execution">
        <h3 id="order-detail-execution" className="text-sm font-medium">
          제출·체결
        </h3>
        <DetailList
          items={[
            { label: "생성 시각", value: formatOrderDateTime(order.created_at) },
            { label: "제출 시각", value: formatOrderDateTime(order.submitted_at) },
            // ★거부·취소 주문도 `filled_at` 이 채워진다 — BE 가 그 자리에 **종결 시각**을 쓴다
            //   (rejected 는 `order_repository.py:941-945` 주석으로 문서화 · cancelled 도 실측
            //   431/431, 부분 체결 0 — 2026-08-25 qa-sweep). 그대로 「체결 시각」이라 적으면
            //   체결되지 않은 주문이 체결된 것처럼 보인다(2026-08-15 codex P1 · BL-824).
            //   기록 의미론 자체(정본 수리)는 [BL-826].
            {
              label:
                order.state === "rejected"
                  ? "실패 시각"
                  : order.state === "cancelled"
                    ? "취소 시각"
                    : "체결 시각",
              value: formatOrderDateTime(order.filled_at),
            },
            { label: "체결가", value: order.filled_price ?? EMPTY_CELL },
            { label: "체결 수량", value: order.filled_quantity ?? EMPTY_CELL },
            // ★손익 노출 판정은 **목록과 같은 SSOT** 를 쓴다. 직접 `order.realized_pnl` 을 읽으면
            //   rejected/cancelled 에 남은 pine_v2 **추정치**가 확정 손실처럼 보인다 — 목록이
            //   이미 그 이유로 `displayRealizedPnl` 을 통과시키고 있었는데 드로어만 우회했다.
            { label: "실현 손익", value: displayRealizedPnl(order) ?? EMPTY_CELL },
            // ★출처는 **말로 적는다** ([BL-458], 2026-08-16). 종전에는 아래 「손익 확정 시각」이
            //   비어 있다는 것으로 사용자가 「추정값이구나」를 추론해야 했다 — 목록은 같은 판정을
            //   `ORDER_REALIZED_PNL_SOURCE_LABEL` 로 적고 있었으므로 상세만 말을 안 한 셈이다.
            //   ★손익을 안 보여줄 때는 출처도 적지 않는다 — 목록의 규칙과 같다. 안 그러면
            //   손익이 빈 rejected 주문에 「추정」이 붙어 없는 숫자에 등급을 매긴다.
            {
              label: ORDER_CSV_EXTRA_HEADER.realizedPnlSource,
              value:
                displayRealizedPnl(order) != null
                  ? ORDER_REALIZED_PNL_SOURCE_LABEL[realizedPnlSource(order)]
                  : EMPTY_CELL,
            },
            {
              label: "손익 확정 시각",
              value: formatOrderDateTime(order.realized_pnl_synced_at),
            },
            {
              label: "오류 메시지",
              value: order.error_message ?? EMPTY_CELL,
              className: "sm:col-span-2",
            },
          ]}
        />
      </section>

      <section className="space-y-3" aria-labelledby="order-detail-protection">
        <h3 id="order-detail-protection" className="text-sm font-medium">
          조건·보호 설정
        </h3>
        <DetailList
          items={[
            {
              label: "레버리지",
              value: order.leverage == null ? EMPTY_CELL : `${order.leverage}x`,
            },
            {
              label: "증거금 모드",
              value:
                order.margin_mode == null ? EMPTY_CELL : ORDER_MARGIN_MODE_LABEL[order.margin_mode],
            },
            { label: "감소전용", value: order.reduce_only ? ORDER_FLAG_LABEL.reduceOnly : "일반" },
            { label: "트리거 가격", value: order.trigger_price ?? EMPTY_CELL },
            { label: "트리거 기준가", value: triggerBy },
            { label: "트리거 방향", value: triggerDirection },
            { label: "익절", value: order.take_profit ?? EMPTY_CELL },
            { label: "손절", value: order.stop_loss ?? EMPTY_CELL },
            { label: "추적손절", value: order.trailing_stop ?? EMPTY_CELL },
            { label: "OCO 그룹 ID", value: order.oco_group_id ?? EMPTY_CELL },
          ]}
        />
      </section>

      <FooterEl>
        <Button variant="ghost" onClick={onClose}>
          닫기
        </Button>
      </FooterEl>
    </>
  );
}

export function OrderDetailDrawer({ order, open, onOpenChange }: OrderDetailDrawerProps) {
  // edit/delete-dialog.tsx 와 같은 경계: 정확히 768px도 bottom sheet 다.
  const isMobile = useMediaQuery("(max-width: 768px)");

  if (order == null) return null;

  const body = (
    <OrderDetailBody
      order={order}
      onClose={() => onOpenChange(false)}
      variant={isMobile ? "sheet" : "dialog"}
    />
  );

  if (isMobile) {
    return (
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent className="max-h-[85dvh] overflow-y-auto">{body}</SheetContent>
      </Sheet>
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85dvh] overflow-y-auto sm:max-w-3xl">{body}</DialogContent>
    </Dialog>
  );
}
