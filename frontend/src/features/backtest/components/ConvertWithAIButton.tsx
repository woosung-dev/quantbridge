"use client";
// AI로 indicator를 strategy로 변환하는 버튼 컴포넌트.
// 미지원 builtin 에러 발생 시 FormErrorInline 카드 하단에 노출.

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { toast } from "sonner";

import { convertIndicator } from "../api";
import type { ConvertIndicatorResponse } from "../schemas";

interface ConvertWithAIButtonProps {
  /** 변환할 Pine Script 소스 코드 */
  indicatorCode: string;
  /** 변환 성공 시 호출. 결과를 부모에서 처리 (클립보드 복사 or 모달). */
  onConverted: (result: ConvertIndicatorResponse) => void;
}

export function ConvertWithAIButton({
  indicatorCode,
  onConverted,
}: ConvertWithAIButtonProps) {
  const { getToken } = useAuth();
  const [isConverting, setIsConverting] = useState(false);

  const handleConvert = async () => {
    const token = await getToken();
    if (!token) return;
    setIsConverting(true);
    try {
      const result = await convertIndicator(
        { code: indicatorCode, strategy_name: "Converted Strategy", mode: "full" },
        token,
      );
      onConverted(result);
      toast.success("변환 완료! 코드를 검토하세요.");
    } catch {
      toast.error("변환 실패. 잠시 후 다시 시도해주세요.");
    } finally {
      setIsConverting(false);
    }
  };

  return (
    <button
      type="button"
      onClick={handleConvert}
      disabled={isConverting}
      className="inline-flex items-center gap-2 rounded-md bg-violet-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50"
    >
      {isConverting ? "변환 중..." : "AI로 변환하기"}
    </button>
  );
}
