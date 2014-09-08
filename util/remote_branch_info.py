__author__ = 'ryan'

from branch_info import BranchInfo
from regexs import hash_regex, named, normal_refname_regex


class RemoteBranchInfo(BranchInfo):

    regex_pieces = [
        " \((?P<names>[^)]+)\) ",
        "%s " % hash_regex,
        "%s " % named("date", "[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}"),
        "[\-+][0-9]{4} ",
        "\(%s\) " % named("reldate", "[^)]+"),
        named("description", ".*")
    ]

    def colors(self):
        return {
            'names': 'BWhite',
            'hash': 'IRed',
            'date': 'IBlue',
            'reldate': 'IGreen',
            'description': 'White'
        }

    def fields(self):
        return [
            'names',
            '  ',
            'hash',
            ' ',
            'reldate',
            ' ',
            'date',
            ' ',
            'description'
        ]

    def __init__(self, line):
        BranchInfo.__init__(self, line)

        self.names = self.get("names")
        self.name = self.names.split(',')[0]

        self.set_dates(self.get("date"), self.get("reldate"))
