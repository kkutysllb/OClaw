"use client";

import { SparklesIcon } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { type PromptInputMessage } from "@/components/ai-elements/prompt-input";
import { ArtifactTrigger } from "@/components/workspace/artifacts";
import {
  ChatBox,
  useSpecificChatMode,
  useThreadChat,
} from "@/components/workspace/chats";
import { FollowupsProvider } from "@/components/workspace/followups-context";
import { InputBox } from "@/components/workspace/input-box";
import {
  MessageList,
  MESSAGE_LIST_DEFAULT_PADDING_BOTTOM,
  MESSAGE_LIST_FOLLOWUPS_EXTRA_PADDING_BOTTOM,
} from "@/components/workspace/messages";
import { ThreadContext } from "@/components/workspace/messages/context";
import { ThreadTitle } from "@/components/workspace/thread-title";
import { TodoTrigger } from "@/components/workspace/todo-trigger";
import { TokenUsageIndicator } from "@/components/workspace/token-usage-indicator";
import { Welcome } from "@/components/workspace/welcome";
import { WorkModeBadge } from "@/components/workspace/work-mode-badge";
import { WorkModeDetailDrawer } from "@/components/workspace/work-mode-detail-drawer";
import { WorkModeSelector } from "@/components/workspace/work-mode-selector";
import { useI18n } from "@/core/i18n/hooks";
import { useModels } from "@/core/models/hooks";
import { useNotification } from "@/core/notification/hooks";
import {
  useThreadSettings,
  saveThreadAgentName,
  saveThreadWorkModeId,
  saveThreadWorkspacePath,
  saveThreadPermissionScope,
} from "@/core/settings";
import type { PermissionScope } from "@/core/threads";
import { useThreadStream } from "@/core/threads/hooks";
import type { QueuedMessage } from "@/core/threads/queue-store";
import { useQueueCoordinator } from "@/core/threads/use-queue-coordinator";
import { textOfMessage } from "@/core/threads/utils";
import { useWorkModes } from "@/core/work-modes/hooks";
import { env } from "@/env";
import { cn } from "@/lib/utils";

