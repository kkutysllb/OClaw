"use client";

import {
  ChevronUpIcon,
  Loader2Icon,
  PencilIcon,
  RotateCwIcon,
  SendHorizonalIcon,
  Trash2Icon,
  ZapIcon,
} from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type {
  QueuedMessage,
  QueuedMessageStatus,
} from "@/core/threads/queue-store";
import { cn } from "@/lib/utils";

const STATUS_LABEL: Record<QueuedMessageStatus, string> = {
  pending: "排队中",
  injecting: "注入中",
  injected: "已注入",
  sending: "发送中",
  error: "失败",
};

const STATUS_CLASS: Record<QueuedMessageStatus, string> = {
  pending: "bg-muted text-muted-foreground",
  injecting:
    "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  injected:
    "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
  sending: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  error: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
};

interface Props {
  /** 所有队列消息（含 pending/injecting/injected/sending/error 各态） */
  messages: QueuedMessage[];
  /** 当前是否有运行中的任务（决定⚡按钮可用性） */
  isStreaming: boolean;
  /** 立即注入回调 */
  onInject: (msg: QueuedMessage) => void;
  /** 删除回调 */
  onRemove: (id: string) => void;
  /** 编辑内容回调 */
  onEdit: (id: string, newContent: string) => void;
  /** 重试回调（error 态） */
  onRetry: (msg: QueuedMessage) => void;
  /** 重排回调 */
  onReorder: (id: string, direction: "up" | "down") => void;
  /** 全部发送回调 */
  onSendAll: () => void;
}

export function QueuedMessagesBar({
  messages,
  isStreaming,
  onInject,
  onRemove,
  onEdit,
  onRetry,
  onReorder,
  onSendAll,
}: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  if (messages.length === 0) return null;

  const pendingCount = messages.filter((m) => m.status === "pending").length;

  const startEdit = (msg: QueuedMessage) => {
    setEditingId(msg.id);
    setEditValue(msg.content);
  };
  const commitEdit = () => {
    if (editingId && editValue.trim()) onEdit(editingId, editValue.trim());
    setEditingId(null);
  };

  return (
    <TooltipProvider delayDuration={300}>
      <div
        role="list"
        aria-label="待发送消息队列"
        className="flex flex-col gap-2 border-t bg-background px-3 py-2"
      >
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-muted-foreground">
            待发送 ({pendingCount})
          </span>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 gap-1 text-xs"
            disabled={pendingCount === 0 || isStreaming}
            onClick={onSendAll}
            title={
              isStreaming ? "任务执行中，将在结束后自动发送" : "全部发送"
            }
          >
            <SendHorizonalIcon className="size-3" />
            全部发送
          </Button>
        </div>

        <div className="flex flex-wrap gap-2">
          {messages.map((msg) => {
            const pendingMsgs = messages.filter((m) => m.status === "pending");
            const pendingPos = pendingMsgs.findIndex((m) => m.id === msg.id);
            const canMoveUp = msg.status === "pending" && pendingPos > 0;
            return (
              <div
                key={msg.id}
                role="listitem"
                className={cn(
                  "relative w-56 rounded-md border bg-muted/50 p-2 text-xs",
                  msg.status === "error" && "border-red-300 dark:border-red-800",
                )}
              >
                <div className="mb-1 flex items-center justify-between gap-1">
                  <Badge
                    variant="secondary"
                    className={cn(
                      "h-4 px-1.5 text-[10px]",
                      STATUS_CLASS[msg.status],
                    )}
                  >
                    {(msg.status === "injecting" ||
                      msg.status === "sending") && (
                      <Loader2Icon className="mr-1 size-2.5 animate-spin" />
                    )}
                    {STATUS_LABEL[msg.status]}
                  </Badge>
                  {msg.status === "error" && msg.error && (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className="max-w-24 truncate text-[10px] text-red-600">
                          {msg.error}
                        </span>
                      </TooltipTrigger>
                      <TooltipContent>{msg.error}</TooltipContent>
                    </Tooltip>
                  )}
                </div>

                {editingId === msg.id ? (
                  <textarea
                    autoFocus
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    onBlur={commitEdit}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        commitEdit();
                      } else if (e.key === "Escape") {
                        setEditingId(null);
                      }
                    }}
                    className="w-full resize-none rounded border bg-background px-1 py-0.5 text-xs outline-none"
                    rows={2}
                  />
                ) : (
                  <p className="line-clamp-2 text-foreground" title={msg.content}>
                    {msg.content}
                  </p>
                )}

                {/* 操作按钮 */}
                <div className="mt-1.5 flex items-center gap-0.5">
                  {msg.status === "pending" && (
                    <>
                      <IconBtn label="编辑" onClick={() => startEdit(msg)}>
                        <PencilIcon className="size-3" />
                      </IconBtn>
                      <IconBtn
                        label="上移"
                        onClick={() => onReorder(msg.id, "up")}
                        disabled={!canMoveUp}
                      >
                        <ChevronUpIcon className="size-3" />
                      </IconBtn>
                      <IconBtn label="删除" onClick={() => onRemove(msg.id)}>
                        <Trash2Icon className="size-3" />
                      </IconBtn>
                      <IconBtn
                        label={
                          isStreaming
                            ? "立即注入到运行中的任务"
                            : "任务未运行，请直接发送"
                        }
                        disabled={!isStreaming}
                        onClick={() => onInject(msg)}
                        className={cn(
                          isStreaming && "text-blue-600 hover:text-blue-700",
                        )}
                      >
                        <ZapIcon className="size-3" />
                      </IconBtn>
                    </>
                  )}
                  {msg.status === "injected" && (
                    <IconBtn
                      label="删除（已注入，仅从队列移除）"
                      onClick={() => onRemove(msg.id)}
                    >
                      <Trash2Icon className="size-3" />
                    </IconBtn>
                  )}
                  {msg.status === "error" && (
                    <>
                      <IconBtn label="重试" onClick={() => onRetry(msg)}>
                        <RotateCwIcon className="size-3" />
                      </IconBtn>
                      <IconBtn label="删除" onClick={() => onRemove(msg.id)}>
                        <Trash2Icon className="size-3" />
                      </IconBtn>
                    </>
                  )}
                  {/* injecting / sending: 仅 spinner，无按钮（已在 Badge 里显示 spinner） */}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </TooltipProvider>
  );
}

function IconBtn({
  children,
  label,
  onClick,
  disabled,
  className,
}: {
  children: React.ReactNode;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  className?: string;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className={cn(
            "size-6",
            disabled && "cursor-not-allowed opacity-40",
            className,
          )}
          onClick={onClick}
          disabled={disabled}
          aria-label={label}
        >
          {children}
        </Button>
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );
}
