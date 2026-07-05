// 테스트 주문 폼 zod 스키마 — sizing 택일(수량 ↔ risk%) + bracket TP/SL + reduce-only 검증.

import { z } from "zod/v4";

// 양수 Decimal 문자열 판정 — 수량/TP/SL/risk%/청산가 미리보기 공용.
export function isPositiveDecimalString(v: string): boolean {
  if (!/^\d*\.?\d+$/.test(v)) return false;
  return Number(v) > 0;
}

// Wave 2 — sizing 택일(수량 직접 ↔ risk% 서버 권위) + bracket TP/SL + reduce-only.
// risk_percent 는 W-A `OrderRequest.risk_percent`(Decimal,%) 계약 (미머지 → 서버 사이징은 Phase 3).
export const TEST_ORDER_FORM_SCHEMA = z
  .object({
    strategy_id: z.string().min(1, "전략을 선택하세요."),
    exchange_account_id: z.string().min(1, "거래소 계정을 선택하세요."),
    symbol: z.string().min(1, "심볼을 입력하세요."),
    side: z.enum(["buy", "sell"]),
    sizing_mode: z.enum(["quantity", "risk_percent"]),
    // sizing 택일로 quantity/risk_percent 가 조건부 unmount → RHF 가 값을 제거할 수 있어
    // `.default("")` 로 undefined 를 "" 로 흡수 (없으면 z.string() 이 silent "Required" 발생).
    quantity: z.string().default(""),
    risk_percent: z.string().default(""),
    take_profit: z.string().default(""),
    stop_loss: z.string().default(""),
    reduce_only: z.boolean().default(false),
  })
  .superRefine((data, ctx) => {
    if (data.sizing_mode === "quantity") {
      if (data.quantity.length === 0) {
        ctx.addIssue({
          code: "custom",
          path: ["quantity"],
          message: "수량을 입력하세요.",
        });
      } else if (!isPositiveDecimalString(data.quantity)) {
        ctx.addIssue({
          code: "custom",
          path: ["quantity"],
          message: "수량은 0보다 큰 숫자여야 합니다.",
        });
      }
    } else {
      if (data.risk_percent.length === 0) {
        ctx.addIssue({
          code: "custom",
          path: ["risk_percent"],
          message: "리스크 %를 입력하세요.",
        });
      } else if (
        !isPositiveDecimalString(data.risk_percent) ||
        Number(data.risk_percent) > 100
      ) {
        ctx.addIssue({
          code: "custom",
          path: ["risk_percent"],
          message: "리스크 %는 0 초과 100 이하 숫자여야 합니다.",
        });
      }
    }
    if (data.take_profit.length > 0 && !isPositiveDecimalString(data.take_profit)) {
      ctx.addIssue({
        code: "custom",
        path: ["take_profit"],
        message: "익절가는 0보다 큰 숫자여야 합니다.",
      });
    }
    if (data.stop_loss.length > 0 && !isPositiveDecimalString(data.stop_loss)) {
      ctx.addIssue({
        code: "custom",
        path: ["stop_loss"],
        message: "손절가는 0보다 큰 숫자여야 합니다.",
      });
    }
  });

export type TestOrderFormValues = z.infer<typeof TEST_ORDER_FORM_SCHEMA>;
