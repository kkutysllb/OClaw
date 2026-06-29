"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  addSkillToWorkMode,
  createWorkMode,
  deleteWorkMode,
  loadWorkModes,
  removeSkillFromWorkMode,
  updateWorkMode,
} from "./api";
import { FALLBACK_WORK_MODES } from "./api";
import type {
  CustomWorkModeCreateRequest,
  CustomWorkModeUpdateRequest,
  WorkModeDetail,
  WorkModesListResponse,
} from "./types";

/**
 * React hook that loads work modes from ``GET /api/work-modes``.
 *
 * Always returns a usable payload — on error or while loading, the fallback
 * builtin modes are returned so the UI can render a selector. The ``isLoading``
 * flag distinguishes "still fetching the real list" from "this is the
 * fallback".
 *
 * @returns ``{ data, isLoading, error, refetch }`` where ``data`` is always
 *     defined (never ``undefined``).
 */
export function useWorkModes(): {
  data: WorkModesListResponse;
  isLoading: boolean;
  error: unknown;
  refetch: () => void;
} {
  const query = useQuery({
    queryKey: ["work-modes"],
    queryFn: () => loadWorkModes(),
    // Keep the data fresh — work-mode skill lists can change after the user
    // adds/removes a skill, and we want the selector to reflect that without
    // a manual refresh.
    staleTime: 30_000,
  });

  return {
    data: query.data ?? FALLBACK_WORK_MODES,
    isLoading: query.isLoading,
    error: query.error,
    refetch: () => {
      void query.refetch();
    },
  };
}

/**
 * Resolve a single work mode by id, using the API-backed list.
 *
 * Falls back to the first mode (or a synthesized default) when the id is
 * unknown — never returns ``undefined``.
 */
export function resolveWorkModeById(
  modes: WorkModeDetail[],
  modeId: string | undefined,
): WorkModeDetail {
  if (modeId) {
    const found = modes.find((m) => m.id === modeId);
    if (found) return found;
  }
  const defaultMode = modes.find((m) => m.is_default) ?? modes[0];
  if (defaultMode) return defaultMode;
  // Last-resort synthetic mode so callers never have to handle undefined.
  return {
    id: "task",
    name: "日常办公",
    description: "",
    builtin: true,
    editable: false,
    is_default: true,
    skills: [],
  };
}

/**
 * Mutation hook: add a skill to a work mode.
 *
 * On success the ``["work-modes"]`` query is invalidated so the UI refetches
 * the updated effective-skill list.
 */
export function useAddSkillToWorkMode() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ modeId, skillName }: { modeId: string; skillName: string }) =>
      addSkillToWorkMode(modeId, skillName),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["work-modes"] });
    },
  });
}

/**
 * Mutation hook: remove a skill from a work mode.
 *
 * On success the ``["work-modes"]`` query is invalidated. Callers should
 * catch errors to surface the "locked skill cannot be removed" message.
 */
export function useRemoveSkillFromWorkMode() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ modeId, skillName }: { modeId: string; skillName: string }) =>
      removeSkillFromWorkMode(modeId, skillName),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["work-modes"] });
    },
  });
}

/**
 * Mutation hook: create a custom work mode.
 *
 * On success the ``["work-modes"]`` query is invalidated so the selector
 * and settings UI reflect the new mode immediately.
 */
export function useCreateWorkMode() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (req: CustomWorkModeCreateRequest) => createWorkMode(req),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["work-modes"] });
    },
  });
}

/**
 * Mutation hook: update a custom work mode.
 *
 * Accepts the ``modeId`` plus partial update fields. On success the
 * ``["work-modes"]`` query is invalidated.
 */
export function useUpdateWorkMode() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (
      args: { modeId: string } & CustomWorkModeUpdateRequest,
    ) => {
      const { modeId, ...patch } = args;
      return updateWorkMode(modeId, patch);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["work-modes"] });
    },
  });
}

/**
 * Mutation hook: delete a custom work mode.
 *
 * On success the ``["work-modes"]`` query is invalidated. Callers should
 * catch errors to surface the "builtin mode cannot be deleted" message.
 */
export function useDeleteWorkMode() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (modeId: string) => deleteWorkMode(modeId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["work-modes"] });
    },
  });
}
