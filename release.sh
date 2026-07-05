#!/usr/bin/env bash
set -euo pipefail

# OClaw release lifecycle manager.
#
# Typical usage:
#   ./release.sh v0.2.1
#   ./release.sh v0.2.1 --push
#
# The script is intentionally conservative:
#   1. verifies the repo and target tag,
#   2. updates version files,
#   3. refreshes lockfiles unless skipped,
#   4. prepends CHANGELOG.md,
#   5. runs release checks unless skipped,
#   6. commits, tags, and optionally pushes.

SCRIPT_NAME="$(basename "$0")"

VERSION=""
TAG=""
REMOTE="origin"
EXPECTED_BRANCH="main"
PUSH=false
YES=false
DRY_RUN=false
SKIP_CHECKS=false
SKIP_LOCK=false
FULL_BUILD=false
NO_COMMIT=false
NO_TAG=false
ALLOW_DIRTY=false
NO_FETCH=false

ROOT_FILES=(
  "frontend/package.json"
  "desktop-electron/package.json"
  "backend/pyproject.toml"
  "backend/packages/harness/pyproject.toml"
)

LOCK_FILES=(
  "frontend/pnpm-lock.yaml"
  "desktop-electron/pnpm-lock.yaml"
  "backend/uv.lock"
)

usage() {
  cat <<'EOF'
Usage:
  ./release.sh <version|vversion> [options]

Examples:
  ./release.sh v0.2.1
  ./release.sh 0.2.1 --push
  ./release.sh v0.2.1 --full-build --push --yes
  ./release.sh v0.2.1 --skip-checks --no-commit

Options:
  --push              Push current branch and the new tag after local tag creation.
  --yes               Auto-confirm prompts. Use with care.
  --dry-run           Print the planned release and exit before changing files.
  --skip-checks       Skip test/typecheck/package-resource verification.
  --skip-lock         Do not refresh pnpm/uv lockfiles.
  --full-build        Run desktop-electron build:app instead of quick resource verification.
  --no-commit         Update files and run checks, but do not commit.
  --no-tag            Do not create a git tag. Implies --no-commit behavior only for tag step.
  --allow-dirty       Allow starting from a dirty worktree.
  --no-fetch          Do not fetch remote tags before checking conflicts.
  --remote <name>     Git remote to fetch/push. Default: origin.
  --branch <name>     Expected release branch. Default: main.
  -h, --help          Show this help.

Release outputs:
  - Version fields are synchronized across frontend, desktop, backend, and harness.
  - CHANGELOG.md receives a new section from git commit subjects since the previous tag.
  - An annotated tag v<version> is created unless --no-tag is used.
  - Pushing the tag triggers .github/workflows/release-desktop.yml.
EOF
}

log() {
  printf '\033[1;34m==>\033[0m %s\n' "$*"
}

warn() {
  printf '\033[1;33mWARN:\033[0m %s\n' "$*" >&2
}

die() {
  printf '\033[1;31mERROR:\033[0m %s\n' "$*" >&2
  exit 1
}

run() {
  printf '+'
  for arg in "$@"; do
    printf ' %q' "$arg"
  done
  printf '\n'
  if [[ "$DRY_RUN" == true ]]; then
    return 0
  fi
  "$@"
}

run_shell() {
  local description="$1"
  local command="$2"
  printf '+ %s\n' "$command"
  if [[ "$DRY_RUN" == true ]]; then
    return 0
  fi
  bash -lc "$command"
}

confirm() {
  local prompt="$1"
  if [[ "$YES" == true ]]; then
    return 0
  fi
  local answer
  read -r -p "$prompt [y/N] " answer
  case "$answer" in
    y|Y|yes|YES) return 0 ;;
    *) return 1 ;;
  esac
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -h|--help)
        usage
        exit 0
        ;;
      --push)
        PUSH=true
        ;;
      --yes)
        YES=true
        ;;
      --dry-run)
        DRY_RUN=true
        ;;
      --skip-checks)
        SKIP_CHECKS=true
        ;;
      --skip-lock)
        SKIP_LOCK=true
        ;;
      --full-build)
        FULL_BUILD=true
        ;;
      --no-commit)
        NO_COMMIT=true
        ;;
      --no-tag)
        NO_TAG=true
        ;;
      --allow-dirty)
        ALLOW_DIRTY=true
        ;;
      --no-fetch)
        NO_FETCH=true
        ;;
      --remote)
        [[ $# -ge 2 ]] || die "--remote requires a value"
        REMOTE="$2"
        shift
        ;;
      --branch)
        [[ $# -ge 2 ]] || die "--branch requires a value"
        EXPECTED_BRANCH="$2"
        shift
        ;;
      --*)
        die "Unknown option: $1"
        ;;
      *)
        if [[ -n "$VERSION" ]]; then
          die "Only one version argument is allowed"
        fi
        VERSION="${1#v}"
        ;;
    esac
    shift
  done

  [[ -n "$VERSION" ]] || die "Missing version. Run ./$SCRIPT_NAME --help"
  [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]] || die "Invalid version: $VERSION"
  TAG="v$VERSION"
}

