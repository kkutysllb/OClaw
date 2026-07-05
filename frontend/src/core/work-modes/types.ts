/**
 * Work Mode type definitions.
 *
 * A "work mode" is a high-level UI concept that maps to a Lead Agent
 * configuration preset. Selecting a work mode sets the `agent_name` in
 * the thread context, which tells the backend `make_lead_agent` to load
 * the corresponding AgentConfig (model / tool_groups / skills overrides).
 *
 * There are two categories:
 *  - **Builtin** modes are shipped with the platform and cannot be deleted.
 *  - **Custom** modes are user-defined (reserved interface for future use).
 */

/** Icon identifier — maps to a Lucide icon name rendered by the selector. */
export type WorkModeIcon =
  | "Briefcase"
  | "Code2"
  | "PenTool"
  | "ResearchIcon"
  | "GraduationCap"
  | "Sparkles"
  | "Bot"
  | "Wrench"
  | "Palette";

export interface WorkMode {
  /** Unique identifier (e.g. "office", "coding", "code-reviewer"). */
  id: string;
  /** Display name — either a literal string or an i18n key resolved by the component. */
  name: string;
  /** Short description shown in tooltips or dropdowns. */
  description?: string;
  /** Lucide icon identifier. */
  icon: WorkModeIcon;
  /**
   * The `agent_name` to inject into the thread context when this mode is selected.
   * `undefined` means the default Lead Agent (no agent_name override).
   */
  agent_name?: string;
  /** Whether this is a builtin mode that cannot be deleted or renamed. */
  builtin: boolean;
  /** Whether the mode is currently selectable in the UI. */
  enabled: boolean;
  /** Sort order — lower values appear first. */
  order: number;
}

/**
 * A user-defined work mode preset.
 *
 * This interface is reserved for the future "create custom work mode" feature.
 * It extends WorkMode with user-specific metadata and is stored per-user.
 */
export interface CustomWorkMode extends WorkMode {
  builtin: false;
  /** ISO timestamp of creation. */
  created_at: string;
  /** ISO timestamp of last modification. */
  updated_at: string;
}

// ---------------------------------------------------------------------------
// API response types (mirror backend ``app/gateway/routers/work_modes.py``)
// ---------------------------------------------------------------------------

/** A single skill entry within a work mode, as returned by /api/work-modes. */
export interface WorkModeSkill {
  /** Skill identifier (matches ``Skill.name``). */
  skill_id: string;
  /** Whether this is a locked core skill that cannot be removed. */
  locked: boolean;
}

/**
 * Detailed work-mode payload returned by ``GET /api/work-modes``.
 *
 * Unlike the local ``WorkMode`` UI type (which is purely presentational),
 * this interface carries the effective skill list resolved by the backend
 * — including which skills are locked. The skills-page / settings UI use
 * this to render per-mode skill management controls.
 */
export interface WorkModeDetail {
  id: string;
  name: string;
  description?: string;
  builtin: boolean;
  editable: boolean;
  /** Whether this is the config's default mode (``work_modes.default_mode_id``). */
  is_default: boolean;
  /** Effective skill set for this mode, locked-core flags included. */
  skills: WorkModeSkill[];
  /** Display name of the bound lead agent (e.g. "KKOCLAW 1.0", "Coding Agent"). */
  lead_agent_name?: string;
  /** Mode-specific task orchestration guidance, shown in the detail drawer. */
  orchestration_hint?: string;
  /** Focus area tags (e.g. ["research", "documents"]). */
  focus_areas?: string[];
  /** Total number of effective skills in this mode. */
  skill_count?: number;
  /**
   * Lucide icon name (e.g. "Bot", "Briefcase", "Search") or emoji used by
   * the frontend sidebar entry. Built-in modes resolve from a hard-coded
   * map on the backend (task→"CheckSquare", coding→"Code2"); custom modes
   * carry the value chosen at creation time. Always present — defaults to
   * "Bot" when the backend omits it.
   */
  icon?: string;
}

/** Top-level response shape of ``GET /api/work-modes``. */
export interface WorkModesListResponse {
  default_mode_id: string;
  modes: WorkModeDetail[];
}

// ---------------------------------------------------------------------------
// Request types for custom work-mode CRUD (mirror backend request models)
// ---------------------------------------------------------------------------

/** Request body for ``POST /api/work-modes`` (create a custom work mode). */
export interface CustomWorkModeCreateRequest {
  /** Slug-style unique id (``^[a-z0-9][a-z0-9_-]*$``). */
  id: string;
  /** Display name shown in the selector and settings UI. */
  name: string;
  /** Short user-facing description (≤ 200 chars). */
  description?: string;
  /** Model-facing orchestration hint injected into the system prompt (≤ 4000 chars). */
  orchestration_hint?: string;
  /** Focus-area tags for the mode. */
  focus_areas?: string[];
  /** Lucide icon name or emoji for the sidebar entry. Defaults to "Bot". */
  icon?: string;
}

/** Request body for ``PUT /api/work-modes/{modeId}`` (update a custom work mode). */
export interface CustomWorkModeUpdateRequest {
  name?: string;
  description?: string;
  orchestration_hint?: string;
  focus_areas?: string[];
  enabled?: boolean;
  icon?: string;
}
