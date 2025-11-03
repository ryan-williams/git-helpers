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
from concurrent.futures import ThreadPoolExecutor, as_completed
from subprocess import run, PIPE, Popen
from io import StringIO

from click import Choice, echo, group, style
from utz import err
from utz.cli import arg, flag, opt


# Common option decorators
color_opt = opt('-c', '--color', type=Choice(['auto', 'always', 'never']), default='auto', help='When to use colored output (default: auto)')
pager_opt = opt('--pager', type=Choice(['auto', 'always', 'never']), default='auto', help='When to use pager (default: auto)')
find_copies_opt = opt('-C', '--find-copies', type=str, metavar='[<n>]', help='Detect copies as well as renames (similarity threshold, e.g., 50% or 0.5)')
find_renames_opt = opt('-M', '--find-renames', type=str, metavar='[<n>]', help='Detect renames (similarity threshold, e.g., 50% or 0.5)')
ignore_whitespace_flag = flag('-w', '--ignore-whitespace', help='Pass -w to git diff commands to ignore whitespace')


def common_opts(func):
    """Apply common options to all commands."""
    func = color_opt(func)
    func = pager_opt(func)
    func = find_copies_opt(func)
    func = find_renames_opt(func)
    func = ignore_whitespace_flag(func)
    return func


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
@common_opts
@arg('refspec1')
@arg('refspec2')
@arg('paths', nargs=-1)
def stat(
    color: str,
    pager: str,
    find_copies: str,
    find_renames: str,
    ignore_whitespace: bool,
    refspec1: str,
    refspec2: str,
    paths: tuple[str, ...],
) -> None:
    """Compare git diff --stat output between two refspecs.

    Example: git-didi.py stat rmb..m/rw/ee m/main..ee
    Optionally filter to specific paths.
    """
    use_color = should_use_color(color)

    with Pager(pager):
        # Use --numstat for machine-readable output (fixed format, no spacing issues)
        # Only use --follow when filtering to a single path
        use_follow = len(paths) == 1
        cmd1 = build_diff_cmd(ignore_whitespace, find_renames, find_copies, follow=use_follow)
        cmd1.extend(['--numstat', refspec1])
        if paths:
            cmd1.extend(['--', *paths])
        result1 = run(cmd1, capture_output=True, text=True)
        if result1.returncode != 0:
            err(f"Error getting diff for {refspec1}: {result1.stderr}")
            sys.exit(1)

        cmd2 = build_diff_cmd(ignore_whitespace, find_renames, find_copies, follow=use_follow)
        cmd2.extend(['--numstat', refspec2])
        if paths:
            cmd2.extend(['--', *paths])
        result2 = run(cmd2, capture_output=True, text=True)
        if result2.returncode != 0:
            err(f"Error getting diff for {refspec2}: {result2.stderr}")
            sys.exit(1)

        lines1 = result1.stdout.splitlines()
        lines2 = result2.stdout.splitlines()

        # Show unified diff
        diff = difflib.unified_diff(
            lines1,
            lines2,
            fromfile=f'git diff --numstat {refspec1}',
            tofile=f'git diff --numstat {refspec2}',
            lineterm=''
        )

        has_changes = False
        for line in diff:
            has_changes = True
            if use_color:
                if line.startswith('+'):
                    echo(style(line, fg='green'), color=True)
                elif line.startswith('-'):
                    echo(style(line, fg='red'), color=True)
                elif line.startswith('@'):
                    echo(style(line, fg='cyan'), color=True)
                else:
                    echo(line)
            else:
                echo(line)

        if not has_changes:
            err("No differences in diff stats")


