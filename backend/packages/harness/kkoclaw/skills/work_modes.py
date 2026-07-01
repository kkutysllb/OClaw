"""Work mode skill-set resolution and locked-skill enforcement.

Work modes (task / coding) are first-class presets that control which skills
are available to the Lead Agent. This module provides the pure functions that
turn an :class:`~kkoclaw.config.extensions_config.ExtensionsConfig` plus a
``work_mode_id`` into a concrete list of effective skill ids, and enforce that
locked core skills cannot be disabled or removed.

**Frontmatter-based binding** (the core architecture): each skill declares
its mode membership via the ``work_modes`` field in its SKILL.md frontmatter
(e.g. ``work_modes: [task, coding]`` or ``work_modes: [core]``). A skill is
active in a work mode if that mode's id appears in its ``work_modes`` list,
or if ``"core"`` appears (shared across all modes). This is surfaced via
:func:`load_skills_by_work_modes`, which scans the disk once and caches the
result. User overrides (``mode_skill_overrides``) and legacy
``default_skill_ids`` are applied on top of this frontmatter baseline.

These helpers are deliberately free of I/O and side effects (except for the
disk-scan cache) so they can be unit-tested in isolation (see
``backend/tests/test_work_modes.py``) and reused by both the gateway HTTP
layer and the agent runtime.
"""

from __future__ import annotations

from functools import lru_cache

from kkoclaw.config.extensions_config import (
    DEFAULT_LOCKED_SKILL_IDS,
    DEFAULT_WORK_MODE_ID,
    ExtensionsConfig,
    ModeSkillOverridesConfig,
)

__all__ = [
    "DEFAULT_LOCKED_SKILL_IDS",
    "DEFAULT_WORK_MODE_ID",
    "resolve_work_mode_id",
    "resolve_effective_skill_ids",
    "compute_effective_skills",
    "load_skills_by_work_modes",
    "load_builtin_skills_by_scope",
    "invalidate_builtin_skills_cache",
    "assert_skill_can_be_disabled",
    "assert_skill_can_be_removed_from_mode",
    "add_skill_to_mode",
    "remove_skill_from_mode",
]


def resolve_work_mode_id(
    work_mode_id: str | None,
    *,
    config: ExtensionsConfig | None = None,
) -> str:
    """Normalize a caller-supplied work mode id, falling back to the default.

    Empty/None/unknown ids all collapse to :data:`DEFAULT_WORK_MODE_ID` so
    callers downstream never have to handle "missing mode" defensively.

    Unknown-but-non-empty ids fall back to the default rather than raising —
    this keeps the system forward-compatible if a future config ships new modes
    the current code doesn't know about, and avoids crashing a turn over a typo.
    Callers that need strict validation (e.g. admin APIs) should validate
    against ``config.work_modes.modes`` themselves.

    .. important::
       Custom (per-user) work modes such as ``stock-quant`` are NOT present in
       the global builtin ``ExtensionsConfig().work_modes.modes`` (which only
       contains ``task`` and ``coding``). Callers that have already resolved a
       per-user config — e.g. via
       :func:`kkoclaw.config.user_work_modes_config.resolve_user_work_modes_sync`
       — MUST pass it via ``config=`` so the custom mode id is recognised
       instead of being silently rewritten to ``task``. Without this argument,
       every custom mode behaves exactly like 日常办公, pulling in all
       task-bound skills (bug: "model in stock-quant mode still lists
       daily-office skills").

    Args:
        work_mode_id: The raw work mode id from the runtime context, or None.
        config: Optional per-user extensions config whose ``work_modes.modes``
            is consulted for mode recognition. When omitted, the global
            builtin config is used (backward-compatible behaviour for callers
            that only deal with task / coding).

    Returns:
        A work mode id. For known modes this is the id itself; for empty/None/
        unknown inputs this is :data:`DEFAULT_WORK_MODE_ID`.
    """
    if not work_mode_id or not isinstance(work_mode_id, str):
        return DEFAULT_WORK_MODE_ID
    work_mode_id = work_mode_id.strip()
    if not work_mode_id:
        return DEFAULT_WORK_MODE_ID
    # Check against the supplied config's modes first (per-user custom modes
    # live here); fall back to the global builtin config for backward compat.
    # We import lazily to avoid a circular dependency at module load time.
    from kkoclaw.config.extensions_config import ExtensionsConfig

    modes = (
        config.work_modes.modes
        if config is not None
        else ExtensionsConfig().work_modes.modes
    )
    if work_mode_id not in modes:
        return DEFAULT_WORK_MODE_ID
    return work_mode_id


