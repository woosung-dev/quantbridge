import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "@clerk/nextjs/server";

import { Button } from "@/components/ui/button";

export default async function LandingPage() {
  const { userId } = await auth();
  if (userId) {
    redirect("/strategies");
  }

  return (
    <main
      id="main-content"
      className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-[1200px] flex-col justify-center gap-10 px-6 py-20"
    >
      <section className="flex flex-col gap-6">
        <h1 className="font-display text-4xl font-extrabold tracking-tight md:text-5xl lg:text-6xl">
          Pine Script를 실전 트레이딩으로.
        </h1>
        <p className="max-w-[560px] text-base text-[color:var(--text-secondary)] md:text-lg">
          TradingView 전략을 백테스트하고, 스트레스 테스트로 강건성을 검증한 뒤 데모/라이브
          트레이딩까지 한 번에 연결하는 퀀트 플랫폼입니다.
        </p>
      </section>
      <div className="flex flex-wrap gap-3">
        <Button size="lg" render={<Link href="/sign-in" />} nativeButton={false}>
          시작하기
        </Button>
      </div>
    </main>
  );
}
