
import os

class GitDirPath:
    def __init__(self, path = None):
        self.base_path = path

        git_dir = '.git'
        if not os.path.isdir('.git'):
            with open('.git', 'r') as fd:
                git_dir = fd.read().strip().replace('gitdir: ', '')

        self.path = os.path.join(git_dir, path) if path else git_dir
