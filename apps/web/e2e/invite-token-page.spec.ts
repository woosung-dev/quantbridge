// [BL-072] `/invite/[token]` — 초대 링크 착지 페이지의 **배선**을 잰다.
//
// ★이 페이지가 없어서 **초대 메일의 링크가 404 로 떨어지고 있었다.** BE·config·Makefile·env
//   네 곳이 이미 `/invite` 를 가리키는데 라우트만 없던 것이 이 항목의 실체다.
//
// ★★**여기서 갈래(invited/joined/pending)를 재려 하지 마라.** 이 페이지는 서버 컴포넌트라
//   BE 호출이 **Next 서버 프로세스**에서 일어나고, Playwright 의 `page.route()` 는
//   **브라우저 요청만** 가로챈다. 초판이 4갈래를 stub 했는데 전부 실 BE 응답으로 떨어졌고
//   그중 하나가 우연히 맞아 **무증거 초록**이 났다(2026-08-16 실측).
//   갈래 판정은 `src/features/waitlist/__tests__/invite-view.test.ts` 가 재고,
//   이 파일은 **e2e 만 잴 수 있는 두 가지**를 잰다:
//     ⑴ 공개 라우트인가 (로그인 없이 열리는가)
//     ⑵ 라우트가 실재하고 실 BE 응답으로 실패 갈래를 렌더하는가 (= 404 가 아니다)

import { expect, test } from "@playwright/test";

// ★세션 없는 컨텍스트 — 이것이 「공개 라우트」계약의 판별자다. 이 줄을 지우면
//   `proxy.ts` 에서 `/invite/(.*)` 를 빼도 초록이라 계약을 못 잰다.
test.use({ storageState: { cookies: [], origins: [] } });

const BOGUS_TOKEN = "bogus-invite-token-0123456789";

test.describe("[BL-072] 초대 링크 착지 페이지", () => {
  test("로그인 없이 열리고, 없던 라우트가 실재한다", async ({ page }) => {
    const res = await page.goto(`/invite/${BOGUS_TOKEN}`);

    // ⑴ 공개 라우트 — `/sign-in` 으로 튕기지 않았다.
    expect(new URL(page.url()).pathname).toBe(`/invite/${BOGUS_TOKEN}`);
    // ⑵ 라우트 실재 — 이 항목 이전에는 여기가 404 였다.
    expect(res?.status()).toBe(200);
  });

  test("못 쓰는 토큰은 사유를 가르지 않는다", async ({ page }) => {
    await page.goto(`/invite/${BOGUS_TOKEN}`);

    // 실 BE 가 이 토큰을 거부한다(서명 불일치 → 400). 화면은 한 갈래로만 답한다.
    await expect(page.getByRole("heading", { name: /확인할 수 없습니다/ })).toBeVisible();

    // ★음성 대조 — BE 의 에러 코드도 「서명」 같은 내부 사유도 새면 안 된다.
    const body = await page.locator("body").innerText();
    expect(body).not.toContain("waitlist_invite_token");
    expect(body).not.toContain("서명");
    // 못 쓰는 토큰에 가입 CTA 가 뜨면 초대 없이 가입이 열린다.
    await expect(page.getByRole("link", { name: "계정 만들기" })).toHaveCount(0);
  });
});
