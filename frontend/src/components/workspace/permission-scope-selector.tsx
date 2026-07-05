"use client";

import {
  ChevronDownIcon,
  LockIcon,
  ShieldCheckIcon,
  ShieldXIcon,
} from "lucide-react";
import { useCallback, useState } from "react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";
import type { PermissionScope } from "@/core/threads";

/**
 * Compact dropdown that lets the user pick the per-thread sandbox
 * permission scope.
 *
 * Three scopes (mirror the backend `_VALID_SCOPES`):
 *  - `read-only`     — block all writes
 *  - `read-write`     — DEFAULT. Read/write the user workspace; external paths rejected.
 *  - `unrestricted`   — trust the whole host (only path traversal rejected)
 *
 * The selection is stored per-thread via the settings store and surfaced
 * to the backend via `permission_scope` in the run context. The backend's
 * `_resolve_effective_scope` reads it from `thread_data` and applies it in
 * `validate_local_tool_path` / `validate_local_bash_command_paths`.
 *
 * Mirrors the props shape of `WorkspaceSelector` so the two can sit
 * side-by-side in the input box.
 */
export function PermissionScopeSelector({
  selectedScope,
  onSelect,
  className,
}: {
  /** Current `permission_scope` from thread context (undefined = default read-write). */
  selectedScope?: PermissionScope | undefined;
  /** Called when the user picks a new scope. `undefined` resets to default. */
  onSelect: (scope: PermissionScope | undefined) => void;
  className?: string;
}) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);

  // Effective scope for display: undefined → "read-write" (the default).
  const effective: PermissionScope = selectedScope ?? "read-write";

  const { Icon, label, iconClassName } = scopeDisplay(effective, t);

  const handleSelect = useCallback(
    (scope: PermissionScope) => {
      // Warn the user before enabling unrestricted mode — it grants the
      // Agent access to any host path.
      if (
        scope === "unrestricted" &&
        effective !== "unrestricted" &&
        typeof window !== "undefined" &&
        !window.confirm(t.inputBox.permissionScopeUnrestrictedConfirm)
      ) {
        return;
      }
      // Selecting "read-write" is equivalent to clearing the override
      // (it is the default), so we store undefined to keep the persisted
      // state minimal. The backend treats undefined as read-write via
      // `_resolve_effective_scope`.
      onSelect(scope === "read-write" ? undefined : scope);
      setOpen(false);
    },
    [effective, onSelect, t.inputBox.permissionScopeUnrestrictedConfirm],
  );

  return (
    <div className={cn("flex items-center", className)}>
      <DropdownMenu open={open} onOpenChange={setOpen}>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            className="inline-flex max-w-[200px] items-center gap-1 px-2 text-xs font-normal text-muted-foreground transition-colors hover:text-foreground"
            title={titleFor(effective, t)}
          >
            <Icon className={cn("size-3 shrink-0", iconClassName)} />
            <span className="truncate">{label}</span>
            <ChevronDownIcon className="size-3 shrink-0 opacity-60" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-64" side="top" sideOffset={8}>
          <DropdownMenuLabel className="text-muted-foreground text-xs">
            {t.inputBox.permissionScope}
          </DropdownMenuLabel>

          <ScopeMenuItem
            scope="read-only"
            effective={effective}
            t={t}
            onSelect={handleSelect}
          />
          <ScopeMenuItem
            scope="read-write"
            effective={effective}
            t={t}
            onSelect={handleSelect}
          />
          <DropdownMenuSeparator />
          <ScopeMenuItem
            scope="unrestricted"
            effective={effective}
            t={t}
            onSelect={handleSelect}
            danger
          />
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

type T = ReturnType<typeof useI18n>["t"];

interface ScopeDisplay {
  Icon: typeof LockIcon;
  label: string;
  iconClassName: string;
}

function scopeDisplay(scope: PermissionScope, t: T): ScopeDisplay {
  switch (scope) {
    case "read-only":
      return {
        Icon: LockIcon,
        label: t.inputBox.permissionScopeReadOnly,
        iconClassName: "text-amber-500",
      };
    case "unrestricted":
      return {
        Icon: ShieldXIcon,
        label: t.inputBox.permissionScopeUnrestricted,
        iconClassName: "text-red-500",
      };
    case "read-write":
    default:
      return {
        Icon: ShieldCheckIcon,
        label: t.inputBox.permissionScopeReadWrite,
        iconClassName: "text-emerald-500",
      };
  }
}

function descriptionFor(scope: PermissionScope, t: T): string {
  switch (scope) {
    case "read-only":
      return t.inputBox.permissionScopeReadOnlyDescription;
    case "unrestricted":
      return t.inputBox.permissionScopeUnrestrictedDescription;
    case "read-write":
    default:
      return t.inputBox.permissionScopeReadWriteDescription;
  }
}

function titleFor(scope: PermissionScope, t: T): string {
  return `${t.inputBox.permissionScope}: ${scopeDisplay(scope, t).label} — ${descriptionFor(scope, t)}`;
}

function ScopeMenuItem({
  scope,
  effective,
  t,
  onSelect,
  danger,
}: {
  scope: PermissionScope;
  effective: PermissionScope;
  t: T;
  onSelect: (scope: PermissionScope) => void;
  danger?: boolean;
}) {
  const { Icon, label, iconClassName } = scopeDisplay(scope, t);
  const active = scope === effective;
  return (
    <DropdownMenuItem
      onClick={() => onSelect(scope)}
      className={danger ? "gap-2 text-red-600 dark:text-red-400" : "gap-2"}
    >
      <Icon className={cn("size-3.5 shrink-0", iconClassName)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <span className="text-sm font-medium">{label}</span>
        <span className="text-muted-foreground truncate text-[10px]">
          {descriptionFor(scope, t)}
        </span>
      </div>
      {active && (
        <span className="size-2 shrink-0 rounded-full bg-emerald-500" aria-label="active" />
      )}
    </DropdownMenuItem>
  );
}
