#!/usr/bin/env bash
set -euo pipefail

# OClaw release lifecycle manager.
#
# The local script prepares the release commit and tag, then delegates
# desktop packaging/signing/publishing to GitHub Actions by pushing the tag.

SCRIPT_NAME="$(basename "$0")"

VERSION=""
TAG=""
REMOTE="origin"
EXPECTED_BRANCH="main"
RELEASE_WORKFLOW="release-desktop.yml"
RELEASE_LOG_DIR=".release-logs"
REPO_SLUG=""
PUSH=false
WATCH=true
YES=false
DRY_RUN=false
SKIP_CHECKS=false
SKIP_LOCK=false
FULL_BUILD=false
FULL_TESTS=false
NO_COMMIT=false
NO_TAG=false
ALLOW_DIRTY=false
NO_FETCH=false
RESUME=false

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
  ./release.sh v0.2.1 --push
  ./release.sh 0.2.1 --push --yes
  ./release.sh v0.2.1 --full-build --push --yes
  ./release.sh v0.2.1 --resume --yes
  ./release.sh v0.2.1 --skip-checks --no-commit

Options:
  --push              Atomic-push the current branch and new tag to GitHub.
  --no-watch          Push the tag but do not wait for GitHub Actions.
  --resume            Do not update/commit/tag/push; watch an existing remote tag run.
  --yes               Auto-confirm prompts. Use with care.
  --dry-run           Print the planned release and exit before changing files.
  --skip-checks       Skip test/typecheck/package-resource verification.
  --skip-lock         Do not refresh pnpm/uv lockfiles.
  --full-build        Compatibility flag; full desktop packaging runs remotely.
  --full-tests        Run the full backend pytest suite instead of stable release smoke tests.
  --no-commit         Update files and run checks, but do not commit.
  --no-tag            Do not create a git tag.
  --allow-dirty       Allow starting from a dirty worktree.
  --no-fetch          Do not fetch remote tags before checking conflicts.
  --remote <name>     Git remote to fetch/push. Default: origin.
  --branch <name>     Expected release branch. Default: main.
  --workflow <name>   GitHub Actions workflow name or file. Default: release-desktop.yml.
  -h, --help          Show this help.

