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


class Remote(object):

    @classmethod
    def parse(cls, input):
        if isinstance(input, list):
            return {remote.name: remote
                    for remote in map(cls.parse, input)
                    if remote}

        match = re.match(https_push_re, input) or re.match(ssh_push_re, input)
        if match:
            return Remote(match)
        return None

    def __init__(self, match):
        self.match = match
        self.name = match.group('name')
        self.host = match.group('host')
        self.opt_host_str = '%s:' % self.host if self.host else ''

        self.user = match.group('user') if 'user' in match.groupdict() else None
        self.opt_user_str = '%s@' % self.user if self.user else ''

        self.path = match.group('path')
        self.host_path_str = '%s%s' % (self.opt_host_str, self.path)

        self.is_local = not self.host
        self.is_remote = not self.is_local


def get_remotes():
    remote_lines = subprocess.Popen(
        ['git', 'remote', '-v'], stdout=subprocess.PIPE).communicate()[0].split('\n')
    return _parse_remotes(remote_lines)


if __name__ == '__main__':
    print get_remotes()
