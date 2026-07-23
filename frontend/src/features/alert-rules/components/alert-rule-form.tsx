"use client";

// 세션에 적용할 알림 규칙을 인라인으로 생성한다.
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";

import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { ApiError } from "@/lib/api-client";
import { zodV4Resolver } from "@/lib/zod-v4-resolver";

import { useCreateAlertRule } from "../hooks";
import {
  AlertRuleCreateRequestSchema,
  type AlertRuleCreateRequest,
} from "../schemas";

interface AlertRuleFormProps {
  sessionId: string;
  onSuccess?: () => void;
}

function isDuplicateActiveRule(error: unknown): boolean {
  if (!(error instanceof ApiError) || error.status !== 409) return false;
  if (error.code === "alert_rule_already_active") return true;
  const detail = error.detail;
  return (
    typeof detail === "object" &&
    detail !== null &&
    "detail" in detail &&
    typeof detail.detail === "object" &&
    detail.detail !== null &&
    "code" in detail.detail &&
    detail.detail.code === "alert_rule_already_active"
  );
}

export function AlertRuleForm({ sessionId, onSuccess }: AlertRuleFormProps) {
  const createRule = useCreateAlertRule(sessionId);
  const [serverError, setServerError] = useState<string | null>(null);
  const form = useForm<AlertRuleCreateRequest>({
    resolver: zodV4Resolver(AlertRuleCreateRequestSchema),
    defaultValues: {
      rule_type: "loss_limit",
      threshold_percent: undefined,
      channel: "telegram",
    },
  });
  const ruleType = useWatch({ control: form.control, name: "rule_type" });

  const onSubmit = async (values: AlertRuleCreateRequest): Promise<void> => {
    setServerError(null);
    const request =
      values.rule_type === "loss_limit"
        ? values
        : { rule_type: values.rule_type, channel: values.channel };
    try {
      await createRule.mutateAsync(request);
      form.reset();
      onSuccess?.();
    } catch (error) {
      setServerError(
        isDuplicateActiveRule(error)
          ? "이미 같은 유형의 활성 규칙이 있습니다."
          : "알림 규칙을 만들지 못했습니다.",
      );
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="mt-3 space-y-3" noValidate>
        <FormField
          control={form.control}
          name="rule_type"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="field-label">규칙 유형</FormLabel>
              <FormControl>
                <select
                  className="input"
                  aria-label="규칙 유형"
                  value={field.value}
                  onChange={(event) => {
                    const value = event.target.value as AlertRuleCreateRequest["rule_type"];
                    field.onChange(value);
                    if (value === "watchdog") form.setValue("threshold_percent", undefined);
                  }}
                >
                  <option value="loss_limit">손실 한도</option>
                  <option value="watchdog">워치독</option>
                </select>
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {ruleType === "loss_limit" ? (
          <FormField
            control={form.control}
            name="threshold_percent"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="field-label">손실 한도 (%)</FormLabel>
                <FormControl>
                  <input
                    className="input"
                    inputMode="decimal"
                    placeholder="5"
                    aria-label="손실 한도 (%)"
                    value={field.value ?? ""}
                    onChange={field.onChange}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        ) : null}
        <FormField
          control={form.control}
          name="channel"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="field-label">발송 채널</FormLabel>
              <FormControl>
                <select className="input" aria-label="발송 채널" {...field}>
                  <option value="telegram">telegram</option>
                  <option value="slack">slack</option>
                  <option value="both">both</option>
                </select>
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {serverError ? (
          <p className="notice-inline" role="alert">
            {serverError}
          </p>
        ) : null}
        <button className="btn btn-primary" type="submit" disabled={createRule.isPending}>
          {createRule.isPending ? "만드는 중..." : "알림 규칙 저장"}
        </button>
      </form>
    </Form>
  );
}
