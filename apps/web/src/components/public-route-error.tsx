"use client";

import Link from "next/link";

/** 공개 경로 error boundary의 안전한 고정 화면. Error/digest 원문은 prop으로 받지 않는다. */
export function PublicRouteError({
  heading,
  body,
  reset,
}: {
  heading: string;
  body: string;
  reset: () => void;
}) {
  return (
    <main
      className="mx-auto flex w-full max-w-[560px] flex-col items-start gap-4 px-4 py-16"
      data-testid="public-route-error"
    >
      <h2 className="text-xl font-bold">{heading}</h2>
      <p className="text-muted-foreground">{body}</p>
      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={reset} className="btn btn-primary">
          다시 시도
        </button>
        <Link href="/" className="btn btn-ghost">
          QuantBridge 홈으로
        </Link>
      </div>
    </main>
  );
}
