"use client";

// Sprint 7c T5: EditorView — 3 탭(코드/파싱/메타) + 헤더(back/백테스트stub/삭제) + URL 쿼리 동기화.
// asChild prop은 Base UI에서 미지원 → render prop으로 변환 (Button render={<Link />}).

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeftIcon, PlayIcon, Trash2Icon } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useStrategy } from "@/features/strategy/hooks";
import { PARSE_STATUS_META } from "@/features/strategy/utils";

import { DeleteDialog } from "./delete-dialog";
import { TabCode } from "./tab-code";
import { TabMetadata } from "./tab-metadata";
import { TabParse } from "./tab-parse";

type TabKey = "code" | "parse" | "metadata";

export function EditorView({ id }: { id: string }) {
  const router = useRouter();
  const params = useSearchParams();
  const initialTab = (params.get("tab") as TabKey) || "code";
  const [tab, setTab] = useState<TabKey>(initialTab);
  const [deleteOpen, setDeleteOpen] = useState(
    params.get("action") === "delete" || params.get("action") === "archive",
  );

  const { data: strategy, isLoading, isError } = useStrategy(id);

  // URL 쿼리 ?action=archive/delete 초기 처리.
  // 아카이브 바로가기는 별도 다이얼로그 없이 DeleteDialog의 archive fallback 재사용.
  // useSearchParams는 Next.js router 외부 API라 effect 내 setState가 정당한 동기화 패턴.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    const action = params.get("action");
    if (action === "delete" || action === "archive") {
      setDeleteOpen(true);
    }
  }, [params]);
  /* eslint-enable react-hooks/set-state-in-effect */

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="h-96 animate-pulse rounded-md bg-[color:var(--bg-alt)]" />
      </div>
    );
  }
  if (isError || !strategy) {
    return (
      <div className="p-8">
        <p className="text-destructive">전략을 불러오지 못했습니다.</p>
        <Button
          variant="outline"
          className="mt-4"
          render={<Link href="/strategies" />}
          nativeButton={false}
        >
          목록으로
        </Button>
      </div>
    );
  }

  const meta = PARSE_STATUS_META[strategy.parse_status];

  return (
    <div className="mx-auto max-w-[1400px] px-6 py-6">
      <header className="mb-5 flex flex-wrap items-center gap-3">
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
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => router.push(`/backtest?strategy_id=${strategy.id}`)}
            disabled
            title="백테스트 탭은 Sprint 7b에서 연결됩니다"
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
        <TabsList>
          <TabsTrigger value="code">코드</TabsTrigger>
          <TabsTrigger value="parse">파싱 결과</TabsTrigger>
          <TabsTrigger value="metadata">메타데이터</TabsTrigger>
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
