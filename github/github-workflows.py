#!/usr/bin/env python
import json
import os
import re
import shlex
import sys
from os.path import basename
from subprocess import check_output, check_call, CalledProcessError
from sys import stderr

from util.branch_resolution import resolve_remote_ref

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


@github_workflows.command('run')
@pass_context
@option('-O', '--no-open', is_flag=True, help='Do not automatically open the job in browser')
@option('-r', '--ref', help='Git reference (branch, tag, or SHA) to run workflow from')
@option('-F', '--field', multiple=True, help='Add a field with a JSON value')
@option('-f', '--raw-field', multiple=True, help='Add a field with a raw string value')
@argument('workflow')
@argument('args', nargs=-1)
def github_workflows_run(ctx, no_open, ref, field, raw_field, workflow, args):
    """Trigger a workflow and optionally open the job when it starts."""
    import time
    import os
    from pathlib import Path

    repo = ctx.obj

    # Handle workflow name (remove .yml extension if present)
    workflow_filename = workflow.removesuffix('.yml').removesuffix('.yaml')

    # Get git root directory
    try:
        git_root = check_output(['git', 'rev-parse', '--show-toplevel']).decode().strip()
    except CalledProcessError:
        stderr.write("Error: Not in a git repository\n")
        exit(1)

    # Get list of git-tracked workflow files
    try:
        tracked_files = check_output(['git', 'ls-tree', '-r', '--name-only', 'HEAD', '.github/workflows/']).decode().strip().split('\n')
        tracked_files = [f for f in tracked_files if f]  # Remove empty strings
    except CalledProcessError:
        tracked_files = []

    # Check for exact workflow file match (only among tracked files)
    workflow_path = None
    for ext in ['.yml', '.yaml']:
        relative_path = f'.github/workflows/{workflow_filename}{ext}'
        if relative_path in tracked_files:
            workflow_path = str(Path(git_root) / relative_path)
            break

    # If exact match not found, try substring matching (only among tracked files)
    if not workflow_path:
        # Find all tracked workflow files that contain the substring
        matching_files = []
        for file in tracked_files:
            filename = os.path.basename(file)
            stem = os.path.splitext(filename)[0]
            if workflow_filename.lower() in stem.lower():
                matching_files.append(file)

        if len(matching_files) == 1:
            workflow_path = str(Path(git_root) / matching_files[0])
            stderr.write(f"Found workflow by substring match: {os.path.basename(matching_files[0])}\n")
        elif len(matching_files) > 1:
            stderr.write(f"Error: Multiple workflows match '{workflow_filename}':\n")
            for f in sorted(matching_files):
                stderr.write(f"  - {os.path.basename(f)}\n")
            stderr.write("Please be more specific.\n")
            exit(1)

    if not workflow_path:
        stderr.write(f"Workflow file not found: no files in .github/workflows/ match '{workflow_filename}'\n")
        exit(1)

    # Read the workflow file to get the actual workflow name
    workflow_name = None
    try:
        import yaml
        with open(workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
            workflow_name = workflow_data.get('name')
            if workflow_name:
                stderr.write(f"Workflow name: '{workflow_name}' (from file: {workflow_filename})\n")
            else:
                stderr.write(f"Warning: No 'name' field in workflow file\n")
    except ImportError:
        stderr.write("Warning: PyYAML not installed, cannot parse workflow file\n")
    except Exception as e:
        stderr.write(f"Warning: Failed to parse workflow file: {e}\n")

    # If we couldn't get the name from the file, try to get it from gh workflow list
    if not workflow_name:
        try:
            # List all workflows to find the one matching our filename
            workflows_data = check_output(['gh', 'workflow', 'list', '--json', 'name,path']).decode()
            workflows = json.loads(workflows_data)
            for wf in workflows:
                if os.path.basename(wf['path']) == os.path.basename(workflow_path):
                    workflow_name = wf['name']
                    stderr.write(f"Workflow name: '{workflow_name}' (from gh workflow list)\n")
                    break
        except Exception as e:
            stderr.write(f"Warning: Failed to get workflow name from gh: {e}\n")

    # Final fallback
    if not workflow_name:
        workflow_name = workflow_filename
        stderr.write(f"Warning: Using filename as workflow name: {workflow_name}\n")

    # If no ref specified, try to match current local ref with remote
    if not ref:
        ref, _ = resolve_remote_ref(verbose=True)

    # Get timestamp before triggering (more reliable than checking existing runs)
    import datetime
    trigger_time = datetime.datetime.now(datetime.timezone.utc)

    # Get workflow ID for more reliable matching
    workflow_id = None
    try:
        workflows_data = check_output(['gh', 'api', f'/repos/{repo}/actions/workflows']).decode()
        workflows = json.loads(workflows_data)['workflows']
        for wf in workflows:
            if os.path.basename(wf['path']) == os.path.basename(workflow_path):
                workflow_id = wf['id']
                stderr.write(f"Workflow ID: {workflow_id} (name: '{workflow_name}')\n")
                break
    except Exception as e:
        stderr.write(f"Warning: Could not get workflow ID: {e}\n")

    # Build command with options
    workflow_file = os.path.basename(workflow_path)
    cmd = ['gh', 'workflow', 'run', workflow_file]

    # Add ref if specified
    if ref:
        cmd.extend(['--ref', ref])

    # Add field options
    for f in field:
        cmd.extend(['-F', f])
    for f in raw_field:
        cmd.extend(['-f', f])

    # Add any remaining args
    cmd.extend(list(args))

    stderr.write(f"Running: {shlex.join(cmd)}\n")
    check_call(cmd)

    if no_open:
        return

    # Poll for new workflow run
    stderr.write("Waiting for workflow to start")
    new_run_id = None
    for attempt in range(30):
        time.sleep(2)
        stderr.write(".")
        stderr.flush()

        try:
            # Get runs for this specific workflow file
            if workflow_id:
                # Use workflow ID if we have it (most reliable)
                runs_data = check_output([
                    'gh', 'api', f'/repos/{repo}/actions/workflows/{workflow_id}/runs',
                    '-q', '.workflow_runs[:10]'
                ]).decode()
            else:
                # Fallback to listing by workflow file
                runs_data = check_output([
                    'gh', 'run', 'list',
                    '-w', os.path.basename(workflow_path),
                    '-L', '10',
                    '--json', 'databaseId,workflowName,status,headBranch,createdAt,event'
                ]).decode()

            runs = json.loads(runs_data)

            # Look for a run created after we triggered it
            for run in runs:
                # Parse creation time
                created_at = run.get('created_at') or run.get('createdAt')
                if not created_at:
                    continue

                run_time = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))

                # Check if this run was created after we triggered
                if run_time < trigger_time:
                    continue

                # Check branch if specified
                run_branch = run.get('head_branch') or run.get('headBranch')
                if ref and run_branch != ref:
                    continue

                # Check if it's a workflow_dispatch event (what we triggered)
                if run.get('event') == 'workflow_dispatch' or attempt > 10:
                    new_run_id = run.get('id') or run.get('databaseId')
                    stderr.write(f"\nFound new workflow run: {new_run_id} (branch: {run_branch}, created: {created_at})\n")
                    break

            if new_run_id:
                break

        except Exception as e:
            if attempt == 0:
                stderr.write(f"\nWarning: Failed to check runs: {e}\n")
            pass

    if not new_run_id:
        stderr.write("\nTimed out waiting for workflow to start\n")
        exit(1)

    # Poll for job to start
    stderr.write("Waiting for job to start")
    job_started = False
    for attempt in range(30):
        time.sleep(1)
        stderr.write(".")
        stderr.flush()

        try:
            job_data = check_output([
                'gh', 'run', 'view', str(new_run_id),
                '--json', 'jobs'
            ]).decode()
            jobs = json.loads(job_data).get('jobs', [])

            if len(jobs) > 0:
                job_started = True
                break
        except:
            pass

    stderr.write("\n")

    if job_started:
        stderr.write("Job started, opening...\n")
        # Get the job URL and open it
        try:
            run_data = check_output([
                'gh', 'run', 'view', str(new_run_id),
                '--json', 'databaseId,jobs'
            ]).decode()
            data = json.loads(run_data)
            if data['jobs']:
                job_url = data['jobs'][-1]['url']  # Get the last (most recent) job
                check_call(['open', job_url])
            else:
                raise Exception("No jobs found")
        except Exception as e:
            stderr.write(f"Failed to open job: {e}\n")
            # Fallback to opening the run
            check_call(['gh', 'run', 'view', '--web', str(new_run_id)])
    else:
        stderr.write("Job didn't start in time, opening workflow run instead...\n")
        check_call(['gh', 'run', 'view', '--web', str(new_run_id)])


if __name__ == '__main__':
    github_workflows()
