#!/usr/bin/env python

from os import chdir, getcwd
from pathlib import Path
from subprocess import check_call as sh
from sys import exit

from repos import repos as get_repos


if __name__ == '__main__':
    # Parse args
    from argparse import ArgumentParser
    parser = ArgumentParser(add_help=False)
    parser.add_argument('org',help='GitHub organization to list repos for')
    parser.add_argument('dir',nargs='?',help='Directory to clone <org> into (default: <org>)')
    parser.add_argument('-h','--https',action='store_true',help='When set, clone with HTTPS URLs (default: SSH)')
    parser.add_argument('--help', action='help', help='Show this help message and exit')
    parser.add_argument('-j','--num-jobs',default=-1,type=int,help='"clone" concurrency')
    parser.add_argument('-n','--dry-run',action='store_true',help="When set, print repos that would be cloned, but don't clone them")
    parser.add_argument('-q','--quiet',action='store_true',help="When set, suppress logging output")
    parser.add_argument('-S','--no-submodules',action='store_true',help='When set, clone repos but do not make them submodules of the current repo/directory')
    args, clone_args = parser.parse_known_args()
    org = args.org
    dir = args.dir or org
    https = args.https
    dry_run = args.dry_run
    quiet = args.quiet
    num_jobs = args.num_jobs
    submodules = not args.no_submodules

    # Make org dir, cd into it
    Path(dir).mkdir(exist_ok=True, parents=True)
    chdir(dir)
    sh(['git','init'])

    # Load repos for org
    repos = get_repos(org)

    # Get clone URLs
    urls = [
        repo[('clone_url' if https else 'ssh_url')]
        for repo in repos
    ]

    if quiet:
        log = lambda *_,**__: ()
    else:
        log = print

    # Print URLs to clone
    if dry_run:
        msg = f'Dry run: would clone {len(urls)} repos into {getcwd()}:'
    else:
        msg = f'Cloning {len(urls)} repos into {getcwd()}:'

    log('\n\t'.join([msg] + urls))

    if dry_run: exit(0)

    if submodules:
        base = ['git','submodule','add'] + clone_args
    else:
        base = ['git','clone'] + clone_args

    def clone(url):
        cmd = base + [url]
        log(f'Running: {cmd}')
        sh(cmd)

    # Perform clones
    try:
        from joblib import Parallel, delayed
        parallel = Parallel(n_jobs=num_jobs)
        num_jobs = parallel.n_jobs
        log(f'Cloning with {num_jobs}x parallelism')
        parallel(delayed(clone)(url) for url in urls)
    except ImportError:
        log(f'Cloning with no parallelism')
        [ clone(url) for url in urls ]
