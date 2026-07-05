"use client";

import {
  BotIcon,
  BriefcaseIcon,
  CalculatorIcon,
  CameraIcon,
  ChartBarIcon,
  ClockIcon,
  CoinsIcon,
  Code2Icon,
  FlaskConicalIcon,
  GlobeIcon,
  GraduationCapIcon,
  MessageCircleIcon,
  MusicIcon,
  PaletteIcon,
  PenLineIcon,
  SearchIcon,
  SparklesIcon,
  TerminalIcon,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { useI18n } from "@/core/i18n/hooks";
import { useWorkModes } from "@/core/work-modes/hooks";

/**
 * Icon name → component map for custom work-mode sidebar entries.
 *
 * Kept in sync with the ICON_PRESETS palette in
 * ``work-modes-settings-page.tsx`` so that an icon chosen at mode-creation
 * time renders correctly here. Unknown names fall back to ``BotIcon``.
 */
const MODE_ICON_MAP: Record<string, LucideIcon> = {
  Bot: BotIcon,
  Briefcase: BriefcaseIcon,
  Search: SearchIcon,
  PenLine: PenLineIcon,
  ChartBar: ChartBarIcon,
  FlaskConical: FlaskConicalIcon,
  GraduationCap: GraduationCapIcon,
  Palette: PaletteIcon,
  Music: MusicIcon,
  Camera: CameraIcon,
  Calculator: CalculatorIcon,
  Globe: GlobeIcon,
};

function resolveModeIcon(iconName: string | undefined): LucideIcon {
  if (!iconName) return BotIcon;
  return MODE_ICON_MAP[iconName] ?? BotIcon;
}

export function WorkspaceNavChatList() {
  const { t } = useI18n();
  const pathname = usePathname();
  const { data: workModesData } = useWorkModes();

  // Custom (user-created) modes only — built-in task/coding have their own
  // fixed entries above. Each custom entry links to a new chat pre-seeded
  // with the mode's work_mode_id, mirroring the existing ?workMode= chain.
  const customModes = workModesData.modes.filter((m) => !m.builtin);

  return (
    <>
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

      {customModes.length > 0 && (
        <SidebarGroup className="pt-0">
          <SidebarGroupLabel>{t.sidebar.customModes}</SidebarGroupLabel>
          <SidebarMenu>
            {customModes.map((mode) => {
              const Icon = resolveModeIcon(mode.icon);
              return (
                <SidebarMenuItem key={mode.id}>
                  <SidebarMenuButton asChild>
                    <Link
                      className="text-muted-foreground"
                      href={`/workspace/chats/new?workMode=${encodeURIComponent(mode.id)}`}
                    >
                      <Icon className="text-blue-500" />
                      <span>{mode.name}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              );
            })}
          </SidebarMenu>
        </SidebarGroup>
      )}
    </>
  );
}
