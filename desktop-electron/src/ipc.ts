/**
 * IPC handler registration.
 *
 * Wires the renderer-side `window.oclawDesktop.*` calls (forwarded by the
 * preload) to the `BackendManager` and native Electron APIs. The channel
 * names and payload shapes mirror the previous Tauri commands so the
 * frontend's desktop abstraction layer stays unchanged.
 */

import { app, BrowserWindow, dialog, ipcMain, shell } from "electron";
import pty from "node-pty";
import { randomUUID } from "node:crypto";
import { accessSync, chmodSync, constants, statSync } from "node:fs";
import { createRequire } from "node:module";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { basename, dirname, extname, join } from "node:path";

import { BackendManager, resolveGatewayPort, type BackendStatus } from "./backend.js";
import {
  readSkillModelsEnv,
  writeSkillModelsEnv,
  type SkillModelsConfig,
} from "./skill-models-env.js";
import { isAllowedExternalUrl } from "./url-policy.js";

// ── Shared payload types (mirrors frontend `core/desktop/types.ts`) ───────

interface FileDialogOptions {
  multiple?: boolean;
  filters?: { name: string; extensions: string[] }[];
  title?: string;
}

interface PickedFile {
  name: string;
  data: Uint8Array;
  type?: string;
}

interface EmbeddedTerminalSession {
  sessionId: string;
  cwd: string;
  shell: string;
  projectName: string;
  promptLabel: string;
}

interface TerminalProcess {
  process: pty.IPty;
  owner: Electron.WebContents;
  cwd: string;
  shell: string;
}

/** Minimal MIME map for common upload extensions. */
const MIME_BY_EXT: Record<string, string> = {
  ".md": "text/markdown",
  ".txt": "text/plain",
  ".json": "application/json",
  ".csv": "text/csv",
  ".pdf": "application/pdf",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".svg": "image/svg+xml",
  ".py": "text/x-python",
  ".js": "text/javascript",
  ".ts": "text/typescript",
  ".html": "text/html",
  ".xml": "application/xml",
  ".zip": "application/zip",
};

function guessMime(ext: string): string | undefined {
  return MIME_BY_EXT[ext.toLowerCase()];
}

const terminalProcesses = new Map<string, TerminalProcess>();

const DEFAULT_TERMINAL_PATH =
  "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin";
const POSIX_SHELL_CANDIDATES = [
  process.env.SHELL,
  "/bin/zsh",
  "/bin/bash",
  "/bin/sh",
].filter(Boolean) as string[];

function resolveEmbeddedShell(): string {
  if (process.platform === "win32") {
    return process.env.ComSpec || "powershell.exe";
  }
  for (const candidate of POSIX_SHELL_CANDIDATES) {
    try {
      accessSync(candidate, constants.X_OK);
      return candidate;
    } catch {
      // Try the next known-good shell path.
    }
  }
  return "/bin/sh";
}

/**
 * Make sure node-pty's bundled `spawn-helper` binary is executable before
 * we hand off to `pty.spawn`. On macOS / Linux, `node-pty` exec's that
 * helper via `posix_spawnp`, and a missing `+x` bit surfaces as the
 * unhelpful `posix_spawnp failed.` error.
 *
 * pnpm's content-addressable store does not always preserve the mode that
 * `node-pty`'s `install.js` set on its own copy, so we self-heal at
 * runtime. If the helper really doesn't exist (e.g. unsupported platform),
 * we silently no-op — `pty.spawn` will produce its own (still cryptic)
 * error, but we won't make things worse.
 *
 * Returns the resolved helper path when found, `null` otherwise.
 */
function ensureNodePtySpawnHelperExecutable(): string | null {
  if (process.platform === "win32") return null;

  // Resolve the bundled package root via the same module the renderer would
  // load — works whether the install is hoisted, pnpm-linked, or in a
  // workspace.
  let ptyPackageRoot: string;
  try {
    const req = createRequire(import.meta.url);
    const entry = req.resolve("node-pty");
    // .../node-pty/lib/index.js → .../node-pty
    ptyPackageRoot = dirname(dirname(entry));
  } catch {
    return null;
  }

  const helper = join(
    ptyPackageRoot,
    "prebuilds",
    `${process.platform}-${process.arch}`,
    "spawn-helper",
  );

  try {
    accessSync(helper, constants.X_OK);
    return helper;
  } catch {
    // Either the file is missing or lacks +x. Try to repair.
  }

  try {
    chmodSync(helper, 0o755);
    accessSync(helper, constants.X_OK);
    console.warn(
      `[oclaw-desktop] Repaired node-pty spawn-helper permissions at ${helper}`,
    );
    return helper;
  } catch (error) {
    // Don't throw — let pty.spawn produce its own error, but log enough
    // context that the next person debugging doesn't have to rediscover
    // this. The error message intentionally names `posix_spawnp failed.`
    // so it's grep-friendly.
    const message = error instanceof Error ? error.message : String(error);
    console.warn(
      `[oclaw-desktop] Could not chmod spawn-helper at ${helper}: ${message}. ` +
        `If "posix_spawnp failed." persists, run: chmod +x "${helper}"`,
    );
    return null;
  }
}

