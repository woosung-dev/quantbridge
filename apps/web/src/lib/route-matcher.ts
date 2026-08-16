// 경로 매처 — 구 Clerk `createRouteMatcher` 의 자리를 대신한다(ADR-034).
// 패턴 문자열은 종전 `proxy.ts` 의 것을 **그대로** 옮겨 왔다. 리뷰어가 두 목록을 눈으로
// 대조할 수 있게 형태를 바꾸지 않은 것이 이 파일의 유일한 설계 의도다.

/**
 * 패턴을 pathname 전체에 앵커된 정규식으로 컴파일한다.
 *
 * ★패턴은 **이미 정규식 조각**이다(`/sign-in(.*)`). 이스케이프하지 않는다 — 종전 Clerk 매처와
 * 같은 문자열을 같은 뜻으로 읽기 위해서다. 그래서 패턴에 임의의 사용자 입력을 넣지 마라.
 */
export function createRouteMatcher(patterns: readonly string[]): (pathname: string) => boolean {
  const compiled = patterns.map((p) => new RegExp(`^${p}$`));
  return (pathname: string) => compiled.some((re) => re.test(pathname));
}
