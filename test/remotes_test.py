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


def test_parse_remote_lines():
    lines = [
        'origin\thttps://github.com/danvk/git-helpers.git (fetch)',
        'origin\thttps://github.com/danvk/git-helpers.git (push)',
        'upstream\thttps://github.com/ryan-williams/git-helpers.git (fetch)',
        'upstream\thttps://github.com/ryan-williams/git-helpers.git (push)'
    ]
    rs = remotes._parse_remotes(lines)
    eq_(['origin', 'upstream'], sorted(rs.keys()))
    eq_({
        'name': 'origin',
        'host': 'github.com',
        'path': 'danvk/git-helpers.git',
    }, rs['origin'].groupdict())
    eq_({
        'name': 'upstream',
        'host': 'github.com',
        'path': 'ryan-williams/git-helpers.git',
    }, rs['upstream'].groupdict())
