// [BL-072] 초대 링크 착지 페이지 — 이 회차 전까지 **이 경로만 없었다**.
//
// ★BE·config·Makefile·env 네 곳이 이미 `/invite` 를 가리키고 있었다:
//   `core/config.py` 의 `waitlist_invite_base_url` 기본값이 `http://localhost:3000/invite`,
//   `.env.prod.example` 이 `https://<실 FE 도메인>/invite`, `Makefile` 이 슬롯 포트판.
//   즉 **지금 초대 메일을 보내면 링크가 404 로 떨어졌다.**
//
// 구조는 `/share/backtests/[token]` 선례를 따르되 **fetch 는 페이지에 두지 않는다** —
// 호출은 `features/waitlist/api.ts`, 갈래 판정은 `features/waitlist/invite-view.ts` 의 순수 함수다
// (`apps/web/AGENTS.md` §3 · 2026-08-16 codex 적대 리뷰 P3). 페이지는 렌더만 한다.
import type { Metadata } from "next";
import Link from "next/link";

import { verifyInviteToken } from "@/features/waitlist/api";
import { resolveInviteView } from "@/features/waitlist/invite-view";

// 토큰 상태(승인·만료)가 즉시 반영돼야 한다 — 캐시하면 만료된 초대가 계속 유효해 보인다.
export const dynamic = "force-dynamic";

interface PageProps {
  params: Promise<{ token: string }>;
}

export const metadata: Metadata = {
  title: "초대 확인 · QuantBridge",
  description: "QuantBridge Beta 초대 링크를 확인합니다.",
  // 초대 링크가 검색 결과에 남으면 안 된다.
  robots: { index: false, follow: false },
};

function Shell({
  heading,
  children,
}: {
  heading: string;
  children: React.ReactNode;
}) {
  return (
    <main className="mx-auto flex w-full max-w-[560px] flex-col gap-6 px-4 py-16">
      <header className="flex flex-col gap-2">
        <p className="text-sm text-muted-foreground">QuantBridge Beta</p>
        <h1 className="text-2xl font-bold md:text-3xl">{heading}</h1>
      </header>
      {children}
    </main>
  );
}

export default async function InvitePage({ params }: PageProps) {
  const { token } = await params;
  const view = resolveInviteView(await verifyInviteToken(token));

  if (view.view === "unusable") {
    return (
      <Shell heading="초대 링크를 확인할 수 없습니다">
        <p className="text-muted-foreground">
          링크가 만료됐거나 이미 사용됐을 수 있습니다. 초대 메일의 링크를 다시
          확인해 주세요.
        </p>
        <Link href="/waitlist" className="underline">
          대기자 명단 다시 신청하기
        </Link>
      </Shell>
    );
  }

  if (view.view === "unavailable") {
    return (
      <Shell heading="지금은 확인할 수 없습니다">
        <p className="text-muted-foreground">
          초대 확인 서버에 닿지 못했습니다. 잠시 후 다시 열어 주세요.
        </p>
        {/* 상세는 화면에 싣지 않는다 — [BL-772] 와 같은 이유다. */}
        <p className="text-sm text-muted-foreground">({view.message})</p>
      </Shell>
    );
  }

  if (view.view === "already-joined") {
    return (
      <Shell heading="이미 가입이 끝났습니다">
        <p className="text-muted-foreground">
          {view.email} 계정으로 바로 로그인하세요.
        </p>
        <Link href="/sign-in" className="underline">
          로그인
        </Link>
      </Shell>
    );
  }

  if (view.view === "not-yet") {
    return (
      <Shell heading="아직 초대가 활성화되지 않았습니다">
        <p className="text-muted-foreground">
          {view.email} 의 신청은 아직 검토 중입니다. 초대가 확정되면 메일로 다시
          알려 드립니다.
        </p>
      </Shell>
    );
  }

  return (
    <Shell heading="QuantBridge Beta 에 초대되었습니다">
      <p className="text-muted-foreground">
        <span className="font-medium text-foreground">{view.email}</span> 로
        초대가 확정됐습니다. 같은 이메일로 계정을 만들어 주세요.
      </p>
      <Link
        href={`/sign-up?email=${encodeURIComponent(view.email)}`}
        className="w-fit rounded-md bg-primary px-4 py-2 font-medium text-primary-foreground"
      >
        계정 만들기
      </Link>
      <p className="text-sm text-muted-foreground">
        이미 계정이 있다면{" "}
        <Link href="/sign-in" className="underline">
          로그인
        </Link>
        하세요.
      </p>
    </Shell>
  );
}
