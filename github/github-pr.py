#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "click",
# ]
# ///
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

from click import argument, Choice, group, option

# Add parent directory to path for local imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Helper for printing to stderr
err = partial(print, file=stderr)

from util.branch_resolution import resolve_remote_ref


def get_pr_info_from_path(path: Path | None = None) -> tuple[str | None, str | None, str | None]:
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


def get_pr_metadata(owner: str, repo: str, pr_number: str) -> dict | None:
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


def extract_gist_footer(body: str | None) -> tuple[str | None, str | None]:
    """Extract gist footer from body and return (body_without_footer, gist_url)."""
    import re

    if not body:
        return body, None

    lines = body.split('\n')

    # Check for visible footer format (last 3 lines: empty, ---, "Synced with...")
    if len(lines) >= 3:
        if (lines[-3].strip() == '' and
            lines[-2].strip() == '---' and
            'Synced with [gist](' in lines[-1]):
            # Extract URL from markdown link
            match = re.search(r'\[gist\]\((https://gist\.github\.com/[a-f0-9]+(?:/[a-f0-9]+)?)\)', lines[-1])
            if match:
                gist_url = match.group(1)
                # Remove the footer (last 3 lines)
                body_without_footer = '\n'.join(lines[:-3]).rstrip()
                return body_without_footer, gist_url

    # Check if last line is a hidden gist footer (handle both old and new formats)
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


def add_gist_footer(body: str | None, gist_url: str, visible: bool = False) -> str:
    """Add or update gist footer in body."""
    body_without_footer, _ = extract_gist_footer(body)

    if visible:
        # Extract gist ID and revision from URL if available
        # URL format: https://gist.github.com/user/gist_id or https://gist.github.com/gist_id/revision
        import re
        gist_match = re.search(r'gist\.github\.com/(?:[^/]+/)?([a-f0-9]+)(?:/([a-f0-9]+))?', gist_url)
        if gist_match:
            gist_id = gist_match.group(1)
            revision = gist_match.group(2)
            if revision:
                gist_link = f'https://gist.github.com/{gist_id}/{revision}'
            else:
                gist_link = f'https://gist.github.com/{gist_id}'
        else:
            gist_link = gist_url

        footer = f'\n---\n\nSynced with [gist]({gist_link}) via [github-pr.py](https://github.com/ryan-williams/git-helpers/blob/main/github/github-pr.py)'
    else:
        footer = f'<!-- Synced with {gist_url} via [github-pr.py](https://github.com/ryan-williams/git-helpers/blob/main/github/github-pr.py) -->'

    if body_without_footer:
        return f'{body_without_footer}\n\n{footer}'
    else:
        return footer


def upload_image_to_github(image_path: str, owner: str, repo: str) -> str | None:
    """Upload an image to GitHub and get the user-attachments URL.

    GitHub stores PR images in a special user-attachments area.
    We use the gh CLI to interact with GitHub's API.
    """
    import base64
    import mimetypes

    if not Path(image_path).exists():
        err(f"Warning: Image file not found: {image_path}")
        return None

    # Determine MIME type
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type or not mime_type.startswith('image/'):
        err(f"Warning: {image_path} doesn't appear to be an image (mime: {mime_type})")
        return None

    # Read and encode the image
    with open(image_path, 'rb') as f:
        image_data = f.read()
    encoded = base64.b64encode(image_data).decode('utf-8')

    # Create a data URL
    data_url = f"data:{mime_type};base64,{encoded}"

    # Use gh api to upload via markdown rendering
    # This is a bit of a hack - we render markdown with an image to trigger upload
    markdown_with_image = f'![image]({data_url})'

    try:
        # Use GitHub's markdown API to process the image
        cmd = [
            'gh', 'api',
            '--method', 'POST',
            '/markdown',
            '-f', f'text={markdown_with_image}',
            '-f', 'mode=gfm',
            '-f', f'context={owner}/{repo}'
        ]
        result = check_output(cmd, stderr=DEVNULL).decode()

        # Extract the uploaded image URL from the rendered HTML
        import re
        match = re.search(r'src="(https://github\.com/user-attachments/assets/[^"]+)"', result)
        if match:
            url = match.group(1)
            err(f"Uploaded {image_path} -> {url}")
            return url
        else:
            err(f"Warning: Could not extract URL from upload response for {image_path}")
            return None
    except CalledProcessError as e:
        err(f"Warning: Failed to upload {image_path}: {e}")
        return None


