// Sprint 13 Phase A.2: webhook secret plaintext 1회 표시 후 sessionStorage 캐시 (TTL 30분).
// Strategy create 시 자동 발급된 secret 또는 rotate 응답을 frontend 가 받아서 캐시 →
// 후속 Test Order Dialog (Phase B) 가 readWebhookSecret 으로 가져와 HMAC 계산.
//
// 보안 trade-off (dogfood-only):
// - sessionStorage XSS 시 탈취 가능. 단 secret 자체가 webhook 외부 노출용이고,
//   Test Order Dialog 는 NEXT_PUBLIC_ENABLE_TEST_ORDER=true 시만 활성.
// - localStorage 사용 X (브라우저 종료 시 자동 제거).
// - strategy_id scoped key (다른 strategy 와 격리).
// - TTL 30분 (rotate 후 grace 5분 + 안전 마진).
// - 사용자가 amber 카드 닫으면 즉시 removeItem (clear()).
//
// Sprint 14 Phase A — useSyncExternalStore subscribe/notify 추가.
// dogfood Day 2 Pain #2 (TabWebhook hydration race) 해소 — sessionStorage 를
// external store 로 추상화. server snapshot 은 항상 null (SSR safe), client snapshot
// 은 mount 후 read. cache/clear 시 listeners notify → 구독 컴포넌트 자동 re-render.
// LESSON-004 H-1 (useEffect setState ban) 회피: useSyncExternalStore 는 React 공식
// external state 동기화 hook 이라 set-state-in-effect 차단 없음.

const STORAGE_PREFIX = "qb-webhook-secret-";
const TTL_MS = 30 * 60 * 1000; // 30분

interface CachedSecret {
  plaintext: string;
  expiresAt: number;
}

function storageKey(strategyId: string): string {
  return `${STORAGE_PREFIX}${strategyId}`;
}

// in-process subscriber registry — useSyncExternalStore 가 mount 시 subscribe 등록.
// 같은 탭 내 cache/clear 호출 시 listeners 호출 → React re-render trigger.
const listeners = new Set<() => void>();

function notify(): void {
  listeners.forEach((listener) => listener());
}

export function subscribeWebhookSecret(callback: () => void): () => void {
  listeners.add(callback);
  return () => {
    listeners.delete(callback);
  };
}

export function cacheWebhookSecret(strategyId: string, plaintext: string): void {
  if (typeof window === "undefined") return; // SSR safety
  const payload: CachedSecret = {
    plaintext,
    expiresAt: Date.now() + TTL_MS,
  };
  sessionStorage.setItem(storageKey(strategyId), JSON.stringify(payload));
  notify();
}

export function readWebhookSecret(strategyId: string): string | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem(storageKey(strategyId));
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as CachedSecret;
    if (Date.now() > parsed.expiresAt) {
      sessionStorage.removeItem(storageKey(strategyId));
      return null;
    }
    return parsed.plaintext;
  } catch {
    sessionStorage.removeItem(storageKey(strategyId));
    return null;
  }
}

export function clearWebhookSecret(strategyId: string): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(storageKey(strategyId));
  notify();
}
