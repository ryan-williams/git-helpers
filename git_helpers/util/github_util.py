'''Utilities for interacting with GitHub.'''

from collections import OrderedDict
import re

from git_helpers.util.remotes import get_remotes


def _uniqueify(iterable):
    return list(OrderedDict.fromkeys(iterable))


def get_github_remotes():
    '''Returns a list of github remotes for the current repo.'''
    return _uniqueify([remote for remote in list(get_remotes().values())
                              if remote.host == 'github.com'])


def make_github_url(remote):
    '''Converts the bit of a remote after github.com to a github repo URL.'''
    # remote looks like 'foo/bar.git'
    assert '.git' in remote
    return 'https://github.com/%s' % re.sub(r'\.git$', '', remote)
