
"""Helpers for "pieces" of formatted output linked to certain format specifiers."""

from color import color as C, clen
from datetime import datetime
from dateutil.parser import parse as parse_datetime
import re
from regexs import refname_or_tag_regex
from reldate_util import shorten_reldate
import subprocess


def fixed(width, s):
    return (' ' * (width - clen(s))) + str(s)


class Piece:

    def __call__(self, segment):
        return C(self.color, self.renderer(self.parser(segment)))

    def __init__(self, name, git_format, parser=lambda x: x, renderer=str, fix_width=True, color='clear'):
        self.name = name
        self.git_format = git_format
        self.parser = parser

        self.renderer = renderer
        self.fix_width = fix_width
        self.color = color


def parse_refnames(s):
    match = re.match('^\((?P<names>(?:%s, )*%s)\)$' %
                     (refname_or_tag_regex, refname_or_tag_regex), s)
    if (match):
        return match.group('names').split(', ')
    else:
        return []


def render_datetime(dt):
    return datetime.strftime(dt, '%Y-%m-%d %H:%M:%S')


default_pieces = [
    Piece('refnames', '%d', parse_refnames, ' '.join, color='Yellow'),
    Piece('hash', '%h', color='IRed'),
    Piece('reldate', '%cr', shorten_reldate, color='IGreen'),
    Piece('author', '%an', color='Cyan'),
    Piece('date', '%ci', parse_datetime, render_datetime, color='IBlue'),
    Piece('description', '%s', fix_width=False)
]

class Pieces(object):

    def __init__(self, *pieces):
        self._pieces_map = {}
        self._pieces = []
        if not pieces:
            self.add(*default_pieces)
        else:
            self.add(pieces)


    def __getitem__(self, item):
        return self._pieces_map[item]


    def __setitem__(self, key, value):
        self._pieces_map[key] = value


    def add(self, *pieces):
        for piece in pieces:
            self._pieces_map[piece.name] = piece
        self._pieces += pieces


    delimiter = '|||'
    def parse_log(self, args):
        cmd = [
            'git',
            'log',
            '--format=%s' % self.delimiter.join(
                map(lambda piece: piece.git_format, self._pieces)
            )
        ] + args + [ '--' ]

        out, err = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()
        if err:
            raise Exception(err)

        lines = out.splitlines()

        self.results = []

        for line in lines:
            segments = line.strip().split(self.delimiter)
            if len(segments) != len(self._pieces):
                raise Exception('Invalid line %s' % line)

            values = {}
            for piece, segment in zip(self._pieces, segments):
                values[piece.name] = piece(segment)
            self.results.append(values)

        def compute_max_width_for_piece(piece):
            piece.max_width = max(
                map(lambda values: clen(values[piece.name]), self.results))

        map(
            compute_max_width_for_piece,
            filter(lambda piece: piece.fix_width, self._pieces)
        )

    def pretty_print(self):
        print ''
        for values in self.results:
            for piece in self._pieces:
                if piece.fix_width:
                    print fixed(piece.max_width, values[piece.name]),
                else:
                    print values[piece.name],
            print ''
        print ''

