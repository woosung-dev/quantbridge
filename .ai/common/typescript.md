---
description: TypeScript 코딩 컨벤션
paths:
  - "**/*.ts"
  - "**/*.tsx"
---

# TypeScript 공통 규칙

> 모든 TypeScript 파일에 적용되는 기본 규칙.

---

## 1. TypeScript

- **Strict 모드 필수**, `any` 사용 엄격히 금지 (부득이한 경우 `unknown` + Type Guard)
- 모든 API 응답 타입은 명시적으로 정의

---

## 2. 네이밍 규칙

- Boolean: `is`, `has`, `should` 접두사
- 이벤트 핸들러: `handle` 접두사
- Props 이벤트: `on` 접두사
- 컴포넌트 파일: PascalCase
- 훅 파일: camelCase `use` 접두사
- 상수: UPPER_SNAKE_CASE