function resolveTerminalCwd(folderPath: string): string {
  try {
    const stat = statSync(folderPath);
    if (stat.isDirectory()) return folderPath;
  } catch {
    // Fall back below.
  }
  return process.env.HOME || process.cwd();
}

function buildTerminalEnv(): Record<string, string> {
  const env: Record<string, string> = {};
  for (const [key, value] of Object.entries(process.env)) {
    if (typeof value === "string") env[key] = value;
  }
  env.PATH = env.PATH || DEFAULT_TERMINAL_PATH;
  env.TERM = env.TERM || "xterm-256color";
  env.COLORTERM = env.COLORTERM || "truecolor";
  return env;
}

function buildTerminalPromptLabel(folderPath: string): string {
  const projectName = basename(folderPath) || folderPath;
  return projectName;
}

function stopTerminalProcess(sessionId: string): void {
  const terminal = terminalProcesses.get(sessionId);
  if (!terminal) return;
  terminalProcesses.delete(sessionId);
  terminal.process.kill();
}

function stopTerminalsForOwner(owner: Electron.WebContents): void {
  for (const [sessionId, terminal] of terminalProcesses.entries()) {
    if (terminal.owner === owner || owner.isDestroyed()) {
      stopTerminalProcess(sessionId);
    }
  }
}

