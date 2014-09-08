#!/usr/bin/python

import re
import subprocess

push_remote_re = '(?P<name>[^\s]+)\s+((?P<user>[^@]+)@)?(?P<host>[^:]+)(?::(?P<path>[^\s]+))?\s\\(push\\)'


def get_remotes():
    remote_lines = subprocess.Popen(
        ['git', 'remote', '-v'], stdout=subprocess.PIPE).communicate()[0].split('\n')
    remotes = {}
    map(
        lambda remote: remotes.update({remote.group('name'): remote}),
        filter(
            lambda x: x,
            map(
                lambda line: re.match(push_remote_re, line),
                remote_lines
            )
        )
    )
    return remotes

if __name__ == '__main__':
    print get_remotes()
