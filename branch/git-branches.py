#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "click",
# ]
# ///
from dataclasses import dataclass
from functools import partial
import re
from subprocess import check_output
from sys import stderr

import click


err = partial(print, file=stderr)


LINE_RGX = re.compile(r'(?P<sha>[0-9a-f]{40})\s+commit\s+refs/(?P<kind>\w+)/(?P<name>.*)')


@dataclass
class Ref:
    sha: str
    kind: str
    name: str


def sh_lines(*cmd):
    lines = list(filter(None, [
        line.rstrip('\n')
        for line in check_output(cmd).decode().split('\n')
    ]))
    return [
        line.rstrip('\n')
        for line in lines
    ]


@click.command()
@click.option('-b', '--before', help='Filter to refs authored before this date')
@click.option("-r", "--remote-glob", help="Filter to refs matching this glob: `refs/remotes/<remote_glob>`")
def main(before, remote_glob):
    cmd = ['git', 'for-each-ref']
    if remote_glob:
        cmd.append(f'refs/remotes/{remote_glob}')

    refs = []
    for line in sh_lines(*cmd):
        m = LINE_RGX.match(line)
        if not m:
            err(f"Unrecognized ref line: {line}")
            continue
        sha = m['sha']
        ref = Ref(sha=sha, kind=m['kind'], name=m['name'])
        if before:
            [date] = sh_lines('git', 'log', '-1', '--format=%ad', '--date=short', sha)
            if date < before:
                refs.append(ref)
        else:
            refs.append(ref)

    for ref in refs:
        print(ref.name)


if __name__ == "__main__":
    main()
