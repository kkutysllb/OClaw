"use client";
import { PromptInputProvider } from "@/components/ai-elements/prompt-input";
import { ArtifactsProvider } from "@/components/workspace/artifacts";
import { SubtasksProvider } from "@/core/tasks/context";
import { TodosProvider } from "@/core/todos/context";
export function ChatProviders({ children }: { children: React.ReactNode }) {
  return (
    <SubtasksProvider>
      <ArtifactsProvider>
        <TodosProvider>
          <PromptInputProvider>{children}</PromptInputProvider>
        </TodosProvider>
      </ArtifactsProvider>
    </SubtasksProvider>
  );
}
