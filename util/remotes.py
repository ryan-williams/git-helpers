#!/usr/bin/python

import re
import subprocess

name_regex = '(?P<name>[^\s]+)'
opt_user_regex = '((?P<user>[^@]+)@)?'
opt_host_regex = '(?:(?P<host>[^:]+):)?'
domain_regex = '(?P<host>[^/]+)'
path_regex = '(?P<path>[^\s]+)'
push_label_regex = '\(push\)'

# e.g. 'origin	git@github.com:danvk/expandable-image-grid.git (push)'
ssh_push_re = re.compile(
    r'%s\s+%s%s%s?\s%s' % (name_regex, opt_user_regex, opt_host_regex, path_regex, push_label_regex))

# e.g. 'origin	https://github.com/danvk/git-helpers.git (push)'
https_push_re = re.compile(
    r'%s\s+https?://%s/%s\s%s' % (name_regex, domain_regex, path_regex, push_label_regex))

local_remote_re = re.compile(r'%s\s+%s\s%s' % (name_regex, path_regex, push_label_regex))

def _parse_remote(remote):
    return re.match(https_push_re, remote) or re.match(ssh_push_re, remote)


def _parse_remotes(remote_lines):
    return {remote.group('name'): remote
            for remote in map(_parse_remote, remote_lines)
            if remote}


def get_remotes():
    remote_lines = subprocess.Popen(
        ['git', 'remote', '-v'], stdout=subprocess.PIPE).communicate()[0].split('\n')
    return _parse_remotes(remote_lines)


if __name__ == '__main__':
    print get_remotes()
