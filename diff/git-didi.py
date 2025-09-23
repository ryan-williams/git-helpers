#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "click",
#     "utz",
# ]
# ///
"""Compare diffs between two git ranges - a 'diff of diffs' tool.

This tool is particularly useful for verifying rebases, especially when complex
conflict resolution was involved. It helps ensure that the actual changes in your
branch remain the same before and after rebasing onto a new upstream.

Common use case - checking a rebase:

After fetching and rebasing your branch onto main:
    git fetch
    git rebase main

You can verify the rebase preserved your changes:
    git-didi.py patch main@{1}..branch@{1} main..branch

This compares:
- Left side: Your changes before the rebase (main@{1}..branch@{1})
- Right side: Your changes after the rebase (main..branch)

The @{1} syntax refers to the previous position in the reflog. If both refs
moved exactly once during the rebase, @{1} will work. If you've done multiple
operations, you may need @{2}, @{3}, etc. Use `git reflog` to find the right
positions.

Aliases for common operations:
- gdds: Compare diff --stat output
- gddp: Compare patches file by file
- gddc: Compare individual commits

The tool automatically filters out spurious differences like git index SHAs
that change even when the actual patch content is identical.
"""

import difflib
import os
import sys
from subprocess import run, PIPE, Popen
from io import StringIO

from click import Choice, echo, group, style
from utz import err
from utz.cli import arg, flag, opt


def should_use_color(color_option: str) -> bool:
    """Determine if color should be used based on option and TTY status."""
    if color_option == 'always':
        return True
    elif color_option == 'never':
        return False
    else:  # auto
        return sys.stdout.isatty()


