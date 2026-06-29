# Task Tool Improvements

## Overview

The task tool has been improved to eliminate wasteful LLM polling. Previously, when using background tasks, the LLM had to repeatedly call `task_status` to poll for completion status, resulting in unnecessary API requests.

## Changes

### 1. Removed the `run_in_background` Parameter

The `run_in_background` parameter has been removed from the `task` tool. All sub-agent tasks now run asynchronously by default, but the tool automatically handles completion status.

**Before:**
```python
# LLM had to manage polling
task_id = task(
    subagent_type="bash",
    prompt="Run tests",
    description="Run tests",
    run_in_background=True
)
# Then LLM had to poll repeatedly:
while True:
    status = task_status(task_id)
    if completed:
        break
```

**After:**
```python
# Tool blocks until completion, polling happens in the background
result = task(
    subagent_type="bash",
    prompt="Run tests",
    description="Run tests"
)
# Get result immediately after call returns
```

### 2. Backend Polling

`task_tool` now:
- Asynchronously starts the sub-agent task
- Polls for completion status in the backend (every 2 seconds)
- Blocks the tool call until completion
- Returns the final result directly

This means:
- ✅ LLM only needs **one** tool call
- ✅ No wasteful LLM polling requests
- ✅ Backend handles all status checks
- ✅ Timeout protection (max 5 minutes)

### 3. Removed `task_status` from LLM Tools

`task_status_tool` is no longer exposed to the LLM. It remains in the codebase for internal/debug use, but the LLM cannot call it.

### 4. Updated Documentation

- Updated `SUBAGENT_SECTION` in `prompt.py`, removing all references to background tasks and polling
- Simplified usage examples
- Clarified that the tool automatically waits for completion

## Implementation Details

### Polling Logic

Located in `packages/harness/kkoclaw/tools/builtins/task_tool.py`:

```python
# Start background execution
task_id = executor.execute_async(prompt)

# Poll for task completion in the backend
while True:
    result = get_background_task_result(task_id)

    # Check if task is completed or failed
    if result.status == SubagentStatus.COMPLETED:
        return f"[Subagent: {subagent_type}]\n\n{result.result}"
    elif result.status == SubagentStatus.FAILED:
        return f"[Subagent: {subagent_type}] Task failed: {result.error}"

    # Wait before polling again
    time.sleep(2)

    # Timeout protection (5 minutes)
    if poll_count > 150:
        return "Task timed out after 5 minutes"
```

### Execution Timeout

In addition to polling timeout, sub-agent execution now has a built-in timeout mechanism:

**Configuration** (`packages/harness/kkoclaw/subagents/config.py`):
```python
@dataclass
class SubagentConfig:
    # ...
    timeout_seconds: int = 300  # 5 minute default
```

**Thread Pool Architecture**:

To avoid nested thread pools and resource waste, we use two dedicated thread pools:

1. **Scheduler Pool** (`_scheduler_pool`):
   - Max workers: 4
   - Purpose: Coordinate background task execution
   - Runs `run_task()` function, managing task lifecycle

2. **Execution Pool** (`_execution_pool`):
   - Max workers: 8 (larger to avoid blocking)
   - Purpose: Actual sub-agent execution, supports timeout
   - Runs `execute()` method, calling the agent

**How it works**:
```python
# In execute_async():
_scheduler_pool.submit(run_task)  # Submit coordination task

# In run_task():
future = _execution_pool.submit(self.execute, task)  # Submit execution
exec_result = future.result(timeout=timeout_seconds)  # Wait with timeout
```

**Advantages**:
- ✅ Clear separation of concerns (scheduling vs execution)
- ✅ No nested thread pools
- ✅ Timeout enforced at the correct level
- ✅ Better resource utilization

**Two-Tier Timeout Protection**:
1. **Execution timeout**: Sub-agent execution itself has a 5-minute timeout (configurable in SubagentConfig)
2. **Polling timeout**: Tool polling has a 5-minute timeout (30 polls × 10 seconds)

This ensures the system won't wait indefinitely even if sub-agent execution hangs.

### Benefits

1. **Reduced API costs**: No more repeated LLM requests for polling
2. **Simpler user experience**: LLM doesn't need to manage polling logic
3. **Higher reliability**: Backend handles all status checks consistently
4. **Timeout protection**: Two-tier timeout prevents infinite waiting (execution + polling)

## Testing

To verify the changes are correct:

1. Start a sub-agent task that takes a few seconds
2. Verify the tool call blocks until completion
3. Verify the result is returned directly
4. Verify no `task_status` calls are made

Example test scenario:
```python
# This should block for about 10 seconds then return the result
result = task(
    subagent_type="bash",
    prompt="sleep 10 && echo 'Done'",
    description="Test task"
)
# result should contain "Done"
```

## Migration Notes

For users/code that previously used `run_in_background=True`:
- Simply remove that parameter
- Remove any polling logic
- The tool will automatically wait for completion

No other changes needed — the API is backward compatible (except for the removed parameter).
