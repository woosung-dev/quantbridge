"use client";

// Sprint 7c T5 / FE-03:
// EditorView — 3 탭(코드/파싱/메타) + 헤더(back/백테스트stub/저장/삭제) + URL 쿼리 동기화.
// Sprint FE-03 에서 편집 버퍼를 Zustand edit-store 로 lift-up. 페이지 진입 시
// loadServerSnapshot 으로 store 초기화, Save 는 header 에서 담당, isDirty 시 unload 경고.

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
  ArrowLeftIcon,
  Loader2Icon,
  PlayIcon,
  SaveIcon,
  Trash2Icon,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  selectIsDirty,
  selectPineSource,
  selectStrategyId,
  useEditStore,
} from "@/features/strategy/edit-store";
import { useStrategy, useUpdateStrategy } from "@/features/strategy/hooks";
import { PARSE_STATUS_META } from "@/features/strategy/utils";

import { DeleteDialog } from "./delete-dialog";
import { TabCode } from "./tab-code";
import { TabMetadata } from "./tab-metadata";
import { TabParse } from "./tab-parse";
import { TabWebhook } from "./tab-webhook";

type TabKey = "code" | "parse" | "metadata" | "webhook";

export function EditorView({ id }: { id: string }) {
  const router = useRouter();
  const params = useSearchParams();
  const initialTab = (params.get("tab") as TabKey) || "code";
  const [tab, setTab] = useState<TabKey>(initialTab);
  const [deleteOpen, setDeleteOpen] = useState(
    params.get("action") === "delete" || params.get("action") === "archive",
  );

  const { data: strategy, isLoading, isError } = useStrategy(id);

  // Sprint FE-03: store 구독 — scalar selector 만 사용 (LESSON-004).
  const storeStrategyId = useEditStore(selectStrategyId);
  const isDirty = useEditStore(selectIsDirty);
  const pineSource = useEditStore(selectPineSource);
  const loadServerSnapshot = useEditStore((s) => s.loadServerSnapshot);
  const markSaved = useEditStore((s) => s.markSaved);

  // 서버에서 받은 strategy 로 store 초기화.
  // - isLoading/isError 완료 시 & store 가 다른 strategy 를 보고 있거나 비어있을 때 1회 실행.
  // - primitive dep (strategy.id, strategy.pine_source) 만 넣고 actions 는 store 에서 꺼내 쓰므로
  //   참조가 안정적이다 (Zustand create 반환 actions 는 불변).
  const serverPineSource = strategy?.pine_source;
  const serverStrategyId = strategy?.id;
  useEffect(() => {
    if (serverStrategyId && typeof serverPineSource === "string") {
      if (storeStrategyId !== serverStrategyId) {
        loadServerSnapshot(serverStrategyId, serverPineSource);
      }
    }
  }, [serverStrategyId, serverPineSource, storeStrategyId, loadServerSnapshot]);

  // URL 쿼리 ?action=archive/delete 초기 처리.
  // useSearchParams는 Next.js router 외부 API라 effect 내 setState가 정당한 동기화 패턴.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    const action = params.get("action");
    if (action === "delete" || action === "archive") {
      setDeleteOpen(true);
    }
  }, [params]);
  /* eslint-enable react-hooks/set-state-in-effect */

  // Sprint FE-03: unload 경고 — isDirty 동안 browser tab close / refresh 시 확인.
  // 최신 브라우저는 preventDefault() 만으로 leave prompt 를 띄운다 (returnValue 는 legacy).
  useEffect(() => {
    if (!isDirty) return;
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isDirty]);

  const update = useUpdateStrategy(id, {
    onSuccess: () => {
      markSaved(new Date());
      toast.success("저장되었습니다");
    },
    onError: (e) => toast.error(`저장 실패: ${e.message}`),
  });

  const handleSave = () => {
    if (!isDirty || update.isPending) return;
    update.mutate({ pine_source: pineSource });
  };

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="h-96 animate-pulse rounded-md bg-[color:var(--bg-alt)]" />
      </div>
    );
  }
  if (isError || !strategy) {
    return (
      <div className="mx-auto max-w-[1200px] px-6 py-8">
        <div className="mx-auto max-w-md rounded-[var(--radius-lg)] border border-[color:var(--destructive-light)] bg-[color:var(--destructive-light)] p-8 text-center">
          <h2 className="font-display text-lg font-semibold text-[color:var(--destructive)]">
            전략을 찾을 수 없습니다
          </h2>
          <p className="mt-2 text-sm text-[color:var(--text-secondary)]">
            전략이 삭제되었거나 접근 권한이 없을 수 있습니다.
          </p>
          <Button
            variant="outline"
            className="mt-5"
            render={<Link href="/strategies" />}
            nativeButton={false}
          >
            ← 전략 목록으로
          </Button>
        </div>
      </div>
    );
  }

  const meta = PARSE_STATUS_META[strategy.parse_status];

  return (
    <div className="mx-auto max-w-[1400px] px-6 py-6">
      <header className="sticky top-0 z-10 mb-5 flex flex-wrap items-center gap-3 bg-[color:var(--bg-primary)] py-2">
        <Button
          variant="ghost"
          size="icon"
          aria-label="목록으로"
          render={<Link href="/strategies" />}
          nativeButton={false}
        >
          <ArrowLeftIcon className="size-4" />
        </Button>
        <div className="min-w-0 flex-1">
          <h1 className="truncate font-display text-xl font-bold">{strategy.name}</h1>
          <p className="flex items-center gap-2 text-xs text-[color:var(--text-muted)]">
            <Badge variant="outline" data-tone={meta.tone}>
              {meta.label}
            </Badge>
            <span className="font-mono">
              {strategy.symbol ?? "—"} · {strategy.timeframe ?? "—"} · Pine {strategy.pine_version}
            </span>
            {strategy.is_archived && <Badge variant="secondary">보관됨</Badge>}
            {isDirty && (
              // Sprint 44 W F2: dirty pulse — 저장 잊지 않도록 0.18 amber ring 호흡 (2.4s).
              <Badge
                variant="outline"
                data-tone="warn"
                className="motion-safe:animate-[dirtyPulse_2.4s_ease-out_infinite]"
              >
                저장되지 않은 변경
              </Badge>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={handleSave}
            disabled={!isDirty || update.isPending}
            aria-label="변경사항 저장"
            aria-busy={update.isPending || undefined}
          >
            {update.isPending ? (
              // Sprint 44 W F2: loading 시 spinner + 텍스트 미세 dim.
              <Loader2Icon className="size-4 motion-safe:animate-spin" aria-hidden />
            ) : (
              <SaveIcon className="size-4" />
            )}
            <span className={update.isPending ? "opacity-80" : undefined}>
              {update.isPending ? "저장 중..." : "저장"}
            </span>
          </Button>
          <Button
            variant="outline"
            render={<Link href={`/backtests/new?strategy_id=${strategy.id}`} />}
            nativeButton={false}
            aria-label="백테스트 실행"
          >
            <PlayIcon className="size-4" />
            백테스트 실행
          </Button>
          <Button variant="outline" onClick={() => setDeleteOpen(true)}>
            <Trash2Icon className="size-4" />
            삭제
          </Button>
        </div>
      </header>

      <Tabs
        value={tab}
        onValueChange={(v) => {
          const next = v as TabKey;
          setTab(next);
          router.replace(`?tab=${next}`);
        }}
      >
        {/* Sprint 43 W9: prototype 01 의 .tab-bar underline + active primary 색상 정합.
            shadcn variant="line" 가 native underline (after pseudo-element 200ms transition).
            data-active:text-primary 로 prototype primary color 매칭. */}
        <TabsList
          variant="line"
          className="h-11 w-full justify-start gap-0 border-b border-[color:var(--border)] bg-transparent px-4 [&_[data-state=active]]:font-semibold [&_[data-state=active]]:text-[color:var(--primary)] [&_[data-state=active]]:after:bg-[color:var(--primary)]"
        >
          <TabsTrigger value="code">코드</TabsTrigger>
          <TabsTrigger value="parse">파싱 결과</TabsTrigger>
          <TabsTrigger value="metadata">메타데이터</TabsTrigger>
          <TabsTrigger value="webhook">Webhook</TabsTrigger>
        </TabsList>
        <TabsContent value="code" className="mt-4">
          <TabCode strategy={strategy} />
        </TabsContent>
        <TabsContent value="parse" className="mt-4">
          <TabParse strategy={strategy} />
        </TabsContent>
        <TabsContent value="metadata" className="mt-4">
          <TabMetadata strategy={strategy} />
        </TabsContent>
        <TabsContent value="webhook" className="mt-4">
          <TabWebhook strategyId={strategy.id} />
        </TabsContent>
      </Tabs>

      <DeleteDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        strategyId={strategy.id}
        strategyName={strategy.name}
        onDone={() => {
          toast.success("전략이 삭제되었습니다");
          router.push("/strategies");
        }}
        onArchived={() => {
          toast.success("전략이 보관되었습니다");
          setDeleteOpen(false);
          router.refresh();
        }}
      />
    </div>
  );
}
