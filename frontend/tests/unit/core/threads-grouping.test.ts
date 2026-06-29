// @vitest-environment happy-dom
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import {
  groupThreadsByWorkMode,
  resolveThreadWorkModeId,
} from "@/core/threads/grouping";
import {
  THREAD_AGENT_KEY_PREFIX,
  THREAD_WORK_MODE_KEY_PREFIX,
} from "@/core/settings/local";
import type { AgentThread } from "@/core/threads/types";

function makeThread(threadId: string): AgentThread {
  // Minimal shape — only thread_id is accessed by the grouping layer.
  return { thread_id: threadId } as unknown as AgentThread;
}

/**
 * happy-dom's localStorage is not always fully wired, so install an
 * in-memory stub backed by a Map. Re-installed in beforeEach for isolation.
 */
function installLocalStorageStub() {
  const store = new Map<string, string>();
  Object.defineProperty(window, "localStorage", {
    configurable: true,
    value: {
      getItem: vi.fn((key: string) => store.get(key) ?? null),
      setItem: vi.fn((key: string, value: string) => {
        store.set(key, value);
      }),
      removeItem: vi.fn((key: string) => {
        store.delete(key);
      }),
      clear: vi.fn(() => {
        store.clear();
      }),
    },
  });
}

function seedLocalStorage(entries: Record<string, string | null>) {
  for (const [key, value] of Object.entries(entries)) {
    if (value === null) {
      window.localStorage.removeItem(key);
    } else {
      window.localStorage.setItem(key, value);
    }
  }
}

describe("resolveThreadWorkModeId", () => {
  beforeEach(() => {
    installLocalStorageStub();
  });

  afterEach(() => {
    window.localStorage.clear();
  });

  test("prefers explicit work_mode_id when present", () => {
    const thread = makeThread("t-1");
    seedLocalStorage({
      [`${THREAD_WORK_MODE_KEY_PREFIX}t-1`]: "coding",
      [`${THREAD_AGENT_KEY_PREFIX}t-1`]: "lead_agent",
    });

    expect(resolveThreadWorkModeId(thread)).toBe("coding");
  });

  test("falls back to agent_name reverse-resolve when work_mode_id absent", () => {
    // coding_agent → coding mode (per BUILTIN_WORK_MODES mapping)
    const thread = makeThread("t-2");
    seedLocalStorage({
      [`${THREAD_AGENT_KEY_PREFIX}t-2`]: "coding_agent",
    });

    expect(resolveThreadWorkModeId(thread)).toBe("coding");
  });

  test("falls back to task when agent_name is the default sentinel", () => {
    // "__default__" sentinel = explicit default mode → task
    const thread = makeThread("t-3");
    seedLocalStorage({
      [`${THREAD_AGENT_KEY_PREFIX}t-3`]: "__default__",
    });

    expect(resolveThreadWorkModeId(thread)).toBe("task");
  });

  test("falls back to task when neither key is stored", () => {
    const thread = makeThread("t-4");

    expect(resolveThreadWorkModeId(thread)).toBe("task");
  });

  test("synthesizes transient mode id for unknown agent_name", () => {
    // agent_name matching no builtin mode → resolveWorkModeByAgentName
    // returns a transient mode whose id is the agent_name itself.
    const thread = makeThread("t-5");
    seedLocalStorage({
      [`${THREAD_AGENT_KEY_PREFIX}t-5`]: "custom-agent-xyz",
    });

    expect(resolveThreadWorkModeId(thread)).toBe("custom-agent-xyz");
  });
});

describe("groupThreadsByWorkMode", () => {
  beforeEach(() => {
    installLocalStorageStub();
  });

  afterEach(() => {
    window.localStorage.clear();
  });

  test("returns empty array for empty input", () => {
    expect(groupThreadsByWorkMode([])).toEqual([]);
  });

  test("groups threads by resolved mode id", () => {
    seedLocalStorage({
      [`${THREAD_WORK_MODE_KEY_PREFIX}a`]: "task",
      [`${THREAD_WORK_MODE_KEY_PREFIX}b`]: "coding",
      [`${THREAD_WORK_MODE_KEY_PREFIX}c`]: "task",
    });

    const groups = groupThreadsByWorkMode([
      makeThread("a"),
      makeThread("b"),
      makeThread("c"),
    ]);

    expect(groups).toHaveLength(2);
    // task (order 0) before coding (order 10)
    expect(groups[0]!.workModeId).toBe("task");
    expect(groups[0]!.threads.map((t) => t.thread_id)).toEqual(["a", "c"]);
    expect(groups[1]!.workModeId).toBe("coding");
    expect(groups[1]!.threads.map((t) => t.thread_id)).toEqual(["b"]);
  });

  test("respects WorkMode.order for sort stability", () => {
    // Shuffle the input order — task should still come first.
    seedLocalStorage({
      [`${THREAD_WORK_MODE_KEY_PREFIX}x`]: "coding",
      [`${THREAD_WORK_MODE_KEY_PREFIX}y`]: "task",
    });

    const groups = groupThreadsByWorkMode([
      makeThread("x"),
      makeThread("y"),
    ]);

    expect(groups[0]!.workModeId).toBe("task");
    expect(groups[1]!.workModeId).toBe("coding");
  });

  test("synthesizes transient mode for unknown mode id", () => {
    seedLocalStorage({
      [`${THREAD_WORK_MODE_KEY_PREFIX}z`]: "mystery-mode",
    });

    const groups = groupThreadsByWorkMode([makeThread("z")]);

    expect(groups).toHaveLength(1);
    expect(groups[0]!.workModeId).toBe("mystery-mode");
    expect(groups[0]!.workMode.builtin).toBe(false);
    expect(groups[0]!.workMode.order).toBe(999);

    // Transient modes sort last when mixed with builtin modes.
    seedLocalStorage({
      [`${THREAD_WORK_MODE_KEY_PREFIX}a`]: "task",
      [`${THREAD_WORK_MODE_KEY_PREFIX}b`]: "mystery-mode",
    });
    const mixed = groupThreadsByWorkMode([makeThread("a"), makeThread("b")]);
    expect(mixed[0]!.workModeId).toBe("task");
    expect(mixed[1]!.workModeId).toBe("mystery-mode");
  });

  test("threads without any stored key land in task group", () => {
    const groups = groupThreadsByWorkMode([makeThread("orphan")]);

    expect(groups).toHaveLength(1);
    expect(groups[0]!.workModeId).toBe("task");
  });
});
