import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { enableSkill, installSkill, updateSkillWorkModes } from "./api";
import type { InstallSkillRequest } from "./api";

import { loadSkills } from ".";

export function useSkills() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["skills"],
    queryFn: () => loadSkills(),
  });
  return { skills: data ?? [], isLoading, error };
}

export function useEnableSkill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      skillName,
      enabled,
    }: {
      skillName: string;
      enabled: boolean;
    }) => {
      await enableSkill(skillName, enabled);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["skills"] });
    },
  });
}

export function useUpdateSkillWorkModes() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      skillName,
      workModes,
    }: {
      skillName: string;
      workModes: string[];
    }) => {
      await updateSkillWorkModes(skillName, workModes);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["skills"] });
      void queryClient.invalidateQueries({ queryKey: ["work-modes"] });
    },
  });
}

export function useInstallSkill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (request: InstallSkillRequest) => {
      return await installSkill(request);
    },
    onSuccess: (result) => {
      if (result.success) {
        void queryClient.invalidateQueries({ queryKey: ["skills"] });
        void queryClient.invalidateQueries({ queryKey: ["work-modes"] });
      }
    },
  });
}
