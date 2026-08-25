// 거래소 계정 등록 다이얼로그. Bybit demo/live 모드로 API key/secret 을 입력받아
// RegisterAccountRequestSchema(zodV4Resolver)로 검증한 뒤 useRegisterExchangeAccount
// mutation 으로 등록한다. 현재 연결 거래소는 Bybit 하나뿐이라 passphrase 는 항상 null 로 보낸다.
"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";

import { zodV4Resolver } from "@/lib/zod-v4-resolver";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useRegisterExchangeAccount } from "../hooks";
import { RegisterAccountRequestSchema, type RegisterAccountRequest } from "../schemas";

export function RegisterExchangeAccountDialog() {
  const [open, setOpen] = useState(false);
  const register = useRegisterExchangeAccount();

  const form = useForm<RegisterAccountRequest>({
    // Phase C QA hotfix (2026-05-30) — Zod v4 superRefine custom issue 가
    // @hookform/resolvers/zod 와 호환 안 됨 → 공유 zodV4Resolver 사용.
    resolver: zodV4Resolver(RegisterAccountRequestSchema),
    defaultValues: {
      exchange: "bybit",
      mode: "demo",
      label: null,
      api_key: "",
      api_secret: "",
      passphrase: null,
    },
  });

  const onSubmit = async (values: RegisterAccountRequest) => {
    // P1-1/11 (S7-A): test-order-dialog 패턴 — clear → try → setError on catch.
    // 이전엔 try/catch 없이 mutateAsync 가 throw 시 unhandled rejection → 사용자 무피드백.
    form.clearErrors("root.serverError");
    try {
      // C 이식(W3-F): 연결 거래소는 Bybit 하나뿐이라 passphrase 는 항상 null 로 보낸다.
      await register.mutateAsync({ ...values, passphrase: null });
      setOpen(false);
      form.reset();
    } catch (err) {
      const message = err instanceof Error ? err.message : "계정 등록 실패";
      form.setError("root.serverError", { type: "manual", message });
    }
  };

  const rootError = form.formState.errors.root?.serverError?.message;

  return (
    <>
      <Button size="sm" onClick={() => setOpen(true)}>
        계정 추가
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[85dvh] overflow-y-auto sm:max-w-md">
          <DialogHeader>
            <DialogTitle>거래소 계정 등록</DialogTitle>
          </DialogHeader>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="exchange"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>거래소</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="거래소 선택" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="bybit">Bybit</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      현재 연결된 거래소는 Bybit 하나입니다.
                    </p>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="mode"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>모드</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="demo">데모</SelectItem>
                        <SelectItem value="live">라이브</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="label"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>레이블 (선택)</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="예: bybit-demo-main"
                        {...field}
                        value={field.value ?? ""}
                        onChange={(e) => field.onChange(e.target.value || null)}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="api_key"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>API Key</FormLabel>
                    <FormControl>
                      <Input placeholder="API Key" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="api_secret"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>API Secret</FormLabel>
                    <FormControl>
                      <Input type="password" placeholder="API Secret" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              {rootError ? (
                <p
                  role="alert"
                  className="rounded-md border border-destructive/30 bg-destructive-light px-3 py-2 text-sm text-destructive"
                >
                  {rootError}
                </p>
              ) : null}
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                  취소
                </Button>
                <Button type="submit" disabled={register.isPending}>
                  {register.isPending ? "등록 중..." : "등록"}
                </Button>
              </div>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </>
  );
}
