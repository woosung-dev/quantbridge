// Better Auth 세션 검증 + geo-block 미들웨어 (Next.js 16 proxy.ts, 구 middleware.ts · ADR-034).
// 공개 라우트가 아닌 모든 요청에서 세션을 **DB 까지 검증**하고, 지정 국가는 /not-available 로,
// 로그인된 사용자의 '/' 접근은 /strategies 로 리다이렉트한다.
import { getSessionCookie } from "better-auth/cookies";
import { NextResponse, type NextRequest } from "next/server";

import { auth } from "@/lib/auth";
import { isRestrictedCountry } from "@/lib/geo";
import { createRouteMatcher } from "@/lib/route-matcher";

// 공개 라우트 — 인증 불필요
const isPublicRoute = createRouteMatcher([
  "/",
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/api/webhooks/(.*)",
  // ADR-034 — Better Auth 자신의 엔드포인트. 여기에 인증을 걸면 로그인이 자기 자신을 막는다.
  "/api/auth/(.*)",
  "/not-available",
  // Sprint 11 Phase B — 법무 페이지는 인증 불필요
  "/disclaimer",
  "/terms",
  "/privacy",
  // Sprint 11 Phase C — Waitlist signup 은 로그인 이전 단계
  "/waitlist",
  // [BL-072] 초대 링크도 로그인 **이전** 단계다 — 공개가 아니면 초대받은 사람이
  // 로그인 화면으로 튕겨 나가 초대가 성립하지 않는다.
  // ★geo 면제 목록에는 **일부러 넣지 않았다**: 이 링크의 목적지는 가입이고 제한 국가의
  //   가입은 L3(`lib/auth.ts` 의 create 훅)이 어차피 거부한다. 폼을 채우게 한 뒤 막는 것보다
  //   /not-available 을 먼저 보여주는 쪽이 정직하다(`/waitlist` 와 갈리는 지점이다 —
  //   그쪽은 신청 자체가 목적이라 열람을 허용한다).
  "/invite/(.*)",
  // Sprint 41 Worker H — public read-only backtest share link
  "/share/backtests/(.*)",
  // Sprint 60 S3 BL-269 — /pricing 은 landing #pricing redirect (인증 불필요)
  "/pricing",
  // W3-H — 점검 페이지는 인증(및 백엔드)이 내려가도 렌더돼야 하므로 공개.
  "/maintenance",
  // W3-H — 디자인 캐논 404 프로브. 존재하지 않는 공개 경로라 인증 게이트를 우회한 뒤
  // not-found 를 렌더한다(design-canon-public.spec.ts 가 인증 없이 감사). 실제 페이지는 없다.
  "/qb-canon-404-probe",
]);

// Sprint 11 Phase A/B — geo-block 제외 라우트 (landing, 법무, webhook 은 모든 지역 표시).
const isGeoExemptRoute = createRouteMatcher([
  "/",
  "/not-available",
  "/disclaimer",
  "/terms",
  "/privacy",
  "/api/webhooks/(.*)",
  // ADR-034 — 인증 엔드포인트는 L2 리다이렉트를 태우지 않는다. XHR 이 리다이렉트를 못 따라가
  // 「로그인이 조용히 실패」로 보이기 때문이다. 가입 차단은 **L3**(`lib/auth.ts` 의 create 훅)이
  // 담당한다 — /waitlist 와 같은 「BE 가 최종 차단」 패턴이다.
  "/api/auth/(.*)",
  // Sprint 11 Phase C — Waitlist 는 restricted country 도 열람 가능 (BE 가 최종 차단).
  "/waitlist",
  // Sprint 41 Worker H — share link 는 모든 지역 view 가능 (외부 viral 흐름).
  "/share/backtests/(.*)",
  // Sprint 60 S3 BL-269 — /pricing 도 모든 지역 열람 가능
  "/pricing",
  // W3-H — 점검 페이지는 모든 지역에서 표시(restricted country 도 서비스 상태는 봐야 함).
  "/maintenance",
]);

export default async function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // Sprint 11 Phase A L2 — Cloudflare CF-IPCountry / Vercel X-Vercel-IP-Country 기반 redirect.
  // L1 (WAF) 이 이미 차단한 요청은 이 지점까지 오지 않음. L3 (가입 훅) 은 signup 시점 차단.
  const country = req.headers.get("CF-IPCountry") ?? req.headers.get("X-Vercel-IP-Country") ?? null;
  if (isRestrictedCountry(country) && !isGeoExemptRoute(pathname)) {
    const url = req.nextUrl.clone();
    url.pathname = "/not-available";
    return NextResponse.redirect(url);
  }

  if (!isPublicRoute(pathname)) {
    // ★여기는 **완전 검증**이다 — `getSessionCookie` 는 쿠키의 존재만 보므로(공식 문서가
    //   "THIS IS NOT SECURE!" 라고 명시한다) 인증 게이트로 쓰지 않는다.
    const session = await auth.api.getSession({ headers: req.headers });
    if (!session) {
      const url = req.nextUrl.clone();
      url.pathname = "/sign-in";
      url.search = "";
      url.searchParams.set("redirect_url", `${pathname}${req.nextUrl.search}`);
      return NextResponse.redirect(url);
    }
    return NextResponse.next();
  }

  // Sprint 60 S3 BL-262 — authed user "/" 접근 시 /strategies redirect (post-signin stuck 방지).
  // ★이것은 보안 게이트가 아니라 **UX 리다이렉트**다. 그래서 쿠키 존재만 보는 빠른 판을 쓴다 —
  //   위조 쿠키로 얻는 것은 `/strategies` 로 보내지는 것뿐이고 그 페이지는 다시 완전 검증을 탄다.
  //   공개 라우트에서 DB 를 안 치는 것이 목적이다(CI 의 공개 e2e 는 DB 없이 돈다).
  if (pathname === "/" && getSessionCookie(req)) {
    const url = req.nextUrl.clone();
    url.pathname = "/strategies";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