function startEmbeddedTerminal(
  owner: Electron.WebContents,
  folderPath: string,
): EmbeddedTerminalSession {
  // Self-heal node-pty's spawn-helper permission BEFORE we try to spawn.
  // Cheap when already correct; avoids the cryptic "posix_spawnp failed."
  // when pnpm stripped the +x bit during install.
  ensureNodePtySpawnHelperExecutable();

  const shellPath = resolveEmbeddedShell();
  const cwd = resolveTerminalCwd(folderPath);
  const sessionId = randomUUID();
  let terminal: pty.IPty;
  try {
    terminal = pty.spawn(shellPath, [], {
      cols: 100,
      cwd,
      env: buildTerminalEnv(),
      name: "xterm-256color",
      rows: 28,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(
      `Failed to start project terminal: ${message}. shell=${shellPath} cwd=${cwd}`,
    );
  }

  terminalProcesses.set(sessionId, {
    process: terminal,
    owner,
    cwd,
    shell: shellPath,
  });

  const sendData = (data: string): void => {
    if (owner.isDestroyed()) {
      stopTerminalProcess(sessionId);
      return;
    }
    owner.send("terminal:data", {
      sessionId,
      data,
    });
  };

  terminal.onData(sendData);
  terminal.onExit((event) => {
    terminalProcesses.delete(sessionId);
    if (!owner.isDestroyed()) {
      owner.send("terminal:exit", {
        sessionId,
        code: event.exitCode,
        signal: event.signal,
      });
    }
  });

  owner.once("destroyed", () => stopTerminalsForOwner(owner));

  return {
    sessionId,
    cwd,
    shell: shellPath,
    projectName: basename(cwd) || cwd,
    promptLabel: buildTerminalPromptLabel(cwd),
  };
}

/**
 * Register all backend-lifecycle and system-integration IPC handlers.
 *
 * Returns the shared `BackendManager` so the main process can drive it
 * (e.g. auto-launch on `app.whenReady`, stop on `before-quit`).
 */
export function registerIpc(): BackendManager {
  const manager = new BackendManager();

  // ── Backend lifecycle ──────────────────────────────────────────────
  ipcMain.handle("backend:get-status", (): BackendStatus =>
    manager.getStatus(),
  );
  ipcMain.handle("backend:start", async (): Promise<BackendStatus> =>
    manager.launch(),
  );
  ipcMain.handle("backend:stop", async (): Promise<BackendStatus> =>
    manager.stop(),
  );
  ipcMain.handle("backend:restart", async (): Promise<BackendStatus> =>
    manager.restart(),
  );
  ipcMain.handle("backend:get-logs", (): string[] => manager.getLogs());
  ipcMain.handle("backend:get-gateway-config", () => ({
    port: resolveGatewayPort(),
  }));

  // ── Native file dialog ──────────────────────────────────────────────
  ipcMain.handle(
    "dialog:pick-files",
    async (_evt, options: FileDialogOptions = {}): Promise<PickedFile[]> => {
      const win = BrowserWindow.fromWebContents(_evt.sender);
      const dialogOpts: Electron.OpenDialogOptions = {
        title: options.title ?? "Select file",
        filters: options.filters,
        properties: [options.multiple ? "multiSelections" : "openFile"],
      };
      const result = win
        ? await dialog.showOpenDialog(win, dialogOpts)
        : await dialog.showOpenDialog(dialogOpts);

      if (result.canceled || result.filePaths.length === 0) return [];

      const files = await Promise.all(
        result.filePaths.map(async (filePath) => {
          const data = await readFile(filePath);
          const ext = extname(filePath);
          return {
            name: basename(filePath),
            data: new Uint8Array(data.buffer, data.byteOffset, data.byteLength),
            type: guessMime(ext),
          } satisfies PickedFile;
        }),
      );
      return files;
    },
  );

  // ── External links ──────────────────────────────────────────────────
  ipcMain.handle("shell:open-external", async (_evt, url: string) => {
    if (!isAllowedExternalUrl(url)) {
      throw new Error("Blocked external URL.");
    }
    await shell.openExternal(url);
  });

  // ── Open local folder in system file manager (Finder / Explorer) ───
  ipcMain.handle("shell:open-folder", async (_evt, folderPath: string) => {
    await shell.openPath(folderPath);
  });

  // ── Embedded project terminal ──────────────────────────────────────
  ipcMain.handle(
    "terminal:start",
    async (_evt, folderPath: string): Promise<EmbeddedTerminalSession> => {
      return startEmbeddedTerminal(_evt.sender, folderPath);
    },
  );
  ipcMain.handle(
    "terminal:write",
    async (_evt, sessionId: string, data: string): Promise<void> => {
      const terminal = terminalProcesses.get(sessionId);
      if (!terminal || terminal.owner !== _evt.sender) {
        throw new Error("Terminal session not found.");
      }
      terminal.process.write(data);
    },
  );
  ipcMain.handle(
    "terminal:resize",
    async (
      _evt,
      sessionId: string,
      cols: number,
      rows: number,
    ): Promise<void> => {
      const terminal = terminalProcesses.get(sessionId);
      if (!terminal || terminal.owner !== _evt.sender) {
        throw new Error("Terminal session not found.");
      }
      terminal.process.resize(cols, rows);
    },
  );
  ipcMain.handle("terminal:stop", async (_evt, sessionId: string): Promise<void> => {
    const terminal = terminalProcesses.get(sessionId);
    if (!terminal || terminal.owner !== _evt.sender) return;
    stopTerminalProcess(sessionId);
  });

  // ── Native directory picker (for Code Mode project selection) ───────
  ipcMain.handle(
    "dialog:pick-directory",
    async (_evt, options: { title?: string } = {}): Promise<string | null> => {
      const win = BrowserWindow.fromWebContents(_evt.sender);
      const dialogOpts: Electron.OpenDialogOptions = {
        title: options.title ?? "选择项目目录",
        properties: ["openDirectory"],
      };
      const result = win
        ? await dialog.showOpenDialog(win, dialogOpts)
        : await dialog.showOpenDialog(dialogOpts);

      if (result.canceled || result.filePaths.length === 0) return null;
      return result.filePaths[0];
    },
  );

  // ── Skill model credentials (.env read/write) ───────────────────────
  // Returns the redacted snapshot of <KKOCLAW_HOME>/.env. Secrets are masked
  // so the renderer never receives raw API keys.
  ipcMain.handle(
    "skill-models:get",
    (): SkillModelsConfig => readSkillModelsEnv(),
  );

  // Merges updates into the .env. Secret fields whose incoming value is a
  // redaction placeholder (`***`-prefixed) are preserved verbatim so the
  // renderer can round-trip the redacted snapshot without losing keys.
  ipcMain.handle(
    "skill-models:set",
    (_evt, updates: Record<string, string>): SkillModelsConfig =>
      writeSkillModelsEnv(updates),
  );

  return manager;
}

/** Forward dropped-file paths from the window to the renderer. */
export async function forwardFileDrop(
  win: BrowserWindow,
  filePaths: string[],
): Promise<void> {
  const files: PickedFile[] = [];
  for (const filePath of filePaths) {
    try {
      const buf = await readFile(filePath);
      const ext = extname(filePath);
      files.push({
        name: basename(filePath),
        data: new Uint8Array(buf.buffer, buf.byteOffset, buf.byteLength),
        type: guessMime(ext),
      });
    } catch {
      /* skip unreadable files */
    }
  }
  if (files.length > 0) {
    win.webContents.send("desktop:file-drop", files);
  }
}
