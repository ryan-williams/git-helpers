#!/usr/bin/env bash

set -exo pipefail

usage() {
  echo "Usage: $0 [-D] [-M]" >&2
  exit 1
}

desc=1
mdcmd=1
while getopts "DM" opt; do
  case "$opt" in
    D) desc= ;;
    M) mdcmd= ;;
    *) usage ;;
  esac
done
shift "$((OPTIND -1))"

# Exec+Update README code blocks
if [ -n "$mdcmd" ]; then
    mdcmd -C
fi

# Update README subtitle
n="$(grep -m1 '^# .* completions added' README.md  | awk '{print $2}')"
ns="$(LC_NUMERIC=en_US.UTF-8 printf "%'d" "$n")"

in=README.md
out=README.tmp
head -n1 "$in" > "$out"
echo "[$ns](#count-completions) Git aliases and scripts." >> "$out"
tail -n+3 "$in" >> "$out"
mv "$out" "$in"

# Update repo description
if [ -n "$desc" ]; then
  d0="$(gh repo view --json description -q .description)"
  d1="$ns Git aliases and scripts"
  if [ "$d0" = "$d1" ]; then
    echo "Description unchanged: $d1" >&2
  else
    echo "Updating description: $d1" >&2
    gh repo edit -d "$d1"
  fi
fi
