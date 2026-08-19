// [BL-797] 화면 증거 팩 — **공개 라우트**의 before/after 증거를 산출한다.
//
// ★결함: `apps/web/` 을 바꾼 PR 이 머지될 때 리뷰어가 얻는 것이 **코드 diff 뿐**이었다.
//   무엇이 어떻게 달라 보이는지도, 그 대가(번들·요청 수)가 얼마인지도 PR 어디에도 안 남았다.
//   2026-08-09 [BL-662~665] 가 `/dashboard` 를 −181.5kB 줄였는데 그 수치가 PR 에 없고,
//   2026-08-17 [BL-786] 의 라우트 감소는 CONTROL 이 대조 빌드를 두 번 돌려 겨우 찾아냈다.
//
// ★이 spec 이 재는 것은 셋이다 — 화면(스크린샷) · first-load 번들(바이트) · 화면당 API 요청 수.
//   셋 다 **커밋된 baseline 과 대조**하고, 어긋나면 red 로 「baseline 을 갱신해라」를 낸다.
//   before/after 표는 `scripts/screen-evidence.mjs` 가 **커밋된 baseline 의 origin/main 판**과
//   대조해서 만든다 — 즉 before 는 추론이 아니라 **git blob** 이다.
//
// ★★**측정은 프로덕션 서버(`next start`)에서 한다.** dev 서버는 ⑴ Turbopack 이 모듈 단위로
//   쪼개 서빙해서 바이트가 캐시 상태에 따라 흔들리고 ⑵ dev 표시기가 화면에 얹힌다.
//   `scripts/screen-evidence.mjs` 가 그 서버를 띄우고 `PLAYWRIGHT_BASE_URL` 로 물린다.
//
// ★2026-08-18 — 측정 본문은 `screen-evidence-cases.ts` 로 옮겼다. authed 라우트가
//   **다른 playwright project**(storageState + `setup-authed-reachability` 의존)를 요구해
//   spec 이 둘로 갈렸고, 재는 방법은 하나여야 하기 때문이다. 여기 남은 것은 **목록**뿐이다.
import { registerScreenEvidenceTests } from "./screen-evidence-cases";
import type { RouteCase } from "./screen-evidence-shared";

/**
 * 공개 라우트 3종. `src/proxy.ts` 의 `isPublicRoute` 목록에서 골랐다.
 *
 * ★`/` 는 랜딩, `/sign-in` 은 인증 셸, `/waitlist` 는 폼이다 — 서로 다른 레이아웃 계열을
 *   하나씩 잡아 두면 공용 셸(헤더·토큰·폰트)이 깨졌을 때 셋이 함께 움직여 원인이 좁혀진다.
 */
const ROUTES: readonly RouteCase[] = [
  { path: "/", slug: "landing", anchor: "QuantBridge" },
  { path: "/sign-in", slug: "sign-in", anchor: "QuantBridge" },
  { path: "/waitlist", slug: "waitlist", anchor: "QuantBridge" },
];

registerScreenEvidenceTests("화면 증거 팩", ROUTES);
