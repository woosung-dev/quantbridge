// `next/font/google` 의 vitest 전용 대역 — 로더 2종을 순수 함수로 되돌린다.
//
// 왜 필요한가: `next/font/google` 의 export 는 **빌드타임 SWC 변환이 치환하는 자리표**다.
// 런타임에는 함수가 아니라서 `Archivo({...})` 가 `TypeError: Archivo is not a function` 으로
// **top-level throw** 한다 ⇒ `src/lib/fonts.ts` 를 (전이로라도) import 하는 모듈이 전부 죽는다.
// 실측 사슬 2개(2026-08-21): `src/app/layout.tsx` · `src/components/monaco/pine-editor.tsx`
// → 후자를 통해 `strategies/new` · `strategies/[id]/edit` 페이지까지 번진다.
//
// ★`vi.mock("next/font/google")` 로 lane 안에서 막지 마라 — 8 lane 이 같은 회피를 각자 복제하게
//   되고, 전이 사슬(에디터 경유)을 가진 lane 은 mock 위치를 매번 다시 찾아야 한다.
//   `server-only` 와 같은 처방으로 resolve 단계에서 한 번만 갈아끼운다.
//
// ★반환값은 **옵션을 그대로 되비춘다** — `variable` 을 빈 문자열로 돌려주면 `layout.tsx` 의
//   `className={`${archivo.variable} …`}` 단언이 판별력을 잃는다. 실제 next/font 도 여기에
//   요청한 CSS 변수명을 그대로 넣는다.
//
// 이 별칭은 vitest 에만 적용된다. Next 빌드·`tsc --noEmit` 은 진짜 패키지를 본다.

interface FontOptions {
  variable?: string;
  weight?: string | string[];
  subsets?: string[];
  display?: string;
}

interface FontResult {
  className: string;
  variable: string;
  style: { fontFamily: string; fontWeight?: number; fontStyle?: string };
}

function makeLoader(family: string) {
  return (options: FontOptions = {}): FontResult => ({
    className: `__stub_${family}`,
    variable: options.variable ?? "",
    style: { fontFamily: family },
  });
}

export const Archivo = makeLoader("Archivo");
export const IBM_Plex_Mono = makeLoader("IBM_Plex_Mono");
