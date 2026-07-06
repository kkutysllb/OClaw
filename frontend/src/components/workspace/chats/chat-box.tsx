import { FilesIcon, XIcon } from "lucide-react";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import type { GroupImperativeHandle } from "react-resizable-panels";

import { ConversationEmptyState } from "@/components/ai-elements/conversation";
import { Button } from "@/components/ui/button";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { TodosProvider, useTodos } from "@/core/todos/context";
import { env } from "@/env";
import { cn } from "@/lib/utils";

import {
  ArtifactFileDetail,
  ArtifactFileList,
  useArtifacts,
} from "../artifacts";
import { useThread } from "../messages/context";
import { TodoList } from "../todo-list";

// 三栏布局比例: chat | todos | artifacts
const LAYOUT_MODES = {
  allClosed: { chat: 100, todos: 0, artifacts: 0 },
  todosOpen: { chat: 75, todos: 25, artifacts: 0 },
  artifactsOpen: { chat: 60, todos: 0, artifacts: 40 },
  bothOpen: { chat: 50, todos: 22, artifacts: 28 },
} as const;

function computeLayout(
  todosOpen: boolean,
  artifactsOpen: boolean,
  hasArtifactsPanel: boolean,
) {
  // artifacts 面板被禁用时,只有 chat | todos 两栏
  if (!hasArtifactsPanel) {
    return todosOpen ? LAYOUT_MODES.todosOpen : LAYOUT_MODES.allClosed;
  }
  if (todosOpen && artifactsOpen) return LAYOUT_MODES.bothOpen;
  if (todosOpen) return LAYOUT_MODES.todosOpen;
  if (artifactsOpen) return LAYOUT_MODES.artifactsOpen;
  return LAYOUT_MODES.allClosed;
}

interface ChatBoxProps {
  children: React.ReactNode;
  threadId: string;
  workModeId?: string;
  artifactsMode?: "side-panel" | "disabled";
}

