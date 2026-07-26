// 테스트 주문 webhook 발송 money-path — payload 조립 + HMAC 서명 + raw fetch.
//
// 보안 trade-off (dogfood-only):
// - sessionStorage 캐시된 webhook secret 으로 browser-side HMAC 서명 → 외부 노출 금지.
// - apiFetch helper 우회 — body 직렬화 drift 방지 위해 raw fetch + 단일 bodyStr 사용.
//   (HMAC 입력과 fetch body 가 반드시 동일 byte 여야 한다.)

import { getApiBase, readErrorBody } from "@/lib/api-base";

import type { TestOrderFormValues } from "./test-order-schema";

// Sprint 14 Phase B-3 — getApiBase helper 통합 (3 곳 일관성 + trailing slash strip).
const API_BASE_URL = getApiBase();

// ArrayBuffer → lowercase hex string. Python `.hexdigest()` 호환.
function bufferToHex(buf: ArrayBuffer): string {
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export async function computeHmacSha256Hex(
  secret: string,
  bodyStr: string,
): Promise<string> {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sigBuf = await crypto.subtle.sign(
    "HMAC",
    key,
    encoder.encode(bodyStr),
  );
  return bufferToHex(sigBuf);
}

/**
 * 폼 값 → webhook payload. 기본 5필드 순서 보존(symbol/side/type/quantity/
 * exchange_account_id) — 기존 HMAC golden vector + body 정확매칭 테스트 유지.
 * optional 필드는 값이 있을 때만, 항상 **뒤에** append (body drift 차단).
 *
 * BL-474 — quantity 는 두 모드 모두 전송한다. 백엔드 `_validate_position_size`
 * 는 수량을 계산하지 않고 상한만 검사하므로, risk_percent 는 quantity 를 대체하는
 * 값이 아니라 그것을 검증하는 상한이다.
 */
export function buildTestOrderPayload(
  values: TestOrderFormValues,
): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    symbol: values.symbol,
    side: values.side,
    type: "market",
    quantity: values.quantity,
    exchange_account_id: values.exchange_account_id,
  };
  if (values.sizing_mode === "risk_percent") {
    payload.risk_percent = values.risk_percent;
  }
  if (values.take_profit.length > 0) {
    payload.take_profit = values.take_profit;
  }
  if (values.stop_loss.length > 0) {
    payload.stop_loss = values.stop_loss;
  }
  if (values.reduce_only) {
    payload.reduce_only = true;
  }
  if (values.realized_pnl.length > 0) {
    payload.realized_pnl = values.realized_pnl;
  }
  return payload;
}

export type TestOrderSendResult =
  | { ok: true; orderHint: string | null }
  | { ok: false; message: string };

/** HMAC 서명 → 발송 → 응답 정규화까지의 발송 파이프라인. UI 반응은 호출측 책임. */
export async function sendTestOrder(
  values: TestOrderFormValues,
  secret: string,
): Promise<TestOrderSendResult> {
  // ── 핵심: bodyStr 은 단 1회만 직렬화. HMAC 입력과 fetch body 가 동일 byte. ──
  const bodyStr = JSON.stringify(buildTestOrderPayload(values));

  // Sprint 14 Phase B-1 — WebCrypto error 처리. 구식 브라우저 / non-HTTPS local /
  // SubtleCrypto 미지원 환경에서 unhandled promise rejection 방지.
  let hmacHex: string;
  let idempotencyKey: string;
  try {
    hmacHex = await computeHmacSha256Hex(secret, bodyStr);
    idempotencyKey = crypto.randomUUID();
  } catch (err) {
    const message = err instanceof Error ? err.message : "WebCrypto 처리 실패";
    return {
      ok: false,
      message:
        `암호화 처리 실패: ${message}. ` +
        "브라우저가 WebCrypto (SubtleCrypto) 를 지원하지 않거나 " +
        "HTTPS / localhost 가 아닌 환경입니다.",
    };
  }

  const url = `${API_BASE_URL}/api/v1/webhooks/${values.strategy_id}?token=${hmacHex}&Idempotency-Key=${idempotencyKey}`;

  let res: Response;
  try {
    res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: bodyStr,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "네트워크 오류";
    return { ok: false, message: `네트워크 오류: ${message}` };
  }

  if (res.status === 201) {
    // Sprint 21 BL-093 — success confirmation 강화: order id 마지막 8자 또는
    // client-side idempotency_key 마지막 8자 노출 → 사용자가 OrdersPanel /
    // Bybit Demo UI 와 매칭 가능 (dogfood Day 0 7번 N 해소).
    let orderHint: string | null = null;
    try {
      const body = (await res.json()) as Record<string, unknown> | null;
      const id = body?.id ?? body?.order_id ?? body?.exchange_order_id;
      if (typeof id === "string" && id.length > 0) {
        orderHint = `#${id.slice(-8)}`;
      }
    } catch {
      // body 가 JSON 이 아니거나 빈 응답 — fallback 으로 idempotency_key 사용
    }
    if (!orderHint && idempotencyKey) {
      orderHint = `client #${idempotencyKey.slice(-8)}`;
    }
    return { ok: true, orderHint };
  }

  // Sprint 14 Phase B-4 — error body size cap + JSON detail 정규화.
  // FastAPI HTTPException detail 우선, JSON 아니면 text 8KB cap.
  const detail = await readErrorBody(res);
  let bodyText: string;
  if (detail && typeof detail === "object") {
    const detailField = (detail as { detail?: unknown }).detail;
    if (typeof detailField === "string" && detailField.length > 0) {
      bodyText = detailField;
    } else {
      bodyText = JSON.stringify(detail);
    }
  } else if (typeof detail === "string" && detail.length > 0) {
    bodyText = detail;
  } else {
    bodyText = "응답 본문 없음";
  }
  return { ok: false, message: `요청 실패 (${res.status}): ${bodyText}` };
}
