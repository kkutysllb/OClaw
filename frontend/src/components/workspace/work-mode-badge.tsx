"use client";

import {
  Briefcase,
  Code2,
  GraduationCap,
  Palette,
  PenTool,
  BotIcon,
  WrenchIcon,
  SparklesIcon,
  type LucideIcon,
} from "lucide-react";

import { useI18n } from "@/core/i18n/hooks";
import {
  resolveWorkMode,
  resolveWorkModeByAgentName,
  type WorkModeIcon as WorkModeIconType,
} from "@/core/work-modes";
import { cn } from "@/lib/utils";

const ICON_MAP: Record<WorkModeIconType, LucideIcon> = {
  Briefcase: Briefcase,
  Code2: Code2,
  PenTool: PenTool,
  ResearchIcon: PenTool,
  GraduationCap: GraduationCap,
  Sparkles: SparklesIcon,
  Bot: BotIcon,
  Wrench: WrenchIcon,
  Palette: Palette,
};

function resolveI18nPath(path: string, obj: unknown): string | undefined {
  if (!path.startsWith("workModes.")) return path;
  const parts = path.split(".");
  let current: unknown = obj;
  for (const part of parts) {
    if (current && typeof current === "object" && part in current) {
      current = (current as Record<string, unknown>)[part];
    } else {
      return undefined;
    }
  }
  return typeof current === "string" ? current : undefined;
}

/**
 * Compact work mode indicator for the conversation header.
 *
 * Shows the active work mode (e.g. "日常办公") as a small badge.
 * Only rendered for existing conversations — the full selector
 * is shown on the new-thread screen.
 *
 * Accepts either ``workModeId`` (preferred) or ``agentName`` (legacy).
 * When both are absent the default mode is displayed.
 */
export function WorkModeBadge({
  workModeId,
  agentName,
  className,
}: {
  /** Preferred: current ``work_mode_id`` from thread context. */
  workModeId?: string | undefined;
  /** Legacy: current ``agent_name`` from thread context. */
  agentName?: string | undefined;
  className?: string;
}) {
  const { t } = useI18n();
  // Prefer the explicit work_mode_id; fall back to deriving from agent_name
  // for legacy threads created before the work_mode_id contract.
  const mode = workModeId
    ? resolveWorkMode(workModeId)
    : resolveWorkModeByAgentName(agentName);
  const Icon = ICON_MAP[mode.icon] ?? BotIcon;
  const displayName = resolveI18nPath(mode.name, t) ?? mode.name;

  return (
    <div
      className={cn(
        "inline-flex shrink-0 items-center gap-1.5 rounded-md border px-2 py-1",
        "text-muted-foreground",
        className,
      )}
    >
      <Icon className="size-3" />
      <span className="text-xs font-medium">{displayName}</span>
    </div>
  );
}
