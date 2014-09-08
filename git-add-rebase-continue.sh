#!/bin/sh

if [ $# -eq 0 ]; then
	args=.
else
	args="$@"
fi

git add "$args" && git rebase --continue
