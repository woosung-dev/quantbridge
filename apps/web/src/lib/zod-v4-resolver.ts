// Zod v4 + react-hook-form 호환 custom resolver (Phase C QA hotfix).
//
// `@hookform/resolvers/zod@3.10.0` 가 Zod v3 의 `error.errors` 를 검사해서 v4 의
// `error.issues` 를 throw 하는 호환성 이슈를 우회한다. superRefine custom issue
// (예: `addIssue({ code: "custom", path: [...] })`) 도 RHF errors 에 정상 매핑.
//
// 표준 reference: test-order-dialog.tsx (Sprint 13 dogfood). Phase C 라이브 QA
// (2026-05-30) 에서 register-exchange-account-dialog 가 평범한 zodResolver 사용
// → cross-field superRefine 이 RHF errors 미매핑 → 사용자 무피드백 + console
// ZodError unhandled. 공유 helper 로 추출하여 여러 dialog·form 이 동일 resolver 사용.
// (당시 예시였던 OKX passphrase 분기는 C 이식 W3-F 에서 Bybit 단일화로 제거됐다.)

import type { Resolver, FieldValues } from "react-hook-form";
import { type core, type ZodType } from "zod/v4";

export function zodV4Resolver<TValues extends FieldValues>(
  schema: ZodType<TValues>,
): Resolver<TValues> {
  const resolver: Resolver<TValues> = async (values) => {
    const parsed = await schema.safeParseAsync(values);
    if (parsed.success) {
      return { values: parsed.data as TValues, errors: {} };
    }
    const errors: Record<string, { type: string; message: string }> = {};
    for (const issue of parsed.error.issues as core.$ZodIssue[]) {
      const path = issue.path.join(".");
      if (!errors[path]) {
        errors[path] = { type: issue.code, message: issue.message };
      }
    }
    return {
      values: {},
      // RHF nested errors path 는 flat key (예: "passphrase") 이므로 cast 안전.
      errors: errors as unknown as Awaited<
        ReturnType<Resolver<TValues>>
      >["errors"],
    };
  };
  return resolver;
}