Release outputs:
  - Version fields are synchronized across frontend, desktop, backend, and harness.
  - CHANGELOG.md receives a new section from git commit subjects since the previous tag.
  - An annotated tag v<version> is created unless --no-tag is used.
  - Pushing the tag triggers .github/workflows/release-desktop.yml.
  - With --push, this script waits for GitHub Actions and verifies Release assets.
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
      --no-watch)
        WATCH=false
        ;;
      --resume)
        RESUME=true
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
      --full-tests)
        FULL_TESTS=true
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
      --workflow)
        [[ $# -ge 2 ]] || die "--workflow requires a value"
        RELEASE_WORKFLOW="$2"
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

  if [[ "$RESUME" == true ]]; then
    PUSH=false
  fi
}

repo_root() {
  git rev-parse --show-toplevel 2>/dev/null
}

repo_slug() {
  local url slug
  url="$(git remote get-url "$REMOTE")" || die "Unknown git remote: $REMOTE"
  case "$url" in
    git@github.com:*) slug="${url#git@github.com:}" ;;
    ssh://git@github.com/*) slug="${url#ssh://git@github.com/}" ;;
    https://github.com/*) slug="${url#https://github.com/}" ;;
    http://github.com/*) slug="${url#http://github.com/}" ;;
    *) die "Cannot infer GitHub repo from remote URL: $url" ;;
  esac
  slug="${slug%.git}"
  [[ "$slug" == */* ]] || die "Cannot infer GitHub repo from remote URL: $url"
  printf '%s\n' "$slug"
}

remote_tag_exists() {
  git ls-remote --exit-code --tags "$REMOTE" "refs/tags/$TAG" >/dev/null 2>&1
  local status=$?
  case "$status" in
    0) return 0 ;;
    2) return 1 ;;
    *) die "Could not check remote tag $TAG on $REMOTE" ;;
  esac
}

worktree_status() {
  git status --porcelain --untracked-files=normal
}

ensure_repo_state() {
  need_cmd git
  need_cmd python3
  local root
  root="$(repo_root)" || die "Not inside a git repository"
  cd "$root"

  git remote get-url "$REMOTE" >/dev/null || die "Unknown git remote: $REMOTE"

  local current_branch
  current_branch="$(git symbolic-ref --quiet --short HEAD || true)"
  if [[ "$RESUME" != true ]]; then
    if [[ -z "$current_branch" ]]; then
      die "Detached HEAD is not supported for release tagging"
    fi
    if [[ "$current_branch" != "$EXPECTED_BRANCH" ]]; then
      if ! confirm "Current branch is '$current_branch', expected '$EXPECTED_BRANCH'. Continue anyway?"; then
        die "Release aborted"
      fi
    fi
  fi

  local status
  status="$(worktree_status)"
  if [[ -n "$status" && "$ALLOW_DIRTY" != true && "$RESUME" != true ]]; then
    die "Worktree is not clean. Commit/stash changes or pass --allow-dirty"$'\n'"$status"
  fi
  if [[ -n "$status" && "$RESUME" == true ]]; then
    warn "Resume mode ignores current worktree changes:"
    printf '%s\n' "$status" >&2
  fi

  if [[ "$NO_FETCH" != true ]]; then
    log "Fetching tags from $REMOTE"
    run git fetch "$REMOTE" --tags
  fi

  if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
    if [[ "$RESUME" != true ]]; then
      die "Local tag already exists: $TAG"
    fi
  fi
  if remote_tag_exists; then
    if [[ "$RESUME" != true ]]; then
      die "Remote tag already exists on $REMOTE: $TAG"
    fi
  elif [[ "$RESUME" == true ]]; then
    die "Cannot resume; remote tag does not exist on $REMOTE: $TAG"
  fi

  if { [[ "$PUSH" == true && "$WATCH" == true && "$NO_TAG" != true ]] || [[ "$RESUME" == true ]]; } && [[ "$DRY_RUN" != true ]]; then
    need_cmd gh
  fi

  REPO_SLUG="$(repo_slug)"
}

print_plan() {
  local previous_tag branch
  previous_tag="$(git describe --tags --abbrev=0 2>/dev/null || true)"
  branch="$(git symbolic-ref --quiet --short HEAD || true)"
  log "Release plan"
  cat <<EOF
  Mode:            $([[ "$RESUME" == true ]] && echo resume existing tag || echo prepare new tag)
  Version:         $VERSION
  Tag:             $TAG
  Repo:            $REPO_SLUG
  Remote:          $REMOTE
  Branch:          ${branch:-<detached>}
  Previous tag:    ${previous_tag:-<none>}
  Refresh locks:   $([[ "$SKIP_LOCK" == true ]] && echo no || echo yes)
  Run checks:      $([[ "$SKIP_CHECKS" == true ]] && echo no || echo yes)
  Local desktop:   quick resource verification
  Remote desktop:  GitHub Actions workflow $RELEASE_WORKFLOW
  Backend tests:   $([[ "$FULL_TESTS" == true ]] && echo full pytest || echo release smoke)
  Commit:          $([[ "$NO_COMMIT" == true || "$RESUME" == true ]] && echo no || echo yes)
  Tag:             $([[ "$NO_TAG" == true || "$RESUME" == true ]] && echo no || echo yes)
  Push:            $([[ "$PUSH" == true ]] && echo yes || echo no)
  Watch:           $([[ "$WATCH" == true ]] && echo yes || echo no)
EOF
  if [[ "$FULL_BUILD" == true ]]; then
    warn "--full-build is accepted for compatibility; full desktop packaging runs in GitHub Actions."
  fi
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
    print(f"CHANGELOG.md already has a section for {tag}; leaving it unchanged")
    raise SystemExit(0)

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

  if [[ "$FULL_TESTS" == true ]]; then
    run_shell "backend full tests" "cd backend && PYTHONPATH=.:packages/harness uv run python -m pytest -q"
  else
    run_shell "backend release smoke tests" "cd backend && PYTHONPATH=.:packages/harness uv run python -m pytest -q tests/test_mcp_sync_wrapper.py tests/test_security_scanner.py tests/test_skill_manage_tool.py tests/test_skill_frontmatter_work_modes.py tests/test_skills_parser.py tests/test_mcp_config_preservation.py tests/test_work_mode_api.py tests/test_client.py::TestMcpConfig tests/test_client.py::TestSkillsManagement"
  fi
  run_shell "frontend tests" "cd frontend && pnpm test"
  run_shell "frontend typecheck" "cd frontend && pnpm run typecheck"
  run_shell "desktop lint" "cd desktop-electron && pnpm run lint"
  run_shell "desktop package tests" "cd desktop-electron && node --test tests/package-build.test.mjs tests/release-lifecycle-script.test.mjs"
  run_shell "desktop package resources" "cd desktop-electron && pnpm run verify:package-resources"
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
    if [[ "$NO_TAG" == true ]]; then
      cat <<EOF
Next manual command:
  git push $REMOTE $(git symbolic-ref --short HEAD)
EOF
    else
      cat <<EOF
Next manual command:
  git push --atomic $REMOTE $(git symbolic-ref --short HEAD) $TAG

Then monitor the remote release:
  ./$SCRIPT_NAME $TAG --resume --yes

Pushing $TAG triggers:
  .github/workflows/release-desktop.yml
EOF
    fi
    return 0
  fi

  if ! confirm "Atomic-push branch and tag $TAG to $REMOTE now?"; then
    die "Push aborted. Local commit/tag remain in your repository."
  fi

  local branch
  branch="$(git symbolic-ref --short HEAD)"
  if [[ "$NO_TAG" == true ]]; then
    run git push "$REMOTE" "$branch"
    return 0
  fi
  run git push --atomic "$REMOTE" "$branch" "$TAG"
}

save_failure_logs() {
  local run_id="$1"
  mkdir -p "$RELEASE_LOG_DIR"
  local summary_path="$RELEASE_LOG_DIR/run-$run_id.json"
  local log_path="$RELEASE_LOG_DIR/run-$run_id.log"

  gh run view "$run_id" \
    --repo "$REPO_SLUG" \
    --json status,conclusion,jobs,url,name,displayTitle,event,headSha,createdAt,updatedAt \
    >"$summary_path" 2>/dev/null || true
  gh run view "$run_id" \
    --repo "$REPO_SLUG" \
    --log-failed \
    >"$log_path" 2>&1 || true

  warn "Saved failed run diagnostics:"
  warn "  $summary_path"
  warn "  $log_path"
}

find_release_run_id() {
  local runs_json="$1"
  RUNS_JSON="$runs_json" RELEASE_TAG="$TAG" python3 <<'PY'
import json
import os

runs = json.loads(os.environ.get("RUNS_JSON") or "[]")
tag = os.environ["RELEASE_TAG"]
for run in runs:
    if run.get("headBranch") == tag:
        print(run.get("databaseId", ""))
        break
PY
}

wait_for_release_run() {
  if [[ "$DRY_RUN" == true ]]; then
    log "Dry run only; skipping GitHub Actions watch"
    return 0
  fi
  if [[ "$WATCH" != true ]]; then
    log "Skipping GitHub Actions watch because --no-watch was provided"
    return 0
  fi
  if [[ "$NO_TAG" == true ]]; then
    log "Skipping GitHub Actions watch because --no-tag was provided"
    return 0
  fi

  log "Waiting for GitHub Actions release run for $TAG"
  local run_id=""
  local output=""
  for attempt in $(seq 1 30); do
    output="$(gh run list \
      --repo "$REPO_SLUG" \
      --workflow "$RELEASE_WORKFLOW" \
      --limit 30 \
      --json databaseId,event,headBranch,status,conclusion,displayTitle,createdAt)"
    run_id="$(find_release_run_id "$output")"
    if [[ -n "$run_id" ]]; then
      break
    fi
    printf 'Still waiting for run (%s/30)...\n' "$attempt"
    sleep 10
  done

  if [[ -z "$run_id" ]]; then
    die "No GitHub Actions run appeared for $TAG in workflow $RELEASE_WORKFLOW"
  fi

  log "Watching GitHub Actions run $run_id"
  if ! gh run watch "$run_id" --repo "$REPO_SLUG" --exit-status; then
    save_failure_logs "$run_id"
    die "GitHub Actions release run failed: $run_id"
  fi
}

verify_release_assets() {
  if [[ "$DRY_RUN" == true || "$WATCH" != true || "$NO_TAG" == true ]]; then
    return 0
  fi

  log "Verifying GitHub Release assets for $TAG"
  local release_json
  release_json="$(gh release view "$TAG" \
    --repo "$REPO_SLUG" \
    --json tagName,name,publishedAt,url,assets)"

  RELEASE_JSON="$release_json" RELEASE_VERSION="$VERSION" python3 <<'PY'
import json
import os
import sys

data = json.loads(os.environ["RELEASE_JSON"])
version = os.environ["RELEASE_VERSION"]
assets = [asset.get("name", "") for asset in data.get("assets", [])]

def has_manifest(name):
    return name in assets

def has_asset(suffix, *needles):
    return any(
        name.endswith(suffix)
        and version in name
        and all(needle in name for needle in needles)
        for name in assets
    )

checks = [
    ("macOS arm64 DMG", has_asset(".dmg", "arm64")),
    ("macOS arm64 ZIP", has_asset(".zip", "arm64", "mac")),
    ("Windows installer", has_asset(".exe")),
    ("Linux deb", has_asset(".deb")),
    ("Linux rpm", has_asset(".rpm")),
    ("latest-mac.yml", has_manifest("latest-mac.yml")),
    ("latest.yml", has_manifest("latest.yml")),
    ("latest-linux.yml", has_manifest("latest-linux.yml")),
]

missing = [label for label, ok in checks if not ok]
if missing:
    print(f"Release {data.get('tagName')} is missing expected assets:", file=sys.stderr)
    for label in missing:
        print(f"  - {label}", file=sys.stderr)
    print("\nAssets found:", file=sys.stderr)
    for name in assets:
        print(f"  - {name}", file=sys.stderr)
    sys.exit(1)

print(f"Release assets verified: {data.get('url', '<no url>')}")
for name in sorted(assets):
    print(f"  - {name}")
PY
}

main() {
  parse_args "$@"
  ensure_repo_state
  print_plan

  if [[ "$DRY_RUN" == true ]]; then
    log "Dry run only; no files changed"
    exit 0
  fi

  if [[ "$RESUME" == true ]]; then
    wait_for_release_run
    verify_release_assets
    log "Release lifecycle complete for $TAG"
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
  if [[ "$PUSH" == true ]]; then
    wait_for_release_run
    verify_release_assets
  fi

  log "Release lifecycle complete for $TAG"
}

main "$@"
