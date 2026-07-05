"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeftIcon,
  FileCodeIcon,
  PackageIcon,
  SparklesIcon,
} from "lucide-react";

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
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { toast } from "sonner";
import { useI18n } from "@/core/i18n/hooks";
import { useWorkModes } from "@/core/work-modes/hooks";
import { openFilePicker } from "@/core/desktop";
import {
  SKILL_TEMPLATES,
  buildCopyTemplate,
  useCreateSkill,
  useInstallSkillFromUpload,
  useSkills,
  useUploadSupportFiles,
  type CreateMode,
  type SkillTemplate,
  type SupportSubdir,
} from "@/core/skills";
import { SUPPORT_SUBDIRS } from "@/core/skills";
import { cn } from "@/lib/utils";

/**
 * Create-skill wizard.
 *
 * Three creation modes (selected from a home screen):
 *  - `template` : existing flow (Basics → Template → Edit → Preview → Create)
 *  - `upload`   : new flow (Upload .skill → Preview → Install)
 *  - `scripts`  : new flow (Basics → Upload scripts → Edit → Preview → Create+Upload)
 *
 * All modes funnel through `POST /api/skills/custom` (create) or
 * `POST /api/skills/install-upload` (package install) or
 * `POST /api/skills/custom/{name}/support-files` (script upload),
 * bypassing the Agent entirely so the product never lands in the sandbox
 * outputs directory.
 */

const MAX_DESCRIPTION = 1024;
const TEMPLATE_STEPS = 4;
const UPLOAD_STEPS = 2;
const SCRIPTS_STEPS = 4;

interface BasicsForm {
  name: string;
  description: string;
  workModes: string[];
}

const INITIAL_BASICS: BasicsForm = {
  name: "",
  description: "",
  workModes: ["task"],
};

