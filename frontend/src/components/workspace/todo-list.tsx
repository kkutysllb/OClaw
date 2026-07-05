import { ListTodoIcon, XIcon } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import type { Todo } from "@/core/todos";
import { cn } from "@/lib/utils";

import {
  QueueItem,
  QueueItemContent,
  QueueItemIndicator,
  QueueList,
} from "../ai-elements/queue";

export function TodoList({
  className,
  todos,
  collapsed: controlledCollapsed,
  onToggle,
}: {
  className?: string;
  todos: Todo[];
  collapsed?: boolean;
  hidden?: boolean;
  onToggle?: () => void;
}) {
  const [internalCollapsed, setInternalCollapsed] = useState(false);
  const isControlled = controlledCollapsed !== undefined;
  const collapsed = isControlled ? controlledCollapsed : internalCollapsed;

  const handleToggle = () => {
    if (isControlled) {
      onToggle?.();
    } else {
      setInternalCollapsed((prev) => !prev);
    }
  };

  const isEmpty = !todos || todos.length === 0;

  return (
    <div
      className={cn(
        "bg-background flex h-full w-full flex-col overflow-hidden border-l",
        className,
      )}
    >
      <header
        className="bg-accent flex min-h-9 shrink-0 items-center justify-between px-4 text-sm"
        onClick={handleToggle}
      >
        <div className="text-muted-foreground flex items-center gap-2">
          <ListTodoIcon className="size-4" />
          <div>任务清单</div>
        </div>
        {onToggle && (
          <Button
            size="icon-sm"
            variant="ghost"
            aria-label="关闭任务面板"
            onClick={(e) => {
              e.stopPropagation();
              onToggle();
            }}
          >
            <XIcon className="size-4" />
          </Button>
        )}
      </header>
      <main
        className={cn(
          "min-h-0 grow flex-col overflow-y-auto px-2 py-2 transition-all duration-300 ease-out",
          collapsed ? "hidden" : "flex",
        )}
      >
        {isEmpty ? (
          <div className="text-muted-foreground flex h-full items-center justify-center text-sm">
            暂无任务清单
          </div>
        ) : (
          <QueueList className="w-full">
            {todos.map((todo, i) => (
              <QueueItem key={i + (todo.content ?? "")}>
                <div className="flex items-center gap-2">
                  <QueueItemIndicator
                    className={
                      todo.status === "in_progress" ? "bg-primary/70" : ""
                    }
                    completed={todo.status === "completed"}
                  />
                  <QueueItemContent
                    className={
                      todo.status === "in_progress" ? "text-primary/70" : ""
                    }
                    completed={todo.status === "completed"}
                  >
                    {todo.content}
                  </QueueItemContent>
                </div>
              </QueueItem>
            ))}
          </QueueList>
        )}
      </main>
    </div>
  );
}
