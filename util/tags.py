from subprocess import check_output
from sys import exit, stderr

from piece import Pieces


def get_tags(n=None):
    cmd = [
        'git', 'tag',
        '-l',
        '--format=%(refname:short)',
        '--sort=-creatordate',
    ]
    # stderr.write(f"Running: {' '.join(cmd)}\n")
    tags = [
        tag
        for tag in (
            check_output(cmd)
            .decode()
            .split('\n')
        ) if tag
    ]
    if n:
        tags = tags[:n]
    return tags


def print_recent_tags(n=None):
    tags = get_tags(n)
    if not tags:
        exit(0)

    pieces = Pieces()
    pieces.parse_log(["--no-walk"] + tags)
    pieces.pretty_print()
