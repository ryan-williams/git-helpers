from color import color as C
from datetime import datetime
from dateutil.parser import parse as parse_datetime
import re
from regexs import refname_or_tag_regex
from reldate_util import shorten_reldate


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


Pieces = {}


def assign_piece_by_key(piece):
    Pieces[piece.name] = piece


map(assign_piece_by_key, [
    Piece('refnames', '%d', parse_refnames, ' '.join, color='Yellow'),
    Piece('hash', '%h', color='IRed'),
    Piece('reldate', '%cr', shorten_reldate, color='IGreen'),
    Piece('author', '%an', color='Cyan'),
    Piece('date', '%ci', parse_datetime, render_datetime, color='IBlue'),
    Piece('description', '%s', fix_width=False)
])
