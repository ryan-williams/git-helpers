
import sys

from piece import Pieces

import subprocess

def get_tags():
    return [tag for tag in subprocess.check_output(['git', 'tag', '-l']).decode().split('\n') if tag]


def print_recent_tags():
    tags = get_tags()
    if not tags:
        sys.exit(0)

    pieces = Pieces()
    pieces.parse_log(["--no-walk"] + tags)
    pieces.pretty_print()

