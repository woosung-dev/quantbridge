// FastAPI 백엔드와 통신하는 fetch 기반 얇은 클라이언트.
// 실제 토큰 주입/에러 매핑은 features/[domain]/api.ts에서 Clerk `getToken()`을 래핑해 수행.

import { getApiBase, readErrorBody } from "./api-base";

const API_BASE_URL = getApiBase();

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly detail?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  token?: string | null;
  params?: Record<string, string | number | boolean | undefined>;
}

/**
 * 에러 body 에서 도메인 코드를 찾는다.
 *
 * ★한 겹 파고드는 것이 핵심이다. FastAPI 는 `HTTPException(detail={"code": …})` 를
 * `{"detail": {"code": …}}` 로 감싸 내보내므로, 최상위만 보면 도메인 코드는 **한 번도**
 * 도달하지 않고 언제나 `"unknown_error"` 가 된다([BL-671] 원인). 그 함정을 이미 한 호출부가
 * 손으로 우회하고 있었다(`features/alert-rules/components/alert-rule-form.tsx:31-44`) —
 * 지식이 레포에 있었는데 클라이언트에 반영되지 않은 상태였다.
 *
 * 최상위를 먼저 보는 순서는 유지한다. 커스텀 핸들러가 최상위 `code` 를 내는 응답이 생기면
 * 그쪽이 더 구체적이다.
 */
function resolveErrorCode(body: unknown): string {
  if (body && typeof body === "object") {
    if ("code" in body) return String((body as { code: unknown }).code);
    const inner = "detail" in body ? (body as { detail: unknown }).detail : undefined;
    if (inner && typeof inner === "object" && "code" in inner) {
      return String((inner as { code: unknown }).code);
    }
  }
  return "unknown_error";
}

function buildUrl(path: string, params?: RequestOptions["params"]): string {
  const url = new URL(path.startsWith("/") ? path : `/${path}`, API_BASE_URL);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined) continue;
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, token, params, headers, ...rest } = options;
  const res = await fetch(buildUrl(path, params), {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (!res.ok) {
    // Sprint 14 Phase B-4 — error body size cap (8KB) + JSON detail 정규화.
    // 큰 HTML 에러 페이지 (Nginx/Cloudflare) 가 ApiError.detail 에 그대로 흘러가는 위험 회피.
    const detail = await readErrorBody(res);
    throw new ApiError(res.status, resolveErrorCode(detail), `API ${res.status} ${path}`, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/**
 * 사용자에게 보여줄 에러 문구. `ApiError.message` 는 `API 422 /api/v1/…` 라
 * 사람에게 아무것도 알려주지 않는다 — 서버가 보낸 이유가 `detail` 에 있는데
 * 버려지고 있었다.
 *
 * 실측한 두 모양만 다룬다(2026-07-26 dogfood).
 *   FastAPI 검증 422 — `{detail: [{loc, msg, …}]}`
 *     예) `Value error, Cannot normalize symbol: BTCUSDT.P`
 *   도메인 예외    — `{detail: {code, detail}}`
 *
 * Pydantic 이 붙이는 `Value error, ` 접두사는 제거한다. 사용자에게는 잡음이다.
 */
export function describeApiError(err: unknown, fallback = "요청에 실패했습니다"): string {
  if (!(err instanceof ApiError)) {
    return err instanceof Error ? err.message : fallback;
  }
  const body = err.detail;
  const inner =
    body && typeof body === "object" && "detail" in body
      ? (body as { detail: unknown }).detail
      : undefined;

  if (Array.isArray(inner)) {
    const messages = inner
      .map((item) =>
        item && typeof item === "object" && "msg" in item
          ? String((item as { msg: unknown }).msg).replace(/^Value error,\s*/, "")
          : null,
      )
      .filter((m): m is string => Boolean(m));
    if (messages.length > 0) return messages.join(" · ");
  }

  if (inner && typeof inner === "object" && "detail" in inner) {
    const nested = (inner as { detail: unknown }).detail;
    if (typeof nested === "string" && nested) return nested;
  }
  if (typeof inner === "string" && inner) return inner;

  return err.message || fallback;
}
