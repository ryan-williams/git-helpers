'''Tests for util/remotes.py.

Run via:

    nosetests
'''

from util.remotes import Remote

from nose.tools import *


def test_regex_https():
    line ='origin	https://github.com/danvk/git-helpers.git (push)'
    remote = Remote.parse(line)
    assert remote
    assert remote.name == 'origin'
    assert remote.host == 'github.com'
    assert remote.path == 'danvk/git-helpers.git'


def test_regex_ssh():
    line ='origin	git@github.com:danvk/expandable-image-grid.git (push)'
    remote = Remote.parse(line)
    assert remote
    assert remote.name == 'origin'
    assert remote.host == 'github.com'
    assert remote.path == 'danvk/expandable-image-grid.git'
    assert remote.user == 'git'


def test_parse_remote_lines():
    lines = [
        'origin\thttps://github.com/danvk/git-helpers.git (fetch)',
        'origin\thttps://github.com/danvk/git-helpers.git (push)',
        'upstream\thttps://github.com/ryan-williams/git-helpers.git (fetch)',
        'upstream\thttps://github.com/ryan-williams/git-helpers.git (push)'
    ]
    remotes = Remote.parse(lines)
    eq_(['origin', 'upstream'], sorted(remotes.keys()))

    assert remotes['origin'].name == 'origin'
    assert remotes['origin'].host == 'github.com'
    assert remotes['origin'].path == 'danvk/git-helpers.git'

    assert remotes['upstream'].name == 'upstream'
    assert remotes['upstream'].host == 'github.com'
    assert remotes['upstream'].path == 'ryan-williams/git-helpers.git'
