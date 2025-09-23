#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "click",
#     "utz",
# ]
# ///
"""Clone and sync GitHub PR descriptions with local folders and GitHub gists."""

import re
import sys
import difflib
from functools import partial
from os import chdir, unlink
from os.path import abspath, dirname, exists, join
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
import webbrowser

from click import Choice, group
from utz import proc, err, cd
from utz.cli import arg, flag, opt

# Add parent directory to path for local imports
sys.path.insert(0, dirname(dirname(abspath(__file__))))

from util.branch_resolution import resolve_remote_ref

# Constants
DEFAULT_GIST_REMOTE = 'g'

# Compiled regex patterns
PR_LINK_REF_PATTERN = re.compile(r'^#\s*\[([^/]+/[^#]+#\d+)]\s+(.*)$')  # # [org/repo#123] Title
PR_INLINE_LINK_PATTERN = re.compile(r'^#\s*\[([^/]+)/([^#]+)#(\d+)](?:\([^)]+\))?\s*(.*)$')  # # [org/repo#123](url) Title
PR_TITLE_PATTERN = re.compile(r'^#\s*\[([^]]+)](?:\([^)]+\))?\s*(.*)$')  # # [owner/repo#num](url) Title
PR_FILENAME_PATTERN = re.compile(r'^([^#]+)#(\d+)\.md$')  # repo#123.md
PR_DIR_PATTERN = re.compile(r'^pr(\d+)$')  # pr123
LINK_DEF_PATTERN = re.compile(r'^\[([^]]+)]:\s*https?://')  # [ref]: url (matches at line start)
GIST_ID_PATTERN = re.compile(r'gist\.github\.com[:/]([a-f0-9]{20,32})')  # GitHub gist IDs are typically 20-32 hex chars
GIST_URL_PATTERN = re.compile(r'https://gist\.github\.com/[a-f0-9]+(?:/[a-f0-9]+)?')  # Full gist URL
GIST_URL_WITH_USER_PATTERN = re.compile(r'gist\.github\.com/(?:[^/]+/)?([a-f0-9]+)(?:/([a-f0-9]+))?')  # Gist URL with optional user
GIST_FOOTER_VISIBLE_PATTERN = re.compile(r'\[gist\]\((https://gist\.github\.com/[a-f0-9]+(?:/[a-f0-9]+)?)\)')  # [gist](url) in markdown
GIST_FOOTER_HIDDEN_PATTERN = re.compile(r'<!-- Synced with (https://gist\.github\.com/[a-f0-9]+(?:/[a-f0-9]+)?)')  # HTML comment footer
GITHUB_URL_PATTERN = re.compile(r'github\.com[:/]([^/]+)/([^/\s]+?)(?:\.git)?$')  # GitHub URL pattern
GITHUB_PR_URL_PATTERN = re.compile(r'https://github\.com/([^/]+)/([^/]+)/pull/(\d+)')  # Full PR URL
PR_SPEC_PATTERN = re.compile(r'([^/]+)/([^#]+)#(\d+)')  # owner/repo#number format
H1_TITLE_PATTERN = re.compile(r'^#\s+(.+)$')  # # Title
PR_LINK_IN_H1_PATTERN = re.compile(r'^#\s*\[[^]]+]')  # Check if H1 has [...]


def extract_title_from_first_line(first_line: str) -> str:
    """Extract title from first line of PR description, removing PR reference."""
    title_match = PR_TITLE_PATTERN.match(first_line.strip())
    if title_match:
        return title_match.group(2).strip()
    else:
        # Fallback to just removing the #
        return first_line.strip().lstrip('#').strip()


def parse_pr_spec(pr_spec: str) -> tuple[str | None, str | None, str | None]:
    """Parse PR specification in various formats.

    Args:
        pr_spec: Can be:
            - Full URL: https://github.com/owner/repo/pull/123
            - Short format: owner/repo#123
            - Just number: 123 (requires being in repo)

    Returns:
        Tuple of (owner, repo, pr_number) or (None, None, number) for just number
    """
    # Full URL
    url_match = GITHUB_PR_URL_PATTERN.match(pr_spec)
    if url_match:
        return url_match.groups()

    # owner/repo#number format
    spec_match = PR_SPEC_PATTERN.match(pr_spec)
    if spec_match:
        return spec_match.groups()

    # Just a number
    if pr_spec.isdigit():
        return None, None, pr_spec

    return None, None, None


def create_gist(
    file_path: str | Path,
    description: str,
    is_public: bool = False,
    store_id: bool = True,
) -> str:
    """Create a GitHub gist and optionally store its ID in git config.

    Args:
        file_path: Path to the file to upload
        description: Description for the gist
        is_public: Whether the gist should be public (default: secret/unlisted)
        store_id: Whether to store the gist ID in git config (default: True)

    Returns:
        Gist ID
    """
    # Create gist using gh CLI
    cmd = [
        'gh', 'gist', 'create',
        '--desc', description,
        '--public' if is_public else None,
        file_path
    ]
    result_str = proc.text(*cmd, log=None)
    # Extract gist ID from URL (last part of the path)
    gist_url = result_str.strip()
    gist_id = gist_url.split('/')[-1]

    if store_id:
        # Store gist ID in git config
        proc.run('git', 'config', 'pr.gist', gist_id, log=None)

    err(f"Created gist: {gist_url}")
    return gist_id


def find_gist_remote() -> str | None:
    """Find the gist remote intelligently.

    Returns:
        Remote name if found, None otherwise

    Priority:
    1. Check git config pr.gist-remote
    2. Look for any remote pointing to gist.github.com
    3. If only one remote exists and it's a gist, use it
    4. Fall back to DEFAULT_GIST_REMOTE if it exists
    """
    # First check config
    configured = proc.line('git', 'config', 'pr.gist-remote', err_ok=True)
    if configured:
        return configured

    # Get all remotes
    remotes = proc.lines('git', 'remote', '-v', err_ok=True) or []
    if not remotes:
        return None

    # Parse remotes to find gist URLs
    gist_remotes = []
    all_remotes = {}
    for line in remotes:
        if '\t' in line:
            name, url = line.split('\t', 1)
            if 'gist.github.com' in url:
                if name not in gist_remotes:
                    gist_remotes.append(name)
            all_remotes[name] = url

    # If we found exactly one gist remote, use it
    if len(gist_remotes) == 1:
        return gist_remotes[0]

    # If multiple gist remotes, prefer DEFAULT_GIST_REMOTE if it's one of them
    if DEFAULT_GIST_REMOTE in gist_remotes:
        return DEFAULT_GIST_REMOTE

    # If we have any gist remote, use the first one
    if gist_remotes:
        return gist_remotes[0]

    # Check if DEFAULT_GIST_REMOTE exists even if not a gist URL
    if DEFAULT_GIST_REMOTE in all_remotes:
        return DEFAULT_GIST_REMOTE

    return None


def get_pr_info_from_path(path: Path | None = None) -> tuple[str | None, str | None, str | None]:
    """Extract PR info from directory structure or git config."""
    if path is None:
        path = Path.cwd()
    else:
        path = Path(path)

    # First, check if we have PR info in git config (highest priority)
    owner = proc.line('git', 'config', 'pr.owner', err_ok=True, log=None)
    repo = proc.line('git', 'config', 'pr.repo', err_ok=True, log=None)
    pr_number = proc.line('git', 'config', 'pr.number', err_ok=True, log=None)
    if owner and repo and pr_number:
        return owner, repo, pr_number

    # Look for pr<number> pattern in current or parent directories
    current = path
    pr_number = None
    repo_path = None

    while current != current.parent:
        # Check if this dir matches pr<number>
        match = PR_DIR_PATTERN.match(current.name)
        if match:
            pr_number = match.group(1)
            repo_path = current.parent
            break
        current = current.parent

    if not pr_number:
        # Check if we're in a directory with DESCRIPTION.md that has metadata
        desc_file = path / 'DESCRIPTION.md'
        if exists(desc_file):
            with open(desc_file, 'r') as f:
                first_line = f.readline().strip()
                # Look for pattern like # [owner/repo#123] or # [owner/repo#123](url)
                match = PR_INLINE_LINK_PATTERN.match(first_line)
                if match:
                    return match.group(1), match.group(2), match.group(3)

        err("Error: Could not determine PR number from directory structure")
        err("Expected to be in a directory named 'pr<number>' or have DESCRIPTION.md with PR metadata")
        return None, None, None

    # Get repo info from parent directory
    chdir(repo_path)

    # Try to get owner/repo from git remote
    try:
        # Get the default remote
        remotes = proc.lines('git', 'remote', err_ok=True, log=None) or []

        for remote in ['origin', 'upstream'] + remotes:
            if not remote:
                continue
            try:
                url = proc.line('git', 'remote', 'get-url', remote, err_ok=True, log=None) or ''
                # Match GitHub URLs
                match = GITHUB_URL_PATTERN.search(url)
                if match:
                    owner = match.group(1)
                    repo = match.group(2)
                    return owner, repo, pr_number
            except Exception as e:
                # Log but continue checking other remotes
                err(f"Warning: Could not get URL for remote {remote}: {e}")
                continue
    except Exception as e:
        err(f"Error while checking git remotes: {e}")
        raise

    err("Error: Could not determine repository from git remotes")
    return None, None, pr_number


