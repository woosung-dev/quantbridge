import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

import { isRestrictedCountry } from "@/lib/geo";

// 공개 라우트 — Clerk 인증 불필요
const isPublicRoute = createRouteMatcher([
  "/",
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/api/webhooks/(.*)",
  "/not-available",
  // Sprint 11 Phase B — 법무 페이지는 인증 불필요
  "/disclaimer",
  "/terms",
  "/privacy",
]);

// Sprint 11 Phase A/B — geo-block 제외 라우트 (landing, 법무, webhook 은 모든 지역 표시).
const isGeoExemptRoute = createRouteMatcher([
  "/",
  "/not-available",
  "/disclaimer",
  "/terms",
  "/privacy",
  "/api/webhooks/(.*)",
]);

export default clerkMiddleware(async (auth, req) => {
  // Sprint 11 Phase A L2 — Cloudflare CF-IPCountry / Vercel X-Vercel-IP-Country 기반 redirect.
  // L1 (WAF) 이 이미 차단한 요청은 이 지점까지 오지 않음. L3 (Clerk webhook) 은 signup 시점 차단.
  const country =
    req.headers.get("CF-IPCountry") ?? req.headers.get("X-Vercel-IP-Country") ?? null;
  if (isRestrictedCountry(country) && !isGeoExemptRoute(req)) {
    const url = req.nextUrl.clone();
    url.pathname = "/not-available";
    return NextResponse.redirect(url);
  }

  if (!isPublicRoute(req)) {
    await auth.protect();
  }
});

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