export function CreateSkillWizard({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { t } = useI18n();
  const router = useRouter();
  const { skills } = useSkills();
  const { data: workModesData } = useWorkModes();

  const [mode, setMode] = useState<CreateMode | null>(null);
  const [step, setStep] = useState(1);

  // Shared basics state (template + scripts modes).
  const [basics, setBasics] = useState<BasicsForm>(INITIAL_BASICS);
  // Template-mode-only state.
  const [templateId, setTemplateId] = useState<string | null>(null);
  const [content, setContent] = useState("");
  // Upload-mode-only state.
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  // Scripts-mode-only state.
  const [scriptFiles, setScriptFiles] = useState<File[]>([]);
  const [scriptSubdir, setScriptSubdir] = useState<SupportSubdir>("scripts");

  const createSkill = useCreateSkill();
  const installUpload = useInstallSkillFromUpload();
  const uploadSupport = useUploadSupportFiles();

  const templates = useMemo<SkillTemplate[]>(() => {
    const builtins = [...SKILL_TEMPLATES];
    const copies: SkillTemplate[] = skills
      .filter((s) => s.category === "custom")
      .slice(0, 5)
      .map((s) =>
        buildCopyTemplate(
          s.name,
          `---\nname: ${s.name}\ndescription: ${s.description}\n---\n# ${s.name}\n\nTODO: 基于「${s.name}」修改。\n`,
        ),
      );
    return [...builtins, ...copies];
  }, [skills]);

  // ----- Mode entry / reset -----
  const enterMode = useCallback((m: CreateMode) => {
    setMode(m);
    setStep(1);
  }, []);

  const backToHome = useCallback(() => {
    setMode(null);
    setStep(1);
    setBasics(INITIAL_BASICS);
    setTemplateId(null);
    setContent("");
    setUploadFile(null);
    setScriptFiles([]);
    setScriptSubdir("scripts");
  }, []);

  const handleClose = useCallback(
    (next: boolean) => {
      if (!next) backToHome();
      onOpenChange(next);
    },
    [backToHome, onOpenChange],
  );

  // ----- Template-mode handlers (existing flow) -----
  const applyTemplate = useCallback(
    (template: SkillTemplate) => {
      const name = normaliseName(basics.name) || basics.name;
      setTemplateId(template.id);
      setContent(template.initialContent(name, basics.description || basics.name));
    },
    [basics.name, basics.description],
  );

  const submitTemplate = useCallback(() => {
    const name = normaliseName(basics.name);
    createSkill.mutate(
      {
        name,
        description: basics.description.trim(),
        content: syncFrontmatterName(content, name),
        work_modes: basics.workModes.length > 0 ? basics.workModes : ["task"],
      },
      {
        onSuccess: (created) => {
          toast.success(t.settings.createSkillWizard.success.replace("{name}", created.name));
          backToHome();
          onOpenChange(false);
        },
        onError: (err: unknown) => {
          toast.error(err instanceof Error ? err.message : String(err));
        },
      },
    );
  }, [basics, content, createSkill, t, toast, backToHome, onOpenChange]);

  // ----- Upload-mode handlers -----
  const handlePickSkillFile = useCallback(async () => {
    const files = await openFilePicker({
      multiple: false,
      filters: [{ name: "Skill", extensions: ["skill"] }],
      title: t.settings.createSkillWizard.uploadButton,
    });
    if (files.length > 0) setUploadFile(files[0] ?? null);
  }, [t]);

  const submitUpload = useCallback(() => {
    if (!uploadFile) return;
    installUpload.mutate(
      { file: uploadFile, workModes: basics.workModes.length > 0 ? basics.workModes : ["task"] },
      {
        onSuccess: (result) => {
          toast.success(t.settings.createSkillWizard.success.replace("{name}", result.skill_name));
          backToHome();
          onOpenChange(false);
        },
        onError: (err: unknown) => {
          toast.error(err instanceof Error ? err.message : String(err));
        },
      },
    );
  }, [uploadFile, basics.workModes, installUpload, t, toast, backToHome, onOpenChange]);

  // ----- Scripts-mode handlers -----
  const handlePickScriptFiles = useCallback(async () => {
    const files = await openFilePicker({
      multiple: true,
      title: t.settings.createSkillWizard.scriptsAddMore,
    });
    if (files.length > 0) {
      setScriptFiles((prev) => [...prev, ...files]);
    }
  }, [t]);

  const removeScriptFile = useCallback((idx: number) => {
    setScriptFiles((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  const submitScripts = useCallback(() => {
    const name = normaliseName(basics.name);
    // Step 1: create the skill shell (with SKILL.md).
    createSkill.mutate(
      {
        name,
        description: basics.description.trim(),
        content: syncFrontmatterName(content, name),
        work_modes: basics.workModes.length > 0 ? basics.workModes : ["task"],
      },
      {
        onSuccess: () => {
          // Step 2: upload scripts into the freshly created skill.
          if (scriptFiles.length === 0) {
            toast.success(t.settings.createSkillWizard.success.replace("{name}", name));
            backToHome();
            onOpenChange(false);
            return;
          }
          uploadSupport.mutate(
            { skillName: name, files: scriptFiles, subdir: scriptSubdir },
            {
              onSuccess: () => {
                toast.success(t.settings.createSkillWizard.success.replace("{name}", name));
                backToHome();
                onOpenChange(false);
              },
              onError: (err: unknown) => {
                // Skill created but script upload failed — partial success.
                // Surface a distinct message; the user can retry from the edit UI.
                const detail = err instanceof Error ? err.message : String(err);
                toast.warning(
                  t.settings.createSkillWizard.scriptsPartialFailure.replace("{error}", detail),
                );
              },
            },
          );
        },
        onError: (err: unknown) => {
          toast.error(err instanceof Error ? err.message : String(err));
        },
      },
    );
  }, [basics, content, scriptFiles, scriptSubdir, createSkill, uploadSupport, t, toast, backToHome, onOpenChange]);

  // ----- Derived step count / progress -----
  const totalSteps = mode === "template" ? TEMPLATE_STEPS : mode === "upload" ? UPLOAD_STEPS : mode === "scripts" ? SCRIPTS_STEPS : 1;
  const progress = mode === null ? 0 : (step / totalSteps) * 100;

  // ----- Validation per step -----
  const basicsValid = basics.name.trim().length > 0 && basics.description.trim().length > 0;
  const canAdvance =
    mode === "template"
      ? step === 1
        ? basicsValid
        : step === 2
          ? templateId !== null
          : step === 3
            ? content.trim().length > 0
            : true
      : mode === "upload"
        ? step === 1
          ? uploadFile !== null
          : true
        : mode === "scripts"
          ? step === 1
            ? basicsValid
            : step === 2
              ? true // no minimum script count; user can add later
              : step === 3
                ? content.trim().length > 0
                : true
          : true;

  const goNext = useCallback(() => {
    if (!canAdvance) return;
    // Scripts mode: when entering the Edit step for the first time, seed
    // the SKILL.md from the task template so the user has a starting point
    // rather than a blank editor.
    if (
      mode === "scripts" &&
      step === 2 &&
      content.trim().length === 0
    ) {
      const taskTemplate = SKILL_TEMPLATES.find((tpl) => tpl.id === "task");
      if (taskTemplate) {
        const name = normaliseName(basics.name) || basics.name;
        setContent(taskTemplate.initialContent(name, basics.description || basics.name));
      }
    }
    setStep((s) => Math.min(s + 1, totalSteps));
  }, [canAdvance, totalSteps, mode, step, content, basics.name, basics.description]);

  const goBack = useCallback(() => {
    if (step === 1) {
      backToHome();
    } else {
      setStep((s) => Math.max(s - 1, 1));
    }
  }, [step, backToHome]);

  // ----- Submit dispatch -----
  const submitting =
    createSkill.isPending ||
    installUpload.isPending ||
    uploadSupport.isPending;

  const handleSubmit = useCallback(() => {
    if (mode === "template") submitTemplate();
    else if (mode === "upload") submitUpload();
    else if (mode === "scripts") submitScripts();
  }, [mode, submitTemplate, submitUpload, submitScripts]);

  const handleEnhanceInChat = useCallback(() => {
    const name = normaliseName(basics.name);
    handleClose(false);
    router.push(
      `/workspace/chats/new?mode=skill&workMode=${basics.workModes[0] ?? "task"}&skill=${encodeURIComponent(name)}`,
    );
  }, [basics.name, basics.workModes, handleClose, router]);

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="flex max-h-[90vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-3xl">
        {/* Header */}
        <DialogHeader className="border-b px-6 py-4">
          <DialogTitle className="flex items-center gap-2">
            {mode !== null && (
              <button
                type="button"
                onClick={backToHome}
                className="text-muted-foreground hover:text-foreground"
                title={t.settings.createSkillWizard.backToHome}
              >
                <ArrowLeftIcon className="size-4" />
              </button>
            )}
            <SparklesIcon className="size-4 text-primary" />
            {t.settings.createSkillWizard.title}
          </DialogTitle>
          <DialogDescription className="sr-only">
            {t.settings.createSkillWizard.title}
          </DialogDescription>
          {mode !== null && (
            <div className="mt-3 flex items-center gap-3">
              <Progress value={progress} className="h-1.5 flex-1" />
              <span className="text-muted-foreground text-xs tabular-nums">
                {t.settings.createSkillWizard.stepOf
                  .replace("{current}", String(step))
                  .replace("{total}", String(totalSteps))}
              </span>
            </div>
          )}
        </DialogHeader>

        {/* Body */}
        <ScrollArea className="flex-1">
          <div className="px-6 py-5">
            {mode === null && (
              <StepHome onPick={enterMode} t={t} />
            )}

            {mode === "template" && (
              <>
                {step === 1 && (
                  <StepBasics form={basics} setForm={setBasics} workModesData={workModesData} t={t} />
                )}
                {step === 2 && (
                  <StepTemplate templates={templates} selectedId={templateId} onPick={applyTemplate} t={t} />
                )}
                {step === 3 && <StepEdit content={content} setContent={setContent} t={t} />}
                {step === 4 && (
                  <StepPreview
                    content={content}
                    name={normaliseName(basics.name)}
                    t={t}
                    onEnhanceInChat={handleEnhanceInChat}
                  />
                )}
              </>
            )}

            {mode === "upload" && (
              <>
                {step === 1 && (
                  <StepUploadSkill
                    file={uploadFile}
                    onPick={handlePickSkillFile}
                    onClear={() => setUploadFile(null)}
                    form={basics}
                    setForm={setBasics}
                    workModesData={workModesData}
                    t={t}
                  />
                )}
                {step === 2 && (
                  <StepPreview
                    content={t.settings.createSkillWizard.willCreateAt.replace(
                      "{name}",
                      uploadFile?.name.replace(/\.skill$/i, "") ?? "",
                    )}
                    name={uploadFile?.name.replace(/\.skill$/i, "") ?? ""}
                    t={t}
                    onEnhanceInChat={handleEnhanceInChat}
                    isInstallPreview
                  />
                )}
              </>
            )}

            {mode === "scripts" && (
              <>
                {step === 1 && (
                  <StepBasics form={basics} setForm={setBasics} workModesData={workModesData} t={t} />
                )}
                {step === 2 && (
                  <StepUploadScripts
                    files={scriptFiles}
                    subdir={scriptSubdir}
                    onSubdirChange={setScriptSubdir}
                    onAdd={handlePickScriptFiles}
                    onRemove={removeScriptFile}
                    skillName={normaliseName(basics.name) || basics.name}
                    t={t}
                  />
                )}
                {step === 3 && <StepEdit content={content} setContent={setContent} t={t} />}
                {step === 4 && (
                  <StepPreview
                    content={content}
                    name={normaliseName(basics.name)}
                    t={t}
                    onEnhanceInChat={handleEnhanceInChat}
                  />
                )}
              </>
            )}
          </div>
        </ScrollArea>

        {/* Footer */}
        <DialogFooter className="border-t px-6 py-3">
          <Button variant="ghost" onClick={() => handleClose(false)} disabled={submitting}>
            {t.settings.createSkillWizard.cancel}
          </Button>
          {mode !== null && (
            <Button variant="outline" onClick={goBack} disabled={submitting}>
              {step === 1 ? t.settings.createSkillWizard.backToHome : t.settings.createSkillWizard.back}
            </Button>
          )}
          {mode !== null && step < totalSteps && (
            <Button onClick={goNext} disabled={!canAdvance || submitting}>
              {t.settings.createSkillWizard.next}
            </Button>
          )}
          {mode !== null && step === totalSteps && (
            <Button onClick={handleSubmit} disabled={submitting}>
              {submitting
                ? t.settings.createSkillWizard.creating
                : mode === "upload"
                  ? t.settings.createSkillWizard.create
                  : mode === "scripts"
                    ? t.settings.createSkillWizard.scriptsCreateAndUpload
                    : t.settings.createSkillWizard.create}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Home (mode picker)
// ---------------------------------------------------------------------------

function StepHome({
  onPick,
  t,
}: {
  onPick: (mode: CreateMode) => void;
  t: ReturnType<typeof useI18n>["t"];
}) {
  const cards: { mode: CreateMode; icon: typeof SparklesIcon; label: string; desc: string }[] = [
    {
      mode: "template",
      icon: SparklesIcon,
      label: t.settings.createSkillWizard.modeTemplate,
      desc: t.settings.createSkillWizard.modeTemplateDesc,
    },
    {
      mode: "upload",
      icon: PackageIcon,
      label: t.settings.createSkillWizard.modeUpload,
      desc: t.settings.createSkillWizard.modeUploadDesc,
    },
    {
      mode: "scripts",
      icon: FileCodeIcon,
      label: t.settings.createSkillWizard.modeScripts,
      desc: t.settings.createSkillWizard.modeScriptsDesc,
    },
  ];

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">{t.settings.createSkillWizard.homeTitle}</h2>
        <p className="text-muted-foreground mt-1 text-sm">{t.settings.createSkillWizard.homeDescription}</p>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {cards.map(({ mode, icon: Icon, label, desc }) => (
          <button
            key={mode}
            type="button"
            onClick={() => onPick(mode)}
            className="hover:bg-accent flex flex-col items-start gap-2 rounded-lg border p-4 text-left transition-colors"
          >
            <Icon className="text-primary size-5" />
            <span className="text-sm font-medium">{label}</span>
            <span className="text-muted-foreground text-xs leading-relaxed">{desc}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step: Basics (shared by template + scripts modes)
// ---------------------------------------------------------------------------

interface StepBasicsProps {
  form: BasicsForm;
  setForm: React.Dispatch<React.SetStateAction<BasicsForm>>;
  workModesData: { modes: { id: string; name: string }[] };
  t: ReturnType<typeof useI18n>["t"];
}

function StepBasics({ form, setForm, workModesData, t }: StepBasicsProps) {
  const descriptionLength = form.description.length;
  const normalisedPreview = form.name ? normaliseName(form.name) : "";

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <label htmlFor="skill-name" className="text-sm font-medium">
          {t.settings.createSkillWizard.nameLabel}
        </label>
        <Input
          id="skill-name"
          value={form.name}
          onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
          placeholder={t.settings.createSkillWizard.namePlaceholder}
          autoFocus
        />
        <p className="text-muted-foreground text-xs">
          {normalisedPreview && normalisedPreview !== form.name
            ? `→ ${normalisedPreview}`
            : t.settings.createSkillWizard.nameHint}
        </p>
      </div>

      <div className="space-y-2">
        <label htmlFor="skill-description" className="text-sm font-medium">
          {t.settings.createSkillWizard.descriptionLabel}
        </label>
        <Textarea
          id="skill-description"
          value={form.description}
          onChange={(e) => setForm((p) => ({ ...p, description: e.target.value.slice(0, MAX_DESCRIPTION) }))}
          placeholder={t.settings.createSkillWizard.descriptionPlaceholder}
          rows={3}
        />
        <p className="text-muted-foreground text-xs tabular-nums">
          {t.settings.createSkillWizard.descriptionCount.replace("{count}", String(descriptionLength))}
        </p>
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium">{t.settings.createSkillWizard.workModesLabel}</label>
        <ToggleGroup
          type="multiple"
          value={form.workModes}
          onValueChange={(values) =>
            setForm((p) => ({ ...p, workModes: values.length > 0 ? values : ["task"] }))
          }
          variant="outline"
        >
          {workModesData.modes.map((mode) => (
            <ToggleGroupItem key={mode.id} value={mode.id} aria-label={mode.name}>
              {mode.name}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step: Template (template mode only)
// ---------------------------------------------------------------------------

interface StepTemplateProps {
  templates: SkillTemplate[];
  selectedId: string | null;
  onPick: (template: SkillTemplate) => void;
  t: ReturnType<typeof useI18n>["t"];
}

function StepTemplate({ templates, selectedId, onPick, t }: StepTemplateProps) {
  const labels: Record<string, string> = {
    blank: t.settings.createSkillWizard.templateBlank,
    task: t.settings.createSkillWizard.templateTask,
    coding: t.settings.createSkillWizard.templateCoding,
  };

  return (
    <div className="space-y-3">
      <p className="text-muted-foreground text-sm">{t.settings.createSkillWizard.templateLabel}</p>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {templates.map((template) => {
          const isCopy = template.id.startsWith("copy:");
          const label = isCopy ? template.label : labels[template.id] ?? template.label;
          return (
            <button
              key={template.id}
              type="button"
              onClick={() => onPick(template)}
              className={cn(
                "flex flex-col items-start gap-1 rounded-lg border p-3 text-left transition-colors hover:bg-accent",
                selectedId === template.id ? "border-primary ring-primary ring-1" : "border-border",
              )}
            >
              <span className="text-sm font-medium">{label}</span>
              <span className="text-muted-foreground line-clamp-2 text-xs">
                {isCopy ? t.settings.createSkillWizard.templateCopyHint : template.description}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step: Edit (template + scripts modes)
// ---------------------------------------------------------------------------

interface StepEditProps {
  content: string;
  setContent: React.Dispatch<React.SetStateAction<string>>;
  t: ReturnType<typeof useI18n>["t"];
}

function StepEdit({ content, setContent, t }: StepEditProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label htmlFor="skill-content" className="text-sm font-medium">
          {t.settings.createSkillWizard.editLabel}
        </label>
        <span className="text-muted-foreground text-xs">{t.settings.createSkillWizard.editHint}</span>
      </div>
      <Textarea
        id="skill-content"
        value={content}
        onChange={(e) => setContent(e.target.value)}
        className="min-h-[320px] font-mono text-xs"
        spellCheck={false}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step: Preview (all modes)
// ---------------------------------------------------------------------------

interface StepPreviewProps {
  content: string;
  name: string;
  t: ReturnType<typeof useI18n>["t"];
  onEnhanceInChat: () => void;
  isInstallPreview?: boolean;
}

function StepPreview({ content, name, t, onEnhanceInChat, isInstallPreview }: StepPreviewProps) {
  return (
    <div className="space-y-3">
      <p className="text-muted-foreground text-sm">{t.settings.createSkillWizard.previewHint}</p>
      <div className="text-muted-foreground rounded-md border border-dashed bg-muted/30 px-3 py-2 text-xs">
        {isInstallPreview
          ? content
          : t.settings.createSkillWizard.willCreateAt.replace("{name}", name)}
      </div>
      {!isInstallPreview && (
        <pre className="max-h-[260px] overflow-auto rounded-md border bg-muted/20 p-3 font-mono text-xs whitespace-pre-wrap">
          {content}
        </pre>
      )}
      <div className="flex justify-end">
        <Button variant="outline" size="sm" onClick={onEnhanceInChat}>
          {t.settings.createSkillWizard.enhanceInChat}
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step: Upload .skill (upload mode)
// ---------------------------------------------------------------------------

interface StepUploadSkillProps {
  file: File | null;
  onPick: () => void;
  onClear: () => void;
  form: BasicsForm;
  setForm: React.Dispatch<React.SetStateAction<BasicsForm>>;
  workModesData: { modes: { id: string; name: string }[] };
  t: ReturnType<typeof useI18n>["t"];
}

function StepUploadSkill({ file, onPick, onClear, form, setForm, workModesData, t }: StepUploadSkillProps) {
  return (
    <div className="space-y-5">
      <div className="space-y-3">
        {file ? (
          <div className="flex items-center justify-between rounded-md border bg-muted/30 px-4 py-3">
            <div className="flex min-w-0 flex-col">
              <span className="truncate text-sm font-medium">
                {t.settings.createSkillWizard.uploadSelected.replace("{name}", file.name)}
              </span>
              <span className="text-muted-foreground text-xs">
                {t.settings.createSkillWizard.uploadSize.replace("{size}", formatBytes(file.size))}
              </span>
            </div>
            <Button variant="ghost" size="sm" onClick={onPick}>
              {t.settings.createSkillWizard.uploadReplace}
            </Button>
          </div>
        ) : (
          <button
            type="button"
            onClick={onPick}
            className="hover:bg-accent flex w-full flex-col items-center gap-2 rounded-lg border border-dashed py-10 text-center transition-colors"
          >
            <PackageIcon className="text-muted-foreground size-6" />
            <span className="text-sm">{t.settings.createSkillWizard.uploadDropHere}</span>
            <span className="text-muted-foreground text-xs">{t.settings.createSkillWizard.uploadButton}</span>
          </button>
        )}
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium">{t.settings.createSkillWizard.workModesLabel}</label>
        <ToggleGroup
          type="multiple"
          value={form.workModes}
          onValueChange={(values) =>
            setForm((p) => ({ ...p, workModes: values.length > 0 ? values : ["task"] }))
          }
          variant="outline"
        >
          {workModesData.modes.map((mode) => (
            <ToggleGroupItem key={mode.id} value={mode.id} aria-label={mode.name}>
              {mode.name}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      </div>

      {file && (
        <Button variant="outline" size="sm" onClick={onClear} className="w-fit">
          <ArrowLeftIcon className="size-3" />
          {t.settings.createSkillWizard.uploadReplace}
        </Button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step: Upload Scripts (scripts mode)
// ---------------------------------------------------------------------------

interface StepUploadScriptsProps {
  files: File[];
  subdir: SupportSubdir;
  onSubdirChange: (subdir: SupportSubdir) => void;
  onAdd: () => void;
  onRemove: (idx: number) => void;
  skillName: string;
  t: ReturnType<typeof useI18n>["t"];
}

function StepUploadScripts({
  files,
  subdir,
  onSubdirChange,
  onAdd,
  onRemove,
  skillName,
  t,
}: StepUploadScriptsProps) {
  const subdirLabel = (s: SupportSubdir): string => {
    switch (s) {
      case "scripts":
        return t.settings.createSkillWizard.scriptsSubdirScripts;
      case "references":
        return t.settings.createSkillWizard.scriptsSubdirReferences;
      case "templates":
        return t.settings.createSkillWizard.scriptsSubdirTemplates;
      case "assets":
        return t.settings.createSkillWizard.scriptsSubdirAssets;
      default:
        return s;
    }
  };

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <label className="text-sm font-medium">{t.settings.createSkillWizard.scriptsSubdir}</label>
        <Select value={subdir} onValueChange={(v) => onSubdirChange(v as SupportSubdir)}>
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {SUPPORT_SUBDIRS.map((s) => (
              <SelectItem key={s} value={s}>
                {subdirLabel(s)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-muted-foreground text-xs">
          {t.settings.createSkillWizard.scriptsUploadHint
            .replace("{name}", skillName)
            .replace("{subdir}", subdir)}
        </p>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">
            {t.settings.createSkillWizard.uploadSelected.replace("{name}", `${files.length} file(s)`)}
          </span>
          <Button variant="outline" size="sm" onClick={onAdd}>
            {t.settings.createSkillWizard.scriptsAddMore}
          </Button>
        </div>
        {files.length === 0 ? (
          <button
            type="button"
            onClick={onAdd}
            className="hover:bg-accent flex w-full flex-col items-center gap-2 rounded-lg border border-dashed py-8 text-center transition-colors"
          >
            <FileCodeIcon className="text-muted-foreground size-5" />
            <span className="text-sm">{t.settings.createSkillWizard.scriptsAddMore}</span>
          </button>
        ) : (
          <ul className="divide-y rounded-md border">
            {files.map((f, idx) => (
              <li key={`${f.name}-${idx}`} className="flex items-center justify-between px-3 py-2">
                <div className="flex min-w-0 flex-col">
                  <span className="truncate text-sm">{f.name}</span>
                  <span className="text-muted-foreground text-xs">{formatBytes(f.size)}</span>
                </div>
                <Button variant="ghost" size="sm" onClick={() => onRemove(idx)}>
                  {t.settings.createSkillWizard.scriptsRemove}
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Lowercase + replace separators with hyphens + collapse repeats (mirrors backend). */
function normaliseName(raw: string): string {
  return raw
    .trim()
    .toLowerCase()
    .replace(/[\s_]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-+|-+$/g, "");
}

/** Rewrite the frontmatter `name:` line so it matches the request name. */
function syncFrontmatterName(content: string, name: string): string {
  const fmMatch = content.match(/^---\n([\s\S]*?)\n---/);
  if (!fmMatch || fmMatch[0] === undefined || fmMatch[1] === undefined) {
    return content;
  }
  const newFrontmatter = fmMatch[1].replace(/^name:.*$/m, `name: ${name}`);
  return content.replace(fmMatch[0], `---\n${newFrontmatter}\n---`);
}

/** Human-readable byte size (mirrors the formatting used elsewhere). */
function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