@lru_cache(maxsize=1)
def _scan_skills_by_work_modes() -> frozenset[tuple[str, tuple[str, ...]]]:
    """Scan disk once and return an immutable ``{(name, work_modes)}`` snapshot.

    Wrapped by :func:`load_skills_by_work_modes` which converts to the dict
    view callers expect. The ``lru_cache`` ensures we only walk the skill tree
    once per process unless explicitly invalidated.
    """
    from kkoclaw.config import get_app_config
    from kkoclaw.skills.storage import get_or_new_skill_storage

    storage = get_or_new_skill_storage(app_config=get_app_config())
    skills = storage.load_skills(enabled_only=False)
    return frozenset((skill.name, skill.work_modes) for skill in skills)


def load_skills_by_work_modes() -> dict[str, tuple[str, ...]]:
    """Return ``{skill_name: work_modes_tuple}`` for ALL skills (builtin + custom).

    This is the frontmatter-driven binding data source. A skill is active in a
    work mode if its returned tuple contains that mode's id, or if it contains
    ``"core"`` (shared across all modes). The result is cached process-wide;
    call :func:`invalidate_builtin_skills_cache` after any skill file is added,
    removed, or renamed on disk.

    Returns:
        A dict like ``{"bootstrap": ("core",), "deep-research": ("task",),
        "code-review": ("coding",), "my-tool": ("task", "coding")}``.
    """
    frozen = _scan_skills_by_work_modes()
    return {name: modes for name, modes in frozen}


def load_builtin_skills_by_scope() -> dict[str, set[str]]:
    """Backward-compat adapter: derive ``{scope: set(names)}`` from work_modes.

    .. deprecated::
        Use :func:`load_skills_by_work_modes` instead. This function is kept
        only so legacy callers (and tests) that expect the directory-scope map
        keep working during the transition. It derives the scope map from the
        new frontmatter-driven data.
    """
    by_mode = load_skills_by_work_modes()
    scope_map: dict[str, set[str]] = {}
    for name, modes in by_mode.items():
        for scope in modes:
            scope_map.setdefault(scope, set()).add(name)
    return scope_map


def invalidate_builtin_skills_cache() -> None:
    """Clear the disk-scan cache so the next ``load_skills_by_work_modes`` re-reads.

    Call this after any operation that changes the set of skill files on disk
    (e.g. installing a new skill, deleting one, or editing work_modes frontmatter).
    """
    _scan_skills_by_work_modes.cache_clear()


def resolve_effective_skill_ids(
    config: ExtensionsConfig,
    work_mode_id: str | None,
    *,
    skills_by_work_modes: dict[str, tuple[str, ...]] | None = None,
    builtin_skills_by_scope: dict[str, set[str]] | None = None,
) -> tuple[str, ...]:
    """Compute the effective skill ids for a work mode.

    Resolution order (each step only *adds* to the set, except removals):
    1. **Frontmatter binding** (baseline): all skills whose ``work_modes``
       contains the active mode id, plus skills whose ``work_modes`` contains
       ``"core"`` (shared across all modes).
    2. **Legacy default_skill_ids** (backward compat): user-configured skills
       in ``mode.default_skill_ids`` are appended on top.
    3. **Per-mode overrides**: ``added_skill_ids`` are appended;
       ``removed_skill_ids`` are removed — but locked skills survive.
    4. **Locked skills** (:data:`DEFAULT_LOCKED_SKILL_IDS`) are unconditionally
       unioned in so the core bootstrap skills are always present.

    Args:
        config: The extensions config containing work modes and overrides.
        work_mode_id: The caller's work mode id (None → default).
        skills_by_work_modes: Optional pre-computed ``{skill_name: work_modes}``
            map from :func:`load_skills_by_work_modes`. When ``None``, the
            cached disk-scan result is used. Pass it explicitly in tests to
            avoid disk dependencies.
        builtin_skills_by_scope: Deprecated alias kept for backward compat —
            legacy callers pass ``{scope: set(names)}`` which is internally
            converted to the frontmatter-based view.

    Returns:
        A de-duplicated, sorted tuple of effective skill ids for the mode.
    """
    # NOTE: pass ``config`` so per-user custom modes (e.g. ``stock-quant``)
    # are recognised. Without it, resolve_work_mode_id would silently rewrite
    # any custom mode to the global default (``task``), causing every
    # task-bound skill to leak into the custom mode.
    resolved_mode_id = resolve_work_mode_id(work_mode_id, config=config)

    # Unknown mode → fall back to the default mode's effective set.
    modes = config.work_modes.modes
    if resolved_mode_id not in modes:
        resolved_mode_id = config.work_modes.default_mode_id

    # Resolve the frontmatter-driven binding map. Support both the new
    # ``skills_by_work_modes`` param and the legacy ``builtin_skills_by_scope``
    # param so existing callers keep working during the transition.
    if skills_by_work_modes is not None:
        by_wm = skills_by_work_modes
    elif builtin_skills_by_scope is not None:
        # Legacy adapter: invert {scope: {names}} → {name: (scopes...)}.
        by_wm: dict[str, tuple[str, ...]] = {}
        for scope, names in builtin_skills_by_scope.items():
            for n in names:
                prev = set(by_wm.get(n, ()))
                prev.add(scope)
                by_wm[n] = tuple(sorted(prev))
    else:
        by_wm = load_skills_by_work_modes()

    # 1. Frontmatter binding baseline: skills that declare this mode OR "core".
    effective: set[str] = {
        name
        for name, wms in by_wm.items()
        if resolved_mode_id in wms or "core" in wms
    }

    # 2. Legacy default_skill_ids (backward compat — user explicitly configured these).
    mode_cfg = modes.get(resolved_mode_id)
    if mode_cfg:
        effective |= set(mode_cfg.default_skill_ids)

    # 3. Per-mode overrides.
    override = config.mode_skill_overrides.get(resolved_mode_id)
    if override is not None:
        effective.update(override.added_skill_ids)
        # Removals are honored only for non-locked skills.
        locked = set(config.locked_skill_ids)
        effective = {s for s in effective if s not in override.removed_skill_ids or s in locked}

    # 4. Locked core skills are always present — this is the contract that
    # protects the agent's self-bootstrap / skill-discovery / skill-creation
    # loop. Config cannot override this.
    effective.update(DEFAULT_LOCKED_SKILL_IDS)

    return tuple(sorted(effective))


