#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "click",
#     "utz",
# ]
# ///

import click
from utz import cd, process
from utz.process import check, lines, run


def parse_submodule_commits(ref, submodule):

    skipping = True
    for line in lines('git', 'show', '--submodule=log', ref, '--', submodule):
        if line.startswith('Submodule '):
            skipping = False
            continue
        elif skipping:
            continue




@click.command()
@click.option('-b', '--base', help='')
@click.option('-n', '--new', help='')
@click.option('-p', '--parent', help='')
@click.argument('submodule')
def main(base, new, parent, submodule):
    # [ first, *rest ] = lines('git', 'log', '--format=%h %s', f'{base}^')
    # rebase_lines = [
    #     f'edit {first}',
    #     *[ f'pick {line}' for line in rest ],
    # ]

    if not new:
        ls_tree_line = process.line('git', 'ls-tree', 'HEAD', submodule)
        [ mode, tpe, sha, name ] = list(filter(None, ls_tree_line.split(' ')))
        if tpe != 'commit' or name != submodule:
            raise RuntimeError(f'Unrecognized output from `git ls-tree HEAD {submodule}`: {ls_tree_line}')
        new = sha

    if not parent:
        parent = f'{base}^'

    hashes = lines('git', 'log', '--format=%H', f'{parent}..{new}', '--', submodule)

    sed_cmd = "sed -i -e '1s/^pick/edit/'"  # edit the first commit
    run(
        'git', 'rebase', '-i', parent,
        env={
            'EDITOR': sed_cmd,
            'GIT_SEQUENCE_EDITOR': sed_cmd,
        }
    )
    while True:
        if check('git', 'rebase', '--continue'):
            # Rebase continued successfully to completion! We are done here.
            break

        with cd(submodule):
            run('git', 'checkout', TODO)

        run('git', 'add', submodule)

if __name__ == '__main__':
    main()
