"use client";

import { LockIcon, SparklesIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import {
  Item,
  ItemActions,
  ItemTitle,
  ItemContent,
  ItemDescription,
} from "@/components/ui/item";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useI18n } from "@/core/i18n/hooks";
import { useEnableSkill, useSkills } from "@/core/skills/hooks";
import type { Skill } from "@/core/skills/type";
import { useWorkModes } from "@/core/work-modes/hooks";
import { env } from "@/env";
import { cn } from "@/lib/utils";

import { SettingsSection } from "./settings-section";

export function SkillSettingsPage({ onClose }: { onClose?: () => void } = {}) {
  const { t } = useI18n();
  const { skills, isLoading, error } = useSkills();
  return (
    <SettingsSection
      title={t.settings.skills.title}
      description={t.settings.skills.description}
      icon={<SparklesIcon className="w-5 h-5 text-violet-500" />}
    >
      {isLoading ? (
        <div className="text-muted-foreground text-sm">{t.common.loading}</div>
      ) : error ? (
        <div>Error: {error.message}</div>
      ) : (
        <SkillSettingsList skills={skills} onClose={onClose} />
      )}
    </SettingsSection>
  );
}

function SkillSettingsList({
  skills,
  onClose,
}: {
  skills: Skill[];
  onClose?: () => void;
}) {
  const { t } = useI18n();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<string>("builtin");
  const { mutate: enableSkill } = useEnableSkill();
  const { data: workModesData } = useWorkModes();

  const modeTabs = workModesData.modes;

  // Locked core skills are global — the same set across all work modes.
  const lockedSkillIds = useMemo(() => {
    const ids = new Set<string>();
    for (const mode of modeTabs) {
      for (const s of mode.skills) {
        if (s.locked) ids.add(s.skill_id);
      }
    }
    return ids;
  }, [modeTabs]);

  const isSkillLocked = (skillName: string): boolean =>
    lockedSkillIds.has(skillName);

  const filteredSkills = useMemo(() => {
    let result = skills;
    if (activeTab === "builtin") {
      // The "内置" tab shows only the locked core skills.
      result = result.filter((s) => lockedSkillIds.has(s.name));
    } else {
      const mode = modeTabs.find((m) => m.id === activeTab);
      if (mode) {
        const modeSkillIds = new Set(mode.skills.map((s) => s.skill_id));
        // Work-mode tabs exclude locked core skills.
        result = result.filter(
          (s) => modeSkillIds.has(s.name) && !lockedSkillIds.has(s.name),
        );
      }
    }
    return result;
  }, [skills, activeTab, modeTabs, lockedSkillIds]);

  const handleCreateSkill = () => {
    onClose?.();
    router.push("/workspace/chats/new?mode=skill");
  };

  const isStatic = env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true";

  return (
    <div className="flex w-full flex-col gap-4">
      <header className="flex justify-between">
        <div className="flex gap-2">
          <Tabs defaultValue="builtin" onValueChange={setActiveTab}>
            <TabsList variant="line">
              <TabsTrigger value="builtin">{t.common.builtin}</TabsTrigger>
              {modeTabs.map((mode) => (
                <TabsTrigger key={mode.id} value={mode.id}>
                  {mode.name}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        </div>
        <div>
          <Button size="sm" onClick={handleCreateSkill}>
            <SparklesIcon className="size-4" />
            {t.settings.skills.createSkill}
          </Button>
        </div>
      </header>
      {filteredSkills.length === 0 && (
        <EmptySkill onCreateSkill={handleCreateSkill} />
      )}
      {filteredSkills.length > 0 &&
        filteredSkills.map((skill) => {
          const locked = isSkillLocked(skill.name);
          return (
            <Item className="w-full" variant="outline" key={skill.name}>
              <ItemContent>
                <ItemTitle>
                  <div className="flex items-center gap-2">
                    {skill.name}
                    {locked && (
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10px] font-semibold",
                          "bg-amber-500/15 text-amber-400",
                        )}
                      >
                        <LockIcon className="size-2.5" />
                        {t.common.locked}
                      </span>
                    )}
                  </div>
                </ItemTitle>
                <ItemDescription className="line-clamp-4">
                  {skill.description}
                </ItemDescription>
              </ItemContent>
              <ItemActions>
                <Switch
                  checked={skill.enabled}
                  disabled={isStatic || locked}
                  onCheckedChange={(checked) =>
                    enableSkill({ skillName: skill.name, enabled: checked })
                  }
                />
              </ItemActions>
            </Item>
          );
        })}
    </div>
  );
}

function EmptySkill({ onCreateSkill }: { onCreateSkill: () => void }) {
  const { t } = useI18n();
  return (
    <Empty>
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <SparklesIcon />
        </EmptyMedia>
        <EmptyTitle>{t.settings.skills.emptyTitle}</EmptyTitle>
        <EmptyDescription>
          {t.settings.skills.emptyDescription}
        </EmptyDescription>
      </EmptyHeader>
      <EmptyContent>
        <Button onClick={onCreateSkill}>{t.settings.skills.emptyButton}</Button>
      </EmptyContent>
    </Empty>
  );
}
