import { describe, expect, test } from "vitest";

import { shouldShowBackendSplash } from "@/components/desktop/backend-splash";

describe("desktop backend splash visibility", () => {
  test("only shows while the desktop backend is explicitly starting", () => {
    expect(shouldShowBackendSplash(null, true)).toBe(false);
    expect(shouldShowBackendSplash({ status: "stopped", port: 29987 }, true)).toBe(false);
    expect(shouldShowBackendSplash({ status: "running", port: 29987 }, true)).toBe(false);
    expect(shouldShowBackendSplash({ status: "error", port: 29987 }, true)).toBe(false);
    expect(shouldShowBackendSplash({ status: "starting", port: 29987 }, true)).toBe(true);
    expect(shouldShowBackendSplash({ status: "starting", port: 29987 }, false)).toBe(false);
  });
});
