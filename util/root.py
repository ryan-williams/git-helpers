
import subprocess

def git_root():
    return subprocess.check_output(['git', 'rev-parse', '--show-toplevel']).decode().strip()

