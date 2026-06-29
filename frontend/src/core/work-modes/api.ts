import { fetch } from "@/core/api/fetcher";
import { getBackendBaseURL } from "@/core/config";

import { DEFAULT_WORK_MODE_ID } from "./defaults";
import type { WorkModesListResponse } from "./types";

/**
 * Fallback work-mode payload used when the backend is unreachable or has
 * not yet implemented the ``/api/work-modes`` endpoint.
 *
 * The UI must always be able to render a selector — returning an empty list
 * would leave the user with no way to pick a mode at all. The fallback
 * mirrors the backend's shipped defaults (task + coding) but carries an
 * empty effective-skill list, since the precise locked/added/removed
 * resolution lives server-side.
 */
export const FALLBACK_WORK_MODES: WorkModesListResponse = {
  default_mode_id: DEFAULT_WORK_MODE_ID,
  modes: [
    {
      id: "task",
      name: "日常办公",
      description: "默认办公模式",
      builtin: true,
      editable: false,
      is_default: true,
      skills: [],
    },
    {
      id: "coding",
      name: "编程",
      description: "编程模式",
      builtin: true,
      editable: false,
      is_default: false,
      skills: [],
    },
  ],
};

/**
 * Load all work modes from ``GET /api/work-modes``.
 *
 * On any network/parse error, returns the fallback builtin modes so the UI
 * can keep rendering. Callers that need to distinguish "loaded from server"
 * from "fallback" can check the ``modes[].skills`` length — fallback entries
 * always carry an empty skill list.
 */
export async function loadWorkModes(): Promise<WorkModesListResponse> {
  try {
    const response = await fetch(`${getBackendBaseURL()}/api/work-modes`);
    if (!response.ok) {
      return FALLBACK_WORK_MODES;
    }
    const json = (await response.json()) as WorkModesListResponse;
    if (!json || !Array.isArray(json.modes)) {
      return FALLBACK_WORK_MODES;
    }
    return json;
  } catch {
    return FALLBACK_WORK_MODES;
  }
}

/**
 * Add a skill to a work mode via ``PUT /api/work-modes/{modeId}/skills/{skillName}``.
 *
 * Throws when the backend rejects the request (e.g. 4xx) so the caller can
 * surface the error. The backend's locked-skill enforcement is the source
 * of truth — no client-side check is performed.
 */
export async function addSkillToWorkMode(
  modeId: string,
  skillName: string,
): Promise<void> {
  const response = await fetch(
    `${getBackendBaseURL()}/api/work-modes/${encodeURIComponent(modeId)}/skills/${encodeURIComponent(skillName)}`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
    },
  );
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(
      (detail as { detail?: string }).detail ??
        `Failed to add skill ${skillName} to mode ${modeId}`,
    );
  }
}

/**
 * Remove a skill from a work mode via ``DELETE /api/work-modes/{modeId}/skills/{skillName}``.
 *
 * Throws on backend refusal — notably HTTP 403 when the skill is locked.
 * The caller should catch and display a user-facing message.
 */
export async function removeSkillFromWorkMode(
  modeId: string,
  skillName: string,
): Promise<void> {
  const response = await fetch(
    `${getBackendBaseURL()}/api/work-modes/${encodeURIComponent(modeId)}/skills/${encodeURIComponent(skillName)}`,
    {
      method: "DELETE",
    },
  );
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(
      (detail as { detail?: string }).detail ??
        `Failed to remove skill ${skillName} from mode ${modeId}`,
    );
  }
}
