#!/usr/bin/env python
"""Create placeholder GitHub Actions workflow on default branch to preserve workflow name."""

import sys
import re
import argparse
from subprocess import check_output, check_call, CalledProcessError, DEVNULL
from pathlib import Path
from functools import partial

err = partial(print, file=sys.stderr)


def run_git(cmd, check=True):
    """Run a git command and return output."""
    full_cmd = ['git'] + cmd
    try:
        if check:
            return check_output(full_cmd, stderr=DEVNULL).decode().strip()
        else:
            return check_output(full_cmd, stderr=DEVNULL).decode().strip()
    except CalledProcessError:
        if check:
            raise
        return None


def get_current_branch():
    """Get the current git branch name."""
    return run_git(['rev-parse', '--abbrev-ref', 'HEAD'])


def get_github_remote():
    """Get the GitHub remote using the same logic as github_default_remote."""
    # Try to find the only GitHub remote
    try:
        # Look for GitHub remotes
        remotes_output = check_output(['git', 'remote', '-v'], stderr=DEVNULL).decode()
        github_remotes = []
        for line in remotes_output.strip().split('\n'):
            if 'github.com' in line:
                remote_name = line.split()[0]
                if remote_name not in github_remotes:
                    github_remotes.append(remote_name)

        if len(github_remotes) == 1:
            return github_remotes[0]
        elif len(github_remotes) > 1:
            # Multiple GitHub remotes, check tracked branch
            try:
                upstream = run_git(['rev-parse', '--abbrev-ref', '@{u}'], check=False)
                if upstream:
                    remote = upstream.split('/')[0]
                    if remote in github_remotes:
                        err(f"Multiple GitHub remotes found, using '{remote}' from tracked branch")
                        return remote
            except:
                pass

            # As last resort, try gh CLI default
            try:
                result = check_output(['gh', 'repo', 'set-default', '--view'],
                                    stderr=DEVNULL).decode().strip()
                if result:
                    # Parse remote name from the output
                    for remote in github_remotes:
                        remote_url = run_git(['remote', 'get-url', remote], check=False)
                        if result in remote_url:
                            return remote
            except:
                pass

            raise ValueError(f"Multiple GitHub remotes found: {', '.join(github_remotes)}. "
                           "Cannot determine which to use.")
        else:
            raise ValueError("No GitHub remote found")
    except CalledProcessError as e:
        raise ValueError(f"Failed to get git remotes: {e}")


def get_default_branch(remote):
    """Get the default branch for the repository from the specified remote."""
    # Try to get from GitHub via gh CLI (most reliable)
    try:
        result = check_output(['gh', 'repo', 'view', '--json', 'defaultBranchRef'],
                            stderr=DEVNULL).decode().strip()
        import json
        data = json.loads(result)
        if 'defaultBranchRef' in data and 'name' in data['defaultBranchRef']:
            branch_name = data['defaultBranchRef']['name']
            err(f"Default branch from GitHub API: {branch_name}")
            return branch_name
    except:
        pass

    # Try to get from git remote HEAD
    try:
        # Get the symbolic ref for the remote HEAD
        result = run_git(['symbolic-ref', f'refs/remotes/{remote}/HEAD'], check=False)
        if result:
            # Extract branch name from refs/remotes/origin/main -> main
            branch_name = result.split('/')[-1]
            err(f"Default branch from remote HEAD: {branch_name}")
            return branch_name

        # Remote HEAD might not be set, try to set it
        err(f"Remote HEAD not set, fetching from {remote}...")
        check_call(['git', 'remote', 'set-head', remote, '-a'], stderr=DEVNULL)
        result = run_git(['symbolic-ref', f'refs/remotes/{remote}/HEAD'], check=False)
        if result:
            branch_name = result.split('/')[-1]
            err(f"Default branch from remote HEAD (after update): {branch_name}")
            return branch_name
    except:
        pass

    raise ValueError(f"Could not determine default branch for remote '{remote}'. "
                    f"Try running: git remote set-head {remote} -a")


def get_modified_workflows():
    """Get list of workflow files modified in the current commit."""
    # Get list of files changed in the last commit
    files = run_git(['diff', '--name-only', 'HEAD~1', 'HEAD']).split('\n')

    # Filter for GitHub Actions workflow files
    workflows = []
    for f in files:
        if f.startswith('.github/workflows/') and f.endswith('.yml'):
            workflows.append(f)
        elif f.startswith('.github/workflows/') and f.endswith('.yaml'):
            workflows.append(f)

    return workflows


def extract_workflow_name(workflow_path):
    """Extract the 'name' field from a workflow YAML file."""
    try:
        with open(workflow_path, 'r') as f:
            content = f.read()

        # Look for the name field at the beginning of the file
        # It should be at the top level (not indented)
        match = re.search(r'^name:\s*(.+)$', content, re.MULTILINE)
        if match:
            name = match.group(1).strip()
            # Remove quotes if present
            if (name.startswith('"') and name.endswith('"')) or \
               (name.startswith("'") and name.endswith("'")):
                name = name[1:-1]
            return name
    except FileNotFoundError:
        pass

    # Fallback to filename without extension
    return Path(workflow_path).stem


