// `server-only` 의 vitest 전용 대역 — 빈 모듈이다.
//
// 왜 필요한가: `server-only` 패키지의 exports 맵은 `react-server` 조건에서만 `empty.js` 를 주고
// 그 밖에는 `index.js` = **top-level throw** 를 준다. vitest 는 그 조건을 켜지 않으므로
// `import "server-only"` 를 가진 모듈(`src/lib/auth-server.ts`)을 **import 하는 순간 죽는다.**
//
// ★`vi.mock("server-only", () => ({}))` 로는 못 막는다 — CJS 로 외부화돼 Node 의 require 가
//   먼저 실행한다(2026-08-21 실측: mock 을 걸어도 같은 throw). 그래서 resolve 단계에서 갈아끼운다.
//
// 이 별칭은 vitest 에만 적용된다. Next 빌드·`tsc --noEmit` 은 진짜 패키지를 그대로 본다 —
// 즉 「서버 전용」 표시는 프로덕션에서 여전히 살아 있다.
export {};
