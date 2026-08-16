// Better Auth 라우트 핸들러 — `/api/auth/*` 전부가 여기로 들어온다(ADR-034).
// ★이 레포의 첫 route handler 다. 그전까지 `apps/web/src/app` 에 `route.ts` 는 0건이었고
//   FE 컨테이너는 DB 커넥션도 없었다 — 그 두 전제가 이 파일과 함께 바뀐다.
import { toNextJsHandler } from "better-auth/next-js";

import { auth } from "@/lib/auth";

export const { GET, POST } = toNextJsHandler(auth);
