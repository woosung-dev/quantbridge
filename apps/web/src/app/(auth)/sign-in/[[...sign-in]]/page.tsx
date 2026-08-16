// 로그인 페이지 — C 디자인 언어 셸 + 자체 폼(ADR-034, 구 Clerk `<SignIn/>` 대체).
// catch-all 세그먼트(`[[...sign-in]]`)는 Clerk 라우팅 요구였지만 그대로 둔다 —
// 링크·리다이렉트·e2e 가 `/sign-in` 을 가리키고, 세그먼트를 지우면 그 경로들이 함께 흔들린다.
import { AuthForm } from "../../_components/auth-form";
import { SplitScreenShell } from "../../_components/split-screen-shell";

export default async function SignInPage({
  searchParams,
}: {
  searchParams: Promise<{ redirect_url?: string | string[] }>;
}) {
  const params = await searchParams;
  const raw = Array.isArray(params.redirect_url) ? params.redirect_url[0] : params.redirect_url;
  // ★열린 리다이렉트 차단 — 앱 내부 경로만 허용한다(`//host` 는 프로토콜 상대 URL 이다).
  const redirectTo = raw && raw.startsWith("/") && !raw.startsWith("//") ? raw : "/strategies";

  return (
    <SplitScreenShell mode="sign-in">
      <AuthForm mode="sign-in" redirectTo={redirectTo} />
    </SplitScreenShell>
  );
}
