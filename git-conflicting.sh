#!/bin/sh

git status -s | sed -n "s/^UU //p"
