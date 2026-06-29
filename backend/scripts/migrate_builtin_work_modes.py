#!/usr/bin/env python3
"""One-shot migration: inject ``work_modes`` frontmatter into builtin SKILL.md files.

Scans ``skills/builtin/{core,task,coding}/.../SKILL.md`` and injects the
appropriate ``work_modes`` field based on the skill's physical sub-directory.
This makes the frontmatter the single source of truth for work-mode binding,
replacing the old directory-inference runtime fallback.

Idempotent: re-running the script is safe — files that already declare
``work_modes`` are skipped.

Usage::

    python -m scripts.migrate_builtin_work_modes          # from backend/
    python scripts/migrate_builtin_work_modes.py           # direct

Or specify a custom skills root::

    python scripts/migrate_builtin_work_modes.py --skills-root /path/to/skills
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap import path so the script works both as a module and standalone.
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_BACKEND_ROOT = _THIS_DIR.parent
_HARNESS_PKG = _BACKEND_ROOT / "packages" / "harness"
if str(_HARNESS_PKG) not in sys.path:
    sys.path.insert(0, str(_HARNESS_PKG))

from kkoclaw.skills.frontmatter import (  # noqa: E402
    has_work_modes_frontmatter,
    inject_work_modes_frontmatter,
)


def _infer_work_mode_from_path(skill_md: Path, builtin_root: Path) -> str | None:
    """Return the work-mode id derived from the skill's sub-directory.

    ``builtin/core/...`` → ``core``
    ``builtin/task/...`` → ``task``
    ``builtin/coding/...`` → ``coding``
    """
    try:
        relative = skill_md.parent.relative_to(builtin_root)
    except ValueError:
        return None
    parts = relative.parts
    if not parts:
        return None
    first = parts[0]
    if first in {"core", "task", "coding"}:
        return first
    return None


def migrate_builtin_skills(skills_root: Path, *, dry_run: bool = False) -> dict[str, int]:
    """Inject ``work_modes`` into all builtin SKILL.md files that lack it.

    Returns a summary dict with keys ``updated``, ``skipped``, ``errors``.
    """
    builtin_root = skills_root / "builtin"
    if not builtin_root.exists():
        print(f"[!] builtin directory not found: {builtin_root}")
        return {"updated": 0, "skipped": 0, "errors": 0}

    summary = {"updated": 0, "skipped": 0, "errors": 0}

    for skill_md in sorted(builtin_root.rglob("SKILL.md")):
        mode = _infer_work_mode_from_path(skill_md, builtin_root)
        if mode is None:
            print(f"  [?] Cannot infer mode for {skill_md.relative_to(skills_root)}")
            summary["errors"] += 1
            continue

        try:
            content = skill_md.read_text(encoding="utf-8")
        except Exception as e:
            print(f"  [!] Error reading {skill_md}: {e}")
            summary["errors"] += 1
            continue

        if has_work_modes_frontmatter(content):
            print(f"  [=] Skip (already has work_modes): {skill_md.relative_to(skills_root)}")
            summary["skipped"] += 1
            continue

        new_content = inject_work_modes_frontmatter(content, [mode])
        if new_content == content:
            print(f"  [!] No frontmatter block found in {skill_md.relative_to(skills_root)}")
            summary["errors"] += 1
            continue

        rel = skill_md.relative_to(skills_root)
        if dry_run:
            print(f"  [DRY] Would inject work_modes: [{mode}] into {rel}")
        else:
            skill_md.write_text(new_content, encoding="utf-8")
            print(f"  [+] Injected work_modes: [{mode}] into {rel}")
        summary["updated"] += 1

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate builtin SKILL.md frontmatter to include work_modes.")
    parser.add_argument(
        "--skills-root",
        type=Path,
        default=_BACKEND_ROOT.parent / "skills",
        help="Path to the skills root directory (default: <repo>/skills)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without writing files.",
    )
    args = parser.parse_args()

    skills_root = args.skills_root.resolve()
    print(f"Skills root: {skills_root}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'WRITE'}")
    print()

    summary = migrate_builtin_skills(skills_root, dry_run=args.dry_run)

    print()
    print(f"Done. Updated: {summary['updated']}, Skipped: {summary['skipped']}, Errors: {summary['errors']}")
    return 0 if summary["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
