"use client";

import {
  ClockIcon,
  CoinsIcon,
  Code2Icon,
  MessageCircleIcon,
  SparklesIcon,
  TerminalIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  SidebarGroup,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { useI18n } from "@/core/i18n/hooks";

export function WorkspaceNavChatList() {
  const { t } = useI18n();
  const pathname = usePathname();

  return (
    <SidebarGroup className="pt-1">
      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton
            isActive={pathname.startsWith("/workspace/coding")}
            asChild
          >
            <Link className="text-muted-foreground" href="/workspace/coding">
              <Code2Icon className="text-emerald-500" />
              <span>{t.sidebar.coding}</span>
            </Link>
          </SidebarMenuButton>
        </SidebarMenuItem>
        <SidebarMenuItem>
          <SidebarMenuButton
            isActive={pathname.startsWith("/workspace/skills")}
            asChild
          >
            <Link className="text-muted-foreground" href="/workspace/skills">
              <SparklesIcon className="text-amber-500" />
              <span>{t.sidebar.skills}</span>
            </Link>
          </SidebarMenuButton>
        </SidebarMenuItem>
        <SidebarMenuItem>
          <SidebarMenuButton
            isActive={pathname.startsWith("/workspace/channels")}
            asChild
          >
            <Link className="text-muted-foreground" href="/workspace/channels">
              <MessageCircleIcon className="text-violet-500" />
              <span>{t.sidebar.channels}</span>
            </Link>
          </SidebarMenuButton>
        </SidebarMenuItem>
        <SidebarMenuItem>
          <SidebarMenuButton
            isActive={pathname.startsWith("/workspace/mcp")}
            asChild
          >
            <Link className="text-muted-foreground" href="/workspace/mcp">
              <TerminalIcon className="text-amber-500" />
              <span>{t.sidebar.mcp}</span>
            </Link>
          </SidebarMenuButton>
        </SidebarMenuItem>
        <SidebarMenuItem>
          <SidebarMenuButton
            isActive={pathname.startsWith("/workspace/crons")}
            asChild
          >
            <Link className="text-muted-foreground" href="/workspace/crons">
              <ClockIcon className="text-orange-500" />
              <span>{t.sidebar.crons}</span>
            </Link>
          </SidebarMenuButton>
        </SidebarMenuItem>
        <SidebarMenuItem>
          <SidebarMenuButton
            isActive={pathname.startsWith("/workspace/token-usage")}
            asChild
          >
            <Link className="text-muted-foreground" href="/workspace/token-usage">
              <CoinsIcon className="text-emerald-500" />
              <span>{t.sidebar.tokenUsage}</span>
            </Link>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarGroup>
  );
}
