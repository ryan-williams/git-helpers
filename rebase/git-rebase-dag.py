#!/usr/bin/env python
import shlex
from functools import partial
from subprocess import check_call, CalledProcessError, check_output
from sys import stderr

import click


def err(msg=''):
    stderr.write(msg)
    stderr.write('\n')


def run(*cmd, log=err, dry_run=False, return_output=False, **kwargs):
    """Wrapper around subprocess.{check_call,check_output}."""
    if dry_run:
        if log:
            log(f'DRY RUN: would run {shlex.join(cmd)}')
        return
    else:
        if log:
            log(f'Running: {shlex.join(cmd)}')
    if return_output:
        return check_output(cmd, **kwargs).decode()
    else:
        check_call(cmd, **kwargs)


output = partial(run, return_output=True)


def lines(*cmd, log=err, dry_run=False, rm_trailing_blank=True, **kwargs):
    """Call subprocess.check_output, split output into lines."""
    if dry_run:
        if log:
            log(f'DRY RUN: would run {shlex.join(cmd)}')
        return
    else:
        if log:
            log(shlex.join(cmd))
    lns = [ ln.rstrip('\n') for ln in check_output(cmd, **kwargs).decode().split('\n') ]
    if rm_trailing_blank and lns[-1] == '':
        return lns[:-1]
    else:
        return lns


def line(*cmd, log=err, dry_run=False, **kwargs):
    """Call subprocess.check_output, verify + return a single line of output."""
    lns = lines(*cmd, log=log, dry_run=dry_run, **kwargs)
    if dry_run:
        return
    elif len(lns) == 1:
        return lns[0]
    else:
        raise ValueError(f'Cmd {cmd} returned {len(lns)} lines:' + "\n\t" + "\n\t".join(lns))


def get_sha(ref=None, **kwargs):
    return line('git', 'log', '-1', '--format=%H', *([ref] if ref else []), **kwargs)


@click.command(help='Rebase a DAG of Git commits onto a new base commit. -b/--base and -o/--onto commits must have identical trees (which also ensures no conflicts arise)')
@click.option('-b', '--base', help='Current base commit (likely the parent of the root of the DAG you want to rebase onto)')
@click.option('-n', '--dry-run', is_flag=True, help="")
@click.option('-o', '--onto')
@click.argument('branch')
def main(base, dry_run, onto, branch):
    try:
        run('git', 'diff', '--quiet', f'{base}..{onto}')
    except CalledProcessError:
        raise RuntimeError(f"Git trees don't match: {base} != {onto}")

    shas = list(filter(None, lines('git', 'log', '--format=%H', '--reverse', '--topo-order', f'{base}..{branch}')))
    print('\n'.join(shas))
    run('git', 'checkout', branch, dry_run=dry_run)
    run('git', 'reset', '--hard', onto, dry_run=dry_run)
    base_sha = get_sha(base)
    onto_sha = get_sha(onto)
    rebased_commits = { base_sha: onto_sha }
    for sha in shas:
        parents = check_output([ 'git', 'rev-list', '--parents', '-n1', sha ]).decode().rstrip('\n').split(' ')[1:]
        for parent in parents:
            if parent not in rebased_commits:
                raise RuntimeError(f"{sha}'s parent {parent} not found in rebased_commits {rebased_commits}")
        rebased_parents = [ rebased_commits[parent] for parent in parents ]
        tree = line('git', 'log', '-1', '--format=%T', sha)
        body = output('git', 'log', '-1', '--format=%B', sha)
        commit_tree_cmd = ['git', 'commit-tree', tree, '-m', body]
        for parent in rebased_parents:
            commit_tree_cmd += [ '-p', parent ]
        new_sha_wip = line(*commit_tree_cmd, dry_run=dry_run)
        err(f'WIP new SHA: {sha} -> {new_sha_wip}')
        run('git', 'reset', '--hard', new_sha_wip)
        run('git', 'commit', '--amend', '--allow-empty', '-C', sha, dry_run=dry_run)
        new_sha = get_sha(dry_run=dry_run)
        err(f'New SHA: {sha} -> {new_sha}')
        rebased_commits[sha] = new_sha


if __name__ == '__main__':
    main()
