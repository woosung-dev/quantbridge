import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// 인증 클라이언트는 전역으로 mock 한다 — 실제 구현은 `fetch("/api/auth/token")` 과 nanostores
// 구독을 하므로 jsdom 단위 테스트에서 의미가 없다. 정본은 `src/lib/__mocks__/auth-client.ts`.
// ★이것이 종전 26개 파일의 인라인 `vi.mock("@clerk/nextjs", …)` 를 대신한다(ADR-034).
vi.mock("@/lib/auth-client");
