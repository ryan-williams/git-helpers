#!/usr/bin/env python

from requests import get as GET

def repos(org, sort='updated'):
    resp = GET(f'https://api.github.com/orgs/{org}/repos?sort={sort}')
    resp.raise_for_status()
    repos = resp.json()
    return repos

if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('org',help='GitHub organization to list repos for')
    #parser.add_argument('-n',help='Number of repos to list')
    parser.add_argument('-s','--sort',choices=['created', 'updated', 'pushed', 'full_name'], default='updated')
    args = parser.parse_args()
    org = args.org
    #n = args.n
    sort = args.sort

    res = repos(org, sort)

    import json
    print(json.dumps(res, indent=2))
