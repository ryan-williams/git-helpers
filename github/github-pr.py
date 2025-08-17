#!/usr/bin/env python
"""Clone and sync GitHub PR descriptions with local folders and GitHub gists."""

import json
import os
import re
import sys
import difflib
from functools import partial
from pathlib import Path
from subprocess import check_output, check_call, CalledProcessError, DEVNULL
from sys import stderr

import click

# Helper for printing to stderr
err = partial(print, file=stderr)

from util.branch_resolution import resolve_remote_ref


def get_pr_info_from_path(path=None):
    """Extract PR info from directory structure or git config."""
    if path is None:
        path = Path.cwd()
    else:
        path = Path(path)

    # First, check if we have PR info in git config (highest priority)
    try:
        owner = check_output(['git', 'config', 'pr.owner'], stderr=DEVNULL).decode().strip()
        repo = check_output(['git', 'config', 'pr.repo'], stderr=DEVNULL).decode().strip()
        pr_number = check_output(['git', 'config', 'pr.number'], stderr=DEVNULL).decode().strip()
        if owner and repo and pr_number:
            return owner, repo, pr_number
    except:
        pass

    # Look for pr<number> pattern in current or parent directories
    current = path
    pr_number = None
    repo_path = None

    while current != current.parent:
        # Check if this dir matches pr<number>
        match = re.match(r'^pr(\d+)$', current.name)
        if match:
            pr_number = match.group(1)
            repo_path = current.parent
            break
        current = current.parent

    if not pr_number:
        # Check if we're in a directory with DESCRIPTION.md that has metadata
        desc_file = path / 'DESCRIPTION.md'
        if desc_file.exists():
            with open(desc_file, 'r') as f:
                first_line = f.readline().strip()
                # Look for pattern like # [owner/repo#123] or # [owner/repo#123](url)
                match = re.match(r'^#\s*\[([^/]+)/([^#]+)#(\d+)\](?:\([^)]+\))?', first_line)
                if match:
                    return match.group(1), match.group(2), match.group(3)

        err("Error: Could not determine PR number from directory structure")
        err("Expected to be in a directory named 'pr<number>' or have DESCRIPTION.md with PR metadata")
        return None, None, None

    # Get repo info from parent directory
    os.chdir(repo_path)

    # Try to get owner/repo from git remote
    try:
        # Get the default remote
        remotes = check_output(['git', 'remote'], stderr=DEVNULL).decode().strip().split('\n')

        for remote in ['origin', 'upstream'] + remotes:
            if not remote:
                continue
            try:
                url = check_output(['git', 'remote', 'get-url', remote], stderr=DEVNULL).decode().strip()
                # Match GitHub URLs
                match = re.search(r'github\.com[:/]([^/]+)/([^/\s]+?)(?:\.git)?$', url)
                if match:
                    owner = match.group(1)
                    repo = match.group(2)
                    return owner, repo, pr_number
            except:
                continue
    except:
        pass

    err("Error: Could not determine repository from git remotes")
    return None, None, pr_number


def get_pr_metadata(owner, repo, pr_number):
    """Get PR metadata from GitHub."""
    try:
        cmd = ['gh', 'pr', 'view', pr_number, '-R', f'{owner}/{repo}', '--json', 'title,body,number,url']
        result = check_output(cmd).decode()
        data = json.loads(result)
        # Normalize line endings from GitHub (convert \r\n to \n)
        if data.get('body'):
            data['body'] = data['body'].replace('\r\n', '\n')
        return data
    except CalledProcessError as e:
        err(f"Error fetching PR metadata: {e}")
        return None


def extract_gist_footer(body):
    """Extract gist footer from body and return (body_without_footer, gist_url)."""
    if not body:
        return body, None

    lines = body.split('\n')
    # Check if last line is a gist footer (handle both old and new formats)
    if lines and lines[-1].strip().startswith('<!-- Synced with '):
        # Try new format with attribution (with or without revision)
        match = re.match(r'<!-- Synced with (https://gist\.github\.com/[a-f0-9]+(?:/[a-f0-9]+)?) via \[github-pr\.py\].*-->', lines[-1].strip())
        if not match:
            # Try old format without attribution (with or without revision)
            match = re.match(r'<!-- Synced with (https://gist\.github\.com/[a-f0-9]+(?:/[a-f0-9]+)?) -->', lines[-1].strip())
        if match:
            gist_url = match.group(1)
            # Remove the footer line
            body_without_footer = '\n'.join(lines[:-1]).rstrip()
            return body_without_footer, gist_url

    return body, None


