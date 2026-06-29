# Automatic Thread Title Generation

## Feature Description

Automatically generates titles for conversation threads, triggered after the user's first question and the assistant's first response.

## Implementation

Uses `TitleMiddleware` in the `after_model` hook:
1. Detects if it's the first conversation (1 user message + 1 assistant reply)
2. Checks if the state already has a title
3. Calls the LLM to generate a concise title (default max 6 words)
4. Stores the title in `ThreadState` (persisted by the checkpointer)

TitleMiddleware first normalizes structured block/list content from LangChain message content into plain text before assembling the title prompt, preventing raw Python/JSON repr from leaking into the title generation model.

## ⚠️ Important: Storage Mechanism

### Title Storage Location

Title is stored in **`ThreadState.title`**, not in thread metadata:

```python
class ThreadState(AgentState):
    sandbox: SandboxState | None = None
    title: str | None = None  # ✅ Title stored here
```

### Persistence Details

| Deployment Method | Persistence | Notes |
|---------|--------|------|
| **LangGraph Studio (local)** | ❌ No | In-memory only, lost on restart |
| **LangGraph Platform** | ✅ Yes | Automatically persisted to database |
| **Custom + Checkpointer** | ✅ Yes | Needs PostgreSQL/SQLite checkpointer configured |

### How to Enable Persistence

If you need to persist titles during local development, configure a checkpointer:

```python
# Create checkpointer.py in the same directory as langgraph.json
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(
    "postgresql://user:pass@localhost/dbname"
)
```

Then reference it in `langgraph.json`:

```json
{
  "graphs": {
    "lead_agent": "kkoclaw.agents:lead_agent"
  },
  "checkpointer": "checkpointer:checkpointer"
}
```

## Configuration

Add to `config.yaml` (optional):

```yaml
title:
  enabled: true
  max_words: 6
  max_chars: 60
  model_name: null  # Use default model
```

Or configure in code:

```python
from kkoclaw.config.title_config import TitleConfig, set_title_config

set_title_config(TitleConfig(
    enabled=True,
    max_words=8,
    max_chars=80,
))
```

## Client Usage

### Getting Thread Title

```typescript
// Method 1: Get from thread state
const state = await client.threads.getState(threadId);
const title = state.values.title || "New Conversation";

// Method 2: Listen to stream events
for await (const chunk of client.runs.stream(threadId, assistantId, {
  input: { messages: [{ role: "user", content: "Hello" }] }
})) {
  if (chunk.event === "values" && chunk.data.title) {
    console.log("Title:", chunk.data.title);
  }
}
```

### Displaying Title

```typescript
// Display in conversation list
function ConversationList() {
  const [threads, setThreads] = useState([]);

  useEffect(() => {
    async function loadThreads() {
      const allThreads = await client.threads.list();
      
      // Get each thread's state to read title
      const threadsWithTitles = await Promise.all(
        allThreads.map(async (t) => {
          const state = await client.threads.getState(t.thread_id);
          return {
            id: t.thread_id,
            title: state.values.title || "New Conversation",
            updatedAt: t.updated_at,
          };
        })
      );
      
      setThreads(threadsWithTitles);
    }
    loadThreads();
  }, []);

  return (
    <ul>
      {threads.map(thread => (
        <li key={thread.id}>
          <a href={`/chat/${thread.id}`}>{thread.title}</a>
        </li>
      ))}
    </ul>
  );
}
```

## Workflow

```mermaid
sequenceDiagram
    participant User
    participant Client
    participant LangGraph
    participant TitleMiddleware
    participant LLM
    participant Checkpointer

    User->>Client: Send first message
    Client->>LangGraph: POST /threads/{id}/runs
    LangGraph->>Agent: Process message
    Agent-->>LangGraph: Return reply
    LangGraph->>TitleMiddleware: after_agent()
    TitleMiddleware->>TitleMiddleware: Check if title generation needed
    TitleMiddleware->>LLM: Generate title
    LLM-->>TitleMiddleware: Return title
    TitleMiddleware->>LangGraph: return {"title": "..."}
    LangGraph->>Checkpointer: Save state (with title)
    LangGraph-->>Client: Return response
    Client->>Client: Read from state.values.title
```

