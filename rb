#!/bin/sh

echo $1
git rebase -i HEAD~$1
