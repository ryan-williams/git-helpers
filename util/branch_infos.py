__author__ = 'ryan'

import sys

"""Functionality for parsing and manipulating data about git branches."""

from branch_info import BranchInfo
from color import clen
import subprocess


class BranchInfos:

    def set_max(self, prop):
        prop_name, left_justify = prop if len(prop) == 2 else (prop, False)
        self.maxs[prop_name] = (
            max(
                [
                    clen(
                        getattr(bi, prop_name) if hasattr(bi, prop_name) else ''
                    ) for bi in self.branches
                ]
            ),
            left_justify
        )

    def cmd(self):
        return ["git", "branch", "-vv"]

    def branchInfoClass(self):
        return BranchInfo

    def get_lines(self):
        out, err = subprocess.Popen(
            self.cmd(), stdout=subprocess.PIPE).communicate()
        return out.decode('utf8').splitlines()

    def run_secondary_cmd(self):
        hashes = [bi.hash for bi in list(self.branches_by_name.values())]#map(lambda bi: bi.hash, self.branches_by_name.values())
        cmd = ['git', 'show',
               # NOTE(ryan): seems to omit 'master' branch in Git 1.7.1; doesn't seem to be necessary in general.
               #'--quiet',
               '-s',
               '--format=%h\t%ci\t%cr'] + hashes
        out, err = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()

        lines = out.decode().splitlines()
        for line in lines:
            if not line:
                continue
            cols = line.strip().split('\t')
            if len(cols) != 3:
                raise Exception(
                    'Expected 3 columns, found %d:\n%s\nfull output:\n%s' % (len(cols), cols, out))
            hsh, date, reldate = cols
            [bi.set_dates(date, reldate) for bi in self.branches_by_hash[hsh]]

    def maxed_fields(self):
        return [
            ('name',
             True), 'remote', 'ahead_str', 'behind_str', 'reldate', 'hash'
        ]

    def __init__(self, lines=None):
        self.maxs = {}

        lines = self.get_lines() if not lines else list(lines)

        self.branches_by_name = {}
        self.branches_by_hash = {}

        for line in lines:
            info = self.branchInfoClass()(line)
            self.branches_by_name[info.name] = info
            if info.hash not in self.branches_by_hash:
                self.branches_by_hash[info.hash] = []
            self.branches_by_hash[info.hash].append(info)

        self.run_secondary_cmd()

        self.branches = sorted(
            list(self.branches_by_name.values()), key=lambda bi: bi.datetime, reverse=True
        )

        if not self.branches:
            return

        [self.set_max(field) for field in self.maxed_fields()]

        try:
            for bi in self.branches:
                print(bi.to_string(self.maxs))
        except BrokenPipeError:
            sys.stderr.close()
