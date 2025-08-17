#!/usr/bin/env python
"""Open GitHub repository or gist in web browser."""

import json
import os
import re
import sys
from subprocess import check_output, check_call, CalledProcessError, DEVNULL
from sys import stderr

# Add parent directory to path to import util modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from util.branch_resolution import resolve_remote_ref, get_default_branch

import click


def is_gist_repo():
    """Check if current repository is a gist."""
    try:
        # Gist repos have URLs like git@gist.github.com:ID.git
        remotes = check_output(['git', 'remote', '-v'], stderr=DEVNULL).decode()
        return 'gist.github.com' in remotes
    except:
        return False


def get_gist_id():
    """Extract gist ID from remote URL."""
    try:
        # Try to get the first remote that looks like a gist
        remotes = check_output(['git', 'remote'], stderr=DEVNULL).decode().strip().split('\n')
        for remote in remotes:
            if not remote:
                continue
            try:
                url = check_output(['git', 'remote', 'get-url', remote], stderr=DEVNULL).decode().strip()
                # Match patterns like:
                # git@gist.github.com:1234567890abcdef.git
                # https://gist.github.com/1234567890abcdef.git
                # https://gist.github.com/username/1234567890abcdef
                match = re.search(r'gist\.github\.com[:/](?:[\w-]+/)?([a-f0-9]+)', url)
                if match:
                    return match.group(1)
            except:
                continue
    except:
        pass
    return None


@click.command('github-open-web')
@click.option('-b', '--branch', help='Branch to open (defaults to current branch)')
@click.option('-d', '--default', is_flag=True, help='Open default branch')
@click.option('-r', '--repo', help='Repository (owner/name format) or gist ID')
@click.option('-g', '--gist', is_flag=True, help='Force gist mode')
def github_open_web(branch, default, repo, gist):
    """Open GitHub repository or gist in web browser."""

    # Check if this is a gist or if gist mode is forced
    if gist or (not repo and is_gist_repo()):
        # Handle gist mode
        if repo:
            # User provided a gist ID
            gist_id = repo
        else:
            # Try to get gist ID from current repo
            gist_id = get_gist_id()
            if not gist_id:
                stderr.write("Error: Could not determine gist ID from repository\n")
                exit(1)

        stderr.write(f"Opening gist: {gist_id}\n")
        cmd = ['gh', 'gist', 'view', '--web', gist_id]
    else:
        # Regular repository mode
        cmd = ['gh', 'repo', 'view', '--web']

        if repo:
            cmd.extend(['-R', repo])

        if default:
            # Just open the default branch (gh does this by default)
            pass
        elif branch:
            # Use specified branch
            cmd.extend(['-b', branch])
        else:
            # Try to determine the appropriate branch
            try:
                # Get the default branch for comparison
                default_branch = get_default_branch(repo)

                # Get current branch
                current_branch = check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode().strip()

                # If we're on the default branch, no need to specify
                if current_branch == default_branch:
                    stderr.write(f"Opening default branch: {default_branch}\n")
                else:
                    # Try to resolve which remote ref to use
                    ref, remote_ref = resolve_remote_ref(verbose=False)

                    if ref:
                        # We found a matching remote ref
                        stderr.write(f"Opening branch: {ref}")
                        if remote_ref:
                            stderr.write(f" (from remote {remote_ref})")
                        stderr.write("\n")
                        cmd.extend(['-b', ref])
                    else:
                        # No remote ref found, use current branch name
                        stderr.write(f"Opening branch: {current_branch} (local branch, no remote match)\n")
                        cmd.extend(['-b', current_branch])

            except CalledProcessError as e:
                stderr.write(f"Warning: Failed to determine branch: {e}\n")
                stderr.write("Opening repository default view\n")
            except Exception as e:
                stderr.write(f"Warning: Unexpected error: {e}\n")
                stderr.write("Opening repository default view\n")

    # Execute the command
    try:
        check_call(cmd)
    except CalledProcessError as e:
        stderr.write(f"Error: Failed to open: {e}\n")
        exit(1)


if __name__ == '__main__':
    github_open_web()