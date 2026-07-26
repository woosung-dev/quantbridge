# .env.example 스타터

> 새 프로젝트 시작 시 아래 내용을 프로젝트 루트의 `.env.example`로 복사하세요.
> 사용하지 않는 항목은 제거하고, 프로젝트에 맞게 수정합니다.

---

## 기본 스택 (Next.js + FastAPI + Clerk + Neon + R2)

```bash
# Auth (Clerk)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=

# Database (Neon PostgreSQL)
DATABASE_URL=

# Storage (Cloudflare R2)
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=
R2_PUBLIC_URL=

# AI
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# App
NEXT_PUBLIC_API_URL=
```