def create_placeholder_yaml(name):
    """Create a placeholder workflow YAML content."""
    return f'''name: {name}
on:
  workflow_dispatch:
jobs:
  placeholder:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Placeholder workflow to preserve workflow name in GitHub Actions UI"
'''


def is_placeholder_workflow(content):
    """Check if workflow content is a placeholder."""
    # Check for telltale signs of a placeholder workflow
    if 'Placeholder workflow to preserve workflow name' in content:
        return True

    # Also check for the minimal structure
    lines = content.strip().split('\n')
    if len(lines) < 10:  # Placeholders are short
        if 'workflow_dispatch:' in content and \
           'echo' in content and \
           'placeholder' in content.lower():
            return True

    return False


def is_placeholder_commit():
    """Check if the current HEAD commit on default branch is a placeholder commit."""
    # Check commit message
    msg = run_git(['log', '-1', '--pretty=%s'])

    # Common patterns for placeholder commits
    placeholder_patterns = [
        r'placeholder.*workflow',
        r'workflow.*placeholder',
        r'preserve.*workflow.*name',
        r'add.*placeholder.*workflow',
        r'^\+\s*\.github/workflows/.*\.yml',  # Commit message showing added workflow
    ]

    for pattern in placeholder_patterns:
        if re.search(pattern, msg, re.IGNORECASE):
            err(f"Detected placeholder commit from message: {msg}")
            return True

    # Check if all modified workflows in the last commit are placeholders
    try:
        # Get files changed in the last commit
        files = run_git(['diff', '--name-only', 'HEAD~1', 'HEAD']).split('\n')
        workflow_files = [f for f in files if f.startswith('.github/workflows/') and
                         (f.endswith('.yml') or f.endswith('.yaml'))]

        if workflow_files:
            all_placeholders = True
            for wf in workflow_files:
                if Path(wf).exists():
                    with open(wf, 'r') as f:
                        if not is_placeholder_workflow(f.read()):
                            all_placeholders = False
                            break

            if all_placeholders:
                err(f"Detected placeholder commit from workflow contents")
                return True
    except:
        pass

    return False


