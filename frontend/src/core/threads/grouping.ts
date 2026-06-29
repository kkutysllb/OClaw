/**
 * Group threads by their resolved work mode for sidebar display.
 *
 * Each thread's work mode is resolved using a 3-layer fallback:
 *   1. ``localStorage`` ``work_mode_id`` (saved at thread creation time)
 *   2. ``localStorage`` ``agent_name`` → ``resolveWorkModeByAgentName``
 *      (covers threads created before ``work_mode_id`` was threaded through)
 *   3. ``DEFAULT_WORK_MODE_ID`` (``"task"``) — the catch-all bucket
 *
 * This keeps older threads visible in the right group without requiring a
 * backend migration, while new threads land in the correct group via the
 * explicit ``work_mode_id`` persisted at creation.
 */

import type { WorkMode } from "@/core/work-modes/types";
import {
  getThreadAgentName,
  getThreadWorkModeId,
} from "@/core/settings/local";
import {
  DEFAULT_WORK_MODE_ID,
  getAvailableWorkModes,
  resolveWorkModeByAgentName,
} from "@/core/work-modes/defaults";
import type { AgentThread } from "./types";

/**
 * Resolve a single thread's ``work_mode_id`` using the 3-layer fallback.
 *
 * Exposed for unit testing and for callers that only need the id (not the
 * full :interface:`WorkMode` metadata).
 */
export function resolveThreadWorkModeId(thread: AgentThread): string {
  const threadId = thread.thread_id;
  const explicit = getThreadWorkModeId(threadId);
  if (explicit) {
    return explicit;
  }
  const agentName = getThreadAgentName(threadId);
  if (agentName !== undefined) {
    return resolveWorkModeByAgentName(agentName).id;
  }
  return DEFAULT_WORK_MODE_ID;
}

export interface ThreadGroup {
  /** The resolved work mode id for this group. */
  workModeId: string;
  /** Display metadata for the group header (icon / order / builtin). */
  workMode: WorkMode;
  /** Threads belonging to this group, in their original order. */
  threads: AgentThread[];
}

/**
 * Group ``threads`` by their resolved ``work_mode_id``.
 *
 * Groups are ordered by :field:`WorkMode.order` ascending so builtin modes
 * appear in a stable order (task before coding). Unknown mode ids (e.g.
 * from a deleted custom mode) are synthesized as a transient mode with
 * ``order: 999`` so they sort last but remain visible.
 *
 * Returns an empty array when ``threads`` is empty — callers should render
 * an empty state rather than hiding the section entirely.
 */
export function groupThreadsByWorkMode(threads: AgentThread[]): ThreadGroup[] {
  if (threads.length === 0) {
    return [];
  }

  const modes = getAvailableWorkModes([]);
  const byMode = new Map<string, AgentThread[]>();
  for (const thread of threads) {
    const modeId = resolveThreadWorkModeId(thread);
    const bucket = byMode.get(modeId);
    if (bucket) {
      bucket.push(thread);
    } else {
      byMode.set(modeId, [thread]);
    }
  }

  const groups: ThreadGroup[] = [];
  for (const [modeId, bucketThreads] of byMode) {
    const mode = modes.find((m) => m.id === modeId) ?? synthesizeUnknownMode(modeId);
    groups.push({
      workModeId: modeId,
      workMode: mode,
      threads: bucketThreads,
    });
  }
  groups.sort((a, b) => a.workMode.order - b.workMode.order);
  return groups;
}

function synthesizeUnknownMode(modeId: string): WorkMode {
  return {
    id: modeId,
    name: modeId,
    icon: "Bot",
    builtin: false,
    enabled: true,
    order: 999,
  };
}
