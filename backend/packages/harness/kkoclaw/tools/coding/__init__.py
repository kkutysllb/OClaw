"""Coding-specific tool set for the Coding Agent.

This package provides enhanced file manipulation, git operations, test
execution, and worktree management tools that go beyond the standard
sandbox tool set (read_file / write_file / str_replace / grep / glob).

All tools follow the same ``runtime: Runtime`` first-parameter convention
as the sandbox tools and reuse the sandbox infrastructure underneath.
"""

from kkoclaw.tools.coding.file_edit import (
    apply_diff_tool,
    insert_at_line_tool,
    multi_edit_tool,
)
from kkoclaw.tools.coding.file_read import (
    find_files_tool,
    read_file_lines_tool,
    search_code_tool,
)
from kkoclaw.tools.coding.git_tools import (
    git_branch_tool,
    git_checkout_tool,
    git_commit_tool,
    git_diff_tool,
    git_log_tool,
    git_push_tool,
    git_show_tool,
    git_stash_tool,
    git_status_tool,
)
from kkoclaw.tools.coding.pr_tools import (
    create_pr_tool,
    review_code_tool,
)
from kkoclaw.tools.coding.refactor_tools import (
    extract_function_tool,
    rename_symbol_tool,
)
from kkoclaw.tools.coding.stage_tools import (
    suggest_delivery_stage_tool,
)
from kkoclaw.tools.coding.symbol_tools import (
    find_symbols_tool,
    read_symbol_tool,
)
from kkoclaw.tools.coding.diagnostic_tools import (
    get_diagnostics_tool,
)
from kkoclaw.tools.coding.impact_analysis import (
    analyze_impact_tool,
)
from kkoclaw.tools.coding.lsp_tools import (
    find_references_tool,
    go_to_definition_tool,
)
from kkoclaw.tools.coding.session_shell import (
    session_shell_tool,
)
from kkoclaw.tools.coding.semantic_search import (
    search_semantic_tool,
)
from kkoclaw.tools.coding.skill_declaration import (
    declare_skill_tool,
    list_coding_skills_tool,
)
from kkoclaw.tools.coding.test_tools import (
    run_linter_tool,
    run_tests_tool,
)
from kkoclaw.tools.coding.undo_tools import (
    list_edit_snapshots_tool,
    undo_last_edit_tool,
)
from kkoclaw.tools.coding.worktree import (
    create_worktree_tool,
    list_worktrees_tool,
    remove_worktree_tool,
)


def get_coding_tools() -> list:
    """Return the full list of coding-specific tools.

    Called by :func:`kkoclaw.agents.lead_agent.coding_mode.get_coding_mode_tools`
    to assemble the extended tool set for the Lead Agent's coding branch.
    """
    return [
        # File reading
        read_file_lines_tool,
        search_code_tool,
        find_files_tool,
        # Symbol-aware navigation + cross-file LSP-like tools
        find_symbols_tool,
        read_symbol_tool,
        go_to_definition_tool,
        find_references_tool,
        # File editing
        apply_diff_tool,
        insert_at_line_tool,
        multi_edit_tool,
        # Semantic refactoring
        rename_symbol_tool,
        extract_function_tool,
        # Edit rollback (transactional undo)
        undo_last_edit_tool,
        list_edit_snapshots_tool,
        # Git
        git_status_tool,
        git_diff_tool,
        git_log_tool,
        git_commit_tool,
        git_branch_tool,
        git_checkout_tool,
        git_push_tool,
        git_stash_tool,
        git_show_tool,
        # Test / lint / diagnostics
        run_tests_tool,
        run_linter_tool,
        get_diagnostics_tool,
        # Persistent shell session
        session_shell_tool,
        # Worktree
        create_worktree_tool,
        remove_worktree_tool,
        list_worktrees_tool,
        # PR & Code Review
        create_pr_tool,
        review_code_tool,
        # Delivery stage tracking
        suggest_delivery_stage_tool,
        # Semantic search (P2)
        search_semantic_tool,
        # Skill management (P2)
        list_coding_skills_tool,
        declare_skill_tool,
        # Impact analysis (P2)
        analyze_impact_tool,
    ]


__all__ = ["get_coding_tools"]
