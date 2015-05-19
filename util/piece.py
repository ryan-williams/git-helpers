from __future__ import print_function

"""Helpers for "pieces" of formatted output linked to certain format specifiers."""

from .color import color as C, color_symbol, clen
from datetime import datetime
from dateutil.parser import parse as parse_datetime
import re
from .regexs import refname_or_tag_regex
from .reldate_util import shorten_reldate
import subprocess


def fixed(width, s):
    return (' ' * (width - clen(s))) + str(s)


class Piece(object):

    def __call__(self, segment):
        return C(self.color, self.render(self.parse(segment)))


    def parse(self, s):
        return s


    def render(self, segment):
        return str(segment)


    def __init__(self, name, git_format, fix_width=True, color='clear'):
        self.name = name
        self.git_format = git_format
        self.fix_width = fix_width
        self.color = color


class RefnamesPiece(Piece):

    def __call__(self, segments):
        return \
            C(
                self.color,
                ' '.join(
                    [
                        color_symbol('IYellow') + segment[5:] + color_symbol(self.color)
                        if segment.startswith('tag: ')
                        else segment
                        for segment
                        in self.parse(segments)
                    ]
                )
            )


    def __init__(self, color='Yellow'):
        super(RefnamesPiece, self).__init__('refnames', '%d', color=color)

    def parse(self, s):
        match = re.match('^\((?P<names>(?:%s, )*%s)\)$' %
                         (refname_or_tag_regex, refname_or_tag_regex), s)
        if (match):
            return match.group('names').split(', ')
        else:
            return []



class CommitDatePiece(Piece):

    def __init__(self, color='IBlue'):
        super(CommitDatePiece, self).__init__('date', '%ci', color=color)

    def parse(self, s):
        return parse_datetime(s)


    def render(self, dt):
        return datetime.strftime(dt, '%Y-%m-%d %H:%M:%S')


class ReldatePiece(Piece):

    def __init__(self, color='IGreen'):
        super(ReldatePiece, self).__init__('reldate', '%cr', color=color)


    def render(self, dt):
        return shorten_reldate(dt)


default_pieces = [
    RefnamesPiece(),
    Piece('hash', '%h', color='IRed'),
    ReldatePiece(),
    Piece('author', '%an', color='Cyan'),
    CommitDatePiece(),
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
        format_str = self.delimiter.join(
            [piece.git_format for piece in self._pieces]
        )
        cmd = [
            'git',
            'log',
            '--format=%s' % format_str
        ] + args + [ '--' ]

        out, err = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()
        if err:
            raise Exception(err.decode())

        lines = out.decode().splitlines()

        self.results = []

        for line in lines:
            segments = line.strip().split(self.delimiter)
            if len(segments) != len(self._pieces):
                raise Exception(
                    'Invalid line:\n\t%s\nformat str:\n\t%s\ncmd:\n\t%s' % (
                        line,
                        format_str,
                        ' '.join(cmd)
                    )
                )

            values = {}
            for piece, segment in zip(self._pieces, segments):
                values[piece.name] = piece(segment)
            self.results.append(values)

        def compute_max_width_for_piece(piece):
            piece.max_width = max(
                [clen(values[piece.name]) for values in self.results]
            )

        [
            compute_max_width_for_piece(piece)
            for piece
            in self._pieces
            if piece.fix_width
        ]

    def pretty_print(self):
        try:
            print('')
            for values in self.results:
                for piece in self._pieces:
                    if piece.fix_width:
                        print(fixed(piece.max_width, values[piece.name]), end=' ')
                    else:
                        print(values[piece.name], end=' ')
                print('')
            print('')
        except IOError as e:
            # Piping to e.g. `head` can cause "Broken pipe"
            pass
