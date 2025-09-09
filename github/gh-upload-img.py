#!/usr/bin/env python
"""Upload images to GitHub Gist and get permanent URLs."""

import sys
import os
from functools import partial
from pathlib import Path
from subprocess import check_output, DEVNULL

# Add current directory to path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gist_upload

err = partial(print, file=sys.stderr)


def get_or_create_gist(gist_id=None, description="Image assets"):
    """Get existing gist ID or create a new one."""
    if gist_id:
        return gist_id

    # Check if we have a gist ID in git config (for PR repos)
    try:
        gist_id = check_output(['git', 'config', 'pr.gist'], stderr=DEVNULL).decode().strip()
        if gist_id:
            err(f"# Using PR gist: {gist_id}")
            return gist_id
    except:
        pass

    # Create a new gist
    err(f"# Creating new gist for assets...")
    gist_id = gist_upload.create_gist(description)
    if gist_id:
        err(f"# Created gist: {gist_id}")
        return gist_id

    err("Error: Could not create gist")
    return None


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Upload images to GitHub Gist and get permanent URLs')
    parser.add_argument('images', nargs='+', help='Image files to upload')
    parser.add_argument('-g', '--gist', help='Gist ID to use (creates new if not specified)')
    parser.add_argument('-b', '--branch', default='assets', help='Branch name in gist (default: assets)')
    parser.add_argument('-f', '--format', choices=['url', 'markdown', 'img', 'auto'], default='auto',
                        help='Output format (default: auto - img for images, url for others)')
    parser.add_argument('-a', '--alt', help='Alt text for markdown/img format')
    parser.add_argument('--local', action='store_true', help='Already in a local clone of the gist')

    args = parser.parse_args()

    # Get or create gist
    gist_id = get_or_create_gist(args.gist)
    if not gist_id:
        sys.exit(1)

    # Prepare files for upload
    files = []
    for image_path in args.images:
        filename = Path(image_path).name
        files.append((image_path, filename))

    # Upload files
    results = gist_upload.upload_files_to_gist(
        files,
        gist_id,
        branch=args.branch,
        is_local_clone=args.local,
        commit_msg=f'Add images'
    )

    # Output formatted results
    for orig_name, safe_name, url in results:
        output = gist_upload.format_output(orig_name, url, args.format, args.alt)
        print(output)

    if not results:
        sys.exit(1)


if __name__ == '__main__':
    main()
