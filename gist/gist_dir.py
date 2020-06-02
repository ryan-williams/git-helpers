from os import chdir, getcwd
from os.path import exists
from pathlib import Path
from re import search
from subprocess import check_call, check_output, DEVNULL, CalledProcessError
import sys
from tempfile import NamedTemporaryFile


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


def run(*args, output=False, stdout=sys.stdout, stderr=sys.stderr, **kwargs):
    """Print a command before running it (converting all args to strs as well; useful for Paths in particular)"""
    cmd = [ str(arg) for arg in args ]
    print('Running: %s' % ' '.join(cmd))
    if output:
        return check_output(cmd, **kwargs).decode()
    else:
        check_call(cmd, stdout=stdout, stderr=stderr, **kwargs)


def lines(*args, **kwargs):
    _lines =  run(*args, output=True, **kwargs).split('\n')
    return ( line.rstrip('\n') for line in _lines )


def line(*args, **kwargs):
    _lines = list(lines(*args, **kwargs))
    if _lines[-1] == '':
        _lines = _lines[:-1]
    [line] = _lines
    return line


def gist_dir(
    dir,
    remote='gist',
    branch='gist',
    copy_url=False,
    open_gist=False,
    private=False,
    files=None,
    push_history=False,
    restore_branch=False
):
    dir = Path(dir)
    print(f"Gist'ing {dir}")
    with cd(dir):
        # We'll make a git repository in this directory iff one doesn't exist
        init = not exists('.git')
        # if not init and files:
        #     raise Exception('File-restrictions not supported for existing git-repo directories')

        with NamedTemporaryFile(dir=Path.cwd()) as f:
            name = f.name
            # initialize the gist with a dummy file
            with open(name, 'w') as f:
                f.write('placeholder text; in process of creating Gist from existing files\n')

            # prepare gist cmd
            cmd = [ 'gist' ]
            if copy_url:
                cmd.append('-c')
            if private:
                cmd.append('-p')
            cmd.append(name)

            # create the gist and grab its ID
            url = check_output(cmd).decode().strip()
            id = search('(?P<id>[^/]+)$', url).groupdict()['id']
            print(f"Created gist {url} (id {id})")

            if init:
                # make working dir a clone of the upstream gist
                run('git', 'init')

            run('git', 'remote', 'add', remote, f"git@gist.github.com:{id}.git")
            run('git', 'fetch', remote)

        prev_branch = line('git', 'symbolic-ref', '-q', '--short', 'HEAD')
        prev_sha = line('git', '--no-pager', 'log', '--no-walk', '--format=%h', 'HEAD')
        print(f'Saved current branch: {prev_branch} ({prev_sha})')

        run('git', 'checkout', '-b', branch, '-t', f'{remote}/master')

        if not push_history:
            # add the local dir's contents (including only specific files if necessary)
            if files:
                for file in files:
                    file = Path(file)
                    if not file.exists():
                        run(*['git','checkout',prev_sha,'--',file])
                    
                    run('git', 'add', file)
            else:
                run('git', 'add', '.')

            # rm the dummy file again (checkout will have restored it, and it's git-tracked this time)
            run('git', 'rm', name)

            # create a new "initial commit", overwriting the one the gist was created with
            run('git', 'commit', '--amend', '-m', 'initial commit')

        # overwrite the gist (and its history) with the single real commit we want to be present
        run('git', 'push', remote, '--force', f'{branch}:master')

        print(f"Updated gist: {url}")
        if open_gist:
            try:
                run('which', 'open', stdout=DEVNULL, stderr=DEVNULL)
                run('open', url)
            except CalledProcessError:
                print("Couldn't find `open` command")

        if restore_branch:
            run('git', 'checkout', prev_branch)


if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('paths', nargs='*', help='Either a list of directories to create GitHub gists of, or a list of files to add to a gist from the current directory (binary files work in both cases!)')
    parser.add_argument('-b', '--branch', default='gist', help="Name for new local branch that will track the new Gist's \"master\" branch")
    parser.add_argument('-B', '--restore_branch', default=False, action='store_true', help="Move back to current branch at end of execution (by default, a new local branch tracking the new Gist's \"master\" branch is checked out when `gist-dir` is finished running")
    parser.add_argument('-c', '--copy', default=False, action='store_true', help="Copy the resulting gist's URL to the clipboard")
    parser.add_argument('-d', '--dir', required=False, help="Specify a single directory to make a gist from; any positional arguments must point to files in this directory")
    parser.add_argument('-o', '--open', default=False, action='store_true', help="Open the gist when finished running")
    parser.add_argument('-p', '--private', default=False, action='store_true', help="Make the gist private")
    parser.add_argument('-r', '--remote', default='gist', help='Name to use for a git remote created in each repo/directory, which points at the created gist.')
    parser.add_argument('--history', '--push_history', default=False, action='store_true', help="When set, push the directory's existing Git history to the newly-created Gist (by default, a standalone commit appearing add applicable files de novo will be created).")
    args = parser.parse_args()

    dir = args.dir
    branch = args.branch
    remote = args.remote
    copy_url = args.copy
    open_gist = args.open
    private = args.private
    push_history = args.history
    restore_branch = args.restore_branch

    paths = [ Path(path) for path in args.paths ]
    are_files = [ path.is_file() for path in paths ]
    files = None
    if dir:
        if not all(are_files):
            raise Exception('When a directory is passed via the -d/--dir flag, all positional arguments must be files (and in that directory)')
        dirs = [ dir ]
        files = paths
    else:
        if paths:
            if any(are_files):
                if all(are_files):
                    dirs = [ Path.cwd() ]
                    files = paths
                else:
                    raise Exception('Arguments should be all directories or all files')
            else:
                dirs = paths
        else:
            dirs = [ Path.cwd() ]

    for dir in dirs:
        gist_dir(
            dir,
            remote=remote,
            branch=branch,
            copy_url=copy_url,
            open_gist=open_gist,
            private=private,
            files=files,
            push_history=push_history,
            restore_branch=restore_branch,
        )
