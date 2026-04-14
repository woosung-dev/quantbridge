import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto flex max-w-[520px] flex-col items-start gap-4 px-6 py-20">
      <h2 className="font-display text-2xl font-bold">페이지를 찾을 수 없습니다</h2>
      <p className="text-sm text-[color:var(--text-secondary)]">
        요청하신 주소가 존재하지 않거나 이동되었을 수 있습니다.
      </p>
      <Link
        href="/"
        className="inline-flex min-h-[48px] items-center gap-2 rounded-[10px] bg-[color:var(--primary)] px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-[color:var(--primary-hover)]"
      >
        홈으로
      </Link>
    </div>
  );
}