@cli.command()
@common_opts
@opt('-U', '--unified', type=int, default=3, help='Number of context lines to show (default: 3)')
@flag('-q', '--quiet', help='Only show files with differences')
@arg('refspec1')
@arg('refspec2')
@arg('paths', nargs=-1)
def patch(
    color: str,
    pager: str,
    find_copies: str,
    find_renames: str,
    unified: int,
    quiet: bool,
    ignore_whitespace: bool,
    refspec1: str,
    refspec2: str,
    paths: tuple[str, ...],
) -> None:
    """Compare patches file-by-file between two refspecs.

    Shows only files where the patches differ.
    Optionally filter to specific paths.
    """
    # Determine color BEFORE pager redirects stdout
    use_color = should_use_color(color)

    with Pager(pager):
        # Get list of changed files in both refspecs
        files1 = get_changed_files(refspec1, paths)
        files2 = get_changed_files(refspec2, paths)

        all_files = sorted(set(files1) | set(files2))

        # Fetch all diffs in parallel
        def fetch_diffs(filepath):
            diff1 = get_file_diff(refspec1, filepath, ignore_whitespace, unified, find_renames, find_copies)
            diff2 = get_file_diff(refspec2, filepath, ignore_whitespace, unified, find_renames, find_copies)
            return filepath, diff1, diff2

        file_diffs = {}
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(fetch_diffs, fp): fp for fp in all_files}
            for future in as_completed(futures):
                filepath, diff1, diff2 = future.result()
                file_diffs[filepath] = (diff1, diff2)

        # Process results in order
        different_files = []
        for filepath in all_files:
            diff1, diff2 = file_diffs[filepath]

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
                            # Handle unified diff headers from outer diff first (---, +++, @@)
                            # These are lines from the outer diff, not nested patterns
                            if line.startswith('---') and not line.startswith('----'):
                                # Real outer diff header - red fg
                                echo(style(line, fg='red'), color=True)
                                continue
                            elif line.startswith('+++') and not line.startswith('++++'):
                                # Real outer diff header - green fg
                                echo(style(line, fg='green'), color=True)
                                continue
                            elif line.startswith('@@') and not (line.startswith('-@@') or line.startswith('+@@') or line.startswith(' @@')):
                                # Hunk header from outer diff (not nested)
                                echo(style(line, fg='cyan'), color=True)
                                continue
                            elif line.startswith('-@@') or line.startswith('-index ') or line.startswith('-diff ') or line.startswith('----') or line.startswith('-+++'):
                                # Nested metadata in removed section - red fg only
                                echo(style(line, fg='red'), color=True)
                                continue
                            elif line.startswith('+@@') or line.startswith('+index ') or line.startswith('+diff ') or line.startswith('++++') or line.startswith('+---'):
                                # Nested metadata in added section - green fg only
                                echo(style(line, fg='green'), color=True)
                                continue

                            # Handle nested diff patterns (diff of diffs)
                            # Use 256-color palette matching Claude's diff colors
                            # Greens: 28 (brighter #00a858-like), 22 (darker #005e25-like)
                            # Reds: 161 (brighter #c1536a-like), 88 (darker #852135-like)
                            # Background determined by FIRST char: + = green, - = red
                            # First 2 chars get their own bg colors based on symbols
                            # All lines in the nested diff have outer prefix (+, -, or space)
                            if len(line) >= 2 and line[0] in '+-':
                                prefix = line[:2]
                                rest = line[2:]

                                # Determine prefix backgrounds based on each char
                                prefix_bg = []
                                for char in prefix:
                                    if char == '+':
                                        prefix_bg.append('28')  # bright green
                                    elif char == '-':
                                        prefix_bg.append('161')  # bright red
                                    else:  # space
                                        prefix_bg.append('0')  # black/clear

                                # Determine line background based on first char
                                if line[0] == '+':
                                    line_bg_bright = '28'
                                    line_bg_dark = '22'
                                    line_bg_vdark = '23'
                                else:  # '-'
                                    line_bg_bright = '161'
                                    line_bg_dark = '88'
                                    line_bg_vdark = '52'

                                if line.startswith('++'):
                                    # Added line in added section - white on bright green (bold)
                                    print(f'\033[1;38;5;231;48;5;{prefix_bg[0]}m{prefix[0]}\033[48;5;{prefix_bg[1]}m{prefix[1]}\033[48;5;{line_bg_bright}m{rest}\033[0m')
                                elif line.startswith('--'):
                                    # Removed line in removed section - white on bright red (bold)
                                    print(f'\033[1;38;5;231;48;5;{prefix_bg[0]}m{prefix[0]}\033[48;5;{prefix_bg[1]}m{prefix[1]}\033[48;5;{line_bg_bright}m{rest}\033[0m')
                                elif line.startswith('+ '):
                                    # Context line in added section - white on very dark green
                                    print(f'\033[38;5;231;48;5;{prefix_bg[0]}m{prefix[0]}\033[48;5;{prefix_bg[1]}m{prefix[1]}\033[48;5;{line_bg_vdark}m{rest}\033[0m')
                                elif line.startswith('- '):
                                    # Context line in removed section - white on very dark red
                                    print(f'\033[38;5;231;48;5;{prefix_bg[0]}m{prefix[0]}\033[48;5;{prefix_bg[1]}m{prefix[1]}\033[48;5;{line_bg_vdark}m{rest}\033[0m')
                                elif line.startswith('+-'):
                                    # Line in added section (+ first char = green bg)
                                    print(f'\033[38;5;231;48;5;{prefix_bg[0]}m{prefix[0]}\033[48;5;{prefix_bg[1]}m{prefix[1]}\033[48;5;{line_bg_dark}m{rest}\033[0m')
                                elif line.startswith('-+'):
                                    # Line in removed section (- first char = red bg)
                                    print(f'\033[38;5;231;48;5;{prefix_bg[0]}m{prefix[0]}\033[48;5;{prefix_bg[1]}m{prefix[1]}\033[48;5;{line_bg_dark}m{rest}\033[0m')
                                elif line.startswith('+'):
                                    # Any other line in added section (e.g., +diff, +index)
                                    print(f'\033[38;5;231;48;5;{prefix_bg[0]}m{prefix[0]}\033[48;5;{prefix_bg[1] if len(prefix) > 1 else line_bg_dark}m{prefix[1] if len(prefix) > 1 else ""}\033[48;5;{line_bg_dark}m{rest}\033[0m')
                                elif line.startswith('-'):
                                    # Any other line in removed section (e.g., -diff, -index)
                                    print(f'\033[38;5;231;48;5;{prefix_bg[0]}m{prefix[0]}\033[48;5;{prefix_bg[1] if len(prefix) > 1 else line_bg_dark}m{prefix[1] if len(prefix) > 1 else ""}\033[48;5;{line_bg_dark}m{rest}\033[0m')
                                else:
                                    echo(line)
                            elif line.startswith(' '):
                                # Context line from outer diff (no color)
                                echo(line)
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
@color_opt
def swatches(color: str) -> None:
    """Display color swatches for all 6 nested diff patterns.

    Shows example lines formatted as they would appear in a diff-of-diffs,
    demonstrating all possible combinations of outer and inner diff markers.
    """
    use_color = should_use_color(color)

    if not use_color:
        err("Color swatches require color output. Use --color=always")
        return

    echo(style("\ngddp Color Swatches - Diff of Diffs Patterns", fg='yellow', bold=True))
    echo(style("=" * 50, fg='blue'))
    echo("\nSimulated diff-of-diffs output showing all 6 patterns:\n")

    # Simulate a diff context
    echo(style("@@ -10,6 +10,6 @@ def example():", fg='cyan'))

    # ++ pattern
    prefix = '++'
    rest = 'version = "2.0.0"  # Added line in added section'
    print(f'\033[1;38;5;231;48;5;28m{prefix[0]}\033[48;5;28m{prefix[1]}\033[48;5;28m{rest}\033[0m')

    # -- pattern
    prefix = '--'
    rest = 'version = "1.0.0"  # Removed line in removed section'
    print(f'\033[1;38;5;231;48;5;161m{prefix[0]}\033[48;5;161m{prefix[1]}\033[48;5;161m{rest}\033[0m')

    # + (space) pattern
    prefix = '+ '
    rest = 'author = "example"  # Context in added section'
    print(f'\033[38;5;231;48;5;28m{prefix[0]}\033[48;5;0m{prefix[1]}\033[48;5;23m{rest}\033[0m')

    # - (space) pattern
    prefix = '- '
    rest = 'license = "MIT"  # Context in removed section'
    print(f'\033[38;5;231;48;5;161m{prefix[0]}\033[48;5;0m{prefix[1]}\033[48;5;52m{rest}\033[0m')

    # +- pattern
    prefix = '+-'
    rest = 'status = "deprecated"  # Line type changed (+- mixed)'
    print(f'\033[38;5;231;48;5;28m{prefix[0]}\033[48;5;161m{prefix[1]}\033[48;5;22m{rest}\033[0m')

    # -+ pattern
    prefix = '-+'
    rest = 'status = "active"  # Line type changed (-+ mixed)'
    print(f'\033[38;5;231;48;5;161m{prefix[0]}\033[48;5;28m{prefix[1]}\033[48;5;88m{rest}\033[0m')

    echo("\n" + style("Color Key:", fg='yellow', bold=True))
    echo("  First 2 chars: Individual bg colors per symbol")
    echo("    + → bright green (28)")
    echo("    - → bright red (161)")
    echo("    (space) → black/clear (0)")
    echo("\n  Rest of line: Background based on first char")
    echo("    ++ → bright green (28, bold)")
    echo("    -- → bright red (161, bold)")
    echo("    + (space) → very dark green (23)")
    echo("    - (space) → very dark red (52)")
    echo("    +- → dark green (22)")
    echo("    -+ → dark red (88)")
    echo()


