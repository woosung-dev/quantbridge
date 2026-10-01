// 로그아웃·계정 삭제 **직전** 정리 훅 — 공유층(`components/layout/account-button.tsx`)이 도메인
// (`features/pwa`)을 import 하지 않고, 도메인이 자기 정리 함수를 여기에 등록한다.
// 방향은 `api-client.ts` 의 `setUnauthorizedHandler` 와 같다(공유층 → features import 금지, biome.jsonc).
//
// ★계약 — 정리는 **best-effort** 다. 실패해도, 2초를 넘겨도 로그아웃은 진행된다
//   (`docs/architecture/pwa.md` §2.7). 정리가 로그아웃을 막으면 공용 기기에서 더 나쁘다.

const BEFORE_SIGN_OUT_TIMEOUT_MS = 2_000;

type Cleanup = () => Promise<void>;

let cleanup: Cleanup | null = null;

export function setBeforeSignOut(next: Cleanup | null): void {
  cleanup = next;
}

/** 등록된 정리를 최대 2초 기다린다. 절대 throw 하지 않는다. */
export async function runBeforeSignOut(): Promise<void> {
  const task = cleanup;
  if (!task) return;
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<void>((resolve) => {
    timer = setTimeout(resolve, BEFORE_SIGN_OUT_TIMEOUT_MS);
  });
  try {
    await Promise.race([task(), timeout]);
  } catch (error) {
    console.warn("[before-sign-out] 정리 실패, 로그아웃은 계속한다", error);
  } finally {
    clearTimeout(timer);
  }
}
