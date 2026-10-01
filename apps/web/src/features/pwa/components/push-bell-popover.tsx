"use client";

// 푸시 벨 팝오버 본체 — 「이 기기에서 알림 받기」 스위치 + 「테스트 알림 보내기」(pwa.md §2.7).
// ★`push-bell.tsx` 가 `next/dynamic` 으로 **지원 ∧ enabled ∧ public_key 일 때만** 불러온다.
//   Base UI Popover(+floating-ui, gz ≈23KB)를 정적 import 하면 셸을 쓰는 대시보드 전 라우트가 그
//   청크를 받는다 — 서버에 VAPID 키가 없으면 렌더가 0% 인데도(`bundle-conditional`).
// ★권한 요청은 여전히 스위치 클릭 핸들러 안에서 **동기로** 시작한다 — 지연 로딩은 렌더 전에
//   끝나므로 클릭 시점의 사용자 제스처와 무관하다(`hooks.ts` `usePushDevice().enable`).

import { Popover } from "@base-ui/react/popover";
import { Bell, BellRing } from "lucide-react";
import { useId } from "react";

import { usePushDevice } from "../hooks";

const TRIGGER_CLASS =
  "inline-flex h-11 w-11 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

export function PushBellPopover({ publicKey }: { publicKey: string }) {
  const { permission, subscribed, pending, error, testResult, enable, disable, sendTest } =
    usePushDevice(publicKey);
  const labelId = useId();
  const denied = permission === "denied";
  const on = subscribed === true;

  const handleToggle = () => {
    void (on ? disable() : enable());
  };
  const handleSendTest = () => {
    void sendTest();
  };

  return (
    <Popover.Root>
      <Popover.Trigger className={TRIGGER_CLASS} aria-label="알림 설정" title="알림 설정">
        {on ? (
          <BellRing className="h-5 w-5" aria-hidden="true" />
        ) : (
          <Bell className="h-5 w-5" aria-hidden="true" />
        )}
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Positioner side="bottom" align="end" sideOffset={8}>
          <Popover.Popup className="w-72 max-w-[calc(100vw-2rem)] rounded-lg border border-border bg-popover p-4 text-sm text-popover-foreground shadow-card outline-none">
            <Popover.Title className="text-sm font-semibold">알림</Popover.Title>

            <div className="mt-2 flex items-center justify-between gap-3">
              <span id={labelId}>이 기기에서 알림 받기</span>
              <button
                type="button"
                role="switch"
                aria-checked={on}
                aria-labelledby={labelId}
                disabled={denied || pending || subscribed === null}
                onClick={handleToggle}
                className="group inline-flex min-h-11 shrink-0 items-center disabled:cursor-not-allowed disabled:opacity-50"
              >
                <span className="inline-flex h-6 w-11 items-center rounded-full bg-[color:var(--line)] transition-colors group-aria-checked:bg-[color:var(--primary)]">
                  <span className="size-5 translate-x-0.5 rounded-full bg-[color:var(--ink)] transition-transform group-aria-checked:translate-x-5 group-aria-checked:bg-[color:var(--primary-foreground)]" />
                </span>
              </button>
            </div>

            {denied ? (
              <p className="field-hint">브라우저 설정에서 알림이 차단되어 있습니다</p>
            ) : null}

            <button
              type="button"
              className="btn mt-3 w-full justify-center"
              disabled={!on || pending}
              onClick={handleSendTest}
            >
              테스트 알림 보내기
            </button>

            {testResult ? (
              <p className="field-hint mt-2" role="status">
                {testResult.sent > 0
                  ? `테스트 알림을 기기 ${testResult.sent}대로 보냈습니다.`
                  : "알림을 받을 수 있는 기기가 없습니다."}
              </p>
            ) : null}
            {error ? (
              <p className="field-error mt-2" role="alert">
                <span>{error}</span>
              </p>
            ) : null}
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
  );
}
