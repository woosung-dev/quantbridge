// [BL-072] 초대 페이지 route error boundary — `apps/web/AGENTS.md` §6 의무.
"use client";

export default function InviteError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="mx-auto flex w-full max-w-[560px] flex-col items-start gap-4 px-4 py-16">
      <h2 className="text-xl font-bold">초대 링크를 여는 중 문제가 발생했습니다</h2>
      <p className="text-muted-foreground">{error.message}</p>
      <button
        onClick={reset}
        className="rounded-md bg-primary px-4 py-2 font-medium text-primary-foreground"
      >
        다시 시도
      </button>
    </main>
  );
}
