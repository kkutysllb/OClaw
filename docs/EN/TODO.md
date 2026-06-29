# TODO List

## Completed Features

- [x] Start sandbox only after the first filesystem or bash tool is called
- [x] Add clarification process for the entire workflow
- [x] Implement context summarization mechanism to avoid context explosion
- [x] Integrate MCP (Model Context Protocol) to extend tools
- [x] Add file upload support with automatic document conversion
- [x] Implement automatic thread title generation
- [x] Add plan mode and TodoList middleware
- [x] Add vision model support and ViewImageMiddleware
- [x] Skill system and SKILL.md format
- [x] Replace `time.sleep(5)` with `asyncio.sleep()` in `packages/harness/kkoclaw/tools/builtins/task_tool.py` (sub-agent polling)
- [x] Implement TF-IDF similarity retrieval based on `current_context`
- [x] Implement weighted ranking of memory facts by similarity + confidence
- [x] Introduce facts-side document set signature cache for memory retrieval
- [x] Enhance `tokenize_text()` for Chinese/technical term segmentation
- [x] Add queryable statistics and debug logging for memory retrieval
- [x] Add scope-aware isolation for memory facts — coding agent only injects `global` + current `coding_project` facts, normal conversations maintain user-level behavior
- [x] Support bridging `.kkoclaw/agents/<name>` custom agents as subagents schedulable by `task`
- [x] Support configuring Gateway concurrency for production deployments via `GATEWAY_WORKERS`
- [x] Make subagent recursion_limit formula configurable (`recursion_limit_multiplier` × max_turns + `recursion_limit_base`, default `3*max_turns+20`)
- [x] Full sync of upstream DeerFlow `backend/app/` modules (2025-05-29)
  - **User isolation**: `paths.py` adds `user_agents_dir`/`user_agent_dir` methods; `agents_config.py` adds `resolve_agent_dir()` for per-user agent directory resolution with legacy shared layout fallback
  - **Route modules**: `agents.py` fully supports per-user agent directories + legacy fallback; `threads.py` adds metadata filter validation (`InvalidMetadataFilterError`); `runs.py` uses `wait_for_run_completion` instead of direct `await task`
  - **Upload security**: `uploads.py` adds `_make_file_sandbox_readable` (Docker sandbox file readability) + `claim_unique_filename` for duplicate filename dedup
  - **Security enhancements**: `artifacts.py` adds `_read_skill_archive_member` ZIP bomb protection (16MB limit); `csrf_middleware.py` adds Origin validation to prevent CSRF login attacks
  - **MCP secret masking**: `mcp.py` refactored to `_mask_server_config` + `_merge_preserving_secrets`, preserving raw JSON `$VAR` placeholders
  - **Auth status cache**: `auth.py` setup-status changed to TTL cache + asyncio dedup to avoid multi-tab 429
  - **Message conversion**: `services.py` uses `convert_to_messages` preserving attachments and other fields, adds `inject_authenticated_user_context` + model validation + `resolve_root_run_name`
  - **Startup recovery**: `deps.py` adds `_mark_latest_recovered_threads_error`, auto-recovering orphaned runs and marking thread status on Gateway restart

## Planned Features
- [ ] Workflow truly one-click driving agent, complex progress calculation, more browser screenshot verification — can be iterated in subsequent versions
- [ ] Pool sandbox resources to reduce sandbox container count
- [ ] Add authentication/authorization layer
- [ ] Implement rate limiting
- [ ] Add metrics and monitoring
- [ ] Support more upload document formats
- [ ] Skill marketplace / remote skill installation
- [ ] Optimize async concurrency on agent hot paths in IM channel multi-task scenarios
- [ ] Upgrade `user/history` summaries to scope-aware structure to prevent project-level summaries from continuing to write into global user background
- [ ] Replace `subprocess.run()` with `asyncio.create_subprocess_shell()` in `packages/harness/kkoclaw/sandbox/local/local_sandbox.py`
  - Replace synchronous `requests` in community tools (tavily, jina_ai, firecrawl, infoquest, image_search) with `httpx.AsyncClient`
  - [x] Replace synchronous `model.invoke()` with async `model.ainvoke()` in title_middleware and memory updater
  - Consider wrapping remaining blocking file I/O with `asyncio.to_thread()`
  - For production: use `langgraph up` (multi-worker) instead of `langgraph dev` (single worker)

## Resolved Issues

- [x] Ensure no duplicate files in `state.artifacts`
- [x] Thinking too long but content is empty (answer is in the thinking process)