def get_pr_metadata(owner: str, repo: str, pr_number: str) -> dict | None:
    """Get PR metadata from GitHub."""
    try:
        data = proc.json('gh', 'pr', 'view', pr_number, '-R', f'{owner}/{repo}', '--json', 'title,body,number,url', log=None)
        # Normalize line endings from GitHub (convert \r\n to \n)
        if data.get('body'):
            data['body'] = data['body'].replace('\r\n', '\n')
        return data
    except Exception as e:
        err(f"Error fetching PR metadata: {e}")
        return None


def extract_gist_footer(body: str | None) -> tuple[str | None, str | None]:
    """Extract gist footer from body and return (body_without_footer, gist_url)."""

    if not body:
        return body, None

    lines = body.split('\n')

    # Check for visible footer format (last 3 lines: empty, ---, "Synced with...")
    if len(lines) >= 3:
        if (lines[-3].strip() == '' and
            lines[-2].strip() == '---' and
            'Synced with [gist](' in lines[-1]):
            # Extract URL from markdown link
            match = GIST_FOOTER_VISIBLE_PATTERN.search(lines[-1])
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
            match = GIST_FOOTER_HIDDEN_PATTERN.match(lines[-1].strip())
        if match:
            gist_url = match.group(1)
            # Remove the footer line
            body_without_footer = '\n'.join(lines[:-1]).rstrip()
            return body_without_footer, gist_url

    return body, None


def add_gist_footer(
    body: str | None,
    gist_url: str,
    visible: bool = False,
) -> str:
    """Add or update gist footer in body."""
    body_without_footer, _ = extract_gist_footer(body)

    if visible:
        # Extract gist ID and revision from URL if available
        # URL format: https://gist.github.com/user/gist_id or https://gist.github.com/gist_id/revision
        gist_match = GIST_URL_WITH_USER_PATTERN.search(gist_url)
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


def upload_image_to_github(
    image_path: str,
    owner: str,
    repo: str,
) -> str | None:
    """Upload an image to GitHub and get the user-attachments URL.

    GitHub stores PR images in a special user-attachments area.
    We use the gh CLI to interact with GitHub's API.
    """
    import base64
    import mimetypes

    if not exists(image_path):
        err(f"Error: Image file not found: {image_path}")
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # Determine MIME type
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type or not mime_type.startswith('image/'):
        err(f"Error: {image_path} doesn't appear to be an image (mime: {mime_type})")
        raise ValueError(f"File is not an image: {mime_type}")

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
        result = proc.text(*cmd, log=None)

        # Extract the uploaded image URL from the rendered HTML
        match = re.search(r'src="(https://github\.com/user-attachments/assets/[^"]+)"', result)
        if match:
            url = match.group(1)
            err(f"Uploaded {image_path} -> {url}")
            return url
        else:
            err(f"Error: Could not extract URL from upload response for {image_path}")
            raise ValueError("Could not extract URL from upload response")
    except Exception as e:
        err(f"Error: Failed to upload {image_path}: {e}")
        raise


def process_images_in_description(body: str, owner: str, repo: str, dry_run: bool = False) -> str:
    """Find local image references and upload them to GitHub."""

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


def get_expected_description_filename(owner: str = None, repo: str = None, pr_number: str | int = None) -> str:
    """Get the expected description filename based on PR info.

    Returns PR-specific name if info available, otherwise DESCRIPTION.md
    """
    if repo and pr_number:
        return f'{repo}#{pr_number}.md'
    return 'DESCRIPTION.md'


def find_description_file(path: Path = None) -> Path | None:
    """Find the description file (either DESCRIPTION.md or {repo}#{pr}.md)."""
    if path is None:
        path = Path.cwd()

    # First check for PR-specific filename
    for file in path.glob('*#*.md'):
        if PR_FILENAME_PATTERN.match(file.name):
            return file

    # Fallback to DESCRIPTION.md
    desc_file = path / 'DESCRIPTION.md'
    if exists(desc_file):
        return desc_file

    return None


def read_description_from_git(ref: str = 'HEAD', path: Path = None) -> tuple[str | None, Path | None]:
    """Read description file from git at specified ref.

    Returns:
        Tuple of (content, filepath) or (None, None) if not found
    """
    desc_file = find_description_file(path)
    if not desc_file:
        return None, None

    try:
        content = proc.text('git', 'show', f'{ref}:{desc_file.name}', err_ok=True)
        if content:
            # Normalize line endings
            content = content.replace('\r\n', '\n')
            return content, desc_file
        return None, None
    except Exception as e:
        err(f"Error: Could not read {desc_file.name} from {ref}: {e}")
        raise


def write_description_with_link_ref(
    file_path: Path,
    owner: str,
    repo: str,
    pr_number: str | int,
    title: str,
    body: str,
    url: str
) -> None:
    """Write a description file with link-reference style header, properly managing the links footer."""
    pr_ref = f'{owner}/{repo}#{pr_number}'
    link_def = f'[{pr_ref}]: {url}'

    # Split body into lines
    lines = body.split('\n') if body else []

    # Find the footer section (trailing lines that are either link defs or blank)
    footer_start = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i].strip()
        if line and not LINK_DEF_PATTERN.match(line):
            # Found a non-link, non-blank line
            footer_start = i + 1
            break

    # Split into main content and footer
    main_content = lines[:footer_start]
    footer_lines = lines[footer_start:]

    # Check if our link def already exists in the footer
    pr_link_pattern = re.compile(r'^\[' + re.escape(pr_ref) + r']:')
    link_exists = any(pr_link_pattern.match(line) for line in footer_lines)

    # Write the file
    with open(file_path, 'w') as f:
        write = partial(print, file=f)

        # Write header with link-reference style
        write(f'# [{pr_ref}] {title}')

        # Write main content
        if main_content and any(line.strip() for line in main_content):
            write()
            write('\n'.join(main_content).rstrip())

        # Write footer with link definitions
        if not link_exists:
            # Add our link as the first in the footer
            write()
            write(link_def)
            if footer_lines and any(line.strip() for line in footer_lines):
                write('\n'.join(footer_lines).rstrip())
        elif footer_lines:
            # Link already exists, just write the existing footer
            write()
            write('\n'.join(footer_lines).rstrip())


def read_description_file(path: Path = None) -> tuple[str | None, str | None]:
    """Read and parse description file."""
    desc_file = find_description_file(path)
    if not desc_file:
        return None, None

    with open(desc_file, 'r') as f:
        content = f.read()
        lines = content.split('\n')

    if not lines:
        return None, None

    # First line should be:
    # - # [owner/repo#123] Title (link-reference style)
    # - # [owner/repo#123](url) Title (inline link style)
    first_line = lines[0].strip()

    # Try link-reference style first (preferred)
    match = PR_LINK_REF_PATTERN.match(first_line)
    if match:
        # This is link-reference style, get the title
        title = match.group(2).strip()
        # Find where the body starts (skip first line and blank lines)
        body_lines = []
        in_body = False
        for line in lines[1:]:
            if in_body or line.strip():
                # Skip link definitions at the end
                if not LINK_DEF_PATTERN.match(line):
                    body_lines.append(line)
                    in_body = True
        # Remove trailing blank lines and link definitions
        while body_lines and not body_lines[-1].strip():
            body_lines.pop()
        body = '\n'.join(body_lines).rstrip()
        return title, body

    # Try inline link style
    match = PR_INLINE_LINK_PATTERN.match(first_line)
    if match:
        title = match.group(4).strip()
        # Rest is the body (skip the first line and any immediately following blank lines)
        body_lines = lines[1:]
        while body_lines and not body_lines[0].strip():
            body_lines = body_lines[1:]
        body = '\n'.join(body_lines).rstrip()
        return title, body

    # Fallback: first line might just be # Title
    match = H1_TITLE_PATTERN.match(first_line)
    if match:
        title = match.group(1).strip()
        body_lines = lines[1:]
        while body_lines and not body_lines[0].strip():
            body_lines = body_lines[1:]
        body = '\n'.join(body_lines).rstrip()
        return title, body

    return None, None


@group()
def cli():
    """Clone and sync GitHub PR descriptions."""
    pass


@cli.command()
@opt('-r', '--repo', help='Repository (owner/repo format)')
@opt('-b', '--base', help='Base branch (default: repo default branch)')
def init(
    repo: str | None,
    base: str | None,
) -> None:
    """Initialize a new PR draft in the current directory."""
    # Check if we're already in a PR directory
    if exists('DESCRIPTION.md'):
        err("Error: DESCRIPTION.md already exists. Are you already managing a PR here?")
        exit(1)

    # Initialize git repo if needed
    if not exists('.git'):
        proc.run('git', 'init', '-q', log=None)
        err("Initialized git repository")

    # Store config if provided
    if repo:
        owner, repo_name = repo.split('/')
        proc.run('git', 'config', 'pr.owner', owner, log=None)
        proc.run('git', 'config', 'pr.repo', repo_name, log=None)
        err(f"Configured for {repo}")

    if base:
        proc.run('git', 'config', 'pr.base', base, log=None)
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
    err("Use 'github-pr.py create' to create the PR when ready")


