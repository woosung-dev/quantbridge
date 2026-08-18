// [BL-797] 화면 증거 팩 — **authed 라우트**의 수치 증거.
//
// ★왜 필요한가 (2026-08-18 실측으로 확정된 공백). 이 게이트를 만든 회차(08-17 night3)가
//   같은 밤 화면을 바꾼 PR 둘을 냈는데 **둘 다 authed** 라 공개 3라우트만 재는 표에서
//   Δ=0 이었다. 다음 회차(08-18 design-t1t2)는 FE 25라우트를 감사해 5커밋을 넣었고 바꾼
//   화면 **대부분이 authed** 라 증거 팩 밖에서 무증거였다 — 검증을 손 playwright 로 때웠다.
//
// ★★**스크린샷 축을 쓰지 않는다.** authed 화면에는 실데이터(시각·가격·행 수)가 실려 매 실행
//   픽셀이 흔들린다. `maxDiffPixels: 0` 을 유지할 수 없고, 값을 올리는 순간 그 축은
//   글자 한 자 변경을 통째로 삼켜 존재 이유를 잃는다(`screen-evidence-cases.ts` 의 근거 주석).
//   ⇒ `slug: null` = **수치 전용**. 번들 바이트와 요청 수만 잰다. 그 둘이 [BL-662~665](−181.5kB)
//   와 [BL-786](라우트 감소)이 실제로 움직인 축이다.
//
// ★★전제 셋이 서야 돈다 — ⑴ 프로덕션 서버(`next start`) ⑵ **그 origin 을 아는 BE**
//   (`FRONTEND_URL` = CORS · `BETTER_AUTH_URL` = JWKS·issuer, **둘 다** 그 포트여야 한다)
//   ⑶ storageState. 셋 중 하나가 없으면 `scripts/screen-evidence.mjs` 가 **측정 전에 죽는다** —
//   조용한 skip 은 「변경 없음」과 구별되지 않고, 그것이 이 게이트가 막으려는 상태다.
import { registerScreenEvidenceTests } from "./screen-evidence-cases";
import type { RouteCase } from "./screen-evidence-shared";

/**
 * authed 목록 화면 4종.
 *
 * ★상세 라우트(`/backtests/:id` 등)는 넣지 않았다 — id 가 환경마다 다르고, 그 라우트의
 *   캐논 커버리지는 `authed-canon-*.spec.ts` 가 진다. 여기는 **번들이 실제로 움직인 면**이다.
 * ★★`/` 를 넣으면 안 된다 — 로그인 상태에서 `proxy.ts:96-100` 이 `/strategies` 로 UX
 *   리다이렉트하므로 측정 대상이 조용히 뒤바뀐다. 공개 leg 가 이미 `/` 를 잰다.
 */
const ROUTES: readonly RouteCase[] = [
  { path: "/dashboard", slug: null, anchor: "QuantBridge", authed: true },
  { path: "/strategies", slug: null, anchor: "전략", authed: true },
  { path: "/backtests", slug: null, anchor: "백테스트", authed: true },
  { path: "/optimizer", slug: null, anchor: "옵티마이저", authed: true },
];

registerScreenEvidenceTests("화면 증거 팩 (authed · 수치 전용)", ROUTES);
