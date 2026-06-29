# Plan Mode & TodoList Middleware

This document describes how to enable and use the Plan Mode feature with TodoList middleware in OClaw 2.0.

## Overview

Plan Mode adds a TodoList middleware to the Agent, providing a `write_todos` tool that helps the Agent:
- Break down complex tasks into smaller, manageable steps
- Track progress as work advances
- Provide users with visibility into ongoing operations

The TodoList middleware is built on LangChain's `TodoListMiddleware`.

## Configuration

### Enabling Plan Mode

Plan Mode is controlled via **runtime configuration** using the `is_plan_mode` parameter in the `configurable` section of `RunnableConfig`. This allows you to dynamically enable or disable plan mode per request.

```python
from langchain_core.runnables import RunnableConfig
from kkoclaw.agents.lead_agent.agent import make_lead_agent

# Enable plan mode via runtime configuration
config = RunnableConfig(
    configurable={
        "thread_id": "example-thread",
        "thinking_enabled": True,
        "is_plan_mode": True,  # Enable plan mode
    }
)

# Create agent with plan mode enabled
agent = make_lead_agent(config)
```

### Configuration Options

- **is_plan_mode** (bool): Whether to enable plan mode with TodoList middleware. Default: `False`
  - Passed via `config.get("configurable", {}).get("is_plan_mode", False)`
  - Can be dynamically set per agent call
  - No global configuration required

## Default Behavior

When plan mode is enabled with default settings, the agent will have access to the `write_todos` tool with the following behavior:

### When to Use TodoList

The Agent will use the todo list when:
1. Complex multi-step tasks (3+ distinct steps)
2. Non-trivial tasks requiring careful planning
3. User explicitly requests a todo list
4. User provides multiple tasks

### When NOT to Use TodoList

The Agent will skip using the todo list when:
1. Single, straightforward task
2. Trivial tasks (fewer than 3 steps)
3. Pure conversation or informational requests

### Task States

- **pending**: Task has not yet started
- **in_progress**: Being worked on (multiple parallel tasks allowed simultaneously)
- **completed**: Task successfully completed

## Usage Examples

### Basic Usage

```python
from langchain_core.runnables import RunnableConfig
from kkoclaw.agents.lead_agent.agent import make_lead_agent

# Create agent with plan mode enabled
config_with_plan_mode = RunnableConfig(
    configurable={
        "thread_id": "example-thread",
        "thinking_enabled": True,
        "is_plan_mode": True,  # Will add TodoList middleware
    }
)
agent_with_todos = make_lead_agent(config_with_plan_mode)

# Create agent with plan mode disabled (default)
config_without_plan_mode = RunnableConfig(
    configurable={
        "thread_id": "another-thread",
        "thinking_enabled": True,
        "is_plan_mode": False,  # No TodoList middleware
    }
)
agent_without_todos = make_lead_agent(config_without_plan_mode)
```

### Dynamic Plan Mode Per Request

You can dynamically enable/disable plan mode for different conversations or tasks:

```python
from langchain_core.runnables import RunnableConfig
from kkoclaw.agents.lead_agent.agent import make_lead_agent

def create_agent_for_task(task_complexity: str):
    """Create agent with plan mode based on task complexity."""
    is_complex = task_complexity in ["high", "very_high"]

    config = RunnableConfig(
        configurable={
            "thread_id": f"task-{task_complexity}",
            "thinking_enabled": True,
            "is_plan_mode": is_complex,  # Enable only for complex tasks
        }
    )

    return make_lead_agent(config)

# Simple task — no TodoList needed
simple_agent = create_agent_for_task("low")

# Complex task — enable TodoList for better tracking
complex_agent = create_agent_for_task("high")
```

## How It Works

1. When `make_lead_agent(config)` is called, it extracts `is_plan_mode` from `config.configurable`
2. The config is passed to `_build_middlewares(config)`
3. `_build_middlewares()` reads `is_plan_mode` and calls `_create_todo_list_middleware(is_plan_mode)`
4. If `is_plan_mode=True`, a `TodoListMiddleware` instance is created and added to the middleware chain
5. The middleware automatically adds the `write_todos` tool to the agent's tool set
6. The Agent can use this tool to manage tasks during execution
7. The middleware handles the todo list state and makes it available to the agent

## Architecture

```
make_lead_agent(config)
  │
  ├─> Extract: is_plan_mode = config.configurable.get("is_plan_mode", False)
  │
  └─> _build_middlewares(config)
        │
        ├─> ThreadDataMiddleware
        ├─> SandboxMiddleware
        ├─> SummarizationMiddleware (enabled via global config)
        ├─> TodoListMiddleware (if is_plan_mode=True) ← NEW
        ├─> TitleMiddleware
        └─> ClarificationMiddleware
```

## Implementation Details

### Agent Module
- **Location**: `packages/harness/kkoclaw/agents/lead_agent/agent.py`
- **Function**: `_create_todo_list_middleware(is_plan_mode: bool)` — Creates TodoListMiddleware if plan mode is enabled
- **Function**: `_build_middlewares(config: RunnableConfig)` — Builds middleware chain based on runtime configuration
- **Function**: `make_lead_agent(config: RunnableConfig)` — Creates agent with appropriate middleware

### Runtime Configuration
Plan Mode is controlled via the `is_plan_mode` parameter in `RunnableConfig.configurable`:
```python
config = RunnableConfig(
    configurable={
        "is_plan_mode": True,  # Enable plan mode
        # ... other configurable options
    }
)
```

## Key Benefits

1. **Dynamic Control**: Enable/disable plan mode per request without global state
2. **Flexibility**: Different conversations can have different plan mode settings
3. **Simplicity**: No global configuration management needed
4. **Context-Aware**: Plan mode decisions can be based on task complexity, user preferences, etc.

## Custom Prompts

OClaw uses custom `system_prompt` and `tool_description` for TodoListMiddleware, matching the overall OClaw prompt style:

### System Prompt Features
- Uses XML tags (`<todo_list_system>`) for structural consistency with the OClaw main prompt
- Emphasizes key rules and best practices
- Clear "when to use" vs "when not to use" guidelines
- Focuses on real-time updates and immediate task completion

### Tool Description Features
- Detailed usage scenarios with examples
- Strong emphasis on NOT using for simple tasks
- Clear task state definitions (pending, in_progress, completed)
- Comprehensive best practices section
- Task completion requirements to prevent premature completion marking

Custom prompts are defined in `_create_todo_list_middleware()`, located at `packages/harness/kkoclaw/agents/lead_agent/agent.py:57`.

## Notes

- TodoList middleware uses LangChain's built-in `TodoListMiddleware` with **custom OClaw-style prompts**
- Plan Mode is **disabled by default** (`is_plan_mode=False`) to maintain backward compatibility
- The middleware is placed before `ClarificationMiddleware`, allowing todo management during the clarification flow
- Custom prompts emphasize the same principles as the OClaw main system prompt (clarity, action-oriented, key rules)