def add_gist_footer(body, gist_url):
    """Add or update gist footer in body."""
    body_without_footer, _ = extract_gist_footer(body)

    footer = f'<!-- Synced with {gist_url} via [github-pr.py](https://github.com/ryan-williams/git-helpers/blob/main/github/github-pr.py) -->'

    if body_without_footer:
        return f'{body_without_footer}\n\n{footer}'
    else:
        return footer


def read_description_file(path):
    """Read and parse DESCRIPTION.md file."""
    desc_file = path / 'DESCRIPTION.md'
    if not desc_file.exists():
        return None, None

    with open(desc_file, 'r') as f:
        lines = f.readlines()

    if not lines:
        return None, None

    # First line should be # [owner/repo#123] Title or # [owner/repo#123](url) Title
    first_line = lines[0].strip()
    match = re.match(r'^#\s*\[([^/]+)/([^#]+)#(\d+)\](?:\([^)]+\))?\s*(.*)$', first_line)

    if match:
        title = match.group(4).strip()
        # Rest is the body (skip the first line and any immediately following blank lines)
        body_lines = lines[1:]
        while body_lines and not body_lines[0].strip():
            body_lines = body_lines[1:]
        body = ''.join(body_lines).rstrip()
        return title, body
    else:
        # Fallback: first line might just be # Title
        match = re.match(r'^#\s+(.+)$', first_line)
        if match:
            title = match.group(1).strip()
            body_lines = lines[1:]
            while body_lines and not body_lines[0].strip():
                body_lines = body_lines[1:]
            body = ''.join(body_lines).rstrip()
            return title, body

    return None, None


@click.group()
def cli():
    """Clone and sync GitHub PR descriptions."""
    pass


@cli.command()
@click.option('-r', '--repo', help='Repository (owner/repo format)')
@click.option('-b', '--base', help='Base branch (default: main/master)')
def init(repo, base):
    """Initialize a new PR draft in the current directory."""
    # Check if we're already in a PR directory
    if Path('DESCRIPTION.md').exists():
        err("Error: DESCRIPTION.md already exists. Are you already managing a PR here?")
        exit(1)

    # Initialize git repo if needed
    if not Path('.git').exists():
        check_call(['git', 'init', '-q'])
        err("Initialized git repository")

    # Store config if provided
    if repo:
        owner, repo_name = repo.split('/')
        check_call(['git', 'config', 'pr.owner', owner])
        check_call(['git', 'config', 'pr.repo', repo_name])
        err(f"Configured for {repo}")

    if base:
        check_call(['git', 'config', 'pr.base', base])
        err(f"Base branch: {base}")

    # Create initial DESCRIPTION.md
    with open('DESCRIPTION.md', 'w') as f:
        if repo:
            f.write(f"# {repo}#NUMBER Title\n\n")
        else:
            f.write("# owner/repo#NUMBER Title\n\n")
        f.write("Description of the PR...\n")

    err("Created DESCRIPTION.md template")
    err("Edit the file with your PR title and description, then commit")
    err("Use 'github-pr.py open' to create the PR when ready")


