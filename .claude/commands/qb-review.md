이 프로젝트의 변경 사항을 리뷰하라.

먼저 다음 문서들을 읽어라:

- `AGENTS.md` (루트 — Golden Rules · 개발 원칙)
- `CONTEXT.md` (도메인 헌법 — 용어/관계 SSOT)
- `apps/api/AGENTS.md` (BE — 3-Layer · Decimal-first · Celery prefork-safe)
- `apps/web/AGENTS.md` (FE — FSD Lite · Hooks H-1~H-3 · Next.js 16)

그런 다음 변경된 파일들을 확인하고, 아래 체크리스트로 검증하라:

## 체크리스트

1. **아키텍처 준수**: BE는 3-Layer(router/service/repository — AsyncSession은 Repository만 보유), FE는 FSD Lite(화면 컴포넌트는 `features/<domain>/components/`, ADR-035)를 따르고 있는가?
2. **기술 스택 준수**: `docs/adr/`(ADR)에 정의된 기술 선택을 벗어나지 않았는가? (예: pine_v2 인터프리터 — `exec`/`eval` 금지, Better Auth JWKS, Zod v4)
3. **테스트 존재**: 새로운 기능에 대한 테스트가 작성되어 있는가? (service mutation은 commit-spy 테스트 포함 — LESSON-019)
4. **Golden Rules**: 시크릿 하드코딩 금지(SecretStr) · Repository 밖 DB 접근 금지 · `.env.example` 밖 env 참조 금지를 위반하지 않았는가?
5. **표준 러너 통과**: `ruff` / `pytest`(BE) · `biome` / `tsc` / `vitest`(FE)가 에러 없이 통과하는가?

## 출력 형식

| 항목           | 결과  | 비고   |
| -------------- | ----- | ------ |
| 아키텍처 준수  | ✅/❌ | {상세} |
| 기술 스택 준수 | ✅/❌ | {상세} |
| 테스트 존재    | ✅/❌ | {상세} |
| Golden Rules   | ✅/❌ | {상세} |
| 표준 러너 통과 | ✅/❌ | {상세} |

위반 사항이 있으면 수정 방안을 구체적으로 제시하라.

> 깊은 리뷰(차원별 병렬 서브에이전트 + 다수결 검증)가 필요하면 `/review-code`를 써라.