def process_images_in_description(body: str, owner: str, repo: str, dry_run: bool = False) -> str:
    """Find local image references and upload them to GitHub."""
    import re

    if dry_run:
        # Just find and report what would be uploaded
        pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        matches = re.findall(pattern, body)
        for alt_text, path in matches:
            if not path.startswith('http'):
                err(f"[DRY-RUN] Would upload image: {path}")
        return body

    def replace_image(match):
        alt_text = match.group(1)
        path = match.group(2)

        # Skip if already a URL
        if path.startswith('http'):
            return match.group(0)

        # Upload the image
        url = upload_image_to_github(path, owner, repo)
        if url:
            # Use <img> tag for consistency with GitHub's format
            return f'<img alt="{alt_text}" src="{url}" />'
        else:
            # Keep original if upload failed
            return match.group(0)

    # Replace markdown image references
    pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    updated_body = re.sub(pattern, replace_image, body)

    return updated_body


def read_description_file(path: Path) -> tuple[str | None, str | None]:
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


@group()
def cli():
    """Clone and sync GitHub PR descriptions."""
    pass


@cli.command()
@option('-r', '--repo', help='Repository (owner/repo format)')
@option('-b', '--base', help='Base branch (default: main/master)')
def init(
    repo: str | None,
    base: str | None,
) -> None:
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
@option('--head', help='Head branch (default: auto-detect from parent repo)')
@option('--base', help='Base branch (default: main/master)')
@option('-d', '--draft', is_flag=True, help='Create as draft PR')
@option('-w', '--web', is_flag=True, help='Open PR in web browser after creating')
def open_pr(
    head: str | None,
    base: str | None,
    draft: bool,
    web: bool,
) -> None:
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
@argument('pr_spec', required=False)
@option('-d', '--directory', help='Directory to clone into')
def clone(
    pr_spec: str | None,
    directory: str | None,
) -> None:
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
@option('-g', '--gist', is_flag=True, help='Also sync to gist')
@option('-n', '--dry-run', is_flag=True, help='Show what would be done without making changes')
@option('-f', '--footer', count=True, help='Footer level: -f = hidden footer, -ff = visible footer')
@option('-F', '--no-footer', is_flag=True, help='Disable footer completely')
@option('-o/-O', '--open/--no-open', 'open_browser', default=False, help='Open PR in browser after pushing')
@option('-i', '--images', is_flag=True, help='Upload local images and replace references')
@option('-p/-P', '--private/--public', 'gist_private', default=None, help='Gist visibility: -p = private, -P = public (default: match repo visibility)')
def push(
    gist: bool,
    dry_run: bool,
    footer: int,
    no_footer: bool,
    open_browser: bool,
    images: bool,
    gist_private: bool | None,
) -> None:
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

    # Process images if requested
    if images:
        err("Processing images in description...")
        body = process_images_in_description(body, owner, repo, dry_run)

    # Check if we have an existing gist
    has_gist = False
    try:
        gist_id = check_output(['git', 'config', 'pr.gist'], stderr=DEVNULL).decode().strip()
        has_gist = bool(gist_id)
    except:
        pass

    # Determine footer behavior
    if no_footer:
        # -F flag: disable footer completely
        should_add_footer = False
        footer_visible = False
    elif footer == 0:
        # No -f flag: auto mode (add footer if gist exists)
        should_add_footer = has_gist
        footer_visible = False  # Default to hidden
    elif footer == 1:
        # -f: Hidden footer (HTML comment)
        should_add_footer = True
        footer_visible = False
        gist = True  # Ensure we sync to gist if adding footer
    elif footer >= 2:
        # -ff: Visible footer (markdown)
        should_add_footer = True
        footer_visible = True
        gist = True  # Ensure we sync to gist if adding footer
    else:
        should_add_footer = False
        footer_visible = False

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
                gist_url = sync_to_gist(owner, repo, pr_number, desc_content, return_url=True, gist_private=gist_private)

    # Add footer if we should
    if should_add_footer and gist_url:
        body = add_gist_footer(body, gist_url, visible=footer_visible)
        err(f"Added {'visible' if footer_visible else 'hidden'} footer with gist URL: {gist_url}")
    elif should_add_footer and not gist_url:
        err("Warning: Should add footer but no gist URL available")

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
            # Use --body-file to avoid command line length issues and special character problems
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write(body)
                body_file = f.name

            cmd.extend(['--body-file', body_file])

        try:
            check_call(cmd)
            if body is not None:
                os.unlink(body_file)  # Clean up temp file
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


