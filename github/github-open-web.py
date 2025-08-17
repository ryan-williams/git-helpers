#!/usr/bin/env python
"""Open GitHub repository in web browser on the current branch."""

import json
import os
import sys
from subprocess import check_output, check_call, CalledProcessError
from sys import stderr

# Add parent directory to path to import util modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from util.branch_resolution import resolve_remote_ref, get_default_branch

import click


@click.command('github-open-web')
@click.option('-b', '--branch', help='Branch to open (defaults to current branch)')
@click.option('-d', '--default', is_flag=True, help='Open default branch')
@click.option('-r', '--repo', help='Repository (owner/name format)')
def github_open_web(branch, default, repo):
    """Open GitHub repository in web browser on the appropriate branch."""
    
    # Build the gh command
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
        stderr.write(f"Error: Failed to open repository: {e}\n")
        exit(1)


if __name__ == '__main__':
    github_open_web()