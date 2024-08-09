#!/usr/bin/env python
from functools import partial
from sys import stderr

import click
import hashlib


err = partial(print, file=stderr)


def compute_sha256(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256.update(byte_block)
    return sha256.digest()


@click.command()
@click.option('-v', '--verbose', is_flag=True, help="Log each file's hexdigest to stderr")
@click.argument('paths', nargs=-1, type=click.Path(exists=True))
def main(verbose, paths):
    sha256 = hashlib.sha256()
    for path in paths:
        # Compute sha256 digest of path contents
        digest = compute_sha256(path)
        if verbose:
            hexdigest = digest.hex()
            err(f"{path}: {hexdigest}")
        sha256.update(digest)
    result = sha256.hexdigest()
    print(result)


if __name__ == "__main__":
    main()