@cli.command()
@opt('-b', '--base', help='Base branch (default: repo default branch)')
@flag('-d', '--draft', help='Create as draft PR')
@opt('-h', '--head', help='Head branch (default: auto-detect from parent repo)')
@flag('-n', '--dry-run', help='Show what would be done without creating the PR')
@flag('-w', '--web', help='Open PR in web browser after creating')
def create(
    head: str | None,
    base: str | None,
    draft: bool,
    web: bool,
    dry_run: bool,
) -> None:
    """Create a new PR from the current draft."""
    # This is the original open_pr logic for creating new PRs
    create_new_pr(head, base, draft, web, dry_run)


@cli.command()
@flag('-g', '--gist', help='Only show gist URL')
def show(gist: bool) -> None:
    """Show PR and/or gist URLs for current directory."""
    # Get PR info
    owner, repo, pr_number = get_pr_info_from_path()

    if not all([owner, repo, pr_number]):
        # Try from git config
        owner = proc.line('git', 'config', 'pr.owner', err_ok=True, log=None) or ''
        repo = proc.line('git', 'config', 'pr.repo', err_ok=True, log=None) or ''
        pr_number = proc.line('git', 'config', 'pr.number', err_ok=True, log=None) or ''

    if gist:
        # Only show gist URL
        gist_id = proc.line('git', 'config', 'pr.gist', err_ok=True, log=None)
        if not gist_id:
            # Try to find from remote
            gist_remote = find_gist_remote()
            if gist_remote:
                remotes = proc.lines('git', 'remote', '-v', log=None)
                for remote_line in remotes:
                    if remote_line.startswith(f"{gist_remote}\t") and 'gist.github.com' in remote_line:
                        match = GIST_ID_PATTERN.search(remote_line)
                        if match:
                            gist_id = match.group(1)
                            break

        if gist_id:
            print(f"https://gist.github.com/{gist_id}")
        else:
            err("No gist found for this PR")
            exit(1)
    else:
        # Show both PR and gist
        if all([owner, repo, pr_number]):
            pr_url = f"https://github.com/{owner}/{repo}/pull/{pr_number}"
            print(f"PR: {pr_url}")

            # Check for gist
            gist_id = proc.line('git', 'config', 'pr.gist', err_ok=True, log=None)
            if gist_id:
                gist_url = f"https://gist.github.com/{gist_id}"
                print(f"Gist: {gist_url}")

            # Check for gist remote if no gist ID in config
            if not gist_id:
                gist_remote = find_gist_remote()
                if gist_remote:
                    remotes = proc.lines('git', 'remote', '-v', log=None)
                    for remote_line in remotes:
                        if remote_line.startswith(f"{gist_remote}\t"):
                            if 'gist.github.com' in remote_line:
                                match = GIST_ID_PATTERN.search(remote_line)
                                if match:
                                    gist_url = f"https://gist.github.com/{match.group(1)}"
                                    print(f"Gist (from remote): {gist_url}")
                                    break
        else:
            err("No PR information found in current directory")
            exit(1)


@cli.command(name='open')
@flag('-g', '--gist', help='Open gist instead of PR')
def open_pr(
    gist: bool,
) -> None:
    """Open PR or gist in web browser."""
    # Get PR info
    owner, repo, pr_number = get_pr_info_from_path()

    if not all([owner, repo, pr_number]):
        # Try from git config
        owner = proc.line('git', 'config', 'pr.owner', err_ok=True, log=None) or ''
        repo = proc.line('git', 'config', 'pr.repo', err_ok=True, log=None) or ''
        pr_number = proc.line('git', 'config', 'pr.number', err_ok=True, log=None) or ''

    if not all([owner, repo, pr_number]):
        # Check for PR-specific files
        desc_file = find_description_file()
        if desc_file:
            # Parse PR info from the file
            match = PR_FILENAME_PATTERN.match(desc_file.name)
            if match:
                repo = match.group(1)
                pr_number = match.group(2)
                # Try to get owner from git config
                owner = proc.line('git', 'config', 'pr.owner', err_ok=True, log=None) or ''

    if gist:
        # Open gist
        gist_id = proc.line('git', 'config', 'pr.gist', err_ok=True, log=None)
        if not gist_id:
            # Try to find from remote
            gist_remote = find_gist_remote()
            if gist_remote:
                remotes = proc.lines('git', 'remote', '-v', log=None)
                for remote_line in remotes:
                    if remote_line.startswith(f"{gist_remote}\t") and 'gist.github.com' in remote_line:
                        match = GIST_ID_PATTERN.search(remote_line)
                        if match:
                            gist_id = match.group(1)
                            break

        if gist_id:
            gist_url = f"https://gist.github.com/{gist_id}"
            import webbrowser
            webbrowser.open(gist_url)
            err(f"Opened: {gist_url}")
        else:
            err("No gist found for this PR")
            exit(1)
    else:
        # Open PR
        if all([owner, repo, pr_number]):
            pr_url = f"https://github.com/{owner}/{repo}/pull/{pr_number}"
            import webbrowser
            webbrowser.open(pr_url)
            err(f"Opened: {pr_url}")
        else:
            err("Error: No PR found in current directory")
            exit(1)


def create_new_pr(
    head: str | None,
    base: str | None,
    draft: bool,
    web: bool,
    dry_run: bool,
) -> None:
    """Create a new PR from DESCRIPTION.md."""
    # Read DESCRIPTION.md
    if not exists('DESCRIPTION.md'):
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
        title = re.sub(r'^\[?[^/\]]+/[^#\]]+#\d+]?\s*', '', title)
        title = re.sub(r'^[^/]+/[^#]+#\w+\s+', '', title)  # Handle owner/repo#NUMBER format
    else:
        title = first_line

    # Get body (rest of the file)
    body_lines = lines[1:]
    while body_lines and not body_lines[0].strip():
        body_lines = body_lines[1:]
    body = '\n'.join(body_lines).strip()

    # Get repo info from config or parent directory
    owner = proc.line('git', 'config', 'pr.owner', err_ok=True, log=None)
    repo = proc.line('git', 'config', 'pr.repo', err_ok=True, log=None)

    if not owner or not repo:
        # Try to get from parent directory
        parent_dir = Path('..').resolve()
        if exists(join(parent_dir, '.git')):
            try:
                with cd(parent_dir):
                    repo_data = proc.json('gh', 'repo', 'view', '--json', 'owner,name', log=None)
                    owner = repo_data['owner']['login']
                    repo = repo_data['name']
            except Exception as e:
                err(f"Error: Could not determine repository: {e}")
                err("Configure with 'github-pr.py init -r owner/repo'")
                exit(1)
        else:
            err("Error: Could not determine repository. Configure with 'github-pr.py init -r owner/repo'")
            exit(1)

    # Get base branch from config or default
    if not base:
        base = proc.line('git', 'config', 'pr.base', err_ok=True, log=None)
        if not base:
            # Try to get default branch from parent repo
            try:
                parent_dir = Path('..').resolve()
                if exists(join(parent_dir, '.git')):
                    with cd(parent_dir):
                        # Get default branch from GitHub
                        default_branch = proc.line('gh', 'repo', 'view', '--json', 'defaultBranchRef', '-q', '.defaultBranchRef.name', log=None)
                        base = default_branch
                    err(f"Auto-detected base branch: {base}")
                else:
                    base = 'main'  # Fallback to main
            except Exception as e:
                err(f"Error: Could not detect base branch: {e}")
                raise

    # Get head branch - try to auto-detect from parent repo
    if not head:
        parent_dir = Path('..').resolve()
        if exists(join(parent_dir, '.git')):
            try:
                with cd(parent_dir):
                    # Use branch resolution
                    ref_name, remote_ref = resolve_remote_ref(verbose=False)
                    if ref_name:
                        head = ref_name
                        err(f"Auto-detected head branch: {head}")

                    if not head:
                        # Fallback to current branch
                        head = proc.line('git', 'rev-parse', '--abbrev-ref', 'HEAD', log=None)
                        if head == 'HEAD':
                            err("Error: Parent repo is in detached HEAD state. Specify --head explicitly")
                            exit(1)
            except Exception as e:
                err(f"Error detecting head branch: {e}")
                err("Specify --head explicitly")
                exit(1)
        else:
            err("Error: Could not detect head branch. Specify --head explicitly")
            exit(1)

    # Create the PR
    if dry_run:
        err(f"[DRY-RUN] Would create PR in {owner}/{repo}")
        err(f"  Title: {title}")
        err(f"  Base: {base}")
        err(f"  Head: {head}")
        if draft:
            err("  Type: Draft PR")
        if body:
            err(f"  Body ({len(body)} chars):")
            # Show first few lines of body
            body_preview = body[:500] + ('...' if len(body) > 500 else '')
            for line in body_preview.split('\n')[:10]:
                err(f"    {line}")
    else:
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
            output = proc.text(*cmd, log=None).strip()
            if not web:
                # Extract PR number from URL
                match = re.search(r'/pull/(\d+)', output)
                if match:
                    pr_number = match.group(1)
                    # Store PR info in git config
                    proc.run('git', 'config', 'pr.number', pr_number, log=None)
                    proc.run('git', 'config', 'pr.url', output, log=None)
                    err(f"Created PR #{pr_number}: {output}")
                    err("PR info stored in git config")

                    # Check for gist remote and store its ID if found
                    try:
                        remotes = proc.lines('git', 'remote', '-v', log=None)
                        for remote_line in remotes:
                            if 'gist.github.com' in remote_line:
                                # Extract gist ID from URL like git@gist.github.com:GIST_ID.git
                                gist_match = GIST_ID_PATTERN.search(remote_line)
                                if gist_match:
                                    gist_id = gist_match.group(1)
                                    proc.run('git', 'config', 'pr.gist', gist_id, log=None)
                                    err(f"Detected and stored gist ID: {gist_id}")
                                    break
                    except Exception:
                        # Gist detection is optional, silently continue
                        pass

                    # Rename DESCRIPTION.md to PR-specific name and update with PR link
                    old_file = Path('DESCRIPTION.md')
                    new_filename = f'{repo}#{pr_number}.md'
                    new_file = Path(new_filename)

                    if exists(old_file):
                        with open(old_file, 'r') as f:
                            lines = f.readlines()

                        if lines:
                            # Update first line to include PR link
                            first_line = lines[0].strip()
                            # Check if first line is an h1 (starts with #)
                            if first_line.startswith('#'):
                                # Check if it already has a PR link
                                if not PR_LINK_IN_H1_PATTERN.match(first_line):
                                    # Extract just the title (remove leading #)
                                    title_only = first_line.lstrip('#').strip()
                                    # Add PR link
                                    lines[0] = f'# [{owner}/{repo}#{pr_number}]({output}) {title_only}\n'

                                    with open(new_file, 'w') as f:
                                        f.writelines(lines)

                                    # Remove old file if different name
                                    if old_file != new_file:
                                        old_file.unlink()
                                        err(f"Renamed DESCRIPTION.md to {new_filename}")

                                    # Commit the update
                                    proc.run('git', 'add', new_filename, log=None)
                                    if old_file != new_file:
                                        proc.run('git', 'rm', 'DESCRIPTION.md', log=None)
                                    proc.run('git', 'commit', '-m', f'Rename to {new_filename} and add PR #{pr_number} link', log=None)
                                    err(f"Updated {new_filename} with PR link")
                            else:
                                err(f"Warning: {old_file.name} first line is not an h1, skipping link update")
                else:
                    err(f"Created PR: {output}")
        except Exception as e:
            err(f"Error creating PR: {e}")
            exit(1)


