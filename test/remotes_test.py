'''Tests for util/remotes.py.

Run via:

    nosetests
'''

from util import remotes

from nose.tools import *

def test_regex_https():
    remote = 'origin	https://github.com/danvk/git-helpers.git (push)'
    m = remotes._parse_remote(remote)
    assert m
    eq_({
        'name': 'origin',
        'host': 'github.com',
        'path': 'danvk/git-helpers.git',
        }, m.groupdict())


def test_regex_ssh():
    remote = 'origin	git@github.com:danvk/expandable-image-grid.git (push)'
    m = remotes._parse_remote(remote)
    assert m
    eq_({
        'name': 'origin',
        'host': 'github.com',
        'path': 'danvk/expandable-image-grid.git',
        'user': 'git'
        }, m.groupdict())
