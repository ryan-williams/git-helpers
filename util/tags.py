
from subprocess import check_output
from sys import exit

from piece import Pieces

def get_tags(n=None):
    tags = [
        tag
        for tag in
        check_output([ 'git', 'tag', '-l' ]) \
        .decode() \
        .split('\n')
        if tag
    ]
    if n: return tags[:n]
    return tags


def print_recent_tags(n=None):
    tags = get_tags(n)
    if not tags: exit(0)

    pieces = Pieces()
    pieces.parse_log(["--no-walk"] + tags)
    pieces.pretty_print()

