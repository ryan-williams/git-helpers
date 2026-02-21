#!/usr/bin/env python
"""Upload files to a GitHub Gist and get permanent URLs.

Looks up gist ID from git config `assets.gist`, falling back to `pr.gist`
(for ghpr interop). Creates a new secret gist if none is configured, and saves
the ID to `assets.gist` for future uploads.
"""

import sys
import os
from functools import partial
from pathlib import Path
from subprocess import check_call, check_output, CalledProcessError, DEVNULL

# Add current directory to path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gist_upload

err = partial(print, file=sys.stderr)

CONFIG_KEY = 'assets.gist'
FALLBACK_KEY = 'pr.gist'  # ghpr sets this in PR-clone repos


def git_config_get(key):
    """Read a git config value, returning None if unset."""
    try:
        return check_output(['git', 'config', key], stderr=DEVNULL).decode().strip() or None
    except (CalledProcessError, FileNotFoundError):
        return None


def git_config_set(key, value):
    """Set a git config value. Returns True on success."""
    try:
        check_call(['git', 'config', key, value], stderr=DEVNULL)
        return True
    except (CalledProcessError, FileNotFoundError):
        return False


def get_or_create_gist(gist_id=None, description="Asset uploads"):
    """Get existing gist ID or create a new one."""
    if gist_id:
        return gist_id

    # Check git config: primary key, then ghpr fallback
    for key in (CONFIG_KEY, FALLBACK_KEY):
        gist_id = git_config_get(key)
        if gist_id:
            err(f"# Using gist from {key}: {gist_id}")
            return gist_id

    # Create a new secret gist
    err("# Creating new gist for assets...")
    gist_id = gist_upload.create_gist(description)
    if not gist_id:
        err("Error: Could not create gist")
        return None

    err(f"# Created gist: {gist_id}")
    if git_config_set(CONFIG_KEY, gist_id):
        err(f"# Saved gist ID to git config {CONFIG_KEY}")
    else:
        err("# Warning: couldn't save gist ID to git config (not in a git repo?)")
    return gist_id


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Upload files to a GitHub Gist and get permanent URLs')
    parser.add_argument('files', nargs='+', help='Files to upload')
    parser.add_argument('-a', '--alt', help='Alt text for markdown/img format')
    parser.add_argument('-b', '--branch', default='assets', help='Branch name in gist (default: assets)')
    parser.add_argument('-f', '--format', choices=['url', 'markdown', 'img', 'auto'], default='auto',
                        help='Output format (default: auto - markdown for images, url for others)')
    parser.add_argument('-g', '--gist', help='Gist ID to use (creates new if not specified)')
    parser.add_argument('--local', action='store_true', help='Already in a local clone of the gist')

    args = parser.parse_args()

    gist_id = get_or_create_gist(args.gist)
    if not gist_id:
        sys.exit(1)

    files = [(path, Path(path).name) for path in args.files]

    results = gist_upload.upload_files_to_gist(
        files,
        gist_id,
        branch=args.branch,
        is_local_clone=args.local,
        commit_msg='Add assets',
    )

    for orig_name, safe_name, url in results:
        output = gist_upload.format_output(orig_name, url, args.format, args.alt)
        print(output)

    if not results:
        sys.exit(1)


if __name__ == '__main__':
    main()
