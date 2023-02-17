#!/usr/bin/env python
import shlex
import sys
from os import environ as env
from subprocess import check_output, check_call

import click


def stderr(msg=''):
    sys.stderr.write(msg)
    sys.stderr.write('\n')


@click.command('git-throw')
@click.option('-a', '--all', is_flag=True, help='Commit unstaged as well as staged changes.')
@click.option('-m', '--message', help='Optional message to use for ephemeral commit (before it is squashed onto the commit pointed to by `dst`).')
@click.option('-n', '--dry-run', count=True, help="1x: commit changes, print rebase todo list; 2x: don't commit changes, show simulated rebase todo list")
@click.argument('dst')
def main(all, message, dry_run, dst):
    dst = check_output([ 'git', 'log', '-1', '--format=%h', dst ]).decode().rstrip('\n')
    if not message:
        message = f'Temporary commit, to be squashed into {dst}'

    commit_cmd = [ 'git', 'commit', *(['-a'] if all else []), '-m', message ]
    if dry_run < 2:
        check_call(commit_cmd)
    else:
        stderr(f'Would run: {shlex.join(commit_cmd)}')

    shas = list(reversed([
        line.rstrip('\n')
        for line in check_output([ 'git', 'log', '--format=%h', f'{dst}^..HEAD' ]).decode().split('\n')
        if line
    ]))
    if dry_run >= 2:
        fixup_sha = '<ephemeral commit sha>'
        rest_shas = shas[1:]
    else:
        fixup_sha = shas[-1]
        rest_shas = shas[1:-1]
    lines = [
        f'p {shas[0]}',
        f'f {fixup_sha}',
        *[
            f'p {sha}'
            for sha in rest_shas
        ]
    ]
    todo_list = '\n'.join(lines)
    todo_contents = 'echo "%s" >' % todo_list
    rebase_cmd = [ 'git', 'rebase', '-i', f'{dst}^' ]
    if dry_run:
        stderr(f'Would run: `{shlex.join(rebase_cmd)}` with GIT_SEQUENCE_EDITOR containing:\n{todo_contents}')
    else:
        stderr("todo list:")
        stderr(todo_list)
        stderr()
        stderr(f"{rebase_cmd=}")
        check_call(rebase_cmd, env={ **env, 'GIT_SEQUENCE_EDITOR': todo_contents, })


if __name__ == '__main__':
    main()
