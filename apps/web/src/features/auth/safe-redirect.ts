// 로그인 뒤 이동할 `redirect_url` 을 **같은 출처의 경로**로만 좁힌다.
//
// ★문자열 접두 검사(`startsWith("/") && !startsWith("//")`)는 우회된다 — URL 파서가 `\` 를 `/` 로
//   바꾸고 탭·개행을 지우므로 `/\evil.com`, `/\t/evil.com` 이 외부 호스트가 된다(보안 감사 2026-11-19).
//   라우터와 같은 WHATWG 파서로 풀어 본 뒤 출처를 비교한다.

const PROBE_ORIGIN = "https://qb.invalid";

export function safeRedirectPath(raw: string | undefined, fallback: string): string {
  if (!raw?.startsWith("/")) return fallback;
  let url: URL;
  try {
    url = new URL(raw, PROBE_ORIGIN);
  } catch {
    return fallback;
  }
  if (url.origin !== PROBE_ORIGIN) return fallback;
  return `${url.pathname}${url.search}${url.hash}`;
}
