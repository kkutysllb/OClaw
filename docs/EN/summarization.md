# Conversation Summarization

OClaw includes automatic conversation summarization to handle long conversations approaching model token limits. When enabled, the system automatically compresses older messages while preserving recent context.

## Overview

The summarization feature uses LangChain's `SummarizationMiddleware` to monitor conversation history and trigger summarization based on configurable thresholds. When activated, it:

1. Monitors message token counts in real-time
2. Triggers summarization when thresholds are reached
3. Keeps recent messages intact while summarizing older conversations
4. Keeps AI/Tool message pairs together, ensuring context continuity
5. Injects summarization results back into the conversation

## Configuration

Summarization is configured under the `summarization` key in `config.yaml`:

```yaml
summarization:
  enabled: true
  model_name: null  # Use default model or specify a lightweight model

  # Trigger conditions (OR logic — any condition triggers summarization)
  trigger:
    - type: tokens
      value: 4000
    # Additional trigger conditions (optional)
    # - type: messages
    #   value: 50
    # - type: fraction
    #   value: 0.8  # 80% of model's max input tokens

  # Context retention strategy
  keep:
    type: messages
    value: 20

  # Token trimming for summarization calls
  trim_tokens_to_summarize: 4000

  # Custom summarization prompt (optional)
  summary_prompt: null

  # Tool names considered as skill file reads
  skill_file_read_tool_names:
    - read_file
    - read
    - view
    - cat
```

### Configuration Options

#### `enabled`
- **Type**: boolean
- **Default**: `false`
- **Description**: Enables or disables automatic summarization

#### `model_name`
- **Type**: string or null
- **Default**: `null` (uses default model)
- **Description**: Model used for generating summaries. It is recommended to use a lightweight, cost-effective model like `gpt-4o-mini` or equivalent.

#### `trigger`
- **Type**: Single `ContextSize` or list of `ContextSize` objects
- **Required**: At least one trigger condition must be specified when enabled
- **Description**: Thresholds that trigger summarization. Uses OR logic — summarization triggers when any threshold is met.

**ContextSize Types:**

1. **Token Trigger**: Triggers when token count reaches the specified value
   ```yaml
   trigger:
     type: tokens
     value: 4000
   ```

2. **Message Trigger**: Triggers when message count reaches the specified value
   ```yaml
   trigger:
     type: messages
     value: 50
   ```

3. **Fraction Trigger**: Triggers when token usage reaches a percentage of the model's max input tokens
   ```yaml
   trigger:
     type: fraction
     value: 0.8  # 80% of max input tokens
   ```

**Multiple Trigger Conditions:**
```yaml
trigger:
  - type: tokens
    value: 4000
  - type: messages
    value: 50
```

#### `keep`
- **Type**: `ContextSize` object
- **Default**: `{type: messages, value: 20}`
- **Description**: Specifies how much recent conversation history to keep after summarization.

**Examples:**
```yaml
# Keep the last 20 messages
keep:
  type: messages
  value: 20

# Keep the last 3000 tokens
keep:
  type: tokens
  value: 3000

# Keep 30% of model's max input tokens
keep:
  type: fraction
  value: 0.3
```

#### `trim_tokens_to_summarize`
- **Type**: integer or null
- **Default**: `4000`
- **Description**: Maximum number of tokens to include when preparing messages for the summarization call. Set to `null` to skip trimming (not recommended for very long conversations).

#### `summary_prompt`
- **Type**: string or null
- **Default**: `null` (uses LangChain default prompt)
- **Description**: Custom prompt template for generating summaries. The prompt should guide the model to extract the most important context.

#### `preserve_recent_skill_count`
- **Type**: integer (≥ 0)
- **Default**: `5`
- **Description**: Number of recently loaded skill files (tool results where tool name is in `skill_file_read_tool_names` and target path is under `skills.container_path`, e.g., `/mnt/skills/...`) to rescue from summarization. Prevents the agent from losing skill instructions after compression. Set to `0` to disable skill rescue completely.