const ChatBoxInner: React.FC<ChatBoxProps> = ({
  children,
  threadId,
  workModeId,
  artifactsMode = "side-panel",
}) => {
  const { thread } = useThread();
  const pathname = usePathname();
  const threadIdRef = useRef(threadId);
  const layoutRef = useRef<GroupImperativeHandle>(null);

  const {
    artifacts,
    open: artifactsOpen,
    setOpen: setArtifactsOpen,
    setArtifacts,
    select: selectArtifact,
    deselect,
    selectedArtifact,
  } = useArtifacts();

  const { open: todosOpen, setOpen: setTodosOpen } = useTodos();

  const [autoSelectFirstArtifact, setAutoSelectFirstArtifact] = useState(true);
  useEffect(() => {
    if (threadIdRef.current !== threadId) {
      threadIdRef.current = threadId;
      deselect();
    }

    // Update artifacts from the current thread
    setArtifacts(thread.values.artifacts ?? []);

    // DO NOT automatically deselect the artifact when switching threads, because the artifacts auto discovering is not work now.
    // if (
    //   selectedArtifact &&
    //   !thread.values.artifacts?.includes(selectedArtifact)
    // ) {
    //   deselect();
    // }

    if (
      env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true" &&
      autoSelectFirstArtifact
    ) {
      if (thread?.values?.artifacts?.length > 0) {
        setAutoSelectFirstArtifact(false);
        selectArtifact(thread.values.artifacts[0]!);
      }
    }
  }, [
    threadId,
    autoSelectFirstArtifact,
    deselect,
    selectArtifact,
    selectedArtifact,
    setArtifacts,
    thread.values.artifacts,
  ]);

  const artifactPanelOpen = useMemo(() => {
    if (env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true") {
      return artifactsOpen && artifacts?.length > 0;
    }
    return artifactsOpen;
  }, [artifactsOpen, artifacts]);

  const effectiveWorkModeId = workModeId ?? thread.values.context?.work_mode_id;

  const resizableIdBase = useMemo(() => {
    return pathname.replace(/[^a-zA-Z0-9_-]+/g, "-").replace(/^-+|-+$/g, "");
  }, [pathname]);

  const hasArtifactsPanel = artifactsMode !== "disabled";

  useEffect(() => {
    if (layoutRef.current) {
      layoutRef.current.setLayout(
        computeLayout(
          todosOpen,
          artifactPanelOpen,
          hasArtifactsPanel,
        ) as Record<string, number>,
      );
    }
  }, [todosOpen, artifactPanelOpen, hasArtifactsPanel]);

  if (artifactsMode === "disabled") {
    // artifacts 被禁用时,仍然渲染 chat | todos 两栏,使 todos 面板可用
    return (
      <ResizablePanelGroup
        id={`${resizableIdBase}-panels`}
        orientation="horizontal"
        defaultLayout={LAYOUT_MODES.allClosed}
        groupRef={layoutRef}
      >
        <ResizablePanel className="relative" defaultSize={100} id="chat">
          {children}
        </ResizablePanel>
        <ResizableHandle
          id={`${resizableIdBase}-todos-separator`}
          className={cn(
            "opacity-33 hover:opacity-100",
            !todosOpen && "pointer-events-none opacity-0",
          )}
        />
        <ResizablePanel
          className={cn(
            "transition-all duration-300 ease-in-out",
            !todosOpen && "opacity-0",
          )}
          id="todos"
        >
          <div
            className={cn(
              "h-full transition-transform duration-300 ease-in-out",
              todosOpen ? "translate-x-0" : "translate-x-full",
            )}
          >
            <TodoList
              todos={thread?.values?.todos ?? []}
              collapsed={false}
              onToggle={() => setTodosOpen(false)}
            />
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    );
  }

  return (
    <ResizablePanelGroup
      id={`${resizableIdBase}-panels`}
      orientation="horizontal"
      defaultLayout={LAYOUT_MODES.allClosed}
      groupRef={layoutRef}
    >
      <ResizablePanel className="relative" defaultSize={100} id="chat">
        {children}
      </ResizablePanel>

      <ResizableHandle
        id={`${resizableIdBase}-todos-separator`}
        className={cn(
          "opacity-33 hover:opacity-100",
          !todosOpen && "pointer-events-none opacity-0",
        )}
      />

      <ResizablePanel
        className={cn(
          "transition-all duration-300 ease-in-out",
          !todosOpen && "opacity-0",
        )}
        id="todos"
      >
        <div
          className={cn(
            "h-full transition-transform duration-300 ease-in-out",
            todosOpen ? "translate-x-0" : "translate-x-full",
          )}
        >
          <TodoList
            todos={thread?.values?.todos ?? []}
            collapsed={false}
            onToggle={() => setTodosOpen(false)}
          />
        </div>
      </ResizablePanel>

      <ResizableHandle
        id={`${resizableIdBase}-separator`}
        className={cn(
          "opacity-33 hover:opacity-100",
          !artifactPanelOpen && "pointer-events-none opacity-0",
        )}
      />
      <ResizablePanel
        className={cn(
          "transition-all duration-300 ease-in-out",
          !artifactsOpen && "opacity-0",
        )}
        id="artifacts"
      >
        <div
          className={cn(
            "h-full p-4 transition-transform duration-300 ease-in-out",
            artifactPanelOpen ? "translate-x-0" : "translate-x-full",
          )}
        >
          {selectedArtifact ? (
            <ArtifactFileDetail
              className="size-full"
              filepath={selectedArtifact}
              threadId={threadId}
              workModeId={effectiveWorkModeId}
            />
          ) : (
            <div className="relative flex size-full justify-center">
              <div className="absolute top-1 right-1 z-30">
                <Button
                  size="icon-sm"
                  variant="ghost"
                  onClick={() => {
                    setArtifactsOpen(false);
                  }}
                >
                  <XIcon />
                </Button>
              </div>
              {thread.values.artifacts?.length === 0 ? (
                <ConversationEmptyState
                  icon={<FilesIcon />}
                  title="No artifact selected"
                  description="Select an artifact to view its details"
                />
              ) : (
                <div className="flex size-full max-w-(--container-width-sm) flex-col justify-center p-4 pt-8">
                  <header className="shrink-0">
                    <h2 className="text-lg font-medium">Artifacts</h2>
                  </header>
                  <main className="min-h-0 grow">
                    <ArtifactFileList
                      className="max-w-(--container-width-sm) p-4 pt-12"
                      files={thread.values.artifacts ?? []}
                      threadId={threadId}
                      workModeId={effectiveWorkModeId}
                    />
                  </main>
                </div>
              )}
            </div>
          )}
        </div>
      </ResizablePanel>
    </ResizablePanelGroup>
  );
};

export { ChatBoxInner as ChatBox };
