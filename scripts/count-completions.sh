#!/usr/bin/env bash

set -e

cd "$(dirname "${BASH_SOURCE[0]}")/.."

docker build -t git-helpers -f test/docker/git-helpers.dockerfile . 2>/dev/null
docker run --rm -it --name git-helpers git-helpers "$@"
