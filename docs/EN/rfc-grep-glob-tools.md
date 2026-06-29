# [RFC] Adding `grep` and `glob` File Search Tools to OClaw

## Summary

I believe this direction is correct and worth pursuing.

If OClaw wants to get closer to the actual workflow of coding agents like Claude Code, having only `ls` / `read_file` / `write_file` / `str_replace` is not enough. Before making modifications, the model typically needs two additional capabilities:

- `glob`: Quickly find files by path patterns
- `grep`: Quickly find candidate locations by content patterns

The value of these two tools is not that "bash can also do it functionally," but that they can replace the model's habit of frequently falling back to `bash find` / `bash grep` / `rg` with lower token cost, stronger constraints, and more stable output formats.

But the premise is that the implementation must be correct: **they should be read-only, structured, constrained, auditable native tools, not simple wrappers around shell commands.**

## Problem

OClaw's current file tool layer mainly covers:

- `ls`: Browse directory structure
- `read_file`: Read file contents
- `write_file`: Write files
- `str_replace`: Do localized string replacement
- `bash`: Fallback command execution

This capability set can complete tasks, but efficiency in the codebase exploration phase is low.

Typical problems:

1. When the model wants to find "all `*.tsx` page files," it can only repeatedly `ls` multiple directory levels, or fall back to `bash find`
2. When the model wants to find "where a symbol / copy / config key appears," it can only `read_file` file by file, or fall back to `bash grep` / `rg`
3. Once falling back to `bash`, tool calls lose structured output, and results become harder to trim, paginate, audit, and make consistent across sandboxes
4. For local mode without host bash enabled, `bash` may even be unavailable, leaving insufficient read-only search capability

Conclusion: What OClaw currently lacks is not "one more shell command," but a **filesystem search layer**.

## Goals

- Provide stable path search and content search capabilities for agents
- Reduce dependency on `bash`, especially during repository exploration
- Stay consistent with the existing sandbox security model
- Output format structured to facilitate the model's subsequent chaining of `read_file` / `str_replace`
- Let local sandbox, container sandbox, and future MCP filesystem tools all comply with the same semantics

## Non-Goals

- Not building a general shell compatibility layer
- Not exposing full grep/find/rg CLI syntax
- Not supporting binary search, complex PCRE features, context window highlighting, or other heavyweight features in the first version
- Not making it "arbitrary disk search" — still only allowed within OClaw-authorized paths

## Why This Is Worth Doing

Referencing the design philosophy of agents like Claude Code, the core value of `glob` and `grep` is not new capabilities themselves, but lowering common "codebase exploration" actions from open-ended shell to the controlled tool layer.

This brings several direct benefits:

1. **Lower model burden**
   The model doesn't need to assemble `find`, `grep`, `rg`, `xargs`, quoting, and other command details itself.

2. **More stable cross-environment behavior**
   Local, Docker, and AIO sandboxes don't need to depend on whether `rg` is installed in the container, and won't experience behavior drift due to shell differences.

3. **Stronger security and audit**
   Call parameters are "search what, where, max results," naturally easier to audit and rate-limit than arbitrary commands.

4. **Better token efficiency**
   `grep` returns hit summaries rather than entire files; the model only calls `read_file` on a few candidate paths.

5. **Friendly to `tool_search`**
   As OClaw continues to expand its tool set, `grep` / `glob` will become very high-frequency base tools worth keeping as built-in, rather than letting the model always fall back to generic bash.

## Proposal

Add two built-in sandbox tools:

- `glob`
- `grep`

Recommended to continue placing them in:

- `backend/packages/harness/kkoclaw/sandbox/tools.py`

And default-include them in the `file:read` group in `config.example.yaml`.

### 1. `glob` Tool

Purpose: Find files or directories by path pattern.

Suggested schema:

```python
@tool("glob", parse_docstring=True)
def glob_tool(
    runtime: ToolRuntime[ContextT, ThreadState],
    description: str,
    pattern: str,
    path: str,
    include_dirs: bool = False,
    max_results: int = 200,
) -> str:
    ...
```

Parameter semantics:

- `description`: Consistent with existing tools
- `pattern`: Glob pattern, e.g., `**/*.py`, `src/**/test_*.ts`
- `path`: Search root directory, must be absolute path
- `include_dirs`: Whether to return directories
- `max_results`: Maximum results to return, prevents blowing up context

