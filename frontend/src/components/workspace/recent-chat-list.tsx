"use client";

import {
  Briefcase,
  Code2,
  Download,
  FileJson,
  FileText,
  MoreHorizontal,
  Pencil,
  Share2,
  SparklesIcon,
  Trash2,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { getAPIClient } from "@/core/api";
import { useI18n } from "@/core/i18n/hooks";
import {
  exportThreadAsJSON,
  exportThreadAsMarkdown,
} from "@/core/threads/export";
import { groupThreadsByWorkMode } from "@/core/threads/grouping";
import type { ThreadGroup } from "@/core/threads/grouping";
import type { WorkMode } from "@/core/work-modes/types";
import { useWorkModes } from "@/core/work-modes/hooks";
import {
  useDeleteThread,
  useRenameThread,
  useThreads,
} from "@/core/threads/hooks";
import type { AgentThread, AgentThreadState } from "@/core/threads/types";
import { pathOfThread, titleOfThread } from "@/core/threads/utils";
import { env } from "@/env";
import { isIMEComposing } from "@/lib/ime";

/**
 * Map a :field:`WorkMode.icon` identifier to a Lucide component for group
 * headers.
 *
 * Mirrors the ICON_MAP in :component:`WorkModeSelector` but only carries the
 * icons used by builtin + transient modes that can appear in the sidebar.
 * Unknown icons fall back to Briefcase so the header always renders a glyph.
 */
const GROUP_ICON_MAP: Record<string, LucideIcon> = {
  Briefcase,
  Code2,
  Sparkles: SparklesIcon,
};

/**
 * Resolve a dot-path i18n key (e.g. ``"workModes.task.name"``) from the
 * translation object. Returns the literal string when it isn't an i18n path
 * (transient / unknown mode ids) so the header still renders a sensible
 * label instead of the raw dotted key.
 */
function resolveModeName(name: string, t: unknown): string {
  if (!name.startsWith("workModes.")) return name;
  const parts = name.split(".");
  let current: unknown = t;
  for (const part of parts) {
    if (current && typeof current === "object" && part in current) {
      current = (current as Record<string, unknown>)[part];
    } else {
      return name;
    }
  }
  return typeof current === "string" ? current : name;
}

function parseThreadIdFromPath(pathname: string | null): string {
  if (!pathname) return "new";
  const match = pathname.match(/\/chats\/([^/?#]+)/);
  const raw = match?.[1];
  if (!raw) return "new";
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}

function parseAgentNameFromPath(pathname: string | null): string | undefined {
  if (!pathname) return undefined;
  const match = pathname.match(/\/workspace\/agents\/([^/]+)\//);
  const raw = match?.[1];
  if (!raw) return undefined;
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}

export function RecentChatList() {
  const { t } = useI18n();
  const router = useRouter();
  const pathname = usePathname();
  // In the Electron desktop build, useParams() returns stale values from the
  // pre-rendered new.html RSC payload. Parse thread_id and agent_name from
  // the real URL pathname instead.
  const threadIdFromPath = parseThreadIdFromPath(pathname);
  const agentNameFromPath = parseAgentNameFromPath(pathname);
  const { data: threads = [] } = useThreads();
  const { mutate: deleteThread } = useDeleteThread();
  const { mutate: renameThread } = useRenameThread();

  // Group threads by their resolved work mode. Pass the API-backed mode
  // list (includes custom modes) so custom mode names display correctly
  // instead of falling back to the raw mode id.
  const { data: workModesData } = useWorkModes();
  const extraModes: WorkMode[] = workModesData.modes
    .filter((m) => !m.builtin)
    .map((m) => ({
      id: m.id,
      name: m.name,
      description: m.description,
      icon: "Sparkles",
      builtin: false,
      enabled: true,
      order: m.is_default ? 0 : 10,
    }));
  const groups = groupThreadsByWorkMode(threads, extraModes);

  // Rename dialog state
  const [renameDialogOpen, setRenameDialogOpen] = useState(false);
  const [renameThreadId, setRenameThreadId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const handleDelete = useCallback(
    (threadId: string) => {
      deleteThread({ threadId });
      if (threadId === threadIdFromPath) {
        const threadIndex = threads.findIndex((t) => t.thread_id === threadId);
        let nextThreadPath = pathOfThread("new", {
          agent_name: agentNameFromPath,
        });
        if (threadIndex > -1) {
          if (threads[threadIndex + 1]) {
            nextThreadPath = pathOfThread(threads[threadIndex + 1]!);
          } else if (threads[threadIndex - 1]) {
            nextThreadPath = pathOfThread(threads[threadIndex - 1]!);
          }
        }
        void router.push(nextThreadPath);
      }
    },
    [agentNameFromPath, deleteThread, router, threadIdFromPath, threads],
  );

  const handleRenameClick = useCallback(
    (threadId: string, currentTitle: string) => {
      setRenameThreadId(threadId);
      setRenameValue(currentTitle);
      setRenameDialogOpen(true);
    },
    [],
  );

  const handleRenameSubmit = useCallback(() => {
    if (renameThreadId && renameValue.trim()) {
      renameThread({ threadId: renameThreadId, title: renameValue.trim() });
      setRenameDialogOpen(false);
      setRenameThreadId(null);
      setRenameValue("");
    }
  }, [renameThread, renameThreadId, renameValue]);

  const handleShare = useCallback(
    async (thread: AgentThread) => {
      // Always use Vercel URL for sharing so others can access
      const VERCEL_URL = "https://kkoclaw.com";
      const isLocalhost =
        window.location.hostname === "localhost" ||
        window.location.hostname === "127.0.0.1";
      // On localhost: use Vercel URL; On production: use current origin
      const baseUrl = isLocalhost ? VERCEL_URL : window.location.origin;
      const shareUrl = `${baseUrl}${pathOfThread(thread)}`;
      try {
        await navigator.clipboard.writeText(shareUrl);
        toast.success(t.clipboard.linkCopied);
      } catch {
        toast.error(t.clipboard.failedToCopyToClipboard);
      }
    },
    [t],
  );

  const handleExport = useCallback(
    async (thread: AgentThread, format: "markdown" | "json") => {
      try {
        const apiClient = getAPIClient();
        const state = await apiClient.threads.getState<AgentThreadState>(
          thread.thread_id,
        );
        const messages = state.values?.messages ?? [];
        if (messages.length === 0) {
          toast.error(t.conversation.noMessages);
          return;
        }
        if (format === "markdown") {
          exportThreadAsMarkdown(thread, messages);
        } else {
          exportThreadAsJSON(thread, messages);
        }
        toast.success(t.common.exportSuccess);
      } catch {
        toast.error("Failed to export conversation");
      }
    },
    [t],
  );

  // Callback bundle so each ThreadModeGroup doesn't need to re-create
  // closures or take the root's hook values as individual props.
  const threadActions = {
    onRename: handleRenameClick,
    onShare: handleShare,
    onExport: handleExport,
    onDelete: handleDelete,
  };

  return (
    <>
      {groups.map((group) => (
        <ThreadModeGroup
          key={group.workModeId}
          group={group}
          pathname={pathname}
          t={t}
          actions={threadActions}
        />
      ))}

      {/* Rename Dialog — single source of truth shared across all groups */}
      <Dialog open={renameDialogOpen} onOpenChange={setRenameDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>{t.common.rename}</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <Input
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              placeholder={t.common.rename}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !isIMEComposing(e)) {
                  e.preventDefault();
                  handleRenameSubmit();
                }
              }}
            />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setRenameDialogOpen(false)}
            >
              {t.common.cancel}
            </Button>
            <Button onClick={handleRenameSubmit}>{t.common.save}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

/**
 * Render one work-mode bucket as a labelled ``SidebarGroup``.
 *
 * The label shows the mode icon, resolved display name (i18n or literal),
 * and a thread-count badge. Threads inside reuse the same rename/share/
 * export/delete menu that the old flat list had.
 */
function ThreadModeGroup({
  group,
  pathname,
  t,
  actions,
}: {
  group: ThreadGroup;
  pathname: string;
  t: ReturnType<typeof useI18n>["t"];
  actions: {
    onRename: (threadId: string, currentTitle: string) => void;
    onShare: (thread: AgentThread) => void;
    onExport: (thread: AgentThread, format: "markdown" | "json") => void;
    onDelete: (threadId: string) => void;
  };
}) {
  const Icon = GROUP_ICON_MAP[group.workMode.icon] ?? Briefcase;
  const displayName = resolveModeName(group.workMode.name, t);
  const count = group.threads.length;

  return (
    <SidebarGroup>
      <SidebarGroupLabel>
        <Icon className="mr-1.5 size-3.5 text-muted-foreground" />
        <span className="truncate">{displayName}</span>
        <span className="ml-auto rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
          {count}
        </span>
      </SidebarGroupLabel>
      <SidebarGroupContent className="group-data-[collapsible=icon]:pointer-events-none group-data-[collapsible=icon]:-mt-8 group-data-[collapsible=icon]:opacity-0">
        <SidebarMenu>
          <div className="flex w-full flex-col gap-1">
            {group.threads.map((thread) => {
              const isActive = pathOfThread(thread) === pathname;
              return (
                <SidebarMenuItem
                  key={thread.thread_id}
                  className="group/side-menu-item"
                >
                  <SidebarMenuButton isActive={isActive} asChild>
                    <div>
                      <Link
                        className="text-muted-foreground block w-full whitespace-nowrap group-hover/side-menu-item:overflow-hidden"
                        href={pathOfThread(thread)}
                      >
                        {titleOfThread(thread)}
                      </Link>
                      {env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY !== "true" && (
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <SidebarMenuAction
                              showOnHover
                              className="bg-background/50 hover:bg-background"
                            >
                              <MoreHorizontal />
                              <span className="sr-only">{t.common.more}</span>
                            </SidebarMenuAction>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent
                            className="w-48 rounded-lg"
                            side={"right"}
                            align={"start"}
                          >
                            <DropdownMenuItem
                              onSelect={() =>
                                actions.onRename(
                                  thread.thread_id,
                                  titleOfThread(thread),
                                )
                              }
                            >
                              <Pencil className="text-blue-500" />
                              <span>{t.common.rename}</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onSelect={() => actions.onShare(thread)}
                            >
                              <Share2 className="text-emerald-500" />
                              <span>{t.common.share}</span>
                            </DropdownMenuItem>
                            <DropdownMenuSub>
                              <DropdownMenuSubTrigger>
                                <Download className="text-violet-500" />
                                <span>{t.common.export}</span>
                              </DropdownMenuSubTrigger>
                              <DropdownMenuSubContent>
                                <DropdownMenuItem
                                  onSelect={() =>
                                    actions.onExport(thread, "markdown")
                                  }
                                >
                                  <FileText className="text-cyan-500" />
                                  <span>{t.common.exportAsMarkdown}</span>
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                  onSelect={() =>
                                    actions.onExport(thread, "json")
                                  }
                                >
                                  <FileJson className="text-amber-500" />
                                  <span>{t.common.exportAsJSON}</span>
                                </DropdownMenuItem>
                              </DropdownMenuSubContent>
                            </DropdownMenuSub>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              onSelect={() => actions.onDelete(thread.thread_id)}
                            >
                              <Trash2 className="text-rose-500" />
                              <span>{t.common.delete}</span>
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      )}
                    </div>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              );
            })}
          </div>
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}
