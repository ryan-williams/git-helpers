#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "utz",
# ]
# ///
import shlex
from os import environ as env

from utz import err
from utz import proc
from utz.cli import arg, cmd, flag, opt


@cmd('git-throw')
@flag('-a', '--all', help='Stage all tracked files before committing (pass -a to git commit).')
@opt('-m', '--message', help='Optional message to use for ephemeral commit (before it is squashed onto the commit pointed to by `dst`).')
@opt('-n', '--dry-run', count=True, help="1x: commit changes, print rebase todo list; 2x: don't commit changes, show simulated rebase todo list")
@arg('dst')
def main(all, message, dry_run, dst):
    """"Throw" (squash) uncommitted changes onto an arbitrary previous commit."""
    dst = proc.line('git', 'log', '-1', '--format=%H', dst)
    root = proc.line('git', 'rev-list', '--max-parents=0', 'HEAD')
    if not message:
        message = f'Temporary commit, to be squashed into {dst}'

    commit_cmd = [ 'git', 'commit' ]
    if all:
        commit_cmd.append('-a')
    commit_cmd.extend(['-m', message])
    if dry_run < 2:
        proc.run(commit_cmd)
    else:
        err(f'Would run: {shlex.join(commit_cmd)}')

    if root == dst:
        rebase_args = [ '--root' ]
        log_args = []
    else:
        rebase_args = [ f'{dst}^' ]
        log_args = [ f'{dst}^..HEAD' ]
    shas = list(reversed(
        proc.lines('git', 'log', '--format=%h', *log_args)
    ))
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
    rebase_cmd = [ 'git', 'rebase', '-i', *rebase_args, ]
    if dry_run:
        err(f'Would run: `{shlex.join(rebase_cmd)}` with GIT_SEQUENCE_EDITOR containing:\n{todo_contents}')
    else:
        err("todo list:")
        err(todo_list)
        err()
        err(f"{rebase_cmd=}")
        proc.run(rebase_cmd, env={ **env, 'GIT_SEQUENCE_EDITOR': todo_contents, })


if __name__ == '__main__':
    main()
