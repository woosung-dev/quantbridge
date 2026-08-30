// [BL-072] 초대 갈래 판정 — 5갈래 전수 + 음성 대조.
//
// ★e2e 로는 못 잰다: `/invite/[token]` 은 서버 컴포넌트라 BE 호출이 Next 서버 프로세스에서
//   일어나고 Playwright `page.route()` 는 브라우저 요청만 가로챈다. 초판 e2e 가 4갈래를
//   stub 했는데 전부 실 BE 응답으로 떨어졌고 그중 하나가 우연히 맞아 초록이었다.

import { describe, expect, it } from "vitest";

import { resolveInviteView } from "../invite-view";

describe("[BL-072] resolveInviteView", () => {
  it("invited 만 가입 CTA 갈래를 연다", () => {
    expect(resolveInviteView({ kind: "ok", email: "a@b.co", status: "invited" })).toEqual({
      view: "invited",
      email: "a@b.co",
    });
  });

  it("joined 는 두 번째 계정을 막는 갈래다", () => {
    expect(resolveInviteView({ kind: "ok", email: "a@b.co", status: "joined" })).toEqual({
      view: "already-joined",
      email: "a@b.co",
    });
  });

  it.each(["pending", "rejected"] as const)("%s 는 초대 확정으로 읽히지 않는다", (status) => {
    const view = resolveInviteView({ kind: "ok", email: "a@b.co", status });
    expect(view.view).toBe("not-yet");
    // ★음성 대조 — 미승인/거절이 가입 갈래로 새면 승인 전 가입이 열린다.
    expect(view.view).not.toBe("invited");
  });

  it("★거절 사실을 링크 소유자에게 통보하지 않는다 — pending 과 같은 갈래다", () => {
    const rejected = resolveInviteView({
      kind: "ok",
      email: "a@b.co",
      status: "rejected",
    });
    const pending = resolveInviteView({
      kind: "ok",
      email: "a@b.co",
      status: "pending",
    });
    expect(rejected).toEqual(pending);
  });

  it("★만료와 위조를 가르지 않는다 — 400 과 404 가 같은 갈래다", () => {
    // 가르면 「이 토큰은 형식은 맞는데 만료됐다」를 알려 주는 셈이라 추측을 좁힌다.
    expect(resolveInviteView({ kind: "invalid" })).toEqual({ view: "unusable" });
    expect(resolveInviteView({ kind: "not-found" })).toEqual({ view: "unusable" });
  });

  it("네트워크 실패는 「사용 불가」와 다른 갈래다", () => {
    const view = resolveInviteView({ kind: "error" });
    expect(view).toEqual({ view: "unavailable" });
    // ★서버가 안 닿는 것과 토큰이 못 쓰는 것을 합치면 사용자가 재시도할지 포기할지 모른다.
    expect(view.view).not.toBe("unusable");
  });
});
