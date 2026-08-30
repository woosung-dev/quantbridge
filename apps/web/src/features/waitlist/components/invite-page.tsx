import Link from "next/link";

import { verifyInviteToken } from "../api";
import { resolveInviteView } from "../invite-view";

function InviteShell({ heading, children }: { heading: string; children: React.ReactNode }) {
  return (
    <main className="mx-auto flex w-full max-w-[560px] flex-col gap-6 px-4 py-16">
      <header className="flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <Link className="mkt-brand" href="/" aria-label="QuantBridge 홈으로">
            <span className="brand-mark" aria-hidden="true">
              <svg
                aria-hidden="true"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.4"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="3 17 9 11 13 15 21 7" />
                <polyline points="15 7 21 7 21 13" />
              </svg>
            </span>
            <span className="brand-name">QuantBridge</span>
          </Link>
          <span className="chip">Beta</span>
        </div>
        <h1 className="text-2xl font-bold md:text-3xl">{heading}</h1>
      </header>
      {children}
    </main>
  );
}

export async function InvitePageView({ token }: { token: string }) {
  const view = resolveInviteView(await verifyInviteToken(token));

  if (view.view === "unusable") {
    return (
      <InviteShell heading="초대 링크를 확인할 수 없습니다">
        <p className="text-muted-foreground">
          링크가 만료됐거나 이미 사용됐을 수 있습니다. 초대 메일의 링크를 다시 확인해 주세요.
        </p>
        <Link href="/waitlist" className="btn btn-ghost w-fit">
          웨이트리스트 다시 신청하기
        </Link>
      </InviteShell>
    );
  }

  if (view.view === "unavailable") {
    return (
      <InviteShell heading="지금은 확인할 수 없습니다">
        <p className="text-muted-foreground">
          초대 확인 서버에 닿지 못했습니다. 잠시 후 다시 열어 주세요.
        </p>
      </InviteShell>
    );
  }

  if (view.view === "already-joined") {
    return (
      <InviteShell heading="이미 가입이 끝났습니다">
        <p className="text-muted-foreground">{view.email} 계정으로 바로 로그인하세요.</p>
        <Link href="/sign-in" className="btn btn-ghost w-fit">
          로그인
        </Link>
      </InviteShell>
    );
  }

  if (view.view === "not-yet") {
    return (
      <InviteShell heading="아직 초대가 활성화되지 않았습니다">
        <p className="text-muted-foreground">
          {view.email} 의 신청은 아직 검토 중입니다. 초대가 확정되면 메일로 다시 알려 드립니다.
        </p>
      </InviteShell>
    );
  }

  return (
    <InviteShell heading="QuantBridge Beta 에 초대되었습니다">
      <p className="text-muted-foreground">
        <span className="font-medium text-foreground">{view.email}</span> 로 초대가 확정됐습니다.
        같은 이메일로 계정을 만들어 주세요.
      </p>
      <Link
        href={`/sign-up?email=${encodeURIComponent(view.email)}`}
        className="btn btn-primary w-fit"
      >
        계정 만들기
      </Link>
      <div className="flex items-center gap-3">
        <span className="text-sm text-muted-foreground">이미 계정이 있다면</span>
        <Link href="/sign-in" className="btn btn-ghost">
          로그인
        </Link>
      </div>
    </InviteShell>
  );
}