#### `preserve_recent_skill_tokens`
- **Type**: integer (≥ 0)
- **Default**: `25000`
- **Description**: Total token budget reserved for rescued skill reads. Once this budget is exhausted, older skill packages are allowed to be summarized.

#### `preserve_recent_skill_tokens_per_skill`
- **Type**: integer (≥ 0)
- **Default**: `5000`
- **Description**: Per-skill token cap. Any single skill read tool result exceeding this size will not be rescued (goes into the summarizer like normal content).

#### `skill_file_read_tool_names`
- **Type**: list of strings
- **Default**: `["read_file", "read", "view", "cat"]`
- **Description**: Tool names considered as skill file reads during summarization rescue. Tool calls are only eligible for skill rescue when the tool name is in this list and the target path is under `skills.container_path`.

**Default Prompt Behavior:**
LangChain's default prompt instructs the model to:
- Extract the highest quality / most relevant context
- Focus on information critical to the overall goal
- Avoid repeating completed actions
- Return only the extracted context

## How It Works

### Summarization Flow

1. **Monitoring**: Before each model call, the middleware counts tokens in the message history
2. **Trigger Check**: If any configured threshold is met, summarization is triggered
3. **Message Partitioning**: Messages are divided into:
   - Messages to summarize (older messages beyond the `keep` threshold)
   - Messages to keep (recent messages within the `keep` threshold)
4. **Summary Generation**: The model generates a concise summary of older messages
5. **Context Replacement**: Message history is updated:
   - All old messages are removed
   - A summary message is added
   - Recent messages are preserved
6. **AI/Tool Pair Protection**: The system ensures AI messages and their corresponding tool messages stay together
7. **Skill Rescue**: Before summarization, recently loaded skill files are extracted from the summarization set and prepended to the tail of kept messages. Selection follows most-recent-first under three budgets: `preserve_recent_skill_count`, `preserve_recent_skill_tokens`, and `preserve_recent_skill_tokens_per_skill`. The triggering AIMessage and all its paired ToolMessages are moved together to keep tool_call ↔ tool_result pairs intact.

### Token Counting

- Uses character-based approximate token counting
- For Anthropic models: approximately 3.3 characters/token
- For other models: uses LangChain default estimation
- Customizable via custom `token_counter` function

### Message Retention

The middleware intelligently preserves message context:

- **Recent Messages**: Always kept intact according to the `keep` configuration
- **AI/Tool Pairs**: Never split — if the cutoff falls within a tool message, the system adjusts to keep the entire AI + Tool message sequence together
- **Summary Format**: Summary is injected as a HumanMessage with the format:
  ```
  Here is a summary of the conversation so far:
  
  [generated summary text]
  ```

## Best Practices

### Choosing Trigger Thresholds

1. **Token Trigger**: Recommended for most scenarios
   - Set to 60-80% of the model's context window
   - Example: For 8K context, use 4000-6000 tokens

2. **Message Trigger**: For controlling conversation length
   - Suitable for apps with many short messages
   - Example: 50-100 messages, depending on average message length

