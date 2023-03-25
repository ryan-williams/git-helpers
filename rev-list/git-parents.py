#!/usr/bin/env python
from subprocess import check_output, check_call

import click


@click.command()
@click.option('-f', '--format', default='%H')
@click.argument('ref', default='HEAD')
def main(format, ref):
    parents = check_output([ 'git', 'rev-list', '--parents', '-n1', ref ]).decode().rstrip('\n').split(' ')[1:]
    check_call(['git', '--no-pager', 'log', '--no-walk', f'--format={format}'] + parents)


if __name__ == '__main__':
    main()
