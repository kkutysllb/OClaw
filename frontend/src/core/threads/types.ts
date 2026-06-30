import type { Message, Thread } from "@langchain/langgraph-sdk";

import type { Todo } from "../todos";

export interface AgentThreadState extends Record<string, unknown> {
  title: string;
  messages: Message[];
  artifacts: string[];
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
