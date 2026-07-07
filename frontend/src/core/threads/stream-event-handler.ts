/**
 * Pure event-dispatch logic extracted from {@link useAgentThread}'s
 * `onCustomEvent` callback so it can be unit-tested without mounting
 * a React component or the `useStream` harness.
 *
 * The handler is intentionally side-effect free apart from the injected
 * dependencies (`toast`, `updateSubtask`). This keeps
 * it deterministic and easy to assert against.
 */

import type { AIMessage } from "@langchain/langgraph-sdk";
import { toast } from "sonner";

/** Callback used to feed `task_running` events into the subtask UI. */
export type UpdateSubtaskFn = (update: {
  id: string;
  latestMessage: AIMessage;
}) => void;

/** All external collaborators the event handler needs. */
export interface StreamEventDependencies {
  /** Subtask context updater from `useUpdateSubtask`. */
  updateSubtask: UpdateSubtaskFn;
}

/**
 * Dispatch a single SSE custom event to the appropriate UI feedback.
 *
 * Supported event types:
 *  - `task_running`                → forward latest AI message to subtask UI
 *  - `subagent_limit_truncated`     → toast warning (tasks silently dropped)
 *  - `task_failed` / `task_timed_out` / `task_cancelled` → toast error
 *  - `llm_retry`                    → generic toast with retry message
 *
 * Unknown events are ignored (forwards-compatible with future backend types).
 */
export function handleStreamEvent(
  event: unknown,
  deps: StreamEventDependencies,
): void {
  const { updateSubtask } = deps;

  if (!isObjectWithKey(event, "type")) {
    return;
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const type = (event as any).type;

  if (type === "task_running") {
    const e = event as {
      type: "task_running";
      task_id: string;
      message: AIMessage;
    };
    updateSubtask({ id: e.task_id, latestMessage: e.message });
    return;
  }

  if (type === "subagent_limit_truncated") {
    const e = event as {
      type: "subagent_limit_truncated";
      dropped_count: number;
      max_concurrent: number;
    };
    toast.warning(
      `已达到子任务并发上限（${e.max_concurrent}），${e.dropped_count} 个任务被跳过。请等待当前任务完成后再试。`,
    );
    return;
  }

  if (type === "task_failed" || type === "task_timed_out" || type === "task_cancelled") {
    const e = event as {
      type: "task_failed" | "task_timed_out" | "task_cancelled";
      task_id: string;
      error?: string;
    };
    const labels: Record<string, string> = {
      task_failed: "子任务执行失败",
      task_timed_out: "子任务执行超时",
      task_cancelled: "子任务已取消",
    };
    const label = labels[type] ?? "子任务异常";
    const errorDetail = e.error ? `：${e.error}` : "";
    toast.error(`${label}${errorDetail}`);
    return;
  }

  if (
    type === "llm_retry" &&
    "message" in (event as object) &&
    typeof (event as { message: unknown }).message === "string" &&
    (event as { message: string }).message.trim()
  ) {
    const e = event as { type: "llm_retry"; message: string };
    toast(e.message);
  }

  // task_interrupted toast disabled per user request
  // Unknown event types are silently ignored.
}

/** Type guard: is `value` a non-null object that contains `key`? */
function isObjectWithKey(value: unknown, key: string): boolean {
  return (
    typeof value === "object" &&
    value !== null &&
    key in value
  );
}
