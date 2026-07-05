"use client";

import { ListChecksIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useTodos } from "@/core/todos/context";
import type { Todo } from "@/core/todos/types";
import { cn } from "@/lib/utils";

interface Props {
  todos: Todo[] | undefined;
}

export function TodoTrigger({ todos }: Props) {
  const { open, toggle } = useTodos();
  const count = todos?.length ?? 0;
  const inProgress =
    todos?.filter((t) => t.status === "in_progress").length ?? 0;

  return (
    <Button
      variant="ghost"
      size="sm"
      className={cn("gap-1", open && "bg-accent")}
      onClick={toggle}
      aria-label="任务清单"
      aria-pressed={open}
    >
      <ListChecksIcon className="size-4" />
      任务
      {count > 0 && (
        <Badge variant="secondary" className="ml-1 h-4 px-1.5 text-[10px]">
          {inProgress > 0 ? `${inProgress}/${count}` : count}
        </Badge>
      )}
    </Button>
  );
}
