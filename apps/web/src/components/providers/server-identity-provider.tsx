"use client";

// SSR 이 이미 확정한 사용자 id 를 클라이언트 첫 렌더에 그대로 넘기는 통로.
//
// ★왜 있나 ([BL-786], 2026-08-17 실측). `useSession()` 은 브라우저에서 `/api/auth/get-session`
//   을 한 번 왕복한 뒤에야 사용자 id 를 준다. 그 사이 `useAuthCtx()` 의 `uid` 는 `"anon"` 이고,
//   React Query 키가 `uid` 를 첫 인자로 갖기 때문에(LESSON-005) **모든 목록·배지 쿼리가 먼저
//   `anon` 키로 한 번 나가고, 세션이 도착하면 진짜 uid 키로 또 한 번 나갔다.** 두 요청은 같은
//   URL·같은 토큰이라 서버는 구분할 수 없고, 화면도 안 깨진다 — 값만 두 배로 나갔다.
//   ★StrictMode 도 컴포넌트 이중 마운트도 아니다: 프로덕션 standalone 빌드에서 동일하게
//   재현됐고 DOM 에는 셸이 정확히 한 벌이었다.
//
// 서버는 `getServerAuth()` 로 이미 같은 값을 알고 있으므로, 그것을 첫 렌더에 주면 키가 흔들리지
// 않는다. 세션이 도착한 **뒤에는** 항상 세션 쪽이 정본이다 — 로그아웃이 여기 값에 가려지면 안 된다.
import { createContext, useContext, type ReactNode } from "react";

const ServerIdentityContext = createContext<string | null>(null);

export function ServerIdentityProvider({
  userId,
  children,
}: {
  userId: string | null;
  children: ReactNode;
}) {
  return (
    <ServerIdentityContext.Provider value={userId}>{children}</ServerIdentityContext.Provider>
  );
}

/** SSR 이 준 사용자 id. Provider 밖(공개 라우트)에서는 `null`. */
export function useServerIdentity(): string | null {
  return useContext(ServerIdentityContext);
}