Suggested return format:

```text
Found 3 paths under /mnt/user-data/workspace
1. /mnt/user-data/workspace/backend/app.py
2. /mnt/user-data/workspace/backend/tests/test_app.py
3. /mnt/user-data/workspace/scripts/build.py
```

If more suitable for frontend consumption later, JSON strings can also be adopted; but the first version should return readable text to stay consistent with existing tool styles.

### 2. `grep` Tool

Purpose: Search files by content pattern, returning hit location summaries.

Suggested schema:

```python
@tool("grep", parse_docstring=True)
def grep_tool(
    runtime: ToolRuntime[ContextT, ThreadState],
    description: str,
    pattern: str,
    path: str,
    glob: str | None = None,
    literal: bool = False,
    case_sensitive: bool = False,
    max_results: int = 100,
) -> str:
    ...
```

Parameter semantics:

- `pattern`: Search term or regex
- `path`: Search root directory, must be absolute path
- `glob`: Optional path filter, e.g., `**/*.py`
- `literal`: When `True`, match as plain string, not interpreted as regex
- `case_sensitive`: Whether case-sensitive
- `max_results`: Maximum hits returned, not file count

Suggested return format:

```text
Found 4 matches under /mnt/user-data/workspace
/mnt/user-data/workspace/backend/config.py:12: TOOL_GROUPS = [...]
/mnt/user-data/workspace/backend/config.py:48: def load_tool_config(...):
/mnt/user-data/workspace/backend/tools.py:91: "tool_groups"
/mnt/user-data/workspace/backend/tests/test_config.py:22: assert "tool_groups" in data
```

First version recommends only returning:

- File path
- Line number
- Hit line summary

Don't return context blocks to avoid oversized results. If the model needs context, then call `read_file(path, start_line, end_line)`.

## Design Principles

### A. Don't make shell wrappers

Don't implement `grep` as:

```python
subprocess.run("grep ...")
```

Also don't assemble `find` / `rg` commands inside containers.

Reasons:

- Would introduce shell quoting and injection surface
- Would depend on whether different sandbox images have the same commands installed
- Windows / macOS / Linux behavior inconsistencies
- Hard to stably control output count and format

The correct direction is:

- `glob` uses Python standard library path traversal
- `grep` uses Python file-by-file scanning
- Output formatted by OClaw itself

If `rg` is preferred for performance in the future, it should be encapsulated inside the provider with guaranteed external semantics unchanged, not exposing CLI to the model.

### B. Continue Using OClaw's Path Permission Model

These two tools must reuse the current `ls` / `read_file` path validation logic:

- Local mode goes through `validate_local_tool_path(..., read_only=True)`
- Supports `/mnt/skills/...`
- Supports `/mnt/acp-workspace/...`
- Supports thread workspace / uploads / outputs virtual path resolution
- Explicitly rejects unauthorized paths and path traversal

That is, they belong to **file:read**, not a `bash` replacement escalation entry point.

### C. Results Must Have Hard Limits

`glob` / `grep` without hard limits can easily blow up context.

First version recommends at minimum:

- `glob.max_results` default 200, max 1000
- `grep.max_results` default 100, max 500
- Single-line summary max length, e.g., 200 characters
- Binary files skipped
- Oversized files skipped, e.g., single file > 1 MB or controlled by config

Additionally, when hit count exceeds threshold, return:

- Count shown
- Fact of truncation
- Suggestion to narrow search scope

For example:

```text
Found more than 100 matches, showing first 100. Narrow the path or add a glob filter.
```

### D. Tool Semantics Should Complement Each Other

The recommended model workflow should be:

1. `glob` finds candidate files
2. `grep` finds candidate locations
3. `read_file` reads local context
4. `str_replace` / `write_file` executes modifications

This keeps tool boundaries clear and also helps the model form stable habits in prompts.

## Implementation Approach

## Option A: Implement First Version Directly in `sandbox/tools.py`

This is my recommended starting approach.

Approach:

- Add `glob_tool` and `grep_tool` in `sandbox/tools.py`
- Use Python filesystem API directly in local sandbox scenarios
- In non-local sandbox scenarios, preferably also implement through OClaw's own controlled path access layer

Advantages:

- Small change
- Can validate agent effectiveness quickly
- No need to change the `Sandbox` abstraction first

Disadvantages:

