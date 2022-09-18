#!/usr/bin/env python

from sys import stderr

import click
from utz import cd, process


@click.command()
@click.option('-n', '--dry-run', is_flag=True)
@click.option('-o', '--orig-submodule-head', )
@click.option('-v', '--verbose', is_flag=True)
@click.argument('submodule', required=False)
def main(
        dry_run,
        orig_submodule_head,
        verbose,
        submodule,
):
    if not submodule:
        submodule = process.line('git', 'diff', '--name-only', '--diff-filter=UU')

    def log(msg):
        if verbose:
            stderr.write(msg)
            stderr.write('\n')

    rebase_head = process.line('git', 'rebase-head')
    rebase_head_msg = process.line('git', 'log', '-n1', '--format=%s', rebase_head)

    log_lines = process.lines('git', 'log', '-p', '-n1', '--submodule=log', rebase_head, '--', submodule)
    scan_state = 'skipping'
    new_commit_msgs = []
    old_commit_msgs = []
    for line in log_lines:
        if scan_state == 'skipping':
            if line.startswith('Submodule '):
                scan_state = 'new_commit_msgs'
            continue

        line = line.lstrip()
        if scan_state == 'new_commit_msgs':
            if line.startswith('> '):
                new_commit_msgs.append(line[len('> '):])
                continue
            elif line.startswith('< '):
                scan_state = 'old_commit_msgs'
            else:
                raise RuntimeError(f'Unrecognized log line in {rebase_head}: {line}')

        if scan_state == 'old_commit_msgs':
            if line.startswith('< '):
                old_commit_msgs.append(line[len('> '):])
            else:
                raise RuntimeError(f'Unrecognized log line in {rebase_head}: {line}')

    # Forward-chron order is easier for processing
    old_commit_msgs = old_commit_msgs[::-1]
    new_commit_msgs = new_commit_msgs[::-1]

    # Print summary of parent commit (iff -v/--verbose)
    log(f"Parent commit: {rebase_head}: \"{rebase_head_msg}\"")
    for msg in reversed(new_commit_msgs):
        log(f'  > {msg}')
    for msg in reversed(old_commit_msgs):
        log(f'  < {msg}')

    num_old_commits = len(old_commit_msgs)
    num_new_commits = len(new_commit_msgs)

    if num_old_commits >= num_new_commits:
        raise RuntimeError(f"Can only operate on rewinds followed by longer fast-forwards; found {num_old_commits} rewinds but only {num_new_commits} replacement/new commits")

    if old_commit_msgs:
        found = False
        for i in range(num_new_commits - num_old_commits):
            if old_commit_msgs[0] == new_commit_msgs[i]:
                found = True
                break
        if not found:
            raise RuntimeError(f"First old commit msg {old_commit_msgs[0]} not found among first {num_new_commits - num_old_commits} new commits")
        num_rebased_commits = i
    else:
        num_rebased_commits = 0

    num_net_commits = num_new_commits - num_old_commits - num_rebased_commits
    if num_rebased_commits:
        log(f'{num_rebased_commits} new rebased commits:')
        for msg in new_commit_msgs[:num_rebased_commits]:
            log(f'  > {msg}')

    # Verify the rewinds are matched exactly by new commits
    for old_msg, new_msg in zip(old_commit_msgs, new_commit_msgs[num_rebased_commits:]):
        if old_msg != new_msg:
            raise RuntimeError(f"Submodule {submodule}: rewound commit msg \"{old_msg}\" doesn't match reapplied commit msg \"{new_msg}\"")

    if not orig_submodule_head:
        orig_parent_head = process.line('git', 'original-head')
        orig_submodule_head = process.line('git', 'ls-tree', '--object-only', orig_parent_head, submodule)

    with cd(submodule):
        num_parents_to_include = num_old_commits + num_rebased_commits
        if num_parents_to_include:
            head_delta = max(0, num_parents_to_include - 1)
            submodule_first_commit = f'HEAD~{head_delta}^!'
            log_args = (submodule_first_commit, orig_submodule_head)
        else:
            log_args = (f'HEAD..{orig_submodule_head}',)
        submodule_sha_msg_lines = list(reversed(process.lines('git', 'log', '--topo-order', '--format=%h %s', *log_args)))
        sha_msgs = [
            line.split(' ', 1)
            for line in submodule_sha_msg_lines
        ]

    submodule_commits = [
        dict(sha=sha, msg=msg)
        for sha, msg in sha_msgs
    ]

    if len(submodule_commits) < num_new_commits:
        raise RuntimeError(f'Expected {num_old_commits} old commits and {num_new_commits} new commits in submodule {submodule}, but only found {len(submodule_commits)} in range `{log_args}`')

    for idx, (submodule_commit, expected_msg) in enumerate(zip(submodule_commits, new_commit_msgs)):
        actual_msg = submodule_commit['msg']
        if actual_msg != expected_msg:
            msg = f'Submodule commit {submodule_commit["sha"]}: msg "{actual_msg}" != "{expected_msg}" from parent commit'
            stderr.write(f'{msg}\n\n')
            stderr.write('submodule_commits:\n')
            stderr.write("\t" + "\n\t".join([ commit['msg'] for commit in submodule_commits]))
            stderr.write("\n\n")
            stderr.write('new_commit_msgs:\n')
            stderr.write("\t" + "\n\t".join(new_commit_msgs))
            stderr.write("\n\n")
            raise RuntimeError(msg)

    new_commit = submodule_commits[len(new_commit_msgs) - 1]
    new_sha = new_commit['sha']
    log(f'Found new commit: {new_sha}')
    if dry_run:
        print(f'Dry run! Would fast-forward submodule {submodule} {num_net_commits} commits, to {new_sha} ("{new_commit["msg"]}"):')
        for msg in reversed(new_commit_msgs[-num_net_commits:]):
            print(f'  > {msg}')
        #', skipping {num_old_commits} rewinds and integrating {num_new_commits} new commits from parent SHA {rebase_head}'
    else:
        with cd(submodule):
            process.run('git', 'checkout', new_sha)


if __name__ == '__main__':
    main()
