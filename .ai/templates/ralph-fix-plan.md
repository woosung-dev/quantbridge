# fix_plan.md 템플릿 (Ralph Loop)

> Stage 4 Sprint 계획에서 이 파일을 생성합니다.
> 에이전트는 위에서부터 순차 실행하며 완료 시 `[x]`로 표시합니다.
>
> 프로젝트 루트에 `fix_plan.md`로 저장하세요.

---

## 작성 규칙

| 규칙 | 설명 |
|------|------|
| 1태스크 = 1 체크박스 | 에이전트가 1회 반복에 1개만 처리 |
| 파일 경로 명시 | 에이전트가 즉시 작업 위치 파악 |
| 테스트 파일 명시 | TDD guardrail 강제 |
| 의존성 순서 배치 | 위에서 아래로 실행되므로, 선행 작업을 위에 배치 |
| 완료 조건 명시 | 에이전트가 "끝"을 판단할 수 있는 구체적 기준 |

### 상태 표시

- `[ ]` — 미완료 (에이전트가 선택)
- `[x]` — 완료 (에이전트가 표시)
- `[blocked]` — 진행 불가 (에이전트가 사유와 함께 표시, 다음 태스크로 건너뜀)

---

## 예시

```markdown
# fix_plan.md — Sprint 1

## 기반 코드 (우선순위 높음)
- [ ] `src/lib/db.ts` — PostgreSQL 연결 유틸 구현 (connection pool). 테스트: `tests/lib/db.test.ts`
- [ ] `src/lib/auth.ts` — JWT 토큰 발급/검증 함수. 테스트: `tests/lib/auth.test.ts` (발급, 검증, 만료 3케이스)

## API 엔드포인트 (우선순위 중간)
- [ ] `src/api/users/route.ts` — 사용자 CRUD API. specs/API-001.md 참조. 테스트: `tests/api/users.test.ts`
- [ ] `src/api/auth/route.ts` — 로그인/회원가입 API. specs/API-002.md 참조. 테스트: `tests/api/auth.test.ts`

## UI 컴포넌트 (우선순위 낮음)
- [ ] `src/components/LoginForm.tsx` — 로그인 폼. specs/SCR-001.md 참조. Storybook 스냅샷 포함
- [ ] `src/components/UserList.tsx` — 사용자 목록 테이블. specs/SCR-002.md 참조. 페이지네이션 포함
```

---

## 팁

### 좋은 태스크 vs 나쁜 태스크

```markdown
# 나쁨 — 너무 모호
- [ ] 로그인 기능 구현
- [ ] API 만들기

# 좋음 — 구체적, 검증 가능
- [ ] `src/auth/login.ts` — email/password 로그인 함수. bcrypt 비교 후 JWT 반환. 테스트: `tests/auth/login.test.ts` (성공, 잘못된 비밀번호, 미존재 사용자 3케이스)
```

### 태스크 크기 기준

- **너무 작음:** 타입 1개 정의, import 추가 → 묶어서 하나로
- **적절함:** 함수 1개 + 테스트, 컴포넌트 1개 + 테스트, API 엔드포인트 1개
- **너무 큼:** "전체 인증 시스템 구현" → 3~5개로 분할