repo_root() {
  git rev-parse --show-toplevel 2>/dev/null
}

ensure_repo_state() {
  need_cmd git
  local root
  root="$(repo_root)" || die "Not inside a git repository"
  cd "$root"

  local current_branch
  current_branch="$(git symbolic-ref --quiet --short HEAD || true)"
  if [[ -z "$current_branch" ]]; then
    die "Detached HEAD is not supported for release tagging"
  fi
  if [[ "$current_branch" != "$EXPECTED_BRANCH" ]]; then
    if ! confirm "Current branch is '$current_branch', expected '$EXPECTED_BRANCH'. Continue anyway?"; then
      die "Release aborted"
    fi
  fi

  if [[ "$ALLOW_DIRTY" != true ]] && ! git diff --quiet --ignore-submodules --; then
    die "Worktree has unstaged changes. Commit/stash them or pass --allow-dirty"
  fi
  if [[ "$ALLOW_DIRTY" != true ]] && ! git diff --cached --quiet --ignore-submodules --; then
    die "Index has staged changes. Commit/stash them or pass --allow-dirty"
  fi
  if [[ "$ALLOW_DIRTY" != true ]] && [[ -n "$(git ls-files --others --exclude-standard)" ]]; then
    die "Worktree has untracked files. Commit/stash them or pass --allow-dirty"
  fi

  if [[ "$NO_FETCH" != true ]]; then
    log "Fetching tags from $REMOTE"
    run git fetch "$REMOTE" --tags
  fi

  if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
    die "Local tag already exists: $TAG"
  fi
  if git ls-remote --exit-code --tags "$REMOTE" "refs/tags/$TAG" >/dev/null 2>&1; then
    die "Remote tag already exists on $REMOTE: $TAG"
  fi
}

print_plan() {
  local previous_tag
  previous_tag="$(git describe --tags --abbrev=0 2>/dev/null || true)"
  log "Release plan"
  cat <<EOF
  Version:         $VERSION
  Tag:             $TAG
  Remote:          $REMOTE
  Branch:          $(git symbolic-ref --short HEAD)
  Previous tag:    ${previous_tag:-<none>}
  Refresh locks:   $([[ "$SKIP_LOCK" == true ]] && echo no || echo yes)
  Run checks:      $([[ "$SKIP_CHECKS" == true ]] && echo no || echo yes)
  Desktop build:   $([[ "$FULL_BUILD" == true ]] && echo full build:app || echo quick verifier)
  Commit:          $([[ "$NO_COMMIT" == true ]] && echo no || echo yes)
  Tag:             $([[ "$NO_TAG" == true ]] && echo no || echo yes)
  Push:            $([[ "$PUSH" == true ]] && echo yes || echo no)
EOF
}

update_versions() {
  log "Updating version files to $VERSION"
  python3 - "$VERSION" <<'PY'
import json
import re
import sys
from pathlib import Path

version = sys.argv[1]

json_files = [
    Path("frontend/package.json"),
    Path("desktop-electron/package.json"),
]

toml_files = [
    Path("backend/pyproject.toml"),
    Path("backend/packages/harness/pyproject.toml"),
]

for path in json_files:
    data = json.loads(path.read_text(encoding="utf-8"))
    old = data.get("version")
    if old != version:
        data["version"] = version
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"updated {path}: {old} -> {version}")
    else:
        print(f"unchanged {path}: {version}")

project_version_re = re.compile(r"(?ms)^(\[project\]\s.*?^version\s*=\s*)\"[^\"]+\"", re.MULTILINE)
for path in toml_files:
    text = path.read_text(encoding="utf-8")
    match = project_version_re.search(text)
    if not match:
        raise SystemExit(f"Could not find [project] version in {path}")
    old_match = re.search(r'^version\s*=\s*"([^"]+)"', match.group(0), re.MULTILINE)
    old = old_match.group(1) if old_match else "<unknown>"
    if old != version:
        text = project_version_re.sub(rf'\1"{version}"', text, count=1)
        path.write_text(text, encoding="utf-8")
        print(f"updated {path}: {old} -> {version}")
    else:
        print(f"unchanged {path}: {version}")
PY
}

refresh_lockfiles() {
  if [[ "$SKIP_LOCK" == true ]]; then
    log "Skipping lockfile refresh"
    return 0
  fi

  log "Refreshing lockfiles"
  if [[ -f frontend/pnpm-lock.yaml ]]; then
    need_cmd pnpm
    run_shell "frontend lockfile" "pnpm --dir frontend install --lockfile-only --ignore-scripts"
  fi
  if [[ -f desktop-electron/pnpm-lock.yaml ]]; then
    need_cmd pnpm
    run_shell "desktop lockfile" "pnpm --dir desktop-electron install --lockfile-only --ignore-scripts"
  fi
  if [[ -f backend/uv.lock ]]; then
    need_cmd uv
    run_shell "backend lockfile" "cd backend && uv lock"
  fi
}

