import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const mainSource = readFileSync(new URL("../src/main.ts", import.meta.url), "utf8");

test("renderer runs with node disabled, context isolation, and sandbox enabled", () => {
  assert.match(mainSource, /contextIsolation:\s*true/);
  assert.match(mainSource, /nodeIntegration:\s*false/);
  assert.match(mainSource, /sandbox:\s*true/);
});

test("tray uses a small dedicated icon instead of the app icon", () => {
  assert.match(mainSource, /function resolveTrayIcon\(\): Electron\.NativeImage \| undefined/);
  assert.match(mainSource, /build", "icons", "16x16\.png"/);
  assert.match(mainSource, /build", "icons", "32x32\.png"/);
  assert.match(mainSource, /setTemplateImage\(true\)/);
  assert.match(mainSource, /const icon = resolveTrayIcon\(\) \?\? nativeImage\.createEmpty\(\)/);
});

test("macOS window uses the native dark title bar without a custom inset frame", () => {
  assert.match(mainSource, /\bnativeTheme\b/);
  assert.match(mainSource, /nativeTheme\.themeSource = "dark"/);
  assert.doesNotMatch(mainSource, /titleBarStyle:\s*process\.platform === "darwin" \? "hiddenInset" : "default"/);
  assert.doesNotMatch(mainSource, /trafficLightPosition:/);
  assert.match(mainSource, /backgroundColor:\s*"#[0-9a-fA-F]{6}"/);
});
