#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "click",
#     "pyyaml",
#     "utz",
# ]
# ///
from datetime import timezone, datetime
from os.path import basename, splitext, abspath, dirname
from pathlib import Path
import re
import shlex
import sys
import time
import yaml

from click import group, pass_context
from utz import proc, err
from utz.cli import flag, opt, arg

# Add parent directory to path for local imports
sys.path.insert(0, dirname(dirname(abspath(__file__))))

from util.branch_resolution import resolve_remote_ref

SSH_REMOTE_URL_RGX = re.compile(r'git@github\.com:(?P<repo>[^/]+/[^/]+?)(?:\.git)?')
HTTPS_REMOTE_URL_RGX = re.compile(r'https://github\.com/(?P<repo>[^/]+/[^/]+?)(?:\.git)?')


def get_github_repo(remote=None):
    if remote:
        remotes = [remote]
    else:
        remotes = proc.lines('git', 'remote', log=None)

    github_repos = {}
    for remote in remotes:
        url = proc.line('git', 'remote', 'get-url', remote, log=None) or ''
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
        err(f"Found no GitHub repo remote URLs")
        return None
    tracked_branch = proc.line('git', 'rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}', err_ok=True, log=None)
    if tracked_branch:
        remote, *_ = tracked_branch.split('/')
        if remote in github_repos:
            return github_repos[remote]
    err(f'Found {len(github_repos)} GitHub repo remote URLs: {github_repos}')
    return None


@group('github-workflows')
@pass_context
@opt('-r', '--remote')
@opt('-R', '--repo')
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
    workflows_data = proc.json('gh', 'api', f'/repos/{repo}/actions/workflows', log=None)
    workflows = workflows_data['workflows']
    workflow_names = [ basename(workflow['path']) for workflow in workflows ]
    for workflow_name in workflow_names:
        print(workflow_name)


def get_runs(repo, workflow):
    runs = proc.json('gh', 'run', 'list', '-R', repo, '-w', workflow, '--json', 'databaseId', log=None)
    return [ run['databaseId'] for run in runs ]


@github_workflows.command('runs')
@pass_context
@arg('workflow')
def github_workflows_runs(ctx, workflow):
    repo = ctx.obj
    proc.run('gh', 'run', 'list', '-R', repo, '-w', workflow)


@github_workflows.command('delete')
@pass_context
@flag('-n', '--dry-run')
@arg('workflow')
def github_workflows_delete(ctx, dry_run, workflow):
    repo = ctx.obj
    run_ids = get_runs(repo, workflow)
    for run_id in run_ids:
        cmd = ['gh', 'api', '-X', 'DELETE', f'/repos/{repo}/actions/runs/{run_id}']
        if dry_run:
            err(f"DRY RUN: {shlex.join(cmd)}")
        else:
            err(shlex.join(cmd))
            proc.run(*cmd, log=None)


