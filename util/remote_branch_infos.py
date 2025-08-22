"""Info about remote branches."""

import sys

if __name__ == '__main__':
    sys.path.append('.')

import fileinput

from util.branch_infos import BranchInfos
from util.remote_branch_info import RemoteBranchInfo


class RemoteBranchInfos(BranchInfos):

    def branch_info_class(self):
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
    RemoteBranchInfos(lines=fileinput.input(), patterns=sys.argv[1:])
