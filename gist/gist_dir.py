import shlex
from functools import partial
from os import chdir, getcwd
from os.path import exists
from pathlib import Path
from subprocess import check_call, check_output, CalledProcessError, DEVNULL
import shutil
import sys
from urllib.parse import urlparse


class cd:
    """Context manager for changing the current working directory"""

    def __init__(self, path):
        path = Path(path)
        self.path = path.expanduser()

    def __enter__(self):
        self.prevPath = Path(getcwd())
        chdir(str(self.path))

    def __exit__(self, etype, value, traceback):
        chdir(str(self.prevPath))


err = partial(print, file=sys.stderr)


def run(
    *args,
    output=False,
    stdout=sys.stdout,
    stderr=sys.stderr,
    **kwargs,
):
    """Print a command to stderr, then run it.

    Also converts args to `str`s (useful for `Path`s).
    """
    cmd = [str(arg) for arg in args]
    err(f'Running: {shlex.join(cmd)}')
    if output:
        return check_output(cmd, **kwargs).decode()
    else:
        return check_call(cmd, stdout=stdout, stderr=stderr, **kwargs)


def lines(*args, **kwargs):
    _lines = run(*args, output=True, **kwargs).split('\n')
    return (line.rstrip('\n') for line in _lines)


def line(*args, **kwargs):
    _lines = list(lines(*args, **kwargs))
    if _lines[-1] == '':
        _lines = _lines[:-1]
    [line] = _lines
    return line


def check_gh_auth():
    """Check if gh CLI is installed and user is authenticated"""
    if not shutil.which('gh'):
        err("Error: 'gh' command not found. Please install GitHub CLI: https://cli.github.com/")
        sys.exit(1)

    try:
        run('gh', 'gist', 'list', '--limit', '1', output=True, stderr=DEVNULL)
        return True
    except CalledProcessError:
        return False


def parse_gist_url(url):
    url = urlparse(url)
    path = url.path
    assert path[0] == '/'
    path = path[1:]
    id = path.split('/')[-1]
    ssh_url = f'git@{url.netloc}:{id}.git'
    return id, ssh_url


