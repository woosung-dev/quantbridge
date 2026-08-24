// 서버 컴포넌트에서 쓰는 인증 헬퍼 — SSR prefetch 가 FastAPI 를 부를 때 필요한 두 값만 준다.
// ★구 Clerk `auth()` 의 자리다(ADR-034). 반환 형태를 `{ userId, token }` 으로 맞춰 둔 것은
//   호출부 4곳(`app/page.tsx` · `(dashboard)/layout.tsx` · `(dashboard)/{backtests,strategies}/page.tsx`)의 diff 를 줄이려는 것이다.
import "server-only";

import { cache } from "react";
import { headers } from "next/headers";

import { auth } from "@/lib/auth";

export interface ServerAuth {
  userId: string | null;
  /** FastAPI 로 보낼 Bearer JWT. 세션이 없으면 `null`. */
  token: string | null;
}

/**
 * 현재 요청의 세션과 API 토큰을 함께 읽는다.
 *
 * ★실패를 삼킨다 — 랜딩(`/`)처럼 **공개 라우트에서도 불리는** 함수라, DB 가 없는 환경(CI 의 공개
 * e2e)에서 예외가 페이지를 죽이면 안 된다. 인증 게이트는 `proxy.ts` 가 이미 통과시킨 뒤이므로
 * 여기서의 `null` 은 「보호를 뚫었다」가 아니라 「프리페치를 못 했다」는 뜻이다.
 *
 * ★`React.cache` 로 감쌌다(`server-cache-react`) — 한 요청 안에서 두 번 불려도 왕복은 한 번이다.
 */
export const getServerAuth = cache(async (): Promise<ServerAuth> => {
  try {
    const h = await headers();
    // ★두 호출은 서로를 기다리지 않는다(`async-parallel`). 순차로 두면 세션 조회 왕복이
    //   토큰 발급 앞에 그대로 쌓여 SSR prefetch 가 그만큼 늦는다. 세션이 없으면 `getToken`
    //   이 실패하고 아래 catch 가 같은 `{null, null}` 을 낸다 — 결과는 동일하다.
    const [session, issued] = await Promise.all([
      auth.api.getSession({ headers: h }),
      auth.api.getToken({ headers: h }).catch(() => null),
    ]);
    if (!session) return { userId: null, token: null };
    return { userId: session.user.id, token: issued?.token ?? null };
  } catch {
    return { userId: null, token: null };
  }
});
