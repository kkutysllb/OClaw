import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, test } from "vitest";

const repoRoot = resolve(__dirname, "../../..");

function read(path: string): string {
  return readFileSync(resolve(repoRoot, path), "utf8");
}

describe("artifact skill install flow", () => {
  test("skill install hook invalidates skills and work modes", () => {
    const source = read("src/core/skills/hooks.ts");

    expect(source).toMatch(/useInstallSkill/);
    expect(source).toMatch(/invalidateQueries\(\{\s*queryKey:\s*\["skills"\]/);
    expect(source).toMatch(
      /invalidateQueries\(\{\s*queryKey:\s*\["work-modes"\]/,
    );
  });

  test("artifact install requests include the active work mode", () => {
    const listSource = read(
      "src/components/workspace/artifacts/artifact-file-list.tsx",
    );
    const detailSource = read(
      "src/components/workspace/artifacts/artifact-file-detail.tsx",
    );

    expect(listSource).toMatch(/useInstallSkill/);
    expect(listSource).toMatch(/work_modes:\s*workModeId\s*\?/);
    expect(detailSource).toMatch(/useInstallSkill/);
    expect(detailSource).toMatch(/work_modes:\s*workModeId\s*\?/);
  });

  test("chat and coding artifact containers pass their mode to installers", () => {
    const chatBoxSource = read("src/components/workspace/chats/chat-box.tsx");
    const messageListSource = read(
      "src/components/workspace/messages/message-list.tsx",
    );
    const chatPageSource = read(
      "src/app/workspace/chats/[thread_id]/page.tsx",
    );
    const codingPanelSource = read(
      "src/components/workspace/coding/coding-results-panel.tsx",
    );

    expect(chatPageSource).toMatch(/workModeId=\{settings\.context\.work_mode_id/);
    expect(messageListSource).toMatch(/workModeId\?:\s*string/);
    expect(chatBoxSource).toMatch(/thread\.values\.context\?\.work_mode_id/);
    expect(chatBoxSource).toMatch(/workModeId=\{effectiveWorkModeId/);
    expect(codingPanelSource).toMatch(/workModeId="coding"/);
  });
});
