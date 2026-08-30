import type { Metadata } from "next";

import { InvitePageView } from "@/features/waitlist/components/invite-page";

// 토큰 상태(승인·만료)가 즉시 반영돼야 한다 — 캐시하면 만료된 초대가 계속 유효해 보인다.
export const dynamic = "force-dynamic";

interface PageProps {
  params: Promise<{ token: string }>;
}

export const metadata: Metadata = {
  title: "초대 확인",
  description: "QuantBridge Beta 초대 링크를 확인합니다.",
  robots: { index: false, follow: false },
};

export default async function InvitePage({ params }: PageProps) {
  const { token } = await params;
  return await InvitePageView({ token });
}
