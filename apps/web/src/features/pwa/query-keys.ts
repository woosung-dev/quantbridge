// PWA(웹 푸시)의 사용자 우선 React Query 키를 만든다.
export const pwaKeys = {
  all: (userId: string) => ["pwa", userId] as const,
  pushConfig: (userId: string) => [...pwaKeys.all(userId), "push-config"] as const,
};
