// 테스트 주문 폼 zod 스키마 — sizing 택일(수량 ↔ risk%) + bracket TP/SL + reduce-only 검증.

import { z } from "zod/v4";

// 양수 Decimal 문자열 판정 — 수량/TP/SL/risk%/청산가 미리보기 공용.
export function isPositiveDecimalString(v: string): boolean {
  if (!/^\d*\.?\d+$/.test(v)) return false;
  return Number(v) > 0;
}

// 부호 있는 Decimal 문자열 — 실현 손익은 음수가 정상이고 0(브레이크이븐)도 유효하다.
export function isSignedDecimalString(v: string): boolean {
  if (!/^-?\d*\.?\d+$/.test(v)) return false;
  return Number.isFinite(Number(v));
}

// Wave 2 — sizing 택일 + bracket TP/SL + reduce-only.
//
// BL-474 — risk% 모드는 "서버가 수량을 계산" 하는 모드가 아니었다. 백엔드
// `_validate_position_size` 는 **상한만 검사**하고(자본×risk% ÷ |진입가−손절가|),
// 수량을 만들어내지 않는다. 게다가 stop 이 없으면 조용히 skip 한다. 그래서
// 모드를 실제 동작에 맞춰 재정의한다 — 수량과 손절가를 모두 요구하고, risk% 는
// 그 수량이 넘으면 안 되는 **상한**으로 쓴다. 진짜 서버 사이징은 별도 BL.
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
    // BL-474 — 청산 주문의 전략 추정 손익. 파서(`webhook.py`)는 이미 읽고 있었고
    // 다이얼로그만 안 보냈다. 이게 있어야 "추정"(synced_at NULL) 상태가 만들어져
    // 출처 라벨 두 칩이 서로 다른 값을 보인다.
    realized_pnl: z.string().default(""),
  })
  .superRefine((data, ctx) => {
    // 수량은 두 모드 모두 필수 — risk% 는 상한이지 생성기가 아니다.
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
    if (data.sizing_mode === "risk_percent") {
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
      // 손절가 없이는 서버가 상한을 계산할 수 없어 가드가 조용히 skip 된다
      // (`order_service.py` risk_sizing_skip_no_stop). 통과처럼 보이는 미검증 금지.
      if (data.stop_loss.length === 0) {
        ctx.addIssue({
          code: "custom",
          path: ["stop_loss"],
          message: "리스크 % 상한 검증에는 손절가가 필요합니다.",
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
    if (
      data.realized_pnl.length > 0 &&
      !isSignedDecimalString(data.realized_pnl)
    ) {
      ctx.addIssue({
        code: "custom",
        path: ["realized_pnl"],
        message: "실현 손익은 숫자여야 합니다 (손실은 음수).",
      });
    }
  });

export type TestOrderFormValues = z.infer<typeof TEST_ORDER_FORM_SCHEMA>;