@cli.command(name='open')
@click.option('--head', help='Head branch (default: auto-detect from parent repo)')
@click.option('--base', help='Base branch (default: main/master)')
@click.option('-d', '--draft', is_flag=True, help='Create as draft PR')
@click.option('-w', '--web', is_flag=True, help='Open PR in web browser after creating')
def open_pr(head, base, draft, web):
    """Create a new PR from the current draft."""

    # Read DESCRIPTION.md
    if not Path('DESCRIPTION.md').exists():
        err("Error: DESCRIPTION.md not found. Run 'github-pr.py init' first")
        exit(1)

    with open('DESCRIPTION.md', 'r') as f:
        content = f.read()

    lines = content.split('\n')
    if not lines:
        err("Error: DESCRIPTION.md is empty")
        exit(1)

    # Parse title from first line
    first_line = lines[0].strip()
    if first_line.startswith('#'):
        title = first_line.lstrip('#').strip()
        # Remove any [owner/repo#NUM] prefix if present
        title = re.sub(r'^\[?[^/\]]+/[^#\]]+#\d+\]?\s*', '', title)
        title = re.sub(r'^[^/]+/[^#]+#\w+\s+', '', title)  # Handle owner/repo#NUMBER format
    else:
        title = first_line

    # Get body (rest of the file)
    body_lines = lines[1:]
    while body_lines and not body_lines[0].strip():
        body_lines = body_lines[1:]
    body = '\n'.join(body_lines).strip()

    # Get repo info from config or parent directory
    try:
        owner = check_output(['git', 'config', 'pr.owner'], stderr=DEVNULL).decode().strip()
        repo = check_output(['git', 'config', 'pr.repo'], stderr=DEVNULL).decode().strip()
    except:
        # Try to get from parent directory
        parent_dir = Path('..').resolve()
        if (parent_dir / '.git').exists():
            try:
                os.chdir(parent_dir)
                repo_info = check_output(['gh', 'repo', 'view', '--json', 'owner,name']).decode()
                repo_data = json.loads(repo_info)
                owner = repo_data['owner']['login']
                repo = repo_data['name']
                os.chdir(Path(__file__).parent)
            except:
                err("Error: Could not determine repository. Configure with 'github-pr.py init -r owner/repo'")
                exit(1)
        else:
            err("Error: Could not determine repository. Configure with 'github-pr.py init -r owner/repo'")
            exit(1)

    # Get base branch from config or default
    if not base:
        try:
            base = check_output(['git', 'config', 'pr.base'], stderr=DEVNULL).decode().strip()
        except:
            base = 'main'  # Default to main

    # Get head branch - try to auto-detect from parent repo
    if not head:
        parent_dir = Path('..').resolve()
        if (parent_dir / '.git').exists():
            try:
                os.chdir(parent_dir)
                # Use branch resolution
                ref_name, remote_ref = resolve_remote_ref(verbose=False)
                if ref_name:
                    head = ref_name
                    err(f"Auto-detected head branch: {head}")

                if not head:
                    # Fallback to current branch
                    head = check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode().strip()
                    if head == 'HEAD':
                        err("Error: Parent repo is in detached HEAD state. Specify --head explicitly")
                        exit(1)
                os.chdir(Path(__file__).parent)
            except Exception as e:
                err(f"Error detecting head branch: {e}")
                err("Specify --head explicitly")
                exit(1)
        else:
            err("Error: Could not detect head branch. Specify --head explicitly")
            exit(1)

    # Create the PR
    cmd = ['gh', 'pr', 'create',
           '-R', f'{owner}/{repo}',
           '--title', title,
           '--body', body,
           '--base', base,
           '--head', head]

    if draft:
        cmd.append('--draft')

    if web:
        cmd.append('--web')

    try:
        output = check_output(cmd).decode().strip()
        if not web:
            # Extract PR number from URL
            match = re.search(r'/pull/(\d+)', output)
            if match:
                pr_number = match.group(1)
                # Store PR info in git config
                check_call(['git', 'config', 'pr.number', pr_number])
                check_call(['git', 'config', 'pr.url', output])
                err(f"Created PR #{pr_number}: {output}")
                err("PR info stored in git config")
            else:
                err(f"Created PR: {output}")
    except CalledProcessError as e:
        err(f"Error creating PR: {e}")
        exit(1)


