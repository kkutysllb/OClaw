"use client";

import {
  BriefcaseIcon,
  Code2Icon,
  LayersIcon,
  PencilIcon,
  PlusIcon,
  SparklesIcon,
  Trash2Icon,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useI18n } from "@/core/i18n/hooks";
import {
  useCreateWorkMode,
  useDeleteWorkMode,
  useUpdateWorkMode,
  useWorkModes,
} from "@/core/work-modes/hooks";
import type { WorkModeDetail } from "@/core/work-modes/types";
import { toast } from "sonner";

import { SettingsSection } from "./settings-section";

// ---------------------------------------------------------------------------
// Mode icon mapping
// ---------------------------------------------------------------------------
const MODE_ICONS: Record<string, typeof BriefcaseIcon> = {
  task: BriefcaseIcon,
  coding: Code2Icon,
};

// ---------------------------------------------------------------------------
// Form state
// ---------------------------------------------------------------------------
interface FormState {
  id: string;
  name: string;
  description: string;
  orchestration_hint: string;
  focus_areas: string;
}

const EMPTY_FORM: FormState = {
  id: "",
  name: "",
  description: "",
  orchestration_hint: "",
  focus_areas: "",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export function WorkModesSettingsPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { data, isLoading } = useWorkModes();
  const createMode = useCreateWorkMode();
  const updateMode = useUpdateWorkMode();
  const deleteMode = useDeleteWorkMode();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);

  const modes = data.modes;
  const builtinModes = modes.filter((m) => m.builtin);
  const customModes = modes.filter((m) => !m.builtin);

  // --- Create / Edit handlers ---
  const openCreateDialog = () => {
    setForm(EMPTY_FORM);
    setEditingId(null);
    setDialogOpen(true);
  };

  const openEditDialog = (mode: WorkModeDetail) => {
    setForm({
      id: mode.id,
      name: mode.name,
      description: mode.description ?? "",
      orchestration_hint: mode.orchestration_hint ?? "",
      focus_areas: (mode.focus_areas ?? []).join(", "),
    });
    setEditingId(mode.id);
    setDialogOpen(true);
  };

  const handleSave = async () => {
    const trimmedId = form.id.trim();
    const trimmedName = form.name.trim();
    if (!trimmedId || !trimmedName) return;

    const payload = {
      id: trimmedId,
      name: trimmedName,
      description: form.description.trim() || undefined,
      orchestration_hint: form.orchestration_hint.trim() || undefined,
      focus_areas: form.focus_areas
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    };

    try {
      if (editingId) {
        // Update existing mode
        const { id: _id, ...patch } = payload;
        await updateMode.mutateAsync({ modeId: editingId, ...patch });
        toast.success(
          t.settings.workModes.updatedSuccess.replace("{name}", trimmedName),
        );
      } else {
        // Create new mode
        await createMode.mutateAsync(payload);
        toast.success(
          t.settings.workModes.createdSuccess.replace("{name}", trimmedName),
        );
        // After creation, show hint to go to skills page
        toast.info(t.settings.workModes.goToSkillsHint, {
          duration: 6000,
          action: {
            label: t.settings.workModes.goToSkills,
            onClick: () => router.push("/workspace/skills"),
          },
        });
      }
      setDialogOpen(false);
      setForm(EMPTY_FORM);
      setEditingId(null);
    } catch {
      // Error is handled by the mutation's error state
    }
  };

  const handleDelete = async (mode: WorkModeDetail) => {
    const confirmed = window.confirm(
      t.settings.workModes.confirmDelete.replace("{name}", mode.name),
    );
    if (!confirmed) return;

    try {
      await deleteMode.mutateAsync(mode.id);
      toast.success(
        t.settings.workModes.deletedSuccess.replace("{name}", mode.name),
      );
    } catch {
      // Error is handled by the mutation's error state
    }
  };

  // --- Render ---
  return (
    <SettingsSection
      title={t.settings.workModes.title}
      description={t.settings.workModes.description}
      icon={<LayersIcon className="w-5 h-5 text-indigo-500" />}
    >
      {/* Create button */}
      <div className="mb-4 flex justify-end">
        <Button
          size="sm"
          onClick={openCreateDialog}
          disabled={createMode.isPending || updateMode.isPending}
        >
          <PlusIcon className="size-4" />
          {t.settings.workModes.createMode}
        </Button>
      </div>

      {isLoading ? (
        <div className="text-muted-foreground text-sm">
          {t.common.loading}
        </div>
      ) : (
        <div className="space-y-6">
          {/* Builtin modes */}
          {builtinModes.length > 0 && (
            <div>
              <h4 className="mb-2 text-sm font-medium text-muted-foreground">
                {t.settings.workModes.builtin}
              </h4>
              <div className="space-y-2">
                {builtinModes.map((mode) => (
                  <ModeCard
                    key={mode.id}
                    mode={mode}
                    t={t}
                    builtin
                  />
                ))}
              </div>
            </div>
          )}

          {/* Custom modes */}
          <div>
            <h4 className="mb-2 text-sm font-medium text-muted-foreground">
              {t.settings.workModes.custom}
            </h4>
            {customModes.length === 0 ? (
              <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                {t.settings.workModes.noCustomModes}
              </div>
            ) : (
              <div className="space-y-2">
                {customModes.map((mode) => (
                  <ModeCard
                    key={mode.id}
                    mode={mode}
                    t={t}
                    onEdit={() => openEditDialog(mode)}
                    onDelete={() => handleDelete(mode)}
                    onGoToSkills={() => router.push("/workspace/skills")}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Create / Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[85vh] grid-rows-[auto_minmax(0,1fr)_auto] overflow-hidden">
          <DialogHeader className="shrink-0">
            <DialogTitle>
              {editingId
                ? t.settings.workModes.editMode
                : t.settings.workModes.createMode}
            </DialogTitle>
            <DialogDescription>
              {t.settings.workModes.description}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2 overflow-y-auto min-h-0 pr-1">
            {/* Mode ID */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium">
                {t.settings.workModes.modeId}
              </label>
              <Input
                value={form.id}
                onChange={(e) => setForm({ ...form, id: e.target.value })}
                placeholder={t.settings.workModes.modeIdPlaceholder}
                disabled={!!editingId}
              />
              <p className="text-xs text-muted-foreground">
                {t.settings.workModes.modeIdHint}
              </p>
            </div>

            {/* Display Name */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium">
                {t.settings.workModes.modeName}
              </label>
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder={t.settings.workModes.modeNamePlaceholder}
              />
            </div>

            {/* Description */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium">
                {t.settings.workModes.modeDescription}
              </label>
              <Input
                value={form.description}
                onChange={(e) =>
                  setForm({ ...form, description: e.target.value })
                }
                placeholder={t.settings.workModes.modeDescriptionPlaceholder}
                maxLength={200}
              />
            </div>

            {/* Orchestration Hint */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium">
                {t.settings.workModes.orchestrationHint}
              </label>
              <Textarea
                value={form.orchestration_hint}
                onChange={(e) =>
                  setForm({ ...form, orchestration_hint: e.target.value })
                }
                placeholder={t.settings.workModes.orchestrationHintPlaceholder}
                rows={5}
                maxLength={4000}
                className="max-h-[200px] resize-y"
              />
              <p className="text-xs text-muted-foreground">
                {t.settings.workModes.orchestrationHintHint}
              </p>
            </div>

            {/* Focus Areas */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium">
                {t.settings.workModes.focusAreas}
              </label>
              <Input
                value={form.focus_areas}
                onChange={(e) =>
                  setForm({ ...form, focus_areas: e.target.value })
                }
                placeholder={t.settings.workModes.focusAreasPlaceholder}
              />
            </div>
          </div>

          <DialogFooter className="shrink-0">
            <Button
              variant="outline"
              onClick={() => setDialogOpen(false)}
            >
              {t.settings.workModes.cancel}
            </Button>
            <Button
              onClick={handleSave}
              disabled={
                !form.id.trim() ||
                !form.name.trim() ||
                createMode.isPending ||
                updateMode.isPending
              }
            >
              {t.settings.workModes.save}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </SettingsSection>
  );
}

// ---------------------------------------------------------------------------
// Mode Card sub-component
// ---------------------------------------------------------------------------
function ModeCard({
  mode,
  t,
  builtin = false,
  onEdit,
  onDelete,
  onGoToSkills,
}: {
  mode: WorkModeDetail;
  t: ReturnType<typeof useI18n>["t"];
  builtin?: boolean;
  onEdit?: () => void;
  onDelete?: () => void;
  onGoToSkills?: () => void;
}) {
  const Icon = MODE_ICONS[mode.id] ?? SparklesIcon;
  const skillCount = mode.skills?.length ?? mode.skill_count ?? 0;

  return (
    <div className="flex items-center justify-between rounded-lg border p-4 transition-colors hover:bg-muted/30">
      <div className="flex min-w-0 flex-1 items-start gap-3">
        <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted">
          <Icon className="size-4 text-muted-foreground" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-medium">{mode.name}</span>
            <span
              className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[10px] font-semibold ${
                builtin
                  ? "bg-sky-500/15 text-sky-500"
                  : "bg-emerald-500/15 text-emerald-500"
              }`}
            >
              {builtin
                ? t.settings.workModes.builtin
                : t.settings.workModes.custom}
            </span>
          </div>
          {mode.description && (
            <p className="mt-0.5 text-sm text-muted-foreground line-clamp-1">
              {mode.description}
            </p>
          )}
          <p className="mt-0.5 text-xs text-muted-foreground">
            {t.settings.workModes.skillCount.replace(
              "{count}",
              String(skillCount),
            )}
            {mode.orchestration_hint && " · "}
            {mode.orchestration_hint && (
              <span className="text-muted-foreground/70">
                {mode.orchestration_hint.slice(0, 80)}
                {mode.orchestration_hint.length > 80 && "..."}
              </span>
            )}
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex shrink-0 items-center gap-1">
        {!builtin && (
          <>
            {onEdit && (
              <Button
                size="sm"
                variant="ghost"
                className="size-8 p-0"
                onClick={onEdit}
                title={t.settings.workModes.editMode}
              >
                <PencilIcon className="size-4" />
              </Button>
            )}
            {onDelete && (
              <Button
                size="sm"
                variant="ghost"
                className="size-8 p-0 text-destructive hover:text-destructive"
                onClick={onDelete}
                title={t.settings.workModes.deleteMode}
              >
                <Trash2Icon className="size-4" />
              </Button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
