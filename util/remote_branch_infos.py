"""Info about remote branches."""

__author__ = 'ryan'

import sys

if __name__ == '__main__':
    sys.path.append('.')

from branch_infos import BranchInfos
from remote_branch_info import RemoteBranchInfo
import fileinput


class RemoteBranchInfos(BranchInfos):

    def branchInfoClass(self):
        return RemoteBranchInfo

    def run_secondary_cmd(self):
        pass

    def maxed_fields(self):
        return [
            ('names', True),
            'hash',
            'date',
            'reldate'
        ]


if __name__ == "__main__":
    RemoteBranchInfos(fileinput.input())
