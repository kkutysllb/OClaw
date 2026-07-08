import { getBackendBaseURL } from "../config";
import type { AgentThread } from "../threads";

/**
 * Percent-encode a filesystem path for safe use in a URL path segment.
 *
 * Splits on ``/`` and encodes each segment individually with
 * ``encodeURIComponent``, then rejoins with ``/``. This preserves path
 * separators while encoding non-ASCII characters (Chinese, accented letters),
 * spaces, and URL-significant characters (``#``, ``?``, ``&``) that would
 * otherwise break the URL or be misinterpreted by the server.
 */
function encodeArtifactPath(path: string): string {
  return path
    .split("/")
    .map((segment) => encodeURIComponent(segment))
    .join("/");
}

export function urlOfArtifact({
  filepath,
  threadId,
  download = false,
  isMock = false,
}: {
  filepath: string;
  threadId: string;
  download?: boolean;
  isMock?: boolean;
}) {
  const encodedPath = encodeArtifactPath(filepath);
  if (isMock) {
    return `${getBackendBaseURL()}/mock/api/threads/${threadId}/artifacts${encodedPath}${download ? "?download=true" : ""}`;
  }
  return `${getBackendBaseURL()}/api/threads/${threadId}/artifacts${encodedPath}${download ? "?download=true" : ""}`;
}

export function extractArtifactsFromThread(thread: AgentThread) {
  return thread.values.artifacts ?? [];
}

export function resolveArtifactURL(absolutePath: string, threadId: string) {
  return `${getBackendBaseURL()}/api/threads/${threadId}/artifacts${encodeArtifactPath(absolutePath)}`;
}

/**
 * Determine whether a string is an artifact path that should be routed through
 * the artifacts API (as opposed to an external URL).
 *
 * Phase 3: artifact paths are real host absolute paths (e.g.
 * `/Users/.../outputs/report.pdf`). A path is an artifact path when it starts
 * with `/` but is not a protocol-relative URL (`//host/...`) or a scheme URL
 * (`http://...`).
 */
export function isArtifactPath(value: string): boolean {
  return value.startsWith("/") && !value.startsWith("//") && !/^[a-z][a-z0-9+.-]*:\/\//i.test(value);
}
