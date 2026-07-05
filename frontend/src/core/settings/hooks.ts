import { useCallback, useMemo, useSyncExternalStore } from "react";

import {
  DEFAULT_LOCAL_SETTINGS,
  applyThreadAgentOverride,
  applyThreadModelOverride,
  applyThreadPermissionScopeOverride,
  applyThreadWorkModeOverride,
  applyThreadWorkspacePathOverride,
  type LocalSettings,
} from "./local";
import {
  getBaseSettingsSnapshot,
  getThreadAgentSnapshot,
  getThreadModelSnapshot,
  getThreadPermissionScopeSnapshot,
  getThreadWorkModeSnapshot,
  getThreadWorkspacePathSnapshot,
  hasThreadAgentOverride,
  hasThreadPermissionScopeOverride,
  hasThreadWorkModeOverride,
  hasThreadWorkspacePathOverride,
  subscribe,
  updateLocalSettings,
  updateThreadSettings,
  type LocalSettingsSetter,
} from "./store";

export function useLocalSettings(): [LocalSettings, LocalSettingsSetter] {
  const settings = useSyncExternalStore(
    subscribe,
    getBaseSettingsSnapshot,
    () => DEFAULT_LOCAL_SETTINGS,
  );

  const setSettings = useCallback<LocalSettingsSetter>((key, value) => {
    updateLocalSettings(key, value);
  }, []);

  return [settings, setSettings];
}

export function useThreadSettings(
  threadId: string,
): [LocalSettings, LocalSettingsSetter] {
  const baseSettings = useSyncExternalStore(
    subscribe,
    getBaseSettingsSnapshot,
    () => DEFAULT_LOCAL_SETTINGS,
  );

  const threadModelName = useSyncExternalStore(
    subscribe,
    () => getThreadModelSnapshot(threadId),
    () => undefined,
  );

  const threadAgentName = useSyncExternalStore(
    subscribe,
    () => getThreadAgentSnapshot(threadId),
    () => undefined,
  );

  const threadHasAgentOverride = useSyncExternalStore(
    subscribe,
    () => hasThreadAgentOverride(threadId),
    () => false,
  );

  const threadWorkModeId = useSyncExternalStore(
    subscribe,
    () => getThreadWorkModeSnapshot(threadId),
    () => undefined,
  );

  const threadHasWorkModeOverride = useSyncExternalStore(
    subscribe,
    () => hasThreadWorkModeOverride(threadId),
    () => false,
  );

  const threadWorkspacePath = useSyncExternalStore(
    subscribe,
    () => getThreadWorkspacePathSnapshot(threadId),
    () => undefined,
  );

  const threadHasWorkspacePathOverride = useSyncExternalStore(
    subscribe,
    () => hasThreadWorkspacePathOverride(threadId),
    () => false,
  );

  const threadPermissionScope = useSyncExternalStore(
    subscribe,
    () => getThreadPermissionScopeSnapshot(threadId),
    () => undefined,
  );

  const threadHasPermissionScopeOverride = useSyncExternalStore(
    subscribe,
    () => hasThreadPermissionScopeOverride(threadId),
    () => false,
  );

  const settings = useMemo(
    () => {
      let result = applyThreadModelOverride(baseSettings, threadModelName);
      result = applyThreadAgentOverride(
        result,
        threadAgentName,
        threadHasAgentOverride,
      );
      result = applyThreadWorkModeOverride(
        result,
        threadWorkModeId,
        threadHasWorkModeOverride,
      );
      result = applyThreadWorkspacePathOverride(
        result,
        threadWorkspacePath,
        threadHasWorkspacePathOverride,
      );
      result = applyThreadPermissionScopeOverride(
        result,
        threadPermissionScope,
        threadHasPermissionScopeOverride,
      );
      return result;
    },
    [
      baseSettings,
      threadModelName,
      threadAgentName,
      threadHasAgentOverride,
      threadWorkModeId,
      threadHasWorkModeOverride,
      threadWorkspacePath,
      threadHasWorkspacePathOverride,
      threadPermissionScope,
      threadHasPermissionScopeOverride,
    ],
  );

  const setSettings = useCallback<LocalSettingsSetter>(
    (key, value) => {
      updateThreadSettings(threadId, key, value);
    },
    [threadId],
  );

  return [settings, setSettings];
}