@cli.command()
@click.argument('pr_spec', required=False)
@click.option('-d', '--directory', help='Directory to clone into')
def clone(pr_spec, directory):
    """Clone a PR description to a local directory.

    PR_SPEC can be:
    - A PR number (when run from within a repo)
    - owner/repo#number format
    - A full PR URL
    """

    # Parse PR spec
    owner = None
    repo = None
    pr_number = None

    if pr_spec:
        # Try to parse different formats
        # Full URL
        url_match = re.match(r'https://github\.com/([^/]+)/([^/]+)/pull/(\d+)', pr_spec)
        if url_match:
            owner, repo, pr_number = url_match.groups()
        else:
            # owner/repo#number format
            spec_match = re.match(r'([^/]+)/([^#]+)#(\d+)', pr_spec)
            if spec_match:
                owner, repo, pr_number = spec_match.groups()
            else:
                # Just a number (need to be in a repo)
                if pr_spec.isdigit():
                    pr_number = pr_spec
                    # Get owner/repo from current directory
                    try:
                        repo_info = check_output(['gh', 'repo', 'view', '--json', 'owner,name']).decode()
                        repo_data = json.loads(repo_info)
                        owner = repo_data['owner']['login']
                        repo = repo_data['name']
                    except:
                        err("Error: Could not determine repository. Use owner/repo#number format.")
                        exit(1)
    else:
        # Try to infer from current directory
        owner, repo, pr_number = get_pr_info_from_path()

    if not all([owner, repo, pr_number]):
        err("Error: Could not determine PR to clone")
        err("Usage: github-pr clone [PR_NUMBER | owner/repo#NUMBER | PR_URL]")
        exit(1)

    # Determine target directory
    if not directory:
        directory = f'pr{pr_number}'

    target_path = Path(directory)

    # Check if directory already exists
    if target_path.exists():
        err(f"Error: Directory {directory} already exists")
        exit(1)

    # Get PR metadata
    err(f"Fetching PR {owner}/{repo}#{pr_number}...")
    pr_data = get_pr_metadata(owner, repo, pr_number)
    if not pr_data:
        exit(1)

    # Create directory and initialize git repo
    target_path.mkdir(parents=True)
    os.chdir(target_path)

    check_call(['git', 'init', '-q'])

    # Create DESCRIPTION.md with proper format
    desc_file = Path('DESCRIPTION.md')
    title = pr_data['title']
    body = pr_data['body'] or ''
    url = pr_data['url']

    # Strip any gist footer from the body before saving locally
    body_without_footer, _ = extract_gist_footer(body)

    with open(desc_file, 'w') as f:
        f.write(f'# [{owner}/{repo}#{pr_number}]({url}) {title}\n')
        if body_without_footer:
            f.write('\n')
            f.write(body_without_footer)
            if not body_without_footer.endswith('\n'):
                f.write('\n')

    # Store metadata in git config
    check_call(['git', 'config', 'pr.owner', owner])
    check_call(['git', 'config', 'pr.repo', repo])
    check_call(['git', 'config', 'pr.number', str(pr_number)])
    check_call(['git', 'config', 'pr.url', pr_data['url']])

    # Initial commit
    check_call(['git', 'add', 'DESCRIPTION.md'])
    check_call(['git', 'commit', '-m', f'Initial clone of {owner}/{repo}#{pr_number}'])

    err(f"Successfully cloned PR to {target_path}")
    err(f"URL: {pr_data['url']}")


@cli.command()
@click.option('-m', '--message', help='Commit message')
@click.option('-g', '--gist', is_flag=True, help='Also sync to gist')
@click.option('-n', '--dry-run', is_flag=True, help='Show what would be done without making changes')
@click.option('-f/-F', '--footer/--no-footer', default=None,
              help='Add gist footer to PR (default: auto - add if gist exists)')
@click.option('-o/-O', '--open/--no-open', 'open_browser', default=False,
              help='Open PR in browser after pushing')
