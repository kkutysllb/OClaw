# Memory System Improvements

This document records memory injection behavior and roadmap status.

## Status (as of 2026-05-24)

Implemented on the `main` branch:

- Precise token counting using `tiktoken` in `format_memory_for_injection`.
- Facts are injected into the prompt memory context.
- Facts are ordered by confidence (descending).
- Injection respects the `max_injection_tokens` budget.
- TF-IDF similarity-based fact retrieval.
- `current_context` input for context-aware scoring.
- Configurable similarity/confidence weights (`similarity_weight`, `confidence_weight`).
- Runtime middleware injects context-ranked facts before each agent execution.
- Retrieval has introduced facts-side document set signature caching, reusing tokenization, IDF, and facts vector preprocessing results.
- `tokenize_text()` has been enhanced with Chinese 2/3-gram, technical term delimiter splitting, camelCase splitting, and path segment tokenization.
- Retrieval has added in-process runtime statistics: queryable cache hit/miss, fallback count, last ranking summary, and injection summary.
- Gateway exposes a read-only debug endpoint `/api/memory/retrieval/stats`.
- `MemoryMiddleware` outputs debug-level retrieval logs containing only cache, fallback, injection budget, and top score numeric summaries — no raw context or fact content.
- Memory facts now support scope-aware isolation: normal conversations default to user-level behavior; coding agent can derive `coding_project` scope via `memory_scope` or `project_id`/`project_root`, injecting only `global`, current project, and unmigrated legacy facts.

## Current Behavior

Current capability:

```python
def format_memory_for_injection(
    memory_data: dict[str, Any],
    max_tokens: int = 2000,
    ranked_facts: list[dict[str, Any]] | None = None,
) -> str:
```

Current injection format:

- `User Context` section from `user.*.summary`
- `History` section from `history.*.summary`
- `Facts` section from `facts[]`
  - When retrieval is off: sorted by confidence
  - When retrieval is on: sorted by weighted score of `current_context` TF-IDF similarity and `confidence`
  - If an active scope exists for the current run (e.g., coding agent's `coding_project`), facts are filtered before ranking and injection
  - Facts are still appended up to the token budget

Token counting:

- Uses `tiktoken` (`cl100k_base`) when available
- Falls back to `len(text) // 4` if tokenizer import fails

## Current Limitations

- Retrieval targets only `facts[]`
- `user.*` and `history.*` are still injected as summary background without participating in retrieval ranking
- `user.*` and `history.*` are still user-level summaries, not yet split by `global` / `coding_project` / `conversation`, so thorough cross-project contamination fixes require subsequent schema upgrades
- First-version cache is in-process `lru_cache` without cross-process sharing
- Tokenizer remains a lightweight rule-based approach without custom technical vocabulary or external tokenizer dependencies
- First version does not introduce BM25 or embedding-based retrieval
- Current statistics are in-process data and reset upon process restart

## Current Scoring Strategy

```text
final_score = (similarity * 0.6) + (confidence * 0.4)
```

Current integration:

1. Extract recent conversation context from filtered user/final assistant turns.
2. Compute TF-IDF cosine similarity between each fact and current context.
3. Rank by weighted score and inject within token budget.
4. If context is unavailable or retrieval encounters an error, fall back to confidence-only ranking.

## Tuning Recommendations

- First observe `last_injected_facts_count`, `last_query_tokens`, `cache_hits/cache_misses`, and `fallback_confidence_only_calls` in `/api/memory/retrieval/stats` before deciding to adjust parameters.
- If `last_injected_facts_count` consistently approaches the limit and high-scoring facts are frequently truncated, consider raising `memory.max_injection_tokens` from `2000` to `2500-3000`.
- If retrieval hits are normal but conversations still frequently trigger summarization, first check whether `summarization.trigger` fires too early before deciding to relax token thresholds.
- At this stage, automatic linked parameter tuning is not recommended; first make manual observations and small-step adjustments based on statistics.

## Verification

Current regression test coverage includes:

- Memory injection output contains facts
- Confidence ranking
- Pre-ranked facts rendering
- Token budget-limited fact inclusion
- Retrieval ranking and no-context fallback
- Retrieval statistics, middleware debug logging, and stats route
- Retrieval integration in lead-agent prompt
- MemoryMiddleware runtime injection

Test files:

- `backend/tests/test_memory_prompt_injection.py`
- `backend/tests/test_memory_retrieval.py`
- `backend/tests/test_lead_agent_prompt.py`
- `backend/tests/test_memory_middleware.py`
- `backend/tests/test_memory_router.py`