- `tools.py` will continue to grow
- If future performance optimization is needed on the provider side, another abstraction layer will be required

## Option B: Extend the `Sandbox` Abstraction First

For example, add:

```python
class Sandbox(ABC):
    def glob(self, path: str, pattern: str, include_dirs: bool = False, max_results: int = 200) -> list[str]:
        ...

    def grep(
        self,
        path: str,
        pattern: str,
        *,
        glob: str | None = None,
        literal: bool = False,
        case_sensitive: bool = False,
        max_results: int = 100,
    ) -> list[GrepMatch]:
        ...
```

Advantages:

- Cleaner abstraction
- Container / remote sandboxes can each optimize

Disadvantages:

- Higher initial introduction cost
- Need to sync changes across all sandbox providers

Conclusion:

**First version should go with Option A; after tool value is validated, consider sinking to the `Sandbox` provider abstraction.**

## Prompting Guidance

If these two tools are introduced, recommend synchronously updating file operation guidance in system prompts:

- Prioritize `glob` when searching for filename patterns
- Prioritize `grep` when searching for code symbols, config keys, copy text
- Only fall back to `bash` when tools are insufficient to achieve the goal

Otherwise the model will still habitually call `bash` first.

## Risks

### 1. Capability overlap with `bash`

This is a fact, but not a problem.

`ls` and `read_file` can also be replaced by `bash`, but we still keep them because structured tools are better suited for agents.

### 2. Performance issues

On large repositories, pure Python `grep` may be slower than `rg`.

Mitigation:

- First version adds result caps and file size caps
- Root path required on path
- Provide `glob` filter to narrow scan scope
- If necessary later, do `rg` optimization inside provider but keep the same schema

### 3. Inconsistent ignore rules

If paths visible to `ls` are invisible to `glob`, the model will be confused.

Mitigation:

- Unify ignore rules
- Document "default skip common dependency and build directories"

### 4. Regex search too complex

If the first version supports many grep dialects, boundaries will be messy.

Mitigation:

- First version only supports Python `re`
- And provides `literal=True` simple mode

## Alternatives Considered

### A. Don't add tools, rely entirely on `bash`

Not recommended.

This would leave OClaw continuously lagging in code exploration experience and weaken capabilities in no-bash or restricted-bash scenarios.

### B. Only add `glob`, not `grep`

Not recommended.

Only solves "find files," not "find locations." The model will eventually fall back to `bash grep`.

### C. Only add `grep`, not `glob`

Also not recommended.

Without path pattern filtering, `grep` scan scope is often too large; `glob` is its natural precursor tool.

### D. Directly integrate MCP filesystem server search capabilities

Not recommended as the primary path in the short term.

MCP can be supplementary, but `glob` / `grep` as OClaw's base coding tools are best kept built-in to be stably available in default installations.

## Acceptance Criteria

- `glob` and `grep` can be default-enabled in `config.example.yaml`
- Both tools belong to the `file:read` group
- Strictly comply with existing path permissions under local sandbox
- Output does not leak host real paths
- Large result sets are truncated with clear notification
- Model can complete typical code modification flow via `glob -> grep -> read_file -> str_replace`
- Repository exploration capability noticeably improved in local mode with host bash disabled

## Rollout Plan

1. Implement `glob_tool` and `grep_tool` in `sandbox/tools.py`
2. Extract ignore rules consistent with `list_dir` to avoid behavior drift
3. Add tool config defaults in `config.example.yaml`
4. Add tests for local path validation, virtual path mapping, result truncation, binary skipping
5. Update README / backend docs / prompt guidance
6. Collect actual agent call data, then decide whether to sink to `Sandbox` abstraction

## Suggested Config

```yaml
tools:
  - name: glob
    group: file:read
    use: kkoclaw.sandbox.tools:glob_tool

  - name: grep
    group: file:read
    use: kkoclaw.sandbox.tools:grep_tool
```

## Final Recommendation

The conclusion is: **it can and should be added.**

But I will explicitly set three boundaries:

1. `grep` / `glob` must be built-in read-only structured tools
2. First version must not be shell wrappers, must not expose CLI dialects directly to the model
3. First validate value in `sandbox/tools.py`, then consider sinking to `Sandbox` provider abstraction

If approached in this direction, it will noticeably improve OClaw's usability in coding / repo exploration scenarios, and the risk is manageable.