def push(message, gist, dry_run, footer, open_browser):
    """Push local description changes back to the PR."""

    # Get PR info from current directory
    owner, repo, pr_number = get_pr_info_from_path()

    if not all([owner, repo, pr_number]):
        # Try git config
        try:
            owner = check_output(['git', 'config', 'pr.owner'], stderr=DEVNULL).decode().strip()
            repo = check_output(['git', 'config', 'pr.repo'], stderr=DEVNULL).decode().strip()
            pr_number = check_output(['git', 'config', 'pr.number'], stderr=DEVNULL).decode().strip()
        except:
            err("Error: Could not determine PR from directory or git config")
            exit(1)

    # Read the current description file (from HEAD, not working directory)
    try:
        desc_content = check_output(['git', 'show', 'HEAD:DESCRIPTION.md']).decode()
        # Normalize line endings to \n
        desc_content = desc_content.replace('\r\n', '\n')
    except CalledProcessError:
        err("Error: Could not read DESCRIPTION.md from HEAD")
        err("Make sure you've committed your changes")
        exit(1)

    lines = desc_content.split('\n')
    if not lines:
        err("Error: DESCRIPTION.md is empty")
        exit(1)

    # Parse the file
    first_line = lines[0].strip()
    # Remove the [owner/repo#num] or [owner/repo#num](url) prefix to get the title
    title_match = re.match(r'^#\s*\[([^]]+)\](?:\([^)]+\))?\s*(.*)$', first_line)
    if title_match:
        title = title_match.group(2).strip()
    else:
        # Fallback to just removing the #
        title = first_line.lstrip('#').strip()

    # Get body (skip first line and any immediately following blank lines)
    body_lines = lines[1:]
    while body_lines and not body_lines[0].strip():
        body_lines = body_lines[1:]
    body = '\n'.join(body_lines).rstrip()

    # Check if we have an existing gist
    has_gist = False
    try:
        gist_id = check_output(['git', 'config', 'pr.gist'], stderr=DEVNULL).decode().strip()
        has_gist = bool(gist_id)
    except:
        pass

    # Determine if we should add footer (auto mode: add if gist exists)
    should_add_footer = footer if footer is not None else has_gist

    # Handle gist syncing first (to get URL for footer if needed)
    gist_url = None
    if gist or should_add_footer:
        if dry_run:
            err("[DRY-RUN] Would sync to gist")
            # Try to get existing gist URL
            if has_gist:
                gist_url = f'https://gist.github.com/{gist_id}'
            else:
                gist_url = 'https://gist.github.com/NEW_GIST'
        else:
            if gist or has_gist:  # Sync if explicitly requested or if gist exists
                gist_url = sync_to_gist(owner, repo, pr_number, desc_content, return_url=True)

    # Add footer if we should
    if should_add_footer and gist_url:
        body = add_gist_footer(body, gist_url)

    # Update the PR
    if dry_run:
        err(f"[DRY-RUN] Would update PR {owner}/{repo}#{pr_number}")
        err(f"  Title: {title}")
        err(f"  Body ({len(body)} chars):")
        # Show first few lines of body
        body_preview = body[:500] + ('...' if len(body) > 500 else '')
        for line in body_preview.split('\n'):
            err(f"    {line}")
    else:
        err(f"Updating PR {owner}/{repo}#{pr_number}...")

        cmd = ['gh', 'pr', 'edit', pr_number, '-R', f'{owner}/{repo}']

        if title:
            cmd.extend(['--title', title])

        if body is not None:  # Allow empty body
            cmd.extend(['--body', body])

        try:
            check_call(cmd)
            err("Successfully updated PR")

            # Get PR URL if we need to open it
            if open_browser:
                try:
                    pr_url = check_output(['git', 'config', 'pr.url'], stderr=DEVNULL).decode().strip()
                except:
                    pr_url = f"https://github.com/{owner}/{repo}/pull/{pr_number}"

                import webbrowser
                webbrowser.open(pr_url)
                err(f"Opened: {pr_url}")
        except CalledProcessError as e:
            err(f"Error updating PR: {e}")
            exit(1)


