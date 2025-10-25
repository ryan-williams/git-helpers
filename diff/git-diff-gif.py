#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "click",
# ]
# ///
import shlex
import shutil
import sys
from os import environ, makedirs
from os.path import splitext, exists, dirname, isdir
from subprocess import check_call, DEVNULL, CalledProcessError, check_output
from tempfile import TemporaryDirectory

import click

# Env var for optionally storing command (incl. any extra arguments) for the final `open` call. Will be parsed with
# `shlex.split`. Default command is:
# - `open -a "/Applications/Google Chrome.app"` (if `open` and Chrome both exist)
# - `open` (if only `open` exists)
# - skip opening otherwise
GIT_DIFF_GIF_OPEN_CMD = 'GIT_DIFF_GIF_OPEN_CMD'

DEFAULT_EXTENSIONS = [ '.jpg', '.png', '.jpeg', ]


def stderr(msg):
    sys.stderr.write(msg)
    sys.stderr.write('\n')


def run(*cmd, log=stderr, **kwargs):
    log(f'Running: {shlex.join(cmd)}')
    check_call(cmd, **kwargs)


def check(*cmd, stdout=DEVNULL, stderr=DEVNULL, **kwargs):
    try:
        check_call(cmd, stdout=stdout, stderr=stderr, **kwargs)
        return True
    except CalledProcessError as e:
        return False


def get_changed_imgs(refspec, *paths):
    return [
        path
        for path in check_output(['git', 'diff', '--name-only', refspec, '--', *paths]).decode().split('\n')
        if splitext(path)[-1] in DEFAULT_EXTENSIONS and exists(path)
    ]


def add_watermark(input_path, output_path, label, ref_info):
    """Add a watermark label to an image using ImageMagick."""
    # Use ImageMagick to add text overlay
    # Position: top-left corner with padding
    # White text with black shadow for visibility on any background
    run(
        'magick', input_path,
        '-gravity', 'NorthWest',
        '-pointsize', '24',
        '-fill', 'black',
        '-annotate', '+11+11', f'{label}\n{ref_info}',
        '-fill', 'white',
        '-annotate', '+10+10', f'{label}\n{ref_info}',
        output_path
    )


@click.command()
@click.option('-a', '--after', 'after_ref', help='Git ref for the "after" image; default: current worktree file')
@click.option('-b', '--before', 'before_ref', help='Git ref for the "before" image; default: `HEAD`')
@click.option('-d', '--delay', default='100', help='Gif delay between frames, in 1/100ths of a second')
@click.option('-f', '--force', is_flag=True, help='Overwrite an existing .gif at the --output path')
@click.option('-o', '--output', 'out_path', help="Write resulting .gif(s) here. By default, they're written to a tempdir, and cleaned up on program exit. If more than one <path> is passed, this is interpreted as a directory, .gif paths are relativized inside it, and their extensions are replaced with `.gif`")
@click.option('-O', '--no-open', is_flag=True, help='Skip `open`ing the generated .gif')
@click.argument('paths', nargs=-1)  # Paths to Git-tracked image to make diff-gifs of
def main(before_ref, after_ref, delay, force, out_path, no_open, paths):
    if after_ref:
        if not before_ref:
            before_ref = f'{after_ref}^'
        refspec = f'{before_ref}..{after_ref}'
    else:
        if not before_ref:
            before_ref = 'HEAD'
        refspec = before_ref

    if paths:
        paths = [
            expanded_path
            for path in paths
            for expanded_path in (get_changed_imgs(refspec, path) if isdir(path) else [path])
        ]
    else:
        paths = get_changed_imgs(refspec)

    out_dir = None
    tmp_out_paths = True
    if out_path:
        tmp_out_paths = False
        if len(paths) > 1:
            out_dir = out_path

    out_paths = []
    with TemporaryDirectory() as tmpdir:
        for path in paths:
            name, ext = splitext(path)
            before_path_raw = f'{tmpdir}/before_raw{ext}'
            with open(before_path_raw, 'wb') as f:
                run('git', 'show', f'{before_ref}:{path}', stdout=f)

            # Get short SHA for before ref
            before_sha = check_output(['git', 'rev-parse', '--short', before_ref]).decode().strip()

            if after_ref:
                after_path_raw = f'{tmpdir}/after_raw{ext}'
                with open(after_path_raw, 'wb') as f:
                    run('git', 'show', f'{after_ref}:{path}', stdout=f)
                after_sha = check_output(['git', 'rev-parse', '--short', after_ref]).decode().strip()
                after_info = f'{after_ref} ({after_sha})'
            else:
                # Copy worktree file to temp location to avoid ImageMagick issues with special chars (e.g., colons)
                after_path_raw = f'{tmpdir}/after_raw{ext}'
                shutil.copy2(path, after_path_raw)
                after_info = 'worktree'

            # Add watermarks
            before_path = f'{tmpdir}/before{ext}'
            after_path = f'{tmpdir}/after{ext}'
            add_watermark(before_path_raw, before_path, 'Before', f'{before_ref} ({before_sha})')
            add_watermark(after_path_raw, after_path, 'After', after_info)

            if out_dir:
                out_path = f'{out_dir}/{name}.gif'
                makedirs(dirname(out_path), exist_ok=True)
            elif len(paths) == 1 and out_path:
                out_path = f'{name}.gif'
            else:
                out_path = f'{tmpdir}/{name}.gif'
            if exists(out_path):
                if force:
                    stderr(f'Overwriting {out_path}')
                else:
                    raise RuntimeError(f'--output {out_path} exists; pass -f/--force to overwrite')

            makedirs(dirname(out_path), exist_ok=True)
            run('magick', '-delay', delay, '-dispose', 'previous', before_path, after_path, out_path)
            out_paths.append(out_path)

        do_open = not no_open
        if do_open:
            if check('which', 'open'):
                for out_path in out_paths:
                    open_cmd = environ.get(GIT_DIFF_GIF_OPEN_CMD, '')
                    if open_cmd:
                        open_cmd = shlex.split(open_cmd)
                    else:
                        open_cmd = ['open']

                        # On macOS, Chrome seems like the best way to `open` .gifs. Preview opens all the frames as separate
                        # images.
                        chrome_path = '/Applications/Google Chrome.app'
                        if exists(chrome_path):
                            open_cmd += [ '-a', chrome_path]
                    open_cmd += [ out_path ]
                    run(*open_cmd)
                if tmp_out_paths:
                    # Give user a chance to inspect `open`ed .gifs before the tempdir is cleaned up
                    input('[enter] to exit')
            else:
                stderr('No `open` executable found, skipping `open`')


if __name__ == '__main__':
    main()
