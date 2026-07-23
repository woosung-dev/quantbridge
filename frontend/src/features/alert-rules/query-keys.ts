// 세션 알림 규칙의 사용자 우선 React Query 키를 만든다.
export const alertRuleKeys = {
  all: (userId: string) => ["alert-rules", userId] as const,
  list: (userId: string, sessionId: string) =>
    [...alertRuleKeys.all(userId), "list", sessionId] as const,
};