def sync_to_gist(owner, repo, pr_number, content, return_url=False, add_remote=True):
    """Sync PR description to a gist.

    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: PR number
        content: Content to sync to gist
        return_url: If True, return the gist URL with revision instead of None
        add_remote: If True, add gist as a git remote

    Returns:
        None or gist URL with revision if return_url=True
    """

    # Check if we already have a gist ID stored
    try:
        gist_id = check_output(['git', 'config', 'pr.gist'], stderr=DEVNULL).decode().strip()
    except:
        gist_id = None

    # Get configured remote name for gist (default: 'g')
    try:
        gist_remote = check_output(['git', 'config', 'pr.gist-remote'], stderr=DEVNULL).decode().strip()
    except:
        gist_remote = 'g'

    filename = 'DESCRIPTION.md'  # Use actual filename, not temp name
    description = f'{owner}/{repo}#{pr_number} - 2-way sync via github-pr.py (ryan-williams/git-helpers)'
    gist_url = None
    revision = None

    if gist_id:
        # Update existing gist
        err(f"Updating gist {gist_id}...")

        # Update gist description
        try:
            check_call(['gh', 'gist', 'edit', gist_id, '-d', description])
        except:
            pass  # Description update is optional

        # Check if remote exists and push to it
        if add_remote:
            try:
                # Commit any changes and push to gist
                check_call(['git', 'add', 'DESCRIPTION.md'])
                check_call(['git', 'commit', '-m', f'Update PR description for {owner}/{repo}#{pr_number}'])
            except:
                pass  # May already be committed

            try:
                check_call(['git', 'push', gist_remote, 'main', '--force'])
                err(f"Pushed to gist remote '{gist_remote}'")
            except:
                err(f"Warning: Could not push to gist remote '{gist_remote}'")

        # Get the latest revision SHA
        try:
            gist_info = check_output(['gh', 'api', f'gists/{gist_id}', '--jq', '.history[0].version']).decode().strip()
            revision = gist_info
        except:
            revision = None

        if revision:
            gist_url = f"https://gist.github.com/{gist_id}/{revision}"
        else:
            gist_url = f"https://gist.github.com/{gist_id}"
        err(f"Updated gist: {gist_url}")
    else:
        # Create new gist
        err("Creating new gist...")

        # Ensure DESCRIPTION.md exists with latest content
        desc_file = Path('DESCRIPTION.md')
        with open(desc_file, 'w') as f:
            f.write(content)

        try:
            # Create gist from actual DESCRIPTION.md file (secret by default)
            output = check_output(['gh', 'gist', 'create', '-d', description, 'DESCRIPTION.md']).decode().strip()
            # Extract gist ID from URL
            match = re.search(r'gist\.github\.com/([a-f0-9]+)', output)
            if match:
                gist_id = match.group(1)
                check_call(['git', 'config', 'pr.gist', gist_id])

                # Add gist as a remote if requested
                if add_remote:
                    gist_ssh_url = f"git@gist.github.com:{gist_id}.git"
                    try:
                        # Check if remote already exists
                        existing_url = check_output(['git', 'remote', 'get-url', gist_remote], stderr=DEVNULL).decode().strip()
                        if existing_url != gist_ssh_url:
                            # Update existing remote
                            check_call(['git', 'remote', 'set-url', gist_remote, gist_ssh_url])
                            err(f"Updated remote '{gist_remote}' to {gist_ssh_url}")
                    except:
                        # Add new remote
                        check_call(['git', 'remote', 'add', gist_remote, gist_ssh_url])
                        err(f"Added remote '{gist_remote}': {gist_ssh_url}")

                # Get the revision SHA for the newly created gist
                try:
                    gist_info = check_output(['gh', 'api', f'gists/{gist_id}', '--jq', '.history[0].version']).decode().strip()
                    revision = gist_info
                    gist_url = f"https://gist.github.com/{gist_id}/{revision}"
                except:
                    gist_url = output  # Fallback to the output URL

                err(f"Created gist: {gist_url}")
        except CalledProcessError as e:
            err(f"Error creating gist: {e}")
            return None

    if return_url:
        return gist_url


@cli.command()
@click.option('-c', '--color', type=click.Choice(['auto', 'always', 'never']), default='auto',
              help='When to use colored output (default: auto)')
def diff(color):
    """Show differences between local and remote PR descriptions."""

    # Determine if we should use color
    use_color = False
    if color == 'always':
        use_color = True
    elif color == 'auto':
        use_color = sys.stdout.isatty()

    # ANSI color codes
    RED = '\033[31m' if use_color else ''
    GREEN = '\033[32m' if use_color else ''
    CYAN = '\033[36m' if use_color else ''
    YELLOW = '\033[33m' if use_color else ''
    RESET = '\033[0m' if use_color else ''
    BOLD = '\033[1m' if use_color else ''

    # Get PR info from current directory
    owner, repo, pr_number = get_pr_info_from_path()

    if not all([owner, repo, pr_number]):
        # Try git config
        try:
            owner = check_output(['git', 'config', 'pr.owner'], stderr=DEVNULL).decode().strip()
            repo = check_output(['git', 'config', 'pr.repo'], stderr=DEVNULL).decode().strip()
            pr_number = check_output(['git', 'config', 'pr.number'], stderr=DEVNULL).decode().strip()
        except:
            err("Error: Could not determine PR from directory or git config")
            exit(1)

    # Get remote PR data
    err(f"Fetching PR {owner}/{repo}#{pr_number}...")
    pr_data = get_pr_metadata(owner, repo, pr_number)
    if not pr_data:
        exit(1)

    # Read local description
    try:
        desc_content = check_output(['git', 'show', 'HEAD:DESCRIPTION.md']).decode()
        # Normalize line endings to \n
        desc_content = desc_content.replace('\r\n', '\n')
    except CalledProcessError:
        err("Error: Could not read DESCRIPTION.md from HEAD")
        err("Make sure you've committed your changes")
        exit(1)

    # Parse local file to get title and body
    lines = desc_content.split('\n')
    if not lines:
        err("Error: DESCRIPTION.md is empty")
        exit(1)

    first_line = lines[0].strip()
    title_match = re.match(r'^#\s*\[([^]]+)\](?:\([^)]+\))?\s*(.*)$', first_line)
    if title_match:
        local_title = title_match.group(2).strip()
    else:
        local_title = first_line.lstrip('#').strip()

    body_lines = lines[1:]
    while body_lines and not body_lines[0].strip():
        body_lines = body_lines[1:]
    local_body = '\n'.join(body_lines).rstrip()

    # Get remote title and body (already normalized in get_pr_metadata)
    remote_title = pr_data['title']
    remote_body = (pr_data['body'] or '').rstrip()

    # Compare titles
    if local_title != remote_title:
        err(f"\n{BOLD}{YELLOW}=== Title Differences ==={RESET}")
        err(f"{GREEN}Local: {RESET} {local_title}")
        err(f"{RED}Remote:{RESET} {remote_title}")
    else:
        err(f"\n{BOLD}{CYAN}=== Title: No differences ==={RESET}")

    # Compare bodies
    if local_body != remote_body:
        err(f"\n{BOLD}{YELLOW}=== Body Differences ==={RESET}")

        # Generate a unified diff
        local_lines = local_body.splitlines(keepends=True)
        remote_lines = remote_body.splitlines(keepends=True)

        diff_lines = difflib.unified_diff(
            remote_lines,
            local_lines,
            fromfile='Remote PR',
            tofile='Local DESCRIPTION.md',
            lineterm=''
        )

        # Color the diff output
        for line in diff_lines:
            if line.startswith('+++'):
                print(f"{BOLD}{line.rstrip()}{RESET}")
            elif line.startswith('---'):
                print(f"{BOLD}{line.rstrip()}{RESET}")
            elif line.startswith('@@'):
                print(f"{CYAN}{line.rstrip()}{RESET}")
            elif line.startswith('+'):
                print(f"{GREEN}{line.rstrip()}{RESET}")
            elif line.startswith('-'):
                print(f"{RED}{line.rstrip()}{RESET}")
            else:
                print(line.rstrip())
    else:
        err(f"\n{BOLD}{CYAN}=== Body: No differences ==={RESET}")


