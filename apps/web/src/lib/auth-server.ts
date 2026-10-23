// 서버 인증 헬퍼 — 화면 신원 조회와 FastAPI prefetch용 JWT 발급을 분리한다(ADR-034).
import "server-only";

import { cache } from "react";
import { headers } from "next/headers";

import { auth } from "@/lib/auth";

export interface ServerAuth {
  userId: string | null;
  /** FastAPI 로 보낼 Bearer JWT. 세션이 없으면 `null`. */
  token: string | null;
}

// 공개 랜딩에서도 사용하므로 인증 저장소 장애는 익명으로 강등한다. 보호 라우트의
// 완전 검증은 proxy.ts가 담당한다. 쿠키 존재 자체를 인증 성공으로 읽지 않는다.
export const getServerSession = cache(async (): Promise<{ userId: string | null }> => {
  try {
    const h = await headers();
    if (!h.get("cookie")) return { userId: null };
    const session = await auth.api.getSession({ headers: h });
    return { userId: session?.user.id ?? null };
  } catch {
    return { userId: null };
  }
});

/** 현재 요청의 신원과 API 토큰. 세션 조회는 레이아웃과 요청 단위 캐시를 공유한다. */
export const getServerAuth = cache(async (): Promise<ServerAuth> => {
  try {
    const h = await headers();
    if (!h.get("cookie")) return { userId: null, token: null };
    // 목록 prefetch에서는 세션 확인과 토큰 발급을 병렬로 유지한다(async-parallel).
    const [session, issued] = await Promise.all([
      getServerSession(),
      auth.api.getToken({ headers: h }).catch(() => null),
    ]);
    if (!session.userId) return { userId: null, token: null };
    return { userId: session.userId, token: issued?.token ?? null };
  } catch {
    return { userId: null, token: null };
  }
});
