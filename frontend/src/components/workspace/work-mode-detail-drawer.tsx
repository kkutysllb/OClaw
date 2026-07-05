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
  LockIcon,
  type LucideIcon,
} from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useWorkModes, resolveWorkModeById } from "@/core/work-modes/hooks";
import type { WorkModeDetail } from "@/core/work-modes/types";
import { cn } from "@/lib/utils";

const ICON_MAP: Record<string, LucideIcon> = {
  Briefcase,
  Code2,
  PenTool,
  ResearchIcon: PenTool,
  GraduationCap,
  Sparkles: SparklesIcon,
  Bot: BotIcon,
  Wrench: WrenchIcon,
  Palette,
};

/**
 * Detail drawer that visualizes the full work-mode runtime graph:
 * mode → lead agent → bound skills → orchestration guidance.
 *
 * Triggered by an info icon on each mode button in WorkModeSelector.
 * Shows the user (and reminds the system) what each mode means.
 */
export function WorkModeDetailDrawer({
  modeId,
  onClose,
}: {
  modeId: string | null;
  onClose: () => void;
}) {
  const { data } = useWorkModes();
  const mode: WorkModeDetail | null = modeId
    ? resolveWorkModeById(data.modes, modeId)
    : null;

  return (
    <Dialog open={modeId !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-lg">
        {mode && <ModeDetailBody mode={mode} />}
      </DialogContent>
    </Dialog>
  );
}

function ModeDetailBody({ mode }: { mode: WorkModeDetail }) {
  const iconKey = mode.id === "coding" ? "Code2" : mode.id === "task" ? "Briefcase" : "Bot";
  const Icon = ICON_MAP[iconKey] ?? BotIcon;
  const leadName = mode.lead_agent_name ?? mode.name;
  const skillCount = mode.skill_count ?? mode.skills.length;
  const focusAreas = mode.focus_areas ?? [];
  const nonLockedSkills = mode.skills.filter((s) => !s.locked).slice(0, 8);
  const lockedSkills = mode.skills.filter((s) => s.locked);

  return (
    <>
      <DialogHeader>
        <div className="flex items-center gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Icon className="size-5" />
          </div>
          <div className="min-w-0 flex-1">
            <DialogTitle className="truncate">{mode.name}</DialogTitle>
            <DialogDescription className="mt-1 line-clamp-2">
              {mode.description?.trim()
                ? mode.description
                : `Work mode: ${mode.id}`}
            </DialogDescription>
          </div>
          {mode.is_default && (
            <span className="shrink-0 rounded-md bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold text-primary">
              默认
            </span>
          )}
        </div>
      </DialogHeader>

      <div className="space-y-4 py-2">
        {/* Lead Agent */}
        <section>
          <div className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
            <BotIcon className="size-3" />
            Lead 智能体
          </div>
          <div className="rounded-md border bg-muted/30 px-3 py-2">
            <div className="text-sm font-medium">{leadName}</div>
            <div className="text-muted-foreground mt-0.5 text-xs">
              这个模式由 {leadName} 主理，负责解析用户意图并编排任务执行。
            </div>
          </div>
        </section>

        {/* Focus Areas */}
        {focusAreas.length > 0 && (
          <section>
            <div className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              <SparklesIcon className="size-3" />
              关注领域
            </div>
            <div className="flex flex-wrap gap-1.5">
              {focusAreas.map((area) => (
                <span
                  key={area}
                  className="inline-flex items-center rounded-md border border-primary/30 bg-primary/5 px-2 py-0.5 text-xs font-medium text-primary/80"
                >
                  {area}
                </span>
              ))}
            </div>
          </section>
        )}

        {/* Bound Skills */}
        <section>
          <div className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
            <WrenchIcon className="size-3" />
            绑定技能
            <span className="ml-1 rounded-md bg-muted px-1.5 py-0.5 text-[10px] font-normal text-muted-foreground">
              {skillCount} 个
            </span>
          </div>
          {nonLockedSkills.length > 0 ? (
            <div className="flex flex-wrap gap-1">
              {nonLockedSkills.map((s) => (
                <span
                  key={s.skill_id}
                  className="inline-flex items-center rounded border bg-card px-1.5 py-0.5 text-[11px] font-mono"
                >
                  {s.skill_id}
                </span>
              ))}
              {mode.skills.length > nonLockedSkills.length + lockedSkills.length && (
                <span className="text-muted-foreground self-center text-[11px]">
                  +{mode.skills.length - nonLockedSkills.length - lockedSkills.length} 个…
                </span>
              )}
            </div>
          ) : (
            <div className="text-muted-foreground text-xs italic">无可配置技能</div>
          )}
          {lockedSkills.length > 0 && (
            <div className="mt-2 flex items-center gap-1 text-[11px] text-amber-500/80">
              <LockIcon className="size-2.5" />
              另有 {lockedSkills.length} 个内置锁定技能（不可关闭）
            </div>
          )}
        </section>

        {/* Orchestration Hint */}
        {mode.orchestration_hint && (
          <section>
            <div className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              <InfoIcon className="size-3" />
              任务编排指导
            </div>
            <pre
              className={cn(
                "max-h-40 overflow-y-auto whitespace-pre-wrap rounded-md border bg-muted/20",
                "px-3 py-2 text-xs leading-relaxed font-sans",
              )}
            >
              {mode.orchestration_hint}
            </pre>
          </section>
        )}
      </div>
    </>
  );
}