def main():
    parser = argparse.ArgumentParser(
        description='Create placeholder GitHub Actions workflow on default branch'
    )
    parser.add_argument('-s', '--squash', action='store_true',
                        help='Squash into existing placeholder commit if detected')
    parser.add_argument('-f', '--force', action='store_true',
                        help='Force creation even if workflow already exists on default branch')
    parser.add_argument('-n', '--dry-run', action='store_true',
                        help='Show what would be done without making changes')
    parser.add_argument('-b', '--branch',
                        help='Override default branch detection')
    parser.add_argument('--stash', action='store_true',
                        help='Stash uncommitted changes before switching branches')
    parser.add_argument('workflow', nargs='?',
                        help='Workflow file path (auto-detects if not specified)')

    args = parser.parse_args()

    # Get GitHub remote
    try:
        remote = get_github_remote()
        err(f"Using GitHub remote: {remote}")
    except ValueError as e:
        err(f"Error: {e}")
        return 1

    # Get default branch
    if args.branch:
        default_branch = args.branch
        err(f"Using specified branch: {default_branch}")
    else:
        try:
            default_branch = get_default_branch(remote)
        except ValueError as e:
            err(f"Error: {e}")
            return 1

    # Check if local branch exists
    if not run_git(['show-ref', '--verify', f'refs/heads/{default_branch}'], check=False):
        err(f"Error: Local branch '{default_branch}' does not exist")
        err(f"You may need to: git checkout -b {default_branch} {remote}/{default_branch}")
        return 1

    # Get current branch
    current_branch = get_current_branch()
    if current_branch == default_branch:
        err(f"Error: Already on default branch ({default_branch}). Run from a feature branch.")
        return 1

    # Determine workflow files to process
    if args.workflow:
        workflows = [args.workflow]
    else:
        # Auto-detect from last commit
        workflows = get_modified_workflows()
        if not workflows:
            err("Error: No workflow files found in the last commit")
            err("Specify a workflow file explicitly or commit a workflow first")
            return 1

    err(f"Processing workflows: {', '.join(workflows)}")

    # Extract workflow names
    workflow_info = []
    for wf_path in workflows:
        if not Path(wf_path).exists():
            err(f"Error: Workflow file not found: {wf_path}")
            return 1

        name = extract_workflow_name(wf_path)
        err(f"  {wf_path} -> name: '{name}'")
        workflow_info.append((wf_path, name))

    if args.dry_run:
        err("\n[DRY-RUN] Would perform the following actions:")

    # Check for uncommitted changes
    stashed = False
    if not args.dry_run:
        # Check for staged or unstaged changes (but ignore untracked files)
        diff_output = run_git(['diff', 'HEAD', '--name-only'], check=False)
        staged_output = run_git(['diff', '--cached', '--name-only'], check=False)

        if diff_output or staged_output:
            if args.stash:
                # User explicitly requested stashing
                err("Stashing uncommitted changes...")
                try:
                    run_git(['stash', 'push', '-m', 'github-placeholder-main auto-stash'])
                    stashed = True
                except:
                    err("Error: Failed to stash changes")
                    return 1
            else:
                # Default behavior: refuse to proceed with uncommitted changes
                err("Error: You have uncommitted changes")
                if diff_output:
                    err("  Unstaged changes in:")
                    for f in diff_output.split('\n')[:5]:
                        if f:
                            err(f"    {f}")
                    if len(diff_output.split('\n')) > 5:
                        err(f"    ... and {len(diff_output.split('\n')) - 5} more files")
                if staged_output:
                    err("  Staged changes in:")
                    for f in staged_output.split('\n')[:5]:
                        if f:
                            err(f"    {f}")
                    if len(staged_output.split('\n')) > 5:
                        err(f"    ... and {len(staged_output.split('\n')) - 5} more files")
                err("\nOptions:")
                err("  1. Commit your changes first")
                err("  2. Use --stash to automatically stash and restore")
                err("  3. Use git stash manually")
                return 1

    try:
        # Switch to default branch
        if not args.dry_run:
            err(f"\nSwitching from {current_branch} to {default_branch}...")
            check_call(['git', 'checkout', default_branch])
        else:
            err(f"\n[DRY-RUN] Would switch from {current_branch} to {default_branch}")

        # Check if we should squash into existing commit
        should_squash = False
        if args.squash or (not args.dry_run and is_placeholder_commit()):
            should_squash = True
            if not args.dry_run:
                err("Will squash into existing placeholder commit")

        # Create placeholder workflows
        created_files = []
        for wf_path, name in workflow_info:
            # Check if workflow already exists in git on default branch
            # In dry-run mode or before switching, check the target branch directly
            if args.dry_run:
                file_exists_in_git = run_git(['ls-tree', f'{default_branch}', wf_path], check=False)
            else:
                file_exists_in_git = run_git(['ls-tree', 'HEAD', wf_path], check=False)

            if file_exists_in_git and not args.force:
                # File exists in git tree, check if it's a placeholder
                if args.dry_run:
                    existing_content = run_git(['show', f'{default_branch}:{wf_path}'], check=False)
                else:
                    existing_content = run_git(['show', f'HEAD:{wf_path}'], check=False)
                if existing_content and not is_placeholder_workflow(existing_content):
                    err(f"Warning: {wf_path} already exists on {default_branch} and is not a placeholder")
                    if not args.force:
                        err("  Use -f to overwrite")
                        continue

            # Create placeholder content
            placeholder_content = create_placeholder_yaml(name)

            if not args.dry_run:
                # Ensure directory exists
                Path(wf_path).parent.mkdir(parents=True, exist_ok=True)

                # Write placeholder file
                with open(wf_path, 'w') as f:
                    f.write(placeholder_content)
                err(f"Created placeholder: {wf_path}")
            else:
                err(f"[DRY-RUN] Would create placeholder: {wf_path}")
                err(f"[DRY-RUN] Content:")
                for line in placeholder_content.strip().split('\n'):
                    err(f"    {line}")

            created_files.append(wf_path)

        if not created_files:
            err("No placeholder files to create")
            return 0

        # Add and commit the changes
        if not args.dry_run:
            # Add the files
            for f in created_files:
                run_git(['add', f])

            # Prepare commit message
            if len(created_files) == 1:
                commit_msg = f"Add placeholder workflow for {Path(created_files[0]).stem}"
            else:
                commit_msg = f"Add placeholder workflows ({len(created_files)} files)"

            if should_squash:
                # Amend the existing commit
                err(f"Amending existing commit...")
                run_git(['commit', '--amend', '--no-edit'])
            else:
                # Create new commit
                err(f"Creating commit: {commit_msg}")
                run_git(['commit', '-m', commit_msg])

            err(f"\nSuccessfully created placeholder workflow(s) on {default_branch}")
            err(f"Returning to branch: {current_branch}")
            check_call(['git', 'checkout', current_branch])
        else:
            err(f"\n[DRY-RUN] Would commit {len(created_files)} placeholder file(s)")
            if should_squash:
                err("[DRY-RUN] Would amend existing commit")
            else:
                err("[DRY-RUN] Would create new commit")
            err(f"[DRY-RUN] Would return to branch: {current_branch}")

    finally:
        # Restore stashed changes if any
        if stashed and not args.dry_run:
            try:
                err("\nRestoring stashed changes...")
                run_git(['stash', 'pop'])
            except:
                err("Warning: Could not restore stashed changes automatically")
                err("Run 'git stash pop' manually to restore")

    return 0


if __name__ == '__main__':
    sys.exit(main())
