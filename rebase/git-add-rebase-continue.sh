#!/usr/bin/env bash

# `git add` files whose conflicts have been resolved, and continue rebasing.

if [ $# -eq 0 ]; then
	args=.
else
	args="$@"
fi

git add "$args" && git rebase --continue