@cli.command()
@common_opts
@opt('-U', '--unified', type=int, default=3, help='Number of context lines to show (default: 3)')
@arg('refspec1')
@arg('refspec2')
def commits(
    color: str,
    pager: str,
    find_copies: str,
    find_renames: str,
    unified: int,
    ignore_whitespace: bool,
    refspec1: str,
    refspec2: str,
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
            cmd1 = ['git', 'diff']
            if ignore_whitespace:
                cmd1.append('-w')
            cmd1.extend([f'{sha1}^', sha1])
            diff1 = run(cmd1, capture_output=True, text=True).stdout

            cmd2 = ['git', 'diff']
            if ignore_whitespace:
                cmd2.append('-w')
            cmd2.extend([f'{sha2}^', sha2])
            diff2 = run(cmd2, capture_output=True, text=True).stdout

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
                    file_diff1 = get_file_diff(f'{sha1}^..{sha1}', filepath, ignore_whitespace, unified, find_renames, find_copies)
                    file_diff2 = get_file_diff(f'{sha2}^..{sha2}', filepath, ignore_whitespace, unified, find_renames, find_copies)

                    # Normalize to ignore index SHAs
                    if normalize_diff(file_diff1) != normalize_diff(file_diff2):
                        echo(f"    {filepath}: patches differ")
            else:
                echo(f"[{i+1}] {msg} - identical")


def build_diff_cmd(
    ignore_whitespace: bool = False,
    find_renames: str = None,
    find_copies: str = None,
    follow: bool = False,
) -> list[str]:
    """Build base git diff command with common options."""
    cmd = ['git', 'diff']
    if follow:
        cmd.append('--follow')
    if ignore_whitespace:
        cmd.append('-w')
    if find_renames:
        cmd.append(f'-M{find_renames}')
    if find_copies:
        cmd.append(f'-C{find_copies}')
    return cmd


def get_changed_files(refspec: str, paths: tuple[str, ...] = ()) -> list[str]:
    """Get list of files changed in a git refspec, optionally filtered by paths."""
    cmd = ['git', 'diff', '--name-only', refspec]
    if paths:
        cmd.extend(['--', *paths])
    result = run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        err(f"Error getting changed files for {refspec}: {result.stderr.strip()}")
        sys.exit(1)
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


def get_file_diff(
    refspec: str,
    filepath: str,
    ignore_whitespace: bool = False,
    unified: int = 3,
    find_renames: str = None,
    find_copies: str = None,
) -> str:
    """Get diff for a specific file in a refspec."""
    cmd = build_diff_cmd(ignore_whitespace, find_renames, find_copies, follow=True)
    cmd.extend([f'-U{unified}', refspec, '--', filepath])
    result = run(cmd, capture_output=True, text=True)
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
