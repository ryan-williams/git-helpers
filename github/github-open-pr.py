#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "click",
# ]
# ///
"""Open a PR: by number, URL, or branch name (default: current branch)."""

import os
import sys
import re
import json
import webbrowser
from subprocess import check_output, CalledProcessError, DEVNULL
from sys import stderr

# Add parent directory to path for local imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from git_helpers.util.branch_resolution import resolve_remote_ref

from click import argument, command, option


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

        # Try short format (owner/repo); excludes local-path remotes (`../foo`, `/abs/path`)
        m = re.fullmatch(r'(?P<repo>[A-Za-z\d][\w.-]*/[\w.-]+?)(?:\.git)?', url)
        if m:
            return m.group('repo')

        return None
    except:
        return None


def get_parent_repo(repo):
    """Get the GitHub parent (fork upstream) of `repo`, or None."""
    try:
        parent_data = json.loads(check_output(['gh', 'repo', 'view', repo, '--json', 'parent']).decode())
        parent = parent_data.get('parent')
        if parent:
            return f"{parent['owner']['login']}/{parent['name']}"
    except Exception as e:
        stderr.write(f"Warning: could not check for parent of {repo}: {e}\n")
    return None


def get_remotes():
    try:
        return check_output(['git', 'remote']).decode().split()
    except CalledProcessError:
        return []


def get_tracking_remote():
    try:
        upstream = check_output(
            ['git', 'rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'],
            stderr=DEVNULL,
        ).decode().strip()
        return upstream.split('/')[0]
    except CalledProcessError:
        return None


def repo_candidates(remote):
    """GitHub repos derived from `remote` (or all remotes, tracking remote first)."""
    if remote:
        remotes = [remote]
    else:
        remotes = get_remotes()
        tracking = get_tracking_remote()
        if tracking in remotes:
            remotes.remove(tracking)
            remotes.insert(0, tracking)
    repos = []
    for r in remotes:
        repo = get_github_repo_from_remote(r)
        if repo and repo not in repos:
            repos.append(repo)
    return repos


def resolve_explicit_branch(branch):
    """Resolve an explicitly-named branch to (ref_name, remote_ref).

    Unlike `resolve_remote_ref`, never falls back to HEAD-based (points-at)
    resolution: uses the branch's configured upstream, else a unique remote ref
    match, else the current tracking remote.
    """
    try:
        upstream = check_output(
            ['git', 'rev-parse', '--abbrev-ref', '--symbolic-full-name', f'{branch}@{{u}}'],
            stderr=DEVNULL,
        ).decode().strip()
        return upstream.split('/', 1)[1], upstream
    except CalledProcessError:
        pass
    remote_refs = check_output(['git', 'branch', '-r', '--format=%(refname:short)']).decode().split()
    remotes = [rem for rem in get_remotes() if f'{rem}/{branch}' in remote_refs]
    if len(remotes) > 1:
        tracking = get_tracking_remote()
        remote = tracking if tracking in remotes else remotes[0]
        stderr.write(f"Multiple remotes have branch '{branch}' ({', '.join(remotes)}); using {remote}\n")
    elif remotes:
        remote = remotes[0]
    else:
        remote = get_tracking_remote()
        if not remote:
            return None, None
        stderr.write(f"No remote ref matches '{branch}'; assuming remote '{remote}'\n")
    return branch, f'{remote}/{branch}'


def find_pr_by_number(number, repos):
    """Return the URL of PR #`number` in the first of `repos` that has it, else None."""
    for repo in repos:
        try:
            pr = json.loads(check_output(
                ['gh', 'pr', 'view', number, '--repo', repo, '--json', 'url'],
                stderr=DEVNULL,
            ).decode())
            return pr['url']
        except CalledProcessError:
            stderr.write(f"No PR #{number} in {repo}\n")
    return None


def open_pr(pr_url, dry_run):
    if dry_run:
        print(f"[DRY-RUN] Would open: {pr_url}")
    else:
        stderr.write(f"Opening: {pr_url}\n")
        webbrowser.open(pr_url)


@command()
@option('-r', '--remote', help='Specify remote (default: auto-detect)')
@option('-b', '--branch', help='Specify branch (default: current branch)')
@option('-n', '--dry-run', is_flag=True, help='Show what would be done without opening')
@argument('target', required=False)
def main(remote, branch, dry_run, target):
    """Open a PR in the browser.

    TARGET can be a PR number (`7166` or `#7166`), a PR URL, a branch name, or
    a `remote/branch` ref. With no TARGET, uses the current branch.
    """
    if target:
        if re.fullmatch(r'https?://\S+', target):
            open_pr(target, dry_run)
            return

        m = re.fullmatch(r'#?(\d+)', target)
        if m:
            number = m.group(1)
            repos = repo_candidates(remote)
            if not repos:
                stderr.write("Error: no GitHub repos found among git remotes\n")
                sys.exit(1)
            # Probe remote-derived repos first; only if all miss, fall back to
            # their GitHub parents (fork upstreams)
            pr_url = find_pr_by_number(number, repos)
            if not pr_url:
                parents = []
                for repo in repos:
                    parent = get_parent_repo(repo)
                    if parent and parent not in repos and parent not in parents:
                        parents.append(parent)
                pr_url = find_pr_by_number(number, parents)
                repos += parents
            if pr_url:
                open_pr(pr_url, dry_run)
                return
            stderr.write(f"Error: PR #{number} not found in: {', '.join(repos)}\n")
            sys.exit(1)

        # Branch name, possibly `remote/branch`
        if branch:
            stderr.write("Error: pass a branch as TARGET or via -b/--branch, not both\n")
            sys.exit(1)
        first, _, rest = target.partition('/')
        if rest and first in get_remotes():
            remote = remote or first
            branch = rest
        else:
            branch = target

    if branch:
        # Branch named explicitly; don't resolve via HEAD
        if remote:
            ref_name, remote_ref = branch, f'{remote}/{branch}'
        else:
            ref_name, remote_ref = resolve_explicit_branch(branch)
    else:
        try:
            branch = check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode().strip()
            if branch == 'HEAD':
                stderr.write("Error: Not on a branch (detached HEAD)\n")
                sys.exit(1)
        except CalledProcessError:
            stderr.write("Error: Could not determine current branch\n")
            sys.exit(1)
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
    parent_repo = get_parent_repo(repo)
    if parent_repo:
        repos_to_search.append(parent_repo)
        stderr.write(f"Detected parent repo: {parent_repo}\n")

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

    open_pr(pr_url, dry_run)


if __name__ == '__main__':
    main()