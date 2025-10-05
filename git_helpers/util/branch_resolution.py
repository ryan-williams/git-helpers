#!/usr/bin/env python
"""Utility for resolving git branch references."""

from subprocess import check_output, CalledProcessError
from sys import stderr


def resolve_remote_ref(current_branch=None, current_sha=None, verbose=True):
    """
    Resolve which remote ref to use based on current branch and SHA.

    Returns:
        tuple: (ref_name, remote_ref) where ref_name is the branch name to use
               and remote_ref is the full remote reference (e.g., 'origin/branch')
        (None, None) if no ref can be determined

    Raises:
        SystemExit: If multiple remote refs match and are ambiguous
    """
    try:
        # Get current branch and SHA if not provided
        if current_branch is None:
            current_branch = check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode().strip()
        if current_sha is None:
            current_sha = check_output(['git', 'rev-parse', 'HEAD']).decode().strip()

        # Get remote branches that match
        remote_refs = check_output(['git', 'branch', '-r', '--format=%(refname:short)']).decode().strip().split('\n')
        matching_refs = [r for r in remote_refs if r.endswith(f'/{current_branch}')]

        if len(matching_refs) == 1:
            # Extract the actual branch name from the remote ref
            remote_ref = matching_refs[0]
            # Split "remote/branch" and take the branch part
            ref = remote_ref.split('/', 1)[1] if '/' in remote_ref else remote_ref
            if verbose:
                stderr.write(f"Using ref: {ref} (from remote {remote_ref})\n")
            return ref, remote_ref

        elif len(matching_refs) > 1:
            # Multiple matches - check which one points to the same SHA
            matching_sha_refs = []
            for remote_ref in matching_refs:
                try:
                    remote_sha = check_output(['git', 'rev-parse', remote_ref]).decode().strip()
                    if remote_sha == current_sha:
                        matching_sha_refs.append(remote_ref)
                except:
                    pass

            if len(matching_sha_refs) == 1:
                # Exactly one remote ref points to the same SHA
                remote_ref = matching_sha_refs[0]
                ref = remote_ref.split('/', 1)[1] if '/' in remote_ref else remote_ref
                if verbose:
                    stderr.write(f"Using ref: {ref} (from remote {remote_ref} - matches current SHA)\n")
                return ref, remote_ref

            elif len(matching_sha_refs) > 1:
                # Multiple refs point to the same SHA - still ambiguous
                stderr.write(f"Error: Multiple remote refs match current branch '{current_branch}' and SHA:\n")
                for r in matching_sha_refs:
                    stderr.write(f"  - {r}\n")
                stderr.write("Please specify --ref explicitly\n")
                exit(1)

            else:
                # No remote refs match the current SHA
                if verbose:
                    stderr.write(f"Warning: Multiple remote refs match branch name '{current_branch}' but none match current SHA:\n")
                    for r in matching_refs:
                        stderr.write(f"  - {r}\n")
                    stderr.write("Using local branch name as ref\n")
                return current_branch, None

        elif current_branch != 'HEAD':
            # No remote matches, but we're on a real branch - use it anyway
            if verbose:
                stderr.write(f"Using ref: {current_branch} (current branch, no remote match)\n")
            return current_branch, None

        else:
            # Detached HEAD with no matches
            return None, None

    except Exception as e:
        # If anything fails, return None
        if verbose:
            stderr.write(f"Warning: Failed to resolve remote ref: {e}\n")
        return None, None


def get_default_branch(repo=None):
    """Get the default branch for a repository."""
    try:
        if repo:
            cmd = ['gh', 'repo', 'view', repo, '--json', 'defaultBranchRef']
        else:
            cmd = ['gh', 'repo', 'view', '--json', 'defaultBranchRef']

        import json
        result = check_output(cmd).decode()
        data = json.loads(result)
        return data['defaultBranchRef']['name']
    except:
        # Fallback to common defaults
        try:
            # Try to get from remote HEAD
            remote_head = check_output(['git', 'symbolic-ref', 'refs/remotes/origin/HEAD']).decode().strip()
            if remote_head:
                return remote_head.replace('refs/remotes/origin/', '')
        except:
            pass

        # Final fallback
        return 'main'