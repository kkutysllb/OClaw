// @vitest-environment happy-dom
import { afterEach, describe, expect, test, vi } from "vitest";

vi.mock("@/env", () => ({
  env: {
    NEXT_PUBLIC_BACKEND_BASE_URL: "http://127.0.0.1:29987",
    NEXT_PUBLIC_LANGGRAPH_BASE_URL: "http://127.0.0.1:29987/api",
  },
}));

vi.mock("@/core/auth/session", () => ({
  getDesktopSessionToken: vi.fn(() => null),
}));

import { installSkill } from "@/core/skills/api";
import {
  addSkillToWorkMode,
  loadWorkModes,
  removeSkillFromWorkMode,
} from "@/core/work-modes/api";

function fetchUrl(input: Parameters<typeof fetch>[0]): string {
  if (typeof input === "string") {
    return input;
  }
  if (input instanceof URL) {
    return input.toString();
  }
  return input.url;
}

function requestBodyText(body: BodyInit | null | undefined): string {
  return typeof body === "string" ? body : "";
}

const SAMPLE_WORK_MODES_RESPONSE = {
  default_mode_id: "task",
  modes: [
    {
      id: "task",
      name: "日常办公",
      description: "Default office tasks mode",
      builtin: true,
      editable: false,
      is_default: true,
      skills: [
        { skill_id: "bootstrap", locked: true },
        { skill_id: "find-skills", locked: true },
        { skill_id: "skill-creator", locked: true },
        { skill_id: "news-search", locked: false },
      ],
    },
    {
      id: "coding",
      name: "编程",
      description: "Coding mode",
      builtin: true,
      editable: false,
      is_default: false,
      skills: [
        { skill_id: "bootstrap", locked: true },
        { skill_id: "skill-creator", locked: true },
        { skill_id: "kk-stock-analysis", locked: false },
      ],
    },
  ],
};

describe("work-modes api", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  test("loadWorkModes fetches /api/work-modes and returns parsed modes", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(JSON.stringify(SAMPLE_WORK_MODES_RESPONSE), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );

    const result = await loadWorkModes();

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0]!;
    expect(fetchUrl(url)).toContain("/api/work-modes");
    expect(init?.method ?? "GET").toBe("GET");

    expect(result.default_mode_id).toBe("task");
    expect(result.modes).toHaveLength(2);
    expect(result.modes[0]!.id).toBe("task");
    expect(result.modes[0]!.is_default).toBe(true);
    expect(result.modes[0]!.skills).toHaveLength(4);
    // Locked core skills are flagged
    const bootstrap = result.modes[0]!.skills.find(
      (s) => s.skill_id === "bootstrap",
    );
    expect(bootstrap?.locked).toBe(true);
    // Non-locked skill
    const newsSearch = result.modes[0]!.skills.find(
      (s) => s.skill_id === "news-search",
    );
    expect(newsSearch?.locked).toBe(false);
  });

  test("loadWorkModes returns fallback builtin modes on network failure", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("network down"));

    const result = await loadWorkModes();

    // Fallback: at least the default "task" mode must be present so the UI
    // never renders an empty selector even when the backend is unreachable.
    expect(result.modes.length).toBeGreaterThan(0);
    const hasTaskMode = result.modes.some((m) => m.id === "task");
    expect(hasTaskMode).toBe(true);
    expect(result.default_mode_id).toBe("task");
  });

  test("addSkillToWorkMode PUTs /api/work-modes/{mode}/skills/{skill}", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(
          JSON.stringify({ success: true, mode_id: "task", skill_id: "x" }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        ),
      );

    await addSkillToWorkMode("task", "my-skill");

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0]!;
    expect(fetchUrl(url)).toContain(
      "/api/work-modes/task/skills/my-skill",
    );
    expect(init?.method).toBe("PUT");
  });

  test("removeSkillFromWorkMode DELETEs /api/work-modes/{mode}/skills/{skill}", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(
          JSON.stringify({ success: true, mode_id: "task", skill_id: "x" }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        ),
      );

    await removeSkillFromWorkMode("task", "my-skill");

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0]!;
    expect(fetchUrl(url)).toContain(
      "/api/work-modes/task/skills/my-skill",
    );
    expect(init?.method).toBe("DELETE");
  });

  test("removeSkillFromWorkMode rejects when the backend refuses a locked skill (403)", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ detail: "locked core skills cannot be removed" }),
        {
          status: 403,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    await expect(
      removeSkillFromWorkMode("task", "bootstrap"),
    ).rejects.toThrow();
  });

  test("installSkill sends requested work mode bindings", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          success: true,
          skill_name: "coding-helper",
          message: "installed",
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    await installSkill({
      thread_id: "thread-1",
      path: "mnt/user-data/outputs/coding-helper.skill",
      work_modes: ["coding"],
    });

    const [, init] = fetchSpy.mock.calls[0]!;
    expect(init?.method).toBe("POST");
    expect(JSON.parse(requestBodyText(init?.body))).toEqual({
      thread_id: "thread-1",
      path: "mnt/user-data/outputs/coding-helper.skill",
      work_modes: ["coding"],
    });
  });
});
