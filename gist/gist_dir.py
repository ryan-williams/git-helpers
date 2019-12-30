from os import chdir, getcwd
from os.path import exists
from pathlib import Path
from re import search
from subprocess import check_call, check_output
from sys import stdout, stderr
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


def run(*args):
    """Print a command before running it (converting all args to strs as well; useful for Paths in particular)"""
    args = [ str(arg) for arg in args ]
    print('Running: %s' % ' '.join(args))
    check_call(args, stdout=stdout, stderr=stderr)


def gist_dir(dir, remote='gist'):
    dir = Path(dir)
    print(f"Gist'ing {dir}")
    with cd(dir):
        # We'll make a git repository in this directory iff one doesn't exist
        init = not exists('.git')

        with NamedTemporaryFile(dir=Path.cwd()) as f:
            name = f.name
            # initialize the gist with a dummy file
            with open(name, 'w') as f:
                f.write('foo')

            # create the gist and grab its ID
            url = check_output([ 'gist', '-p', name ]).decode().strip()
            id = search('(?P<id>[^/]+)$', url).groupdict()['id']
            print(f"Created gist {url} (id {id})")

            if init:
                # make working dir a clone of the upstream gist
                run('git', 'init')

            run('git', 'remote', 'add', remote, f"git@gist.github.com:{id}.git")

            if init:
                run('git', 'fetch', remote)

        if init:
            run('git', 'checkout', f'{remote}/master')

            # add the local dir's contents
            run('git', 'add' '.')

            # rm the dummy file again (checkout will have restored it, and it's git-tracked this time)
            run('git', 'rm', name)

            # create a new "initial commit", overwriting the one the gist was created with
            run('git', 'commit', '--amend', '-m', 'initial commit')

        # overwrite the gist (and its history) with the single real commit we want to be present
        run('git', 'push', remote, '--force', 'HEAD:master')

        print(f"Updated gist: {url}")


if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('dir', nargs='?', help='Directories to commit as GitHub gists')
    parser.add_argument('-r', '--remote', default='gist', help='Name to use for a git remote created in each repo/directory, which points at the created gist.')
    args = parser.parse_args()

    remote = args.remote

    dirs = args.dir
    if not dirs:
        dirs = [ Path.cwd() ]

    for dir in dirs:
        gist_dir(dir, remote)
