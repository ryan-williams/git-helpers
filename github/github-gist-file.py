#!/usr/bin/env python
"""Upload files to GitHub gist preserving their original names."""

import sys
import os
import argparse
import json
from subprocess import check_output, check_call, CalledProcessError, DEVNULL
from pathlib import Path


def create_gist_with_files(files, description=None, private=False, open_browser=False):
    """Create a gist with multiple files."""

    # Build the gist creation command
    cmd = ['gh', 'gist', 'create']

    if description:
        cmd.extend(['--desc', description])

    # gh gist create defaults to private, use --public for public gists
    if not private:
        cmd.append('--public')

    # Open in browser if requested
    if open_browser:
        cmd.append('--web')

    # Add all files
    for filepath in files:
        if not Path(filepath).exists():
            print(f"Error: File not found: {filepath}", file=sys.stderr)
            return None
        cmd.append(filepath)

    try:
        # Create the gist
        output = check_output(cmd).decode().strip()
        return output
    except CalledProcessError as e:
        print(f"Error creating gist: {e}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Upload files to GitHub gist preserving their original names'
    )
    parser.add_argument('files', nargs='+', help='Files to upload')
    parser.add_argument('-d', '--description', help='Gist description')
    parser.add_argument('-o', '--open', action='store_true',
                        help='Open gist in browser after creation')
    parser.add_argument('-p', '--private', action='store_true',
                        help='Create private gist (default: public)')

    args = parser.parse_args()

    # Default description if not provided
    if not args.description:
        if len(args.files) == 1:
            args.description = Path(args.files[0]).name
        else:
            args.description = f"{len(args.files)} files"

    # Create the gist
    gist_url = create_gist_with_files(
        args.files,
        description=args.description,
        private=args.private,
        open_browser=args.open
    )

    if gist_url:
        print(gist_url)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()