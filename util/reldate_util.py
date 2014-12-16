#!/usr/bin/env python

import re
import sys

reldate_subs = [
    (' weeks?', 'wk'),
    (' years?', 'yr'),
    (' months?', 'mo'),
    (' days?', 'd'),
    (' hours?', 'h'),
    (' minutes?', 'm'),
    (' seconds?', 's'),
    (',', ''),
    (' ago', '')
]


def shorten_reldate(reldate):
    for sub in reldate_subs:
        reldate = re.sub(sub[0], sub[1], reldate)
    return reldate

if __name__ == '__main__':
    print '\n'.join([shorten_reldate(arg) for arg in sys.argv[1:]])
