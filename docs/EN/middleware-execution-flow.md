# Middleware Execution Flow

## Middleware List

The full middleware chain assembled by `create_kkoclaw_agent` via `RuntimeFeatures` (with all features enabled by default):

| # | Middleware | `before_agent` | `before_model` | `after_model` | `after_agent` | `wrap_tool_call` | Lead Agent | Subagent | Source |
|---|-----------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|------|
| 0 | ThreadDataMiddleware | ✓ | | | | | ✓ | ✓ | `sandbox` |
| 1 | UploadsMiddleware | ✓ | | | | | ✓ | ✗ | `sandbox` |
| 2 | SandboxMiddleware | ✓ | | | ✓ | | ✓ | ✓ | `sandbox` |
| 3 | DanglingToolCallMiddleware | | | ✓ | | | ✓ | ✗ | Always on |
| 4 | GuardrailMiddleware | | | | | ✓ | ✓ | ✓ | *Phase 2 included* |
| 5 | ToolErrorHandlingMiddleware | | | | | ✓ | ✓ | ✓ | Always on |
| 6 | SummarizationMiddleware | | | ✓ | | | ✓ | ✗ | `summarization` |
| 7 | TodoMiddleware | | | ✓ | | | ✓ | ✗ | `plan_mode` param |
| 8 | TitleMiddleware | | | ✓ | | | ✓ | ✗ | `auto_title` |
| 9 | MemoryMiddleware | | | | ✓ | | ✓ | ✗ | `memory` |
| 10 | ViewImageMiddleware | | ✓ | | | | ✓ | ✗ | `vision` |
| 11 | SubagentLimitMiddleware | | | ✓ | | | ✓ | ✗ | `subagent` |
| 12 | LoopDetectionMiddleware | | | ✓ | | | ✓ | ✗ | Always on |
| 13 | ClarificationMiddleware | | | ✓ | | | ✓ | ✗ | Always last |

Lead agent has **14** middleware layers (`make_lead_agent`), subagent has **4** (ThreadData, Sandbox, Guardrail, ToolErrorHandling). `create_kkoclaw_agent` Phase 1 implements **13** (Guardrail only supports custom instances, no built-in default).

## Execution Flow

LangChain `create_agent` rules:
- **`before_*` executes in forward order** (list position 0 → N)
- **`after_*` executes in reverse order** (list position N → 0)

```mermaid
graph TB
    START(["invoke"]) --> TD

    subgraph BA ["<b>before_agent</b> forward 0→N"]
        direction TB
        TD["[0] ThreadData<br/>Create thread directory"] --> UL["[1] Uploads<br/>Scan uploaded files"] --> SB["[2] Sandbox<br/>Acquire sandbox"]
    end

    subgraph BM ["<b>before_model</b> forward 0→N"]
        direction TB
        VI["[10] ViewImage<br/>Inject image base64"]
    end

    SB --> VI
    VI --> M["<b>MODEL</b>"]

    subgraph AM ["<b>after_model</b> reverse N→0"]
        direction TB
        CL["[13] Clarification<br/>Intercept ask_clarification"] --> LD["[12] LoopDetection<br/>Detect loops"] --> SL["[11] SubagentLimit<br/>Truncate excess tasks"] --> TI["[8] Title<br/>Generate title"] --> SM["[6] Summarization<br/>Context compression"] --> DTC["[3] DanglingToolCall<br/>Fill missing ToolMessage"]
    end

    M --> CL

    subgraph AA ["<b>after_agent</b> reverse N→0"]
        direction TB
        SBR["[2] Sandbox<br/>Release sandbox"] --> MEM["[9] Memory<br/>Enqueue memory"]
    end

    DTC --> SBR
    MEM --> END(["response"])

    classDef beforeNode fill:#a0a8b5,stroke:#636b7a,color:#2d3239
    classDef modelNode fill:#b5a8a0,stroke:#7a6b63,color:#2d3239
    classDef afterModelNode fill:#b5a0a8,stroke:#7a636b,color:#2d3239
    classDef afterAgentNode fill:#a0b5a8,stroke:#637a6b,color:#2d3239
    classDef terminalNode fill:#a8b5a0,stroke:#6b7a63,color:#2d3239

    class TD,UL,SB,VI beforeNode
    class M modelNode
    class CL,LD,SL,TI,SM,DTC afterModelNode
    class SBR,MEM afterAgentNode
    class START,END terminalNode
```

## Sequence Diagram

```mermaid
sequenceDiagram
    participant U as User
    participant TD as ThreadDataMiddleware
    participant UL as UploadsMiddleware
    participant SB as SandboxMiddleware
    participant VI as ViewImageMiddleware
    participant M as MODEL
    participant CL as ClarificationMiddleware
    participant SL as SubagentLimitMiddleware
    participant TI as TitleMiddleware
    participant SM as SummarizationMiddleware
    participant DTC as DanglingToolCallMiddleware
    participant MEM as MemoryMiddleware

    U ->> TD: invoke
    activate TD
    Note right of TD: before_agent create directory

    TD ->> UL: before_agent
    activate UL
    Note right of UL: before_agent scan uploaded files

    UL ->> SB: before_agent
    activate SB
    Note right of SB: before_agent acquire sandbox

    SB ->> VI: before_model
    activate VI
    Note right of VI: before_model inject image base64

    VI ->> M: messages + tools
    activate M
    M -->> CL: AI response
    deactivate M

    activate CL
    Note right of CL: after_model intercept ask_clarification
    CL -->> SL: after_model
    deactivate CL

    activate SL
    Note right of SL: after_model truncate excess tasks
    SL -->> TI: after_model
    deactivate SL

    activate TI
    Note right of TI: after_model generate title
    TI -->> SM: after_model
    deactivate TI

    activate SM
    Note right of SM: after_model context compression
    SM -->> DTC: after_model
    deactivate SM

    activate DTC
    Note right of DTC: after_model fill missing ToolMessage
    DTC -->> VI: done
    deactivate DTC

    VI -->> SB: done
    deactivate VI

    Note right of SB: after_agent release sandbox
    SB -->> UL: done
    deactivate SB

    UL -->> TD: done
    deactivate UL

    Note right of MEM: after_agent enqueue memory

    TD -->> U: response
    deactivate TD
```