def compute_effective_skills(
    agent_skills: list[str] | None,
    work_mode_id: str | None,
    extensions_config: ExtensionsConfig,
    *,
    skills_by_work_modes: dict[str, tuple[str, ...]] | None = None,
    builtin_skills_by_scope: dict[str, set[str]] | None = None,
) -> set[str] | None:
    """Compute the final effective skill set for the lead agent's prompt.

    This is the runtime bridge between two independent skill-selection
    dimensions:

    - ``agent_skills`` — the per-agent whitelist from ``AgentConfig.skills``,
      or ``None`` to inherit all available skills.
    - ``work_mode_id`` — the active work mode preset (task / coding), or
      ``None`` to opt out of mode-based filtering.

    When ``work_mode_id`` is active, the mode's effective set is computed via
    :func:`resolve_effective_skill_ids` (directory auto-binding + overrides +
    locked). The optional ``builtin_skills_by_scope`` lets the caller pass a
    pre-loaded snapshot to avoid redundant disk scans within a single request.

    Resolution matrix:

    =======================  =====================  ==============================
    ``agent_skills``         ``work_mode_id``       Result
    =======================  =====================  ==============================
    ``None``                 ``None``               ``None`` — no filtering
    ``None``                 ``"task"/"coding"``    Mode's effective set (locked
                                                  skills always included)
    ``["a", "b"]``           ``None``               ``{"a", "b"}`` — agent
                                                  whitelist applied, mode ignored
    ``["a", "b"]``           ``"task"``             ``agent ∩ mode_effective``;
                                                  locked skills from the mode
                                                  union in if they aren't already
    ``[]`` (explicit empty)  any                   ``set()`` — the agent has
                                                  explicitly opted out of every
                                                  skill; this wins over the mode
    =======================  =====================  ==============================

    Args:
        agent_skills: The agent's per-agent skill whitelist (from
            ``AgentConfig.skills``). ``None`` means "inherit everything";
            ``[]`` means "disable all skills".
        work_mode_id: The active work mode id, or ``None`` for opt-out.
        extensions_config: The extensions config containing work-mode
            definitions and overrides.

    Returns:
        The final set of skill ids the agent should see in its prompt, or
        ``None`` to mean "no filtering — show every enabled skill" (used by
        callers that want the legacy behavior).
    """
    # Opt-out from mode filtering — preserve caller semantics, but locked
    # core skills are still always present (they're a global invariant that
    # protects the agent's self-bootstrap loop).
    if work_mode_id is None:
        if agent_skills is None:
            return None
        return set(agent_skills) | set(DEFAULT_LOCKED_SKILL_IDS)

    # Mode is active. Compute the mode's effective set first (it already
    # contains locked skills — see ``resolve_effective_skill_ids``).
    mode_effective = resolve_effective_skill_ids(
        extensions_config,
        work_mode_id,
        skills_by_work_modes=skills_by_work_modes,
        builtin_skills_by_scope=builtin_skills_by_scope,
    )

    # Agent has no whitelist: adopt the mode's effective set wholesale.
    if agent_skills is None:
        return set(mode_effective)

    # Explicit empty agent whitelist is a hard opt-out for non-locked skills,
    # but locked core skills are an invariant and remain present.
    if len(agent_skills) == 0:
        return set(DEFAULT_LOCKED_SKILL_IDS)

    # Both present: intersect the agent's whitelist with the mode's effective
    # set. Locked core skills are unconditionally unioned in — they're a
    # global invariant that survives any per-agent or per-mode restriction.
    agent_set = set(agent_skills)
    intersected = agent_set & set(mode_effective)
    intersected.update(DEFAULT_LOCKED_SKILL_IDS)
    return intersected