generate_changelog() {
  log "Updating CHANGELOG.md"
  local previous_tag
  previous_tag="$(git describe --tags --abbrev=0 2>/dev/null || true)"
  local range="HEAD"
  if [[ -n "$previous_tag" ]]; then
    range="$previous_tag..HEAD"
  fi

  local notes
  notes="$(git log --pretty=format:'- %s (%h)' "$range" --no-merges || true)"
  if [[ -z "$notes" ]]; then
    notes="- Version metadata update."
  fi

  RELEASE_VERSION="$VERSION" RELEASE_TAG="$TAG" RELEASE_PREVIOUS_TAG="$previous_tag" RELEASE_NOTES="$notes" python3 <<'PY'
import os
from datetime import date
from pathlib import Path

version = os.environ["RELEASE_VERSION"]
tag = os.environ["RELEASE_TAG"]
previous_tag = os.environ.get("RELEASE_PREVIOUS_TAG") or ""
notes = os.environ["RELEASE_NOTES"]
today = date.today().isoformat()

path = Path("CHANGELOG.md")
existing = path.read_text(encoding="utf-8") if path.exists() else "# Changelog\n\n"
if not existing.startswith("# Changelog"):
    existing = "# Changelog\n\n" + existing

compare = f"{previous_tag}...{tag}" if previous_tag else tag
section = f"## {tag} - {today}\n\n"
section += f"Compare: `{compare}`\n\n"
section += f"{notes}\n\n"

if f"## {tag} " in existing:
    raise SystemExit(f"CHANGELOG.md already has a section for {tag}")

head, _, tail = existing.partition("\n\n")
path.write_text(head + "\n\n" + section + tail.lstrip(), encoding="utf-8")
print(f"prepended CHANGELOG.md section for {tag}")
PY
}

run_checks() {
  if [[ "$SKIP_CHECKS" == true ]]; then
    log "Skipping checks"
    return 0
  fi

  log "Running release checks"
  need_cmd pnpm
  need_cmd uv

  run_shell "backend tests" "cd backend && PYTHONPATH=.:packages/harness uv run python -m pytest -q"
  run_shell "frontend tests" "cd frontend && pnpm test"
  run_shell "frontend typecheck" "cd frontend && pnpm run typecheck"
  run_shell "desktop lint" "cd desktop-electron && pnpm run lint"
  run_shell "desktop package tests" "cd desktop-electron && node --test tests/package-build.test.mjs"

  if [[ "$FULL_BUILD" == true ]]; then
    run_shell "desktop full build" "cd desktop-electron && pnpm run build:app"
  else
    run_shell "desktop package resources" "cd desktop-electron && pnpm run verify:package-resources"
  fi
}

stage_paths() {
  local paths=()
  for path in "${ROOT_FILES[@]}"; do
    [[ -e "$path" ]] && paths+=("$path")
  done
  for path in "${LOCK_FILES[@]}"; do
    [[ -e "$path" ]] && paths+=("$path")
  done
  [[ -e CHANGELOG.md ]] && paths+=("CHANGELOG.md")

  if [[ ${#paths[@]} -eq 0 ]]; then
    die "No release files found to stage"
  fi
  run git add "${paths[@]}"
}

commit_and_tag() {
  if [[ "$NO_COMMIT" == true ]]; then
    log "Skipping commit because --no-commit was provided"
    return 0
  fi

  log "Creating release commit"
  stage_paths
  if git diff --cached --quiet --; then
    die "No staged release changes. Is $VERSION already applied?"
  fi
  run git commit -m "chore(release): $TAG"

  if [[ "$NO_TAG" == true ]]; then
    log "Skipping tag because --no-tag was provided"
    return 0
  fi

  log "Creating annotated tag $TAG"
  run git tag -a "$TAG" -m "Release $TAG"
}

push_release() {
  if [[ "$PUSH" != true ]]; then
    log "Local release is ready"
    cat <<EOF
Next manual commands:
  git push $REMOTE $(git symbolic-ref --short HEAD)
  git push $REMOTE $TAG

Pushing $TAG triggers:
  .github/workflows/release-desktop.yml
EOF
    return 0
  fi

  if ! confirm "Push branch and tag $TAG to $REMOTE now?"; then
    die "Push aborted. Local commit/tag remain in your repository."
  fi

  local branch
  branch="$(git symbolic-ref --short HEAD)"
  run git push "$REMOTE" "$branch"
  if [[ "$NO_TAG" != true ]]; then
    run git push "$REMOTE" "$TAG"
  fi
}

main() {
  parse_args "$@"
  ensure_repo_state
  print_plan

  if [[ "$DRY_RUN" == true ]]; then
    log "Dry run only; no files changed"
    exit 0
  fi

  if ! confirm "Proceed with release $TAG?"; then
    die "Release aborted"
  fi

  update_versions
  refresh_lockfiles
  generate_changelog
  run_checks
  commit_and_tag
  push_release

  log "Release lifecycle complete for $TAG"
}

main "$@"
