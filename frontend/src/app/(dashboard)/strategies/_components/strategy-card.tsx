// 전략 카드 — 06 prototype 의 status-indicator + meta-badge + hover lift 매핑
"use client";

import Link from "next/link";
import { ArrowRightIcon, MoreVerticalIcon } from "lucide-react";
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
    <Card
      // Precision Instrument: hover 는 Card data-hoverable opt-in (1px lift + 보더 강조) SSOT.
      data-hoverable="true"
      className="group relative cursor-pointer focus-within:ring-2 focus-within:ring-[color:var(--primary-light)]"
      aria-label={`${strategy.name} 전략`}
    >
      {/* 상단 — status indicator + kebab */}
      <CardHeader className="flex flex-row items-start justify-between gap-2 pb-2">
        <Badge variant="outline" data-tone={meta.tone}>
          <span aria-hidden="true" className="size-1.5 rounded-full bg-current" />
          {meta.label}
        </Badge>
        <RowActions id={strategy.id} />
      </CardHeader>

      {/* 본문 — 제목 + 메타 (심볼·TF·Pine 버전) */}
      <CardContent className="space-y-2 pb-3">
        <Link
          href={`/strategies/${strategy.id}/edit`}
          className="line-clamp-2 block text-base font-semibold text-[color:var(--text-primary)] transition group-hover:text-[color:var(--primary)]"
        >
          {strategy.name}
        </Link>

        {/* 메타 badge — 심볼 / 타임프레임 / Pine 버전 */}
        <div className="flex flex-wrap items-center gap-1.5">
          {strategy.symbol && (
            <Badge variant="secondary" className="font-mono text-[11px]">
              {strategy.symbol}
            </Badge>
          )}
          {strategy.timeframe && (
            <Badge variant="secondary" className="font-mono text-[11px]">
              {strategy.timeframe}
            </Badge>
          )}
          <span className="font-mono text-[11px] text-[color:var(--text-muted)]">
            · Pine {strategy.pine_version}
          </span>
        </div>

        {/* tag + 보관 + 세션 */}
        <div className="flex flex-wrap items-center gap-1.5">
          {strategy.is_archived && (
            <Badge variant="outline" className="text-[10px]">
              보관됨
            </Badge>
          )}
          {strategy.tags.slice(0, 3).map((t) => (
            <Badge
              key={t}
              variant="outline"
              className="bg-[color:var(--primary-light)] text-[10px] font-normal text-[color:var(--primary)]"
            >
              {t}
            </Badge>
          ))}
          {strategy.tags.length > 3 && (
            <span className="font-mono text-[10px] text-[color:var(--text-muted)]">
              +{strategy.tags.length - 3}
            </span>
          )}
          {strategy.trading_sessions.length === 0 ? (
            <Badge variant="secondary" className="font-mono text-[10px]">
              24h
            </Badge>
          ) : (
            strategy.trading_sessions.slice(0, 2).map((s) => (
              <Badge
                key={s}
                variant="outline"
                className="font-mono text-[10px] uppercase"
              >
                {s}
              </Badge>
            ))
          )}
        </div>
      </CardContent>

      {/* 하단 — 수정 시각 + 편집 CTA */}
      <CardFooter className="flex items-center justify-between border-t border-[color:var(--border)] pt-3 text-xs text-[color:var(--text-muted)]">
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
          className="inline-flex items-center gap-1 font-medium text-[color:var(--primary)] transition hover:underline"
        >
          편집
          <ArrowRightIcon aria-hidden="true" className="size-3.5" />
        </Link>
      </CardFooter>
    </Card>
  );
}

function RowActions({ id }: { id: string }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button
            variant="ghost"
            size="icon"
            aria-label="카드 액션 메뉴"
            className="opacity-60 transition group-hover:opacity-100"
          />
        }
      >
        <MoreVerticalIcon className="size-4" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem render={<Link href={`/strategies/${id}/edit`} />}>
          편집
        </DropdownMenuItem>
        <DropdownMenuItem
          render={<Link href={`/backtests/new?strategy_id=${id}`} />}
        >
          백테스트
        </DropdownMenuItem>
        <DropdownMenuItem disabled>복제 (준비 중)</DropdownMenuItem>
        <DropdownMenuItem disabled>공유 (준비 중)</DropdownMenuItem>
        <DropdownMenuItem
          render={<Link href={`/strategies/${id}/edit?action=archive`} />}
        >
          보관
        </DropdownMenuItem>
        <DropdownMenuItem
          render={<Link href={`/strategies/${id}/edit?action=delete`} />}
        >
          삭제
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
