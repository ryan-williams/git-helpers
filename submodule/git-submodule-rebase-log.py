#!/usr/bin/env python
#
# Visualize relevant commits in a conflicted submodule (e.g. during a rebase)
#
# During a rebase, there are a few relevant "heads":
# - ONTO: the "upstream" commit that a series of commits are beinb rebased "on to"
# - REBASE_HEAD: the original commit currently being "cherrypicked" over onto a new "ONTO"
# - HEAD: the current commit (last rebased commit) that REBASE_HEAD is being cherrypicked onto (this will be ONTO plus
#   the rebased/"cherrypicked" commits that have been completed so far during this rebase)
# - ORIG_HEAD: the branch being rebased; desired end state is this commit, but rebased onto ONTO
# - MERGE_BASE: common ancestor of ORIG_HEAD and ONTO; the whole rebase can be thought of as a sequence of cherrypicks
#   of the commit range MERGE_BASE..ORIG_HEAD onto the "new base" ONTO.
#
# Summarizing the last point, a rebase can generally be approximated with the following pseudocode:
# - starting from ORIG_HEAD…
# - git checkout ONTO
# - for REBASE_HEAD in MERGE_BASE..ORIG_HEAD:
#       # - HEAD is the current commit, that REBASE_HEAD is about to be "rebased" (cherrypicked) onto
#       # - REBASE_HEAD is the commit about to be cherrypicked
#       git cherrypick REBASE_HEAD
#
# This script helps to visualize all these commits when rebasing a repo that contains submodules, where one or more
# submodules runs into a rebase conflict:
#
# - find the first conflicted submodule
# - look up all the above "heads" in the parent repo
# - see what commit the conflicted submodule is at for each parent head
# - put ephemeral tags into the submodule repo itself, reflecting the relevant parent heads
#   - these tags get prefixed with "parent/", e.g. "parent/ORIG_HEAD", "parent/REBASE_HEAD", etc.
# - run a `git graph` in the submodule, that shows a graph of how all the parent's pointers relate
# - clean up the ephemeral tags / exit


from os import chdir, getcwd
from os.path import expanduser
import re
from subprocess import CalledProcessError, DEVNULL, check_call, check_output
import sys

from click import command, option, argument


def read_sha(name):
    with open(f'.git/{name}', 'r') as f:
        return f.read().strip()


def output(*args):
    return check_output(args).decode().strip()


def lines(*args):
    return output(*args).split('\n')


def get_shas_for_head(parent_sha, submodule):
    child = re.split('\s+', output('git', 'ls-tree', parent_sha, submodule), 3)[2]
    return dict(
        parent=parent_sha,
        child=child,
    )


def stderr(*args):
    for arg in args:
        sys.stderr.write('%s\n' % arg)


class cd:
    """Context manager for changing the current working directory"""
    def __init__(self, path):
        self.path = expanduser(path)

    def __enter__(self):
        self.prevPath = getcwd()
        chdir(str(self.path))

    def __exit__(self, etype, value, traceback):
        chdir(str(self.prevPath))


@command()
@option('-v', '--verbose', is_flag=True, help='Debug log to stderr')
@argument('submodule', required=False)
def main(submodule, verbose):
    if verbose:
        err = stderr
    else:
        def err(*args): pass

    if not submodule:
        submodules = [ line[3:] for line in lines('git', 'status', '--porcelain') if line.startswith('UU') ]
        if not submodules:
            err('No conflicted submodules found')
            return
        elif len(submodules) > 1:
            submodule = submodules[0]
            err(f'Inspecting first conflicted submodule: {submodule}')
            # raise RuntimeError(f'{len(submodules)} conflicted submodules found, unsure which to choose')
        else:
            [submodule] = submodules

    rebase_head = read_sha('REBASE_HEAD')
    orig_head = read_sha('ORIG_HEAD')
    head = read_sha('HEAD')
    onto = read_sha('rebase-merge/onto')

    merge_base = output('git', 'merge-base', rebase_head, head)

    heads = {
        name: get_shas_for_head(parent_sha, submodule)
        for name, parent_sha in {
            'REBASE_HEAD': rebase_head,
            'ORIG_HEAD': orig_head,
            'HEAD': head,
            'ONTO': onto,
            'BASE': merge_base,
        }.items()
    }

    with cd(submodule):
        tags = []
        try:
            for name, shas in heads.items():
                tag = f'parent/{name}'
                parent_sha = shas['parent']
                child_sha = shas['child']
                err(f'{name}: parent {parent_sha}, {submodule} {child_sha}')
                check_call([ 'git', 'tag', tag, child_sha, ])
                tags.append(tag)

            check_call([ 'git', 'graph', 'HEAD', ] + tags)
        except CalledProcessError as e:
            if e.returncode == 141:
                err(f'Suppressing returncode 141 from `git graph`; most likely a SIGPIPE artifact due to using `less +%S` as Git pager, cf. https://www.ingeniousmalarkey.com/2016/07/git-log-exit-code-141.html')
            else:
                raise
        finally:
            fd = None if verbose else DEVNULL
            for tag in tags:
                check_call(['git', 'tag','-d', tag], stderr=fd, stdout=fd)



if __name__ == '__main__':
    main()
