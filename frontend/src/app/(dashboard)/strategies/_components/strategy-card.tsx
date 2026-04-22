"use client";

import Link from "next/link";
import { MoreVerticalIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { StrategyListItem } from "@/features/strategy/schemas";
import { PARSE_STATUS_META } from "@/features/strategy/utils";

export function StrategyCard({ strategy }: { strategy: StrategyListItem }) {
  const meta = PARSE_STATUS_META[strategy.parse_status];
  return (
    <Card className="group relative transition hover:-translate-y-0.5 hover:shadow-[var(--card-shadow-hover)]">
      <CardHeader className="flex flex-row items-start justify-between gap-2 pb-2">
        <div className="min-w-0">
          <Link
            href={`/strategies/${strategy.id}/edit`}
            className="text-base font-semibold text-[color:var(--text-primary)] hover:text-[color:var(--primary)]"
          >
            {strategy.name}
          </Link>
          <p className="mt-1 flex items-center gap-1 font-mono text-xs text-[color:var(--text-muted)]">
            <span>{strategy.symbol ?? "심볼 없음"}</span>
            <span>·</span>
            <span>{strategy.timeframe ?? "TF 없음"}</span>
            <span>·</span>
            <span>Pine {strategy.pine_version}</span>
          </p>
        </div>
        <RowActions id={strategy.id} />
      </CardHeader>
      <CardContent className="pb-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline" data-tone={meta.tone}>
            {meta.label}
          </Badge>
          {strategy.is_archived && <Badge variant="secondary">보관됨</Badge>}
          {strategy.tags.slice(0, 3).map((t) => (
            <Badge key={t} variant="secondary" className="font-normal">
              {t}
            </Badge>
          ))}
          {strategy.trading_sessions.length === 0 ? (
            <Badge variant="secondary" className="font-mono text-xs">
              24h
            </Badge>
          ) : (
            strategy.trading_sessions.map((s) => (
              <Badge key={s} variant="outline" className="font-mono text-xs uppercase">
                {s}
              </Badge>
            ))
          )}
        </div>
      </CardContent>
      <CardFooter className="flex items-center justify-between pt-0 text-xs text-[color:var(--text-muted)]">
        <time dateTime={strategy.updated_at}>
          {new Intl.DateTimeFormat("ko-KR", {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          }).format(new Date(strategy.updated_at))}
        </time>
        <Link
          href={`/strategies/${strategy.id}/edit`}
          className="font-medium text-[color:var(--primary)] hover:underline"
        >
          편집 →
        </Link>
      </CardFooter>
    </Card>
  );
}

function RowActions({ id }: { id: string }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={<Button variant="ghost" size="icon" aria-label="카드 액션 메뉴" />}
      >
        <MoreVerticalIcon className="size-4" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem render={<Link href={`/strategies/${id}/edit`} />}>
          편집
        </DropdownMenuItem>
        <DropdownMenuItem disabled>복제 (Sprint 7d+)</DropdownMenuItem>
        <DropdownMenuItem disabled>공유 (Sprint 7d+)</DropdownMenuItem>
        <DropdownMenuItem render={<Link href={`/strategies/${id}/edit?action=archive`} />}>
          보관
        </DropdownMenuItem>
        <DropdownMenuItem render={<Link href={`/strategies/${id}/edit?action=delete`} />}>
          삭제
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
