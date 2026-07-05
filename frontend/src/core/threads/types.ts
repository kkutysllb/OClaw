import type { Message, Thread } from "@langchain/langgraph-sdk";

import type { Todo } from "../todos";

/**
 * Per-thread sandbox permission scope.
 *
 * - `read-only`     — block all write operations (file writes, bash
 *                      redirection, cp/mv/rm/touch/mkdir, ...).
 * - `read-write`    — DEFAULT. Read/write the user workspace + sandbox
 *                      internal paths; external paths rejected unless granted.
 * - `unrestricted`  — trust the whole host (only path traversal rejected).
 *
 * Mirrors the backend `_VALID_SCOPES` in `sandbox/tools.py`. Forwarded to
 * the agent runtime via the gateway's `_CONTEXT_CONFIGURABLE_KEYS`
 * whitelist and resolved by `_resolve_effective_scope` in the sandbox
 * path validators.
 */
export type PermissionScope = "read-only" | "read-write" | "unrestricted";

export const PERMISSION_SCOPES: readonly PermissionScope[] = [
  "read-only",
  "read-write",
  "unrestricted",
] as const;

export interface AgentThreadState extends Record<string, unknown> {
  title: string;
  messages: Message[];
  artifacts: string[];
  context?: Partial<AgentThreadContext>;
  todos?: Todo[];
}

export interface AgentThreadContext extends Record<string, unknown> {
  thread_id: string;
  model_name: string | undefined;
  thinking_enabled: boolean;
  is_plan_mode: boolean;
  subagent_enabled: boolean;
  reasoning_effort?: "minimal" | "low" | "medium" | "high";
  agent_name?: string;
  /**
   * Active work mode preset id (task / coding).
   *
   * Forwarded to the agent runtime via the gateway's
   * ``_CONTEXT_CONFIGURABLE_KEYS`` whitelist. The backend uses it to
   * resolve the effective skill set for this turn (see
   * ``resolve_effective_skill_ids``). Falls back to the default mode
   * ("task") when absent.
   */
  work_mode_id?: string;
  /**
   * Per-thread user-selected workspace directory.
   *
   * When set, the backend's sandbox grants bash/read/write access to
   * this directory for the current thread. Forwarded via the gateway's
   * ``_CONTEXT_CONFIGURABLE_KEYS`` whitelist and injected into
   * ``thread_data`` by ``ThreadDataMiddleware``. Falls back to the
   * default user data root (~/.kkoclaw) when absent.
   */
  user_workspace_path?: string;
  /**
   * Per-thread sandbox permission scope. Controls how wide the backend's
   * path validators cast their allow-list. Forwarded via the gateway's
   * ``_CONTEXT_CONFIGURABLE_KEYS`` whitelist (same channel as
   * ``user_workspace_path``) and injected into ``thread_data`` by
   * ``ThreadDataMiddleware``. Falls back to ``"read-write"`` when absent.
   */
  permission_scope?: PermissionScope;
}

export interface AgentThread extends Thread<AgentThreadState> {
  context?: AgentThreadContext;
}

export interface RunMessage {
  run_id: string;
  content: Message;
  metadata: {
    caller: string;
  };
  created_at: string;
}
