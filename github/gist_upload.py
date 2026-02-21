#!/usr/bin/env python
"""Shared library for uploading files to GitHub Gists."""

import sys
import os
import re
import tempfile
import shutil
from functools import partial
from subprocess import check_output, check_call, run, CalledProcessError, DEVNULL, PIPE
from pathlib import Path
from urllib.parse import quote


err = partial(print, file=sys.stderr)


def run_quiet(cmd, **kwargs):
    """Run a command, suppressing stderr unless it fails."""
    result = run(cmd, stderr=PIPE, **kwargs)
    if result.returncode != 0:
        stderr_text = result.stderr.decode().strip() if result.stderr else ''
        if stderr_text:
            err(stderr_text)
        raise CalledProcessError(result.returncode, cmd)
    return result


def get_github_username():
    """Get the current GitHub username."""
    try:
        return check_output(['gh', 'api', 'user', '--jq', '.login']).decode().strip()
    except:
        # Try to extract from gist info if we have a gist_id
        return None


def get_gist_remote_name(gist_id):
    """Find the remote name for a gist repository."""
    try:
        # Get all remotes
        remotes = check_output(['git', 'remote']).decode().strip().split('\n')
        for remote in remotes:
            if not remote:
                continue
            try:
                url = check_output(['git', 'remote', 'get-url', remote], stderr=DEVNULL).decode().strip()
                if f'gist.github.com:{gist_id}' in url or f'gist.github.com/{gist_id}' in url:
                    return remote
            except:
                continue
    except:
        pass
    # Default to 'origin' if not found
    return 'origin'


def create_gist(description="Image assets", content="# Image Assets\nThis gist stores image assets.\n"):
    """Create a new gist and return its ID."""
    try:
        output = check_output([
            'gh', 'gist', 'create',
            '--desc', description,
            '-'
        ], input=content.encode()).decode().strip()

        # Extract gist ID from URL (may include username: gist.github.com/user/hash)
        match = re.search(r'gist\.github\.com/(?:[^/]+/)?([a-f0-9]+)', output)
        if match:
            return match.group(1)
    except CalledProcessError as e:
        err(f"Error creating gist: {e}")
    return None


