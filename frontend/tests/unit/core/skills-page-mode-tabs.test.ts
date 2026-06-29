import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, test } from "vitest";

const repoRoot = resolve(__dirname, "../../..");

function read(path: string): string {
  return readFileSync(resolve(repoRoot, path), "utf8");
}

describe("skills page mode-scoped tabs", () => {
  const PAGE_PATH = "src/components/workspace/skills/skills-page.tsx";

  test("removes the legacy all/public/custom category filter pills", () => {
    const source = read(PAGE_PATH);

    // The old "全部" (all) pill must be gone — it overlapped with the
    // builtin tab and made the UI confusing.
    expect(source).not.toMatch(/filter === "all"/);
    expect(source).not.toMatch(/setFilter\("all"\)/);

    // The old "公共" / "自定义" pills (category === "public"/"custom")
    // must be gone — replaced by builtin + work-mode tabs.
    expect(source).not.toMatch(/CATEGORY_COLORS[\s\S]*public:/);
    expect(source).not.toMatch(/CATEGORY_COLORS[\s\S]*custom:/);
  });

  test("renders builtin + dynamic work-mode tabs", () => {
    const source = read(PAGE_PATH);

    // The "builtin" tab is always present.
    expect(source).toMatch(/["']builtin["']/);
    // Work mode tabs are rendered dynamically from the API via
    // useWorkModes — each mode produces its own ModeTabPill.
    expect(source).toMatch(/useWorkModes\(\)/);
    expect(source).toMatch(/modeTabs\.map/);
    expect(source).toMatch(/ModeTabPill/);
  });

  test("create skill carries the active work mode", () => {
    const source = read(PAGE_PATH);

    // The "Create Skill" button must pass the active work mode tab
    // as a query param so the new chat pre-selects it.
    expect(source).toMatch(/workMode=/);
  });

  test("builtin tab shows only locked core skills", () => {
    const source = read(PAGE_PATH);

    // The "内置" tab must filter to show ONLY core skills (the 3 core
    // skills that cannot be turned off or deleted), not all skills.
    // This is the user-facing contract: "内置" = "cannot remove".
    expect(source).toMatch(/activeTab === ["']builtin["']/);
    // Core skills are identified by work_modes including "core".
    expect(source).toMatch(/work_modes\.includes\(["']core["']\)/);
  });

  test("work-mode tabs filter by work_modes field", () => {
    const source = read(PAGE_PATH);

    // Work-mode tabs (task / coding) filter skills by the work_modes
    // frontmatter field, showing only skills bound to that mode.
    expect(source).toMatch(/work_modes\.includes\(activeTab\)/);
  });

  test("shows a locked badge for locked core skills", () => {
    const source = read(PAGE_PATH);

    // Locked skills (bootstrap, find-skills, skill-creator) must show
    // a visual "locked" indicator so users understand why they cannot
    // be removed from a mode.
    expect(source).toMatch(/locked/);
  });

  test("disables the enable/disable switch for locked skills", () => {
    const source = read(PAGE_PATH);

    // The Switch component must be disabled when the skill is locked,
    // so users cannot turn off the core bootstrap loop.
    expect(source).toMatch(/disabled=\{[^}]*locked[^}]*\}/);
  });
});

describe("skill settings page mode-scoped tabs", () => {
  const PAGE_PATH = "src/components/workspace/settings/skill-settings-page.tsx";

  test("removes the legacy public/custom tab triggers", () => {
    const source = read(PAGE_PATH);

    // The old <TabsTrigger value="public"> and value="custom" must be
    // gone — replaced by builtin + work-mode tabs.
    expect(source).not.toMatch(/value="public"/);
    expect(source).not.toMatch(/value="custom"/);
  });

  test("renders builtin + dynamic work-mode tab triggers", () => {
    const source = read(PAGE_PATH);

    // The "builtin" tab is always rendered.
    expect(source).toMatch(/value="builtin"/);
    // Work mode tabs are rendered dynamically from the API via useWorkModes.
    expect(source).toMatch(/useWorkModes/);
    expect(source).toMatch(/mode\.id/);
  });

  test("disables destructive controls for locked skills", () => {
    const source = read(PAGE_PATH);

    // The settings page must disable the switch for locked skills,
    // mirroring the skills page behavior.
    expect(source).toMatch(/locked/);
  });
});
