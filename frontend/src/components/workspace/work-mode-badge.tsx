"use client";

import { Briefcase, Code2, SparklesIcon, type LucideIcon } from "lucide-react";

import { useI18n } from "@/core/i18n/hooks";
import {
  resolveWorkModeById,
  useWorkModes,
  type WorkModeDetail,
} from "@/core/work-modes";
import { cn } from "@/lib/utils";

// Icon lookup for builtin modes. Custom modes default to SparklesIcon.
const BUILTIN_ICONS: Record<string, LucideIcon> = {
  task: Briefcase,
  coding: Code2,
};

/**
 * Map a legacy ``agent_name`` to a work-mode id by matching against the
 * API-backed mode list. Returns ``undefined`` when no match is found.
 */
function _agentNameToModeId(
  modes: WorkModeDetail[],
  agentName: string | undefined,
): string | undefined {
  if (!agentName) return undefined;
  // coding_agent → coding, etc. Only builtin modes carry agent_name mapping.
  return modes.find(
    (m) => m.builtin && m.lead_agent_name === agentName,
  )?.id;
}

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
  const { data } = useWorkModes();

  // Resolve from the API-backed list (includes custom modes).
  // Falls back to default when workModeId / agentName are absent.
  const mode = resolveWorkModeById(
    data.modes,
    workModeId ?? _agentNameToModeId(data.modes, agentName),
  );
  const Icon = mode.builtin
    ? (BUILTIN_ICONS[mode.id] ?? Briefcase)
    : SparklesIcon;
  // Builtin mode names are i18n keys (e.g. "workModes.task.name");
  // custom mode names are literal strings set by the user.
  const displayName = mode.builtin
    ? (resolveI18nPath(mode.name, t) ?? mode.name)
    : mode.name;

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
