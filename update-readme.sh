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
    if ! mdcmd -C; then
        echo "Error: mdcmd -C failed" >&2
        exit 1
    fi
fi

# Update README subtitle
# Extract count from count-completions.sh output in README
n="$(grep -m1 '^# [0-9]' README.md | awk '{print $2}')"
if [ -z "$n" ]; then
  echo "Error: Could not extract completion count from README (did count-completions.sh run successfully?)" >&2
  exit 1
fi
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
