"use client";

// 상단바 푸시 벨 — 「이 기기에서 알림 받기」 스위치 + 「테스트 알림 보내기」(pwa.md §2.7).
// 렌더 조건 = serviceWorker ∧ PushManager ∧ Notification 지원 ∧ 서버 config `enabled === true`.
// 하나라도 아니면 **아무것도 그리지 않는다**(서버에 VAPID 키가 들어가기 전까지 벨이 없다).
// ★3단 분리 — 지원 판정(클라이언트 전용) → 설정 조회(React Query) → 기기 상태. 지원하지 않는 환경은
//   쿼리 훅까지 내려가지 않으므로 설정 요청도 0건이다.
// ★팝오버 본체(Base UI Popover + floating-ui)는 마지막 단에서만 지연 로딩한다 — 이 파일은 셸을 통해
//   대시보드 전 라우트에 실리므로 여기에 정적 import 를 두지 마라(`bundle-conditional`).

import dynamic from "next/dynamic";
import { useSyncExternalStore } from "react";

import {
  usePushConfig,
  useReclaimDeviceSubscription,
  useRegisterPushSignOutCleanup,
} from "../hooks";
import { isPushSupported } from "../push";

const PushBellPopover = dynamic(
  () => import("./push-bell-popover").then((m) => m.PushBellPopover),
  { ssr: false, loading: () => null },
);

// 지원 여부는 세션 중 바뀌지 않는다 — 구독할 것이 없다.
const subscribeNever = () => () => {};

export function PushBell() {
  // 서버·하이드레이션 첫 렌더는 false(미렌더) → 커밋 뒤 실제 값. 하이드레이션 불일치가 없다.
  const supported = useSyncExternalStore(subscribeNever, isPushSupported, () => false);
  return supported ? <SupportedPushBell /> : null;
}

function SupportedPushBell() {
  useRegisterPushSignOutCleanup();
  const { data: config } = usePushConfig();
  // 팝오버는 지연 로딩이라 열기 전엔 마운트되지 않는다 — 재할당은 여기서 한다.
  useReclaimDeviceSubscription(config?.enabled === true);
  return config?.enabled && config.public_key ? (
    <PushBellPopover publicKey={config.public_key} />
  ) : null;
}
