#!/usr/bin/env python
import json
import sys
from subprocess import Popen, check_output
from tempfile import TemporaryDirectory

import click


@click.command()
@click.option('-a', '--after', help='"After" ref; default: current work-tree')
@click.option('-b', '--before', help='"Before" ref; default: HEAD (if no -a/--after is provided), otherwise `after`^ (the parent commit of `after`)')
@click.argument('path')
def main(before, after, path):
    if after:
        if not before:
            # after^..after
            before = f'{after}^'
    elif not before:
        #  HEAD..<worktree>
        before = 'HEAD'

    with TemporaryDirectory() as tmpdir:
        before_path = f'{tmpdir}/before.json'
        with open(before_path, 'w') as f:
            json.dump(json.loads(check_output(['git', 'show', f'{before}:{path}'])), f, indent=4)

        after_path = f'{tmpdir}/after.json'
        with open(after_path, 'w') as f:
            if after:
                after_json = json.loads(check_output(['git', 'show', f'{before}:{path}']))
            else:
                with open(path, 'r') as worktree:
                    after_json = json.load(worktree)
            json.dump(after_json, f, indent=4)

        diff = Popen(['diff', before_path, after_path])
        diff.wait()
        sys.exit(diff.returncode)


if __name__ == '__main__':
    main()
