// Better Auth 서버 인스턴스 — 이 앱이 인증 서버 본체다(구 Clerk 대체, ADR-034).
// FastAPI 는 여기서 발급한 JWT 를 `/api/auth/jwks` 로 검증한다. 세션 쿠키는 브라우저↔Next 구간
// 전용이고, Next↔FastAPI 구간은 Bearer JWT 다 — 두 구간의 자격증명이 다르다는 점을 헷갈리지 마라.
import { betterAuth } from "better-auth";
import { nextCookies } from "better-auth/next-js";
import { jwt } from "better-auth/plugins/jwt";
import { Pool } from "pg";

import { isRestrictedCountry } from "@/lib/geo";

/** FastAPI 의 오리진. `NEXT_PUBLIC_API_URL` 은 빌드타임 인라인이라 서버에서도 읽힌다. */
function apiBase(): string {
  return (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");
}

// ★테이블은 `public` 스키마에 `auth_` 접두로 둔다(ADR-034 §D3). 스키마 한정 이름(`auth.user`)은
//   Better Auth 문서에 없어 검증할 수 없고, 접두 방식은 alembic 이 DDL 정본을 유지하는 것과 맞는다.
const MODEL = {
  user: "auth_user",
  session: "auth_session",
  account: "auth_account",
  verification: "auth_verification",
  jwks: "auth_jwks",
} as const;

// ★Pool 은 dev 의 hot reload 를 넘어 재사용한다 — 매 리로드마다 새 Pool 을 만들면 커넥션이 샌다.
const globalForPool = globalThis as unknown as { qbAuthPool?: Pool };

function getPool(): Pool {
  if (!globalForPool.qbAuthPool) {
    globalForPool.qbAuthPool = new Pool({
      connectionString: process.env.BETTER_AUTH_DATABASE_URL,
      // 인증 트래픽은 얇다. 소크 워커와 같은 Postgres 를 쓰므로 커넥션을 아낀다.
      max: 5,
    });
  }
  return globalForPool.qbAuthPool;
}

/**
 * 요청 헤더에서 Cloudflare 가 붙인 ISO 3166-1 alpha-2 국가코드를 꺼낸다.
 *
 * ★geo-block L3 은 2026-08-17 까지 **한 번도 발화한 적이 없었다** — Clerk 시절 BE 는
 * `public_metadata.country` 를 읽었는데 그 값을 넣는 코드가 FE 어디에도 없었다(grep 0건).
 * Better Auth 는 Next 안에서 돌아 가입 요청의 헤더를 직접 보므로, 여기가 L3 이 처음으로
 * 실재하게 되는 자리다. 헤더가 없으면 `null` — 차단하지 않는다(로컬 개발·기존 호환).
 */
function countryFromContext(context: { headers?: Headers; request?: Request } | null): string | null {
  const headers = context?.headers ?? context?.request?.headers;
  const raw = headers?.get("cf-ipcountry") ?? headers?.get("x-vercel-ip-country") ?? null;
  if (!raw) return null;
  const code = raw.trim().toUpperCase();
  return code.length === 2 ? code : null;
}

export const auth = betterAuth({
  database: getPool(),
  // ★미설정이면 production 에서 Better Auth 자신이 throw 한다. 개발 기본값에 의존하지 마라.
  secret: process.env.BETTER_AUTH_SECRET,
  baseURL: process.env.BETTER_AUTH_URL,
  emailAndPassword: {
    enabled: true,
    // ★이번 회차는 검증 메일을 켜지 않는다 — Resend 도메인 검증(사용자 수동)이 배포를 막지
    //   않게 하기 위해서다. [BL-072] 와 함께 켠다.
    requireEmailVerification: false,
    minPasswordLength: 8,
  },
  user: {
    modelName: MODEL.user,
    additionalFields: {
      // 서버 소유 필드 — 클라이언트가 보내도 무시된다(`input: false`).
      country: { type: "string", required: false, input: false },
    },
    deleteUser: {
      enabled: true,
      /**
       * ★★**탈퇴가 「돈을 멈추는」 경로다.** 우리 API 가 계정 잠금 · 전략 archive ·
       * 라이브 세션 전량 비활성 · 웹훅 시크릿 revoke 를 한 트랜잭션으로 처리한다
       * (2026-08-15 surface-truth S3 P1).
       *
       * ★**여기서 부르는 이유** — 클라이언트에게 「우리 API 를 먼저, 그다음 deleteUser」
       * 순서를 맡기면 그 순서가 지켜지는지 아무도 보증하지 않는다. `beforeDelete` 는
       * **throw 하면 삭제가 중단**되므로 fail-closed 다: 우리 API 가 실패하면 인증
       * 사용자도 남고, 성공해야만 사라진다. 2026-08-17 codex 적대 리뷰가 이 배선의
       * 부재를 P1 으로 잡았다 — 엔드포인트는 있었고 **부르는 쪽이 없었다.**
       */
      beforeDelete: async (_user, request) => {
        if (!request) throw new Error("계정 삭제 요청 컨텍스트를 읽지 못했습니다.");
        const issued = await auth.api.getToken({ headers: request.headers });
        const token = issued?.token;
        if (!token) throw new Error("계정 삭제에 필요한 토큰을 발급하지 못했습니다.");
        const res = await fetch(`${apiBase()}/api/v1/auth/me`, {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        });
        // 204 만 통과. 그 외에는 **삭제를 진행하지 않는다** — 돈이 안 멈춘 채로
        // 인증 사용자가 사라지는 것이 최악이다.
        if (res.status !== 204) {
          throw new Error(`계정 정리에 실패했습니다 (status ${res.status}). 잠시 후 다시 시도해 주세요.`);
        }
      },
    },
  },
  session: { modelName: MODEL.session },
  account: { modelName: MODEL.account },
  verification: { modelName: MODEL.verification },
  databaseHooks: {
    user: {
      create: {
        before: async (user, context) => {
          const country = countryFromContext(context);
          // geo-block L3 — 제한 국가는 가입 자체를 거부한다(L1 = Cloudflare WAF, L2 = proxy.ts).
          if (isRestrictedCountry(country)) return false;
          return { data: { ...user, country } };
        },
      },
    },
  },
  plugins: [
    jwt({
      schema: { jwks: { modelName: MODEL.jwks } },
      jwt: {
        // FastAPI 가 이 두 값을 그대로 검증한다. 서버 env 와 어긋나면 전건 401 이 된다.
        issuer: process.env.BETTER_AUTH_URL,
        audience: process.env.BETTER_AUTH_URL,
        definePayload: ({ user }) => ({
          email: user.email,
          username: user.name,
          country: (user as { country?: string | null }).country ?? null,
        }),
      },
    }),
    // ★nextCookies 는 반드시 배열의 마지막이어야 한다(공식 문서 명시).
    nextCookies(),
  ],
});
