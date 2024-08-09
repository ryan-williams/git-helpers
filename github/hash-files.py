#!/usr/bin/env python
# Standalone script that mimics GitHub Actions' hashFiles helper
# See also: https://gist.github.com/ryan-williams/2e616363c68072bf67cad675fcb18f3b
import hashlib
import sys


sha256 = hashlib.sha256()

for path in sys.argv[1:]:
    file_sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            file_sha256.update(byte_block)
    sha256.update(file_sha256.digest())

print(sha256.hexdigest())