@cli.command()
@opt('-d', '--directory', help='Directory to clone into (default: pr{number})')
@flag('-G', '--no-gist', help='Skip creating a gist')
@arg('pr_spec', required=False)
def clone(
    directory: str | None,
    no_gist: bool,
    pr_spec: str | None,
) -> None:
    """Clone a PR description to a local directory.

    PR_SPEC can be:
    - A PR number (when run from within a repo)
    - owner/repo#number format
    - A full PR URL
    """

    # Parse PR spec
    if pr_spec:
        # Try to parse different formats
        owner, repo, pr_number = parse_pr_spec(pr_spec)

        # If just a number, need to get owner/repo from current directory
        if pr_number and not owner:
            # Get owner/repo from current directory
            try:
                repo_data = proc.json('gh', 'repo', 'view', '--json', 'owner,name', log=None)
                owner = repo_data['owner']['login']
                repo = repo_data['name']
            except Exception as e:
                err(f"Error: Could not determine repository: {e}")
                err("Use owner/repo#number format.")
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
    if exists(target_path):
        err(f"Error: Directory {directory} already exists")
        exit(1)

    # Get PR metadata
    err(f"Fetching PR {owner}/{repo}#{pr_number}...")
    pr_data = get_pr_metadata(owner, repo, pr_number)
    if not pr_data:
        exit(1)

    # Create directory and initialize git repo
    target_path.mkdir(parents=True)
    chdir(target_path)

    proc.run('git', 'init', '-q', log=None)

    # Create PR-specific filename
    new_filename = get_expected_description_filename(owner, repo, pr_number)
    desc_file = Path(new_filename)
    title = pr_data['title']
    body = pr_data['body'] or ''
    url = pr_data['url']

    # Strip any gist footer from the body before saving locally
    body_without_footer, existing_gist_url = extract_gist_footer(body)

    # Write using helper to avoid duplicate link definitions
    write_description_with_link_ref(desc_file, owner, repo, pr_number, title, body_without_footer, url)

    # Store metadata in git config
    proc.run('git', 'config', 'pr.owner', owner, log=None)
    proc.run('git', 'config', 'pr.repo', repo, log=None)
    proc.run('git', 'config', 'pr.number', str(pr_number), log=None)
    proc.run('git', 'config', 'pr.url', pr_data['url'], log=None)

    # Initial commit
    proc.run('git', 'add', new_filename, log=None)
    proc.run('git', 'commit', '-m', f'Initial clone of {owner}/{repo}#{pr_number}', log=None)

    # Create or use existing gist unless --no-gist was specified
    if not no_gist:
        gist_id = None
        gist_url = None  # Initialize to avoid potential undefined variable

        # Check if PR already has a gist in its footer
        if existing_gist_url:
            # Extract gist ID from the URL
            match = GIST_ID_PATTERN.search(existing_gist_url)
            if match:
                gist_id = match.group(1)
                gist_url = existing_gist_url
                err(f"Found existing gist in PR description: {gist_url}")

                # Store gist ID
                proc.run('git', 'config', 'pr.gist', gist_id, log=None)

                # Add gist as remote
                proc.run('git', 'remote', 'add', DEFAULT_GIST_REMOTE, f'git@gist.github.com:{gist_id}.git', log=None)
                proc.run('git', 'config', 'pr.gist-remote', DEFAULT_GIST_REMOTE, log=None)

                # Fetch and push our version
                proc.run('git', 'fetch', DEFAULT_GIST_REMOTE, log=None)
                proc.run('git', 'push', '--set-upstream', DEFAULT_GIST_REMOTE, 'main', '--force', log=None)
                err("Pushed to existing gist")

                # Note: PR already has the gist footer since we found it there

        # Create new gist if none exists
        if not gist_id:
            err("Creating gist for PR sync...")

            # Get repository visibility to determine gist visibility
            try:
                is_private = proc.json('gh', 'api', f'repos/{owner}/{repo}', '--jq', '.private', log=None)
                gist_private = is_private if isinstance(is_private, bool) else True
            except Exception as e:
                err(f"Error: Could not determine repo visibility: {e}")
                raise

            # Create the gist
            description = f'{owner}/{repo}#{pr_number} - 2-way sync via github-pr.py (ryan-williams/git-helpers)'
            gist_id = create_gist(desc_file, description, is_public=not gist_private)

            # Add gist as remote
            proc.run('git', 'remote', 'add', DEFAULT_GIST_REMOTE, f'git@gist.github.com:{gist_id}.git', log=None)
            proc.run('git', 'config', 'pr.gist-remote', DEFAULT_GIST_REMOTE, log=None)

            # Fetch and push
            proc.run('git', 'fetch', DEFAULT_GIST_REMOTE, log=None)
            proc.run('git', 'push', '--set-upstream', DEFAULT_GIST_REMOTE, 'main', '--force', log=None)
            err("Pushed to gist")

            # Construct gist URL
            gist_url = f"https://gist.github.com/{gist_id}"

            # Open the gist in browser (first time creation)
            webbrowser.open(gist_url)
            err("Opened gist in browser")

            # Add gist footer to PR (default behavior)
            err("Adding gist footer to PR...")
            body_with_footer = add_gist_footer(body, gist_url, visible=False)

            # Update PR with footer
            with NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write(body_with_footer)
                temp_file = f.name

            try:
                proc.run('gh', 'pr', 'edit', str(pr_number), '-R', f'{owner}/{repo}',
                        '--body-file', temp_file, log=None)
                err("Added gist footer to PR")
            finally:
                unlink(temp_file)

    err(f"Successfully cloned PR to {target_path}")
    err(f"URL: {pr_data['url']}")

    # Check if we should ingest user-attachments
    from os import environ
    should_ingest = environ.get('GHPR_INGEST_ATTACHMENTS', '1') != '0'

    if should_ingest and gist_url:
        # Check for user-attachments in the cloned description
        desc_file = target_path / new_filename
        if desc_file.exists():
            with open(desc_file, 'r') as f:
                content = f.read()

            # Check for user-attachments in reference-style links
            ref_link_pattern = re.compile(r'^\[([^\]]+)\]:\s+(https://github\.com/user-attachments/assets/[a-f0-9-]+)\s*$', re.MULTILINE)
            if ref_link_pattern.search(content):
                err("Found user-attachments, ingesting...")
                # Change to the clone directory and run ingest
                with cd(target_path):
                    # Call the ingest function directly
                    from click import Context
                    ctx = Context(ingest_attachments)
                    # Use None for branch to let it fall back to env var or default
                    ctx.invoke(ingest_attachments, branch=None, no_ingest=False, dry_run=False)


