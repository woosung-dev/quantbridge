// 청산 응답/에러 → 화면이 그릴 수 있는 하나의 상태.
//
// ★왜 별도 모듈인가. 두 테이블(`open-positions-table` · `account-positions-table`)이
//   같은 갈래를 각자 구현하면 곧 갈라진다 — 실제로 그렇게 갈라져 있었다(한쪽만
//   `describeApiError` 를 썼다). 판정은 여기 한 곳에 두고 표현은 패널 하나가 맡는다.
//
// ★갈래는 CLI(`apps/api/scripts/live_session_admin.py:374-423`)의 종료 코드와 1:1 이다.
//   rc 0 = clean · rc 3 = blocked_resting · rc 4 = accepted_with_resting|accepted_unknown ·
//   rc 1 = failed. 화면이 CLI 보다 적게 말하면 그것이 [BL-688] 이 지목한 구멍이다.

import { ApiError, describeApiError } from "@/lib/api-client";

import {
  type ClosePositionResponse,
  type RestingEntryOrder,
  RestingEntriesConflictSchema,
} from "./schemas";

export type CloseOutcome =
  /** 청산 접수 + 잔량 0 + 조회 성공. 화면이 더 말할 것이 없다. */
  | { kind: "clean"; orderId: string; state: string }
  /** 청산 접수. 거래소에 미체결 진입이 남아 있다. */
  | { kind: "accepted_with_resting"; orderId: string; state: string; orders: RestingEntryOrder[] }
  /** 청산 접수. 미체결 진입이 있는지 **묻지 못했다**. */
  | { kind: "accepted_unknown"; orderId: string; state: string }
  /** 청산 주문을 내지 않았다 — 포지션이 0인데 진입만 남아 있다. */
  | { kind: "blocked_resting"; message: string; orders: RestingEntryOrder[] }
  /** 그 외 실패. */
  | { kind: "failed"; message: string };

/** 접수는 됐다 = 재제출이 오답인 상태. 화면이 청산 버튼을 감추는 판정에 쓴다. */
export function isAccepted(outcome: CloseOutcome): boolean {
  return outcome.kind === "accepted_with_resting" || outcome.kind === "accepted_unknown";
}

export function outcomeFromResponse(res: ClosePositionResponse): CloseOutcome {
  const base = { orderId: res.order_id, state: res.state };
  // ★두 필드를 **함께** 켜서 보내는 경로는 오늘 서버에 없다 — 조회가 실패하면
  //   `entries = []` 로 리셋하고 플래그를 켠다(`close_service.py:180-182`). 그래서 이
  //   순서는 지금 관측되지 않는다(변이로 확인: 순서를 뒤집어도 시험이 초록이었다).
  //   그럼에도 `unknown` 을 앞에 두는 것은 **우리가 고르는 계약**이다 — 서버가 언젠가
  //   「일부는 읽었고 나머지는 못 읽었다」를 보내게 되면, 목록이 있다는 이유로
  //   「이게 전부다」라고 말해서는 안 된다. 아래 시험이 그 선택을 고정한다.
  if (res.resting_entries_unknown) return { kind: "accepted_unknown", ...base };
  if (res.resting_entries.length > 0) {
    return { kind: "accepted_with_resting", ...base, orders: res.resting_entries };
  }
  return { kind: "clean", ...base };
}

export function outcomeFromError(err: unknown): CloseOutcome {
  const fallback = "청산 요청을 보내지 못했습니다.";
  if (err instanceof ApiError && err.status === 409) {
    // FastAPI 가 `{"detail": <서비스 dict>}` 로 한 겹 감싼다. 같은 409 의 다른 사유는
    // `detail` 이 평문 문자열이라 이 `safeParse` 가 거부한다.
    const inner =
      err.detail && typeof err.detail === "object" && "detail" in err.detail
        ? (err.detail as { detail: unknown }).detail
        : undefined;
    const parsed = RestingEntriesConflictSchema.safeParse(inner);
    if (parsed.success) {
      return {
        kind: "blocked_resting",
        message: parsed.data.detail,
        orders: parsed.data.orders,
      };
    }
  }
  return { kind: "failed", message: describeApiError(err, fallback) };
}