def gist_dir(
    dir,
    remote='g',
    branch='gist',
    copy_url=False,
    open_gist=False,
    public=False,
    files=None,
    restore_branch=False,
    gist=None,
):
    """Create a gist from a directory using GitHub CLI.

    Note: Requires 'gh' (GitHub CLI) to be installed and authenticated.
    For GitHub Enterprise, configure gh with: gh auth login --hostname your-github-enterprise.com
    """
    dir = Path(dir)
    with cd(dir):
        # We'll make a git repository in this directory iff one doesn't exist
        init = not exists('.git')

        # Capture current branch if in existing repo (for restore_branch option)
        original_branch = None
        if not init:
            try:
                original_branch = line('git', 'symbolic-ref', '-q', '--short', 'HEAD')
            except:
                pass  # Detached HEAD or other edge case

        if gist:
            id, ssh_url = parse_gist_url(gist)
        else:
            # Get list of files to include in gist
            if files:
                gist_files = [str(f) for f in files]
            else:
                gist_files = lines('git', 'ls-files')
                gist_files = [f for f in gist_files if f]  # Remove empty strings

            if not gist_files:
                err("No files to create gist from")
                sys.exit(1)

            # Prepare gh gist create cmd with actual files
            cmd = ['gh', 'gist', 'create']
            if public:
                cmd.append('--public')
            cmd.extend(gist_files)

            # Create the gist and grab its ID
            try:
                url = line(*cmd)
            except CalledProcessError:
                # Check if authentication is the issue
                if not check_gh_auth():
                    err("Error: Not authenticated with gh CLI. Please run 'gh auth login' first.")
                    sys.exit(1)
                else:
                    # Re-raise the original error if it's not an auth issue
                    raise
            id, ssh_url = parse_gist_url(url)
            err(f"Created gist {url} (id {id})")

            # Copy URL to clipboard if requested
            if copy_url:
                try:
                    run('pbcopy', input=url.encode())
                    err("Gist URL copied to clipboard")
                except CalledProcessError:
                    err("Couldn't copy to clipboard (pbcopy not available)")

            if init:
                # Make working dir a clone of the upstream gist
                run('git', 'init')

        remotes = list(lines('git', 'remote'))

        # If the specified remote already exists and it's 'g', try 'gist' instead
        if remote == 'g' and 'g' in remotes:
            if 'gist' not in remotes:
                err(f"Remote 'g' already exists, using 'gist' instead")
                remote = 'gist'
            else:
                err(f"Both 'g' and 'gist' remotes already exist")
                # Keep the original remote name, will just update it

        if remote not in remotes:
            run('git', 'remote', 'add', remote, ssh_url)

        # If we're in an existing git repo (not newly initialized), push current commit to gist
        if not init:
            prev_sha = line('git', 'log', '-1', '--format=%h')

            err(f'Pushing existing commit {prev_sha} to gist')
            # Force push current HEAD to gist's main branch
            run('git', 'push', remote, '--force', 'HEAD:main')

            # Set up tracking if we're on a branch
            if original_branch:
                run('git', 'branch', '--set-upstream-to', f'{remote}/main', original_branch)
                err(f'Set {original_branch} to track {remote}/main')
        else:
            # For newly initialized repos, fetch and create tracking branch
            run('git', 'fetch', remote)

            # Create local branch to track the gist
            run('git', 'checkout', '-b', branch, f'{remote}/main')
            run('git', 'branch', '-u', f'{remote}/main')

        # Configure push.default so that `git push` will update gist/main
        run('git', 'config', 'push.default', 'upstream')

        err(f"Gist created: {url}")
        if open_gist:
            try:
                run('open', url)
            except CalledProcessError:
                err("Couldn't find `open` command")

        if restore_branch and original_branch:
            run('git', 'checkout', original_branch)


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('paths', nargs='*',
                        help='Either a list of directories to create GitHub gists of, or a list of files to add to a gist from the current directory (binary files work in both cases!)')
    parser.add_argument('-b', '--branch', default='gist',
                        help="Name for new local branch when creating gist from non-git directory (ignored for existing git repos)")
    parser.add_argument('-B', '--restore_branch', default=False, action='store_true',
                        help="Stay on current branch after creating gist (only applies to existing git repos)")
    parser.add_argument('-c', '--copy', default=False, action='store_true',
                        help="Copy the resulting gist's URL to the clipboard")
    parser.add_argument('-d', '--dir', required=False,
                        help="Specify a single directory to make a gist from; any positional arguments must point to files in this directory")
    parser.add_argument('-g', '--gist', help="URL of an existing Gist (will overwrite that Gist's contents!)")
    parser.add_argument('-o', '--open', default=False, action='store_true', help="Open the gist when finished running")
    parser.add_argument('-p', '--public', default=False, action='store_true', help="Make the gist public (default is secret)")
    parser.add_argument('-r', '--remote', default='g',
                        help='Name to use for a git remote created in each repo/directory, which points at the created gist (defaults to "g", falls back to "gist" if "g" is taken).')
    args = parser.parse_args()

    dir = args.dir
    branch = args.branch
    remote = args.remote
    copy_url = args.copy
    open_gist = args.open
    public = args.public
    restore_branch = args.restore_branch

    gist = args.gist

    paths = [Path(path) for path in args.paths]
    are_files = [path.is_file() for path in paths]
    files = None
    if dir:
        if not all(are_files):
            raise Exception('When a directory is passed via the -d/--dir flag, all positional arguments must be files (and in that directory)')
        dirs = [dir]
        files = paths
    else:
        if paths:
            if any(are_files):
                if all(are_files):
                    dirs = [Path.cwd()]
                    files = paths
                else:
                    raise Exception('Arguments should be all directories or all files')
            else:
                dirs = paths
        else:
            dirs = [Path.cwd()]

    for dir in dirs:
        gist_dir(
            dir,
            remote=remote,
            branch=branch,
            copy_url=copy_url,
            open_gist=open_gist,
            public=public,
            files=files,
            restore_branch=restore_branch,
            gist=gist,
        )
