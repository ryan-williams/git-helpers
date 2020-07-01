#!/usr/bin/env python

from argparse import ArgumentParser
from re import match
from subprocess import check_call, check_output


parser = ArgumentParser()
parser.add_argument('--https',action='store_true',help='When set, add an HTTPS remote')
parser.add_argument('-s','--ssh',action='store_true',help='When set, add an SSH remote')
parser.add_argument('name',nargs='?',help='Name of the remote to add')
parser.add_argument('remote',nargs='?',help='Name of the remote to add')
args = parser.parse_args()
https = args.https
ssh = args.ssh
remote = args.remote
name = args.name

if not remote:
    remotes = [ remote.strip() for remote in check_output(['git','remote']).decode().split('\n') ]
    remotes = [ remote for remote in remotes if remote ]
    if len(remotes) > 1:
        print('Expected one remote:\n\t%s' % "\n\t".join(remotes))
    remote = remotes[0].strip()


from urllib.parse import urlparse
url_str = check_output(['git','remote','get-url',remote]).decode().strip()
url = urlparse(url_str)
if url.scheme:
    if url.scheme != 'https':
        raise ValueError(f'Unrecognized URL: {url_str}')

    assert not ssh
    if not name: name = 's'

    ssh_url = f'git@{url.hostname}:{url.path[1:]}'
    if not ssh_url.endswith('.git'): ssh_url += '.git'

    print(f'Adding SSH remote {name}: {ssh_url}')
    check_call(['git','remote','add',name,ssh_url])
else:
    assert not https
    if not name: name = 'h'

    ssh_url_regex = r'git@(?P<hostname>[^:]+):(?P<path>[\w/\-]+)\.git'
    m = match(ssh_url_regex, url_str).groupdict()

    https_url = f'https://{m["hostname"]}/{m["path"]}'

    print(f'Adding HTTPS remote {name}: {https_url}')
    check_call(['git','remote','add',name,https_url])