3. **Fraction Trigger**: Suitable when using multiple models
   - Automatically adapts to each model's capacity
   - Example: 0.8 (80% of model's max input tokens)

### Choosing Keep Strategy (`keep`)

1. **Message-based Keep**: Suitable for most scenarios
   - Preserves natural conversation flow
   - Recommended: 15-25 messages

2. **Token-based Keep**: Use when precise control is needed
   - Suitable for managing exact token budgets
   - Recommended: 2000-4000 tokens

3. **Fraction-based Keep**: Suitable for multi-model setups
   - Automatically scales with model capacity
   - Recommended: 0.2-0.4 (20-40% of max input tokens)

### Model Selection

- **Recommended**: Use lightweight, cost-effective models for summarization
  - Examples: `gpt-4o-mini`, `claude-haiku`, or equivalents
  - Summarization doesn't need the most powerful model
  - Significant cost savings for high-traffic applications

- **Default**: If `model_name` is `null`, the default model is used
  - May be more expensive but ensures consistency
  - Suitable for simple setups

### Optimization Tips

1. **Balanced Triggers**: Combine token and message triggers for robust handling
   ```yaml
   trigger:
     - type: tokens
       value: 4000
     - type: messages
       value: 50
   ```

2. **Conservative Keep**: Keep more messages initially, adjust based on performance
   ```yaml
   keep:
     type: messages
     value: 25  # Start high, reduce as needed
   ```

3. **Strategic Trimming**: Limit tokens sent to the summarization model
   ```yaml
   trim_tokens_to_summarize: 4000  # Prevent expensive summarization calls
   ```

4. **Monitor and Iterate**: Track summarization quality and adjust configuration

## Troubleshooting

### Summarization Quality Issues

**Problem**: Summary loses important context

**Solution**:
1. Increase the `keep` value to retain more messages
2. Lower the trigger threshold for earlier summarization
3. Customize `summary_prompt` to emphasize key information
4. Use a more capable model for summarization

### Performance Issues

**Problem**: Summarization calls take too long

**Solution**:
1. Use a faster model for summarization (e.g., `gpt-4o-mini`)
2. Reduce `trim_tokens_to_summarize` to send less context
3. Raise trigger thresholds to reduce summarization frequency

### Token Limit Errors

**Problem**: Hitting token limits despite summarization

**Solution**:
1. Lower trigger thresholds for earlier summarization
2. Reduce `keep` value to retain fewer messages
3. Check if individual messages are very large
4. Consider using fraction-based triggers

## Implementation Details

### Code Structure

- **Configuration**: `packages/harness/kkoclaw/config/summarization_config.py`
- **Integration**: `packages/harness/kkoclaw/agents/lead_agent/agent.py`
- **Middleware**: Uses `langchain.agents.middleware.SummarizationMiddleware`

### Middleware Order

Summarization runs after thread data and Sandbox initialization, before title and clarification:

1. ThreadDataMiddleware
2. SandboxMiddleware
3. **SummarizationMiddleware** ← Runs here
4. TitleMiddleware
5. ClarificationMiddleware

### State Management

- Summarization is stateless — configuration is loaded once at startup
- Summaries are added as normal messages in the conversation history
- Checkpointer automatically persists post-summarization history

## Configuration Examples

### Minimal Configuration
```yaml
summarization:
  enabled: true
  trigger:
    type: tokens
    value: 4000
  keep:
    type: messages
    value: 20
```

### Production Configuration
```yaml
summarization:
  enabled: true
  model_name: gpt-4o-mini  # Lightweight model for cost savings
  trigger:
    - type: tokens
      value: 6000
    - type: messages
      value: 75
  keep:
    type: messages
    value: 25
  trim_tokens_to_summarize: 5000
```

### Multi-Model Configuration
```yaml
summarization:
  enabled: true
  model_name: gpt-4o-mini
  trigger:
    type: fraction
    value: 0.7  # 70% of model's max input tokens
  keep:
    type: fraction
    value: 0.3  # Keep 30% of max input tokens
  trim_tokens_to_summarize: 4000
```

### Conservative Configuration (High Quality)
```yaml
summarization:
  enabled: true
  model_name: gpt-4  # Use full model for high-quality summaries
  trigger:
    type: tokens
    value: 8000
  keep:
    type: messages
    value: 40  # Keep more context
  trim_tokens_to_summarize: null  # Don't trim
```

## References

- [LangChain Summarization Middleware Documentation](https://docs.langchain.com/oss/python/langchain/middleware/built-in#summarization)
- [LangChain Source Code](https://github.com/langchain-ai/langchain)