@cli.command()
@click.option('-m', '--message', help='Commit message')
@click.option('-g', '--gist', is_flag=True, help='Also sync to gist')
@click.option('-n', '--dry-run', is_flag=True, help='Show what would be done')
@click.option('-f/-F', '--footer/--no-footer', default=None,
              help='Add gist footer to PR (default: auto - add if gist exists)')
@click.option('-o/-O', '--open/--no-open', 'open_browser', default=False,
              help='Open PR in browser after pulling')
def pull(message, gist, dry_run, footer, open_browser):
    """Pull latest from PR and optionally push changes back."""
    # First pull
    err("Pulling latest from PR...")

    # Get PR info
    owner, repo, pr_number = get_pr_info_from_path()

    if not all([owner, repo, pr_number]):
        try:
            owner = check_output(['git', 'config', 'pr.owner'], stderr=DEVNULL).decode().strip()
            repo = check_output(['git', 'config', 'pr.repo'], stderr=DEVNULL).decode().strip()
            pr_number = check_output(['git', 'config', 'pr.number'], stderr=DEVNULL).decode().strip()
        except:
            err("Error: Could not determine PR")
            exit(1)

    # Get latest PR data
    pr_data = get_pr_metadata(owner, repo, pr_number)
    if not pr_data:
        exit(1)

    # Update local file
    desc_file = Path('DESCRIPTION.md')
    title = pr_data['title']
    body = pr_data['body'] or ''
    url = pr_data['url']

    # Strip any gist footer from the body before saving locally
    body_without_footer, _ = extract_gist_footer(body)

    with open(desc_file, 'w') as f:
        f.write(f'# [{owner}/{repo}#{pr_number}]({url}) {title}\n')
        if body_without_footer:
            f.write('\n')
            f.write(body_without_footer)
            if not body_without_footer.endswith('\n'):
                f.write('\n')

    # Check if there are changes
    try:
        check_output(['git', 'diff', '--exit-code', 'DESCRIPTION.md'], stderr=DEVNULL)
        err("No changes from PR")
    except CalledProcessError:
        # There are changes, commit them
        if not dry_run:
            check_call(['git', 'add', 'DESCRIPTION.md'])
            check_call(['git', 'commit', '-m', f'Sync from PR (pulled latest)'])
            err("Pulled and committed changes from PR")
        else:
            err("[DRY-RUN] Would pull and commit changes from PR")

    # Now push our version back
    err("Pushing to PR...")
    push.callback(message, gist, dry_run, footer, open_browser)


if __name__ == '__main__':
    cli()
