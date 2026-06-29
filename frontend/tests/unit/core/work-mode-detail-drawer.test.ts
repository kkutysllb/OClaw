import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, test } from "vitest";

const repoRoot = resolve(__dirname, "../../..");

function read(path: string): string {
  return readFileSync(resolve(repoRoot, path), "utf8");
}

describe("work mode detail drawer", () => {
  const DRAWER_PATH = "src/components/workspace/work-mode-detail-drawer.tsx";
  const SELECTOR_PATH = "src/components/workspace/work-mode-selector.tsx";
  const PAGE_PATH = "src/app/workspace/chats/[thread_id]/page.tsx";

  test("drawer component exists and renders the four runtime-graph sections", () => {
    const source = read(DRAWER_PATH);

    // Lead agent section
    expect(source).toMatch(/lead_agent_name|Lead 智能体/);
    // Bound skills section
    expect(source).toMatch(/skill_count|绑定技能/);
    // Focus areas section
    expect(source).toMatch(/focus_areas|关注领域/);
    // Orchestration hint section
    expect(source).toMatch(/orchestration_hint|任务编排指导/);
  });

  test("drawer uses Dialog component for the overlay", () => {
    const source = read(DRAWER_PATH);
    expect(source).toMatch(/from "@\/components\/ui\/dialog"/);
    expect(source).toMatch(/<Dialog/);
    expect(source).toMatch(/DialogContent/);
  });

  test("drawer reads work-mode data from useWorkModes hook", () => {
    const source = read(DRAWER_PATH);
    expect(source).toMatch(/useWorkModes/);
    expect(source).toMatch(/resolveWorkModeById/);
  });

  test("selector exposes onShowDetail callback prop", () => {
    const source = read(SELECTOR_PATH);
    expect(source).toMatch(/onShowDetail/);
    // The info icon must trigger the callback
    expect(source).toMatch(/InfoIcon/);
  });

  test("selector renders info button next to each mode button", () => {
    const source = read(SELECTOR_PATH);
    // The info button must call onShowDetail with the mode id
    expect(source).toMatch(/onShowDetail\(mode\.id\)/);
  });

  test("page.tsx wires the drawer and passes setDetailModeId to selector", () => {
    const source = read(PAGE_PATH);

    // State for the drawer's open/close
    expect(source).toMatch(/detailModeId/);
    // Drawer component rendered
    expect(source).toMatch(/WorkModeDetailDrawer/);
    // Selector receives onShowDetail
    expect(source).toMatch(/onShowDetail=\{setDetailModeId\}/);
  });

  test("WorkModeDetail type carries the extended fields", () => {
    const source = read("src/core/work-modes/types.ts");
    expect(source).toMatch(/lead_agent_name\?/);
    expect(source).toMatch(/orchestration_hint\?/);
    expect(source).toMatch(/focus_areas\?/);
    expect(source).toMatch(/skill_count\?/);
  });
});
