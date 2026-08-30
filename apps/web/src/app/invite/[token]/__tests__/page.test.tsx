// [BL-072] 초대 페이지의 **렌더**를 잰다 — 갈래 판정이 아니라 「그 갈래가 무엇을 그리는가」.
//
// ★2026-08-16 codex 적대 리뷰 P3 — 순수 함수 테스트(`invite-view.test.ts`)와 e2e 둘 다
//   **서버 페이지의 렌더를 보지 않는다.** 그래서 `not-yet` 갈래에 가입 CTA 를 얹어도 둘 다
//   초록이었다. [LESSON-092] 2 — 순수 함수 정확성 ≠ 배선. 여기가 그 배선이다.
//
// 서버 컴포넌트는 async 함수라 직접 await 해서 JSX 를 얻고 정적 마크업으로 굳힌다.

import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import InvitePage from "../page";

vi.mock("@/features/waitlist/api", () => ({
  verifyInviteToken: vi.fn(),
}));

import { verifyInviteToken } from "@/features/waitlist/api";

const mocked = vi.mocked(verifyInviteToken);

async function render(result: unknown): Promise<string> {
  mocked.mockResolvedValue(result as never);
  const el = await InvitePage({ params: Promise.resolve({ token: "t-123" }) });
  return renderToStaticMarkup(el);
}

const CTA = "계정 만들기";

afterEach(() => vi.clearAllMocks());

describe("[BL-072] 초대 페이지 렌더", () => {
  it("invited — 이메일과 가입 CTA 를 그리고 이메일을 가입 폼으로 넘긴다", async () => {
    const html = await render({ kind: "ok", email: "a@b.co", status: "invited" });
    expect(html).toContain("초대되었습니다");
    expect(html).toContain("a@b.co");
    expect(html).toContain(CTA);
    // 다른 주소로 가입하는 사고를 줄인다.
    expect(html).toContain("/sign-up?email=a%40b.co");
  });

  it.each(["pending", "rejected"] as const)(
    "%s — ★CTA 를 그리지 않는다 (승인 전 가입이 열리면 안 된다)",
    async (status) => {
      const html = await render({ kind: "ok", email: "a@b.co", status });
      expect(html).toContain("아직 초대가 활성화되지 않았습니다");
      expect(html).not.toContain(CTA);
      expect(html).not.toContain("/sign-up");
    },
  );

  it("joined — CTA 대신 로그인으로 보낸다 (두 번째 계정 방지)", async () => {
    const html = await render({ kind: "ok", email: "a@b.co", status: "joined" });
    expect(html).toContain("이미 가입이 끝났습니다");
    expect(html).not.toContain(CTA);
    expect(html).toContain("/sign-in");
  });

  it("★invalid 와 not-found 는 **같은 마크업**이어야 한다 — 사유를 가르면 안 된다", async () => {
    // ★「만료」라는 낱말이 화면에 있는지로 재면 안 된다 — 이 화면은 「만료됐거나 이미
    //   사용됐을 수 있습니다」로 **둘을 함께 적어** 어느 쪽인지 못 가르게 한 것이 계약이다.
    //   진짜 계약은 **두 갈래가 구분 불가능한가**이고, 그것은 동일성으로만 잰다.
    const invalid = await render({ kind: "invalid" });
    const notFound = await render({ kind: "not-found" });
    expect(invalid).toBe(notFound);
    expect(invalid).not.toContain(CTA);
    // 내부 사유(서명 불일치)는 절대 노출하지 않는다.
    expect(invalid).not.toContain("서명");
    expect(invalid).not.toContain("waitlist_invite_token");
  });

  it("error — 「못 쓰는 토큰」과 **다른 화면**이어야 재시도할지 알 수 있다", async () => {
    const err = await render({ kind: "error" });
    const unusable = await render({ kind: "invalid" });
    // ★`toContain` 으로 제목을 가르려 하지 마라 — "확인할 수 없습니다" 는
    //   "지금은 확인할 수 없습니다" 의 **부분문자열**이라 판별이 안 된다([BL-766] 과 같은 함정).
    expect(err).not.toBe(unusable);
    expect(err).toContain("지금은 확인할 수 없습니다");
    expect(err).not.toContain(CTA);
  });
});

// [S3] 브랜드 정합 — 초대 메일에서 처음 도착하는 표면이 마케팅 군과 같은 브랜드
// 언어(brand-mark + 워드마크)를 쓰는지, 액션이 .btn 체계인지, 용어가 통일됐는지를 잰다.
describe("[S3] 초대 페이지 브랜드 정합", () => {
  it("모든 갈래의 Shell 이 brand-mark + 워드마크 홈 링크를 그린다", async () => {
    const branches: unknown[] = [
      { kind: "ok", email: "a@b.co", status: "invited" },
      { kind: "ok", email: "a@b.co", status: "pending" },
      { kind: "ok", email: "a@b.co", status: "joined" },
      { kind: "invalid" },
      { kind: "error" },
    ];
    for (const branch of branches) {
      const html = await render(branch);
      expect(html).toContain("brand-mark");
      expect(html).toContain("brand-name");
      expect(html).toContain("QuantBridge 홈으로");
    }
  });

  it("invited — 주 CTA 는 btn-primary, 보조 로그인은 btn-ghost (위계 유지)", async () => {
    const html = await render({ kind: "ok", email: "a@b.co", status: "invited" });
    expect(html).toContain("btn btn-primary");
    expect(html).toContain("btn btn-ghost");
    // underline 맨 텍스트 링크는 남기지 않는다.
    expect(html).not.toContain('class="underline"');
  });

  it("unusable — 「웨이트리스트」 용어로 .btn-ghost 재신청 링크를 그린다", async () => {
    const html = await render({ kind: "invalid" });
    expect(html).toContain("웨이트리스트 다시 신청하기");
    // 이 페이지만 「대기자 명단」이던 용어 분열을 막는다 (다른 표면은 전부 「웨이트리스트」).
    expect(html).not.toContain("대기자 명단");
    expect(html).toContain("btn btn-ghost");
    expect(html).not.toContain('class="underline"');
  });

  it("joined — 로그인 링크가 .btn-ghost 다", async () => {
    const html = await render({ kind: "ok", email: "a@b.co", status: "joined" });
    expect(html).toContain("btn btn-ghost");
    expect(html).not.toContain('class="underline"');
  });
});
