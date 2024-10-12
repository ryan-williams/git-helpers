#!/usr/bin/env bash

set -e

cd "$(dirname "${BASH_SOURCE[0]}")/../test/docker"

docker build -t git-helpers -f git-helpers.dockerfile . 2>/dev/null
docker run --rm -it --name git-helpers git-helpers "$@"