def upload_files_to_gist(files, gist_id, branch='assets', is_local_clone=False, commit_msg=None, verbose=True, remote_name=None):
    """
    Upload files to a gist branch.

    Args:
        files: List of (source_path, target_name) tuples
        gist_id: Gist ID to upload to
        branch: Branch name (default: 'assets')
        is_local_clone: True if we're already in a clone of this gist
        commit_msg: Custom commit message (optional)
        verbose: Print progress messages
        remote_name: Name of the remote (auto-detected if not provided)

    Returns:
        List of (original_name, safe_name, url) tuples
    """
    if not gist_id:
        err("Error: No gist ID provided")
        return []

    # Get GitHub username
    user = get_github_username()
    if not user:
        err("Error: Could not determine GitHub username")
        return []

    # Prepare file mappings
    file_mapping = []
    for source_path, target_name in files:
        if not Path(source_path).exists():
            err(f"Error: File not found: {source_path}")
            continue

        # Keep original filename - Git handles special characters
        file_mapping.append((source_path, target_name, target_name))

    if not file_mapping:
        return []

    results = []

    if is_local_clone:
        # We're already in the gist repo, create assets on a separate branch without changing HEAD
        temp_dir = tempfile.mkdtemp(prefix='assets_')

        # Get the remote name if not provided
        if not remote_name:
            remote_name = get_gist_remote_name(gist_id)
            if verbose:
                err(f"Using remote '{remote_name}'")

        try:
            # Copy files to temp directory with sanitized names
            temp_files = []
            for source_path, orig_name, safe_name in file_mapping:
                temp_path = Path(temp_dir) / safe_name
                shutil.copy2(source_path, temp_path)
                temp_files.append((orig_name, safe_name, temp_path))
                if verbose:
                    err(f"Staged {orig_name}")

            # Check if branch exists on remote
            try:
                output = check_output(['git', 'ls-remote', '--heads', remote_name, branch], stderr=DEVNULL).decode().strip()
                branch_exists = bool(output)  # Empty output means branch doesn't exist
            except:
                branch_exists = False

            if branch_exists:
                # Fetch the branch without checking it out
                check_call(['git', 'fetch', remote_name, f'{branch}:{branch}'], stderr=DEVNULL)
                if verbose:
                    err(f"Fetched existing branch '{branch}'")
                parent_ref = branch
            else:
                # Create orphan commit for new branch
                if verbose:
                    err(f"Creating new branch '{branch}'")
                parent_ref = None

            # Build tree with all files
            tree_entries = []

            # Get existing tree if we have a parent
            if parent_ref:
                try:
                    existing_tree = check_output(['git', 'ls-tree', parent_ref], stderr=DEVNULL).decode()
                    # Keep existing files that we're not replacing
                    new_files = {safe_name for _, safe_name, _ in temp_files}
                    for line in existing_tree.strip().split('\n'):
                        if line:
                            parts = line.split('\t', 1)
                            if len(parts) == 2:
                                filename = parts[1]
                                if filename not in new_files:
                                    tree_entries.append(line)
                except:
                    pass

            # Add new/updated files
            for orig_name, safe_name, temp_path in temp_files:
                blob_hash = check_output(['git', 'hash-object', '-w', str(temp_path)]).decode().strip()
                tree_entries.append(f'100644 blob {blob_hash}\t{safe_name}')

            # Create tree
            tree_input = '\n'.join(tree_entries) + '\n'
            tree_hash = check_output(['git', 'mktree'], input=tree_input.encode()).decode().strip()

            # Create commit
            if not commit_msg:
                commit_msg = f'Add assets'
            commit_cmd = ['git', 'commit-tree', tree_hash, '-m', commit_msg]
            if parent_ref:
                commit_cmd.extend(['-p', parent_ref])
            commit_hash = check_output(commit_cmd).decode().strip()

            # Update branch ref
            check_call(['git', 'update-ref', f'refs/heads/{branch}', commit_hash])

            # Push the branch
            run_quiet(['git', 'push', remote_name, f'{branch}:{branch}'])
            if verbose:
                err(f"Pushed to branch '{branch}'")

            # Build results - use commit SHA instead of branch name for gist URLs
            for orig_name, safe_name, _ in temp_files:
                # URL-encode the filename for the URL
                encoded_name = quote(safe_name)
                url = f"https://gist.githubusercontent.com/{user}/{gist_id}/raw/{commit_hash}/{encoded_name}"
                results.append((orig_name, safe_name, url))
                if verbose:
                    err(f"Uploaded: {url}")

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    else:
        # Need to clone the gist
        temp_dir = tempfile.mkdtemp(prefix='gist_')

        try:
            gist_url = f"git@gist.github.com:{gist_id}.git"
            run_quiet(['git', 'clone', gist_url, temp_dir])

            os.chdir(temp_dir)

            # Detect the clone's remote name (respects clone.defaultRemoteName)
            clone_remote = check_output(['git', 'remote']).decode().strip().split('\n')[0]

            # Create or switch to branch
            try:
                run_quiet(['git', 'checkout', '-b', branch])
                if verbose:
                    err(f"Created branch '{branch}'")
            except CalledProcessError:
                try:
                    run_quiet(['git', 'checkout', branch])
                    if verbose:
                        err(f"Using existing branch '{branch}'")
                except CalledProcessError:
                    if verbose:
                        err(f"Warning: Could not checkout branch '{branch}', using main")
                    branch = 'main'

            # Copy and add files
            for source_path, orig_name, safe_name in file_mapping:
                shutil.copy2(source_path, safe_name)
                check_call(['git', 'add', safe_name])
                if verbose:
                    err(f"Added {orig_name}")

            # Commit and push
            if not commit_msg:
                commit_msg = f'Add assets'
            run_quiet(['git', 'commit', '-m', commit_msg])
            run_quiet(['git', 'push', clone_remote, branch])

            # Get the commit hash for the URL
            commit_hash = check_output(['git', 'rev-parse', 'HEAD']).decode().strip()

            # Build results - use commit SHA instead of branch name for gist URLs
            for _, orig_name, safe_name in file_mapping:
                # URL-encode the filename for the URL
                encoded_name = quote(safe_name)
                url = f"https://gist.githubusercontent.com/{user}/{gist_id}/raw/{commit_hash}/{encoded_name}"
                results.append((orig_name, safe_name, url))
                if verbose:
                    err(f"Uploaded: {url}")

        finally:
            # Clean up
            original_dir = Path.cwd().parent if Path.cwd().name.startswith('gist_') else Path.cwd()
            os.chdir(original_dir)
            shutil.rmtree(temp_dir, ignore_errors=True)

    return results


def format_output(filename, url, format_type='auto', alt_text=None):
    """
    Format the output based on file type and format preference.

    Args:
        filename: Original filename
        url: URL to the file
        format_type: 'url', 'markdown', 'img', or 'auto'
        alt_text: Alt text for markdown/img formats

    Returns:
        Formatted string
    """
    if not alt_text:
        alt_text = filename

    # Determine output format
    output_format = format_type
    if format_type == 'auto':
        # Check if it's an image based on extension
        ext = Path(filename).suffix.lower()
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.bmp'}

        if ext in image_extensions:
            output_format = 'markdown'  # Default to markdown for images
        else:
            # Try using mimetypes as fallback
            import mimetypes
            mime_type, _ = mimetypes.guess_type(filename)
            if mime_type and mime_type.startswith('image/'):
                output_format = 'markdown'  # Default to markdown for images
            else:
                output_format = 'url'  # Just URL for non-images

    if output_format == 'url':
        return url
    elif output_format == 'markdown':
        return f'![{alt_text}]({url})'
    elif output_format == 'img':
        return f'<img alt="{alt_text}" src="{url}" />'
    else:
        return url