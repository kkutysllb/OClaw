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
  InfoIcon,
  type LucideIcon,
} from "lucide-react";

import { useI18n } from "@/core/i18n/hooks";
import {
  BUILTIN_WORK_MODES,
  resolveWorkModeByAgentName,
  type WorkMode,
  type WorkModeIcon as WorkModeIconType,
} from "@/core/work-modes";
import { useWorkModes } from "@/core/work-modes/hooks";
import { cn } from "@/lib/utils";

import { Tooltip } from "./tooltip";

/** Map WorkModeIcon identifier → Lucide icon component. */
const ICON_MAP: Record<WorkModeIconType, LucideIcon> = {
  Briefcase: Briefcase,
  Code2: Code2,
  PenTool: PenTool,
  ResearchIcon: PenTool, // alias — Lucide has no "Research"
  GraduationCap: GraduationCap,
  Sparkles: SparklesIcon,
  Bot: BotIcon,
  Wrench: WrenchIcon,
  Palette: Palette,
};

/**
 * Resolve a dot-path i18n key (e.g. "workModes.task.name") from the
 * translation object. Returns the literal string if it doesn't start with
 * "workModes." or the path can't be resolved.
 */
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
 * Render the work-mode selector buttons.
 *
 * The selector loads work modes from ``GET /api/work-modes`` via
 * :hook:`useWorkModes`. While the request is in-flight (or if the backend
 * is unreachable), it falls back to the compiled-in
 * :data:`BUILTIN_WORK_MODES` so the UI is never empty.
 *
 * Selection is by ``work_mode_id`` — the canonical id that the backend uses
 * to resolve the effective skill set. The legacy ``selectedAgentName`` prop
 * is accepted for backward compatibility with threads that were created
 * before ``work_mode_id`` was threaded through the runtime context.
 */
export function WorkModeSelector({
  selectedWorkModeId,
  selectedAgentName,
  onSelect,
  onShowDetail,
  className,
}: {
  /**
   * Current ``work_mode_id`` from thread context (undefined = default/task).
   * Preferred over ``selectedAgentName`` when both are supplied.
   */
  selectedWorkModeId?: string | undefined;
  /**
   * Legacy: current ``agent_name`` from thread context. Used to derive the
   * active mode when ``selectedWorkModeId`` is absent (older threads).
   */
  selectedAgentName?: string | undefined;
  /** Called when the user picks a different work mode. */
  onSelect: (workModeId: string | undefined) => void;
  /** Called when the user clicks the info icon to open the detail drawer. */
  onShowDetail?: (modeId: string) => void;
  className?: string;
}) {
  const { t } = useI18n();
  const { data, isLoading } = useWorkModes();

  // Always have the builtin list available as a baseline so the selector
  // renders instantly on first paint (before the API resolves) and as a
  // fallback when the backend is unreachable.
  const builtinModes: WorkMode[] = BUILTIN_WORK_MODES;

  // Once the API payload arrives, prefer its ordering and any custom modes
  // it may carry. We merge by id so the API's authoritative list wins for
  // duplicates but builtins stay visible if the API hasn't returned yet.
  //
  // Builtin mode names are i18n keys (resolved via resolveI18nPath below).
  // Custom mode names are literal strings set by the user — use them as-is.
  const apiModes: WorkMode[] = isLoading
    ? []
    : data.modes.map((m) => ({
        id: m.id,
        name: m.builtin ? `workModes.${m.id}.name` : m.name,
        description: m.builtin
          ? m.description
            ? `workModes.${m.id}.description`
            : undefined
          : m.description,
        icon: iconForModeId(m.id),
        agent_name: agentNameForModeId(m.id),
        builtin: m.builtin,
        enabled: true,
        order: m.is_default ? 0 : 10,
      }));

  const seenIds = new Set<string>();
  const modes: WorkMode[] = [];
  for (const mode of [...apiModes, ...builtinModes]) {
    if (seenIds.has(mode.id)) continue;
    seenIds.add(mode.id);
    modes.push(mode);
  }
  modes.sort((a, b) => a.order - b.order);

  // Resolve the currently-active mode. Prefer the explicit work_mode_id;
  // fall back to deriving from agent_name for legacy threads.
  const currentMode = selectedWorkModeId
    ? (modes.find((m) => m.id === selectedWorkModeId) ??
      resolveWorkModeByAgentName(selectedAgentName))
    : resolveWorkModeByAgentName(selectedAgentName);

  return (
    <div
      className={cn(
        "flex items-center justify-center gap-2",
        className,
      )}
    >
      {modes.map((mode) => {
        const Icon = ICON_MAP[mode.icon] ?? BotIcon;
        const isSelected = currentMode.id === mode.id;
        const displayName = resolveI18nPath(mode.name, t) ?? mode.name;
        const description = mode.description
          ? resolveI18nPath(mode.description, t)
          : undefined;

        return (
          <Tooltip key={mode.id} content={description}>
            <div className="inline-flex items-center gap-0.5">
              <button
                type="button"
                onClick={() => onSelect(mode.id)}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full border py-1 pl-3 text-xs font-medium transition-all duration-200",
                  onShowDetail ? "pr-2" : "pr-3",
                  "hover:-translate-y-0.5 hover:shadow-sm",
                  isSelected
                    ? "border-primary/40 bg-primary/10 text-primary"
                    : "border-border text-muted-foreground hover:border-border/80 hover:text-foreground",
                )}
              >
                <Icon className="size-3" />
                {displayName}
              </button>
              {onShowDetail && (
                <Tooltip content="查看模式详情">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onShowDetail(mode.id);
                    }}
                    className={cn(
                      "inline-flex size-5 items-center justify-center rounded-full border text-muted-foreground/70 transition-colors",
                      "hover:bg-muted hover:text-foreground",
                      isSelected
                        ? "border-primary/30"
                        : "border-border/60",
                    )}
                    aria-label={`查看 ${displayName} 详情`}
                  >
                    <InfoIcon className="size-2.5" />
                  </button>
                </Tooltip>
              )}
            </div>
          </Tooltip>
        );
      })}

    </div>
  );
}

/** Map a mode id to its canonical Lucide icon identifier. */
function iconForModeId(modeId: string): WorkModeIconType {
  if (modeId === "coding") return "Code2";
  if (modeId === "task" || modeId === "office") return "Briefcase";
  return "Bot";
}

/** Map a mode id to its agent_name override (undefined for the default mode). */
function agentNameForModeId(modeId: string): string | undefined {
  if (modeId === "coding") return "coding_agent";
  return undefined;
}
