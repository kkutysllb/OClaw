export interface Skill {
  name: string;
  description: string;
  category: string;
  license: string;
  enabled: boolean;
  /** Work mode ids this skill is bound to (e.g. ["task", "coding"]). */
  work_modes: string[];
}
