#!/usr/bin/env python

import os
import re
import subprocess
import sys

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
        return {remote.name: remote
                for remote in map(cls.parse_line, input)
                if remote}

    @classmethod
    def parse_line(cls, line):
        match = re.match(https_push_re, line) or re.match(ssh_push_re, line)
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
        self.user_host_str = '%s%s' % (self.opt_user_str, self.host)

        self.path = match.group('path')
        self.host_path_str = '%s%s' % (self.opt_host_str, self.path)

        self.user_host_path_str = '%s%s' % (self.opt_user_str, self.host_path_str)

        self.is_local = not self.host
        self.is_remote = not self.is_local


def get_remotes():
    remote_lines = subprocess.Popen(
        ['git', 'remote', '-v'], stdout=subprocess.PIPE).communicate()[0].decode().split('\n')
    return Remote.parse(remote_lines)


def remote_exists(remote_name):
    return remote_name in subprocess.check_output(['git', 'remote']).split('\n')


def prompt(p, default='y'):
    while True:
        inp = input(p)
        if (not inp and default.lower() == 'y') or inp.lower() == 'y' or inp.lower() == 'yes':
            return True
        if (not inp and default.lower() == 'n') or inp.lower() == 'n' or inp.lower() == 'no':
            return False


def remove_remote(remote_name):
    print('Removing remote: %s' % remote_name)
    subprocess.check_call(['git', 'remote', 'remove', remote_name])


def maybe_remove_remote_if_exists(remote_name):
    if remote_exists(remote_name):
        if prompt('Found existing remote: %s; remove? [Y/n]: ' % remote_name):
            remove_remote(remote_name)
            return True
        else:
            return False
    else:
        return True


def get_mirror_remote():

    remote_names = []
    if len(sys.argv) > 1:
        remote_names = [sys.argv[1]]
    elif os.environ.get('MIRROR_REMOTES'):
        remote_names = os.environ.get('MIRROR_REMOTES').split(',')
    else:
        raise Exception(
            "Pass remote name as an argument, or set MIRROR_REMOTES environment variable "
            "with a comma-separated list of eligible remotes"
        )

    remotes = get_remotes()
    found_remotes = [remotes[remote]
                     for remote in remote_names if remote in remotes]
    if len(found_remotes) > 1:
        raise Exception('Found multiple eligible remotes: %s' % ','.join(
            [remote.name for remote in found_remotes]))
    if not found_remotes:
        raise Exception('Found no eligible remotes: %s' % ','.join(remote_names))

    return found_remotes[0]



if __name__ == '__main__':
    print(get_remotes())
