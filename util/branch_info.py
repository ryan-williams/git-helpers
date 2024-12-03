__author__ = 'ryan'

"""Encapsulates info about one git branch."""

from color import clen, color
from datetime import datetime as dt
from regexs import refname_regex, captured_whitespace_regex, hash_regex
from reldate_util import shorten_reldate
import re


def fixed(width, s, left_justified=False):
    spaces = (' ' * (width - clen(s)))
    return s + spaces if left_justified else spaces + s


class BranchInfo(object):

    line_begin_regex = r"(?P<line_begin>^(?:(?P<is_active>\*)| ) )"

    ahead_regex = "ahead (?P<ahead>[0-9]+)"
    behind_regex = "behind (?P<behind>[0-9]+)"
    ahead_behind_regex = "(?:%s)?(?:, )?(?:%s)?" % (
        ahead_regex, behind_regex)
    upstream_gone_regex = '(?P<gone>gone)'
    tracking_info_regex = r"(?:\s\[%s(?:: %s|%s)?\])?" % (
        refname_regex('tracking_name'), ahead_behind_regex, upstream_gone_regex)

    description_regex = r"\s(?P<description>.*)"

    regex_pieces = [
        line_begin_regex,
        refname_regex('name'),
        captured_whitespace_regex('pre_hash'),
        hash_regex,
        tracking_info_regex,
        description_regex
    ]

    def regex(self):
        return ''.join(self.regex_pieces)

    def get(self, key, default=''):
        return self.dict[key] if key in self.dict and self.dict[key] is not None else default

    def colors(self):
        return {
            'name': 'BGreen' if 'is_active' in self.dict and self.dict['is_active'] else 'BWhite',
            'hash': 'IRed',
            'remote': 'Yellow' if not 'gone' in self.dict or not self.dict['gone'] else ['On_Red', 'BIYellow'],
            'ahead_str': 'ICyan',
            'behind_str': 'IPurple',
            'date': 'IBlue',
            'reldate': 'IGreen',
            'description': 'White'
        }

    def __getattr__(self, item):
        if re.match(r'\s+$', item):
            return item
        return super(BranchInfo, self).__getattribute__(item)

    def __init__(self, line):
        self.line = line

        match = re.match(self.regex(), line, re.UNICODE)
        if (match):
            pass
        else:
            raise Exception(
                u'Invalid branch line:\n%s\nregex:\n%s' % (line, '\n'.join(self.regex_pieces)))

        self.dict = match.groupdict()

        self.line_begin = self.get('line_begin')
        self.name = self.get('name')
        self.pre_hash = self.get('pre_hash')
        self.hash = self.get('hash')

        self.remote = self.get('tracking_name')

        self.ahead = int(self.get('ahead', '0'))
        self.ahead_str = "+%d" % self.ahead if self.ahead else ''

        self.behind = int(self.get('behind', '0'))
        self.behind_str = "-%d" % self.behind if self.behind else ''

        self.pre_remote = ''  # '[' if self.remote else ' '
        self.post_remote = ''  # ']' if self.remote else ' '

        self.description = self.get('description')

    def colored_field(self, prop_name):
        my_val = getattr(self, prop_name)
        if prop_name in self.colors():
            return color(self.colors()[prop_name], my_val)
        return my_val

    def field_string(self, prop_name, fixed_width_map):
        fixed_width, left_justify = \
            fixed_width_map[
                prop_name] if fixed_width_map and prop_name in fixed_width_map else (0, False)
        return fixed(fixed_width, self.colored_field(prop_name), left_justified=left_justify)

    def fields(self):
        return [
            'line_begin',
            'name',
            ' ',
            'hash',
            ' ',
            'pre_remote',
            'remote',
            ' ',
            'ahead_str',
            ' ',
            'behind_str',
            'post_remote',
            ' ',
            'reldate',
            ' ',
            'date',
            ' ',
            'description'
        ]

    def to_string(self, fixed_width_map=None):
        return ''.join([self.field_string(field, fixed_width_map) for field in self.fields()])

    def __str__(self):
        return self.to_string()

    def set_dates(self, date, reldate):
        try:
            self.datetime = dt.strptime(date, '%Y-%m-%d %H:%M:%S %z')
        except ValueError:
            self.datetime = dt.strptime(date, '%Y-%m-%d %H:%M:%S')

        self.date = dt.strftime(self.datetime, '%Y-%m-%d %H:%M:%S')
        self.reldate = shorten_reldate(reldate)
