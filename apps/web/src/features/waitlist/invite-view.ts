// [BL-072] 초대 토큰 조회 결과 → 화면 갈래. 순수 함수라 SSR 밖에서 검증할 수 있다.
//
// ★**왜 페이지에서 뺐나** — `/invite/[token]` 은 서버 컴포넌트라 BE 를 **Next 서버 프로세스**가
//   부른다. Playwright 의 `page.route()` 는 **브라우저 요청만** 가로채므로 e2e 로는 갈래를
//   심을 수 없다(2026-08-16 실측: 4갈래를 stub 한 spec 이 전부 실 BE 응답으로 떨어졌고,
//   그중 하나가 우연히 맞아 **무증거 초록**이 났다).
//   ⇒ 갈래 판정은 여기서 vitest 로 재고, e2e 는 **페이지가 이 함수를 쓰는지**(공개 라우트 ·
//   실패 갈래 렌더)를 잰다. 순수 함수 정확성 ≠ 배선([LESSON-092] 2).

import type { WaitlistStatus } from "./schemas";

export type InviteFetchResult =
  | { kind: "ok"; email: string; status: WaitlistStatus }
  | { kind: "invalid" } // 400 — 서명 불일치 · 만료. ★둘을 가르지 않는다(토큰 추측 힌트).
  | { kind: "not-found" } // 404 — 토큰은 읽혔으나 신청서가 없다
  | { kind: "error"; message: string };

export type InviteView =
  | { view: "invited"; email: string }
  | { view: "already-joined"; email: string }
  | { view: "not-yet"; email: string }
  | { view: "unusable" }
  | { view: "unavailable"; message: string };

export function resolveInviteView(result: InviteFetchResult): InviteView {
  // 만료·위조·신청서 없음을 **한 갈래**로 합친다 — 어느 쪽인지 알려 주면 토큰을 좁힐 수 있다.
  if (result.kind === "invalid" || result.kind === "not-found") {
    return { view: "unusable" };
  }
  if (result.kind === "error") {
    return { view: "unavailable", message: result.message };
  }
  // 이미 가입까지 끝났다 — 다시 가입시키면 두 번째 계정이 생긴다.
  if (result.status === "joined") {
    return { view: "already-joined", email: result.email };
  }
  // `invited` 만 가입 CTA 를 연다. `pending`·`rejected` 는 아직(또는 영영) 아니다.
  // ★거절을 링크 소유자에게 통보하는 자리가 아니므로 `pending` 과 같은 문구를 쓴다.
  if (result.status !== "invited") {
    return { view: "not-yet", email: result.email };
  }
  return { view: "invited", email: result.email };
}
