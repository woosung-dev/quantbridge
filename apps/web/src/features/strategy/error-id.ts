// 서버가 만든 **상관 ID** 를 화면으로 꺼낸다.
//
// ★배경 — BE 의 `_opaque()`(`strategy/router.py` · `strategy/convert/router.py`)는 SDK 예외
// 문자열을 응답에서 지우는 대신 `error_id` 를 만들어 로그와 잇는다([BL-772]). 그런데 FE 는
// 이 값을 **전역에서 한 번도 쓰지 않았다**(2026-08-27 실측: `grep -rn error_id src/` → 0건).
// 지우기만 하고 ID 를 버리면 사용자 문의를 추적할 수 없다 — `_opaque` 의 docstring 이 명시한
// 설계 의도가 FE 에서 깨져 있던 것이다.

import { ApiError } from "@/lib/api-client";

/** `{detail: {code, detail, error_id}}` 에서 상관 ID 를 꺼낸다. 없으면 undefined. */
export function errorIdOf(err: unknown): string | undefined {
  if (!(err instanceof ApiError)) return undefined;
  const body = err.detail;
  if (!body || typeof body !== "object" || !("detail" in body)) return undefined;
  const inner = (body as { detail: unknown }).detail;
  if (!inner || typeof inner !== "object" || !("error_id" in inner)) return undefined;
  const id = (inner as { error_id: unknown }).error_id;
  return typeof id === "string" && id ? id : undefined;
}
