export interface Skill {
  name: string;
  description: string;
  category: string;
  license: string;
  enabled: boolean;
  /** Work mode ids this skill is bound to (e.g. ["task", "coding"]). */
  work_modes: string[];
}

/**
 * Request body for `POST /api/skills/custom` (wizard-driven creation).
 *
 * Mirrors the backend `CustomSkillCreateRequest`. The backend normalises
 * the name to hyphen-case, injects `work_modes` frontmatter, validates,
 * runs a security scan, and writes atomically to `skills/custom/<name>/`.
 */
export interface CreateSkillRequest {
  /** Hyphen-case skill name. The backend normalises uppercase/underscores/spaces. */
  name: string;
  /** Short description (≤1024 chars) shown in the skill list. */
  description: string;
  /** Full SKILL.md body, including `---\nname:\ndescription:\n---` frontmatter. */
  content: string;
  /** Work mode ids to bind (e.g. ["task", "coding"]). Defaults to ["task"]. */
  work_modes: string[];
}

/** Skill content response from the backend (includes raw SKILL.md). */
export interface CustomSkillContent extends Skill {
  content: string;
}

/**
 * Wizard home mode selector. Each mode drives a different sub-flow:
 *  - `template` : existing 4-step flow (Basics → Template → Edit → Preview)
 *  - `upload`   : new 3-step flow (Upload → Preview → Install)
 *  - `scripts`  : new 4-step flow (Basics → Upload Scripts → Edit → Preview)
 */
export type CreateMode = "template" | "upload" | "scripts";

/**
 * Allowed support-file subdirectories under a custom skill.
 * Mirrors the backend `_ALLOWED_SUPPORT_SUBDIRS` in
 * `SkillStorage.ensure_safe_support_path`.
 */
export type SupportSubdir =
  | "references"
  | "templates"
  | "scripts"
  | "assets"
  | "models"
  | "adapters";

/** All valid support subdirs (for UI dropdowns / validation). */
export const SUPPORT_SUBDIRS: readonly SupportSubdir[] = [
  "references",
  "templates",
  "scripts",
  "assets",
  "models",
  "adapters",
] as const;

/**
 * A selectable skill template for the create wizard.
 *
 * `initialContent` is a factory so the template can incorporate the
 * user-entered name and description before being loaded into the editor.
 */
export interface SkillTemplate {
  /** Stable id. Built-ins: "blank" | "task" | "coding". Copy templates: `copy:<name>`. */
  id: string;
  label: string;
  /** English label (used when the active locale is en-US). */
  labelEn?: string;
  description: string;
  /** English description (used when the active locale is en-US). */
  descriptionEn?: string;
  /** Produce the initial SKILL.md body for this template. */
  initialContent: (name: string, description: string) => string;
}
