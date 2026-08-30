"use client";

import { PublicRouteError } from "@/components/public-route-error";

export default function SharedBacktestError({ reset }: { reset: () => void }) {
  return (
    <PublicRouteError
      heading="공유 결과를 여는 중 문제가 발생했습니다"
      body="잠시 후 다시 시도해 주세요."
      reset={reset}
    />
  );
}
