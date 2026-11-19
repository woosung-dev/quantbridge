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
  // ★정규화된 경로가 `//` 로 시작하면 다시 풀 때 프로토콜 상대 URL(다른 호스트)이 된다 —
  //   `/.//evil.com` 처럼 점 세그먼트가 지워지며 생긴다. 결과를 한 번 더 풀어 같은 출처인지 확인한다.
  const path = `${url.pathname}${url.search}${url.hash}`;
  if (path.startsWith("//") || new URL(path, PROBE_ORIGIN).origin !== PROBE_ORIGIN) return fallback;
  return path;
}
