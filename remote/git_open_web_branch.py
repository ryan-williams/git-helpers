#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "click",
#     "utz",
# ]
# ///
from __future__ import annotations

import re
from typing import Pattern, Callable

from click import command, option, argument
from utz import proc, silent, err

GH_SSH_REMOTE_URL_RGX = re.compile(r'git@github\.com:(?P<repo>[^/]+/[^/]+?)(?:\.git)?')
GH_HTTPS_REMOTE_URL_RGX = re.compile(r'https://github\.com/(?P<repo>[^/]+/[^/]+?)(?:\.git)?')
GL_SSH_REMOTE_URL_RGX = re.compile(r'git@gitlab\.com:(?P<repo>[^/]+/[^/]+?)(?:\.git)?')
GL_HTTPS_REMOTE_URL_RGX = re.compile(r'https://gitlab\.com/(?P<repo>.+)(?:\.git)?')
GH_GIST_SSH_RGX = re.compile(r'git@gist.github.com:(?P<id>[\da-f]{32}).git')
GH_GIST_HTTPS_RGX = re.compile(r'https://gist.github.com/(?P<id>[\da-f]{32})(?:.git)?')


@command
@option('-D', '--no-elide-default-ref', is_flag=True, help="Allow explicitly opening the remote's default ref; by default, a suffix like `/tree/main` will be elided before opening the URL")
@option('-n', '--dry-run', is_flag=True, help="Print the URL that would be opened, but don't actually attempt to `open` it")
@option('-r', '--remote', help='Open a branch from this remote')
@option('-R', '--local-ref', help='Look for remote branches that point at this local ref name')
@option('-u', '--upstream', is_flag=True, help='Open the upstream/tracked ref')
@option('-v', '--verbose', is_flag=True, help='Log intermediate subprocess commands and debugging info')
@argument('remote_ref', required=False)
def main(
    no_elide_default_ref: bool,
    dry_run: bool,
    remote: str | None,
    local_ref: str | None,
    upstream: bool,
    verbose: bool,
    remote_ref: str | None,
):
    """`open` an HTTPS URL for a Git remote branch corresponding to a local or remote ref."""
    log = err if verbose else silent
    if upstream:
        remote_ref = proc.line('git', 'rev-parse', '--abbrev-ref', '@{u}', log=log)
    if remote_ref:
        if remote:
            if not proc.check('git', 'show-ref', '--verify', '--quiet', f'refs/remotes/{remote}/{remote_ref}'):
                raise ValueError(f"{remote}/{remote_ref} found")  # TODO: optionally "force" open anyway
        else:
            if proc.check('git', 'show-ref', '--verify', '--quiet', f'refs/remotes/{remote_ref}', log=log):
                assert '/' in remote_ref
                remote, remote_ref = remote_ref.split('/', 1)
            else:
                tracked = proc.line('git', 'rev-parse', '--abbrev-ref', '@{u}', log=log)
                remote, tracked_branch = tracked.split('/', 1)
                log(f"Checking {remote}/{remote_ref} (from tracked {remote=})")
            if not proc.check('git', 'show-ref', '--verify', '--quiet', f'refs/remotes/{remote}/{remote_ref}', log=log):
                raise ValueError(f"Neither {remote_ref} nor {remote}/{remote_ref} found")
    else:
        local_ref = local_ref or 'HEAD'
        if not remote:
            tracked = proc.line('git', 'rev-parse', '--abbrev-ref', '%s@{u}' % ("" if local_ref == "HEAD" else local_ref), log=log, err_ok=True)
            if tracked:
                remote, tracked_branch = tracked.split('/', 1)
            else:
                remotes = proc.lines('git', 'remote', log=log)
                if len(remotes) == 1:
                    remote = remotes[0]
                elif not remotes:
                    raise ValueError("No remotes found")
                else:
                    raise ValueError(f"{len(remotes)} remotes found: {remotes}")
        remote_branches = [
            branch
            for branch in proc.lines('git', 'branch', '--format=%(refname:short)', '-r', '--points-at', local_ref, log=log)
            if branch == remote or branch.startswith(f"{remote}/")
        ]
        if remote_branches:
            remote_ref = re.sub(f'{remote}/?', '', remote_branches[0])
            if len(remote_branches) > 1:
                log(f"Found {len(remote_branches)} remote branches pointing at {local_ref=}: {', '.join(remote_branches)}. Using first {remote_ref=}")
        else:
            remote_ref = proc.line('git', 'log', '-1', '--format=%h', local_ref, log=log)
            log(f"No {remote=} branches found pointing at {local_ref=}; using SHA {remote_ref=}")

    remote_default_ref = proc.line('git', 'rev-parse', '--abbrev-ref', f'{remote}/HEAD')
    assert remote_default_ref.startswith(f"{remote}/"), remote_default_ref
    remote_default_ref = remote_default_ref.removeprefix(f"{remote}/")
    append_ref = remote_ref and (remote_ref != remote_default_ref or no_elide_default_ref)

    remote_url = proc.line('git', 'remote', 'get-url', remote, log=log)

    def get_url(rgxs: list[Pattern], fn: Callable[[...], str]) -> str | None:
        m = None
        for rgx in rgxs:
            m = rgx.fullmatch(remote_url)
            if m:
                break
        if m:
            return fn(**m.groupdict())

    url = get_url(
        [GH_SSH_REMOTE_URL_RGX, GH_HTTPS_REMOTE_URL_RGX],
        lambda repo: f'https://github.com/{repo}' + (f'/tree/{remote_ref}' if append_ref else ''),
    )
    if not url:
        url = get_url(
            [GL_SSH_REMOTE_URL_RGX, GL_HTTPS_REMOTE_URL_RGX],
            lambda repo: f'https://gitlab.com/{repo}' + (f'/-/tree/{remote_ref}' if append_ref else ''),
        )
    if not url:
        url = get_url(
            [GH_GIST_SSH_RGX, GH_GIST_HTTPS_RGX],
            lambda id: f'https://gist.github.com/{id}',
        )

    if dry_run:
        print(url)
    else:
        proc.run('open', url, log=log)


if __name__ == '__main__':
    main()