def assert_skill_can_be_disabled(skill_name: str) -> None:
    """Raise ``ValueError`` if *skill_name* is locked and cannot be disabled.

    Used by the skill-enable/disable HTTP endpoints to reject attempts to turn
    off core bootstrap skills. Non-locked skills pass through silently.

    Args:
        skill_name: The skill id being toggled.

    Raises:
        ValueError: If *skill_name* is in :data:`DEFAULT_LOCKED_SKILL_IDS`.
    """
    if skill_name in DEFAULT_LOCKED_SKILL_IDS:
        raise ValueError(
            f"Skill '{skill_name}' is locked and cannot be disabled. "
            "Locked skills protect the agent's core self-bootstrap, skill-discovery, "
            "and skill-creation capabilities."
        )


def assert_skill_can_be_removed_from_mode(skill_name: str, work_mode_id: str | None = None) -> None:
    """Raise ``ValueError`` if *skill_name* is locked and cannot be removed from a mode.

    Used by the work-mode skill management endpoints. The *work_mode_id* is
    included only for a clearer error message — the lock is global, not
    per-mode.

    Args:
        skill_name: The skill id being removed.
        work_mode_id: The mode the caller is trying to remove it from (optional,
            used purely for the error message).

    Raises:
        ValueError: If *skill_name* is locked — the message notes it is
            required by all work modes.
    """
    if skill_name in DEFAULT_LOCKED_SKILL_IDS:
        mode_clause = f" from work mode '{work_mode_id}'" if work_mode_id else ""
        raise ValueError(
            f"Skill '{skill_name}' is required by all work modes and cannot be removed{mode_clause}. "
            "Locked skills guarantee a consistent baseline capability across every mode."
        )


def add_skill_to_mode(
    config: ExtensionsConfig,
    mode_id: str,
    skill_name: str,
) -> ExtensionsConfig:
    """Add a skill to a work mode via ``mode_skill_overrides``.

    Returns a **new** ``ExtensionsConfig`` copy; the original is not mutated.
    Adding a skill that was previously in ``removed_skill_ids`` clears the
    removal (net effect: the skill becomes active in the mode again).

    Args:
        config: The current extensions config.
        mode_id: The target work mode id (resolved via ``resolve_work_mode_id``).
        skill_name: The skill id to add.

    Returns:
        A new config with the override applied.
    """
    resolved = resolve_work_mode_id(mode_id, config=config)
    overrides = dict(config.mode_skill_overrides)
    current = overrides.get(resolved, ModeSkillOverridesConfig())
    added = list(current.added_skill_ids)
    if skill_name not in added:
        added.append(skill_name)
    removed = [s for s in current.removed_skill_ids if s != skill_name]
    overrides[resolved] = ModeSkillOverridesConfig(
        added_skill_ids=tuple(added),
        removed_skill_ids=tuple(removed),
    )
    return config.model_copy(update={"mode_skill_overrides": overrides})


def remove_skill_from_mode(
    config: ExtensionsConfig,
    mode_id: str,
    skill_name: str,
) -> ExtensionsConfig:
    """Remove a skill from a work mode via ``mode_skill_overrides``.

    Returns a **new** ``ExtensionsConfig`` copy; the original is not mutated.
    Removing a skill that was previously in ``added_skill_ids`` clears the
    addition (net effect: the skill is no longer active in the mode).

    Locked skills are rejected — see
    :func:`assert_skill_can_be_removed_from_mode`.

    Args:
        config: The current extensions config.
        mode_id: The target work mode id (resolved via ``resolve_work_mode_id``).
        skill_name: The skill id to remove.

    Returns:
        A new config with the override applied.

    Raises:
        ValueError: If *skill_name* is a locked core skill.
    """
    assert_skill_can_be_removed_from_mode(skill_name, mode_id)
    resolved = resolve_work_mode_id(mode_id, config=config)
    overrides = dict(config.mode_skill_overrides)
    current = overrides.get(resolved, ModeSkillOverridesConfig())
    removed = list(current.removed_skill_ids)
    if skill_name not in removed:
        removed.append(skill_name)
    added = [s for s in current.added_skill_ids if s != skill_name]
    overrides[resolved] = ModeSkillOverridesConfig(
        added_skill_ids=tuple(added),
        removed_skill_ids=tuple(removed),
    )
    return config.model_copy(update={"mode_skill_overrides": overrides})
