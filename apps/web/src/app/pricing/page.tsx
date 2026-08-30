import type { Metadata } from "next";

import { PricingPage } from "@/features/marketing/components/pricing-page";

export const metadata: Metadata = {
  title: "요금제",
  description:
    "QuantBridge 요금제. 아직 가격을 정하지 않았고, 지금 무엇이 되고 무엇이 안 되는지를 그대로 적었습니다.",
};

export default function PricingRoute() {
  return <PricingPage />;
}
