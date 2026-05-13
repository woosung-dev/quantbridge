// 가격 페이지 — Sprint 60 S3 BL-269 (404 → 200, landing #pricing redirect)
import { redirect } from "next/navigation";

export default function PricingPage() {
  // landing 의 #pricing section 으로 anchor redirect (Beta 단계, 별도 페이지 없음)
  redirect("/#pricing");
}
