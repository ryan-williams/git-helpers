#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "click",
# ]
# ///
"""Open PR associated with the current branch."""

import os
import sys
import re
import json
from subprocess import check_output, CalledProcessError
from sys import stderr

# Add parent directory to path for local imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from git_helpers.util.branch_resolution import resolve_remote_ref

from click import command, option


SSH_REMOTE_URL_RGX = re.compile(r'git@github\.com:(?P<repo>[^/]+/[^/]+?)(?:\.git)?')
HTTPS_REMOTE_URL_RGX = re.compile(r'https://github\.com/(?P<repo>[^/]+/[^/]+?)(?:\.git)?')


def get_github_repo_from_remote(remote):
    """Get GitHub owner/repo from remote."""
    try:
        url = check_output(['git', 'remote', 'get-url', remote]).decode().strip()

        # Try SSH format
        m = SSH_REMOTE_URL_RGX.fullmatch(url)
        if m:
            return m.group('repo')

        # Try HTTPS format
        m = HTTPS_REMOTE_URL_RGX.fullmatch(url)
        if m:
            return m.group('repo')

        # Try short format (owner/repo)
        if '/' in url and not url.startswith('http'):
            return url.rstrip('.git')

        return None
    except:
        return None


@command()
@option('-r', '--remote', help='Specify remote (default: auto-detect)')
@option('-b', '--branch', help='Specify branch (default: current branch)')
@option('-n', '--dry-run', is_flag=True, help='Show what would be done without opening')
def main(remote, branch, dry_run):
    """Open PR associated with the current branch."""

    # Get current branch name if not specified
    if not branch:
        try:
            branch = check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode().strip()
            if branch == 'HEAD':
                stderr.write("Error: Not on a branch (detached HEAD)\n")
                sys.exit(1)
        except CalledProcessError:
            stderr.write("Error: Could not determine current branch\n")
            sys.exit(1)

    # Resolve remote ref
    ref_name, remote_ref = resolve_remote_ref(current_branch=branch, verbose=True)

    if not remote_ref:
        stderr.write(f"Error: No remote branch found for '{branch}'\n")
        stderr.write("Have you pushed your branch?\n")
        sys.exit(1)

    # Parse remote from remote_ref (e.g., "origin/branch" -> "origin")
    if not remote and remote_ref:
        remote = remote_ref.split('/')[0]

    # Get repository info
    repo = get_github_repo_from_remote(remote)
    if not repo:
        stderr.write(f"Error: Could not determine GitHub repo from remote '{remote}'\n")
        sys.exit(1)

    # Extract branch name from remote ref
    branch_name = ref_name if ref_name else branch

    # Search for PRs in multiple places:
    # 1. In the fork repo (e.g., ryan-williams/parquet2json with head limit)
    # 2. In upstream repos with head repo:branch (e.g., ryan-williams:limit)

    repos_to_search = [repo]

    # Check if there's a parent/upstream repo
    try:
        parent_data_raw = check_output([
            'gh', 'repo', 'view', repo,
            '--json', 'parent'
        ]).decode()
        parent_data = json.loads(parent_data_raw)
        if parent_data.get('parent'):
            parent_owner = parent_data['parent']['owner']['login']
            parent_name = parent_data['parent']['name']
            parent_repo = f"{parent_owner}/{parent_name}"
            repos_to_search.append(parent_repo)
            stderr.write(f"Detected parent repo: {parent_repo}\n")
    except Exception as e:
        stderr.write(f"Warning: Could not check for parent repo: {e}\n")

    pr_data = []
    for search_repo in repos_to_search:
        stderr.write(f"Searching for PR in {search_repo} with branch {branch_name}...\n")

        try:
            # Search with just branch name (for PRs within the same repo)
            pr_data_raw = check_output([
                'gh', 'pr', 'list',
                '--repo', search_repo,
                '--head', branch_name,
                '--json', 'number,url,state',
                '--limit', '100'
            ]).decode()
            prs = json.loads(pr_data_raw)
            if prs:
                pr_data.extend(prs)

            # If searching parent/upstream, also try with repo:branch format
            if search_repo != repo:
                head_with_repo = f"{repo.split('/')[0]}:{branch_name}"
                stderr.write(f"Searching for PR in {search_repo} with head {head_with_repo}...\n")
                pr_data_raw = check_output([
                    'gh', 'pr', 'list',
                    '--repo', search_repo,
                    '--head', head_with_repo,
                    '--json', 'number,url,state',
                    '--limit', '100'
                ]).decode()
                prs = json.loads(pr_data_raw)
                if prs:
                    pr_data.extend(prs)
        except CalledProcessError as e:
            stderr.write(f"Error running gh pr list: {e}\n")
            continue
        except json.JSONDecodeError as e:
            stderr.write(f"Error parsing PR data: {e}\n")
            continue

    if not pr_data:
        stderr.write(f"No PR found for branch {branch_name}\n")
        stderr.write(f"Create one with: gh pr create --repo {repo}\n")
        sys.exit(1)

    # Select the appropriate PR
    if len(pr_data) == 1:
        pr_url = pr_data[0]['url']
    else:
        # Multiple PRs - prefer open ones
        stderr.write(f"Multiple PRs found for branch {branch_name}:\n")
        open_prs = [pr for pr in pr_data if pr['state'] == 'OPEN']

        for pr in pr_data:
            stderr.write(f"  #{pr['number']} ({pr['state']}): {pr['url']}\n")

        if open_prs:
            pr_url = open_prs[0]['url']
            stderr.write(f"Using first open PR: #{open_prs[0]['number']}\n")
        else:
            pr_url = pr_data[0]['url']
            stderr.write(f"Using first PR: #{pr_data[0]['number']}\n")

    # Open the PR
    if dry_run:
        print(f"[DRY-RUN] Would open: {pr_url}")
    else:
        stderr.write(f"Opening: {pr_url}\n")
        import webbrowser
        webbrowser.open(pr_url)


if __name__ == '__main__':
    main()