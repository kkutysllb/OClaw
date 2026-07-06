// @vitest-environment happy-dom
import { beforeEach, describe, expect, test, vi } from "vitest";

function installLocalStorageMock() {
  const store = new Map<string, string>();
  const mock = {
    getItem: vi.fn((key: string) => store.get(key) ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store.set(key, String(value));
    }),
    removeItem: vi.fn((key: string) => {
      store.delete(key);
    }),
    clear: vi.fn(() => {
      store.clear();
    }),
    key: vi.fn((index: number) => Array.from(store.keys())[index] ?? null),
    get length() {
      return store.size;
    },
  };

  Object.defineProperty(window, "localStorage", {
    configurable: true,
    value: mock,
  });
}

async function loadStore() {
  vi.resetModules();
  return await import("@/core/settings/store");
}

describe("thread settings overrides", () => {
  beforeEach(() => {
    installLocalStorageMock();
    window.localStorage.clear();
  });

  test("updates permission_scope override immediately for the active thread", async () => {
    const store = await loadStore();

    store.updateThreadSettings("thread-a", "context", {
      permission_scope: "unrestricted",
    });

    expect(store.hasThreadPermissionScopeOverride("thread-a")).toBe(true);
    expect(store.getThreadPermissionScopeSnapshot("thread-a")).toBe(
      "unrestricted",
    );
  });

  test("updates workspace path override immediately for the active thread", async () => {
    const store = await loadStore();

    store.updateThreadSettings("thread-a", "context", {
      user_workspace_path: "/tmp/workspace-a",
    });

    expect(store.hasThreadWorkspacePathOverride("thread-a")).toBe(true);
    expect(store.getThreadWorkspacePathSnapshot("thread-a")).toBe(
      "/tmp/workspace-a",
    );
  });

  test("updates work mode override immediately for the active thread", async () => {
    const store = await loadStore();

    store.updateThreadSettings("thread-a", "context", {
      work_mode_id: "stock-quant",
    });

    expect(store.hasThreadWorkModeOverride("thread-a")).toBe(true);
    expect(store.getThreadWorkModeSnapshot("thread-a")).toBe("stock-quant");
  });
});