def sync_to_gist(
    owner: str,
    repo: str,
    pr_number: str,
    content: str,
    return_url: bool = False,
    add_remote: bool = True,
    gist_private: bool | None = None,
) -> str | None:
    """Sync PR description to a gist.

    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: PR number
        content: Content to sync to gist
        return_url: If True, return the gist URL with revision instead of None
        add_remote: If True, add gist as a git remote
        gist_private: If True, create private gist; if False, create public; if None, match repo visibility

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

    # Determine gist visibility
    if gist_private is not None:
        # Explicit visibility specified
        is_public = not gist_private  # Invert: if private flag is True, public is False
        err(f"Using explicit gist visibility: {'PUBLIC' if is_public else 'PRIVATE'}")
    else:
        # Check repository visibility to determine gist visibility
        is_public = True  # Default to public
        try:
            repo_info = check_output(['gh', 'repo', 'view', f'{owner}/{repo}', '--json', 'visibility']).decode()
            repo_data = json.loads(repo_info)
            is_public = repo_data.get('visibility', 'PUBLIC').upper() == 'PUBLIC'
            err(f"Repository visibility: {'PUBLIC' if is_public else 'PRIVATE'}, gist will match")
        except Exception as e:
            err(f"Warning: Could not determine repository visibility, defaulting to public gist: {e}")

    filename = 'DESCRIPTION.md'  # Use actual filename, not temp name
    description = f'{owner}/{repo}#{pr_number} - 2-way sync via github-pr.py (ryan-williams/git-helpers)'
    gist_url = None
    revision = None

    if gist_id:
        # Update existing gist
        err(f"Updating gist {gist_id}...")

        # Update gist description using API to avoid editor
        try:
            check_call(['gh', 'api', f'gists/{gist_id}', '-X', 'PATCH',
                       '-f', f'description={description}'], stderr=DEVNULL)
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
        err(f"Creating new {'public' if is_public else 'secret'} gist...")

        # Ensure DESCRIPTION.md exists with latest content
        desc_file = Path('DESCRIPTION.md')
        with open(desc_file, 'w') as f:
            f.write(content)

        try:
            # Create gist from actual DESCRIPTION.md file (visibility based on repo)
            import subprocess
            gist_cmd = ['gh', 'gist', 'create', '-d', description]
            if is_public:
                gist_cmd.append('--public')
            gist_cmd.append('DESCRIPTION.md')
            result = subprocess.run(gist_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                err(f"Error creating gist: {result.stderr}")
                return None
            output = result.stdout.strip()
            err(f"Gist create output: {output}")
            # Extract gist ID from URL (format: https://gist.github.com/username/gist_id or https://gist.github.com/gist_id)
            match = re.search(r'gist\.github\.com/(?:[^/]+/)?([a-f0-9]+)', output)
            if match:
                gist_id = match.group(1)
                check_call(['git', 'config', 'pr.gist', gist_id])
                err(f"Stored gist ID: {gist_id}")

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

                    # Fetch from the gist remote first
                    try:
                        check_call(['git', 'fetch', gist_remote], stderr=DEVNULL)
                    except:
                        pass  # Fetch might fail if gist is empty

                    # Set up branch tracking
                    try:
                        current_branch = check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], stderr=DEVNULL).decode().strip()
                        check_call(['git', 'branch', '--set-upstream-to', f'{gist_remote}/main', current_branch])
                        err(f"Set {current_branch} to track {gist_remote}/main")
                    except Exception as e:
                        err(f"Could not set up branch tracking: {e}")

                    # Commit and push to the gist
                    try:
                        # Check if there are uncommitted changes
                        check_call(['git', 'diff', '--quiet', 'DESCRIPTION.md'], stderr=DEVNULL)
                    except:
                        # There are changes, commit them
                        check_call(['git', 'add', 'DESCRIPTION.md'])
                        check_call(['git', 'commit', '-m', f'Sync PR {owner}/{repo}#{pr_number} to gist'])

                    # Push to the gist remote
                    try:
                        check_call(['git', 'push', gist_remote, 'main', '--force'])
                        err(f"Pushed to gist remote '{gist_remote}'")
                    except Exception as e:
                        err(f"Warning: Could not push to gist remote '{gist_remote}': {e}")

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
@argument('files', nargs=-1, required=True)
@option('-b', '--branch', default='assets', help='Branch name in gist (default: assets)')
@option('-f', '--format', type=Choice(['url', 'markdown', 'img', 'auto']), default='auto', help='Output format (default: auto - img for images, url for others)')
@option('-a', '--alt', help='Alt text for markdown/img format')
def upload(
    files: tuple[str, ...],
    branch: str,
    format: str,
    alt: str | None,
) -> None:
    """Upload images to the PR's gist and get URLs."""
    from subprocess import check_call
    import gist_upload

    # Get PR info
    owner, repo, pr_number = get_pr_info_from_path()

    if not all([owner, repo, pr_number]):
        try:
            owner = check_output(['git', 'config', 'pr.owner'], stderr=DEVNULL).decode().strip()
            repo = check_output(['git', 'config', 'pr.repo'], stderr=DEVNULL).decode().strip()
            pr_number = check_output(['git', 'config', 'pr.number'], stderr=DEVNULL).decode().strip()
        except:
            err("Error: Could not determine PR from directory or git config")
            exit(1)

    # Get or create gist
    try:
        gist_id = check_output(['git', 'config', 'pr.gist'], stderr=DEVNULL).decode().strip()
    except:
        gist_id = None

    if not gist_id:
        # Create a gist for this PR
        err("Creating gist for PR assets...")
        description = f'{owner}/{repo}#{pr_number} assets'
        desc_content = "# PR Assets\nImage assets for PR"

        gist_id = gist_upload.create_gist(description, desc_content)
        if gist_id:
            check_call(['git', 'config', 'pr.gist', gist_id])
            err(f"Created gist: {gist_id}")
        else:
            err("Error: Could not create gist")
            exit(1)

    # Check if we're already in a gist clone
    is_local_clone = False
    remote_name = None
    try:
        # Check all remotes to see if any point to this gist
        remotes = check_output(['git', 'remote']).decode().strip().split('\n')
        for remote in remotes:
            if not remote:
                continue
            try:
                remote_url = check_output(['git', 'remote', 'get-url', remote], stderr=DEVNULL).decode().strip()
                if f'gist.github.com:{gist_id}' in remote_url or f'gist.github.com/{gist_id}' in remote_url:
                    is_local_clone = True
                    remote_name = remote
                    err(f"Already in gist repository with remote '{remote}'")
                    break
            except:
                continue
    except:
        pass

    # Prepare files for upload
    file_list = []
    for file_path in files:
        filename = Path(file_path).name
        file_list.append((file_path, filename))

    # Upload files using the library
    results = gist_upload.upload_files_to_gist(
        file_list,
        gist_id,
        branch=branch,
        is_local_clone=is_local_clone,
        commit_msg=f'Add assets for {owner}/{repo}#{pr_number}',
        remote_name=remote_name
    )

    # Output formatted results
    for orig_name, safe_name, url in results:
        output = gist_upload.format_output(orig_name, url, format, alt)
        print(output)

    if not results:
        exit(1)