class Pager:
    """Context manager for paging output through less or similar."""

    def __init__(self, use_pager: str = 'auto'):
        """Initialize pager settings.

        Args:
            use_pager: 'always', 'never', or 'auto' (default)
        """
        self.use_pager = use_pager
        self.original_stdout = None
        self.buffer = None
        self.pager_process = None

    def should_page(self) -> bool:
        """Determine if paging should be used."""
        if self.use_pager == 'always':
            return True
        elif self.use_pager == 'never':
            return False
        else:  # auto
            # Use pager if output is to a TTY
            return sys.stdout.isatty()

    def __enter__(self):
        """Start capturing output for potential paging."""
        if self.should_page():
            # Capture output in a buffer first
            self.original_stdout = sys.stdout
            self.buffer = StringIO()
            sys.stdout = self.buffer
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Send captured output through pager if needed."""
        if self.original_stdout:
            # Restore original stdout
            sys.stdout = self.original_stdout

            if self.buffer:
                output = self.buffer.getvalue()

                # Only page if output is substantial (more than terminal height)
                try:
                    terminal_height = int(os.environ.get('LINES', 24))
                    output_lines = output.count('\n')

                    if output_lines > terminal_height - 2:  # Leave room for prompt
                        # Use git's pager settings if available
                        pager_cmd = run(['git', 'config', 'core.pager'],
                                      capture_output=True, text=True).stdout.strip()
                        if not pager_cmd:
                            # Default to less with good options
                            pager_cmd = 'less -FRSX'

                        # Send output through pager
                        try:
                            pager = Popen(pager_cmd, shell=True, stdin=PIPE, text=True)
                            pager.communicate(output)
                        except Exception:
                            # If pager fails, just print directly
                            print(output, end='')
                    else:
                        # Output fits in terminal, print directly
                        print(output, end='')
                except Exception:
                    # If anything goes wrong, just print
                    print(output, end='')


@group()
def cli():
    """Compare git diffs between two ranges.

    Useful for comparing changes before and after a rebase.
    """
    pass


@cli.command()
@opt('--color', type=Choice(['auto', 'always', 'never']), default='auto', help='When to use colored output (default: auto)')
@opt('--pager', type=Choice(['auto', 'always', 'never']), default='auto', help='When to use pager (default: auto)')
@arg('refspec1')
@arg('refspec2')
def stat(
    color: str,
    pager: str,
    refspec1: str,
    refspec2: str,
) -> None:
    """Compare git diff --stat output between two refspecs.

    Example: git-didi.py stat rmb..m/rw/ee m/main..ee
    """
    use_color = should_use_color(color)

    with Pager(pager):
        # Get diff --stat for both ranges
        result1 = run(['git', 'diff', '--stat', refspec1], capture_output=True, text=True)
        if result1.returncode != 0:
            err(f"Error getting diff for {refspec1}: {result1.stderr}")
            sys.exit(1)

        result2 = run(['git', 'diff', '--stat', refspec2], capture_output=True, text=True)
        if result2.returncode != 0:
            err(f"Error getting diff for {refspec2}: {result2.stderr}")
            sys.exit(1)

        lines1 = result1.stdout.splitlines()
        lines2 = result2.stdout.splitlines()

        # Show unified diff
        diff = difflib.unified_diff(
            lines1,
            lines2,
            fromfile=f'git diff --stat {refspec1}',
            tofile=f'git diff --stat {refspec2}',
            lineterm=''
        )

        has_changes = False
        for line in diff:
            has_changes = True
            if use_color:
                if line.startswith('+'):
                    echo(style(line, fg='green'))
                elif line.startswith('-'):
                    echo(style(line, fg='red'))
                elif line.startswith('@'):
                    echo(style(line, fg='cyan'))
                else:
                    echo(line)
            else:
                echo(line)

        if not has_changes:
            err("No differences in diff stats")


@cli.command()
@opt('--color', type=Choice(['auto', 'always', 'never']), default='auto', help='When to use colored output (default: auto)')
@opt('--pager', type=Choice(['auto', 'always', 'never']), default='auto', help='When to use pager (default: auto)')
@flag('-q', '--quiet', help='Only show files with differences')
@arg('refspec1')
@arg('refspec2')
def patch(
    color: str,
    pager: str,
    quiet: bool,
    refspec1: str,
    refspec2: str,
) -> None:
    """Compare patches file-by-file between two refspecs.

    Shows only files where the patches differ.
    """
    use_color = should_use_color(color)

    with Pager(pager):
        # Get list of changed files in both refspecs
        files1 = get_changed_files(refspec1)
        files2 = get_changed_files(refspec2)

        all_files = sorted(set(files1) | set(files2))

        different_files = []

        for filepath in all_files:
            # Get diff for this file in both refspecs
            diff1 = get_file_diff(refspec1, filepath)
            diff2 = get_file_diff(refspec2, filepath)

            # Normalize diffs to ignore index SHAs
            norm_diff1 = normalize_diff(diff1)
            norm_diff2 = normalize_diff(diff2)

            if norm_diff1 != norm_diff2:
                different_files.append(filepath)
                if not quiet:
                    echo(style(f"\n{'='*60}", fg='blue') if use_color else f"\n{'='*60}")
                    echo(style(f"File: {filepath}", fg='yellow', bold=True) if use_color else f"File: {filepath}")
                    echo(style(f"{'='*60}", fg='blue') if use_color else f"{'='*60}")

                    # Show the diff of diffs for this file
                    diff_lines = list(difflib.unified_diff(
                        diff1.splitlines(),
                        diff2.splitlines(),
                        fromfile=f'{filepath} in {refspec1}',
                        tofile=f'{filepath} in {refspec2}',
                        lineterm=''
                    ))

                    for line in diff_lines:
                        if use_color:
                            if line.startswith('+'):
                                echo(style(line, fg='green'))
                            elif line.startswith('-'):
                                echo(style(line, fg='red'))
                            elif line.startswith('@'):
                                echo(style(line, fg='cyan'))
                            else:
                                echo(line)
                        else:
                            echo(line)

        if quiet and different_files:
            echo(style("\nFiles with different patches:", fg='yellow', bold=True) if use_color else "\nFiles with different patches:")
            for f in different_files:
                echo(f"  {f}")

        if not different_files:
            err("No differences in patches")
        else:
            err(f"\n{len(different_files)} file(s) have different patches")


@cli.command()
@opt('--color', type=Choice(['auto', 'always', 'never']), default='auto', help='When to use colored output (default: auto)')
@opt('--pager', type=Choice(['auto', 'always', 'never']), default='auto', help='When to use pager (default: auto)')
@arg('refspec1')
@arg('refspec2')
def commits(
    refspec1: str,
    refspec2: str,
    color: str,
    pager: str,
) -> None:
    """Compare commits between two refspecs.

    First verifies that commits correspond (same count and messages),
    then shows per-commit differences.
    """
    use_color = should_use_color(color)

    with Pager(pager):
        # Get commit info for both refspecs
        commits1 = get_commits(refspec1)
        commits2 = get_commits(refspec2)

        if len(commits1) != len(commits2):
            err(f"Different number of commits: {len(commits1)} in {refspec1}, {len(commits2)} in {refspec2}")

        # Compare commit messages
        echo(style("Comparing commits:", fg='yellow', bold=True) if use_color else "Comparing commits:")
        for i, (c1, c2) in enumerate(zip(commits1, commits2)):
            sha1, msg1 = c1.split(' ', 1)
            sha2, msg2 = c2.split(' ', 1)

            if msg1 == msg2:
                echo(f"  [{i+1}] ✓ {msg1}")
            else:
                echo(style(f"  [{i+1}] ✗ Messages differ:", fg='red') if use_color else f"  [{i+1}] ✗ Messages differ:")
                echo(f"    {refspec1}: {msg1}")
                echo(f"    {refspec2}: {msg2}")

        # Compare each commit's changes
        echo(style("\nComparing commit patches:", fg='yellow', bold=True) if use_color else "\nComparing commit patches:")

        for i, (c1, c2) in enumerate(zip(commits1, commits2)):
            sha1 = c1.split(' ', 1)[0]
            sha2 = c2.split(' ', 1)[0]
            msg = c1.split(' ', 1)[1]

            # Get diff for each commit
            diff1 = run(['git', 'diff', f'{sha1}^', sha1], capture_output=True, text=True).stdout
            diff2 = run(['git', 'diff', f'{sha2}^', sha2], capture_output=True, text=True).stdout

            # Normalize to ignore index SHAs
            norm_diff1 = normalize_diff(diff1)
            norm_diff2 = normalize_diff(diff2)

            if norm_diff1 != norm_diff2:
                echo(style(f"\n[{i+1}] {msg} - DIFFERS", fg='red', bold=True) if use_color else f"\n[{i+1}] {msg} - DIFFERS")

                # Show file-by-file differences for this commit
                files1 = get_changed_files(f'{sha1}^..{sha1}')
                files2 = get_changed_files(f'{sha2}^..{sha2}')
                all_files = sorted(set(files1) | set(files2))

                for filepath in all_files:
                    file_diff1 = get_file_diff(f'{sha1}^..{sha1}', filepath)
                    file_diff2 = get_file_diff(f'{sha2}^..{sha2}', filepath)

                    # Normalize to ignore index SHAs
                    if normalize_diff(file_diff1) != normalize_diff(file_diff2):
                        echo(f"    {filepath}: patches differ")
            else:
                echo(f"[{i+1}] {msg} - identical")


def get_changed_files(refspec: str) -> list[str]:
    """Get list of files changed in a git refspec."""
    result = run(['git', 'diff', '--name-only', refspec], capture_output=True, text=True)
    if result.returncode != 0:
        return []
    return [f for f in result.stdout.strip().split('\n') if f]


def normalize_diff(diff_text: str) -> str:
    """Normalize diff text by removing variable parts like index SHAs."""
    lines = []
    for line in diff_text.splitlines():
        # Remove index line SHAs: "index abc123..def456" -> "index ..."
        if line.startswith('index '):
            lines.append('index ...')
        else:
            lines.append(line)
    return '\n'.join(lines)


def get_file_diff(refspec: str, filepath: str) -> str:
    """Get diff for a specific file in a refspec."""
    result = run(['git', 'diff', refspec, '--', filepath], capture_output=True, text=True)
    return result.stdout


def get_commits(refspec: str) -> list[str]:
    """Get list of commits in a refspec."""
    result = run(['git', 'log', '--oneline', refspec], capture_output=True, text=True)
    if result.returncode != 0:
        err(f"Error getting commits for {refspec}: {result.stderr}")
        return []
    return [line for line in result.stdout.strip().split('\n') if line]


if __name__ == '__main__':
    cli()
