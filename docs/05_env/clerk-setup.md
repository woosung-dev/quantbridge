# QuantBridge — Clerk 셋업 가이드

> **목적:** Clerk 외부 의존성 설정 절차.
> **SSOT:** Clerk 공식 문서 (https://clerk.com/docs). 본 문서는 QuantBridge 통합 관점.
> 환경 변수: [`env-vars.md`](./env-vars.md) §3

---

## 1. Clerk Application 생성

1. https://dashboard.clerk.com 가입/로그인
2. **Create Application** → 이름 (예: `QuantBridge Dev`)
3. 인증 방법 선택 권장: **Email + Password** + **Google OAuth** (옵션)
4. **Create**

---

## 2. API Keys 발급

생성된 앱 → **API Keys** 메뉴:

| 키 | 환경 변수 | 노출 위치 |
|----|-----------|-----------|
| **Secret key** (`sk_test_...`) | `CLERK_SECRET_KEY` | 백엔드 only — 절대 FE 노출 금지 |
| **Publishable key** (`pk_test_...`) | `CLERK_PUBLISHABLE_KEY` + `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | FE에 노출 가능 |

복사 → `.env.local`의 해당 키에 붙여넣기:
```env
CLERK_SECRET_KEY=sk_test_xxxxx
CLERK_PUBLISHABLE_KEY=pk_test_xxxxx
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxxxx   # 동일값
```

---

## 3. JWT 검증 (백엔드)

QuantBridge 백엔드는 Clerk JWKS endpoint를 사용해 JWT 서명 검증.

- 코드 위치: `backend/src/auth/clerk.py` 또는 `backend/src/auth/dependencies.py`
- JWKS URL: Clerk SDK가 `CLERK_SECRET_KEY` 기반으로 자동 fetch + 캐시
- 검증 항목: signature, exp, iss

> 별도 환경 변수 불필요. `CLERK_SECRET_KEY`만 있으면 SDK가 처리.

---

## 4. Webhook 등록

> Sprint 3에서 user 동기화에 사용. 로컬 개발은 placeholder secret으로 충분 (mock 서명 테스트).
> 실 endpoint는 **공개 URL이 필요** — Sprint 7 배포 시점에 등록.

### 4.1 로컬 개발 (Sprint 3~6)

`.env.local`에 placeholder 유지:
```env
CLERK_WEBHOOK_SECRET=whsec_placeholder_sprint7_real_value
```

테스트 코드는 mock 서명 사용 — 실제 Clerk 서버와 통신하지 않음.

### 4.2 프로덕션 등록 (Sprint 7+)

1. Clerk Dashboard → **Webhooks** → **Endpoints** → **+ Add Endpoint**
2. **Endpoint URL**: `https://<your-domain>/webhooks/clerk`
3. **Subscribe to events**:
   - `user.created`
   - `user.updated`
   - `user.deleted`
4. **Create** → **Signing Secret** 복사 (`whsec_...`)
5. 프로덕션 환경 변수에 `CLERK_WEBHOOK_SECRET` 설정

### 4.3 Webhook 동작

- 백엔드 엔드포인트: `POST /webhooks/clerk`
- 검증: Svix 서명 + timestamp (replay 방지)
- 처리:
  - `user.created` → `User` INSERT
  - `user.updated` → `User` UPDATE
  - `user.deleted` → `User` DELETE (CASCADE → strategies/backtests/...)

상세 흐름: [`../04_architecture/data-flow.md`](../04_architecture/data-flow.md) §5

---

## 5. Frontend Clerk 통합

### 5.1 Clerk SDK 설치

`frontend/package.json`에 이미 포함:
```json
"@clerk/nextjs": "^x.y.z"
```

### 5.2 ClerkProvider 래핑

`frontend/src/app/layout.tsx` (이미 셋업됨):
```tsx
import { ClerkProvider } from "@clerk/nextjs";

export default function RootLayout({ children }) {
  return (
    <ClerkProvider>
      <html>...</html>
    </ClerkProvider>
  );
}
```

### 5.3 환경 변수 확인

`frontend/.env.local`:
```env
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxxxx
```

> `NEXT_PUBLIC_*` prefix가 없으면 클라이언트에서 접근 불가.

---

## 6. dev / prod 인스턴스 분리

| 환경 | Clerk 앱 | 키 prefix |
|------|----------|-----------|
| local / dev | `QuantBridge Dev` | `sk_test_...`, `pk_test_...` |
| staging | (Sprint 7+) `QuantBridge Staging` | 동일 `_test_` 또는 별도 prod |
| production | (Sprint 7+) `QuantBridge Prod` | `sk_live_...`, `pk_live_...` |

> dev/prod 사용자 데이터는 분리됨. 마이그레이션 도구는 Clerk Dashboard 제공.

---

## 7. 검증

### 7.1 백엔드 JWT 검증 동작
```bash
# 1. FE에서 로그인 후 JWT 추출 (브라우저 dev tools → Application → Cookies → __session)
# 2. curl로 보호 엔드포인트 호출
curl -H "Authorization: Bearer <JWT>" http://localhost:8000/auth/me
# 200 + user payload
```

### 7.2 Webhook (로컬 mock)
- 테스트: `cd backend && uv run pytest tests/auth/test_clerk_webhook.py`
- 모든 케이스 pass 확인

### 7.3 Webhook (실제 Clerk → 로컬)
- ngrok 등으로 로컬 8000 포트를 공개 URL로 노출
- Clerk Dashboard에 ngrok URL 등록
- Clerk Dashboard에서 user 생성 → 백엔드 로그에 webhook 수신 확인

---

## 8. 자주 발생하는 문제

### 8.1 JWT 검증 실패 (`auth.invalid_token`)
- `CLERK_SECRET_KEY` 누락/오타
- 토큰 만료 — 새 세션 발급
- 다른 Clerk 인스턴스의 토큰 — dev/prod 키 혼동 확인

### 8.2 Webhook 서명 검증 실패
- `CLERK_WEBHOOK_SECRET` 미설정 또는 잘못된 endpoint의 secret
- timestamp drift — 서버 시간 동기화 (NTP)

### 8.3 FE에서 `Missing Publishable Key`
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` 미설정
- prefix 누락 (`NEXT_PUBLIC_` 필수)
- Next.js 재시작 필요 (env 변경 후)

---

## 9. 참고

- Clerk 공식 Next.js: https://clerk.com/docs/quickstarts/nextjs
- Clerk 공식 FastAPI: https://clerk.com/docs/quickstarts/fastapi (또는 백엔드 SDK 문서)
- Svix 서명 검증: https://docs.svix.com/receiving/verifying-payloads/how
- 본 프로젝트 백엔드 코드: `backend/src/auth/`

---

## 변경 이력

- **2026-04-16** — 초안 작성 (Sprint 5 Stage A)
