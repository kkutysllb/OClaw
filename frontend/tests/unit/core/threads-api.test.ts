import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, test } from "vitest";

import { threadTitlePath } from "@/core/threads/api";

const repoRoot = resolve(__dirname, "../../..");

function read(path: string): string {
  return readFileSync(resolve(repoRoot, path), "utf8");
}

describe("threads api", () => {
  test("encodes thread id for title lookup path", () => {
    expect(threadTitlePath("thread/with space")).toBe(
      "/api/threads/thread%2Fwith%20space",
    );
  });

  test("AgentThreadContext type includes work_mode_id for runtime forwarding", () => {
    // Source-level check so this test does not pull in the langgraph SDK
    // (which is heavy and sometimes mismatched in unit-test environments).
    const source = read("src/core/threads/types.ts");
    expect(source).toMatch(/work_mode_id\??\s*:\s*string/);
  });

  test("thread.submit context includes work_mode_id from settings", () => {
    // The submit() call in useThreadStream builds the run context from the
    // LocalSettings.context spread. We assert that the context object
    // literal passed to thread.submit contains a work_mode_id key so the
    // backend's _CONTEXT_CONFIGURABLE_KEYS whitelist can pick it up.
    const source = read("src/core/threads/hooks.ts");
    expect(source).toMatch(/work_mode_id/);
  });

  test("LocalSettings.context includes work_mode_id", () => {
    const source = read("src/core/settings/local.ts");
    expect(source).toMatch(/work_mode_id/);
  });

  test("settings local exports saveThreadWorkModeId / getThreadWorkModeId", () => {
    const source = read("src/core/settings/local.ts");
    expect(source).toMatch(/export function saveThreadWorkModeId/);
    expect(source).toMatch(/export function getThreadWorkModeId/);
  });

  test("AgentThreadContext type includes user_workspace_path for runtime forwarding", () => {
    const source = read("src/core/threads/types.ts");
    expect(source).toMatch(/user_workspace_path\??\s*:\s*string/);
  });

  test("thread.submit context includes user_workspace_path from settings", () => {
    // The submit() call in useThreadStream builds the run context from the
    // LocalSettings.context spread. We assert that the context object
    // literal passed to thread.submit contains a user_workspace_path key so
    // the backend's _CONTEXT_CONFIGURABLE_KEYS whitelist can pick it up.
    const source = read("src/core/threads/hooks.ts");
    expect(source).toMatch(/user_workspace_path/);
  });

  test("settings local exports saveThreadWorkspacePath / getThreadWorkspacePath", () => {
    const source = read("src/core/settings/local.ts");
    expect(source).toMatch(/export function saveThreadWorkspacePath/);
    expect(source).toMatch(/export function getThreadWorkspacePath/);
  });

  test("AgentThreadContext type includes permission_scope for runtime forwarding", () => {
    const source = read("src/core/threads/types.ts");
    expect(source).toMatch(/permission_scope\??\s*:\s*PermissionScope/);
  });

  test("thread.submit context includes permission_scope from settings", () => {
    // Mirror of the user_workspace_path assertion: confirms the context
    // object literal passed to thread.submit contains a permission_scope
    // key so the backend's _CONTEXT_CONFIGURABLE_KEYS whitelist can pick
    // it up.
    const source = read("src/core/threads/hooks.ts");
    expect(source).toMatch(/permission_scope/);
  });

  test("settings local exports saveThreadPermissionScope / getThreadPermissionScope", () => {
    const source = read("src/core/settings/local.ts");
    expect(source).toMatch(/export function saveThreadPermissionScope/);
    expect(source).toMatch(/export function getThreadPermissionScope/);
  });
});