@cli.command()
@flag('-g', '--gist', help='Also sync to gist')
@flag('-n', '--dry-run', help='Show what would be done without making changes')
@opt('-f', '--footer', count=True, help='Footer level: -f = hidden footer, -ff = visible footer')
@flag('-F', '--no-footer', help='Disable footer completely')
@flag('-o', '--open', 'open_browser', help='Open PR in browser after pushing')
@flag('-i', '--images', help='Upload local images and replace references')
@opt('-p/-P', '--private/--public', 'gist_private', default=None, help='Gist visibility: -p = private, -P = public (default: match repo visibility)')
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
            owner = proc.line('git', 'config', 'pr.owner', err_ok=True, log=None) or ''
            repo = proc.line('git', 'config', 'pr.repo', err_ok=True, log=None) or ''
            pr_number = proc.line('git', 'config', 'pr.number', err_ok=True, log=None) or ''
        except Exception as e:
            err(f"Error: Could not determine PR from directory or git config: {e}")
            exit(1)

    # Read the current description file (from HEAD, not working directory)
    desc_content, desc_file = read_description_from_git('HEAD')
    if not desc_content:
        expected_filename = get_expected_description_filename(owner, repo, pr_number)
        err(f"Error: Could not read {expected_filename} or DESCRIPTION.md from HEAD")
        err("Make sure you've committed your changes")
        exit(1)

    lines = desc_content.split('\n')
    if not lines:
        err("Error: Description file is empty")
        exit(1)

    # Parse the file
    first_line = lines[0].strip()
    # Remove the [owner/repo#num] or [owner/repo#num](url) prefix to get the title
    title = extract_title_from_first_line(first_line)

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
    try:
        gist_id = proc.line('git', 'config', 'pr.gist', err_ok=True, log=None)
        has_gist = bool(gist_id)
    except Exception:
        # Reading git config is optional, silently set to False
        has_gist = False
        gist_id = None

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
        if dry_run:
            err(f"[DRY-RUN] Would add {'visible' if footer_visible else 'hidden'} footer with gist URL: {gist_url}")
        else:
            err(f"Added {'visible' if footer_visible else 'hidden'} footer with gist URL: {gist_url}")
    elif should_add_footer and not gist_url:
        err("Error: Should add footer but no gist URL available")
        raise ValueError("Footer requires gist URL but none available")

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
            with NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write(body)
                body_file = f.name

            cmd.extend(['--body-file', body_file])

        try:
            proc.run(*cmd, log=None)
            if body is not None:
                unlink(body_file)  # Clean up temp file
            err("Successfully updated PR")

            # Get PR URL if we need to open it
            if open_browser:
                pr_url = proc.line('git', 'config', 'pr.url', err_ok=True, log=None)
                if not pr_url:
                    pr_url = f"https://github.com/{owner}/{repo}/pull/{pr_number}"

                import webbrowser
                webbrowser.open(pr_url)
                err(f"Opened: {pr_url}")
        except Exception as e:
            err(f"Error updating PR: {e}")
            exit(1)