@cli.command()
@option('-c', '--color', type=Choice(['auto', 'always', 'never']), default='auto', help='When to use colored output (default: auto)')
def diff(
    color: str,
) -> None:
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

    # Strip footer from local body for comparison
    local_body_without_footer, _ = extract_gist_footer(local_body)

    # Get remote title and body (already normalized in get_pr_metadata)
    remote_title = pr_data['title']
    remote_body = (pr_data['body'] or '').rstrip()

    # Strip footer from remote body for comparison
    remote_body_without_footer, _ = extract_gist_footer(remote_body)

    # Compare titles
    if local_title != remote_title:
        err(f"\n{BOLD}{YELLOW}=== Title Differences ==={RESET}")
        err(f"{GREEN}Local: {RESET} {local_title}")
        err(f"{RED}Remote:{RESET} {remote_title}")
    else:
        err(f"\n{BOLD}{CYAN}=== Title: No differences ==={RESET}")

    # Compare bodies (without footers)
    if local_body_without_footer != remote_body_without_footer:
        err(f"\n{BOLD}{YELLOW}=== Body Differences ==={RESET}")

        # Generate a unified diff
        local_lines = local_body_without_footer.splitlines(keepends=True)
        remote_lines = remote_body_without_footer.splitlines(keepends=True)

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
@option('-g', '--gist', is_flag=True, help='Also sync to gist')
@option('-n', '--dry-run', is_flag=True, help='Show what would be done')
@option('-f/-F', '--footer/--no-footer', default=None, help='Add gist footer to PR (default: auto - add if gist exists)')
@option('-o/-O', '--open/--no-open', 'open_browser', default=False, help='Open PR in browser after pulling')
@option('-p/-P', '--private/--public', 'gist_private', default=None, help='Gist visibility: -p = private, -P = public (default: match repo visibility)')
def pull(
    gist: bool,
    dry_run: bool,
    footer: bool | None,
    open_browser: bool,
    gist_private: bool | None,
) -> None:
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
    # Convert pull's footer boolean to push's footer count
    footer_count = 1 if footer else 0 if footer is False else 0
    push.callback(gist, dry_run, footer_count, no_footer=False, open_browser=open_browser, images=False, gist_private=gist_private)


if __name__ == '__main__':
    cli()