## Onion Model

List position determines the layer in the onion — position 0 is the outermost layer, position N is the innermost:

```
Enter before_*:   [0] → [1] → [2] → ... → [10] → MODEL
Exit after_*:     MODEL → [13] → [11] → ... → [6] → [3] → [2] → [0]
                          ↑ Innermost executes first
```

> [!important] Core Rule
> The middleware at the end of the list has its `after_model` execute **first**.
> ClarificationMiddleware is at the end of the list, so it intercepts model output first.

## Comparison: True Onion vs OClaw's Reality

### True Onion (e.g., Koa/Express)

Each middleware handles both before and after, forming symmetric nesting:

```mermaid
sequenceDiagram
    participant U as User
    participant A as AuthMiddleware
    participant L as LogMiddleware
    participant R as RateLimitMiddleware
    participant H as Handler

    U ->> A: request
    activate A
    Note right of A: before: validate token

    A ->> L: next()
    activate L
    Note right of L: before: log request time

    L ->> R: next()
    activate R
    Note right of R: before: check rate

    R ->> H: next()
    activate H
    H -->> R: result
    deactivate H

    Note right of R: after: update counter
    R -->> L: result
    deactivate R

    Note right of L: after: log duration
    L -->> A: result
    deactivate L

    Note right of A: after: cleanup context
    A -->> U: response
    deactivate A
```

> [!tip] Onion Characteristics
> Each middleware has symmetric before/after operations, `activate` spans the entire inner execution, forming perfect nesting.

### OClaw's Reality

It's not an onion, it's a pipeline. Most middleware only uses one hook, there is no symmetric nesting. In multi-turn conversations, before_model / after_model execute in a loop:

```mermaid
sequenceDiagram
    participant U as User
    participant TD as ThreadData
    participant UL as Uploads
    participant SB as Sandbox
    participant VI as ViewImage
    participant M as MODEL
    participant CL as Clarification
    participant SL as SubagentLimit
    participant TI as Title
    participant SM as Summarization
    participant MEM as Memory

    U ->> TD: invoke
    Note right of TD: before_agent create directory
    TD ->> UL: .
    Note right of UL: before_agent scan files
    UL ->> SB: .
    Note right of SB: before_agent acquire sandbox

    loop Each turn (tool call loop)
        SB ->> VI: .
        Note right of VI: before_model inject images
        VI ->> M: messages + tools
        M -->> CL: AI response
        Note right of CL: after_model intercept ask_clarification
        CL -->> SL: .
        Note right of SL: after_model truncate excess tasks
        SL -->> TI: .
        Note right of TI: after_model generate title
        TI -->> SM: .
        Note right of SM: after_model context compression
    end

    Note right of SB: after_agent release sandbox
    SB -->> MEM: .
    Note right of MEM: after_agent enqueue memory
    MEM -->> U: response
```

> [!warning] Not an Onion
> Out of 14 middleware, only SandboxMiddleware has before/after symmetry (acquire/release). The rest are unidirectional: they either only do things in `before_*` or only in `after_*`. `before_agent` / `after_agent` run only once, `before_model` / `after_model` run on every loop iteration.

There are only 2 hard dependencies:

1. **ThreadData before Sandbox** — sandbox needs the thread directory
2. **Clarification at the end of the list** — `after_model` executes first in reverse order, first to intercept `ask_clarification`

### Conclusion

| | True Onion | OClaw Actual |
|---|---|---|
| Each middleware | before + after symmetric | Mostly uses only one hook |
| Activation bars | Nested (outer long, inner short) | Not nested (serial) |
| Meaning of reverse order | Cleanup paired with initialization | Only affects after_model execution priority |
| Typical example | Auth: validate token / cleanup context | ThreadData: only create directory, no cleanup |

## Key Design Points

### Why is ClarificationMiddleware at the End of the List?

Last position = `after_model` executes first. It needs to be the **first** to see model output and check for `ask_clarification` tool calls. If found, it immediately interrupts (`Command(goto=END)`), and subsequent middleware `after_model` calls are not executed.

### SandboxMiddleware's Symmetry

`before_agent` (3rd in forward order) acquires the sandbox, `after_agent` (1st in reverse order) releases the sandbox. Outer entry → outer exit, natural onion symmetry.

### Most Middleware Uses Only One Hook

Out of 14 middleware, only SandboxMiddleware uses both `before_agent` + `after_agent` (acquire/release). All others execute in only one phase. The onion model's reverse order characteristic mainly affects the execution order of the `after_model` phase.
