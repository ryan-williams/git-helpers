#!/usr/bin/python

import re
import subprocess

# e.g. 'origin	git@github.com:danvk/expandable-image-grid.git (push)'
ssh_push_re = re.compile(
    '(?P<name>[^\s]+)\s+((?P<user>[^@]+)@)?(?P<host>[^:]+)(?::(?P<path>[^\s]+))?\s\(push\)')

# e.g. 'origin	https://github.com/danvk/git-helpers.git (push)'
https_push_re = re.compile(
    r'(?P<name>[^\s]+)\s+https?://(?P<host>[^/]+)/(?P<path>[^\s]+)\s\(push\)')


def _parse_remote(remote):
    return re.match(https_push_re, remote) or re.match(ssh_push_re, remote)


def get_remotes():
    remote_lines = subprocess.Popen(
        ['git', 'remote', '-v'], stdout=subprocess.PIPE).communicate()[0].split('\n')
    remotes = {}
    map(
        lambda remote: remotes.update({remote.group('name'): remote}),
        filter(
            lambda x: x,
            map(_parse_remote, remote_lines)
        )
    )
    return remotes

if __name__ == '__main__':
    print get_remotes()
