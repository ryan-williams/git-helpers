#!/usr/bin/env bash

set -e

cd "$(dirname "${BASH_SOURCE[0]}")/.."

args=()
keep_platform=
rm=(--rm)
while getopts "ckpv" opt; do
  case "$opt" in
    c) args+=(-c) ;;
    k) rm=() ;;
    p) keep_platform=1 ;;
    v) args+=(-v) ;;
    \?) usage ;;
  esac
done
shift $((OPTIND-1))

if [ -z "$keep_platform" ] && [ -n "$DOCKER_DEFAULT_PLATFORM" ]; then
  echo "Unsetting \$DOCKER_DEFAULT_PLATFORM=$DOCKER_DEFAULT_PLATFORM" >&2
  unset DOCKER_DEFAULT_PLATFORM
fi

docker build -q -t git-helpers -f test/docker/git-helpers.dockerfile . >&2
tty_flag=()
if [ -t 0 ]; then
  tty_flag=(-it)
else
  tty_flag=(-i)
fi
docker run "${rm[@]}" "${tty_flag[@]}" --name git-helpers git-helpers "${args[@]}" "$@" | tr -d '\r'