@github_workflows.command('run')
@pass_context
@flag('-O', '--no-open', help='Do not automatically open the job in browser')
@opt('-r', '--ref', help='Git reference (branch, tag, or SHA) to run workflow from')
@opt('-F', '--field', multiple=True, help='Add a field with a JSON value')
@opt('-f', '--raw-field', multiple=True, help='Add a field with a raw string value')
@arg('workflow')
@arg('args', nargs=-1)
def github_workflows_run(ctx, no_open, ref, field, raw_field, workflow, args):
    """Trigger a workflow and optionally open the job when it starts."""
    repo = ctx.obj

    # Handle workflow name (remove .yml extension if present)
    workflow_filename = workflow.removesuffix('.yml').removesuffix('.yaml')

    # Get git root directory
    git_root = proc.line('git', 'rev-parse', '--show-toplevel', log=None)
    if not git_root:
        err("Error: Not in a git repository")
        exit(1)

    # Get list of git-tracked workflow files
    tracked_files = proc.lines('git', 'ls-tree', '-r', '--name-only', 'HEAD', '.github/workflows/', err_ok=True, log=None) or []

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
            filename = basename(file)
            stem = splitext(filename)[0]
            if workflow_filename.lower() in stem.lower():
                matching_files.append(file)

        if len(matching_files) == 1:
            workflow_path = str(Path(git_root) / matching_files[0])
            err(f"Found workflow by substring match: {basename(matching_files[0])}")
        elif len(matching_files) > 1:
            err(f"Error: Multiple workflows match '{workflow_filename}':")
            for f in sorted(matching_files):
                err(f"  - {basename(f)}")
            err("Please be more specific.")
            exit(1)

    if not workflow_path:
        err(f"Workflow file not found: no files in .github/workflows/ match '{workflow_filename}'")
        exit(1)

    # Read the workflow file to get the actual workflow name
    workflow_name = None
    try:
        with open(workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
            workflow_name = workflow_data.get('name')
            if workflow_name:
                err(f"Workflow name: '{workflow_name}' (from file: {workflow_filename})")
            else:
                err(f"Warning: No 'name' field in workflow file")
    except Exception as e:
        err(f"Warning: Failed to parse workflow file: {e}")

    # If we couldn't get the name from the file, try to get it from gh workflow list
    if not workflow_name:
        try:
            # List all workflows to find the one matching our filename
            workflows = proc.json('gh', 'workflow', 'list', '--json', 'name,path', log=None)
            for wf in workflows:
                if basename(wf['path']) == basename(workflow_path):
                    workflow_name = wf['name']
                    err(f"Workflow name: '{workflow_name}' (from gh workflow list)")
                    break
        except Exception as e:
            err(f"Warning: Failed to get workflow name from gh: {e}")

    # Final fallback
    if not workflow_name:
        workflow_name = workflow_filename
        err(f"Warning: Using filename as workflow name: {workflow_name}")

    # If no ref specified, try to match current local ref with remote
    if not ref:
        ref, _ = resolve_remote_ref(verbose=True)

    # Get timestamp before triggering (more reliable than checking existing runs)
    trigger_time = datetime.now(timezone.utc)

    # Get workflow ID for more reliable matching
    workflow_id = None
    try:
        workflows_data = proc.json('gh', 'api', f'/repos/{repo}/actions/workflows', log=None)
        workflows = workflows_data['workflows']
        for wf in workflows:
            if basename(wf['path']) == basename(workflow_path):
                workflow_id = wf['id']
                err(f"Workflow ID: {workflow_id} (name: '{workflow_name}')")
                break
    except Exception as e:
        err(f"Warning: Could not get workflow ID: {e}")

    # Build command with options
    workflow_file = basename(workflow_path)
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

    err(f"Running: {shlex.join(cmd)}")
    proc.run(cmd)

    if no_open:
        return

    # Poll for new workflow run
    err("Waiting for workflow to start", end="")
    new_run_id = None
    for attempt in range(30):
        time.sleep(2)
        err(".", end="", flush=True)
        try:
            # Get runs for this specific workflow file
            if workflow_id:
                # Use workflow ID if we have it (most reliable)
                runs = proc.json(
                    'gh', 'api', f'/repos/{repo}/actions/workflows/{workflow_id}/runs',
                    '-q', '.workflow_runs[:10]'
                )
            else:
                # Fallback to listing by workflow file
                runs = proc.json(
                    'gh', 'run', 'list',
                    '-w', basename(workflow_path),
                    '-L', '10',
                    '--json', 'databaseId,workflowName,status,headBranch,createdAt,event'
                )

            # Look for a run created after we triggered it
            for run in runs:
                # Parse creation time
                created_at = run.get('created_at') or run.get('createdAt')
                if not created_at:
                    continue

                run_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

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
                    err()
                    err(f"Found new workflow run: {new_run_id} (branch: {run_branch}, created: {created_at})")
                    break

            if new_run_id:
                break

        except Exception as e:
            if attempt == 0:
                err(f"\nWarning: Failed to check runs: {e}")
            pass

    if not new_run_id:
        err("\nTimed out waiting for workflow to start")
        exit(1)

    # Poll for job to start
    err("Waiting for job to start", end="")
    job_started = False
    for attempt in range(30):
        time.sleep(1)
        err(".", end="", flush=True)
        try:
            jobs = proc.json(
                'gh', 'run', 'view', str(new_run_id),
                '--json', 'jobs'
            ).get('jobs', [])
            if len(jobs) > 0:
                job_started = True
                break
        except:
            pass

    err()

    if job_started:
        err("Job started, opening...")
        # Get the job URL and open it
        try:
            data = proc.json(
                'gh', 'run', 'view', str(new_run_id),
                '--json', 'databaseId,jobs'
            )
            if data['jobs']:
                job_url = data['jobs'][-1]['url']  # Get the last (most recent) job
                proc.run('open', job_url)
            else:
                raise Exception("No jobs found")
        except Exception as e:
            err(f"Failed to open job: {e}")
            # Fallback to opening the run
            proc.run('gh', 'run', 'view', '--web', new_run_id)
    else:
        err("Job didn't start in time, opening workflow run instead...")
        proc.run('gh', 'run', 'view', '--web', new_run_id)


if __name__ == '__main__':
    github_workflows()