export default function ChatPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [showFollowups, setShowFollowups] = useState(false);
  const [detailModeId, setDetailModeId] = useState<string | null>(null);
  const { threadId, setThreadId, isNewThread, setIsNewThread, isMock } =
    useThreadChat();
  const [settings, setSettings] = useThreadSettings(threadId);
  const { tokenUsageEnabled } = useModels();
  const mountedRef = useRef(false);
  const searchParams = useSearchParams();
  useSpecificChatMode();

  // Detect skill-creation mode (?mode=skill) to show the binding banner.
  const isSkillMode = searchParams.get("mode") === "skill";
  const { data: workModesData } = useWorkModes();

  // When entering a new chat via ?mode=skill&workMode=X, pre-select that
  // work mode so skill_manage_tool auto-binds the new skill to it.
  const workModeInitRef = useRef(false);
  useEffect(() => {
    if (isNewThread && !workModeInitRef.current) {
      workModeInitRef.current = true;
      const workMode = searchParams.get("workMode");
      if (workMode) {
        setSettings("context", { work_mode_id: workMode });
      }
    }
  }, [isNewThread]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    mountedRef.current = true;
  }, []);

  const { showNotification } = useNotification();

  const {
    thread,
    sendMessage,
    isUploading,
    isHistoryLoading,
    hasMoreHistory,
    loadMoreHistory,
    currentRunId,
    registerAutoSendTrigger,
  } = useThreadStream({
    threadId: isNewThread ? undefined : threadId,
    context: settings.context,
    isMock,
    onSend: (_threadId) => {
      setThreadId(_threadId);
      setIsNewThread(false);
    },
    onStart: (createdThreadId) => {
      setThreadId(createdThreadId);
      setIsNewThread(false);
      // ! Important: Never use next.js router for navigation in this case, otherwise it will cause the thread to re-mount and lose all states. Use native history API instead.
      const nextPath = `/workspace/chats/${createdThreadId}`;
      history.replaceState(null, "", nextPath);
      // Lock the work mode for this thread so reopening it always
      // resolves the same effective skill set. Both the legacy
      // ``agent_name`` (older contract) and the canonical
      // ``work_mode_id`` are persisted so either dimension can be
      // used to restore the thread's mode on remount.
      saveThreadAgentName(createdThreadId, settings.context.agent_name as string | undefined);
      saveThreadWorkModeId(createdThreadId, settings.context.work_mode_id as string | undefined);
      // Lock the user-selected workspace path so reopening the thread
      // restores the same directory sandbox permissions.
      saveThreadWorkspacePath(
        createdThreadId,
        settings.context.user_workspace_path as string | undefined,
      );
      // Lock the user-selected permission scope so reopening the thread
      // restores the same sandbox authorization level.
      saveThreadPermissionScope(
        createdThreadId,
        settings.context.permission_scope as PermissionScope | undefined,
      );
    },
    onFinish: (state) => {
      if (document.hidden || !document.hasFocus()) {
        let body = "Conversation finished";
        const lastMessage = state.messages.at(-1);
        if (lastMessage) {
          const textContent = textOfMessage(lastMessage);
          if (textContent) {
            body =
              textContent.length > 200
                ? textContent.substring(0, 200) + "..."
                : textContent;
          }
        }
        showNotification(state.title, { body });
      }
    },
  });

  const handleSubmit = useCallback(
    (message: PromptInputMessage) => {
      void sendMessage(threadId, message);
    },
    [sendMessage, threadId],
  );
  const handleStop = useCallback(async () => {
    await thread.stop();
  }, [thread]);

  // ── 队列协调器（Task 16） ──────────────────────────────────────────
  // sendMessage 签名适配：ThreadStreamLike 期望 (content, attachments)，
  // 而真实 sendMessage 是 (threadId, PromptInputMessage)。这里用闭包包装。
  const coordinator = useQueueCoordinator(
    threadId,
    {
      sendMessage: (content, attachments) =>
        sendMessage(threadId, {
          text: content,
          files: (attachments ?? []) as PromptInputMessage["files"],
        }),
    },
    currentRunId,
  );

  // 把协调器的 autoSendNext 注册到 useThreadStream 的 onFinish 链路，
  // 这样每次任务正常结束（非手动停止）就会自动发送队列里的下一条。
  useEffect(() => {
    registerAutoSendTrigger(coordinator.autoSendNext);
    return () => registerAutoSendTrigger(null);
  }, [coordinator.autoSendNext, registerAutoSendTrigger]);

  const handleEnqueue = useCallback(
    (message: PromptInputMessage) => {
      coordinator.enqueue(message.text, message.files ?? []);
      toast.info(t.queue.toast.queued);
    },
    [coordinator, t.queue.toast.queued],
  );

  // 重试处于 error 态的队列消息：先降级回 pending，再触发 autoSendNext。
  // 若当前无运行任务（currentRunId 为空），injectNow 会 no-op，所以用
  // "降级 + autoSendNext" 让消息在不依赖活动 run 的情况下也能发出。
  const handleRetryQueued = useCallback(
    (msg: QueuedMessage) => {
      coordinator.updateStatus(msg.id, "pending");
      void coordinator.autoSendNext();
    },
    [coordinator],
  );

  const messageListPaddingBottom = showFollowups
    ? MESSAGE_LIST_DEFAULT_PADDING_BOTTOM +
      MESSAGE_LIST_FOLLOWUPS_EXTRA_PADDING_BOTTOM
    : undefined;

  return (
    <ThreadContext.Provider value={{ thread, isMock }}>
      <FollowupsProvider>
      <ChatBox
        threadId={threadId}
        workModeId={settings.context.work_mode_id as string | undefined}
      >
        <div className="relative flex size-full min-h-0 justify-between">
          <header
            className={cn(
              "absolute top-0 right-0 left-0 z-30 flex h-12 shrink-0 items-center px-4",
              isNewThread
                ? "bg-background/0 backdrop-blur-none"
                : "bg-background/80 shadow-xs backdrop-blur",
            )}
          >
            <div className="flex w-full items-center gap-2 text-sm font-medium">
              {!isNewThread && (
                <WorkModeBadge
                  workModeId={settings.context.work_mode_id as string | undefined}
                  agentName={settings.context.agent_name as string | undefined}
                />
              )}
              <ThreadTitle threadId={threadId} thread={thread} />
            </div>
            <div className="flex items-center gap-2">
              <TokenUsageIndicator
                enabled={tokenUsageEnabled}
                messages={thread.messages}
              />
              <TodoTrigger todos={thread.values.todos} />
              <ArtifactTrigger />
            </div>
          </header>
          <main className="flex min-h-0 max-w-full grow flex-col">
            <div className="flex size-full justify-center">
              <MessageList
                className={cn("size-full", !isNewThread && "pt-10")}
                threadId={threadId}
                thread={thread}
                workModeId={settings.context.work_mode_id as string | undefined}
                paddingBottom={messageListPaddingBottom}
                hasMoreHistory={hasMoreHistory}
                loadMoreHistory={loadMoreHistory}
                isHistoryLoading={isHistoryLoading}
              />
            </div>
            <div className="absolute right-0 bottom-0 left-0 z-30 flex justify-center px-4">
              <div
                className={cn(
                  "relative w-full",
                  isNewThread && "-translate-y-[calc(50vh-96px)]",
                  isNewThread
                    ? "max-w-(--container-width-sm)"
                    : "max-w-(--container-width-md)",
                )}
              >
                {isNewThread && (
                  <div className={cn("max-w-(--container-width-sm) mx-auto w-full space-y-6 pb-6")}>
                    <Welcome mode={settings.context.mode} />
                    {isSkillMode && (
                      <SkillModeBindingBanner
                        t={t}
                        workModeId={settings.context.work_mode_id as string | undefined}
                        modes={workModesData.modes}
                      />
                    )}
                    <WorkModeSelector
                      selectedWorkModeId={settings.context.work_mode_id as string | undefined}
                      selectedAgentName={settings.context.agent_name as string | undefined}
                      onSelect={(work_mode_id) => {
                        // Coding mode has its own dedicated workbench — leave
                        // the chat page entirely instead of just flipping the
                        // mode flag. Other modes stay in chat.
                        if (work_mode_id === "coding") {
                          router.push("/workspace/coding");
                          return;
                        }
                        setSettings("context", { work_mode_id });
                      }}
                      onShowDetail={setDetailModeId}
                    />
                  </div>
                )}
                {mountedRef.current ? (
                  <InputBox
                    className={cn("bg-background/5 w-full", isNewThread ? "" : "-translate-y-4")}
                    isNewThread={isNewThread}
                    threadId={threadId}
                    autoFocus={isNewThread}
                    status={
                      thread.error
                        ? "error"
                        : thread.isLoading
                          ? "streaming"
                          : "ready"
                    }
                    context={settings.context}
                    disabled={
                      env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true" ||
                      isUploading
                    }
                    onContextChange={(context) =>
                      setSettings("context", context)
                    }
                    onFollowupsVisibilityChange={setShowFollowups}
                    onSubmit={handleSubmit}
                    onStop={handleStop}
                    onEnqueue={handleEnqueue}
                    queuedMessages={coordinator.messages}
                    onInjectFromQueue={coordinator.injectNow}
                    onRemoveFromQueue={coordinator.remove}
                    onEditQueued={coordinator.editContent}
                    onRetryQueued={handleRetryQueued}
                    onReorderQueued={coordinator.reorder}
                    onSendAllQueued={coordinator.manualSendAll}
                  />
                ) : (
                  <div
                    aria-hidden="true"
                    className={cn(
                      "bg-background/5 h-32 w-full -translate-y-4 rounded-2xl",
                    )}
                  />
                )}
                {env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true" && (
                  <div className="text-muted-foreground/67 w-full translate-y-12 text-center text-xs">
                    {t.common.notAvailableInDemoMode}
                  </div>
                )}
              </div>
            </div>
          </main>
        </div>
      </ChatBox>
      </FollowupsProvider>
      <WorkModeDetailDrawer
        modeId={detailModeId}
        onClose={() => setDetailModeId(null)}
      />
    </ThreadContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// SkillModeBindingBanner — shown when ?mode=skill to make the work-mode
// binding explicit. Reminds the user that the new skill will be bound to
// the currently selected work mode and that switching modes changes the
// binding target.
// ---------------------------------------------------------------------------
function SkillModeBindingBanner({
  t,
  workModeId,
  modes,
}: {
  t: ReturnType<typeof useI18n>["t"];
  workModeId: string | undefined;
  modes: { id: string; name: string }[];
}) {
  const currentMode = modes.find((m) => m.id === workModeId) ?? modes[0];
  const modeName = currentMode?.name ?? workModeId ?? "task";
  return (
    <div className="flex items-start gap-3 rounded-lg border border-violet-500/30 bg-violet-500/5 p-3">
      <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md bg-violet-500/15 text-violet-500">
        <SparklesIcon className="size-3.5" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 text-sm font-medium">
          {t.inputBox.skillModeBanner}
          <span className="inline-flex items-center rounded-md bg-violet-500/15 px-1.5 py-0.5 text-xs font-semibold text-violet-500">
            {modeName}
          </span>
        </div>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {t.inputBox.skillModeBannerHint}
        </p>
      </div>
    </div>
  );
}
