#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { existsSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const nextDir = join(ROOT, ".next");

if (existsSync(nextDir)) {
  console.log("[typecheck] Clearing stale .next cache...");
  rmSync(nextDir, { recursive: true, force: true });
}

const pnpm = process.platform === "win32" ? "pnpm.cmd" : "pnpm";
const result = spawnSync(pnpm, ["exec", "tsc", "--noEmit"], {
  cwd: ROOT,
  stdio: "inherit",
  windowsHide: true,
});

if (result.error) {
  console.error(`[typecheck] Failed to start TypeScript: ${result.error.message}`);
  process.exit(1);
}

process.exit(result.status ?? 1);