## Benefits

✅ **Reliable Persistence** — Uses LangGraph's state mechanism, auto-persisted  
✅ **Fully Backend-Handled** — Client needs no additional logic  
✅ **Auto-Triggered** — Automatically generated after first conversation  
✅ **Configurable** — Supports custom length, model, etc.  
✅ **Fault-Tolerant** — Uses fallback strategy on failure  
✅ **Architecture-Consistent** — Consistent with existing SandboxMiddleware  

## Notes

1. **Different Read Method**: Title is in `state.values.title`, not `thread.metadata.title`
2. **Performance Consideration**: Title generation adds about 0.5–1 second latency; can be optimized by using a faster model
3. **Concurrency Safety**: Middleware runs after agent execution, not blocking the main flow
4. **Fallback Strategy**: If LLM call fails, uses the first few words of the user message as the title

## Testing

```python
# Test title generation
import pytest
from kkoclaw.agents.title_middleware import TitleMiddleware

def test_title_generation():
    # TODO: Add unit tests
    pass
```

## Troubleshooting

### Title Not Generated

1. Check if configuration is enabled: `get_title_config().enabled == True`
2. Check logs: Look for "Generated thread title" or error messages
3. Confirm it's the first conversation: Only triggers with 1 user message and 1 assistant reply

### Title Generated but Client Can't See It

1. Confirm read location: Should read from `state.values.title`, not `thread.metadata.title`
2. Check API response: Confirm state includes the title field
3. Try re-fetching state: `client.threads.getState(threadId)`

### Title Lost After Restart

1. Check if checkpointer is configured (needed for local development)
2. Confirm deployment method: LangGraph Platform auto-persists
3. Check database: Confirm checkpointer is working properly

## Architecture Design

### Why State Instead of Metadata?

| Feature | State | Metadata |
|------|-------|----------|
| **Persistence** | ✅ Automatic (via checkpointer) | ⚠️ Depends on implementation |
| **Version Control** | ✅ Supports time travel | ❌ Not supported |
| **Type Safety** | ✅ TypedDict definition | ❌ Arbitrary dict |
| **Traceability** | ✅ Every update recorded | ⚠️ Only latest value |
| **Standardization** | ✅ LangGraph core mechanism | ⚠️ Extension feature |

### Implementation Details

```python
# TitleMiddleware core logic
@override
def after_agent(self, state: TitleMiddlewareState, runtime: Runtime) -> dict | None:
    """Generate and set thread title after the first agent response."""
    if self._should_generate_title(state, runtime):
        title = self._generate_title(runtime)
        print(f"Generated thread title: {title}")
        
        # ✅ Return state update, auto-persisted by checkpointer
        return {"title": title}
    
    return None
```

## Related Files

- [`packages/harness/kkoclaw/agents/thread_state.py`](../packages/harness/kkoclaw/agents/thread_state.py) — ThreadState definition
- [`packages/harness/kkoclaw/agents/middlewares/title_middleware.py`](../packages/harness/kkoclaw/agents/middlewares/title_middleware.py) — TitleMiddleware implementation
- [`packages/harness/kkoclaw/config/title_config.py`](../packages/harness/kkoclaw/config/title_config.py) — Configuration management
- [`config.yaml`](../../config.example.yaml) — Configuration file
- [`packages/harness/kkoclaw/agents/lead_agent/agent.py`](../packages/harness/kkoclaw/agents/lead_agent/agent.py) — Middleware registration

## References

- [LangGraph Checkpointer Documentation](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [LangGraph State Management](https://langchain-ai.github.io/langgraph/concepts/low_level/#state)
- [LangGraph Middleware](https://langchain-ai.github.io/langgraph/concepts/middleware/)
