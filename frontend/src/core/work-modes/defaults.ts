import type { WorkMode } from "./types";

/**
 * Builtin work modes shipped with the platform.
 *
 * These mirror the backend's shipped ``work_modes.modes`` config
 * (task / coding). The frontend keeps its own copy so the UI can render
 * instantly before the API call resolves, and so it has a fallback when
 * the backend is unreachable (see ``FALLBACK_WORK_MODES`` in ``./api``).
 *
 * Note: the previous "office" id (used in early UI iterations before the
 * backend work-mode contract landed) has been renamed to "task" to match
 * the canonical ``ExtensionsConfig.work_modes.default_mode_id``.
 */
export const BUILTIN_WORK_MODES: WorkMode[] = [
  {
    id: "task",
    name: "workModes.task.name",
    description: "workModes.task.description",
    icon: "Briefcase",
    agent_name: undefined, // default Lead Agent — no agent_name override
    builtin: true,
    enabled: true,
    order: 0,
  },
  {
    id: "coding",
    name: "workModes.coding.name",
    description: "workModes.coding.description",
    icon: "Code2",
    agent_name: "coding_agent",
    builtin: true,
    enabled: true,
    order: 10,
  },
];

/** The default work mode id used when no selection has been made. */
export const DEFAULT_WORK_MODE_ID = "task";

/**
 * Return all available work modes: builtins + custom (reserved).
 *
 * Custom modes are fetched from a per-user store (TBD). For now, only
 * builtins are returned. The `customModes` parameter is the extension
 * point for the future "user-defined work mode" feature.
 */
export function getAvailableWorkModes(
  customModes: WorkMode[] = [],
): WorkMode[] {
  return [...BUILTIN_WORK_MODES, ...customModes]
    .filter((m) => m.enabled)
    .sort((a, b) => a.order - b.order);
}

/**
 * Resolve a work mode by id. Falls back to the default mode.
 */
export function resolveWorkMode(
  id: string | undefined,
  customModes: WorkMode[] = [],
): WorkMode {
  const modes = getAvailableWorkModes(customModes);
  return (
    modes.find((m) => m.id === id) ??
    modes.find((m) => m.id === DEFAULT_WORK_MODE_ID) ??
    modes[0]!
  );
}

/**
 * Resolve the work mode from an ``agent_name`` value (e.g. from thread
 * context). Returns the matching mode or the default "task" mode.
 *
 * This is kept for backward compatibility with threads created before
 * ``work_mode_id`` was threaded through the runtime context — those threads
 * only carry ``agent_name`` in their metadata.
 */
export function resolveWorkModeByAgentName(
  agentName: string | undefined,
  customModes: WorkMode[] = [],
): WorkMode {
  if (!agentName) {
    return resolveWorkMode(DEFAULT_WORK_MODE_ID, customModes);
  }
  const modes = getAvailableWorkModes(customModes);
  return (
    modes.find((m) => m.agent_name === agentName) ??
    // If agent_name doesn't match any known mode, create a transient mode
    // so the selector can still highlight it.
    {
      id: agentName,
      name: agentName,
      icon: "Bot",
      agent_name: agentName,
      builtin: false,
      enabled: true,
      order: 999,
    }
  );
}
