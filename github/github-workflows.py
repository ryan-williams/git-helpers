#!/usr/bin/env python
import json
import re
import shlex
from os.path import basename
from subprocess import check_output, check_call, PIPE, CalledProcessError
from sys import stderr

from click import group, pass_context, option, argument

SSH_REMOTE_URL_RGX = re.compile(r'git@github\.com:(?P<repo>[^/]+/[^/]+?)(?:\.git)?')
HTTPS_REMOTE_URL_RGX = re.compile(r'https://github\.com/(?P<repo>[^/]+/[^/]+?)(?:\.git)?')


def get_github_repo(remote=None):
    if remote:
        remotes = [remote]
    else:
        remotes = [
            remote
            for remote in check_output(['git', 'remote']).decode().split('\n')
            if remote
        ]

    github_repos = {}
    for remote in remotes:
        url = check_output(['git', 'remote', 'get-url', remote]).decode().rstrip('\n')
        m = SSH_REMOTE_URL_RGX.fullmatch(url)
        if m:
            github_repos[remote] = m['repo']
        else:
            m = HTTPS_REMOTE_URL_RGX.fullmatch(url)
            if m:
                github_repos[remote] = m['repo']

    if len(github_repos) == 1:
        return list(github_repos.values())[0]
    if not github_repos:
        stderr.write(f"Found no GitHub repo remote URLs\n")
        return None
    try:
        tracked_branch = check_output([ 'git', 'rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}' ]).decode().rstrip('\n')
        remote, *_ = tracked_branch.split('/')
        return github_repos[remote]
    except CalledProcessError:
        stderr.write(f'Found {len(github_repos)} GitHub repo remote URLs: {github_repos}\n')
        return None


@group('github-workflows')
@pass_context
@option('-r', '--remote')
@option('-R', '--repo')
def github_workflows(ctx, remote, repo):
    if remote:
        remote_repo = get_github_repo(remote)
        if not remote_repo:
            raise ValueError(f"Failed to infer GitHub repo from remote {remote}")
        if repo and repo != remote_repo:
            raise ValueError(f"Remote repo {remote_repo} != repo {repo}")
        repo = remote_repo
    elif not repo:
        repo = get_github_repo()
        if not repo:
            raise RuntimeError("No repo passed or inferred from remotes")
    ctx.obj = repo


@github_workflows.command('list')
@pass_context
def github_workflows_list(ctx):
    repo = ctx.obj
    workflows = json.loads(check_output(['gh', 'api', f'/repos/{repo}/actions/workflows']).decode())['workflows']
    workflow_names = [ basename(workflow['path']) for workflow in workflows ]
    for workflow_name in workflow_names:
        print(workflow_name)


def get_runs(repo, workflow):
    runs = json.loads(check_output(['gh', 'run', 'list', '-R', repo, '-w', workflow, '--json', 'databaseId']).decode())
    return [ run['databaseId'] for run in runs ]


@github_workflows.command('runs')
@pass_context
@argument('workflow')
def github_workflows_runs(ctx, workflow):
    repo = ctx.obj
    check_call(['gh', 'run', 'list', '-R', repo, '-w', workflow])


@github_workflows.command('delete')
@pass_context
@option('-n', '--dry-run', is_flag=True)
@argument('workflow')
def github_workflows_delete(ctx, dry_run, workflow):
    repo = ctx.obj
    run_ids = get_runs(repo, workflow)
    for run_id in run_ids:
        cmd = ['gh', 'api', '-X', 'DELETE', f'/repos/{repo}/actions/runs/{run_id}']
        if dry_run:
            stderr.write(f"DRY RUN: {shlex.join(cmd)}\n")
        else:
            stderr.write(shlex.join(cmd) + "\n")
            check_call(cmd)


if __name__ == '__main__':
    github_workflows()
