import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const releaseScriptUrl = new URL("../../release.sh", import.meta.url);
const releaseScriptPath = fileURLToPath(releaseScriptUrl);
const releaseScriptSource = existsSync(releaseScriptUrl)
  ? readFileSync(releaseScriptUrl, "utf8")
  : "";

test("root release lifecycle script exposes a remote release flow", () => {
  assert.equal(existsSync(releaseScriptUrl), true);

  const help = spawnSync("bash", [releaseScriptPath, "--help"], {
    encoding: "utf8",
    windowsHide: true,
  });

  assert.equal(help.status, 0, `stdout:\n${help.stdout}\nstderr:\n${help.stderr}`);
  assert.match(help.stdout, /Usage:/);
  assert.match(help.stdout, /--push/);
  assert.match(help.stdout, /--no-watch/);
  assert.match(help.stdout, /--resume/);
  assert.match(help.stdout, /GitHub Actions/);
});

test("release lifecycle script delegates desktop packaging to GitHub Actions", () => {
  assert.match(releaseScriptSource, /release-desktop\.yml/);
  assert.match(releaseScriptSource, /git push --atomic/);
  assert.match(releaseScriptSource, /gh run list/);
  assert.match(releaseScriptSource, /gh run watch/);
  assert.match(releaseScriptSource, /gh run view/);
  assert.match(releaseScriptSource, /gh release view/);
  assert.match(releaseScriptSource, /\.release-logs/);
  assert.match(releaseScriptSource, /verify_release_assets/);
  assert.doesNotMatch(releaseScriptSource, /pnpm run build:app/);
});