def sync_to_gist(
    owner: str,
    repo: str,
    pr_number: str,
    content: str,
    return_url: bool = False,
    add_remote: bool = True,
    gist_private: bool = None,
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
    gist_id = proc.line('git', 'config', 'pr.gist', err_ok=True, log=None)

    # Find the gist remote intelligently
    gist_remote = find_gist_remote()
    if not gist_remote:
        # Only set a default if we're actually going to use it
        if gist_id or add_remote:
            gist_remote = DEFAULT_GIST_REMOTE
            err(f"No gist remote found, will use '{gist_remote}'")

    # Determine gist visibility
    if gist_private is not None:
        # Explicit visibility specified
        is_public = not gist_private  # Invert: if private flag is True, public is False
        err(f"Using explicit gist visibility: {'PUBLIC' if is_public else 'PRIVATE'}")
    else:
        # Check repository visibility to determine gist visibility
        try:
            repo_data = proc.json('gh', 'repo', 'view', f'{owner}/{repo}', '--json', 'visibility', err_ok=True, log=None) or {}
            is_public = repo_data.get('visibility', 'PUBLIC').upper() == 'PUBLIC'
            err(f"Repository visibility: {'PUBLIC' if is_public else 'PRIVATE'}, gist will match")
        except Exception as e:
            err(f"Error: Could not determine repository visibility: {e}")
            raise

    # Use PR-specific filename for better gist organization
    pr_filename = f'{repo}#{pr_number}.md'
    local_filename = pr_filename  # Use same filename locally
    description = f'{owner}/{repo}#{pr_number} - 2-way sync via github-pr.py (ryan-williams/git-helpers)'
    gist_url = None

    if gist_id:
        # Update existing gist
        err(f"Updating gist {gist_id}...")

        # Check if we need to rename the file in the gist
        try:
            gist_files = proc.json('gh', 'api', f'gists/{gist_id}', '--jq', '.files', log=None) or {}
            old_filename = None

            # Find the existing markdown file (could be DESCRIPTION.md or a PR-specific name)
            for fname in gist_files.keys():
                if fname.endswith('.md'):
                    old_filename = fname
                    break

            # Update gist with new filename if needed
            if old_filename and old_filename != pr_filename:
                # Rename file by deleting old and adding new
                proc.run('gh', 'api', f'gists/{gist_id}', '-X', 'PATCH',
                           '-f', f'description={description}',
                           '-f', f'files[{old_filename}][filename]={pr_filename}', log=None)
                err(f"Renamed gist file from {old_filename} to {pr_filename}")
            else:
                # Just update description
                proc.run('gh', 'api', f'gists/{gist_id}', '-X', 'PATCH',
                           '-f', f'description={description}', log=None)
        except Exception as e:
            err(f"Error: Could not update gist metadata: {e}")
            raise

        # Check if remote exists and push to it
        if add_remote:
            try:
                # Commit any changes and push to gist
                proc.run('git', 'add', local_filename, log=None)
                proc.run('git', 'commit', '-m', f'Update PR description for {owner}/{repo}#{pr_number}', log=None)
            except Exception:
                # May already be committed - check if there are changes
                if proc.line('git', 'diff', '--cached', '--name-only', local_filename, err_ok=True, log=None):
                    raise  # Re-raise if there were actual changes that failed to commit

            try:
                proc.run('git', 'push', gist_remote, 'main', '--force', log=None)
                err(f"Pushed to gist remote '{gist_remote}'")
            except Exception as e:
                err(f"Error: Could not push to gist remote '{gist_remote}': {e}")
                raise

        # Get the latest revision SHA
        try:
            gist_info = proc.line('gh', 'api', f'gists/{gist_id}', '--jq', '.history[0].version', log=None)
            revision = gist_info
        except Exception as e:
            err(f"Error: Could not get gist revision: {e}")
            raise

        if revision:
            gist_url = f"https://gist.github.com/{gist_id}/{revision}"
        else:
            gist_url = f"https://gist.github.com/{gist_id}"
        err(f"Updated gist: {gist_url}")
    else:
        # Create new gist
        err(f"Creating new {'public' if is_public else 'secret'} gist...")

        # Create a temporary file with the PR-specific name for gist creation
        with TemporaryDirectory() as tmpdir:
            # Create temp file with PR-specific name
            temp_file = Path(tmpdir) / pr_filename
            with open(temp_file, 'w') as f:
                f.write(content)

            # Also update local DESCRIPTION.md
            desc_file = Path(local_filename)
            with open(desc_file, 'w') as f:
                f.write(content)

            try:
                # Create gist from PR-specific filename (visibility based on repo)
                output = None
                gist_id_from_creation = create_gist(temp_file, description, is_public=is_public, store_id=False)
                if gist_id_from_creation:
                    output = f"https://gist.github.com/{gist_id_from_creation}"
                if not output:
                    err("Error creating gist")
                    return None
                output = output.strip()
                err(f"Gist create output: {output}")
                # Extract gist ID from URL (format: https://gist.github.com/username/gist_id or https://gist.github.com/gist_id)
                match = GIST_URL_WITH_USER_PATTERN.search(output)
                if match:
                    gist_id = match.group(1)
                    proc.run('git', 'config', 'pr.gist', gist_id, log=None)
                    err(f"Stored gist ID: {gist_id}")

                    # Add gist as a remote if requested
                    if add_remote:
                        gist_ssh_url = f"git@gist.github.com:{gist_id}.git"
                        try:
                            # Check if remote already exists
                            existing_url = proc.line('git', 'remote', 'get-url', gist_remote, err_ok=True, log=None)
                            if existing_url != gist_ssh_url:
                                # Update existing remote
                                proc.run('git', 'remote', 'set-url', gist_remote, gist_ssh_url, log=None)
                                err(f"Updated remote '{gist_remote}' to {gist_ssh_url}")
                        except Exception:
                            # Add new remote
                            proc.run('git', 'remote', 'add', gist_remote, gist_ssh_url, log=None)
                            err(f"Added remote '{gist_remote}': {gist_ssh_url}")

                    # Fetch from the gist remote first
                    try:
                        proc.run('git', 'fetch', gist_remote, log=None)
                    except Exception as e:
                        # Fetch might fail if gist is empty, which is OK for new gists
                        err(f"Note: Could not fetch from gist (may be empty): {e}")

                    # Set up branch tracking
                    try:
                        current_branch = proc.line('git', 'rev-parse', '--abbrev-ref', 'HEAD', log=None)
                        proc.run('git', 'branch', '--set-upstream-to', f'{gist_remote}/main', current_branch, log=None)
                        err(f"Set {current_branch} to track {gist_remote}/main")
                    except Exception as e:
                        err(f"Could not set up branch tracking: {e}")

                    # Commit and push to the gist
                    try:
                        # Check if there are uncommitted changes
                        proc.check('git', 'diff', '--quiet', 'DESCRIPTION.md', log=None)
                    except Exception:
                        # There are changes, commit them
                        proc.run('git', 'add', 'DESCRIPTION.md', log=None)
                        proc.run('git', 'commit', '-m', f'Sync PR {owner}/{repo}#{pr_number} to gist', log=None)

                        # Push to the gist remote
                        try:
                            proc.run('git', 'push', gist_remote, 'main', '--force', log=None)
                            err(f"Pushed to gist remote '{gist_remote}'")
                        except Exception as e:
                            err(f"Error: Could not push to gist remote '{gist_remote}': {e}")
                            raise

                    # Get the revision SHA for the newly created gist
                    try:
                        gist_info = proc.line('gh', 'api', f'gists/{gist_id}', '--jq', '.history[0].version', log=None)
                        revision = gist_info
                        gist_url = f"https://gist.github.com/{gist_id}/{revision}"
                    except Exception as e:
                        err(f"Error: Could not get gist revision: {e}")
                        raise

                    err(f"Created gist: {gist_url}")
            except Exception as e:
                err(f"Error creating gist: {e}")
                return None

    if return_url:
        return gist_url


@cli.command()
@arg('files', nargs=-1, required=True)
@opt('-b', '--branch', default='assets', help='Branch name in gist (default: assets)')
@opt('-f', '--format', type=Choice(['url', 'markdown', 'img', 'auto']), default='auto', help='Output format (default: auto - img for images, url for others)')
@opt('-a', '--alt', help='Alt text for markdown/img format')
def upload(
    files: tuple[str, ...],
    branch: str,
    format: str,
    alt: str | None,
) -> None:
    """Upload images to the PR's gist and get URLs."""
    import gist_upload

    # Get PR info
    owner, repo, pr_number = get_pr_info_from_path()

    if not all([owner, repo, pr_number]):
        try:
            owner = proc.line('git', 'config', 'pr.owner', err_ok=True, log=None) or ''
            repo = proc.line('git', 'config', 'pr.repo', err_ok=True, log=None) or ''
            pr_number = proc.line('git', 'config', 'pr.number', err_ok=True, log=None) or ''
        except Exception as e:
            err(f"Error: Could not determine PR from directory or git config: {e}")
            exit(1)

    # Get or create gist
    # Read gist ID from git config (optional)
    gist_id = proc.line('git', 'config', 'pr.gist', err_ok=True, log=None)

    if not gist_id:
        # Create a gist for this PR
        err("Creating gist for PR assets...")
        description = f'{owner}/{repo}#{pr_number} assets'
        desc_content = "# PR Assets\nImage assets for PR"

        gist_id = gist_upload.create_gist(description, desc_content)
        if gist_id:
            proc.run('git', 'config', 'pr.gist', gist_id, log=None)
            err(f"Created gist: {gist_id}")
        else:
            err("Error: Could not create gist")
            exit(1)

    # Check if we're already in a gist clone
    is_local_clone = False
    remote_name = None
    try:
        # Check all remotes to see if any point to this gist
        remotes = proc.lines('git', 'remote', log=None)
        for remote in remotes:
            if not remote:
                continue
            try:
                remote_url = proc.line('git', 'remote', 'get-url', remote, err_ok=True, log=None)
                if f'gist.github.com:{gist_id}' in remote_url or f'gist.github.com/{gist_id}' in remote_url:
                    is_local_clone = True
                    remote_name = remote
                    err(f"Already in gist repository with remote '{remote}'")
                    break
            except Exception:
                # Remote URL doesn't match gist pattern, continue checking others
                continue
    except Exception:
        # Not in a gist repo, which is expected for PR directories
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
@opt('-c', '--color', type=Choice(['auto', 'always', 'never']), default='auto', help='When to use colored output (default: auto)')
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
            owner = proc.line('git', 'config', 'pr.owner', err_ok=True, log=None) or ''
            repo = proc.line('git', 'config', 'pr.repo', err_ok=True, log=None) or ''
            pr_number = proc.line('git', 'config', 'pr.number', err_ok=True, log=None) or ''
        except Exception as e:
            err(f"Error: Could not determine PR from directory or git config: {e}")
            exit(1)

    # Get remote PR data
    err(f"Fetching PR {owner}/{repo}#{pr_number}...")
    pr_data = get_pr_metadata(owner, repo, pr_number)
    if not pr_data:
        exit(1)

    # Read local description from git
    desc_content, desc_file = read_description_from_git('HEAD')
    if not desc_content or not desc_file:
        err("Error: Could not read description file from HEAD")
        err("Make sure you've committed your changes")
        exit(1)

    # Parse local file to get title and body
    lines = desc_content.split('\n')
    if not lines:
        err("Error: DESCRIPTION.md is empty")
        exit(1)

    first_line = lines[0].strip()
    local_title = extract_title_from_first_line(first_line)

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
            tofile=f'Local {desc_file.name}',
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
@flag('-g', '--gist', help='Also sync to gist')
@flag('-n', '--dry-run', help='Show what would be done')
@opt('-f/-F', '--footer/--no-footer', default=None, help='Add gist footer to PR (default: auto - add if gist exists)')
@flag('-o', '--open', 'open_browser', help='Open PR in browser after pulling')
@opt('-p/-P', '--private/--public', 'gist_private', default=None, help='Gist visibility: -p = private, -P = public (default: match repo visibility)')
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
        owner = proc.line('git', 'config', 'pr.owner', err_ok=True, log=None) or ''
        repo = proc.line('git', 'config', 'pr.repo', err_ok=True, log=None) or ''
        pr_number = proc.line('git', 'config', 'pr.number', err_ok=True, log=None) or ''

        if not all([owner, repo, pr_number]):
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

    # Write using helper to avoid duplicate link definitions
    write_description_with_link_ref(desc_file, owner, repo, pr_number, title, body_without_footer, url)

    # Check if there are changes
    if proc.check('git', 'diff', '--exit-code', 'DESCRIPTION.md', log=None):
        err("No changes from PR")
    else:
        # There are changes, commit them
        if not dry_run:
            proc.run('git', 'add', 'DESCRIPTION.md', log=None)
            proc.run('git', 'commit', '-m', 'Sync from PR (pulled latest)', log=None)
            err("Pulled and committed changes from PR")
        else:
            err("[DRY-RUN] Would pull and commit changes from PR")

    # Now push our version back
    err("Pushing to PR...")
    # Convert pull's footer boolean to push's footer count
    footer_count = 1 if footer else 0 if footer is False else 0
    push.callback(gist, dry_run, footer_count, no_footer=False, open_browser=open_browser, images=False, gist_private=gist_private)


@cli.command()
@arg('directory', required=False, type=Path)
@flag('-n', '--dry-run', help='Show what would be done without making changes')
def sync(
    directory: Path | None,
    dry_run: bool,
) -> None:
    """Update existing PR clones to use new naming conventions.

    This command:
    - Renames DESCRIPTION.md to {repo}#{pr}.md
    - Updates the gist filename if a gist exists
    - Updates the gist description
    - Commits and pushes changes to the gist

    Args:
        directory: Optional path to PR directory (default: current directory)
    """

    # Use provided directory or current directory
    target_dir = directory if directory else Path.cwd()

    if not exists(target_dir):
        err(f"Error: Directory {target_dir} does not exist")
        exit(1)

    if not exists(target_dir / '.git'):
        err(f"Error: {target_dir} is not a git repository")
        exit(1)

    with cd(target_dir):
        # Try to get PR info from multiple sources
        owner = proc.line('git', 'config', 'pr.owner', err_ok=True, log=None)
        repo = proc.line('git', 'config', 'pr.repo', err_ok=True, log=None)
        pr_number = proc.line('git', 'config', 'pr.number', err_ok=True, log=None)

        # If missing info, try to parse from existing files
        if not all([owner, repo, pr_number]):
            # Look for markdown files
            desc_file = find_description_file()

            if desc_file:
                # Try to parse from filename first (e.g., ec2-gha#3.md)
                match = PR_FILENAME_PATTERN.match(desc_file.name)
                if match:
                    if not repo:
                        repo = match.group(1)
                    if not pr_number:
                        pr_number = match.group(2)

                # Parse owner from file content (first line)
                with open(desc_file, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')
                    first_line = lines[0].strip() if lines else ''

                    # Match pattern like # [Open-Athena/ec2-gha#3] or # [org/repo#num]
                    match = PR_INLINE_LINK_PATTERN.match(first_line)
                    if match:
                        # Inline link style: groups are (owner, repo, pr_number, title)
                        if not owner:
                            owner = match.group(1)
                        if not repo:
                            repo = match.group(2)
                        if not pr_number:
                            pr_number = match.group(3)
                    else:
                        # Check for link reference style (just [org/repo#num] without URL)
                        link_match = PR_LINK_REF_PATTERN.match(first_line)
                        if link_match:
                            link_ref = link_match.group(1)  # e.g., "org/repo#123"
                            # Parse the reference directly
                            ref_parts = PR_SPEC_PATTERN.match(link_ref)
                            if ref_parts:
                                if not owner:
                                    owner = ref_parts.group(1)
                                if not repo:
                                    repo = ref_parts.group(2)
                                if not pr_number:
                                    pr_number = ref_parts.group(3)

            # If still missing, try parent directory name (e.g., pr3)
            if not pr_number and target_dir.name.startswith('pr'):
                match = PR_DIR_PATTERN.match(target_dir.name)
                if match:
                    pr_number = match.group(1)

        # Store any newly discovered info in git config (unless dry-run)
        if owner and not proc.line('git', 'config', 'pr.owner', err_ok=True, log=None):
            if dry_run:
                err(f"[DRY-RUN] Would store pr.owner = {owner}")
            else:
                proc.run('git', 'config', 'pr.owner', owner, log=None)
                err(f"Stored pr.owner = {owner}")

        if repo and not proc.line('git', 'config', 'pr.repo', err_ok=True, log=None):
            if dry_run:
                err(f"[DRY-RUN] Would store pr.repo = {repo}")
            else:
                proc.run('git', 'config', 'pr.repo', repo, log=None)
                err(f"Stored pr.repo = {repo}")

        if pr_number and not proc.line('git', 'config', 'pr.number', err_ok=True, log=None):
            if dry_run:
                err(f"[DRY-RUN] Would store pr.number = {pr_number}")
            else:
                proc.run('git', 'config', 'pr.number', pr_number, log=None)
                err(f"Stored pr.number = {pr_number}")

        if not all([owner, repo, pr_number]):
            err("Error: Could not determine PR information")
            err(f"  Owner: {owner or 'MISSING'}")
            err(f"  Repo: {repo or 'MISSING'}")
            err(f"  PR: {pr_number or 'MISSING'}")
            err("Please check the markdown file or directory structure")
            exit(1)

        err(f"Syncing {owner}/{repo}#{pr_number}...")

        # Check for existing files
        old_file = Path('DESCRIPTION.md')
        new_filename = get_expected_description_filename(owner, repo, pr_number)
        new_file = Path(new_filename)

        # If already using new name, check if content needs updating
        if exists(new_file) and not exists(old_file):
            # Check if h1 has PR link
            with open(new_file, 'r') as f:
                first_line = f.readline().strip()

            # Check if first line already has the PR link
            if not PR_LINK_IN_H1_PATTERN.match(first_line):
                if dry_run:
                    err(f"[DRY-RUN] Would update h1 in {new_filename} with PR link")
                else:
                    # Read content and parse
                    title, body = read_description_file(Path.cwd())

                    # Get PR URL
                    pr_url = proc.line('git', 'config', 'pr.url', err_ok=True, log=None)
                    if not pr_url:
                        pr_url = f"https://github.com/{owner}/{repo}/pull/{pr_number}"

                    # Write with updated format
                    write_description_with_link_ref(new_file, owner, repo, pr_number, title, body, pr_url)

                    # Commit the update
                    proc.run('git', 'add', new_filename, log=None)
                    proc.run('git', 'commit', '-m', f'Update {new_filename} with PR link', log=None)
                    err(f"Updated {new_filename} with PR link")
            else:
                err(f"Already using {new_filename} with PR link")
            # Still check if gist needs updating
        elif exists(old_file):
            if dry_run:
                err(f"[DRY-RUN] Would rename {old_file} to {new_file}")
                err("[DRY-RUN] Would update h1 with PR link")
            else:
                # Read content and parse
                title, body = read_description_file(Path.cwd())

                # Get PR URL if available
                pr_url = proc.line('git', 'config', 'pr.url', err_ok=True, log=None)
                if not pr_url:
                    pr_url = f"https://github.com/{owner}/{repo}/pull/{pr_number}"

                # Write with updated format
                write_description_with_link_ref(new_file, owner, repo, pr_number, title, body, pr_url)

                # Remove old file
                old_file.unlink()

                # Commit the rename and update
                proc.run('git', 'add', new_filename, log=None)
                proc.run('git', 'rm', 'DESCRIPTION.md', log=None)
                proc.run('git', 'commit', '-m', f'Rename to {new_filename} and update with PR link', log=None)
                err(f"Renamed {old_file} to {new_file} and updated with PR link")
        else:
            err(f"No description file found in {target_dir}")
            exit(1)

        # Check if we have a gist - try config first, then g remote
        gist_id = proc.line('git', 'config', 'pr.gist', err_ok=True, log=None)

        # If no gist in config, check for g remote
        if not gist_id:
            remotes = proc.lines('git', 'remote', '-v', log=None) or []
            for remote_line in remotes:
                if remote_line.startswith('g\t') and 'gist.github.com' in remote_line:
                    # Extract gist ID from URL like git@gist.github.com:GIST_ID.git
                    match = GIST_ID_PATTERN.search(remote_line)
                    if match:
                        gist_id = match.group(1)
                        if dry_run:
                            err(f"[DRY-RUN] Would store gist ID from 'g' remote: {gist_id}")
                        else:
                            proc.run('git', 'config', 'pr.gist', gist_id, log=None)
                            err(f"Found and stored gist ID from 'g' remote: {gist_id}")
                        break

        # Create gist if needed
        if not gist_id:
            if dry_run:
                err("[DRY-RUN] Would create new gist for PR")
                err(f"[DRY-RUN] Would add gist as remote '{DEFAULT_GIST_REMOTE}'")
                err("[DRY-RUN] Would push to new gist")
            else:
                # Get repository visibility to determine gist visibility
                try:
                    is_private = proc.json('gh', 'api', f'repos/{owner}/{repo}', '--jq', '.private', log=None)
                    gist_private = is_private if isinstance(is_private, bool) else True
                except Exception as e:
                    err(f"Error: Could not determine repo visibility: {e}")
                    raise

                # Create the gist
                err("Creating gist for PR...")
                description = f'{owner}/{repo}#{pr_number} - 2-way sync via github-pr.py (ryan-williams/git-helpers)'

                # Find current file
                desc_file = find_description_file()
                if not desc_file:
                    err("Error: No description file found")
                    exit(1)

                gist_id = create_gist(desc_file, description, is_public=not gist_private)

                # Add gist as remote
                proc.run('git', 'remote', 'add', 'g', f'git@gist.github.com:{gist_id}.git', log=None)
                proc.run('git', 'config', 'pr.gist-remote', 'g', log=None)
                err(f"Added gist as remote '{DEFAULT_GIST_REMOTE}'")

                # Fetch and push
                proc.run('git', 'fetch', 'g', log=None)
                proc.run('git', 'push', '--set-upstream', 'g', 'main', '--force', log=None)
                err("Pushed to gist")

        if gist_id:
            # Push to gist remote if it exists
            gist_remote = find_gist_remote() or DEFAULT_GIST_REMOTE
            remotes = proc.lines('git', 'remote', log=None)

            if gist_remote in remotes:
                # Check if there are actually changes to push
                try:
                    # Check for unpushed commits
                    unpushed = proc.line('git', 'rev-list', f'{gist_remote}/main..HEAD', '--count', err_ok=True, log=None)
                    has_changes = unpushed and int(unpushed) > 0
                except Exception as e:
                    err(f"Error: Could not check for unpushed commits: {e}")
                    raise

                if has_changes:
                    if dry_run:
                        err(f"[DRY-RUN] Would push changes to gist remote '{gist_remote}'")
                    else:
                        err(f"Pushing to gist {gist_id}...")
                        try:
                            proc.run('git', 'push', gist_remote, 'main', '--force', log=None)
                            err(f"Pushed changes to gist remote '{gist_remote}'")

                            # Update gist description via API (this is metadata only, not file content)
                            description = f'{owner}/{repo}#{pr_number} - 2-way sync via github-pr.py (ryan-williams/git-helpers)'
                            try:
                                proc.run('gh', 'api', f'gists/{gist_id}', '-X', 'PATCH',
                                           '-f', f'description={description}', log=None)
                                err("Updated gist description")
                            except Exception as e:
                                err(f"Error: Could not update gist description: {e}")
                                raise
                        except Exception as e:
                            err(f"Error: Could not push to gist: {e}")
                            raise
                else:
                    err("No changes to push to gist")
            else:
                err(f"Error: Gist remote '{gist_remote}' not found")
                raise ValueError(f"Gist remote '{gist_remote}' not found")

        # Check if PR needs gist footer
        if gist_id:
            gist_url = f'https://gist.github.com/{gist_id}'

            # Get current PR body to check for footer
            pr_data = get_pr_metadata(owner, repo, pr_number)
            if pr_data:
                current_body = pr_data['body'] or ''
                _, existing_gist_url = extract_gist_footer(current_body)

                if not existing_gist_url:
                    # PR is missing gist footer
                    if dry_run:
                        err(f"[DRY-RUN] Would add gist footer to PR {owner}/{repo}#{pr_number}")
                    else:
                        err("Adding gist footer to PR...")
                        body_with_footer = add_gist_footer(current_body, gist_url, visible=False)

                        # Update PR with footer
                        with NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                            f.write(body_with_footer)
                            temp_file = f.name

                        try:
                            proc.run('gh', 'pr', 'edit', str(pr_number), '-R', f'{owner}/{repo}',
                                    '--body-file', temp_file, log=None)
                            err("Added gist footer to PR")
                        finally:
                            unlink(temp_file)
                else:
                    err("PR already has gist footer")


@cli.command(name='ingest-attachments')
@opt('-b', '--branch', help='Branch name for attachments (default: $GHPR_INGEST_BRANCH or "attachments")')
@flag('--no-ingest', help='Disable attachment ingestion')
@flag('-n', '--dry-run', help='Show what would be done without making changes')
def ingest_attachments(
    branch: str | None,
    no_ingest: bool,
    dry_run: bool,
) -> None:
    """Download GitHub user-attachments and convert to gist permalinks.

    This command:
    1. Finds reference-style links with user-attachments URLs in DESCRIPTION.md
    2. Downloads the attachments via gh api
    3. Commits them to a dedicated branch on the gist
    4. Replaces URLs with gist permalinks in the main branch
    """
    from os import environ
    import subprocess

    # Use provided branch, or fall back to env var, or default
    if not branch:
        branch = environ.get('GHPR_INGEST_BRANCH', 'attachments')

    # Check environment variable for default behavior
    should_ingest = not no_ingest
    if not no_ingest and environ.get('GHPR_INGEST_ATTACHMENTS') == '0':
        should_ingest = False

    if not should_ingest:
        err("Attachment ingestion disabled")
        return

    # Get PR info from current directory
    owner = proc.line('git', 'config', 'pr.owner', err_ok=True, log=None)
    repo = proc.line('git', 'config', 'pr.repo', err_ok=True, log=None)
    pr_number = proc.line('git', 'config', 'pr.number', err_ok=True, log=None)
    gist_id = proc.line('git', 'config', 'pr.gist', err_ok=True, log=None)

    if not all([owner, repo, pr_number]):
        err("Error: Not in a PR clone directory (missing pr.* git config)")
        exit(1)

    if not gist_id:
        err("Error: No gist associated with this PR clone")
        exit(1)

    # Find description file
    desc_file = find_description_file()
    if not desc_file:
        err("Error: No description file found")
        exit(1)

    # Read description content
    with open(desc_file, 'r') as f:
        content = f.read()

    # Pattern for reference-style links: [name]: url
    ref_link_pattern = re.compile(r'^\[([^\]]+)\]:\s+(https://github\.com/user-attachments/assets/[a-f0-9-]+)\s*$', re.MULTILINE)

    matches = ref_link_pattern.findall(content)
    if not matches:
        err("No user-attachments found in reference-style links")
        return

    err(f"Found {len(matches)} user-attachment(s) to process")

    # Store current branch
    current_branch = proc.line('git', 'rev-parse', '--abbrev-ref', 'HEAD', log=None)

    # Check if attachments branch exists
    branches = proc.lines('git', 'branch', '-a', log=None) or []
    branch_exists = any(b.strip().endswith(branch) for b in branches)

    if not branch_exists:
        if dry_run:
            err(f"[DRY-RUN] Would create branch '{branch}'")
        else:
            # Create orphan branch for attachments
            proc.run('git', 'checkout', '--orphan', branch, log=None)
            # Remove all files from index (might fail if working tree is empty, that's ok)
            try:
                proc.run('git', 'rm', '-rf', '.', log=None)
            except Exception:
                pass  # Empty working tree is fine
            # Create initial commit
            proc.run('git', 'commit', '--allow-empty', '-m', 'Initial commit for attachments', log=None)
            err(f"Created branch '{branch}' for attachments")
    else:
        if dry_run:
            err(f"[DRY-RUN] Would switch to branch '{branch}'")
        else:
            proc.run('git', 'checkout', branch, log=None)

    # Process each attachment
    replacements = []
    for name, url in matches:
        # Extract asset ID from URL
        asset_id = url.split('/')[-1]

        if dry_run:
            err(f"[DRY-RUN] Would download: {name} from {url}")
        else:
            err(f"Downloading: {name} from {url}")

            # Download via gh api
            try:
                # gh api returns binary data for these URLs
                result = subprocess.run(['gh', 'api', url, '--method', 'GET'],
                                       capture_output=True, check=False)
                if result.returncode != 0:
                    err(f"Failed to download {url}")
                    continue

                data = result.stdout

                # Try to determine file extension from content
                # Common magic bytes
                ext = '.bin'
                if data.startswith(b'\x89PNG'):
                    ext = '.png'
                elif data.startswith(b'\xff\xd8\xff'):
                    ext = '.jpg'
                elif data.startswith(b'GIF8'):
                    ext = '.gif'
                elif data.startswith(b'%PDF'):
                    ext = '.pdf'
                elif data.startswith(b'PK\x03\x04'):
                    ext = '.zip'

                # Use asset_id as filename with detected extension
                filename = f"{asset_id}{ext}"

                # Write file
                with open(filename, 'wb') as f:
                    f.write(data)

                # Add and commit
                proc.run('git', 'add', filename, log=None)
                proc.run('git', 'commit', '-m', f'Add {name}: {filename}', log=None)

                err(f"Saved as: {filename}")

                # Get the blob SHA for permalink
                blob_sha = proc.line('git', 'rev-parse', f'HEAD:{filename}', log=None)

                # Get GitHub username from gist metadata via gh api
                github_username = None
                try:
                    github_username = proc.line('gh', 'api', f'/gists/{gist_id}', '--jq', '.owner.login', log=None)
                except Exception as e:
                    err(f"Warning: Could not get gist owner: {e}")

                if not github_username:
                    err(f"Error: Could not determine GitHub username for gist {gist_id}")
                    err("The gist permalink requires the owner's username")
                    exit(1)

                # Build gist permalink with username for githubusercontent.com format
                gist_url = f"https://gist.githubusercontent.com/{github_username}/{gist_id}/raw/{blob_sha}/{filename}"

                replacements.append((name, url, gist_url))

            except Exception as e:
                err(f"Error downloading {url}: {e}")
                continue

    if not dry_run and replacements:
        # Push attachments branch
        err(f"Pushing {branch} branch to gist...")
        proc.run('git', 'push', '-u', 'g', branch, log=None)

        # Switch back to main branch
        proc.run('git', 'checkout', current_branch, log=None)

        # Update description file with new URLs
        new_content = content
        for name, old_url, new_url in replacements:
            pattern = f"[{name}]: {old_url}"
            replacement = f"[{name}]: {new_url}"
            new_content = new_content.replace(pattern, replacement)

        # Write updated content
        with open(desc_file, 'w') as f:
            f.write(new_content)

        # Commit the URL updates
        proc.run('git', 'add', str(desc_file), log=None)
        commit_msg = f"Replace user-attachments with gist permalinks\n\nConverted {len(replacements)} attachment(s) to gist permalinks"
        proc.run('git', 'commit', '-m', commit_msg, log=None)

        err(f"Updated {len(replacements)} reference(s) in {desc_file}")
        err("You can now push these changes with 'ghprp' to update the PR")

    elif dry_run:
        err(f"[DRY-RUN] Would update {len(replacements)} reference(s)")


if __name__ == '__main__':
    cli()
