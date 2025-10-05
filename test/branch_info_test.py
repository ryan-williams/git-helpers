# -*- coding: utf-8 -*-
'''Tests for util/branch_info.py.

Run via:

    nosetests
'''

from git_helpers.util.branch_info import BranchInfo

from nose.tools import *

import sys


def test_unicode_branch():
    line = u'* unicøde        f557531 [origin/unicøde] Allow ☃ unicode messages.'
    branch = BranchInfo(line)
    eq_(branch.name, u'unicøde')
    eq_(branch.hash, 'f557531')
    eq_(branch.remote, u'origin/unicøde')
    eq_(branch.description, u'Allow ☃ unicode messages.')
